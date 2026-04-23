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
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from PIL import Image
from plyfile import PlyData
from skimage.metrics import structural_similarity

try:
    import lpips
except ImportError:  # pragma: no cover - exercised inside the container image
    lpips = None

from gsplat import rasterization

from sky_quality import compute_sky_image_metrics
from tile_pipeline import (
    normalize_image_name,
    ordered_unique,
    resolve_tiled_input_manifests,
    select_pipeline_review_image_names_by_bucket,
    subset_tile_manifest,
)
from train_nerfstudio_production import NerfStudioTrainer


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CONFIG_PATH = Path("/opt/ml/code/nerfstudio_config.yaml")
DEFAULT_BUCKET_ORDER = [
    ("near_detail_camera_ids", "near_detail"),
    ("boundary_camera_ids", "boundary"),
    ("horizon_camera_ids", "horizon"),
]
PROMOTION_THRESHOLDS = {
    "near_detail": {"psnr_drop": 1.0, "ssim_drop": 0.015, "lpips_rise": 0.035},
    "boundary": {"psnr_gain": 0.5, "ssim_gain": 0.01, "lpips_drop": 0.025},
    "horizon": {"psnr_drop": 0.75, "ssim_drop": 0.012, "lpips_rise": 0.03, "sky_score_drop_ratio": 0.10},
}
DEFAULT_RENDER_MAX_GAUSSIANS_PER_VIEW = 900_000
DEFAULT_RENDER_CULL_MARGIN = 0.50
DEFAULT_RENDER_MIN_GAUSSIANS_ON_OOM = 75_000


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)) or default)
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, str(default)) or default)
    except ValueError:
        return default
    if not math.isfinite(value):
        return default
    return value


def resolve_render_settings_from_env() -> dict[str, Any]:
    render_scale = max(0.05, min(1.0, env_float("QUALITY_REVIEW_RENDER_SCALE", 1.0)))
    max_gaussians = env_int(
        "QUALITY_REVIEW_MAX_GAUSSIANS_PER_VIEW",
        DEFAULT_RENDER_MAX_GAUSSIANS_PER_VIEW,
    )
    return {
        "render_scale": render_scale,
        "max_gaussians_per_view": max(1, max_gaussians),
        "cull_margin": max(0.0, env_float("QUALITY_REVIEW_CULL_MARGIN", DEFAULT_RENDER_CULL_MARGIN)),
        "min_gaussians_on_oom": max(1, env_int("QUALITY_REVIEW_MIN_GAUSSIANS_ON_OOM", DEFAULT_RENDER_MIN_GAUSSIANS_ON_OOM)),
    }


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


def prepare_converted_dataset(colmap_input_dir: Path, temp_dir: Path) -> tuple[NerfStudioTrainer, Path, Path]:
    review_input_dir = prepare_review_input_dir(colmap_input_dir, temp_dir / "source_input")
    trainer = NerfStudioTrainer(str(CONFIG_PATH))
    trainer.input_dir = review_input_dir
    trainer.output_dir = temp_dir / "trainer_output"
    trainer.temp_dir = temp_dir / "trainer_work"
    trainer.output_dir.mkdir(parents=True, exist_ok=True)
    trainer.temp_dir.mkdir(parents=True, exist_ok=True)
    if not trainer.validate_input_data():
        raise RuntimeError("COLMAP validation/conversion failed for tiled quality review")
    converted_dir = trainer.input_dir
    return trainer, review_input_dir, converted_dir


def resolve_review_manifest_inputs(
    *,
    trainer: NerfStudioTrainer,
    review_input_dir: Path,
    selected_tile_ids: Sequence[str],
    max_images_per_bucket: int,
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
    source_width = int(frame.get("w", transforms.get("w")))
    source_height = int(frame.get("h", transforms.get("h")))
    width = max(1, int(round(source_width * render_scale)))
    height = max(1, int(round(source_height * render_scale)))
    fx = float(frame.get("fl_x", transforms.get("fl_x"))) * render_scale
    fy = float(frame.get("fl_y", transforms.get("fl_y"))) * render_scale
    cx = float(frame.get("cx", transforms.get("cx", source_width / 2.0))) * render_scale
    cy = float(frame.get("cy", transforms.get("cy", source_height / 2.0))) * render_scale
    return fx, fy, cx, cy, width, height


def load_image_tensor(image_path: Path, *, size: tuple[int, int] | None = None) -> np.ndarray:
    image = Image.open(image_path).convert("RGB")
    if size is not None and image.size != size:
        resampling = getattr(Image, "Resampling", Image).LANCZOS
        image = image.resize(size, resampling)
    return np.asarray(image, dtype=np.float32) / 255.0


def save_rgb_image(image: np.ndarray, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(image * 255.0, 0, 255).astype(np.uint8), mode="RGB").save(output_path)
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
    raw_opacities = np.asarray(vertex["opacity"], dtype=np.float32)
    if float(np.nanmin(raw_opacities)) < 0.0 or float(np.nanmax(raw_opacities)) > 1.0:
        opacity_values = 1.0 / (1.0 + np.exp(-np.clip(raw_opacities, -20.0, 20.0)))
    else:
        opacity_values = np.clip(raw_opacities, 0.0, 1.0)
    opacities = torch.from_numpy(opacity_values.astype(np.float32)).to(device)

    raw_scales = np.stack(
        [
            np.asarray(vertex["scale_0"], dtype=np.float32),
            np.asarray(vertex["scale_1"], dtype=np.float32),
            np.asarray(vertex["scale_2"], dtype=np.float32),
        ],
        axis=1,
    )
    if float(np.nanmin(raw_scales)) < 0.0:
        scale_values = np.exp(np.clip(raw_scales, -20.0, 8.0))
    else:
        scale_values = np.clip(raw_scales, 1e-8, None)
    scales = torch.from_numpy(scale_values.astype(np.float32)).to(device)

    raw_quats = np.stack(
        [
            np.asarray(vertex["rot_0"], dtype=np.float32),
            np.asarray(vertex["rot_1"], dtype=np.float32),
            np.asarray(vertex["rot_2"], dtype=np.float32),
            np.asarray(vertex["rot_3"], dtype=np.float32),
        ],
        axis=1,
    )
    quat_norms = np.linalg.norm(raw_quats, axis=1, keepdims=True).clip(min=1e-8)
    quats = torch.from_numpy((raw_quats / quat_norms).astype(np.float32)).to(device)
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
    }


def _slice_gaussian_model(model: Mapping[str, Any], indices: torch.Tensor | None) -> dict[str, Any]:
    if indices is None:
        return dict(model)

    source_count = int(model.get("gaussian_count", 0) or 0)
    sliced: dict[str, Any] = {}
    for key, value in model.items():
        if isinstance(value, torch.Tensor) and value.dim() > 0 and value.shape[0] == source_count:
            sliced[key] = value.index_select(0, indices)
        else:
            sliced[key] = value
    sliced["gaussian_count"] = int(indices.numel())
    return sliced


def _view_projected_subset(
    model: Mapping[str, Any],
    frame: Mapping[str, Any],
    transforms: Mapping[str, Any],
    *,
    render_scale: float,
    max_gaussians_per_view: int | None,
    cull_margin: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_count = int(model.get("gaussian_count", 0) or 0)
    stats: dict[str, Any] = {
        "source_gaussians": source_count,
        "visible_gaussians": source_count,
        "rendered_gaussians": source_count,
        "limited": False,
        "projection_sign": None,
    }
    if source_count == 0 or max_gaussians_per_view is None or source_count <= max_gaussians_per_view:
        return dict(model), stats

    fx, fy, cx, cy, width, height = frame_intrinsics(frame, transforms, render_scale=render_scale)
    c2w = np.asarray(frame["transform_matrix"], dtype=np.float32)
    world_to_camera = torch.from_numpy(np.linalg.inv(c2w).astype(np.float32)).to(model["means"].device)

    with torch.no_grad():
        means = model["means"]
        camera_xyz = means @ world_to_camera[:3, :3].T + world_to_camera[:3, 3]
        best: tuple[int, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor] | None = None
        for sign in (-1, 1):
            depth = float(sign) * camera_xyz[:, 2]
            safe_depth = torch.clamp(depth, min=1e-6)
            u = (fx * (camera_xyz[:, 0] / safe_depth)) + cx
            v = (fy * (camera_xyz[:, 1] / safe_depth)) + cy
            mask = (
                (depth > 0.01)
                & (u >= (-cull_margin * width))
                & (u <= ((1.0 + cull_margin) * width))
                & (v >= (-cull_margin * height))
                & (v <= ((1.0 + cull_margin) * height))
            )
            if best is None or int(mask.sum().item()) > int(best[1].sum().item()):
                best = (sign, mask, depth, u, v)

        assert best is not None
        sign, visible_mask, depth, u, v = best
        visible_indices = torch.nonzero(visible_mask, as_tuple=False).flatten()
        if visible_indices.numel() == 0:
            opacity_score = torch.sigmoid(model["opacities"].float())
            selected_count = min(source_count, int(max_gaussians_per_view))
            selected_indices = torch.topk(opacity_score, k=selected_count, largest=True).indices
            stats.update(
                {
                    "visible_gaussians": 0,
                    "rendered_gaussians": int(selected_indices.numel()),
                    "limited": source_count > int(selected_indices.numel()),
                    "projection_sign": sign,
                    "selection_reason": "opacity_fallback_no_projected_support",
                }
            )
            return _slice_gaussian_model(model, torch.sort(selected_indices).values), stats

        stats["visible_gaussians"] = int(visible_indices.numel())
        if visible_indices.numel() <= max_gaussians_per_view:
            selected_indices = visible_indices
            stats["selection_reason"] = "projected_visibility"
        else:
            selected_count = int(max_gaussians_per_view)
            depth_visible = torch.clamp(depth.index_select(0, visible_indices), min=1e-3)
            opacity_visible = torch.sigmoid(model["opacities"].float().index_select(0, visible_indices))
            scale_max = torch.amax(model["scales"].float().index_select(0, visible_indices), dim=1)
            center_distance = torch.square((u.index_select(0, visible_indices) - cx) / max(width, 1))
            center_distance = center_distance + torch.square((v.index_select(0, visible_indices) - cy) / max(height, 1))
            median_depth = torch.median(depth_visible)
            depth_score = torch.clamp(median_depth / depth_visible, min=0.05, max=4.0)
            scale_penalty = torch.clamp(scale_max, min=-8.0, max=4.0)
            support_score = opacity_visible + (0.12 * depth_score) - (0.035 * scale_penalty) - (0.05 * center_distance)
            selected_relative = torch.topk(support_score, k=selected_count, largest=True).indices
            selected_indices = visible_indices.index_select(0, selected_relative)
            stats["selection_reason"] = "projected_support_topk"

        selected_indices = torch.sort(selected_indices).values
        stats.update(
            {
                "rendered_gaussians": int(selected_indices.numel()),
                "limited": source_count > int(selected_indices.numel()),
                "projection_sign": sign,
            }
        )
        return _slice_gaussian_model(model, selected_indices), stats


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


def render_gaussian_view(
    model: Mapping[str, Any],
    frame: Mapping[str, Any],
    transforms: Mapping[str, Any],
    device: torch.device,
    *,
    render_scale: float = 1.0,
    max_gaussians_per_view: int | None = None,
    cull_margin: float = DEFAULT_RENDER_CULL_MARGIN,
    min_gaussians_on_oom: int = DEFAULT_RENDER_MIN_GAUSSIANS_ON_OOM,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    fx, fy, cx, cy, width, height = frame_intrinsics(frame, transforms, render_scale=render_scale)
    c2w = np.asarray(frame["transform_matrix"], dtype=np.float32)
    world_to_camera = np.linalg.inv(c2w).astype(np.float32)
    K = torch.tensor([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], device=device, dtype=torch.float32)

    active_limit = max_gaussians_per_view
    retries: list[dict[str, Any]] = []
    while True:
        render_model, stats = _view_projected_subset(
            model,
            frame,
            transforms,
            render_scale=render_scale,
            max_gaussians_per_view=active_limit,
            cull_margin=cull_margin,
        )
        stats["render_scale"] = render_scale
        stats["width"] = width
        stats["height"] = height
        if retries:
            stats["oom_retries"] = retries
        try:
            with torch.no_grad():
                render_colors, render_alphas, _ = rasterization(
                    means=render_model["means"],
                    scales=render_model["scales"],
                    quats=render_model["quats"],
                    opacities=render_model["opacities"],
                    colors=render_model["colors"],
                    viewmats=torch.from_numpy(world_to_camera).to(device).unsqueeze(0),
                    Ks=K.unsqueeze(0),
                    width=width,
                    height=height,
                    sh_degree=int(render_model["sh_degree"]),
                )
            return normalize_render_color(render_colors), normalize_render_alpha(render_alphas, (height, width)), stats
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            current_count = int(stats.get("rendered_gaussians", render_model.get("gaussian_count", 0)) or 0)
            next_limit = max(int(min_gaussians_on_oom), max(1, current_count // 2))
            retries.append({"rendered_gaussians": current_count, "next_limit": next_limit})
            logger.warning(
                "Gaussian render OOM at %s gaussians for %sx%s; retrying with limit %s",
                current_count,
                width,
                height,
                next_limit,
            )
            if next_limit >= current_count:
                raise
            active_limit = next_limit


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
            (grid_y - cy) / fy,
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


def _as_float_or_none(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def _metric_delta(candidate: float | None, baseline: float | None) -> float | None:
    if candidate is None or baseline is None:
        return None
    return float(candidate - baseline)


def compare_review_manifests(
    *,
    baseline_manifest: Mapping[str, Any],
    candidate_manifest: Mapping[str, Any],
    thresholds: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    thresholds = thresholds or PROMOTION_THRESHOLDS
    baseline_medians = baseline_manifest.get("bucket_medians", {}) or {}
    candidate_medians = candidate_manifest.get("bucket_medians", {}) or {}
    baseline_sky = baseline_manifest.get("sky_bucket_medians", {}) or {}
    candidate_sky = candidate_manifest.get("sky_bucket_medians", {}) or {}
    deltas: dict[str, Any] = {}
    block_reasons: list[dict[str, Any]] = []

    for bucket_name in ("near_detail", "boundary", "horizon"):
        baseline_bucket = baseline_medians.get(bucket_name, {}) or {}
        candidate_bucket = candidate_medians.get(bucket_name, {}) or {}
        bucket_delta = {
            metric_name: _metric_delta(
                _as_float_or_none(candidate_bucket.get(metric_name)),
                _as_float_or_none(baseline_bucket.get(metric_name)),
            )
            for metric_name in ("psnr", "ssim", "lpips")
        }
        deltas[bucket_name] = {
            "baseline": dict(baseline_bucket),
            "candidate": dict(candidate_bucket),
            "delta": bucket_delta,
        }

    near_thresholds = thresholds["near_detail"]
    near_delta = deltas["near_detail"]["delta"]
    if near_delta["psnr"] is None or near_delta["ssim"] is None or near_delta["lpips"] is None:
        block_reasons.append({"code": "near_detail_metrics_missing", "bucket": "near_detail"})
    else:
        if near_delta["psnr"] < -float(near_thresholds["psnr_drop"]):
            block_reasons.append({"code": "near_detail_psnr_regression", "bucket": "near_detail", "delta": near_delta["psnr"]})
        if near_delta["ssim"] < -float(near_thresholds["ssim_drop"]):
            block_reasons.append({"code": "near_detail_ssim_regression", "bucket": "near_detail", "delta": near_delta["ssim"]})
        if near_delta["lpips"] > float(near_thresholds["lpips_rise"]):
            block_reasons.append({"code": "near_detail_lpips_regression", "bucket": "near_detail", "delta": near_delta["lpips"]})

    boundary_thresholds = thresholds["boundary"]
    boundary_delta = deltas["boundary"]["delta"]
    boundary_missing = boundary_delta["psnr"] is None or boundary_delta["ssim"] is None or boundary_delta["lpips"] is None
    if boundary_missing:
        block_reasons.append({"code": "boundary_metrics_missing", "bucket": "boundary"})
    else:
        boundary_improved = (
            boundary_delta["psnr"] >= float(boundary_thresholds["psnr_gain"])
            or boundary_delta["ssim"] >= float(boundary_thresholds["ssim_gain"])
            or boundary_delta["lpips"] <= -float(boundary_thresholds["lpips_drop"])
        )
        if not boundary_improved:
            block_reasons.append({"code": "boundary_no_required_improvement", "bucket": "boundary", "delta": boundary_delta})
        if boundary_delta["psnr"] < -float(near_thresholds["psnr_drop"]):
            block_reasons.append({"code": "boundary_psnr_regression", "bucket": "boundary", "delta": boundary_delta["psnr"]})
        if boundary_delta["ssim"] < -float(near_thresholds["ssim_drop"]):
            block_reasons.append({"code": "boundary_ssim_regression", "bucket": "boundary", "delta": boundary_delta["ssim"]})
        if boundary_delta["lpips"] > float(near_thresholds["lpips_rise"]):
            block_reasons.append({"code": "boundary_lpips_regression", "bucket": "boundary", "delta": boundary_delta["lpips"]})

    horizon_thresholds = thresholds["horizon"]
    horizon_delta = deltas["horizon"]["delta"]
    if horizon_delta["psnr"] is None or horizon_delta["ssim"] is None or horizon_delta["lpips"] is None:
        block_reasons.append({"code": "horizon_metrics_missing", "bucket": "horizon"})
    else:
        if horizon_delta["psnr"] < -float(horizon_thresholds["psnr_drop"]):
            block_reasons.append({"code": "horizon_psnr_regression", "bucket": "horizon", "delta": horizon_delta["psnr"]})
        if horizon_delta["ssim"] < -float(horizon_thresholds["ssim_drop"]):
            block_reasons.append({"code": "horizon_ssim_regression", "bucket": "horizon", "delta": horizon_delta["ssim"]})
        if horizon_delta["lpips"] > float(horizon_thresholds["lpips_rise"]):
            block_reasons.append({"code": "horizon_lpips_regression", "bucket": "horizon", "delta": horizon_delta["lpips"]})

    baseline_horizon_sky = _as_float_or_none((baseline_sky.get("horizon", {}) or {}).get("score"))
    candidate_horizon_sky = _as_float_or_none((candidate_sky.get("horizon", {}) or {}).get("score"))
    sky_delta = _metric_delta(candidate_horizon_sky, baseline_horizon_sky)
    sky_drop_ratio = None
    if baseline_horizon_sky is not None and baseline_horizon_sky > 0 and candidate_horizon_sky is not None:
        sky_drop_ratio = max(0.0, baseline_horizon_sky - candidate_horizon_sky) / baseline_horizon_sky
        if sky_drop_ratio > float(horizon_thresholds["sky_score_drop_ratio"]):
            block_reasons.append({"code": "horizon_sky_score_regression", "bucket": "horizon", "drop_ratio": sky_drop_ratio})
    deltas["horizon"]["sky_score_delta"] = sky_delta
    deltas["horizon"]["sky_score_drop_ratio"] = sky_drop_ratio

    merge_report = candidate_manifest.get("merge_report", {}) or {}
    fallback_tile_count = int(merge_report.get("fallback_tile_count", 0) or 0)
    retain_all_tile_count = int(merge_report.get("retain_all_tile_count", 0) or 0)
    if fallback_tile_count > 0:
        block_reasons.append({"code": "merge_fallback_tile_count_nonzero", "fallback_tile_count": fallback_tile_count})
    if retain_all_tile_count > 0:
        block_reasons.append({"code": "merge_retain_all_tile_count_nonzero", "retain_all_tile_count": retain_all_tile_count})

    baseline_views = {
        (view.get("bucket"), view.get("image_name")): view
        for view in baseline_manifest.get("views", [])
        if isinstance(view, Mapping)
    }
    candidate_views = {
        (view.get("bucket"), view.get("image_name")): view
        for view in candidate_manifest.get("views", [])
        if isinstance(view, Mapping)
    }
    side_by_side_render_paths = []
    for key, candidate_view in candidate_views.items():
        baseline_view = baseline_views.get(key)
        if baseline_view is None:
            continue
        side_by_side_render_paths.append(
            {
                "bucket": key[0],
                "image_name": key[1],
                "baseline_render": baseline_view.get("merged_render"),
                "candidate_render": candidate_view.get("merged_render"),
                "baseline_no_background_render": baseline_view.get("merged_no_background_render"),
                "candidate_no_background_render": candidate_view.get("merged_no_background_render"),
                "candidate_boundary_composite": candidate_view.get("boundary_composite"),
            }
        )

    promotion_status = "promoted" if not block_reasons else "blocked"
    return {
        "version": "geometry_consistency_review_v1",
        "baseline_artifact": baseline_manifest.get("model_artifact"),
        "candidate_artifact": candidate_manifest.get("model_artifact"),
        "camera_manifest": candidate_manifest.get("review_camera_manifest"),
        "thresholds": dict(thresholds),
        "per_bucket": deltas,
        "fallback_breakdown": {
            "fallback_tile_count": fallback_tile_count,
            "retain_all_tile_count": retain_all_tile_count,
            "tiles": merge_report.get("tiles", []),
        },
        "side_by_side_render_paths": side_by_side_render_paths,
        "block_reasons": block_reasons,
        "promotion_decision": {
            "status": promotion_status,
            "promoted": promotion_status == "promoted",
        },
    }


def load_frozen_review_images_by_bucket(
    path: Path,
    *,
    max_images_per_bucket: int | None = None,
) -> dict[str, list[str]]:
    payload = load_json(path)
    raw_buckets = payload.get("review_image_names_by_bucket", payload)
    label_to_key = {bucket_label: bucket_key for bucket_key, bucket_label in DEFAULT_BUCKET_ORDER}
    selected: dict[str, list[str]] = {}
    for bucket_key, bucket_label_value in DEFAULT_BUCKET_ORDER:
        values = raw_buckets.get(bucket_key)
        if values is None:
            values = raw_buckets.get(bucket_label_value)
        if values is None:
            values = raw_buckets.get(label_to_key.get(bucket_label_value, ""))
        image_names = [normalize_image_name(str(value)) for value in values or []]
        if max_images_per_bucket is not None:
            image_names = image_names[:max_images_per_bucket]
        selected[bucket_key] = image_names
    return selected


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
    render_settings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    bucket_medians: dict[str, dict[str, float | None]] = {}
    no_background_bucket_medians: dict[str, dict[str, float | None]] = {}
    sky_bucket_medians: dict[str, dict[str, float | None]] = {}
    for _bucket_name, bucket_label_value in DEFAULT_BUCKET_ORDER:
        bucket_views = [view for view in review_views if view["bucket"] == bucket_label_value]
        bucket_medians[bucket_label_value] = {
            "psnr": median_or_none([view["metrics"]["psnr"] for view in bucket_views]),
            "ssim": median_or_none([view["metrics"]["ssim"] for view in bucket_views]),
            "lpips": median_or_none([view["metrics"]["lpips"] for view in bucket_views]),
        }
        no_background_bucket_medians[bucket_label_value] = {
            "psnr": median_or_none([(view.get("metrics_no_background") or {}).get("psnr") for view in bucket_views]),
            "ssim": median_or_none([(view.get("metrics_no_background") or {}).get("ssim") for view in bucket_views]),
            "lpips": median_or_none([(view.get("metrics_no_background") or {}).get("lpips") for view in bucket_views]),
        }
        sky_bucket_medians[bucket_label_value] = {
            "score": median_or_none([view["sky_metrics"]["score"] for view in bucket_views]),
            "luminance": median_or_none([view["sky_metrics"]["luminance"] for view in bucket_views]),
            "saturation": median_or_none([view["sky_metrics"]["saturation"] for view in bucket_views]),
            "blue_dominance": median_or_none([view["sky_metrics"]["blue_dominance"] for view in bucket_views]),
            "edge_density": median_or_none([view["sky_metrics"]["edge_density"] for view in bucket_views]),
        }

    expected_bucket_counts = {bucket_label_value: max_images_per_bucket for _, bucket_label_value in DEFAULT_BUCKET_ORDER}
    requested_bucket_counts = {
        bucket_label_value: len(review_images_by_bucket.get(bucket_name, []))
        for bucket_name, bucket_label_value in DEFAULT_BUCKET_ORDER
    }
    actual_bucket_counts = {
        bucket_label_value: sum(1 for view in review_views if view.get("bucket") == bucket_label_value)
        for _, bucket_label_value in DEFAULT_BUCKET_ORDER
    }
    review_buckets_complete = all(
        actual_bucket_counts.get(bucket_label_value, 0) >= expected_bucket_counts[bucket_label_value]
        for _, bucket_label_value in DEFAULT_BUCKET_ORDER
    )
    retain_all_tile_count = int(merge_report.get("retain_all_tile_count", 0) or 0)
    fallback_tile_count = int(merge_report.get("fallback_tile_count", 0) or 0)
    promotion_status = (
        "ready_for_manual_signoff"
        if review_buckets_complete and retain_all_tile_count == 0 and fallback_tile_count == 0
        else "blocked"
    )
    promotion_notes: list[str] = []
    if not review_buckets_complete:
        promotion_notes.append(f"review buckets did not produce the requested {max_images_per_bucket}/{max_images_per_bucket}/{max_images_per_bucket} coverage")
    if fallback_tile_count > 0:
        promotion_notes.append("merge used fallback ownership on at least one tile")
    if retain_all_tile_count > 0:
        promotion_notes.append("merge used retain_all fallback on at least one tile")
    if merged_background_present:
        promotion_notes.append("merged review included promoted background skybox")
    else:
        promotion_notes.append("merged review had no promoted background skybox")
    merged_render_stats = [
        view.get("merged_render_stats", {})
        for view in review_views
        if isinstance(view.get("merged_render_stats"), Mapping)
    ]
    merged_rendered_counts = [
        int(stats.get("rendered_gaussians"))
        for stats in merged_render_stats
        if stats.get("rendered_gaussians") is not None
    ]
    limited_render_count = sum(1 for stats in merged_render_stats if stats.get("limited"))
    if limited_render_count:
        promotion_notes.append(f"merged review used deterministic view-capped rendering on {limited_render_count} views")

    return {
        "version": "1.0.0",
        "model_artifact": str(model_tarball),
        "selected_tile_ids": list(selected_tile_ids),
        "manifest_resolution": dict(manifest_resolution),
        "merge_report": dict(merge_report),
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
        "no_background_bucket_medians": no_background_bucket_medians,
        "sky_bucket_medians": sky_bucket_medians,
        "render_settings": dict(render_settings or {}),
        "render_stats_summary": {
            "merged_view_count": len(merged_render_stats),
            "merged_limited_view_count": limited_render_count,
            "merged_rendered_gaussian_min": float(min(merged_rendered_counts)) if merged_rendered_counts else None,
            "merged_visible_gaussian_median": median_or_none(
                [stats.get("visible_gaussians") for stats in merged_render_stats]
            ),
        },
        "promotion_readiness": {
            "status": promotion_status,
            "review_buckets_complete": review_buckets_complete,
            "retain_all_tile_count": retain_all_tile_count,
            "fallback_tile_count": fallback_tile_count,
            "manual_visual_review_required": True,
            "notes": promotion_notes,
        },
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
    render_settings = resolve_render_settings_from_env()

    logger.info("🚀 Starting tiled 3DGS quality review")
    logger.info("📦 Model input: %s", model_input_dir)
    logger.info("📁 COLMAP input: %s", colmap_input_dir)
    logger.info("📁 Output dir: %s", output_dir)
    logger.info("🖼️ Render settings: %s", render_settings)

    selected_tile_ids: list[str] = []
    trainer: NerfStudioTrainer | None = None
    try:
        model_tarball = find_model_artifact(model_input_dir)
        extracted_model_dir = extract_model_artifact(model_tarball, temp_dir / "model")
        trainer, review_input_dir, converted_input_dir = prepare_converted_dataset(colmap_input_dir, temp_dir)
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
        )
        frozen_camera_manifest = os.environ.get("QUALITY_REVIEW_CAMERA_MANIFEST", "").strip()
        if frozen_camera_manifest:
            frozen_path = Path(frozen_camera_manifest)
            if not frozen_path.exists():
                raise FileNotFoundError(f"Frozen review camera manifest was missing: {frozen_path}")
            review_images_by_bucket = load_frozen_review_images_by_bucket(
                frozen_path,
                max_images_per_bucket=max_images_per_bucket,
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
                _fx, _fy, _cx, _cy, render_width, render_height = frame_intrinsics(
                    frame,
                    transforms,
                    render_scale=float(render_settings["render_scale"]),
                )
                reference_image = load_image_tensor(reference_image_path, size=(render_width, render_height))
                reference_output_path = reference_root / bucket_label_value / Path(image_name).name
                saved_reference_path = save_rgb_image(reference_image, reference_output_path)

                merged_foreground, merged_alpha, merged_render_stats = render_gaussian_view(
                    merged_model,
                    frame,
                    transforms,
                    device,
                    render_scale=float(render_settings["render_scale"]),
                    max_gaussians_per_view=int(render_settings["max_gaussians_per_view"]),
                    cull_margin=float(render_settings["cull_margin"]),
                    min_gaussians_on_oom=int(render_settings["min_gaussians_on_oom"]),
                )
                merged_background = render_skybox_view(
                    merged_background_path,
                    frame,
                    transforms,
                    render_scale=float(render_settings["render_scale"]),
                )
                merged_final = composite_render(merged_foreground, merged_alpha, merged_background)
                merged_no_background = composite_render(
                    merged_foreground,
                    merged_alpha,
                    np.zeros_like(merged_foreground, dtype=np.float32),
                )
                merged_render_path = merged_root / bucket_label_value / f"{Path(image_name).stem}.png"
                saved_merged_path = save_rgb_image(merged_final, merged_render_path)
                merged_no_background_path = merged_no_background_root / bucket_label_value / f"{Path(image_name).stem}.png"
                saved_merged_no_background_path = save_rgb_image(merged_no_background, merged_no_background_path)

                metrics = compute_metrics(
                    merged_final,
                    reference_image,
                    lpips_model=lpips_model,
                    device=device,
                )
                metrics_no_background = compute_metrics(
                    merged_no_background,
                    reference_image,
                    lpips_model=lpips_model,
                    device=device,
                )
                sky_metrics = compute_sky_image_metrics((merged_final * 255.0).astype(np.uint8))
                sky_metrics_no_background = compute_sky_image_metrics((merged_no_background * 255.0).astype(np.uint8))

                view_entry: dict[str, Any] = {
                    "bucket": bucket_label_value,
                    "image_name": image_name,
                    "reference_image": saved_reference_path,
                    "merged_render": saved_merged_path,
                    "merged_no_background_render": saved_merged_no_background_path,
                    "metrics": metrics,
                    "metrics_no_background": metrics_no_background,
                    "sky_metrics": sky_metrics,
                    "sky_metrics_no_background": sky_metrics_no_background,
                    "merged_render_stats": merged_render_stats,
                }

                boundary_tile_ids: list[str] = []
                if bucket_label_value == "boundary":
                    boundary_tile_ids = resolve_boundary_tile_ids(tile_manifest, selected_tile_ids, image_name)
                    boundary_images = [reference_image, merged_final]
                    tile_render_paths: list[str] = []
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
                            render_scale=float(render_settings["render_scale"]),
                            max_gaussians_per_view=int(render_settings["max_gaussians_per_view"]),
                            cull_margin=float(render_settings["cull_margin"]),
                            min_gaussians_on_oom=int(render_settings["min_gaussians_on_oom"]),
                        )
                        tile_background = render_skybox_view(
                            tile_background_path,
                            frame,
                            transforms,
                            render_scale=float(render_settings["render_scale"]),
                        )
                        tile_final = composite_render(tile_foreground, tile_alpha, tile_background)
                        tile_render_path = tiles_root / tile_id / bucket_label_value / f"{Path(image_name).stem}.png"
                        tile_render_paths.append(save_rgb_image(tile_final, tile_render_path))
                        view_entry.setdefault("boundary_tile_render_stats", {})[tile_id] = tile_render_stats
                        boundary_images.append(tile_final)
                    composite_path = composites_root / f"{Path(image_name).stem}.png"
                    view_entry["boundary_context_tile_ids"] = boundary_tile_ids
                    view_entry["boundary_tile_renders"] = tile_render_paths
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
        with open(output_dir / "quality_review_manifest.json", "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)
        baseline_manifest_path = os.environ.get("BASELINE_REVIEW_MANIFEST_PATH", "").strip()
        if baseline_manifest_path:
            baseline_manifest = load_json(Path(baseline_manifest_path))
            comparison = compare_review_manifests(
                baseline_manifest=baseline_manifest,
                candidate_manifest=manifest,
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
