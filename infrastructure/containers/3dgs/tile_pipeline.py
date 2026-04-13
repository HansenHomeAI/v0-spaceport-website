#!/usr/bin/env python3
"""Helpers for manifest-driven tiled Gaussian training and merge."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from plyfile import PlyData, PlyElement


@dataclass
class AxisAlignedBounds:
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AxisAlignedBounds":
        return cls(
            min_x=float(payload["min_x"]),
            max_x=float(payload["max_x"]),
            min_y=float(payload["min_y"]),
            max_y=float(payload["max_y"]),
            min_z=float(payload["min_z"]),
            max_z=float(payload["max_z"]),
        )

    def contains_points(self, positions: np.ndarray) -> np.ndarray:
        return (
            (positions[:, 0] >= self.min_x)
            & (positions[:, 0] <= self.max_x)
            & (positions[:, 1] >= self.min_y)
            & (positions[:, 1] <= self.max_y)
            & (positions[:, 2] >= self.min_z)
            & (positions[:, 2] <= self.max_z)
        )

    def is_degenerate(self, *, epsilon: float = 1e-6) -> bool:
        return (
            abs(self.max_x - self.min_x) <= epsilon
            or abs(self.max_y - self.min_y) <= epsilon
            or abs(self.max_z - self.min_z) <= epsilon
        )


def load_json(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_image_name(file_path: str) -> str:
    return Path(str(file_path).lstrip("./")).name


def ordered_unique(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = normalize_image_name(item)
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def resolve_tile_entry(tile_manifest: Mapping[str, Any], tile_id: str) -> Mapping[str, Any]:
    for tile in tile_manifest.get("tiles", []):
        if str(tile.get("tile_id")) == tile_id:
            return tile
    raise KeyError(f"Unknown tile_id={tile_id}")


def select_manifest_tile_ids(
    tile_manifest: Mapping[str, Any],
    *,
    explicit_tile_ids: Sequence[str] | None = None,
    max_tiles: int | None = None,
) -> list[str]:
    tile_ids = [str(tile.get("tile_id")) for tile in tile_manifest.get("tiles", []) if tile.get("tile_id")]
    if explicit_tile_ids:
        requested = [str(tile_id).strip() for tile_id in explicit_tile_ids if str(tile_id).strip()]
        missing = [tile_id for tile_id in requested if tile_id not in tile_ids]
        if missing:
            raise ValueError(f"Unknown tile ids requested: {', '.join(missing)}")
        tile_ids = requested
    if max_tiles is not None and max_tiles > 0:
        tile_ids = tile_ids[:max_tiles]
    return tile_ids


def subset_tile_manifest(
    tile_manifest: Mapping[str, Any],
    *,
    selected_tile_ids: Sequence[str],
) -> dict[str, Any]:
    selected = {str(tile_id) for tile_id in selected_tile_ids}
    subset = dict(tile_manifest)
    subset["tiles"] = [
        dict(tile)
        for tile in tile_manifest.get("tiles", [])
        if str(tile.get("tile_id")) in selected
    ]
    return subset


def select_training_image_names(
    *,
    training_mode: str,
    tile_manifest: Mapping[str, Any] | None,
    tile_id: str | None = None,
    max_images: int | None = None,
    stride: int = 1,
) -> list[str]:
    normalized_mode = (training_mode or "monolithic").strip().lower()
    stride = max(1, int(stride))

    if normalized_mode == "monolithic":
        if tile_manifest is None:
            return []
        image_names = ordered_unique(tile_manifest.get("all_image_names", []))
        return image_names[::stride]

    if tile_manifest is None:
        raise ValueError(f"training_mode={normalized_mode} requires a tile manifest")

    if normalized_mode == "global_scaffold":
        seed_names = ordered_unique(tile_manifest.get("global_scaffold_camera_ids", []))
        if not seed_names:
            seed_names = ordered_unique(tile_manifest.get("all_image_names", []))
        selected = seed_names[::stride]
        if max_images is not None and max_images > 0:
            selected = selected[:max_images]
        return selected

    if normalized_mode == "leaf_tile":
        if not tile_id:
            raise ValueError("leaf_tile training requires tile_id")
        tile_entry = resolve_tile_entry(tile_manifest, tile_id)
        candidate_names = ordered_unique(
            [
                *tile_entry.get("base_camera_ids", []),
                *tile_entry.get("border_camera_ids", []),
                *tile_entry.get("context_camera_ids", []),
            ]
        )
        return candidate_names[::stride]

    raise ValueError(f"Unsupported training_mode={training_mode}")


def filter_transforms_frames(
    transforms: Mapping[str, Any],
    selected_image_names: Sequence[str],
) -> dict[str, Any]:
    selected = set(ordered_unique(selected_image_names))
    filtered_frames = [
        frame
        for frame in transforms.get("frames", [])
        if normalize_image_name(frame.get("file_path", "")) in selected
    ]
    filtered = dict(transforms)
    filtered["frames"] = filtered_frames
    for key, value in transforms.items():
        if key.endswith("_filenames") and isinstance(value, list):
            filtered[key] = [
                file_name
                for file_name in value
                if normalize_image_name(str(file_name)) in selected
            ]
    return filtered


def selection_counts_for_buckets(
    selected_image_names: Sequence[str],
    view_buckets: Mapping[str, Sequence[str]] | None,
) -> dict[str, int]:
    if not view_buckets:
        return {}
    selected = set(ordered_unique(selected_image_names))
    return {
        bucket_name: sum(1 for image_name in ordered_unique(image_names) if image_name in selected)
        for bucket_name, image_names in view_buckets.items()
    }


def merge_tile_outputs(
    *,
    tile_manifest: Mapping[str, Any],
    tile_output_dirs: Mapping[str, Path],
    output_dir: Path,
    merge_mode: str = "strict_core",
) -> dict[str, Any]:
    normalized_mode = merge_mode.strip().lower()
    if normalized_mode != "strict_core":
        raise ValueError(f"Unsupported merge_mode={merge_mode}")

    output_dir.mkdir(parents=True, exist_ok=True)
    merged_vertices: list[np.ndarray] = []
    reference_dtype: np.dtype | None = None
    report_tiles: list[dict[str, Any]] = []

    for tile_entry in tile_manifest.get("tiles", []):
        tile_id = str(tile_entry["tile_id"])
        tile_dir = tile_output_dirs.get(tile_id)
        if tile_dir is None:
            raise FileNotFoundError(f"Missing output directory for tile {tile_id}")
        ply_path = tile_dir / "splat.ply"
        if not ply_path.exists():
            raise FileNotFoundError(f"Missing splat.ply for tile {tile_id}: {ply_path}")

        ply = PlyData.read(str(ply_path))
        vertex = ply["vertex"].data
        total_vertex_count = int(len(vertex))
        if total_vertex_count == 0:
            report_tiles.append(
                {
                    "tile_id": tile_id,
                    "source_ply": str(ply_path),
                    "source_gaussians": 0,
                    "retained_gaussians": 0,
                    "dropped_gaussians": 0,
                }
            )
            continue

        positions = np.stack(
            [
                np.asarray(vertex["x"], dtype=np.float32),
                np.asarray(vertex["y"], dtype=np.float32),
                np.asarray(vertex["z"], dtype=np.float32),
            ],
            axis=1,
        )
        core_bounds = AxisAlignedBounds.from_dict(tile_entry["core_bounds"])
        overlap_bounds_payload = tile_entry.get("overlap_bounds")
        overlap_bounds = (
            AxisAlignedBounds.from_dict(overlap_bounds_payload)
            if isinstance(overlap_bounds_payload, Mapping)
            else None
        )
        if not core_bounds.is_degenerate():
            keep_mask = core_bounds.contains_points(positions)
            retention_strategy = "core_bounds"
        elif overlap_bounds is not None and not overlap_bounds.is_degenerate():
            keep_mask = overlap_bounds.contains_points(positions)
            retention_strategy = "overlap_bounds_fallback"
        else:
            keep_mask = np.ones(total_vertex_count, dtype=bool)
            retention_strategy = "retain_all"

        if not np.any(keep_mask) and overlap_bounds is not None and not overlap_bounds.is_degenerate():
            keep_mask = overlap_bounds.contains_points(positions)
            if np.any(keep_mask):
                retention_strategy = "overlap_bounds_fallback"

        kept_vertex = vertex[keep_mask]

        if reference_dtype is None:
            reference_dtype = kept_vertex.dtype if len(kept_vertex) else vertex.dtype
        elif kept_vertex.dtype != reference_dtype and len(kept_vertex):
            kept_vertex = kept_vertex.astype(reference_dtype, copy=False)

        if len(kept_vertex):
            merged_vertices.append(kept_vertex)

        report_tiles.append(
            {
                "tile_id": tile_id,
                "source_ply": str(ply_path),
                "source_gaussians": total_vertex_count,
                "retained_gaussians": int(len(kept_vertex)),
                "dropped_gaussians": int(total_vertex_count - len(kept_vertex)),
                "retention_strategy": retention_strategy,
            }
        )

    if not merged_vertices:
        raise RuntimeError("Strict core merge produced no retained gaussians")

    merged_vertex = np.concatenate(merged_vertices)
    merged_path = output_dir / "merged_splat.ply"
    PlyData([PlyElement.describe(merged_vertex, "vertex")], text=False).write(str(merged_path))

    report = {
        "merge_mode": normalized_mode,
        "merged_ply": str(merged_path),
        "tile_count": len(report_tiles),
        "source_gaussians": sum(tile["source_gaussians"] for tile in report_tiles),
        "retained_gaussians": sum(tile["retained_gaussians"] for tile in report_tiles),
        "dropped_gaussians": sum(tile["dropped_gaussians"] for tile in report_tiles),
        "tiles": report_tiles,
    }
    with open(output_dir / "merge_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return report
