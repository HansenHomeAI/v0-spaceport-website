#!/usr/bin/env python3
"""Helpers for manifest-driven tiled Gaussian training and merge."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
try:
    from plyfile import PlyData, PlyElement
except ModuleNotFoundError:  # pragma: no cover - local planning/dry-run paths do not need plyfile
    PlyData = None
    PlyElement = None

DEFAULT_GLOBAL_SCAFFOLD_MAX_IMAGES = 240
DEFAULT_GLOBAL_SCAFFOLD_STRIDE = 2
DEFAULT_TILE_CONTEXT_IMAGES = 12
DEFAULT_TILE_BOUNDS_PADDING_M = 12.0
DEFAULT_CAMERA_BOUNDS_XY_PADDING_M = 24.0
DEFAULT_CAMERA_BOUNDS_Z_DOWN_PADDING_M = 48.0
DEFAULT_CAMERA_BOUNDS_Z_UP_PADDING_M = 18.0


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


def zero_bounds() -> dict[str, float]:
    return {
        "min_x": 0.0,
        "max_x": 0.0,
        "min_y": 0.0,
        "max_y": 0.0,
        "min_z": 0.0,
        "max_z": 0.0,
    }


def _quaternion_to_rotation_matrix(qw: float, qx: float, qy: float, qz: float) -> np.ndarray:
    norm = float(np.sqrt(qw * qw + qx * qx + qy * qy + qz * qz))
    if norm <= 1e-12:
        return np.eye(3, dtype=np.float64)
    qw /= norm
    qx /= norm
    qy /= norm
    qz /= norm
    return np.array(
        [
            [1.0 - 2.0 * (qy * qy + qz * qz), 2.0 * (qx * qy - qz * qw), 2.0 * (qx * qz + qy * qw)],
            [2.0 * (qx * qy + qz * qw), 1.0 - 2.0 * (qx * qx + qz * qz), 2.0 * (qy * qz - qx * qw)],
            [2.0 * (qx * qz - qy * qw), 2.0 * (qy * qz + qx * qw), 1.0 - 2.0 * (qx * qx + qy * qy)],
        ],
        dtype=np.float64,
    )


def _update_bounds(bounds: list[float] | None, point: Sequence[float]) -> list[float]:
    x, y, z = float(point[0]), float(point[1]), float(point[2])
    if bounds is None:
        return [x, x, y, y, z, z]
    bounds[0] = min(bounds[0], x)
    bounds[1] = max(bounds[1], x)
    bounds[2] = min(bounds[2], y)
    bounds[3] = max(bounds[3], y)
    bounds[4] = min(bounds[4], z)
    bounds[5] = max(bounds[5], z)
    return bounds


def _bounds_payload(bounds: Sequence[float], *, padding_m: float) -> dict[str, float]:
    return {
        "min_x": round(float(bounds[0]) - padding_m, 3),
        "max_x": round(float(bounds[1]) + padding_m, 3),
        "min_y": round(float(bounds[2]) - padding_m, 3),
        "max_y": round(float(bounds[3]) + padding_m, 3),
        "min_z": round(float(bounds[4]) - padding_m, 3),
        "max_z": round(float(bounds[5]) + padding_m, 3),
    }


def _camera_bounds_payload(bounds: Sequence[float]) -> dict[str, float]:
    return {
        "min_x": round(float(bounds[0]) - DEFAULT_CAMERA_BOUNDS_XY_PADDING_M, 3),
        "max_x": round(float(bounds[1]) + DEFAULT_CAMERA_BOUNDS_XY_PADDING_M, 3),
        "min_y": round(float(bounds[2]) - DEFAULT_CAMERA_BOUNDS_XY_PADDING_M, 3),
        "max_y": round(float(bounds[3]) + DEFAULT_CAMERA_BOUNDS_XY_PADDING_M, 3),
        "min_z": round(float(bounds[4]) - DEFAULT_CAMERA_BOUNDS_Z_DOWN_PADDING_M, 3),
        "max_z": round(float(bounds[5]) + DEFAULT_CAMERA_BOUNDS_Z_UP_PADDING_M, 3),
    }


def load_sparse_bounds_support(
    sparse_dir: str | Path | None,
) -> tuple[dict[int, str], dict[str, np.ndarray], dict[str, list[float]]]:
    if sparse_dir is None:
        return {}, {}, {}

    sparse_root = Path(sparse_dir)
    images_txt = sparse_root / "images.txt"
    points3d_txt = sparse_root / "points3D.txt"
    if not images_txt.exists():
        return {}, {}, {}

    image_id_to_name: dict[int, str] = {}
    camera_centers: dict[str, np.ndarray] = {}
    with open(images_txt, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 10:
                continue
            try:
                image_id = int(parts[0])
                qw, qx, qy, qz = (float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
                tx, ty, tz = (float(parts[5]), float(parts[6]), float(parts[7]))
            except ValueError:
                continue
            image_name = normalize_image_name(parts[9])
            image_id_to_name[image_id] = image_name
            rotation = _quaternion_to_rotation_matrix(qw, qx, qy, qz)
            translation = np.array([tx, ty, tz], dtype=np.float64)
            camera_centers[image_name] = -rotation.T @ translation

    point_bounds_by_image: dict[str, list[float]] = {}
    if not points3d_txt.exists():
        return image_id_to_name, camera_centers, point_bounds_by_image

    with open(points3d_txt, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 8:
                continue
            try:
                point = (float(parts[1]), float(parts[2]), float(parts[3]))
            except ValueError:
                continue
            track_tokens = parts[8:]
            for token_index in range(0, len(track_tokens) - 1, 2):
                try:
                    image_id = int(track_tokens[token_index])
                except ValueError:
                    continue
                image_name = image_id_to_name.get(image_id)
                if image_name is None:
                    continue
                point_bounds_by_image[image_name] = _update_bounds(
                    point_bounds_by_image.get(image_name),
                    point,
                )

    return image_id_to_name, camera_centers, point_bounds_by_image


def load_transformed_camera_centers(
    transforms_payload: Mapping[str, Any] | None,
    image_name_map_payload: Mapping[str, Any] | None,
) -> dict[str, np.ndarray]:
    if not isinstance(transforms_payload, Mapping):
        return {}

    by_converted_name = {}
    if isinstance(image_name_map_payload, Mapping):
        by_converted_name = image_name_map_payload.get("by_converted_name", {}) or {}

    transformed_camera_centers: dict[str, np.ndarray] = {}
    for frame in transforms_payload.get("frames", []):
        if not isinstance(frame, Mapping):
            continue
        transform_matrix = frame.get("transform_matrix")
        if not isinstance(transform_matrix, Sequence) or len(transform_matrix) < 3:
            continue

        try:
            transform = np.asarray(transform_matrix, dtype=np.float64)
        except (TypeError, ValueError):
            continue
        if transform.shape[0] < 3 or transform.shape[1] < 4:
            continue

        converted_name = normalize_image_name(str(frame.get("file_path", "")))
        original_entry = by_converted_name.get(converted_name)
        original_name = (
            normalize_image_name(str(original_entry.get("original_image_name")))
            if isinstance(original_entry, Mapping) and original_entry.get("original_image_name")
            else converted_name
        )
        transformed_camera_centers[original_name] = transform[:3, 3]

    return transformed_camera_centers


def load_transformed_point_bounds(
    transforms_payload: Mapping[str, Any] | None,
    image_name_map_payload: Mapping[str, Any] | None,
    point_bounds_by_image: Mapping[str, Sequence[float]],
) -> dict[str, list[float]]:
    if not isinstance(transforms_payload, Mapping) or not point_bounds_by_image:
        return {}

    applied_transform_payload = transforms_payload.get("applied_transform")
    if not isinstance(applied_transform_payload, Sequence):
        return {}
    try:
        applied_transform = np.asarray(applied_transform_payload, dtype=np.float64)
    except (TypeError, ValueError):
        return {}
    if applied_transform.shape == (3, 4):
        affine = np.eye(4, dtype=np.float64)
        affine[:3, :4] = applied_transform
    elif applied_transform.shape == (4, 4):
        affine = applied_transform
    else:
        return {}

    scale = transforms_payload.get("scale")
    if not isinstance(scale, (int, float)):
        scale = 1.0
    offset_payload = transforms_payload.get("offset")
    if isinstance(offset_payload, Sequence) and len(offset_payload) >= 3:
        try:
            offset = np.asarray(offset_payload[:3], dtype=np.float64)
        except (TypeError, ValueError):
            offset = np.zeros(3, dtype=np.float64)
    else:
        offset = np.zeros(3, dtype=np.float64)

    by_original_name = {}
    if isinstance(image_name_map_payload, Mapping):
        by_original_name = image_name_map_payload.get("by_original_image_name", {}) or {}

    transformed_bounds_by_image: dict[str, list[float]] = {}
    for original_name, bounds in point_bounds_by_image.items():
        if not isinstance(bounds, Sequence) or len(bounds) < 6:
            continue
        if by_original_name and original_name not in by_original_name:
            continue

        min_x, max_x, min_y, max_y, min_z, max_z = [float(value) for value in bounds[:6]]
        corners = np.asarray(
            [
                [x, y, z, 1.0]
                for x in (min_x, max_x)
                for y in (min_y, max_y)
                for z in (min_z, max_z)
            ],
            dtype=np.float64,
        )
        transformed = (affine @ corners.T).T[:, :3]
        transformed = transformed * float(scale) + offset
        transformed_bounds_by_image[original_name] = [
            float(np.min(transformed[:, 0])),
            float(np.max(transformed[:, 0])),
            float(np.min(transformed[:, 1])),
            float(np.max(transformed[:, 1])),
            float(np.min(transformed[:, 2])),
            float(np.max(transformed[:, 2])),
        ]

    return transformed_bounds_by_image


def selection_bounds_from_support(
    image_names: Sequence[str],
    *,
    transformed_point_bounds_by_image: Mapping[str, Sequence[float]] | None = None,
    transformed_camera_centers: Mapping[str, np.ndarray] | None = None,
    camera_centers: Mapping[str, np.ndarray],
    point_bounds_by_image: Mapping[str, Sequence[float]],
    padding_m: float = DEFAULT_TILE_BOUNDS_PADDING_M,
) -> tuple[dict[str, float], str, bool]:
    ordered_names = ordered_unique(image_names)
    transformed_bounds: list[float] | None = None
    for image_name in ordered_names:
        center = (transformed_camera_centers or {}).get(image_name)
        if center is None:
            continue
        transformed_bounds = _update_bounds(transformed_bounds, center.tolist())
    if transformed_bounds is not None:
        return _bounds_payload(transformed_bounds, padding_m=padding_m), "transformed_camera_centers", True

    transformed_point_bounds: list[float] | None = None
    for image_name in ordered_names:
        per_image_bounds = (transformed_point_bounds_by_image or {}).get(image_name)
        if per_image_bounds is None:
            continue
        transformed_point_bounds = _update_bounds(
            transformed_point_bounds,
            (per_image_bounds[0], per_image_bounds[2], per_image_bounds[4]),
        )
        transformed_point_bounds = _update_bounds(
            transformed_point_bounds,
            (per_image_bounds[1], per_image_bounds[3], per_image_bounds[5]),
        )
    if transformed_point_bounds is not None:
        return _bounds_payload(transformed_point_bounds, padding_m=padding_m), "transformed_observed_points", True

    point_bounds: list[float] | None = None
    for image_name in ordered_names:
        per_image_bounds = point_bounds_by_image.get(image_name)
        if per_image_bounds is None:
            continue
        point_bounds = _update_bounds(point_bounds, (per_image_bounds[0], per_image_bounds[2], per_image_bounds[4]))
        point_bounds = _update_bounds(point_bounds, (per_image_bounds[1], per_image_bounds[3], per_image_bounds[5]))
    if point_bounds is not None:
        return _bounds_payload(point_bounds, padding_m=padding_m), "observed_points", True

    camera_bounds: list[float] | None = None
    for image_name in ordered_names:
        center = camera_centers.get(image_name)
        if center is None:
            continue
        camera_bounds = _update_bounds(camera_bounds, center.tolist())
    if camera_bounds is not None:
        return _camera_bounds_payload(camera_bounds), "camera_centers_fallback", True

    return zero_bounds(), "missing_sparse_support", False


def normalize_view_bucket_payload(view_buckets: Mapping[str, Any] | None) -> dict[str, list[str]]:
    if not isinstance(view_buckets, Mapping):
        return {
            "near_detail_camera_ids": [],
            "boundary_camera_ids": [],
            "horizon_camera_ids": [],
        }
    return {
        "near_detail_camera_ids": ordered_unique(view_buckets.get("near_detail_camera_ids", [])),
        "boundary_camera_ids": ordered_unique(view_buckets.get("boundary_camera_ids", [])),
        "horizon_camera_ids": ordered_unique(view_buckets.get("horizon_camera_ids", [])),
    }


def select_review_image_names_by_bucket(
    selected_image_names: Sequence[str],
    view_buckets: Mapping[str, Sequence[str]] | None,
    *,
    max_images_per_bucket: int = 4,
) -> dict[str, list[str]]:
    if max_images_per_bucket <= 0:
        return {}
    selected = set(ordered_unique(selected_image_names))
    normalized_buckets = normalize_view_bucket_payload(view_buckets)
    review_images: dict[str, list[str]] = {}
    for bucket_name, image_names in normalized_buckets.items():
        review_images[bucket_name] = [
            image_name
            for image_name in ordered_unique(image_names)
            if image_name in selected
        ][:max_images_per_bucket]
    return review_images


def select_pipeline_image_names(
    tile_manifest: Mapping[str, Any],
    *,
    selected_tile_ids: Sequence[str],
) -> list[str]:
    selected = {str(tile_id).strip() for tile_id in selected_tile_ids if str(tile_id).strip()}
    image_names: list[str] = []
    for tile_entry in tile_manifest.get("tiles", []):
        tile_id = str(tile_entry.get("tile_id", "")).strip()
        if tile_id not in selected:
            continue
        image_names.extend(tile_entry.get("base_camera_ids", []))
        image_names.extend(tile_entry.get("border_camera_ids", []))
        image_names.extend(tile_entry.get("context_camera_ids", []))
        image_names.extend(tile_entry.get("image_names", []))
    return ordered_unique(image_names)


def select_pipeline_review_image_names_by_bucket(
    tile_manifest: Mapping[str, Any],
    view_buckets: Mapping[str, Sequence[str]] | None,
    *,
    selected_tile_ids: Sequence[str],
    max_images_per_bucket: int = 4,
) -> dict[str, list[str]]:
    return select_review_image_names_by_bucket(
        select_pipeline_image_names(tile_manifest, selected_tile_ids=selected_tile_ids),
        view_buckets,
        max_images_per_bucket=max_images_per_bucket,
    )


def _shared_image_count(first_chunk: Mapping[str, Any], second_chunk: Mapping[str, Any]) -> int:
    first_names = set(ordered_unique(first_chunk.get("image_names", [])))
    second_names = set(ordered_unique(second_chunk.get("image_names", [])))
    return len(first_names.intersection(second_names))


def synthesize_tiled_inputs_from_chunk_planner(
    chunk_planner_manifest: Mapping[str, Any],
    sfm_metadata: Mapping[str, Any] | None = None,
    *,
    colmap_sparse_dir: str | Path | None = None,
    transforms_payload: Mapping[str, Any] | None = None,
    image_name_map_payload: Mapping[str, Any] | None = None,
    global_scaffold_max_images: int = DEFAULT_GLOBAL_SCAFFOLD_MAX_IMAGES,
    global_scaffold_stride: int = DEFAULT_GLOBAL_SCAFFOLD_STRIDE,
    tile_context_images: int = DEFAULT_TILE_CONTEXT_IMAGES,
    tile_bounds_padding_m: float = DEFAULT_TILE_BOUNDS_PADDING_M,
) -> tuple[dict[str, Any], dict[str, list[str]], dict[str, Any]]:
    chunks = list(chunk_planner_manifest.get("chunks", []))
    if not chunks:
        raise ValueError("chunk_planner_manifest did not include any chunks")

    probe_subsets = chunk_planner_manifest.get("probe_subsets", {})
    view_buckets = normalize_view_bucket_payload(
        {
            "near_detail_camera_ids": probe_subsets.get("geometry_mix", []),
            "boundary_camera_ids": probe_subsets.get("cross_pass", []),
            "horizon_camera_ids": probe_subsets.get("horizon_context", []),
        }
    )
    all_image_names = ordered_unique(
        image_name
        for chunk in chunks
        for image_name in ordered_unique(chunk.get("image_names", []))
    )

    scaffold_names = ordered_unique(
        [
            *view_buckets["near_detail_camera_ids"],
            *view_buckets["boundary_camera_ids"],
            *view_buckets["horizon_camera_ids"],
        ]
    )
    stride = max(1, int(global_scaffold_stride))
    if len(scaffold_names) < global_scaffold_max_images:
        for image_name in all_image_names[::stride]:
            if image_name in scaffold_names:
                continue
            scaffold_names.append(image_name)
            if len(scaffold_names) >= global_scaffold_max_images:
                break
    scaffold_names = scaffold_names[:global_scaffold_max_images]
    _image_id_to_name, camera_centers, point_bounds_by_image = load_sparse_bounds_support(colmap_sparse_dir)
    transformed_camera_centers = load_transformed_camera_centers(transforms_payload, image_name_map_payload)
    transformed_point_bounds_by_image = load_transformed_point_bounds(
        transforms_payload,
        image_name_map_payload,
        point_bounds_by_image,
    )

    tiles: list[dict[str, Any]] = []
    all_tiles_have_bounds = True
    for index, chunk in enumerate(chunks):
        core_names = ordered_unique(chunk.get("core_names", []))
        overlap_names = ordered_unique(chunk.get("overlap_names", []))
        image_names = ordered_unique(chunk.get("image_names", []) or [*core_names, *overlap_names])
        ranked_neighbor_indexes = sorted(
            range(len(chunks)),
            key=lambda candidate_index: (
                -_shared_image_count(chunk, chunks[candidate_index]) if candidate_index != index else float("inf"),
                abs(candidate_index - index),
            ),
        )
        neighbor_tile_ids: list[str] = []
        context_camera_ids: list[str] = []
        image_name_set = set(image_names)
        for candidate_index in ranked_neighbor_indexes:
            if candidate_index == index:
                continue
            candidate_chunk = chunks[candidate_index]
            shared_count = _shared_image_count(chunk, candidate_chunk)
            is_adjacent = abs(candidate_index - index) == 1
            if shared_count <= 0 and not is_adjacent:
                continue
            candidate_tile_id = f"tile_{candidate_index:02d}"
            if candidate_tile_id not in neighbor_tile_ids:
                neighbor_tile_ids.append(candidate_tile_id)
            for candidate_name in ordered_unique(candidate_chunk.get("core_names", [])):
                if candidate_name in image_name_set or candidate_name in context_camera_ids:
                    continue
                context_camera_ids.append(candidate_name)
                if len(context_camera_ids) >= max(0, int(tile_context_images)):
                    break
            if len(context_camera_ids) >= max(0, int(tile_context_images)):
                break

        tile_id = f"tile_{int(chunk.get('index', index)):02d}"
        core_bounds, core_bounds_strategy, core_bounds_available = selection_bounds_from_support(
            core_names or image_names,
            transformed_point_bounds_by_image=transformed_point_bounds_by_image,
            transformed_camera_centers=transformed_camera_centers,
            camera_centers=camera_centers,
            point_bounds_by_image=point_bounds_by_image,
            padding_m=tile_bounds_padding_m,
        )
        overlap_bounds, overlap_bounds_strategy, overlap_bounds_available = selection_bounds_from_support(
            image_names or core_names,
            transformed_point_bounds_by_image=transformed_point_bounds_by_image,
            transformed_camera_centers=transformed_camera_centers,
            camera_centers=camera_centers,
            point_bounds_by_image=point_bounds_by_image,
            padding_m=tile_bounds_padding_m,
        )
        ownership_bounds_available = core_bounds_available or overlap_bounds_available
        all_tiles_have_bounds = all_tiles_have_bounds and ownership_bounds_available
        tiles.append(
            {
                "tile_id": tile_id,
                "index": int(chunk.get("index", index)),
                "parent_id": "root_lod_0",
                "core_bounds": core_bounds,
                "overlap_bounds": overlap_bounds,
                "base_camera_ids": core_names,
                "border_camera_ids": overlap_names,
                "context_camera_ids": context_camera_ids,
                "image_names": image_names,
                "neighbor_tile_ids": neighbor_tile_ids,
                "bounds_strategy": {
                    "core": core_bounds_strategy,
                    "overlap": overlap_bounds_strategy,
                },
                "ownership_bounds_available": ownership_bounds_available,
            }
        )

    manifest = {
        "version": "1.0.0",
        "planner": chunk_planner_manifest.get("planner")
        or (sfm_metadata or {}).get("hierarchy_mode")
        or "chunk_planner_compatibility_v1",
        "chunk_matcher_strategy": chunk_planner_manifest.get("chunk_matcher_strategy")
        or (sfm_metadata or {}).get("chunk_matcher_strategy"),
        "all_image_names": all_image_names,
        "global_scaffold_camera_ids": scaffold_names,
        "view_bucket_manifest": "3dgs_view_buckets.json",
        "tiles": tiles,
        "manifest_resolution": {
            "source_mode": "chunk_planner_synthesized_v1",
            "chunk_planner_available": True,
            "native_tile_manifest_available": False,
            "native_view_buckets_available": False,
            "ownership_bounds_available": all_tiles_have_bounds,
        },
    }
    resolution = dict(manifest["manifest_resolution"])
    resolution["tile_count"] = len(tiles)
    resolution["scaffold_count"] = len(scaffold_names)
    return manifest, view_buckets, resolution


def resolve_tiled_input_manifests(
    *,
    tile_manifest_payload: Mapping[str, Any] | None,
    view_bucket_payload: Mapping[str, Any] | None,
    chunk_planner_manifest: Mapping[str, Any] | None = None,
    sfm_metadata: Mapping[str, Any] | None = None,
    colmap_sparse_dir: str | Path | None = None,
    transforms_payload: Mapping[str, Any] | None = None,
    image_name_map_payload: Mapping[str, Any] | None = None,
    global_scaffold_max_images: int = DEFAULT_GLOBAL_SCAFFOLD_MAX_IMAGES,
    global_scaffold_stride: int = DEFAULT_GLOBAL_SCAFFOLD_STRIDE,
    tile_context_images: int = DEFAULT_TILE_CONTEXT_IMAGES,
    tile_bounds_padding_m: float = DEFAULT_TILE_BOUNDS_PADDING_M,
) -> tuple[dict[str, Any], dict[str, list[str]], dict[str, Any]]:
    if isinstance(tile_manifest_payload, Mapping) and isinstance(view_bucket_payload, Mapping):
        manifest = dict(tile_manifest_payload)
        view_buckets = normalize_view_bucket_payload(view_bucket_payload)
        resolution = {
            "source_mode": "native_3dgs_manifests",
            "chunk_planner_available": chunk_planner_manifest is not None,
            "native_tile_manifest_available": True,
            "native_view_buckets_available": True,
            "ownership_bounds_available": True,
            "tile_count": len(manifest.get("tiles", [])),
            "scaffold_count": len(manifest.get("global_scaffold_camera_ids", [])),
        }
        manifest.setdefault("manifest_resolution", resolution)
        return manifest, view_buckets, resolution

    if chunk_planner_manifest is None:
        raise FileNotFoundError("Missing 3DGS manifests and no chunk_planner_manifest.json was available")

    return synthesize_tiled_inputs_from_chunk_planner(
        chunk_planner_manifest,
        sfm_metadata=sfm_metadata,
        colmap_sparse_dir=colmap_sparse_dir,
        transforms_payload=transforms_payload,
        image_name_map_payload=image_name_map_payload,
        global_scaffold_max_images=global_scaffold_max_images,
        global_scaffold_stride=global_scaffold_stride,
        tile_context_images=tile_context_images,
        tile_bounds_padding_m=tile_bounds_padding_m,
    )


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
    image_name_map: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    selected = set(ordered_unique(selected_image_names))

    by_colmap_im_id = {}
    by_converted_name = {}
    if isinstance(image_name_map, Mapping):
        by_colmap_im_id = image_name_map.get("by_colmap_im_id", {}) or {}
        by_converted_name = image_name_map.get("by_converted_name", {}) or {}

    def frame_aliases(frame: Mapping[str, Any]) -> set[str]:
        aliases: set[str] = set()
        for key in ("file_path", "original_file_path", "original_image_name"):
            value = frame.get(key)
            if value:
                aliases.add(normalize_image_name(str(value)))

        converted_name = normalize_image_name(str(frame.get("file_path", "")))
        converted_entry = by_converted_name.get(converted_name)
        if isinstance(converted_entry, Mapping):
            original_name = converted_entry.get("original_image_name")
            if original_name:
                aliases.add(normalize_image_name(str(original_name)))

        colmap_im_id = frame.get("colmap_im_id")
        if colmap_im_id is not None:
            mapped_entry = by_colmap_im_id.get(str(colmap_im_id))
            if isinstance(mapped_entry, Mapping):
                original_name = mapped_entry.get("original_image_name")
                if original_name:
                    aliases.add(normalize_image_name(str(original_name)))
        return aliases

    filtered_frames = [
        frame
        for frame in transforms.get("frames", [])
        if frame_aliases(frame) & selected
    ]
    filtered = dict(transforms)
    filtered["frames"] = filtered_frames
    retained_converted_names = {
        normalize_image_name(frame.get("file_path", ""))
        for frame in filtered_frames
        if frame.get("file_path")
    }
    for key, value in transforms.items():
        if key.endswith("_filenames") and isinstance(value, list):
            filtered[key] = [
                file_name
                for file_name in value
                if normalize_image_name(str(file_name)) in retained_converted_names
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


def compute_tile_centroids(
    tile_manifest: Mapping[str, Any],
    tile_output_dirs: Mapping[str, Path],
) -> dict[str, np.ndarray]:
    if PlyData is None:
        raise ModuleNotFoundError("plyfile is required to compute tile centroids")

    centroids: dict[str, np.ndarray] = {}
    for tile_entry in tile_manifest.get("tiles", []):
        tile_id = str(tile_entry["tile_id"])
        tile_dir = tile_output_dirs.get(tile_id)
        if tile_dir is None:
            continue
        ply_path = tile_dir / "splat.ply"
        if not ply_path.exists():
            continue
        ply = PlyData.read(str(ply_path))
        vertex = ply["vertex"].data
        if len(vertex) == 0:
            continue
        positions = np.stack(
            [
                np.asarray(vertex["x"], dtype=np.float32),
                np.asarray(vertex["y"], dtype=np.float32),
                np.asarray(vertex["z"], dtype=np.float32),
            ],
            axis=1,
        )
        centroids[tile_id] = np.mean(positions, axis=0, dtype=np.float64)
    return centroids


def centroid_voronoi_mask(
    tile_id: str,
    positions: np.ndarray,
    tile_entry: Mapping[str, Any],
    tile_centroids: Mapping[str, np.ndarray],
) -> np.ndarray | None:
    candidate_tile_ids = [tile_id]
    for neighbor_tile_id in ordered_unique(tile_entry.get("neighbor_tile_ids", [])):
        if neighbor_tile_id in tile_centroids and neighbor_tile_id not in candidate_tile_ids:
            candidate_tile_ids.append(neighbor_tile_id)

    if len(candidate_tile_ids) <= 1:
        for candidate_tile_id in tile_centroids:
            if candidate_tile_id == tile_id or candidate_tile_id in candidate_tile_ids:
                continue
            candidate_tile_ids.append(candidate_tile_id)
            if len(candidate_tile_ids) >= 3:
                break

    if len(candidate_tile_ids) <= 1:
        return None

    centroids = np.stack([tile_centroids[candidate_tile_id] for candidate_tile_id in candidate_tile_ids], axis=0)
    deltas = positions[:, None, :] - centroids[None, :, :]
    distances = np.sum(np.square(deltas), axis=2)
    keep_mask = np.argmin(distances, axis=1) == 0
    if not np.any(keep_mask):
        return None
    return keep_mask


def _background_selection_score(payload: Mapping[str, Any]) -> float | None:
    selection = payload.get("selection")
    if not isinstance(selection, Mapping):
        selection = payload.get("background_selection")
    if not isinstance(selection, Mapping):
        return None
    score = selection.get("score")
    if score is None:
        return None
    try:
        return float(score)
    except (TypeError, ValueError):
        return None


def copy_best_background_skybox(
    *,
    tile_output_dirs: Mapping[str, Path],
    report_tiles: Sequence[Mapping[str, Any]],
    output_dir: Path,
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    retained_counts = {
        str(tile.get("tile_id")): int(tile.get("retained_gaussians", 0))
        for tile in report_tiles
    }
    for report_index, tile in enumerate(report_tiles):
        tile_id = str(tile.get("tile_id", "")).strip()
        if not tile_id:
            continue
        tile_dir = tile_output_dirs.get(tile_id)
        if tile_dir is None:
            continue
        skybox_path = tile_dir / "background_skybox.webp"
        if not skybox_path.exists():
            continue

        background_manifest_path = tile_dir / "background_manifest.json"
        export_manifest_path = tile_dir / "export_manifest.json"
        background_manifest = (
            load_json(background_manifest_path)
            if background_manifest_path.exists()
            else {}
        )
        export_manifest = load_json(export_manifest_path) if export_manifest_path.exists() else {}
        selection_score = _background_selection_score(background_manifest)
        if selection_score is None:
            selection_score = _background_selection_score(export_manifest)

        candidates.append(
            {
                "tile_id": tile_id,
                "tile_dir": tile_dir,
                "skybox_path": skybox_path,
                "background_manifest_path": background_manifest_path if background_manifest_path.exists() else None,
                "export_manifest_path": export_manifest_path if export_manifest_path.exists() else None,
                "background_manifest": background_manifest,
                "export_manifest": export_manifest,
                "selection_score": selection_score,
                "retained_gaussians": retained_counts.get(tile_id, 0),
                "report_index": report_index,
            }
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda candidate: (
            candidate["selection_score"] is not None,
            float(candidate["selection_score"] or float("-inf")),
            candidate["retained_gaussians"],
            -candidate["report_index"],
        ),
        reverse=True,
    )
    selected = candidates[0]
    merged_skybox_path = output_dir / "background_skybox.webp"
    shutil.copy2(selected["skybox_path"], merged_skybox_path)

    merged_background_manifest = dict(selected["background_manifest"])
    merged_background_manifest["asset"] = merged_skybox_path.name
    merged_background_manifest["source_tile_id"] = selected["tile_id"]
    merged_background_manifest["source_asset"] = str(selected["skybox_path"])
    if selected["selection_score"] is not None:
        merged_background_manifest["selection_score"] = selected["selection_score"]
    with open(output_dir / "background_manifest.json", "w", encoding="utf-8") as handle:
        json.dump(merged_background_manifest, handle, indent=2)

    return {
        "asset": merged_skybox_path.name,
        "source_tile_id": selected["tile_id"],
        "source_asset": str(selected["skybox_path"]),
        "selection_score": selected["selection_score"],
        "retained_gaussians": selected["retained_gaussians"],
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
    if PlyData is None or PlyElement is None:
        raise ModuleNotFoundError("plyfile is required to merge tile outputs")

    output_dir.mkdir(parents=True, exist_ok=True)
    merged_vertices: list[np.ndarray] = []
    reference_dtype: np.dtype | None = None
    report_tiles: list[dict[str, Any]] = []
    fallback_tile_count = 0
    retain_all_tile_count = 0
    tile_centroids = compute_tile_centroids(tile_manifest, tile_output_dirs)

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
        used_fallback = False
        if not core_bounds.is_degenerate():
            keep_mask = core_bounds.contains_points(positions)
            retention_strategy = "core_bounds"
        elif overlap_bounds is not None and not overlap_bounds.is_degenerate():
            keep_mask = overlap_bounds.contains_points(positions)
            retention_strategy = "overlap_bounds_fallback"
            used_fallback = True
        else:
            keep_mask = np.ones(total_vertex_count, dtype=bool)
            retention_strategy = "retain_all"
            used_fallback = True

        if not np.any(keep_mask) and overlap_bounds is not None and not overlap_bounds.is_degenerate():
            keep_mask = overlap_bounds.contains_points(positions)
            if np.any(keep_mask):
                retention_strategy = "overlap_bounds_fallback"
                used_fallback = True
        if not np.any(keep_mask):
            centroid_keep_mask = centroid_voronoi_mask(tile_id, positions, tile_entry, tile_centroids)
            if centroid_keep_mask is not None:
                keep_mask = centroid_keep_mask
                retention_strategy = "centroid_voronoi_fallback"
                used_fallback = True
            else:
                keep_mask = np.ones(total_vertex_count, dtype=bool)
                retention_strategy = "retain_all"
                used_fallback = True

        if used_fallback:
            fallback_tile_count += 1
        if retention_strategy == "retain_all":
            retain_all_tile_count += 1

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
                "ownership_bounds_available": bool(tile_entry.get("ownership_bounds_available", True)),
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
        "fallback_tile_count": fallback_tile_count,
        "retain_all_tile_count": retain_all_tile_count,
        "tiles": report_tiles,
    }
    background_asset = copy_best_background_skybox(
        tile_output_dirs=tile_output_dirs,
        report_tiles=report_tiles,
        output_dir=output_dir,
    )
    if background_asset is not None:
        report["background_asset"] = background_asset
    with open(output_dir / "merge_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return report
