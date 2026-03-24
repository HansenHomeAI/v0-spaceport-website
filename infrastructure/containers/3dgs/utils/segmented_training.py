#!/usr/bin/env python3
"""
Segmented large-scene helpers for the 3DGS container.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
import os
import shutil

import numpy as np

from .colmap_loader import (
    COLMAPCamera,
    COLMAPImage,
    COLMAPPoint3D,
    qvec2rotmat,
    read_cameras_text,
    read_images_text,
    read_points3d_text,
)


@dataclass
class SegmentedProfile:
    name: str = "landscape_v1"
    max_tiles: int = 6
    max_cameras_per_tile: int = 220
    max_points_per_tile: int = 200_000
    min_cameras_per_tile: int = 80
    min_points_per_tile: int = 50_000
    overlap_ratio: float = 0.15
    camera_overlap_ratio: float = 0.01
    min_observation_fraction: float = 0.05
    default_iterations: int = 6000
    heavy_tile_iterations: int = 8000
    heavy_camera_threshold: int = 180
    heavy_point_threshold: int = 250_000


@dataclass(frozen=True)
class Bounds2D:
    minimum: np.ndarray
    maximum: np.ndarray

    @property
    def size(self) -> np.ndarray:
        return self.maximum - self.minimum

    def contains(self, coordinates: np.ndarray) -> np.ndarray:
        if coordinates.size == 0:
            return np.zeros((0,), dtype=bool)
        return np.all(
            (coordinates >= self.minimum[None, :]) & (coordinates <= self.maximum[None, :]),
            axis=1,
        )

    def expanded(self, margin: float) -> "Bounds2D":
        return Bounds2D(self.minimum - margin, self.maximum + margin)

    def expanded_per_axis(self, margins: np.ndarray) -> "Bounds2D":
        return Bounds2D(self.minimum - margins, self.maximum + margins)

    def to_dict(self) -> Dict[str, List[float]]:
        return {
            "minimum": self.minimum.astype(float).tolist(),
            "maximum": self.maximum.astype(float).tolist(),
        }


@dataclass(frozen=True)
class PlaneProjector:
    origin: np.ndarray
    basis_u: np.ndarray
    basis_v: np.ndarray
    basis_w: np.ndarray

    def project(self, xyz: np.ndarray) -> np.ndarray:
        centered = xyz - self.origin[None, :]
        return np.stack(
            (
                centered @ self.basis_u,
                centered @ self.basis_v,
            ),
            axis=1,
        )

    def project_points(self, xyz: np.ndarray) -> np.ndarray:
        if xyz.size == 0:
            return np.zeros((0, 2), dtype=np.float32)
        return self.project(xyz)

    def to_dict(self) -> Dict[str, List[float]]:
        return {
            "origin": self.origin.astype(float).tolist(),
            "basis_u": self.basis_u.astype(float).tolist(),
            "basis_v": self.basis_v.astype(float).tolist(),
            "basis_w": self.basis_w.astype(float).tolist(),
        }


@dataclass
class SparseScene:
    sparse_dir: Path
    images_dir: Path
    cameras: Dict[int, COLMAPCamera]
    images: Dict[int, COLMAPImage]
    points3d: Dict[int, COLMAPPoint3D]
    camera_centers: Dict[int, np.ndarray]
    image_observation_ids: Dict[int, List[int]]
    point_ids: List[int]
    point_xyz: np.ndarray
    point_id_to_index: Dict[int, int]
    image_ids: List[int]

    @classmethod
    def from_training_root(cls, training_root: Path) -> "SparseScene":
        sparse_dir = training_root / "sparse" / "0"
        cameras = read_cameras_text(sparse_dir / "cameras.txt")
        images = read_images_text(sparse_dir / "images.txt")
        points3d = read_points3d_text(sparse_dir / "points3D.txt")

        camera_centers: Dict[int, np.ndarray] = {}
        image_observation_ids: Dict[int, List[int]] = {}
        image_ids = sorted(images.keys())

        for image_id in image_ids:
            image = images[image_id]
            rotation = qvec2rotmat(image.qvec)
            center = -rotation.T @ image.tvec
            camera_centers[image_id] = center.astype(np.float64)

            observed_ids = [
                point_id
                for _, _, point_id in image.points2d
                if point_id != -1 and point_id in points3d
            ]
            image_observation_ids[image_id] = observed_ids

        point_ids = sorted(points3d.keys())
        point_xyz = (
            np.array([points3d[point_id].xyz for point_id in point_ids], dtype=np.float64)
            if point_ids
            else np.zeros((0, 3), dtype=np.float64)
        )
        point_id_to_index = {point_id: index for index, point_id in enumerate(point_ids)}

        return cls(
            sparse_dir=sparse_dir,
            images_dir=training_root / "images",
            cameras=cameras,
            images=images,
            points3d=points3d,
            camera_centers=camera_centers,
            image_observation_ids=image_observation_ids,
            point_ids=point_ids,
            point_xyz=point_xyz,
            point_id_to_index=point_id_to_index,
            image_ids=image_ids,
        )


@dataclass
class TileSpec:
    tile_id: str
    core_bounds: Bounds2D
    expanded_bounds: Bounds2D
    core_point_ids: List[int]
    expanded_point_ids: List[int]
    image_ids: List[int]
    core_center_image_ids: List[int]
    camera_ids: List[int]
    iterations: int

    def to_manifest_entry(self) -> Dict[str, object]:
        return {
            "tile_id": self.tile_id,
            "core_bounds": self.core_bounds.to_dict(),
            "expanded_bounds": self.expanded_bounds.to_dict(),
            "core_point_count": len(self.core_point_ids),
            "expanded_point_count": len(self.expanded_point_ids),
            "image_count": len(self.image_ids),
            "core_center_image_count": len(self.core_center_image_ids),
            "camera_ids": self.camera_ids,
            "iterations": self.iterations,
        }


@dataclass
class TileDatasetPaths:
    root: Path
    sparse_dir: Path
    images_dir: Path


def load_profile(name: str) -> SegmentedProfile:
    if name != "landscape_v1":
        raise ValueError(f"Unsupported segmented profile: {name}")
    return SegmentedProfile()


def fit_ground_plane(scene: SparseScene) -> PlaneProjector:
    cloud_parts: List[np.ndarray] = []
    if scene.point_xyz.size:
        cloud_parts.append(scene.point_xyz)
    if scene.camera_centers:
        cloud_parts.append(np.array(list(scene.camera_centers.values()), dtype=np.float64))
    if not cloud_parts:
        raise ValueError("Scene has no sparse points or camera centers")

    stacked = np.concatenate(cloud_parts, axis=0)
    origin = stacked.mean(axis=0)
    centered = stacked - origin[None, :]
    _, _, vh = np.linalg.svd(centered, full_matrices=False)

    basis_u = vh[0] / np.linalg.norm(vh[0])
    basis_v = vh[1] / np.linalg.norm(vh[1])
    basis_w = np.cross(basis_u, basis_v)
    basis_w /= np.linalg.norm(basis_w)

    return PlaneProjector(origin=origin, basis_u=basis_u, basis_v=basis_v, basis_w=basis_w)


def build_tiles(scene: SparseScene, profile: SegmentedProfile) -> Tuple[PlaneProjector, List[TileSpec], Dict[str, object]]:
    projector = fit_ground_plane(scene)
    point_uv = projector.project_points(scene.point_xyz)
    camera_uv = projector.project_points(
        np.array([scene.camera_centers[image_id] for image_id in scene.image_ids], dtype=np.float64)
    )

    if point_uv.size and camera_uv.size:
        reference_uv = np.concatenate([point_uv, camera_uv], axis=0)
    else:
        reference_uv = point_uv if point_uv.size else camera_uv
    if reference_uv.size == 0:
        raise ValueError("Cannot build tiles without points or cameras")

    root_bounds = Bounds2D(reference_uv.min(axis=0), reference_uv.max(axis=0))

    partition_bounds = _partition_bounds(point_uv, camera_uv, root_bounds, profile)
    tiles = _assign_tiles(scene, point_uv, camera_uv, partition_bounds, profile)

    orphan_images = sorted(
        image_id
        for image_id in scene.image_ids
        if not any(image_id in tile.image_ids for tile in tiles)
    )
    if orphan_images:
        raise ValueError(f"Registered cameras were not assigned to any tile: {orphan_images[:10]}")

    summary = {
        "profile": asdict(profile),
        "tile_count": len(tiles),
        "orphan_image_count": 0,
        "projector": projector.to_dict(),
    }
    return projector, tiles, summary


def _partition_bounds(
    point_uv: np.ndarray,
    camera_uv: np.ndarray,
    root_bounds: Bounds2D,
    profile: SegmentedProfile,
) -> List[Bounds2D]:
    tiles = [root_bounds]
    unsplittable: set[int] = set()

    while len(tiles) < profile.max_tiles:
        candidate_index = _select_split_candidate(tiles, point_uv, camera_uv, profile, unsplittable)
        if candidate_index is None:
            break

        child_bounds = _split_bounds(tiles[candidate_index], point_uv, camera_uv, profile)
        if not child_bounds:
            unsplittable.add(candidate_index)
            continue

        tiles = tiles[:candidate_index] + child_bounds + tiles[candidate_index + 1 :]
        unsplittable = set()

    return tiles


def _select_split_candidate(
    tiles: Sequence[Bounds2D],
    point_uv: np.ndarray,
    camera_uv: np.ndarray,
    profile: SegmentedProfile,
    unsplittable: set[int],
) -> Optional[int]:
    best_index: Optional[int] = None
    best_overload = 1.0

    for index, bounds in enumerate(tiles):
        if index in unsplittable:
            continue
        point_count = int(bounds.contains(point_uv).sum())
        camera_count = int(bounds.contains(camera_uv).sum())
        overload = max(
            point_count / max(profile.max_points_per_tile, 1),
            camera_count / max(profile.max_cameras_per_tile, 1),
        )
        if overload > best_overload:
            best_overload = overload
            best_index = index

    return best_index


def _split_bounds(
    bounds: Bounds2D,
    point_uv: np.ndarray,
    camera_uv: np.ndarray,
    profile: SegmentedProfile,
) -> Optional[List[Bounds2D]]:
    point_mask = bounds.contains(point_uv)
    camera_mask = bounds.contains(camera_uv)

    if not point_mask.any() and not camera_mask.any():
        return None

    side_lengths = bounds.size
    axis = int(np.argmax(side_lengths))
    reference = point_uv[point_mask, axis] if point_mask.any() else camera_uv[camera_mask, axis]

    split_value = float(np.median(reference))
    if split_value <= bounds.minimum[axis] or split_value >= bounds.maximum[axis]:
        return None

    left_min = bounds.minimum.copy()
    left_max = bounds.maximum.copy()
    left_max[axis] = split_value

    right_min = bounds.minimum.copy()
    right_min[axis] = split_value
    right_max = bounds.maximum.copy()

    children = [Bounds2D(left_min, left_max), Bounds2D(right_min, right_max)]

    for child in children:
        child_point_count = int(child.contains(point_uv).sum())
        child_camera_count = int(child.contains(camera_uv).sum())
        if child_point_count < profile.min_points_per_tile:
            return None
        if child_camera_count < profile.min_cameras_per_tile:
            return None

    return children


def _assign_tiles(
    scene: SparseScene,
    point_uv: np.ndarray,
    camera_uv: np.ndarray,
    partition_bounds: Sequence[Bounds2D],
    profile: SegmentedProfile,
) -> List[TileSpec]:
    tiles: List[TileSpec] = []
    image_index_lookup = {image_id: index for index, image_id in enumerate(scene.image_ids)}

    for tile_index, core_bounds in enumerate(partition_bounds):
        axis_margins = np.maximum(core_bounds.size * profile.overlap_ratio, 1e-6)
        expanded_bounds = core_bounds.expanded_per_axis(axis_margins)

        core_point_ids = [
            scene.point_ids[index]
            for index in np.where(core_bounds.contains(point_uv))[0].tolist()
        ]
        expanded_point_ids = [
            scene.point_ids[index]
            for index in np.where(expanded_bounds.contains(point_uv))[0].tolist()
        ]

        center_image_ids = [
            scene.image_ids[index]
            for index in np.where(core_bounds.contains(camera_uv))[0].tolist()
        ]

        if center_image_ids:
            center_indices = [image_index_lookup[image_id] for image_id in center_image_ids]
            center_camera_uv = camera_uv[center_indices]
            camera_bounds = Bounds2D(center_camera_uv.min(axis=0), center_camera_uv.max(axis=0))
            camera_margins = np.maximum(camera_bounds.size * profile.camera_overlap_ratio, 1e-6)
            expanded_camera_bounds = camera_bounds.expanded_per_axis(camera_margins)
        else:
            expanded_camera_bounds = core_bounds

        image_ids = [
            scene.image_ids[index]
            for index in np.where(expanded_camera_bounds.contains(camera_uv))[0].tolist()
        ]

        if len(image_ids) < profile.min_cameras_per_tile:
            assigned_image_ids = set(image_ids)
            core_point_id_set = set(core_point_ids)
            for image_id in scene.image_ids:
                if image_id in assigned_image_ids:
                    continue

                observed_point_ids = scene.image_observation_ids.get(image_id, [])
                if not observed_point_ids:
                    continue

                observed_in_tile = sum(1 for point_id in observed_point_ids if point_id in core_point_id_set)
                if observed_in_tile / len(observed_point_ids) >= profile.min_observation_fraction:
                    image_ids.append(image_id)
                    assigned_image_ids.add(image_id)

        if not image_ids:
            raise ValueError(f"Tile {tile_index} has no assigned images")

        camera_ids = sorted({scene.images[image_id].camera_id for image_id in image_ids})
        iterations = (
            profile.heavy_tile_iterations
            if len(image_ids) > profile.heavy_camera_threshold or len(core_point_ids) > profile.heavy_point_threshold
            else profile.default_iterations
        )

        tiles.append(
            TileSpec(
                tile_id=f"tile_{tile_index:02d}",
                core_bounds=core_bounds,
                expanded_bounds=expanded_bounds,
                core_point_ids=core_point_ids,
                expanded_point_ids=expanded_point_ids,
                image_ids=sorted(image_ids),
                core_center_image_ids=sorted(center_image_ids),
                camera_ids=camera_ids,
                iterations=iterations,
            )
        )

    tiles.sort(key=lambda tile: tile.tile_id)
    return tiles


def write_tile_dataset(scene: SparseScene, tile: TileSpec, tile_root: Path) -> TileDatasetPaths:
    if tile_root.exists():
        shutil.rmtree(tile_root)
    sparse_dir = tile_root / "sparse" / "0"
    images_dir = tile_root / "images"
    sparse_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    image_id_set = set(tile.image_ids)
    valid_point_ids = _filter_valid_points(scene, tile, image_id_set)
    valid_camera_ids = sorted({scene.images[image_id].camera_id for image_id in tile.image_ids})

    _write_cameras(scene, valid_camera_ids, sparse_dir / "cameras.txt")
    _write_images(scene, tile.image_ids, valid_point_ids, sparse_dir / "images.txt")
    _write_points(scene, valid_point_ids, image_id_set, sparse_dir / "points3D.txt")
    _link_images(scene, tile.image_ids, images_dir)

    return TileDatasetPaths(root=tile_root, sparse_dir=sparse_dir, images_dir=images_dir)


def _filter_valid_points(scene: SparseScene, tile: TileSpec, image_id_set: set[int]) -> List[int]:
    valid_point_ids: List[int] = []
    for point_id in tile.expanded_point_ids:
        point = scene.points3d[point_id]
        track = [(image_id, point2d_id) for image_id, point2d_id in point.track if image_id in image_id_set]
        if len(track) >= 2:
            valid_point_ids.append(point_id)
    return valid_point_ids


def _write_cameras(scene: SparseScene, camera_ids: Iterable[int], destination: Path) -> None:
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write("# Camera list with one line of data per camera:\n")
        handle.write("# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
        for camera_id in sorted(camera_ids):
            camera = scene.cameras[camera_id]
            params = " ".join(str(param) for param in camera.params)
            handle.write(
                f"{camera.camera_id} {camera.model} {camera.width} {camera.height} {params}\n"
            )


def _write_images(
    scene: SparseScene,
    image_ids: Sequence[int],
    valid_point_ids: Sequence[int],
    destination: Path,
) -> None:
    valid_point_id_set = set(valid_point_ids)
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write("# Image list with two lines of data per image:\n")
        handle.write("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, IMAGE_NAME\n")
        handle.write("# POINTS2D[] as (X, Y, POINT3D_ID)\n")
        for image_id in image_ids:
            image = scene.images[image_id]
            qvec = " ".join(str(float(value)) for value in image.qvec.tolist())
            tvec = " ".join(str(float(value)) for value in image.tvec.tolist())
            handle.write(f"{image.image_id} {qvec} {tvec} {image.camera_id} {image.name}\n")

            point_tokens: List[str] = []
            for x, y, point_id in image.points2d:
                point_tokens.extend(
                    [
                        str(float(x)),
                        str(float(y)),
                        str(point_id if point_id in valid_point_id_set else -1),
                    ]
                )
            handle.write(" ".join(point_tokens) + "\n")


def _write_points(
    scene: SparseScene,
    point_ids: Sequence[int],
    image_id_set: set[int],
    destination: Path,
) -> None:
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write("# 3D point list with one line of data per point:\n")
        handle.write("# POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
        for point_id in point_ids:
            point = scene.points3d[point_id]
            track = [(image_id, point2d_id) for image_id, point2d_id in point.track if image_id in image_id_set]
            if len(track) < 2:
                continue

            xyz = " ".join(str(float(value)) for value in point.xyz.tolist())
            rgb = " ".join(str(int(value)) for value in point.rgb.tolist())
            track_tokens = " ".join(f"{image_id} {point2d_id}" for image_id, point2d_id in track)
            handle.write(f"{point.point3d_id} {xyz} {rgb} {float(point.error)} {track_tokens}\n")


def _link_images(scene: SparseScene, image_ids: Sequence[int], destination_dir: Path) -> None:
    for image_id in image_ids:
        image_name = scene.images[image_id].name
        source_path = scene.images_dir / image_name
        destination_path = destination_dir / image_name
        if destination_path.exists():
            continue
        try:
            os.link(source_path, destination_path)
        except OSError:
            try:
                os.symlink(source_path, destination_path)
            except OSError:
                with open(source_path, "rb") as source_handle, open(destination_path, "wb") as destination_handle:
                    destination_handle.write(source_handle.read())
