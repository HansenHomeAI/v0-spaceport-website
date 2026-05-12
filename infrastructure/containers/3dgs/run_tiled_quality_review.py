#!/usr/bin/env python3
"""
Render a fixed merged-model review bundle for tiled 3DGS outputs.
"""

from __future__ import annotations

import json
import logging
import math
import os
import shutil
import tarfile
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from plyfile import PlyData
from skimage.metrics import structural_similarity

try:
    import lpips
except ImportError:  # pragma: no cover - exercised inside the container image
    lpips = None

from gsplat import rasterization

from geometry_review import REVIEW_BUCKETS, build_review_comparison
from sky_quality import compute_sky_image_metrics
from tile_pipeline import (
    normalize_image_name,
    ordered_unique,
    resolve_tiled_input_manifests,
    select_pipeline_review_image_names_by_bucket,
    subset_tile_manifest,
)
from train_nerfstudio_production import NerfStudioTrainer, prepare_colmap_subset_for_image_names


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CONFIG_PATH = Path("/opt/ml/code/nerfstudio_config.yaml")
DEFAULT_BUCKET_ORDER = list(REVIEW_BUCKETS)


@dataclass(frozen=True)
class RenderSettings:
    render_scale: float = 1.0
    max_gaussians_per_view: int = 0
    cull_margin: float = 0.25
    min_gaussians_on_oom: int = 75_000


def parse_float_env(name: str, default: float, *, minimum: float | None = None, maximum: float | None = None) -> float:
    raw_value = os.environ.get(name, "").strip()
    value = default if not raw_value else float(raw_value)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def parse_int_env(name: str, default: int, *, minimum: int | None = None) -> int:
    raw_value = os.environ.get(name, "").strip()
    value = default if not raw_value else int(raw_value)
    if minimum is not None:
        value = max(minimum, value)
    return value


def load_render_settings_from_env() -> RenderSettings:
    return RenderSettings(
        render_scale=parse_float_env("QUALITY_REVIEW_RENDER_SCALE", 1.0, minimum=0.05, maximum=1.0),
        max_gaussians_per_view=parse_int_env("QUALITY_REVIEW_MAX_GAUSSIANS_PER_VIEW", 0, minimum=0),
        cull_margin=parse_float_env("QUALITY_REVIEW_CULL_MARGIN", 0.25, minimum=0.0, maximum=2.0),
        min_gaussians_on_oom=parse_int_env("QUALITY_REVIEW_MIN_GAUSSIANS_ON_OOM", 75_000, minimum=1),
    )


def find_model_artifact(model_input_dir: Path) -> Path:
    if model_input_dir.is_file():
        return model_input_dir
    candidates = sorted(model_input_dir.rglob("model.tar.gz"))
    if not candidates:
        raise FileNotFoundError(f"No model.tar.gz found under {model_input_dir}")
    return candidates[0]


def extract_model_artifact(model_tarball: Path, extract_dir: Path) -> Path:
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(model_tarball, "r:gz") as tar:
        for member in tar.getmembers():
            member_path = Path(member.name)
            if member_path.is_absolute() or ".." in member_path.parts or member.issym() or member.islnk():
                raise RuntimeError(f"Refusing unsafe tar member: {member.name}")
        tar.extractall(extract_dir)
    return extract_dir


def load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def prepare_review_input_dir(source_dir: Path, target_dir: Path) -> Path:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    images_dir = source_dir / "images"
    if images_dir.exists():
        os.symlink(images_dir, target_dir / "images")

    sparse_dir = source_dir / "sparse"
    if sparse_dir.exists():
        shutil.copytree(sparse_dir, target_dir / "sparse")

    for file_name in (
        "3dgs_tile_manifest.json",
        "3dgs_view_buckets.json",
        "chunk_planner_manifest.json",
        "sfm_metadata.json",
        "transforms.json",
        "transforms.full.json",
        "colmap_image_name_map.json",
    ):
        source_path = source_dir / file_name
        if source_path.exists():
            shutil.copy2(source_path, target_dir / file_name)
    return target_dir


def resolve_selected_tile_ids(
    extracted_model_dir: Path,
    requested_tile_ids: Sequence[str],
) -> list[str]:
    if requested_tile_ids:
        return [tile_id for tile_id in ordered_unique(requested_tile_ids) if tile_id]

    for candidate_name in ("training_metadata.json", "tiled_pipeline_summary.json"):
        candidate_path = extracted_model_dir / candidate_name
        if not candidate_path.exists():
            continue
        payload = load_json(candidate_path)
        selected = payload.get("selected_tile_ids")
        if isinstance(selected, list) and selected:
            return [str(tile_id) for tile_id in selected if str(tile_id).strip()]

    return [str(tile.get("tile_id")) for tile in tile_manifest.get("tiles", []) if tile.get("tile_id")]


def review_images_for_preconversion(
    frozen_review_camera_manifest_path: Path | None,
    *,
    max_images_per_bucket: int,
    review_camera_set: str,
) -> list[str]:
    if frozen_review_camera_manifest_path is None or not frozen_review_camera_manifest_path.exists():
        return []
    review_images_by_bucket = load_frozen_review_images_by_bucket(
        frozen_review_camera_manifest_path,
        max_images_per_bucket=max_images_per_bucket,
        camera_set=review_camera_set,
    )
    selected: list[str] = []
    for bucket_key, _bucket_label in DEFAULT_BUCKET_ORDER:
        selected.extend(review_images_by_bucket.get(bucket_key, []))
    return ordered_unique(selected)


def prepare_review_preconversion_input_dir(
    review_input_dir: Path,
    temp_dir: Path,
    selected_image_names: Sequence[str],
) -> tuple[Path, dict[str, Any]]:
    if not selected_image_names:
        return review_input_dir, {
            "enabled": False,
            "reason": "no_frozen_review_preconversion_selection",
        }

    subset_input_dir = temp_dir / "review_preconversion_selected_input"
    summary = prepare_colmap_subset_for_image_names(
        review_input_dir,
        subset_input_dir,
        selected_image_names,
    )
    if not summary.get("enabled"):
        logger.warning("⚠️ Review pre-conversion COLMAP subsetting skipped: %s", summary)
        return review_input_dir, summary
    if int(summary.get("missing_image_count", 0) or 0) > 0:
        logger.error("❌ Review pre-conversion subset has missing selected images: %s", summary)
        raise RuntimeError("Review pre-conversion COLMAP subset is missing selected images")
    logger.info("🧩 Review pre-conversion COLMAP subset enabled:")
    logger.info(
        "   Images: %s selected from %s source records; sparse points retained: %s",
        summary.get("selected_image_count"),
        summary.get("source_image_count"),
        summary.get("retained_sparse_point_count"),
    )
    logger.info("   Subset input: %s", summary.get("subset_input_dir"))
    return subset_input_dir, summary


def prepare_converted_dataset(
    colmap_input_dir: Path,
    temp_dir: Path,
    *,
    frozen_review_camera_manifest_path: Path | None = None,
    max_images_per_bucket: int = 4,
    review_camera_set: str = "auto",
) -> tuple[NerfStudioTrainer, Path, Path, dict[str, Any]]:
    review_input_dir = prepare_review_input_dir(colmap_input_dir, temp_dir / "source_input")
    preconversion_names = review_images_for_preconversion(
        frozen_review_camera_manifest_path,
        max_images_per_bucket=max_images_per_bucket,
        review_camera_set=review_camera_set,
    )
    conversion_input_dir, preconversion_summary = prepare_review_preconversion_input_dir(
        review_input_dir,
        temp_dir,
        preconversion_names,
    )
    trainer = NerfStudioTrainer(str(CONFIG_PATH))
    trainer.input_dir = conversion_input_dir
    trainer.output_dir = temp_dir / "trainer_output"
    trainer.temp_dir = temp_dir / "trainer_work"
    trainer.output_dir.mkdir(parents=True, exist_ok=True)
    trainer.temp_dir.mkdir(parents=True, exist_ok=True)
    if not trainer.validate_input_data():
        raise RuntimeError("COLMAP validation/conversion failed for tiled quality review")
    converted_dir = trainer.input_dir
    return trainer, review_input_dir, converted_dir, preconversion_summary


def load_frozen_review_images_by_bucket(
    camera_manifest_path: Path,
    *,
    max_images_per_bucket: int,
    camera_set: str,
) -> dict[str, list[str]]:
    payload = load_json(camera_manifest_path)
    requested_set = camera_set.strip().lower().replace("_", "-")
    if requested_set.startswith("frozen-"):
        requested_set = "auto"
    if requested_set in {"", "auto"}:
        requested_set = "smoke" if max_images_per_bucket <= 4 else "buckets"
    if requested_set in {"full", "promotion", "bucket", "buckets"}:
        set_key = "buckets"
    elif requested_set == "smoke":
        set_key = "smoke_buckets" if "smoke_buckets" in payload else "buckets"
    else:
        raise ValueError(f"Unknown QUALITY_REVIEW_CAMERA_SET={camera_set!r}")

    selected_payload = payload.get(set_key) or {}
    frozen: dict[str, list[str]] = {}
    for bucket_key, bucket_label in DEFAULT_BUCKET_ORDER:
        names = selected_payload.get(bucket_label, selected_payload.get(bucket_key, []))
        frozen[bucket_key] = ordered_unique([str(name) for name in names])[:max_images_per_bucket]
    return frozen


def resolve_optional_input_path(path_value: str, *, base_dirs: Sequence[Path]) -> Path | None:
    cleaned = path_value.strip()
    if not cleaned:
        return None
    candidate = Path(cleaned)
    if candidate.exists():
        return candidate
    for base_dir in base_dirs:
        base_candidate = base_dir / cleaned
        if base_candidate.exists():
            return base_candidate
    return candidate


def resolve_review_manifest_inputs(
    *,
    trainer: NerfStudioTrainer,
    review_input_dir: Path,
    selected_tile_ids: Sequence[str],
    max_images_per_bucket: int,
    frozen_review_camera_manifest_path: Path | None = None,
    review_camera_set: str = "auto",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, list[str]]]:
    tile_manifest_source = review_input_dir / "3dgs_tile_manifest.json"
    view_bucket_source = review_input_dir / "3dgs_view_buckets.json"
    chunk_planner_source = review_input_dir / "chunk_planner_manifest.json"
    sfm_metadata_source = review_input_dir / "sfm_metadata.json"

    tile_manifest_payload = load_json(tile_manifest_source) if tile_manifest_source.exists() else None
    view_bucket_payload = load_json(view_bucket_source) if view_bucket_source.exists() else None
    chunk_planner_payload = load_json(chunk_planner_source) if chunk_planner_source.exists() else None
    sfm_metadata_payload = load_json(sfm_metadata_source) if sfm_metadata_source.exists() else None
    transforms_payload = load_json(trainer.input_dir / "transforms.json")
    image_name_map_path = trainer.input_dir / "colmap_image_name_map.json"
    image_name_map_payload = load_json(image_name_map_path) if image_name_map_path.exists() else None

    tile_manifest, view_buckets, manifest_resolution = resolve_tiled_input_manifests(
        tile_manifest_payload=tile_manifest_payload,
        view_bucket_payload=view_bucket_payload,
        chunk_planner_manifest=chunk_planner_payload,
        sfm_metadata=sfm_metadata_payload,
        colmap_sparse_dir=review_input_dir / "sparse" / "0",
        transforms_payload=transforms_payload,
        image_name_map_payload=image_name_map_payload,
    )
    selected_subset = subset_tile_manifest(tile_manifest, selected_tile_ids=selected_tile_ids)
    review_images_by_bucket = select_pipeline_review_image_names_by_bucket(
        selected_subset,
        view_buckets,
        selected_tile_ids=selected_tile_ids,
        max_images_per_bucket=max_images_per_bucket,
    )
    if frozen_review_camera_manifest_path is not None and frozen_review_camera_manifest_path.exists():
        review_images_by_bucket = load_frozen_review_images_by_bucket(
            frozen_review_camera_manifest_path,
            max_images_per_bucket=max_images_per_bucket,
            camera_set=review_camera_set,
        )
    return selected_subset, view_buckets, manifest_resolution, review_images_by_bucket


def build_frame_index(converted_input_dir: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    transforms = load_json(converted_input_dir / "transforms.json")
    image_name_map_path = converted_input_dir / "colmap_image_name_map.json"
    image_name_map = load_json(image_name_map_path) if image_name_map_path.exists() else {}
    by_converted_name = image_name_map.get("by_converted_name", {}) or {}
    by_original_name = image_name_map.get("by_original_image_name", {}) or {}

    frame_index: dict[str, dict[str, Any]] = {}
    for frame in transforms.get("frames", []):
        file_path = str(frame.get("file_path", ""))
        converted_name = normalize_image_name(file_path)
        aliases = {converted_name}
        mapped_original = by_converted_name.get(converted_name, {}).get("original_image_name")
        if mapped_original:
            aliases.add(normalize_image_name(str(mapped_original)))
        original_image_name = frame.get("original_image_name")
        if original_image_name:
            aliases.add(normalize_image_name(str(original_image_name)))

        frame_record = {
            "frame": frame,
            "file_path": file_path,
            "converted_name": converted_name,
            "original_image_name": normalize_image_name(str(mapped_original or original_image_name or converted_name)),
        }
        original_entry = by_original_name.get(frame_record["original_image_name"])
        if isinstance(original_entry, Mapping):
            frame_record["converted_file_path"] = str(
                original_entry.get("converted_file_path") or file_path
            )
        for alias in aliases:
            frame_index.setdefault(alias, frame_record)
    return transforms, frame_index


def frame_intrinsics(
    frame: Mapping[str, Any],
    transforms: Mapping[str, Any],
    *,
    render_scale: float = 1.0,
) -> tuple[float, float, float, float, int, int]:
    width = int(frame.get("w", transforms.get("w")))
    height = int(frame.get("h", transforms.get("h")))
    fx = float(frame.get("fl_x", transforms.get("fl_x")))
    fy = float(frame.get("fl_y", transforms.get("fl_y")))
    cx = float(frame.get("cx", transforms.get("cx", width / 2.0)))
    cy = float(frame.get("cy", transforms.get("cy", height / 2.0)))
    if render_scale <= 0:
        raise ValueError(f"render_scale must be positive, got {render_scale}")
    if render_scale == 1.0:
        return fx, fy, cx, cy, width, height
    scaled_width = max(1, int(round(width * render_scale)))
    scaled_height = max(1, int(round(height * render_scale)))
    scale_x = scaled_width / float(width)
    scale_y = scaled_height / float(height)
    return fx * scale_x, fy * scale_y, cx * scale_x, cy * scale_y, scaled_width, scaled_height


def load_image_tensor(image_path: Path) -> np.ndarray:
    image = Image.open(image_path).convert("RGB")
    return np.asarray(image, dtype=np.float32) / 255.0


def resize_image_array(image: np.ndarray, *, width: int, height: int) -> np.ndarray:
    if image.shape[1] == width and image.shape[0] == height:
        return image
    pil_image = Image.fromarray(np.clip(image * 255.0, 0, 255).astype(np.uint8), mode="RGB")
    resized = pil_image.resize((width, height), Image.Resampling.BILINEAR)
    return np.asarray(resized, dtype=np.float32) / 255.0


def save_rgb_image(image: np.ndarray, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(image * 255.0, 0, 255).astype(np.uint8), mode="RGB").save(output_path)
    return str(output_path)


def build_difference_heatmap(reference: np.ndarray, prediction: np.ndarray) -> np.ndarray:
    reference = np.clip(reference.astype(np.float32), 0.0, 1.0)
    prediction = np.clip(prediction.astype(np.float32), 0.0, 1.0)
    if reference.shape != prediction.shape:
        raise ValueError(f"Heatmap inputs must share shape, got {reference.shape} and {prediction.shape}")
    error = np.mean(np.abs(prediction - reference), axis=-1)
    scaled = np.clip(error * 4.0, 0.0, 1.0)
    heatmap = np.zeros((*scaled.shape, 3), dtype=np.float32)
    heatmap[..., 0] = np.clip(scaled * 1.8, 0.0, 1.0)
    heatmap[..., 1] = np.clip((scaled - 0.20) * 2.0, 0.0, 1.0)
    heatmap[..., 2] = np.clip(1.0 - (scaled * 1.6), 0.0, 1.0) * (scaled > 0.001)
    return heatmap


def difference_summary_stats(reference: np.ndarray, prediction: np.ndarray) -> dict[str, float]:
    reference = np.clip(reference.astype(np.float32), 0.0, 1.0)
    prediction = np.clip(prediction.astype(np.float32), 0.0, 1.0)
    if reference.shape != prediction.shape:
        raise ValueError(f"Difference inputs must share shape, got {reference.shape} and {prediction.shape}")
    error = np.mean(np.abs(prediction - reference), axis=-1)
    return {
        "mean_abs_rgb_error": float(np.mean(error)),
        "p95_abs_rgb_error": float(np.percentile(error, 95)),
        "p99_abs_rgb_error": float(np.percentile(error, 99)),
        "max_abs_rgb_error": float(np.max(error)),
    }


def _array_to_pil_rgb(image: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(image * 255.0, 0, 255).astype(np.uint8), mode="RGB")


def build_visual_qa_panel(
    *,
    reference: np.ndarray,
    merged: np.ndarray,
    merged_no_background: np.ndarray,
    diff_heatmap: np.ndarray,
    output_path: Path,
) -> str:
    labels = ["reference", "merged", "no_background", "abs_diff_x4"]
    images = [
        _array_to_pil_rgb(reference),
        _array_to_pil_rgb(merged),
        _array_to_pil_rgb(merged_no_background),
        _array_to_pil_rgb(diff_heatmap),
    ]
    label_height = 28
    gap = 6
    width = sum(image.width for image in images) + (gap * (len(images) - 1))
    height = max(image.height for image in images) + label_height
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.load_default()
    except Exception:  # pragma: no cover - visual label fallback only
        font = None

    x = 0
    for label, image in zip(labels, images):
        draw.text((x + 4, 7), label, fill=(0, 0, 0), font=font)
        canvas.paste(image, (x, label_height))
        x += image.width + gap

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
    return str(output_path)


def load_gaussian_model(ply_path: Path, device: torch.device) -> dict[str, Any]:
    ply = PlyData.read(str(ply_path))
    vertex = ply["vertex"].data
    if len(vertex) == 0:
        raise RuntimeError(f"PLY contained zero gaussians: {ply_path}")

    positions = torch.from_numpy(
        np.stack(
            [
                np.asarray(vertex["x"], dtype=np.float32),
                np.asarray(vertex["y"], dtype=np.float32),
                np.asarray(vertex["z"], dtype=np.float32),
            ],
            axis=1,
        )
    ).to(device)
    raw_opacities = torch.from_numpy(np.asarray(vertex["opacity"], dtype=np.float32)).to(device)
    raw_scales = torch.from_numpy(
        np.stack(
            [
                np.asarray(vertex["scale_0"], dtype=np.float32),
                np.asarray(vertex["scale_1"], dtype=np.float32),
                np.asarray(vertex["scale_2"], dtype=np.float32),
            ],
            axis=1,
        )
    ).to(device)
    raw_quats = torch.from_numpy(
        np.stack(
            [
                np.asarray(vertex["rot_0"], dtype=np.float32),
                np.asarray(vertex["rot_1"], dtype=np.float32),
                np.asarray(vertex["rot_2"], dtype=np.float32),
                np.asarray(vertex["rot_3"], dtype=np.float32),
            ],
            axis=1,
        )
    ).to(device)
    scales_activation = "exp" if bool((raw_scales <= 0.0).any().detach().cpu().item()) else "identity"
    opacity_activation = (
        "sigmoid"
        if bool(((raw_opacities < 0.0) | (raw_opacities > 1.0)).any().detach().cpu().item())
        else "identity_clamped"
    )
    scales = torch.exp(raw_scales) if scales_activation == "exp" else raw_scales
    scales = torch.clamp(scales, min=1e-6, max=1e3)
    opacities = (
        torch.sigmoid(raw_opacities)
        if opacity_activation == "sigmoid"
        else torch.clamp(raw_opacities, min=0.0, max=1.0)
    )
    quats = torch.nn.functional.normalize(raw_quats, dim=1, eps=1e-8)
    sh_dc = torch.from_numpy(
        np.stack(
            [
                np.asarray(vertex["f_dc_0"], dtype=np.float32),
                np.asarray(vertex["f_dc_1"], dtype=np.float32),
                np.asarray(vertex["f_dc_2"], dtype=np.float32),
            ],
            axis=1,
        )
    ).to(device)[:, None, :]

    sh_rest_fields = sorted(
        (name for name in vertex.dtype.names if name.startswith("f_rest_")),
        key=lambda name: int(name.split("_")[-1]),
    )
    if sh_rest_fields:
        sh_rest_flat = np.stack([np.asarray(vertex[field], dtype=np.float32) for field in sh_rest_fields], axis=1)
        if sh_rest_flat.shape[1] % 3 != 0:
            raise RuntimeError(f"Unexpected SH payload width in {ply_path}: {sh_rest_flat.shape[1]}")
        sh_rest = torch.from_numpy(sh_rest_flat.reshape(len(vertex), -1, 3)).to(device)
    else:
        sh_rest = torch.zeros((len(vertex), 0, 3), dtype=torch.float32, device=device)

    colors = torch.cat([sh_dc, sh_rest], dim=1)
    sh_degree = max(0, int(math.sqrt(colors.shape[1]) - 1))
    while sh_degree > 0 and (sh_degree + 1) ** 2 > colors.shape[1]:
        sh_degree -= 1
    return {
        "ply_path": str(ply_path),
        "means": positions,
        "scales": scales,
        "quats": quats,
        "opacities": opacities,
        "colors": colors,
        "sh_degree": sh_degree,
        "gaussian_count": int(len(vertex)),
        "activation_metadata": {
            "scales": scales_activation,
            "opacities": opacity_activation,
            "quats": "normalized",
        },
    }


def normalize_render_color(render_colors: torch.Tensor) -> np.ndarray:
    if render_colors.dim() == 4:
        render_colors = render_colors.squeeze(0)
    if render_colors.dim() == 3 and render_colors.shape[0] == 3 and render_colors.shape[-1] != 3:
        render_colors = render_colors.permute(1, 2, 0)
    return render_colors[..., :3].detach().cpu().numpy().clip(0.0, 1.0)


def normalize_render_alpha(render_alphas: torch.Tensor, shape: tuple[int, int]) -> np.ndarray:
    if render_alphas.dim() == 4:
        render_alphas = render_alphas.squeeze(0)
    if render_alphas.dim() == 3 and render_alphas.shape[-1] == 1:
        render_alphas = render_alphas[..., 0]
    if render_alphas.dim() == 3 and render_alphas.shape[0] == 1:
        render_alphas = render_alphas.squeeze(0)
    alpha = render_alphas.detach().cpu().numpy().clip(0.0, 1.0)
    return alpha.reshape(shape)


def _opacity_score(opacities: torch.Tensor) -> torch.Tensor:
    if opacities.numel() == 0:
        return opacities
    if float(opacities.detach().max().cpu()) <= 1.0 and float(opacities.detach().min().cpu()) >= 0.0:
        return opacities
    return torch.sigmoid(opacities)


def _project_visible_gaussians(
    model: Mapping[str, Any],
    world_to_camera: np.ndarray,
    *,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
    width: int,
    height: int,
    cull_margin: float,
) -> tuple[torch.Tensor, torch.Tensor, int]:
    means = model["means"]
    viewmat = torch.from_numpy(world_to_camera).to(means.device, dtype=means.dtype)
    camera_means = means @ viewmat[:3, :3].T + viewmat[:3, 3]
    margin_x = float(width) * cull_margin
    margin_y = float(height) * cull_margin

    depth = camera_means[:, 2]
    valid_depth = depth > 1e-4
    safe_depth = torch.clamp(depth, min=1e-4)
    projected_x = (camera_means[:, 0] * float(fx) / safe_depth) + float(cx)
    projected_y = (camera_means[:, 1] * float(fy) / safe_depth) + float(cy)
    mask = (
        valid_depth
        & (projected_x >= -margin_x)
        & (projected_x <= float(width) + margin_x)
        & (projected_y >= -margin_y)
        & (projected_y <= float(height) + margin_y)
    )
    return mask, safe_depth, 1


def frame_world_to_camera(frame: Mapping[str, Any]) -> np.ndarray:
    c2w = np.asarray(frame["transform_matrix"], dtype=np.float32)
    world_to_camera_gl = np.linalg.inv(c2w).astype(np.float32)
    opengl_to_opencv = np.diag([1.0, -1.0, -1.0, 1.0]).astype(np.float32)
    return opengl_to_opencv @ world_to_camera_gl


def select_gaussians_for_view(
    model: Mapping[str, Any],
    world_to_camera: np.ndarray,
    *,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
    width: int,
    height: int,
    settings: RenderSettings,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_count = int(model["gaussian_count"])
    visible_mask, depths, projection_sign = _project_visible_gaussians(
        model,
        world_to_camera,
        fx=fx,
        fy=fy,
        cx=cx,
        cy=cy,
        width=width,
        height=height,
        cull_margin=settings.cull_margin,
    )
    visible_indices = torch.nonzero(visible_mask, as_tuple=False).flatten()
    visible_count = int(visible_indices.numel())
    max_gaussians = int(settings.max_gaussians_per_view or 0)
    selected_indices: torch.Tensor | None = visible_indices if visible_count < source_count else None
    selection_reason = "projected_visibility"

    if visible_count == 0:
        selection_reason = "opacity_topk_no_projected_support"
        selected_indices = None
        if max_gaussians and source_count > max_gaussians:
            scores = _opacity_score(model["opacities"])
            selected_indices = torch.topk(scores, k=max_gaussians, sorted=False).indices
    elif max_gaussians and visible_count > max_gaussians:
        selection_reason = "projected_support_topk"
        visible_depths = depths.index_select(0, visible_indices)
        visible_opacity = _opacity_score(model["opacities"].index_select(0, visible_indices))
        scores = visible_opacity / torch.sqrt(torch.clamp(visible_depths, min=1e-4))
        topk_local = torch.topk(scores, k=max_gaussians, sorted=False).indices
        selected_indices = visible_indices.index_select(0, topk_local)

    rendered_count = source_count if selected_indices is None else int(selected_indices.numel())
    if selected_indices is None:
        selected_model = dict(model)
    else:
        selected_model = {
            **model,
            "means": model["means"].index_select(0, selected_indices),
            "scales": model["scales"].index_select(0, selected_indices),
            "quats": model["quats"].index_select(0, selected_indices),
            "opacities": model["opacities"].index_select(0, selected_indices),
            "colors": model["colors"].index_select(0, selected_indices),
            "gaussian_count": rendered_count,
        }

    stats = {
        "source_gaussians": source_count,
        "visible_gaussians": visible_count,
        "rendered_gaussians": rendered_count,
        "limited": rendered_count < source_count,
        "projection_sign": projection_sign,
        "selection_reason": selection_reason,
        "render_scale": settings.render_scale,
        "width": width,
        "height": height,
    }
    return selected_model, stats


def render_gaussian_view(
    model: Mapping[str, Any],
    frame: Mapping[str, Any],
    transforms: Mapping[str, Any],
    device: torch.device,
    *,
    settings: RenderSettings,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    fx, fy, cx, cy, width, height = frame_intrinsics(frame, transforms, render_scale=settings.render_scale)
    world_to_camera = frame_world_to_camera(frame)
    K = torch.tensor([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], device=device, dtype=torch.float32)

    source_count = int(model["gaussian_count"])
    cap = settings.max_gaussians_per_view if settings.max_gaussians_per_view > 0 else source_count
    min_cap = min(max(1, settings.min_gaussians_on_oom), source_count)
    last_oom: RuntimeError | None = None
    while cap >= min_cap:
        effective_settings = replace(settings, max_gaussians_per_view=cap if cap < source_count else 0)
        selected_model, stats = select_gaussians_for_view(
            model,
            world_to_camera,
            fx=fx,
            fy=fy,
            cx=cx,
            cy=cy,
            width=width,
            height=height,
            settings=effective_settings,
        )
        try:
            with torch.no_grad():
                render_colors, render_alphas, _ = rasterization(
                    means=selected_model["means"],
                    scales=selected_model["scales"],
                    quats=selected_model["quats"],
                    opacities=selected_model["opacities"],
                    colors=selected_model["colors"],
                    viewmats=torch.from_numpy(world_to_camera).to(device).unsqueeze(0),
                    Ks=K.unsqueeze(0),
                    width=width,
                    height=height,
                    sh_degree=int(model["sh_degree"]),
                )
            return normalize_render_color(render_colors), normalize_render_alpha(render_alphas, (height, width)), stats
        except torch.cuda.OutOfMemoryError as exc:
            last_oom = exc
            torch.cuda.empty_cache()
            if cap <= min_cap:
                break
            cap = max(min_cap, cap // 2)
            logger.warning("CUDA OOM during review render; retrying with max_gaussians_per_view=%s", cap)
    assert last_oom is not None
    raise last_oom


def render_skybox_view(
    skybox_path: Path | None,
    frame: Mapping[str, Any],
    transforms: Mapping[str, Any],
    *,
    render_scale: float = 1.0,
) -> np.ndarray | None:
    if skybox_path is None or not skybox_path.exists():
        return None

    skybox = np.asarray(Image.open(skybox_path).convert("RGB"), dtype=np.float32) / 255.0
    fx, fy, cx, cy, width, height = frame_intrinsics(frame, transforms, render_scale=render_scale)
    c2w = np.asarray(frame["transform_matrix"], dtype=np.float32)
    rotation = c2w[:3, :3]

    xs = np.arange(width, dtype=np.float32)
    ys = np.arange(height, dtype=np.float32)
    grid_x, grid_y = np.meshgrid(xs, ys)
    dirs_camera = np.stack(
        (
            (grid_x - cx) / fx,
            -(grid_y - cy) / fy,
            -np.ones_like(grid_x, dtype=np.float32),
        ),
        axis=-1,
    )
    dirs_camera /= np.linalg.norm(dirs_camera, axis=-1, keepdims=True).clip(min=1e-8)
    dirs_world = dirs_camera @ rotation.T
    dirs_world /= np.linalg.norm(dirs_world, axis=-1, keepdims=True).clip(min=1e-8)

    theta = np.arctan2(dirs_world[..., 0], dirs_world[..., 2])
    phi = np.arcsin(np.clip(dirs_world[..., 1], -1.0, 1.0))
    u = (theta / (2.0 * math.pi)) + 0.5
    v = 0.5 - (phi / math.pi)

    sample_x = np.clip(np.round(u * (skybox.shape[1] - 1)).astype(np.int32), 0, skybox.shape[1] - 1)
    sample_y = np.clip(np.round(v * (skybox.shape[0] - 1)).astype(np.int32), 0, skybox.shape[0] - 1)
    return skybox[sample_y, sample_x]


def composite_render(foreground: np.ndarray, alpha: np.ndarray, background: np.ndarray | None) -> np.ndarray:
    if background is None:
        return foreground
    return np.clip(foreground + (background * (1.0 - alpha[..., None])), 0.0, 1.0)


def compute_metrics(
    prediction: np.ndarray,
    target: np.ndarray,
    *,
    lpips_model: Any,
    device: torch.device,
) -> dict[str, Any]:
    prediction = np.clip(prediction.astype(np.float32), 0.0, 1.0)
    target = np.clip(target.astype(np.float32), 0.0, 1.0)
    mse = float(np.mean(np.square(prediction - target)))
    psnr = float(-10.0 * math.log10(max(mse, 1e-8)))
    ssim = float(
        structural_similarity(
            target,
            prediction,
            channel_axis=-1,
            data_range=1.0,
        )
    )

    lpips_value = None
    if lpips_model is not None:
        prediction_tensor = torch.from_numpy(prediction).permute(2, 0, 1).unsqueeze(0).to(device)
        target_tensor = torch.from_numpy(target).permute(2, 0, 1).unsqueeze(0).to(device)
        with torch.no_grad():
            lpips_value = float(lpips_model((prediction_tensor * 2.0) - 1.0, (target_tensor * 2.0) - 1.0).item())

    return {
        "psnr": psnr,
        "ssim": ssim,
        "lpips": lpips_value,
    }


def median_or_none(values: Sequence[float | None]) -> float | None:
    filtered = [float(value) for value in values if value is not None]
    if not filtered:
        return None
    return float(median(filtered))


def image_summary_stats(image: np.ndarray) -> dict[str, float]:
    image = np.clip(image.astype(np.float32), 0.0, 1.0)
    luminance = (0.2126 * image[..., 0]) + (0.7152 * image[..., 1]) + (0.0722 * image[..., 2])
    return {
        "mean_luminance": float(np.mean(luminance)),
        "max_luminance": float(np.max(luminance)),
        "mean_rgb": float(np.mean(image)),
        "max_rgb": float(np.max(image)),
    }


def alpha_summary_stats(alpha: np.ndarray) -> dict[str, float]:
    alpha = np.clip(alpha.astype(np.float32), 0.0, 1.0)
    return {
        "mean": float(np.mean(alpha)),
        "max": float(np.max(alpha)),
        "coverage_gt_001": float(np.mean(alpha > 0.01)),
        "coverage_gt_005": float(np.mean(alpha > 0.05)),
    }


def summarize_render_sanity(review_views: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    checked_views = [view for view in review_views if isinstance(view.get("merged_alpha_stats"), Mapping)]
    blank_views: list[dict[str, Any]] = []
    for view in checked_views:
        alpha_stats = view.get("merged_alpha_stats", {})
        foreground_stats = view.get("merged_foreground_stats", {})
        alpha_max = float(alpha_stats.get("max", 0.0) or 0.0)
        alpha_coverage = float(alpha_stats.get("coverage_gt_001", 0.0) or 0.0)
        foreground_max = float(foreground_stats.get("max_rgb", 0.0) or 0.0)
        if alpha_max < 0.01 or alpha_coverage < 1e-5 or foreground_max < 1e-4:
            blank_views.append(
                {
                    "bucket": view.get("bucket"),
                    "image_name": view.get("image_name"),
                    "alpha_max": alpha_max,
                    "alpha_coverage_gt_001": alpha_coverage,
                    "foreground_max_rgb": foreground_max,
                }
            )
    status = "unknown" if not checked_views else ("blocked" if blank_views else "ok")
    return {
        "status": status,
        "checked_view_count": len(checked_views),
        "blank_view_count": len(blank_views),
        "blank_views": blank_views[:12],
    }


def build_review_manifest(
    *,
    model_tarball: Path,
    selected_tile_ids: Sequence[str],
    manifest_resolution: Mapping[str, Any],
    merge_report: Mapping[str, Any],
    review_images_by_bucket: Mapping[str, Sequence[str]],
    review_camera_manifest_path: Path,
    review_views: Sequence[Mapping[str, Any]],
    max_images_per_bucket: int,
    merged_background_present: bool,
    render_settings: RenderSettings,
) -> dict[str, Any]:
    bucket_medians: dict[str, dict[str, float | None]] = {}
    sky_bucket_medians: dict[str, dict[str, float | None]] = {}
    for _bucket_name, bucket_label_value in DEFAULT_BUCKET_ORDER:
        bucket_views = [view for view in review_views if view["bucket"] == bucket_label_value]
        bucket_medians[bucket_label_value] = {
            "psnr": median_or_none([view["metrics"]["psnr"] for view in bucket_views]),
            "ssim": median_or_none([view["metrics"]["ssim"] for view in bucket_views]),
            "lpips": median_or_none([view["metrics"]["lpips"] for view in bucket_views]),
        }
        sky_bucket_medians[bucket_label_value] = {
            "score": median_or_none([view["sky_metrics"]["score"] for view in bucket_views]),
            "luminance": median_or_none([view["sky_metrics"]["luminance"] for view in bucket_views]),
            "saturation": median_or_none([view["sky_metrics"]["saturation"] for view in bucket_views]),
            "blue_dominance": median_or_none([view["sky_metrics"]["blue_dominance"] for view in bucket_views]),
            "edge_density": median_or_none([view["sky_metrics"]["edge_density"] for view in bucket_views]),
        }

    expected_bucket_counts = {bucket_label_value: max_images_per_bucket for _, bucket_label_value in DEFAULT_BUCKET_ORDER}
    actual_bucket_counts = {
        bucket_label_value: len(review_images_by_bucket.get(bucket_name, []))
        for bucket_name, bucket_label_value in DEFAULT_BUCKET_ORDER
    }
    requested_bucket_counts = dict(expected_bucket_counts)
    review_buckets_complete = all(
        actual_bucket_counts.get(bucket_label_value, 0) >= expected_bucket_counts[bucket_label_value]
        for _, bucket_label_value in DEFAULT_BUCKET_ORDER
    )
    render_sanity = summarize_render_sanity(review_views)
    retain_all_tile_count = int(merge_report.get("retain_all_tile_count", 0) or 0)
    fallback_tile_count = int(merge_report.get("fallback_tile_count", 0) or 0)
    promotion_status = (
        "ready_for_comparison"
        if review_buckets_complete
        and retain_all_tile_count == 0
        and fallback_tile_count == 0
        and render_sanity["status"] != "blocked"
        else "blocked"
    )
    promotion_notes: list[str] = []
    if not review_buckets_complete:
        promotion_notes.append("review buckets did not produce the requested 4/4/4 coverage")
    if retain_all_tile_count > 0:
        promotion_notes.append("merge used retain_all fallback on at least one tile")
    if fallback_tile_count > 0:
        promotion_notes.append("merge used fallback on at least one tile")
    if render_sanity["status"] == "blocked":
        promotion_notes.append("merged gaussian foreground rendered blank for at least one review view")
    if merged_background_present:
        promotion_notes.append("merged review included promoted background skybox")
    else:
        promotion_notes.append("merged review had no promoted background skybox")

    return {
        "version": "1.0.0",
        "model_artifact": str(model_tarball),
        "selected_tile_ids": list(selected_tile_ids),
        "manifest_resolution": dict(manifest_resolution),
        "merge_report": dict(merge_report),
        "render_settings": {
            "render_scale": render_settings.render_scale,
            "max_gaussians_per_view": render_settings.max_gaussians_per_view,
            "cull_margin": render_settings.cull_margin,
            "min_gaussians_on_oom": render_settings.min_gaussians_on_oom,
        },
        "review_image_names_by_bucket": {
            bucket_name: list(image_names)
            for bucket_name, image_names in review_images_by_bucket.items()
        },
        "expected_bucket_counts": expected_bucket_counts,
        "requested_bucket_counts": requested_bucket_counts,
        "actual_bucket_counts": actual_bucket_counts,
        "review_camera_manifest": str(review_camera_manifest_path),
        "views": list(review_views),
        "bucket_medians": bucket_medians,
        "sky_bucket_medians": sky_bucket_medians,
        "render_sanity": render_sanity,
        "promotion_readiness": {
            "status": promotion_status,
            "review_buckets_complete": review_buckets_complete,
            "retain_all_tile_count": retain_all_tile_count,
            "fallback_tile_count": fallback_tile_count,
            "render_sanity": render_sanity,
            "manual_visual_review_required": True,
            "notes": promotion_notes,
        },
    }


def visual_asset_record(path_value: Any, *, output_dir: Path) -> dict[str, str] | None:
    if not path_value:
        return None
    path_text = str(path_value)
    record = {"path": path_text}
    try:
        record["artifact_relative_path"] = str(Path(path_text).relative_to(output_dir))
    except ValueError:
        record["artifact_relative_path"] = path_text
    return record


def build_visual_qa_manifest(
    *,
    model_tarball: Path,
    selected_tile_ids: Sequence[str],
    review_views: Sequence[Mapping[str, Any]],
    output_dir: Path,
    quality_review_manifest_path: Path,
) -> dict[str, Any]:
    bucket_counts: dict[str, int] = {}
    visual_views: list[dict[str, Any]] = []
    for view in review_views:
        bucket = str(view.get("bucket", ""))
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        assets = {
            "reference_image": visual_asset_record(view.get("reference_image"), output_dir=output_dir),
            "merged_render": visual_asset_record(view.get("merged_render"), output_dir=output_dir),
            "merged_no_background_render": visual_asset_record(
                view.get("merged_no_background_render"),
                output_dir=output_dir,
            ),
            "diff_heatmap": visual_asset_record(view.get("visual_diff_heatmap"), output_dir=output_dir),
            "side_by_side_panel": visual_asset_record(view.get("visual_side_by_side_panel"), output_dir=output_dir),
            "boundary_composite": visual_asset_record(view.get("boundary_composite"), output_dir=output_dir),
        }
        visual_views.append(
            {
                "bucket": bucket,
                "image_name": view.get("image_name"),
                "assets": {key: value for key, value in assets.items() if value is not None},
                "metrics": view.get("metrics", {}),
                "metrics_no_background": view.get("metrics_no_background", {}),
                "sky_metrics": view.get("sky_metrics", {}),
                "sky_metrics_no_background": view.get("sky_metrics_no_background", {}),
                "difference_stats": view.get("difference_stats", {}),
                "boundary_context_tile_ids": view.get("boundary_context_tile_ids", []),
                "review_focus": [
                    "geometry_alignment",
                    "boundary_seams",
                    "sky_horizon_continuity",
                    "floaters_or_overdensity",
                    "texture_blur_or_smearing",
                    "missing_geometry_or_holes",
                    "color_exposure_shift",
                ],
            }
        )

    panel_count = sum(1 for view in visual_views if view["assets"].get("side_by_side_panel"))
    return {
        "version": "1.0.0",
        "model_artifact": str(model_tarball),
        "selected_tile_ids": list(selected_tile_ids),
        "quality_review_manifest": visual_asset_record(quality_review_manifest_path, output_dir=output_dir),
        "view_count": len(visual_views),
        "panel_count": panel_count,
        "bucket_counts": bucket_counts,
        "difference_heatmap_scale": "mean_abs_rgb_error_x4_clipped",
        "ai_review_required": True,
        "review_instructions": [
            "Compare reference_image to merged_render for camera-by-camera usability, not only scalar metrics.",
            "Use merged_no_background_render to separate gaussian foreground defects from skybox/background defects.",
            "Use diff_heatmap and side_by_side_panel to identify localized regressions that bucket medians can hide.",
            "Treat severe geometry drift, boundary seams, sky discontinuity, holes, floaters, blur, or exposure shift as blocking even when PSNR/SSIM passes.",
        ],
        "ai_review_response_schema": {
            "type": "object",
            "required": [
                "overall_status",
                "blocking_defects",
                "per_view_findings",
                "confidence",
                "recommended_next_action",
            ],
            "properties": {
                "overall_status": ["pass", "conditional_pass", "block"],
                "blocking_defects": [
                    "geometry_alignment",
                    "boundary_seam",
                    "horizon_or_sky",
                    "missing_geometry",
                    "floaters_or_overdensity",
                    "texture_blur",
                    "color_or_exposure",
                    "viewer_packaging",
                ],
                "per_view_findings": "list of bucket/image findings with severity none|minor|major|blocking",
                "confidence": "0.0-1.0 reviewer confidence",
                "recommended_next_action": "one concise action before more paid compute",
            },
        },
        "views": visual_views,
    }


def bucket_label(bucket_name: str) -> str:
    return bucket_name.replace("_camera_ids", "")


def resolve_boundary_tile_ids(
    tile_manifest: Mapping[str, Any],
    selected_tile_ids: Sequence[str],
    image_name: str,
) -> list[str]:
    selected = set(selected_tile_ids)
    matching_tile_ids: list[str] = []
    for tile in tile_manifest.get("tiles", []):
        tile_id = str(tile.get("tile_id", "")).strip()
        if tile_id not in selected:
            continue
        candidate_names = ordered_unique(
            [
                *tile.get("base_camera_ids", []),
                *tile.get("border_camera_ids", []),
                *tile.get("context_camera_ids", []),
                *tile.get("image_names", []),
            ]
        )
        if image_name in candidate_names:
            matching_tile_ids.append(tile_id)

    if len(matching_tile_ids) >= 2:
        return matching_tile_ids[:2]

    if matching_tile_ids:
        tile_lookup = {
            str(tile.get("tile_id")): tile
            for tile in tile_manifest.get("tiles", [])
        }
        for neighbor_tile_id in ordered_unique(tile_lookup[matching_tile_ids[0]].get("neighbor_tile_ids", [])):
            if neighbor_tile_id in selected and neighbor_tile_id not in matching_tile_ids:
                matching_tile_ids.append(neighbor_tile_id)
            if len(matching_tile_ids) >= 2:
                break

    for tile_id in selected_tile_ids:
        if tile_id not in matching_tile_ids:
            matching_tile_ids.append(tile_id)
        if len(matching_tile_ids) >= 2:
            break
    return matching_tile_ids[:2]


def build_boundary_composite(images: Sequence[np.ndarray], output_path: Path) -> str:
    composite = np.concatenate([np.clip(image * 255.0, 0, 255).astype(np.uint8) for image in images], axis=1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(composite, mode="RGB").save(output_path)
    return str(output_path)


def main() -> None:
    model_input_dir = Path(os.environ.get("MODEL_INPUT_DIR", "/opt/ml/processing/input/model"))
    colmap_input_dir = Path(os.environ.get("COLMAP_INPUT_DIR", "/opt/ml/processing/input/colmap"))
    output_dir = Path(os.environ.get("OUTPUT_DIR", "/opt/ml/processing/output"))
    temp_dir = Path("/tmp/tiled_quality_review")
    requested_tile_ids = [
        tile_id.strip()
        for tile_id in os.environ.get("QUALITY_REVIEW_TILE_IDS", "").split(",")
        if tile_id.strip()
    ]
    max_images_per_bucket = max(1, int(os.environ.get("QUALITY_REVIEW_MAX_IMAGES_PER_BUCKET", "4") or 4))
    review_camera_set = os.environ.get("QUALITY_REVIEW_CAMERA_SET", "auto")
    frozen_review_camera_manifest_path = resolve_optional_input_path(
        os.environ.get("FROZEN_REVIEW_CAMERA_MANIFEST", "") or os.environ.get("QUALITY_REVIEW_CAMERA_MANIFEST", ""),
        base_dirs=[
            Path("/opt/ml/processing/input/review"),
            Path("/opt/ml/input/data/review-manifest"),
            Path("/opt/ml/input/data/camera"),
            model_input_dir,
            colmap_input_dir,
        ],
    )
    render_settings = load_render_settings_from_env()

    logger.info("🚀 Starting tiled 3DGS quality review")
    logger.info("📦 Model input: %s", model_input_dir)
    logger.info("📁 COLMAP input: %s", colmap_input_dir)
    logger.info("📁 Output dir: %s", output_dir)
    logger.info("🖼️ Render settings: %s", render_settings.__dict__)
    if frozen_review_camera_manifest_path is not None:
        logger.info("📷 Frozen camera manifest: %s", frozen_review_camera_manifest_path)

    selected_tile_ids: list[str] = []
    trainer: NerfStudioTrainer | None = None
    try:
        model_tarball = find_model_artifact(model_input_dir)
        extracted_model_dir = extract_model_artifact(model_tarball, temp_dir / "model")
        trainer, review_input_dir, converted_input_dir, preconversion_summary = prepare_converted_dataset(
            colmap_input_dir,
            temp_dir,
            frozen_review_camera_manifest_path=frozen_review_camera_manifest_path,
            max_images_per_bucket=max_images_per_bucket,
            review_camera_set=review_camera_set,
        )
        merged_ply_path = extracted_model_dir / "merged" / "merged_splat.ply"
        if not merged_ply_path.exists():
            raise FileNotFoundError(f"Merged tiled model was missing: {merged_ply_path}")
        merge_report_path = extracted_model_dir / "merged" / "merge_report.json"
        merge_report = load_json(merge_report_path) if merge_report_path.exists() else {}

        selected_tile_ids = resolve_selected_tile_ids(extracted_model_dir, requested_tile_ids)
        tile_manifest, _view_buckets, manifest_resolution, review_images_by_bucket = resolve_review_manifest_inputs(
            trainer=trainer,
            review_input_dir=review_input_dir,
            selected_tile_ids=selected_tile_ids,
            max_images_per_bucket=max_images_per_bucket,
            frozen_review_camera_manifest_path=frozen_review_camera_manifest_path,
            review_camera_set=review_camera_set,
        )
        if not selected_tile_ids:
            selected_tile_ids = [str(tile.get("tile_id")) for tile in tile_manifest.get("tiles", []) if tile.get("tile_id")]

        transforms, frame_index = build_frame_index(converted_input_dir)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        merged_model = load_gaussian_model(merged_ply_path, device)
        merged_background_path = extracted_model_dir / "merged" / "background_skybox.webp"

        lpips_model = None
        if lpips is not None:
            lpips_model = lpips.LPIPS(net="alex").to(device)
            lpips_model.eval()

        output_dir.mkdir(parents=True, exist_ok=True)
        review_root = output_dir / "quality_review"
        reference_root = review_root / "reference"
        merged_root = review_root / "merged"
        merged_no_background_root = review_root / "merged_no_background"
        diff_heatmap_root = review_root / "diff_heatmaps"
        visual_panel_root = review_root / "visual_panels"
        tiles_root = review_root / "tiles"
        composites_root = review_root / "boundary_composites"
        camera_manifest_entries: list[dict[str, Any]] = []
        review_views: list[dict[str, Any]] = []

        for bucket_name, bucket_label_value in DEFAULT_BUCKET_ORDER:
            for image_name in review_images_by_bucket.get(bucket_name, []):
                frame_record = frame_index.get(image_name)
                if frame_record is None:
                    logger.warning("Skipping review image with no converted frame mapping: %s", image_name)
                    continue

                frame = frame_record["frame"]
                reference_image_path = converted_input_dir / str(frame_record.get("converted_file_path") or frame_record["file_path"])
                if not reference_image_path.exists():
                    reference_image_path = converted_input_dir / str(frame_record["file_path"])
                reference_image_full = load_image_tensor(reference_image_path)
                _, _, _, _, render_width, render_height = frame_intrinsics(
                    frame,
                    transforms,
                    render_scale=render_settings.render_scale,
                )
                reference_image = resize_image_array(reference_image_full, width=render_width, height=render_height)
                reference_output_path = reference_root / bucket_label_value / Path(image_name).name
                saved_reference_path = save_rgb_image(reference_image, reference_output_path)

                merged_foreground, merged_alpha, merged_render_stats = render_gaussian_view(
                    merged_model,
                    frame,
                    transforms,
                    device,
                    settings=render_settings,
                )
                merged_background = render_skybox_view(
                    merged_background_path,
                    frame,
                    transforms,
                    render_scale=render_settings.render_scale,
                )
                merged_final = composite_render(merged_foreground, merged_alpha, merged_background)
                merged_render_path = merged_root / bucket_label_value / f"{Path(image_name).stem}.png"
                saved_merged_path = save_rgb_image(merged_final, merged_render_path)
                merged_no_background_path = merged_no_background_root / bucket_label_value / f"{Path(image_name).stem}.png"
                saved_merged_no_background_path = save_rgb_image(merged_foreground, merged_no_background_path)
                diff_heatmap = build_difference_heatmap(reference_image, merged_final)
                diff_heatmap_path = diff_heatmap_root / bucket_label_value / f"{Path(image_name).stem}.png"
                saved_diff_heatmap_path = save_rgb_image(diff_heatmap, diff_heatmap_path)
                visual_panel_path = visual_panel_root / bucket_label_value / f"{Path(image_name).stem}.png"
                saved_visual_panel_path = build_visual_qa_panel(
                    reference=reference_image,
                    merged=merged_final,
                    merged_no_background=merged_foreground,
                    diff_heatmap=diff_heatmap,
                    output_path=visual_panel_path,
                )

                metrics = compute_metrics(
                    merged_final,
                    reference_image,
                    lpips_model=lpips_model,
                    device=device,
                )
                metrics_no_background = compute_metrics(
                    merged_foreground,
                    reference_image,
                    lpips_model=lpips_model,
                    device=device,
                )
                sky_metrics = compute_sky_image_metrics((merged_final * 255.0).astype(np.uint8))
                sky_metrics_no_background = compute_sky_image_metrics((merged_foreground * 255.0).astype(np.uint8))

                view_entry: dict[str, Any] = {
                    "bucket": bucket_label_value,
                    "image_name": image_name,
                    "reference_image": saved_reference_path,
                    "merged_render": saved_merged_path,
                    "merged_no_background_render": saved_merged_no_background_path,
                    "visual_diff_heatmap": saved_diff_heatmap_path,
                    "visual_side_by_side_panel": saved_visual_panel_path,
                    "metrics": metrics,
                    "metrics_no_background": metrics_no_background,
                    "sky_metrics": sky_metrics,
                    "sky_metrics_no_background": sky_metrics_no_background,
                    "difference_stats": difference_summary_stats(reference_image, merged_final),
                    "merged_render_stats": merged_render_stats,
                    "merged_alpha_stats": alpha_summary_stats(merged_alpha),
                    "merged_foreground_stats": image_summary_stats(merged_foreground),
                    "merged_final_stats": image_summary_stats(merged_final),
                }

                boundary_tile_ids: list[str] = []
                if bucket_label_value == "boundary":
                    boundary_tile_ids = resolve_boundary_tile_ids(tile_manifest, selected_tile_ids, image_name)
                    boundary_images = [reference_image, merged_final]
                    tile_render_paths: list[str] = []
                    tile_render_stats_by_id: dict[str, Any] = {}
                    for tile_id in boundary_tile_ids:
                        tile_ply_path = extracted_model_dir / "tiles" / tile_id / "splat.ply"
                        if not tile_ply_path.exists():
                            continue
                        tile_model = load_gaussian_model(tile_ply_path, device)
                        tile_background_path = extracted_model_dir / "tiles" / tile_id / "background_skybox.webp"
                        tile_foreground, tile_alpha, tile_render_stats = render_gaussian_view(
                            tile_model,
                            frame,
                            transforms,
                            device,
                            settings=render_settings,
                        )
                        tile_background = render_skybox_view(
                            tile_background_path,
                            frame,
                            transforms,
                            render_scale=render_settings.render_scale,
                        )
                        tile_final = composite_render(tile_foreground, tile_alpha, tile_background)
                        tile_render_path = tiles_root / tile_id / bucket_label_value / f"{Path(image_name).stem}.png"
                        tile_render_paths.append(save_rgb_image(tile_final, tile_render_path))
                        tile_render_stats_by_id[tile_id] = tile_render_stats
                        boundary_images.append(tile_final)
                    composite_path = composites_root / f"{Path(image_name).stem}.png"
                    view_entry["boundary_context_tile_ids"] = boundary_tile_ids
                    view_entry["boundary_tile_renders"] = tile_render_paths
                    view_entry["boundary_tile_render_stats"] = tile_render_stats_by_id
                    view_entry["boundary_composite"] = build_boundary_composite(boundary_images, composite_path)

                camera_manifest_entries.append(
                    {
                        "bucket": bucket_label_value,
                        "image_name": image_name,
                        "frame_file_path": str(frame_record["file_path"]),
                        "boundary_context_tile_ids": boundary_tile_ids,
                    }
                )
                review_views.append(view_entry)

        camera_manifest = {
            "selected_tile_ids": selected_tile_ids,
            "review_image_names_by_bucket": review_images_by_bucket,
            "views": camera_manifest_entries,
        }
        review_camera_manifest_path = review_root / "review_camera_manifest.json"
        with open(review_camera_manifest_path, "w", encoding="utf-8") as handle:
            json.dump(camera_manifest, handle, indent=2)

        manifest = build_review_manifest(
            model_tarball=model_tarball,
            selected_tile_ids=selected_tile_ids,
            manifest_resolution=manifest_resolution,
            merge_report=merge_report,
            review_images_by_bucket=review_images_by_bucket,
            review_camera_manifest_path=review_camera_manifest_path,
            review_views=review_views,
            max_images_per_bucket=max_images_per_bucket,
            merged_background_present=merged_background_path.exists(),
            render_settings=render_settings,
        )
        manifest["preconversion_selection"] = preconversion_summary
        quality_review_manifest_path = output_dir / "quality_review_manifest.json"
        visual_qa_manifest = build_visual_qa_manifest(
            model_tarball=model_tarball,
            selected_tile_ids=selected_tile_ids,
            review_views=review_views,
            output_dir=output_dir,
            quality_review_manifest_path=quality_review_manifest_path,
        )
        manifest["visual_qa_manifest"] = {
            "path": str(output_dir / "visual_qa_manifest.json"),
            "view_count": visual_qa_manifest["view_count"],
            "panel_count": visual_qa_manifest["panel_count"],
            "ai_review_required": visual_qa_manifest["ai_review_required"],
        }
        with open(quality_review_manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)
        with open(output_dir / "visual_qa_manifest.json", "w", encoding="utf-8") as handle:
            json.dump(visual_qa_manifest, handle, indent=2)
        baseline_manifest_path = os.environ.get("BASELINE_REVIEW_MANIFEST", "").strip()
        if baseline_manifest_path:
            baseline_manifest = load_json(Path(baseline_manifest_path))
            comparison = build_review_comparison(
                baseline_manifest=baseline_manifest,
                candidate_manifest=manifest,
                baseline_artifact=baseline_manifest.get("model_artifact"),
                candidate_artifact=str(model_tarball),
                camera_manifest=camera_manifest,
            )
            with open(output_dir / "review_comparison.json", "w", encoding="utf-8") as handle:
                json.dump(comparison, handle, indent=2)
        logger.info("✅ Tiled quality review complete: %s", output_dir / "quality_review_manifest.json")
    finally:
        if selected_tile_ids:
            logger.info("Reviewed selected tile ids: %s", ",".join(selected_tile_ids))
        try:
            if trainer is not None:
                trainer.cleanup_temp_files()
        except Exception:  # pragma: no cover - cleanup only
            pass


if __name__ == "__main__":
    main()
