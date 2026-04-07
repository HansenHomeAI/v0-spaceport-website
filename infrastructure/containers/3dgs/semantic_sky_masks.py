#!/usr/bin/env python3
"""
Semantic sky mask generation for NerfStudio COLMAP datasets.

This module keeps the training-time sky mask path separate from the viewer's
learned background export logic. It generates binary masks from a semantic
segmentation model, post-processes them with topology-only rules, and injects
`mask_path` entries into a NerfStudio `transforms.json`.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover - exercised in container/runtime.
    cv2 = None

try:
    import torch
    import torch.nn.functional as torch_functional
except ImportError:  # pragma: no cover - exercised in container/runtime.
    torch = None
    torch_functional = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover - exercised in container/runtime.
    Image = None

try:
    from transformers import AutoImageProcessor, AutoModelForSemanticSegmentation
except ImportError:  # pragma: no cover - exercised in container/runtime.
    AutoImageProcessor = None
    AutoModelForSemanticSegmentation = None


DEFAULT_MODEL_ID = "nvidia/segformer-b0-finetuned-ade-512-512"
CC_STAT_LEFT = 0
CC_STAT_TOP = 1
CC_STAT_WIDTH = 2
CC_STAT_HEIGHT = 3
CC_STAT_AREA = 4


@dataclass(frozen=True)
class SemanticSkyMaskSettings:
    enabled: bool = False
    model_id: str = DEFAULT_MODEL_ID
    confidence_threshold: float = 0.55
    min_component_area: float = 0.002
    fill_hole_area: float = 0.001
    keep_top_connected_only: bool = True


@dataclass(frozen=True)
class ColmapImageRecord:
    image_id: int
    name: str


def _require_runtime_dependency(module: Any, package_name: str) -> None:
    if module is None:
        raise RuntimeError(f"{package_name} is required for semantic sky masking")


def _binary_mask(mask: np.ndarray) -> np.ndarray:
    return (mask.astype(bool)).astype(np.uint8)


def _mask_area_ratio(mask: np.ndarray) -> float:
    return float(mask.astype(bool).sum() / mask.size) if mask.size else 0.0


def _connected_components_with_stats(mask: np.ndarray) -> tuple[int, np.ndarray, np.ndarray]:
    binary = _binary_mask(mask)
    if cv2 is not None:
        component_count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        return component_count, labels, stats

    height, width = binary.shape
    labels = np.zeros((height, width), dtype=np.int32)
    stats: List[List[int]] = [[0, 0, width, height, int((binary == 0).sum())]]
    current_label = 1

    for row in range(height):
        for col in range(width):
            if binary[row, col] == 0 or labels[row, col] != 0:
                continue

            stack = [(row, col)]
            labels[row, col] = current_label
            min_row = max_row = row
            min_col = max_col = col
            area = 0

            while stack:
                current_row, current_col = stack.pop()
                area += 1
                min_row = min(min_row, current_row)
                max_row = max(max_row, current_row)
                min_col = min(min_col, current_col)
                max_col = max(max_col, current_col)

                for delta_row in (-1, 0, 1):
                    for delta_col in (-1, 0, 1):
                        if delta_row == 0 and delta_col == 0:
                            continue
                        next_row = current_row + delta_row
                        next_col = current_col + delta_col
                        if (
                            0 <= next_row < height
                            and 0 <= next_col < width
                            and binary[next_row, next_col] == 1
                            and labels[next_row, next_col] == 0
                        ):
                            labels[next_row, next_col] = current_label
                            stack.append((next_row, next_col))

            stats.append(
                [
                    int(min_col),
                    int(min_row),
                    int(max_col - min_col + 1),
                    int(max_row - min_row + 1),
                    int(area),
                ]
            )
            current_label += 1

    return current_label, labels, np.array(stats, dtype=np.int32)


def load_colmap_image_records(images_txt_path: Path) -> List[ColmapImageRecord]:
    """Read registered image IDs and names from COLMAP's images.txt."""
    records: List[ColmapImageRecord] = []
    non_comment_lines: List[str] = []

    with open(images_txt_path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                non_comment_lines.append(stripped)

    for line_index in range(0, len(non_comment_lines), 2):
        parts = non_comment_lines[line_index].split(maxsplit=9)
        if len(parts) < 10:
            raise ValueError(f"Malformed COLMAP image record: {non_comment_lines[line_index]}")
        records.append(ColmapImageRecord(image_id=int(parts[0]), name=parts[9]))

    return records


def post_process_semantic_sky_mask(
    mask: np.ndarray,
    min_component_area_ratio: float,
    fill_hole_area_ratio: float,
    keep_top_connected_only: bool,
) -> np.ndarray:
    """
    Apply topology-only cleanup to a binary semantic sky mask.

    Rules:
    1. keep only components above `min_component_area_ratio`
    2. optionally keep only components touching the top image border
    3. remove small islands again after top-border filtering
    4. fill small interior holes under `fill_hole_area_ratio`
    """

    if mask.ndim != 2:
        raise ValueError("Semantic sky masks must be 2D")

    height, width = mask.shape
    image_area = max(1, height * width)
    min_component_pixels = max(1, int(round(image_area * float(min_component_area_ratio))))
    fill_hole_pixels = max(1, int(round(image_area * float(fill_hole_area_ratio))))

    cleaned = _binary_mask(mask)
    cleaned = remove_small_components(cleaned, min_component_pixels)

    if keep_top_connected_only:
        cleaned = keep_top_connected_components(cleaned)
        cleaned = remove_small_components(cleaned, min_component_pixels)

    cleaned = fill_small_holes(cleaned, fill_hole_pixels)
    return cleaned.astype(bool)


def remove_small_components(mask: np.ndarray, min_component_pixels: int) -> np.ndarray:
    binary = _binary_mask(mask)
    if binary.size == 0:
        return binary

    component_count, labels, stats = _connected_components_with_stats(binary)
    kept = np.zeros_like(binary)
    for label in range(1, component_count):
        if int(stats[label, CC_STAT_AREA]) >= int(min_component_pixels):
            kept[labels == label] = 1
    return kept


def keep_top_connected_components(mask: np.ndarray) -> np.ndarray:
    binary = _binary_mask(mask)
    if binary.size == 0:
        return binary

    component_count, labels, _ = _connected_components_with_stats(binary)
    if component_count <= 1:
        return binary

    top_labels = np.unique(labels[0, :])
    top_labels = top_labels[top_labels != 0]
    if top_labels.size == 0:
        return np.zeros_like(binary)

    return np.isin(labels, top_labels).astype(np.uint8)


def fill_small_holes(mask: np.ndarray, max_hole_pixels: int) -> np.ndarray:
    binary = _binary_mask(mask)
    if binary.size == 0:
        return binary

    inverse = 1 - binary
    component_count, labels, stats = _connected_components_with_stats(inverse)
    filled = binary.copy()
    height, width = binary.shape

    for label in range(1, component_count):
        x = int(stats[label, CC_STAT_LEFT])
        y = int(stats[label, CC_STAT_TOP])
        component_width = int(stats[label, CC_STAT_WIDTH])
        component_height = int(stats[label, CC_STAT_HEIGHT])
        area = int(stats[label, CC_STAT_AREA])
        touches_border = (
            x == 0
            or y == 0
            or (x + component_width) >= width
            or (y + component_height) >= height
        )
        if not touches_border and area <= int(max_hole_pixels):
            filled[labels == label] = 1

    return filled


class SemanticSkyMaskGenerator:
    """Generate binary semantic sky masks from source RGB images."""

    def __init__(
        self,
        settings: SemanticSkyMaskSettings,
        device: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.settings = settings
        self.device = device or self._resolve_device()
        self.logger = logger or logging.getLogger(__name__)
        self._processor = None
        self._model = None
        self._sky_label_id = None

    def _resolve_device(self) -> str:
        if torch is not None and torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def _load_model(self) -> None:
        _require_runtime_dependency(torch, "torch")
        _require_runtime_dependency(Image, "Pillow")
        _require_runtime_dependency(AutoImageProcessor, "transformers")
        _require_runtime_dependency(AutoModelForSemanticSegmentation, "transformers")

        if self._processor is not None and self._model is not None and self._sky_label_id is not None:
            return

        self.logger.info(
            "Loading semantic sky model %s on %s",
            self.settings.model_id,
            self.device,
        )
        self._processor = AutoImageProcessor.from_pretrained(self.settings.model_id)
        self._model = AutoModelForSemanticSegmentation.from_pretrained(self.settings.model_id)
        self._model.to(self.device)
        self._model.eval()

        id_to_label = getattr(self._model.config, "id2label", {}) or {}
        normalized = {
            int(label_id): str(label_name).strip().lower()
            for label_id, label_name in id_to_label.items()
        }
        sky_matches = [label_id for label_id, label_name in normalized.items() if label_name == "sky"]
        if len(sky_matches) != 1:
            raise RuntimeError(
                f"Could not resolve a unique 'sky' label in {self.settings.model_id}: {normalized}"
            )
        self._sky_label_id = int(sky_matches[0])
        self.logger.info("Resolved semantic sky label id: %s", self._sky_label_id)

    @property
    def sky_label_id(self) -> int:
        self._load_model()
        assert self._sky_label_id is not None
        return self._sky_label_id

    def generate_mask(self, image_path: Path, output_path: Path) -> Dict[str, Any]:
        return self.generate_masks(
            image_paths=[image_path],
            output_paths=[output_path],
        )[0]

    def generate_masks(self, image_paths: List[Path], output_paths: List[Path]) -> List[Dict[str, Any]]:
        self._load_model()
        assert self._processor is not None
        assert self._model is not None
        assert self._sky_label_id is not None
        assert torch is not None
        assert torch_functional is not None
        assert Image is not None

        if len(image_paths) != len(output_paths):
            raise ValueError("image_paths and output_paths must have the same length")

        rgb_images = []
        source_sizes = []
        for image_path in image_paths:
            with Image.open(image_path) as image_handle:
                rgb_image = image_handle.convert("RGB")
                rgb_images.append(rgb_image)
                source_sizes.append(rgb_image.size)

        processor_inputs = self._processor(images=rgb_images, return_tensors="pt")

        pixel_values = processor_inputs["pixel_values"].to(self.device)
        with torch.no_grad():
            logits = self._model(pixel_values=pixel_values).logits
            probabilities = torch.softmax(logits, dim=1)
            sky_probabilities = probabilities[:, self._sky_label_id : self._sky_label_id + 1]
            predicted_labels = probabilities.argmax(dim=1, keepdim=True)
            binary_reduced = (
                (predicted_labels == self._sky_label_id)
                & (sky_probabilities >= float(self.settings.confidence_threshold))
            ).float()
        records: List[Dict[str, Any]] = []
        for image_index, (image_path, output_path) in enumerate(zip(image_paths, output_paths)):
            source_width, source_height = source_sizes[image_index]
            binary_source_resolution = torch_functional.interpolate(
                binary_reduced[image_index : image_index + 1],
                size=(source_height, source_width),
                mode="nearest",
            )[0, 0]

            raw_mask = binary_source_resolution.detach().cpu().numpy() > 0.5
            final_mask = post_process_semantic_sky_mask(
                mask=raw_mask,
                min_component_area_ratio=self.settings.min_component_area,
                fill_hole_area_ratio=self.settings.fill_hole_area,
                keep_top_connected_only=self.settings.keep_top_connected_only,
            )

            output_path.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray((final_mask.astype(np.uint8) * 255), mode="L").save(output_path)
            records.append(
                {
                    "source_image": image_path.name,
                    "source_path": str(image_path),
                    "mask_path": str(output_path),
                    "width": int(source_width),
                    "height": int(source_height),
                    "raw_mask_ratio": _mask_area_ratio(raw_mask),
                    "mask_ratio": _mask_area_ratio(final_mask),
                    "top_border_ratio": float(final_mask[0].mean()) if final_mask.size else 0.0,
                    "sky_label_id": int(self._sky_label_id),
                    "confidence_threshold": float(self.settings.confidence_threshold),
                }
            )

        return records


def _safe_mask_basename(record: ColmapImageRecord) -> str:
    relative_path = Path(record.name)
    safe_stem = "__".join(relative_path.with_suffix("").parts)
    return f"{record.image_id:05d}-{safe_stem}.png"


def generate_source_semantic_sky_masks(
    dataset_dir: Path,
    output_dir: Path,
    settings: SemanticSkyMaskSettings,
    device: Optional[str] = None,
    batch_size: Optional[int] = None,
    selected_image_names: Optional[Iterable[str]] = None,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """
    Generate source-resolution semantic sky masks for registered COLMAP frames.

    Returns a summary with the per-image records embedded so the caller can map
    the masks onto NerfStudio's converted image names later.
    """

    logger = logger or logging.getLogger(__name__)
    records = load_colmap_image_records(dataset_dir / "sparse" / "0" / "images.txt")
    if selected_image_names is not None:
        selected_lookup = {str(name) for name in selected_image_names}
        records = [record for record in records if record.name in selected_lookup]
    generator = SemanticSkyMaskGenerator(settings=settings, device=device, logger=logger)
    mask_records: List[Dict[str, Any]] = []
    records_by_name: Dict[str, Dict[str, Any]] = {}
    records_by_id: Dict[int, Dict[str, Any]] = {}

    image_root = dataset_dir / "images"
    output_dir.mkdir(parents=True, exist_ok=True)
    effective_batch_size = batch_size or (8 if generator.device == "cpu" else 16)

    for batch_start in range(0, len(records), effective_batch_size):
        batch_records = records[batch_start : batch_start + effective_batch_size]
        batch_image_paths = []
        batch_mask_paths = []
        for record in batch_records:
            image_path = image_root / record.name
            if not image_path.exists():
                raise FileNotFoundError(f"Registered COLMAP image is missing: {image_path}")
            batch_image_paths.append(image_path)
            batch_mask_paths.append(output_dir / _safe_mask_basename(record))

        batch_mask_records = generator.generate_masks(
            image_paths=batch_image_paths,
            output_paths=batch_mask_paths,
        )

        for record, mask_record in zip(batch_records, batch_mask_records):
            mask_record["image_id"] = int(record.image_id)
            mask_record["image_name"] = record.name
            mask_records.append(mask_record)
            records_by_name[record.name] = mask_record
            records_by_id[record.image_id] = mask_record

    mask_coverages = [record["mask_ratio"] for record in mask_records]
    top_border_coverages = [record["top_border_ratio"] for record in mask_records]
    summary = {
        "enabled": True,
        "settings": asdict(settings),
        "device": generator.device,
        "sky_label_id": generator.sky_label_id,
        "registered_image_count": len(records),
        "mean_mask_ratio": float(np.mean(mask_coverages)) if mask_coverages else 0.0,
        "min_mask_ratio": float(np.min(mask_coverages)) if mask_coverages else 0.0,
        "max_mask_ratio": float(np.max(mask_coverages)) if mask_coverages else 0.0,
        "mean_top_border_ratio": float(np.mean(top_border_coverages)) if top_border_coverages else 0.0,
        "mask_records": mask_records,
        "records_by_name": records_by_name,
        "records_by_id": records_by_id,
    }
    return summary


def _resolve_source_mask_record(
    frame: Dict[str, Any],
    frame_index: int,
    frame_count: int,
    source_summary: Dict[str, Any],
) -> tuple[Dict[str, Any], str]:
    records_by_id = source_summary.get("records_by_id", {})
    records_by_name = source_summary.get("records_by_name", {})
    mask_records = source_summary.get("mask_records", [])

    colmap_image_id = frame.get("colmap_im_id")
    if colmap_image_id is not None and int(colmap_image_id) in records_by_id:
        return records_by_id[int(colmap_image_id)], "colmap_im_id"

    file_path = str(frame.get("file_path", ""))
    relative_name = Path(file_path).name
    direct_name_match = records_by_name.get(relative_name)
    if direct_name_match is not None:
        return direct_name_match, "file_name"

    frame_stem = Path(file_path).stem
    stem_matches = [
        record for record in mask_records if Path(str(record["image_name"])).stem == frame_stem
    ]
    if len(stem_matches) == 1:
        return stem_matches[0], "file_stem"

    if frame_count == len(mask_records):
        return mask_records[frame_index], "frame_index"

    raise KeyError(f"Could not resolve source mask for frame {frame_index}: {frame}")


def attach_masks_to_transforms(
    transforms_path: Path,
    converted_data_dir: Path,
    source_summary: Dict[str, Any],
    settings: SemanticSkyMaskSettings,
) -> Dict[str, Any]:
    """
    Copy per-image sky masks into `converted_data/masks/` and inject mask paths.

    When disabled, all existing `mask_path` entries are removed from the
    transforms file and no mask directory is created.
    """

    with open(transforms_path, "r", encoding="utf-8") as handle:
        transforms = json.load(handle)

    frames = transforms.get("frames", [])
    if not isinstance(frames, list):
        raise ValueError("transforms.json is missing a valid frames array")

    if not settings.enabled:
        for frame in frames:
            frame.pop("mask_path", None)
        with open(transforms_path, "w", encoding="utf-8") as handle:
            json.dump(transforms, handle, indent=2)
        return {
            "enabled": False,
            "settings": asdict(settings),
            "frames_total": len(frames),
            "frames_with_masks": 0,
        }

    mask_dir = converted_data_dir / "masks"
    mask_dir.mkdir(parents=True, exist_ok=True)

    per_frame_stats: List[Dict[str, Any]] = []
    mapping_strategy_counts: Dict[str, int] = {}
    frame_count = len(frames)

    for frame_index, frame in enumerate(frames):
        source_record, strategy = _resolve_source_mask_record(
            frame=frame,
            frame_index=frame_index,
            frame_count=frame_count,
            source_summary=source_summary,
        )
        mapping_strategy_counts[strategy] = mapping_strategy_counts.get(strategy, 0) + 1

        source_mask_path = Path(str(source_record["mask_path"]))
        if not source_mask_path.exists():
            raise FileNotFoundError(f"Source semantic mask missing: {source_mask_path}")

        converted_frame_path = Path(str(frame.get("file_path", "")))
        converted_mask_name = f"{converted_frame_path.stem}.png"
        converted_mask_path = mask_dir / converted_mask_name
        converted_mask_path.write_bytes(source_mask_path.read_bytes())

        relative_mask_path = converted_mask_path.relative_to(converted_data_dir)
        frame["mask_path"] = relative_mask_path.as_posix()

        per_frame_stats.append(
            {
                "frame_index": frame_index,
                "file_path": frame.get("file_path"),
                "mask_path": frame["mask_path"],
                "image_name": source_record["image_name"],
                "image_id": source_record["image_id"],
                "mask_ratio": source_record["mask_ratio"],
                "top_border_ratio": source_record["top_border_ratio"],
                "mapping_strategy": strategy,
            }
        )

    with open(transforms_path, "w", encoding="utf-8") as handle:
        json.dump(transforms, handle, indent=2)

    mask_coverages = [record["mask_ratio"] for record in per_frame_stats]
    top_border_coverages = [record["top_border_ratio"] for record in per_frame_stats]
    return {
        "enabled": True,
        "settings": asdict(settings),
        "frames_total": frame_count,
        "frames_with_masks": len(per_frame_stats),
        "mean_mask_ratio": float(np.mean(mask_coverages)) if mask_coverages else 0.0,
        "min_mask_ratio": float(np.min(mask_coverages)) if mask_coverages else 0.0,
        "max_mask_ratio": float(np.max(mask_coverages)) if mask_coverages else 0.0,
        "mean_top_border_ratio": float(np.mean(top_border_coverages)) if top_border_coverages else 0.0,
        "mapping_strategy_counts": mapping_strategy_counts,
        "per_frame_stats": per_frame_stats,
    }


def compact_semantic_mask_summary(summary: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Drop bulky per-frame mappings while keeping reproducible settings/statistics."""
    if not summary:
        return {
            "enabled": False,
            "settings": asdict(SemanticSkyMaskSettings()),
        }

    compact = dict(summary)
    compact.pop("mask_records", None)
    compact.pop("records_by_name", None)
    compact.pop("records_by_id", None)
    return compact


def write_summary_json(summary: Dict[str, Any], output_path: Path) -> None:
    serializable = compact_semantic_mask_summary(summary)
    if "per_frame_stats" in summary:
        serializable["per_frame_stats"] = summary["per_frame_stats"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(serializable, handle, indent=2)
