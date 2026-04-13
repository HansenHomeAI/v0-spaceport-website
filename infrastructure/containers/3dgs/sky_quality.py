#!/usr/bin/env python3
"""
Utilities for background camera selection and foreground floater pruning.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image
from plyfile import PlyData, PlyElement

try:
    import cv2
except ImportError:  # pragma: no cover - only exercised inside the container image
    cv2 = None


SH_C0 = 0.28209479177387814


@dataclass
class BackgroundSelectionResult:
    requested_mode: str
    resolved_mode: str
    camera_idx: Optional[int]
    image_path: Optional[str]
    score: Optional[float]
    stride: int
    max_frames: int
    sampled_candidates: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FloaterPruningResult:
    enabled: bool
    evaluated_gaussians: int
    candidate_gaussians: int
    removed_gaussians: int
    remaining_gaussians: int
    sampled_views: int
    min_views: int
    top_region_ratio: float
    top_view_fraction: float
    min_sky_views: int
    sky_min_luminance: float
    sky_min_saturation: float
    sky_blue_dominance_margin: float
    max_opacity: float
    max_color_distance: float
    min_edge_support: int
    patch_size: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_transforms(data_dir: Path) -> dict[str, Any]:
    transforms_path = data_dir / "transforms.json"
    with open(transforms_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_image_path(data_dir: Path, file_path: str) -> Path:
    candidate = (data_dir / file_path).resolve()
    if candidate.exists():
        return candidate
    stripped = file_path.lstrip("./")
    candidate = (data_dir / stripped).resolve()
    if candidate.exists():
        return candidate
    candidate = (data_dir / "images" / Path(stripped).name).resolve()
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Could not resolve image path for frame: {file_path}")


def _load_image_rgb(image_path: Path) -> np.ndarray:
    image = Image.open(image_path).convert("RGB")
    return np.asarray(image, dtype=np.uint8)


def _ensure_cv2() -> Any:
    if cv2 is None:
        raise RuntimeError("opencv-python-headless is required for sky quality analysis")
    return cv2


def _compute_image_score(image: np.ndarray, top_ratio: float = 0.3) -> dict[str, float]:
    cv2_mod = _ensure_cv2()
    top_height = max(1, int(round(image.shape[0] * top_ratio)))
    crop = image[:top_height]
    rgb = crop.astype(np.float32) / 255.0

    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]
    luminance = float((0.2126 * r + 0.7152 * g + 0.0722 * b).mean())
    saturation = float((rgb.max(axis=-1) - rgb.min(axis=-1)).mean())
    blue_mask = (b > r + 0.02) & (b > g + 0.02)
    blue_dominance = float(blue_mask.mean())

    gray = cv2_mod.cvtColor(crop, cv2_mod.COLOR_RGB2GRAY)
    edges = cv2_mod.Canny(gray, 50, 150)
    edge_density = float((edges > 0).mean())
    score = (0.45 * blue_dominance) + (0.35 * saturation) + (0.20 * luminance) - (0.25 * edge_density)

    return {
        "luminance": luminance,
        "saturation": saturation,
        "blue_dominance": blue_dominance,
        "edge_density": edge_density,
        "score": score,
    }


def select_background_camera(
    data_dir: Path,
    requested_mode: str,
    stride: int,
    max_frames: int,
    default_camera_idx: int = 0,
    top_ratio: float = 0.3,
) -> BackgroundSelectionResult:
    if requested_mode == "average":
        return BackgroundSelectionResult(
            requested_mode=requested_mode,
            resolved_mode="average",
            camera_idx=default_camera_idx,
            image_path=None,
            score=None,
            stride=stride,
            max_frames=max_frames,
            sampled_candidates=0,
        )

    transforms = _load_transforms(data_dir)
    frames = transforms.get("frames", [])
    if not frames:
        raise RuntimeError("No frames found in transforms.json for background selection")

    if requested_mode == "camera":
        frame = frames[min(max(default_camera_idx, 0), len(frames) - 1)]
        return BackgroundSelectionResult(
            requested_mode=requested_mode,
            resolved_mode="camera",
            camera_idx=min(max(default_camera_idx, 0), len(frames) - 1),
            image_path=str(_resolve_image_path(data_dir, frame["file_path"])),
            score=None,
            stride=stride,
            max_frames=max_frames,
            sampled_candidates=1,
        )

    if requested_mode != "auto_camera":
        raise ValueError(f"Unsupported background appearance mode: {requested_mode}")

    candidate_indices = list(range(0, len(frames), max(1, stride)))[: max(1, max_frames)]
    best_result: Optional[BackgroundSelectionResult] = None

    for camera_idx in candidate_indices:
        frame = frames[camera_idx]
        image_path = _resolve_image_path(data_dir, frame["file_path"])
        image = _load_image_rgb(image_path)
        stats = _compute_image_score(image=image, top_ratio=top_ratio)

        candidate = BackgroundSelectionResult(
            requested_mode=requested_mode,
            resolved_mode="camera",
            camera_idx=camera_idx,
            image_path=str(image_path),
            score=stats["score"],
            stride=stride,
            max_frames=max_frames,
            sampled_candidates=len(candidate_indices),
        )
        if best_result is None or (candidate.score or float("-inf")) > (best_result.score or float("-inf")):
            best_result = candidate

    if best_result is None:
        raise RuntimeError("Automatic background camera selection did not evaluate any frames")
    return best_result


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-values))


def _gaussian_rgb_from_vertex_data(vertex_data: np.ndarray) -> np.ndarray:
    sh0 = np.stack(
        [
            vertex_data["f_dc_0"].astype(np.float32),
            vertex_data["f_dc_1"].astype(np.float32),
            vertex_data["f_dc_2"].astype(np.float32),
        ],
        axis=1,
    )
    return np.clip((sh0 * SH_C0) + 0.5, 0.0, 1.0)


def _frame_intrinsics(frame: dict[str, Any], transforms: dict[str, Any]) -> tuple[float, float, float, float, int, int]:
    width = int(frame.get("w", transforms.get("w")))
    height = int(frame.get("h", transforms.get("h")))
    fx = float(frame.get("fl_x", transforms.get("fl_x")))
    fy = float(frame.get("fl_y", transforms.get("fl_y")))
    cx = float(frame.get("cx", transforms.get("cx", width / 2.0)))
    cy = float(frame.get("cy", transforms.get("cy", height / 2.0)))
    return fx, fy, cx, cy, width, height


def _project_points(points_world: np.ndarray, c2w: np.ndarray, intrinsics: tuple[float, float, float, float, int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    fx, fy, cx, cy, width, height = intrinsics
    points_h = np.concatenate([points_world, np.ones((points_world.shape[0], 1), dtype=np.float32)], axis=1)
    w2c = np.linalg.inv(c2w)
    camera_points = (w2c @ points_h.T).T[:, :3]
    depth = -camera_points[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        xs = (fx * (camera_points[:, 0] / depth)) + cx
        ys = (fy * (camera_points[:, 1] / depth)) + cy
    visible = (
        np.isfinite(xs)
        & np.isfinite(ys)
        & (depth > 1e-6)
        & (xs >= 0)
        & (xs < width)
        & (ys >= 0)
        & (ys < height)
    )
    return xs, ys, visible


def _integral_sum(integral: np.ndarray, x1: np.ndarray, y1: np.ndarray, x2: np.ndarray, y2: np.ndarray) -> np.ndarray:
    return integral[y2 + 1, x2 + 1] - integral[y1, x2 + 1] - integral[y2 + 1, x1] + integral[y1, x1]


def _patch_means(image: np.ndarray, xs: np.ndarray, ys: np.ndarray, patch_size: int) -> np.ndarray:
    radius = patch_size // 2
    xs_i = np.round(xs).astype(np.int32)
    ys_i = np.round(ys).astype(np.int32)
    x1 = np.clip(xs_i - radius, 0, image.shape[1] - 1)
    x2 = np.clip(xs_i + radius, 0, image.shape[1] - 1)
    y1 = np.clip(ys_i - radius, 0, image.shape[0] - 1)
    y2 = np.clip(ys_i + radius, 0, image.shape[0] - 1)
    area = ((x2 - x1 + 1) * (y2 - y1 + 1)).astype(np.float32)

    means = []
    for channel in range(image.shape[2]):
        channel_integral = cv2.integral(image[..., channel].astype(np.float32))
        channel_sum = _integral_sum(channel_integral, x1, y1, x2, y2)
        means.append(channel_sum / area)
    return np.stack(means, axis=1)


def _patch_edge_presence(edge_map: np.ndarray, xs: np.ndarray, ys: np.ndarray, patch_size: int) -> np.ndarray:
    radius = patch_size // 2
    xs_i = np.round(xs).astype(np.int32)
    ys_i = np.round(ys).astype(np.int32)
    x1 = np.clip(xs_i - radius, 0, edge_map.shape[1] - 1)
    x2 = np.clip(xs_i + radius, 0, edge_map.shape[1] - 1)
    y1 = np.clip(ys_i - radius, 0, edge_map.shape[0] - 1)
    y2 = np.clip(ys_i + radius, 0, edge_map.shape[0] - 1)
    edge_integral = cv2.integral(edge_map.astype(np.float32))
    edge_sum = _integral_sum(edge_integral, x1, y1, x2, y2)
    return edge_sum > 0


def _patch_sky_presence(
    patch_means: np.ndarray,
    min_luminance: float,
    min_saturation: float,
    blue_dominance_margin: float,
) -> np.ndarray:
    r = patch_means[:, 0]
    g = patch_means[:, 1]
    b = patch_means[:, 2]
    luminance = (0.2126 * r) + (0.7152 * g) + (0.0722 * b)
    saturation = patch_means.max(axis=1) - patch_means.min(axis=1)
    blue_dominant = (b > (r + blue_dominance_margin)) & (b > (g + blue_dominance_margin))
    return blue_dominant & (luminance >= min_luminance) & (saturation >= min_saturation)


def prune_foreground_floaters(
    ply_path: Path,
    data_dir: Path,
    sampled_views: int = 24,
    min_views: int = 4,
    top_region_ratio: float = 0.35,
    top_view_fraction: float = 0.8,
    min_sky_views: int = 0,
    sky_min_luminance: float = 0.3,
    sky_min_saturation: float = 0.08,
    sky_blue_dominance_margin: float = 0.02,
    max_opacity: float = 0.25,
    max_color_distance: float = 0.12,
    min_edge_support: int = 2,
    patch_size: int = 9,
) -> FloaterPruningResult:
    cv2_mod = _ensure_cv2()
    transforms = _load_transforms(data_dir)
    frames = transforms.get("frames", [])
    if not frames:
        raise RuntimeError("No frames available for floater pruning")

    ply = PlyData.read(str(ply_path))
    vertex = ply["vertex"].data
    total_gaussians = len(vertex)
    if total_gaussians == 0:
        return FloaterPruningResult(
            enabled=True,
            evaluated_gaussians=0,
            candidate_gaussians=0,
            removed_gaussians=0,
            remaining_gaussians=0,
            sampled_views=0,
            min_views=min_views,
            top_region_ratio=top_region_ratio,
            top_view_fraction=top_view_fraction,
            min_sky_views=min_sky_views,
            sky_min_luminance=sky_min_luminance,
            sky_min_saturation=sky_min_saturation,
            sky_blue_dominance_margin=sky_blue_dominance_margin,
            max_opacity=max_opacity,
            max_color_distance=max_color_distance,
            min_edge_support=min_edge_support,
            patch_size=patch_size,
        )

    positions = np.stack([vertex["x"], vertex["y"], vertex["z"]], axis=1).astype(np.float32)
    actual_opacity = _sigmoid(np.asarray(vertex["opacity"], dtype=np.float32))
    candidate_mask = actual_opacity < max_opacity
    candidate_indices = np.flatnonzero(candidate_mask)
    if candidate_indices.size == 0:
        return FloaterPruningResult(
            enabled=True,
            evaluated_gaussians=total_gaussians,
            candidate_gaussians=0,
            removed_gaussians=0,
            remaining_gaussians=total_gaussians,
            sampled_views=min(sampled_views, len(frames)),
            min_views=min_views,
            top_region_ratio=top_region_ratio,
            top_view_fraction=top_view_fraction,
            min_sky_views=min_sky_views,
            sky_min_luminance=sky_min_luminance,
            sky_min_saturation=sky_min_saturation,
            sky_blue_dominance_margin=sky_blue_dominance_margin,
            max_opacity=max_opacity,
            max_color_distance=max_color_distance,
            min_edge_support=min_edge_support,
            patch_size=patch_size,
        )

    candidate_positions = positions[candidate_indices]
    candidate_colors = _gaussian_rgb_from_vertex_data(vertex)[candidate_indices]

    sampled_frame_indices = np.unique(
        np.linspace(0, len(frames) - 1, num=min(sampled_views, len(frames)), dtype=int)
    )
    visible_counts = np.zeros(candidate_indices.shape[0], dtype=np.int32)
    top_counts = np.zeros(candidate_indices.shape[0], dtype=np.int32)
    sky_support_counts = np.zeros(candidate_indices.shape[0], dtype=np.int32)
    edge_support_counts = np.zeros(candidate_indices.shape[0], dtype=np.int32)
    sky_edge_support_counts = np.zeros(candidate_indices.shape[0], dtype=np.int32)
    color_distances = np.full((candidate_indices.shape[0], sampled_frame_indices.shape[0]), np.nan, dtype=np.float32)

    for sample_slot, frame_idx in enumerate(sampled_frame_indices):
        frame = frames[int(frame_idx)]
        image_path = _resolve_image_path(data_dir, frame["file_path"])
        image = _load_image_rgb(image_path)
        fx, fy, cx, cy, width, height = _frame_intrinsics(frame, transforms)
        intrinsics = (fx, fy, cx, cy, width, height)
        c2w = np.asarray(frame["transform_matrix"], dtype=np.float32)

        xs, ys, visible = _project_points(candidate_positions, c2w, intrinsics)
        visible_counts += visible.astype(np.int32)
        if not visible.any():
            continue

        top_visible = visible & (ys < (height * top_region_ratio))
        top_counts += top_visible.astype(np.int32)
        active_visible = np.flatnonzero(visible)
        if active_visible.size == 0:
            continue

        gray = cv2_mod.cvtColor(image, cv2_mod.COLOR_RGB2GRAY)
        edge_map = cv2_mod.Canny(gray, 50, 150)
        patch_means = _patch_means(
            image=image.astype(np.float32) / 255.0,
            xs=xs[active_visible],
            ys=ys[active_visible],
            patch_size=patch_size,
        )
        patch_edges = _patch_edge_presence(
            edge_map=edge_map > 0,
            xs=xs[active_visible],
            ys=ys[active_visible],
            patch_size=patch_size,
        )
        patch_sky = _patch_sky_presence(
            patch_means=patch_means,
            min_luminance=sky_min_luminance,
            min_saturation=sky_min_saturation,
            blue_dominance_margin=sky_blue_dominance_margin,
        )
        edge_support_counts[active_visible] += patch_edges.astype(np.int32)
        sky_support_counts[active_visible] += patch_sky.astype(np.int32)
        sky_edge_support_counts[active_visible] += (patch_edges & patch_sky).astype(np.int32)

        rgb_delta = candidate_colors[active_visible] - patch_means
        color_distances[active_visible, sample_slot] = np.linalg.norm(rgb_delta, axis=1)

    finite_color_mask = np.isfinite(color_distances).any(axis=1)
    median_color_distance = np.full(candidate_indices.shape[0], np.inf, dtype=np.float32)
    if finite_color_mask.any():
        median_color_distance[finite_color_mask] = np.nanmedian(color_distances[finite_color_mask], axis=1)

    top_fraction = np.divide(
        top_counts,
        np.maximum(visible_counts, 1),
        out=np.zeros_like(top_counts, dtype=np.float32),
        where=visible_counts > 0,
    )
    meets_top_region = top_fraction >= top_view_fraction
    meets_sky_support = (
        sky_support_counts >= min_sky_views
        if min_sky_views > 0
        else np.zeros_like(sky_support_counts, dtype=bool)
    )
    removal_local_mask = (
        (visible_counts >= min_views)
        & (meets_top_region | meets_sky_support)
        & (sky_edge_support_counts < min_edge_support)
        & (median_color_distance <= max_color_distance)
    )
    removal_global_mask = np.zeros(total_gaussians, dtype=bool)
    removal_global_mask[candidate_indices[removal_local_mask]] = True

    if removal_global_mask.any():
        pruned_vertex = vertex[~removal_global_mask]
        pruned_element = PlyElement.describe(pruned_vertex, "vertex")
        PlyData([pruned_element], text=False).write(str(ply_path))
    removed_gaussians = int(removal_global_mask.sum())
    remaining_gaussians = int(total_gaussians - removed_gaussians)

    return FloaterPruningResult(
        enabled=True,
        evaluated_gaussians=total_gaussians,
        candidate_gaussians=int(candidate_indices.shape[0]),
        removed_gaussians=removed_gaussians,
        remaining_gaussians=remaining_gaussians,
        sampled_views=int(sampled_frame_indices.shape[0]),
        min_views=min_views,
        top_region_ratio=top_region_ratio,
        top_view_fraction=top_view_fraction,
        min_sky_views=min_sky_views,
        sky_min_luminance=sky_min_luminance,
        sky_min_saturation=sky_min_saturation,
        sky_blue_dominance_margin=sky_blue_dominance_margin,
        max_opacity=max_opacity,
        max_color_distance=max_color_distance,
        min_edge_support=min_edge_support,
        patch_size=patch_size,
    )
