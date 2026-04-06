#!/usr/bin/env python3
"""
Semantic sky masking helpers for NerfStudio preprocessing.

This module generates sky-only masks from semantic segmentation, post-processes
them into horizon-safe regions, and writes NerfStudio-compatible training masks
that ignore sky pixels during foreground training.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import cv2
import numpy as np
from PIL import Image


LOGGER = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}


@dataclass
class SemanticSkyMaskConfig:
    enabled: bool = False
    model_id: str = "nvidia/segformer-b0-finetuned-ade-512-512"
    confidence_threshold: float = 0.55
    min_component_area: float = 0.002
    fill_hole_area: float = 0.001
    keep_top_connected_only: bool = True
    inference_device: str = "cpu"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FrameMaskStats:
    frame_name: str
    image_width: int
    image_height: int
    masked_fraction: float
    masked_pixel_count: int
    top_border_masked_fraction: float
    connected_to_top_border: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticSkyMaskSummary:
    enabled: bool
    config: Dict[str, Any]
    model_labels: list[str]
    mask_mode: str
    mask_output_dir: Optional[str]
    frame_count: int
    sampled_overlay_count: int
    average_masked_fraction: float
    min_masked_fraction: float
    max_masked_fraction: float
    top_connected_frame_fraction: float
    frame_stats: list[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_semantic_sky_config(raw_config: Optional[Dict[str, Any]]) -> SemanticSkyMaskConfig:
    raw_config = raw_config or {}
    return SemanticSkyMaskConfig(
        enabled=bool(raw_config.get("enabled", False)),
        model_id=str(raw_config.get("model_id", "nvidia/segformer-b0-finetuned-ade-512-512")),
        confidence_threshold=float(raw_config.get("confidence_threshold", 0.55)),
        min_component_area=float(raw_config.get("min_component_area", 0.002)),
        fill_hole_area=float(raw_config.get("fill_hole_area", 0.001)),
        keep_top_connected_only=bool(raw_config.get("keep_top_connected_only", True)),
        inference_device=str(raw_config.get("inference_device", "cpu")),
    )


def _list_images(images_dir: Path) -> list[Path]:
    image_paths = sorted(
        path
        for path in images_dir.iterdir()
        if path.is_file() and path.suffix in IMAGE_EXTENSIONS
    )
    if not image_paths:
        raise FileNotFoundError(f"No images found in {images_dir}")

    stems: Dict[str, Path] = {}
    for path in image_paths:
        if path.stem in stems:
            raise ValueError(
                f"Duplicate image stem '{path.stem}' found in {stems[path.stem]} and {path}; "
                "semantic mask outputs would collide"
            )
        stems[path.stem] = path
    return image_paths


def _load_model_bundle(config: SemanticSkyMaskConfig) -> tuple[Any, Any, list[int], list[str]]:
    import torch
    from transformers import AutoImageProcessor, AutoModelForSemanticSegmentation

    processor = AutoImageProcessor.from_pretrained(config.model_id)
    model = AutoModelForSemanticSegmentation.from_pretrained(config.model_id)
    model.to(config.inference_device)
    model.eval()

    id2label = getattr(model.config, "id2label", {}) or {}
    sky_class_ids = [
        int(class_id)
        for class_id, label in id2label.items()
        if str(label).strip().lower() == "sky"
    ]
    if not sky_class_ids:
        sky_class_ids = [
            int(class_id)
            for class_id, label in id2label.items()
            if "sky" in str(label).strip().lower()
        ]
    if not sky_class_ids:
        raise RuntimeError(f"Model {config.model_id} does not expose a sky class in id2label")

    sky_labels = [str(id2label[class_id]) for class_id in sky_class_ids]
    return processor, model, sky_class_ids, sky_labels


def _predict_raw_sky_mask(
    image_path: Path,
    processor: Any,
    model: Any,
    sky_class_ids: list[int],
    confidence_threshold: float,
    device: str,
) -> np.ndarray:
    import torch

    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    pixel_values = inputs["pixel_values"].to(device)

    with torch.no_grad():
        outputs = model(pixel_values=pixel_values)
        logits = outputs.logits
        probabilities = torch.softmax(logits, dim=1)
        sky_probability = probabilities[:, sky_class_ids, :, :].sum(dim=1, keepdim=False)
        reduced_mask = sky_probability.squeeze(0).cpu().numpy() >= confidence_threshold

    # Resize the reduced semantic mask back to the source image before morphology.
    restored = Image.fromarray((reduced_mask.astype(np.uint8) * 255), mode="L").resize(
        image.size,
        resample=Image.Resampling.NEAREST,
    )
    return np.asarray(restored, dtype=np.uint8) > 0


def _connected_components(binary_mask: np.ndarray) -> tuple[int, np.ndarray, np.ndarray]:
    binary_mask = binary_mask.astype(np.uint8)
    component_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(binary_mask, connectivity=8)
    return component_count, labels, stats


def keep_top_connected_components(binary_mask: np.ndarray) -> np.ndarray:
    if not binary_mask.any():
        return binary_mask.astype(bool)

    component_count, labels, _ = _connected_components(binary_mask)
    keep_labels = {int(label) for label in np.unique(labels[0, :]) if int(label) != 0}
    if not keep_labels:
        return np.zeros_like(binary_mask, dtype=bool)

    kept = np.isin(labels, list(keep_labels))
    return kept.astype(bool)


def remove_small_components(binary_mask: np.ndarray, min_area_px: int) -> np.ndarray:
    if min_area_px <= 0 or not binary_mask.any():
        return binary_mask.astype(bool)

    component_count, labels, stats = _connected_components(binary_mask)
    kept = np.zeros_like(binary_mask, dtype=bool)
    for label in range(1, component_count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area >= min_area_px:
            kept |= labels == label
    return kept


def fill_small_holes(binary_mask: np.ndarray, max_hole_area_px: int) -> np.ndarray:
    if max_hole_area_px <= 0:
        return binary_mask.astype(bool)

    inverted = (~binary_mask.astype(bool)).astype(np.uint8)
    component_count, labels, stats = _connected_components(inverted)
    filled = binary_mask.astype(bool).copy()
    height, width = filled.shape

    border_labels = set(np.unique(labels[0, :]).tolist())
    border_labels.update(np.unique(labels[-1, :]).tolist())
    border_labels.update(np.unique(labels[:, 0]).tolist())
    border_labels.update(np.unique(labels[:, -1]).tolist())

    for label in range(1, component_count):
        if label in border_labels:
            continue
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area <= max_hole_area_px:
            filled |= labels == label
    return filled


def postprocess_sky_mask(binary_mask: np.ndarray, config: SemanticSkyMaskConfig) -> np.ndarray:
    image_area = int(binary_mask.shape[0] * binary_mask.shape[1])
    min_component_area_px = max(1, int(round(image_area * config.min_component_area)))
    max_hole_area_px = max(1, int(round(image_area * config.fill_hole_area)))

    processed = binary_mask.astype(bool)
    if config.keep_top_connected_only:
        processed = keep_top_connected_components(processed)
    processed = remove_small_components(processed, min_component_area_px)
    processed = fill_small_holes(processed, max_hole_area_px)
    return processed


def build_training_keep_mask(sky_mask: np.ndarray) -> np.ndarray:
    keep_mask = np.full(sky_mask.shape, 255, dtype=np.uint8)
    keep_mask[sky_mask.astype(bool)] = 0
    return keep_mask


def _write_mask(path: Path, mask: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((mask.astype(np.uint8) * 255), mode="L").save(path)


def _mask_stats(frame_name: str, sky_mask: np.ndarray) -> FrameMaskStats:
    height, width = sky_mask.shape
    masked_pixels = int(np.count_nonzero(sky_mask))
    top_masked_pixels = int(np.count_nonzero(sky_mask[0, :])) if height else 0
    return FrameMaskStats(
        frame_name=frame_name,
        image_width=width,
        image_height=height,
        masked_fraction=masked_pixels / float(width * height) if width and height else 0.0,
        masked_pixel_count=masked_pixels,
        top_border_masked_fraction=top_masked_pixels / float(width) if width else 0.0,
        connected_to_top_border=bool(top_masked_pixels > 0),
    )


def _build_summary(
    *,
    enabled: bool,
    config: SemanticSkyMaskConfig,
    model_labels: Iterable[str],
    mask_mode: str,
    mask_output_dir: Optional[Path],
    frame_stats: list[FrameMaskStats],
    sampled_overlay_count: int = 0,
) -> SemanticSkyMaskSummary:
    masked_fractions = [frame.masked_fraction for frame in frame_stats]
    connected_frames = [frame.connected_to_top_border for frame in frame_stats]
    return SemanticSkyMaskSummary(
        enabled=enabled,
        config=config.to_dict(),
        model_labels=list(model_labels),
        mask_mode=mask_mode,
        mask_output_dir=str(mask_output_dir) if mask_output_dir else None,
        frame_count=len(frame_stats),
        sampled_overlay_count=sampled_overlay_count,
        average_masked_fraction=float(np.mean(masked_fractions)) if masked_fractions else 0.0,
        min_masked_fraction=float(np.min(masked_fractions)) if masked_fractions else 0.0,
        max_masked_fraction=float(np.max(masked_fractions)) if masked_fractions else 0.0,
        top_connected_frame_fraction=float(np.mean(connected_frames)) if connected_frames else 0.0,
        frame_stats=[frame.to_dict() for frame in frame_stats],
    )


def generate_semantic_sky_masks(
    images_dir: Path,
    output_dir: Path,
    config: SemanticSkyMaskConfig,
) -> SemanticSkyMaskSummary:
    if not config.enabled:
        return _build_summary(
            enabled=False,
            config=config,
            model_labels=[],
            mask_mode="disabled",
            mask_output_dir=None,
            frame_stats=[],
        )

    image_paths = _list_images(images_dir)
    processor, model, sky_class_ids, sky_labels = _load_model_bundle(config)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame_stats: list[FrameMaskStats] = []
    for image_path in image_paths:
        raw_mask = _predict_raw_sky_mask(
            image_path=image_path,
            processor=processor,
            model=model,
            sky_class_ids=sky_class_ids,
            confidence_threshold=config.confidence_threshold,
            device=config.inference_device,
        )
        processed_mask = postprocess_sky_mask(raw_mask, config)
        _write_mask(output_dir / f"{image_path.stem}.png", processed_mask)
        frame_stats.append(_mask_stats(image_path.name, processed_mask))

    summary = _build_summary(
        enabled=True,
        config=config,
        model_labels=sky_labels,
        mask_mode="sky_region_binary",
        mask_output_dir=output_dir,
        frame_stats=frame_stats,
    )
    (output_dir / "semantic_sky_mask_summary.json").write_text(
        json.dumps(summary.to_dict(), indent=2),
        encoding="utf-8",
    )
    return summary


def parse_colmap_images(image_list_path: Path) -> tuple[dict[int, str], list[str]]:
    image_by_id: dict[int, str] = {}
    ordered_names: list[str] = []
    raw_lines = [
        line.strip()
        for line in image_list_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    for index in range(0, len(raw_lines), 2):
        metadata_line = raw_lines[index]
        parts = metadata_line.split()
        if len(parts) < 10:
            continue
        image_id = int(parts[0])
        image_name = parts[-1]
        image_by_id[image_id] = image_name
        ordered_names.append(image_name)
    return image_by_id, ordered_names


def _resolve_source_image_name(
    frame: Dict[str, Any],
    frame_index: int,
    image_by_id: dict[int, str],
    ordered_names: list[str],
) -> str:
    colmap_image_id = frame.get("colmap_im_id")
    if colmap_image_id is not None and int(colmap_image_id) in image_by_id:
        return image_by_id[int(colmap_image_id)]

    file_name = Path(str(frame.get("file_path", ""))).name
    if file_name in ordered_names:
        return file_name

    file_stem = Path(file_name).stem
    for candidate in ordered_names:
        if Path(candidate).stem == file_stem:
            return candidate

    if frame_index < len(ordered_names):
        return ordered_names[frame_index]

    raise KeyError(f"Could not resolve source image for frame {frame_index}: {frame}")


def materialize_nerfstudio_training_masks(
    *,
    enabled: bool,
    converted_dir: Path,
    transforms_path: Path,
    source_mask_dir: Path,
    colmap_images_path: Path,
    config: Optional[SemanticSkyMaskConfig] = None,
) -> SemanticSkyMaskSummary:
    with open(transforms_path, "r", encoding="utf-8") as f:
        transforms = json.load(f)

    if not enabled:
        return _build_summary(
            enabled=False,
            config=SemanticSkyMaskConfig(enabled=False),
            model_labels=[],
            mask_mode="disabled",
            mask_output_dir=None,
            frame_stats=[],
        )

    image_by_id, ordered_names = parse_colmap_images(colmap_images_path)
    masks_dir = converted_dir / "masks"
    masks_dir.mkdir(parents=True, exist_ok=True)

    frame_stats: list[FrameMaskStats] = []
    for frame_index, frame in enumerate(transforms.get("frames", [])):
        source_name = _resolve_source_image_name(frame, frame_index, image_by_id, ordered_names)
        source_stem = Path(source_name).stem
        source_mask_path = source_mask_dir / f"{source_stem}.png"
        if not source_mask_path.exists():
            raise FileNotFoundError(f"Expected semantic sky mask for {source_name} at {source_mask_path}")

        converted_image_path = converted_dir / Path(str(frame["file_path"]))
        if not converted_image_path.exists():
            raise FileNotFoundError(f"Converted image missing for frame {frame_index}: {converted_image_path}")

        sky_mask = np.asarray(Image.open(source_mask_path).convert("L"), dtype=np.uint8) > 0
        with Image.open(converted_image_path) as converted_image:
            target_size = converted_image.size
        if target_size != (sky_mask.shape[1], sky_mask.shape[0]):
            resized_mask = Image.fromarray((sky_mask.astype(np.uint8) * 255), mode="L").resize(
                target_size,
                resample=Image.Resampling.NEAREST,
            )
            sky_mask = np.asarray(resized_mask, dtype=np.uint8) > 0

        keep_mask = build_training_keep_mask(sky_mask)
        keep_mask_path = masks_dir / f"{source_stem}.png"
        Image.fromarray(keep_mask, mode="L").save(keep_mask_path)

        frame["mask_path"] = f"masks/{keep_mask_path.name}"
        frame_stats.append(_mask_stats(source_name, sky_mask))

    with open(transforms_path, "w", encoding="utf-8") as f:
        json.dump(transforms, f, indent=2)

    summary = _build_summary(
        enabled=True,
        config=config or SemanticSkyMaskConfig(enabled=True),
        model_labels=["sky"],
        mask_mode="nerfstudio_keep_mask",
        mask_output_dir=masks_dir,
        frame_stats=frame_stats,
    )
    (converted_dir / "semantic_sky_training_mask_summary.json").write_text(
        json.dumps(summary.to_dict(), indent=2),
        encoding="utf-8",
    )
    return summary


def write_diagnostic_overlays(
    *,
    images_dir: Path,
    sky_mask_dir: Path,
    output_dir: Path,
    sample_count: int = 24,
    config: Optional[SemanticSkyMaskConfig] = None,
) -> SemanticSkyMaskSummary:
    image_paths = _list_images(images_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    overlays_dir = output_dir / "overlays"
    overlays_dir.mkdir(parents=True, exist_ok=True)

    if not image_paths:
        raise FileNotFoundError(f"No images found in {images_dir}")

    if sample_count <= 0:
        sample_indices: list[int] = []
    elif len(image_paths) <= sample_count:
        sample_indices = list(range(len(image_paths)))
    else:
        sample_indices = sorted({int(round(index)) for index in np.linspace(0, len(image_paths) - 1, sample_count)})

    frame_stats: list[FrameMaskStats] = []
    for image_path in image_paths:
        sky_mask_path = sky_mask_dir / f"{image_path.stem}.png"
        if not sky_mask_path.exists():
            raise FileNotFoundError(f"Missing diagnostic mask for {image_path.name}: {sky_mask_path}")
        sky_mask = np.asarray(Image.open(sky_mask_path).convert("L"), dtype=np.uint8) > 0
        frame_stats.append(_mask_stats(image_path.name, sky_mask))

    for index in sample_indices:
        image_path = image_paths[index]
        image = np.asarray(Image.open(image_path).convert("RGB"), dtype=np.uint8)
        sky_mask = np.asarray(Image.open(sky_mask_dir / f"{image_path.stem}.png").convert("L"), dtype=np.uint8) > 0

        overlay = image.copy()
        overlay[sky_mask] = (
            0.35 * overlay[sky_mask] + 0.65 * np.array([90, 180, 255], dtype=np.float32)
        ).astype(np.uint8)
        Image.fromarray(overlay, mode="RGB").save(overlays_dir / f"{image_path.stem}.jpg", quality=92)

    summary = _build_summary(
        enabled=True,
        config=config or SemanticSkyMaskConfig(enabled=True),
        model_labels=["sky"],
        mask_mode="diagnostic_overlay",
        mask_output_dir=overlays_dir,
        frame_stats=frame_stats,
        sampled_overlay_count=len(sample_indices),
    )
    (output_dir / "semantic_sky_diagnostics.json").write_text(
        json.dumps(summary.to_dict(), indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate semantic sky mask diagnostics")
    parser.add_argument("--images-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--model-id",
        type=str,
        default="nvidia/segformer-b0-finetuned-ade-512-512",
    )
    parser.add_argument("--confidence-threshold", type=float, default=0.55)
    parser.add_argument("--min-component-area", type=float, default=0.002)
    parser.add_argument("--fill-hole-area", type=float, default=0.001)
    parser.add_argument(
        "--keep-top-connected-only",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--sample-overlays", type=int, default=24)
    parser.add_argument("--device", type=str, default="cpu")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    config = SemanticSkyMaskConfig(
        enabled=True,
        model_id=args.model_id,
        confidence_threshold=args.confidence_threshold,
        min_component_area=args.min_component_area,
        fill_hole_area=args.fill_hole_area,
        keep_top_connected_only=args.keep_top_connected_only,
        inference_device=args.device,
    )

    sky_mask_dir = args.output_dir / "sky_masks"
    summary = generate_semantic_sky_masks(args.images_dir, sky_mask_dir, config)
    diagnostics = write_diagnostic_overlays(
        images_dir=args.images_dir,
        sky_mask_dir=sky_mask_dir,
        output_dir=args.output_dir,
        sample_count=args.sample_overlays,
        config=config,
    )
    LOGGER.info("✅ Semantic sky diagnostics complete")
    LOGGER.info(json.dumps({"mask_summary": summary.to_dict(), "diagnostics": diagnostics.to_dict()}, indent=2))


if __name__ == "__main__":
    main()
