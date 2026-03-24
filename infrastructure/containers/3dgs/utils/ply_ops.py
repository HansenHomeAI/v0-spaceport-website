#!/usr/bin/env python3
"""
PLY utilities for clipping, merging, and dry-run model generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
from plyfile import PlyData, PlyElement

from .segmented_training import Bounds2D, PlaneProjector


@dataclass
class ClippedTileResult:
    tile_id: str
    output_path: Path
    input_count: int
    clipped_count: int
    core_bounds: Bounds2D
    projected_xy: np.ndarray
    vertex_data: np.ndarray


@dataclass
class MergeResult:
    output_path: Path
    pre_prune_count: int
    merged_count: int
    seam_density_ratio: float
    tile_counts: Dict[str, int]


def read_vertex_data(ply_path: Path) -> tuple[PlyData, np.ndarray]:
    ply = PlyData.read(str(ply_path))
    vertex_data = ply["vertex"].data
    return ply, vertex_data


def clip_ply_to_bounds(
    ply_path: Path,
    projector: PlaneProjector,
    core_bounds: Bounds2D,
    output_path: Path,
    tile_id: str,
) -> ClippedTileResult:
    ply, vertex_data = read_vertex_data(ply_path)
    projected_xy = projector.project_points(_extract_xyz(vertex_data))
    keep_mask = core_bounds.contains(projected_xy)
    clipped_data = vertex_data[keep_mask]
    if clipped_data.size == 0:
        raise ValueError(f"Tile {tile_id} produced no gaussians inside its core bounds")

    _write_vertex_data(clipped_data, output_path, ply.comments)

    return ClippedTileResult(
        tile_id=tile_id,
        output_path=output_path,
        input_count=int(vertex_data.shape[0]),
        clipped_count=int(clipped_data.shape[0]),
        core_bounds=core_bounds,
        projected_xy=projected_xy[keep_mask],
        vertex_data=clipped_data,
    )


def merge_clipped_tiles(
    clipped_tiles: Sequence[ClippedTileResult],
    target_total_gaussians: int,
    output_path: Path,
    seam_ratio_limit: float = 2.5,
) -> MergeResult:
    if not clipped_tiles:
        raise ValueError("No clipped tiles were provided for merge")

    seam_density_ratio = _compute_seam_density_ratio(clipped_tiles)
    if seam_density_ratio > seam_ratio_limit:
        raise ValueError(
            f"Seam density ratio {seam_density_ratio:.2f} exceeded limit {seam_ratio_limit:.2f}"
        )

    combined = np.concatenate([tile.vertex_data for tile in clipped_tiles])
    pre_prune_count = int(combined.shape[0])
    if pre_prune_count > target_total_gaussians:
        scores = _compute_scores(combined)
        keep_indices = np.argpartition(scores, -target_total_gaussians)[-target_total_gaussians:]
        keep_indices = keep_indices[np.argsort(scores[keep_indices])[::-1]]
        combined = combined[keep_indices]

    _write_vertex_data(combined, output_path)

    return MergeResult(
        output_path=output_path,
        pre_prune_count=pre_prune_count,
        merged_count=int(combined.shape[0]),
        seam_density_ratio=seam_density_ratio,
        tile_counts={tile.tile_id: tile.clipped_count for tile in clipped_tiles},
    )


def write_mock_gaussian_ply(
    output_path: Path,
    centers_xyz: np.ndarray,
    count: int,
    seed: int,
) -> None:
    if centers_xyz.size == 0:
        raise ValueError("Mock gaussian generation requires at least one center")

    rng = np.random.default_rng(seed)
    source_indices = rng.integers(0, centers_xyz.shape[0], size=max(count, 1))
    sampled = centers_xyz[source_indices]
    jitter = rng.normal(0.0, 0.01, size=sampled.shape)
    points = sampled + jitter

    dtype = np.dtype(
        [
            ("x", "f4"),
            ("y", "f4"),
            ("z", "f4"),
            ("opacity", "f4"),
            ("scale_0", "f4"),
            ("scale_1", "f4"),
            ("scale_2", "f4"),
        ]
    )
    vertex_data = np.empty(points.shape[0], dtype=dtype)
    vertex_data["x"] = points[:, 0].astype(np.float32)
    vertex_data["y"] = points[:, 1].astype(np.float32)
    vertex_data["z"] = points[:, 2].astype(np.float32)
    vertex_data["opacity"] = rng.uniform(0.35, 0.95, size=points.shape[0]).astype(np.float32)
    vertex_data["scale_0"] = rng.normal(-2.4, 0.1, size=points.shape[0]).astype(np.float32)
    vertex_data["scale_1"] = rng.normal(-2.4, 0.1, size=points.shape[0]).astype(np.float32)
    vertex_data["scale_2"] = rng.normal(-2.2, 0.1, size=points.shape[0]).astype(np.float32)
    _write_vertex_data(vertex_data, output_path, comments=["Mock gaussian output for dry-run validation"])


def _extract_xyz(vertex_data: np.ndarray) -> np.ndarray:
    return np.stack(
        (
            np.asarray(vertex_data["x"], dtype=np.float64),
            np.asarray(vertex_data["y"], dtype=np.float64),
            np.asarray(vertex_data["z"], dtype=np.float64),
        ),
        axis=1,
    )


def _write_vertex_data(vertex_data: np.ndarray, output_path: Path, comments: Optional[List[str]] = None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    element = PlyElement.describe(vertex_data, "vertex")
    comments = comments or ["Generated by Spaceport segmented training"]
    PlyData([element], text=False, comments=comments).write(str(output_path))


def _compute_scores(vertex_data: np.ndarray) -> np.ndarray:
    opacity = _extract_opacity(vertex_data)
    scales = _extract_scales(vertex_data)
    scale_mean = np.maximum(scales.mean(axis=1), 1e-6)
    return opacity / scale_mean


def _extract_opacity(vertex_data: np.ndarray) -> np.ndarray:
    if "opacity" not in vertex_data.dtype.names:
        return np.ones((vertex_data.shape[0],), dtype=np.float32)
    opacity = np.asarray(vertex_data["opacity"], dtype=np.float64)
    if np.any(opacity < 0.0) or np.any(opacity > 1.0):
        opacity = 1.0 / (1.0 + np.exp(-opacity))
    return np.clip(opacity, 1e-4, 1.0)


def _extract_scales(vertex_data: np.ndarray) -> np.ndarray:
    scale_fields = [field for field in ("scale_0", "scale_1", "scale_2") if field in vertex_data.dtype.names]
    if not scale_fields:
        return np.ones((vertex_data.shape[0], 3), dtype=np.float32)
    scales = np.column_stack([np.asarray(vertex_data[field], dtype=np.float64) for field in scale_fields])
    if np.any(scales <= 0.0):
        scales = np.exp(scales)
    if scales.shape[1] == 1:
        scales = np.repeat(scales, 3, axis=1)
    return np.maximum(scales, 1e-6)


def _compute_seam_density_ratio(clipped_tiles: Sequence[ClippedTileResult]) -> float:
    max_ratio = 1.0
    bounds_tolerance = 1e-6

    for left_index in range(len(clipped_tiles)):
        left = clipped_tiles[left_index]
        for right_index in range(left_index + 1, len(clipped_tiles)):
            right = clipped_tiles[right_index]
            ratio = _border_density_ratio(left, right, bounds_tolerance)
            max_ratio = max(max_ratio, ratio)

    return max_ratio


def _border_density_ratio(left: ClippedTileResult, right: ClippedTileResult, tolerance: float) -> float:
    left_bounds = left.core_bounds
    right_bounds = right.core_bounds

    overlap_y = min(left_bounds.maximum[1], right_bounds.maximum[1]) - max(
        left_bounds.minimum[1], right_bounds.minimum[1]
    )
    overlap_x = min(left_bounds.maximum[0], right_bounds.maximum[0]) - max(
        left_bounds.minimum[0], right_bounds.minimum[0]
    )

    if abs(left_bounds.maximum[0] - right_bounds.minimum[0]) <= tolerance and overlap_y > 0:
        strip_width = max(min(left_bounds.size[0], right_bounds.size[0]) * 0.05, 1e-6)
        left_count = _count_vertical_strip(left.projected_xy, left_bounds.maximum[0] - strip_width, left_bounds.maximum[0])
        right_count = _count_vertical_strip(right.projected_xy, right_bounds.minimum[0], right_bounds.minimum[0] + strip_width)
        return _safe_ratio(left_count, right_count)

    if abs(right_bounds.maximum[0] - left_bounds.minimum[0]) <= tolerance and overlap_y > 0:
        strip_width = max(min(left_bounds.size[0], right_bounds.size[0]) * 0.05, 1e-6)
        left_count = _count_vertical_strip(left.projected_xy, left_bounds.minimum[0], left_bounds.minimum[0] + strip_width)
        right_count = _count_vertical_strip(right.projected_xy, right_bounds.maximum[0] - strip_width, right_bounds.maximum[0])
        return _safe_ratio(left_count, right_count)

    if abs(left_bounds.maximum[1] - right_bounds.minimum[1]) <= tolerance and overlap_x > 0:
        strip_width = max(min(left_bounds.size[1], right_bounds.size[1]) * 0.05, 1e-6)
        left_count = _count_horizontal_strip(left.projected_xy, left_bounds.maximum[1] - strip_width, left_bounds.maximum[1])
        right_count = _count_horizontal_strip(right.projected_xy, right_bounds.minimum[1], right_bounds.minimum[1] + strip_width)
        return _safe_ratio(left_count, right_count)

    if abs(right_bounds.maximum[1] - left_bounds.minimum[1]) <= tolerance and overlap_x > 0:
        strip_width = max(min(left_bounds.size[1], right_bounds.size[1]) * 0.05, 1e-6)
        left_count = _count_horizontal_strip(left.projected_xy, left_bounds.minimum[1], left_bounds.minimum[1] + strip_width)
        right_count = _count_horizontal_strip(right.projected_xy, right_bounds.maximum[1] - strip_width, right_bounds.maximum[1])
        return _safe_ratio(left_count, right_count)

    return 1.0


def _count_vertical_strip(projected_xy: np.ndarray, minimum: float, maximum: float) -> int:
    if projected_xy.size == 0:
        return 0
    return int(np.sum((projected_xy[:, 0] >= minimum) & (projected_xy[:, 0] <= maximum)))


def _count_horizontal_strip(projected_xy: np.ndarray, minimum: float, maximum: float) -> int:
    if projected_xy.size == 0:
        return 0
    return int(np.sum((projected_xy[:, 1] >= minimum) & (projected_xy[:, 1] <= maximum)))


def _safe_ratio(left_count: int, right_count: int) -> float:
    if left_count == 0 and right_count == 0:
        return 1.0
    return max(left_count, right_count) / max(1, min(left_count, right_count))

