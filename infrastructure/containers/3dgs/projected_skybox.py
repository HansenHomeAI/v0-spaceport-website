#!/usr/bin/env python3
"""
Projected-photo skybox composition for Nerfstudio datasets.

This compositor uses semantic sky masks to exclude sky from the foreground
trainer, then reuses those same separated sky pixels to build the deployed
equirectangular skybox. A low-frequency learned fill is only used where photo
coverage is missing, so there is a single export path instead of a fallback.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image, ImageFilter

try:
    import cv2
except ImportError:  # pragma: no cover - exercised in container/runtime.
    cv2 = None


@dataclass(frozen=True)
class ProjectedSkyboxSettings:
    enabled: bool = True
    composition_mode: str = "projected_photo_low_frequency"
    world_up_source: str = "colmap_pose_consensus"
    min_sky_mask_ratio: float = 0.01
    min_observations_per_pixel: int = 1
    blend_edge_feather_px: int = 24
    low_frequency_fill: bool = True
    training_mask_mode: str = "exclude_sky"
    projection_max_long_side: int = 1024


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-8:
        return vector.astype(np.float32)
    return (vector / norm).astype(np.float32)


def _load_transforms(data_dir: Path) -> dict[str, Any]:
    with open(data_dir / "transforms.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_frame_path(data_dir: Path, relative_path: str) -> Path:
    stripped = str(relative_path).lstrip("./")
    direct = (data_dir / stripped).resolve()
    if direct.exists():
        return direct
    nested = (data_dir / Path(stripped).name).resolve()
    if nested.exists():
        return nested
    return direct


def _frame_intrinsics(frame: dict[str, Any], transforms: dict[str, Any]) -> tuple[float, float, float, float, int, int]:
    width = int(frame.get("w", transforms.get("w")))
    height = int(frame.get("h", transforms.get("h")))
    fx = float(frame.get("fl_x", transforms.get("fl_x")))
    fy = float(frame.get("fl_y", transforms.get("fl_y")))
    cx = float(frame.get("cx", transforms.get("cx", width / 2.0)))
    cy = float(frame.get("cy", transforms.get("cy", height / 2.0)))
    return fx, fy, cx, cy, width, height


def derive_sky_mask_from_training_mask(training_mask: np.ndarray, training_mask_mode: str) -> np.ndarray:
    binary_keep = np.asarray(training_mask, dtype=np.uint8) >= 128
    if training_mask_mode == "exclude_sky":
        return ~binary_keep
    if training_mask_mode == "keep_sky":
        return binary_keep
    raise ValueError(f"Unsupported training mask mode: {training_mask_mode}")


def build_projection_basis(frames: list[dict[str, Any]]) -> dict[str, Any]:
    if not frames:
        raise RuntimeError("No frames available for projected skybox composition")

    up_vectors: list[np.ndarray] = []
    forward_vectors: list[np.ndarray] = []
    up_reference: Optional[np.ndarray] = None

    for frame in frames:
        c2w = np.asarray(frame["transform_matrix"], dtype=np.float32)
        up = _normalize(c2w[:3, 1])
        if up_reference is None:
            up_reference = up
        elif float(np.dot(up, up_reference)) < 0.0:
            up = -up
        up_vectors.append(up)

    up_consensus = _normalize(np.mean(np.stack(up_vectors, axis=0), axis=0))

    forward_reference: Optional[np.ndarray] = None
    for frame in frames:
        c2w = np.asarray(frame["transform_matrix"], dtype=np.float32)
        forward = _normalize(-c2w[:3, 2])
        horizontal = forward - (np.dot(forward, up_consensus) * up_consensus)
        if float(np.linalg.norm(horizontal)) <= 1e-6:
            continue
        horizontal = _normalize(horizontal)
        if forward_reference is None:
            forward_reference = horizontal
        elif float(np.dot(horizontal, forward_reference)) < 0.0:
            horizontal = -horizontal
        forward_vectors.append(horizontal)

    if not forward_vectors:
        fallback = np.cross(np.array([0.0, 0.0, 1.0], dtype=np.float32), up_consensus)
        if float(np.linalg.norm(fallback)) <= 1e-6:
            fallback = np.cross(np.array([1.0, 0.0, 0.0], dtype=np.float32), up_consensus)
        forward_consensus = _normalize(np.cross(up_consensus, fallback))
    else:
        forward_consensus = _normalize(np.mean(np.stack(forward_vectors, axis=0), axis=0))

    right = _normalize(np.cross(forward_consensus, up_consensus))
    forward_consensus = _normalize(np.cross(up_consensus, right))
    world_to_sky = np.stack([right, up_consensus, forward_consensus], axis=0)

    return {
        "world_to_sky": world_to_sky,
        "right": right,
        "up": up_consensus,
        "forward": forward_consensus,
    }


def world_dirs_to_equirectangular(
    world_directions: np.ndarray,
    world_to_sky: np.ndarray,
    width: int,
    height: int,
) -> tuple[np.ndarray, np.ndarray]:
    local = (world_to_sky @ world_directions.T).T
    local = local / np.clip(np.linalg.norm(local, axis=1, keepdims=True), 1e-8, None)
    theta = np.arctan2(local[:, 0], local[:, 2])
    phi = np.arcsin(np.clip(local[:, 1], -1.0, 1.0))
    xs = ((theta / (2.0 * np.pi)) + 0.5) * width - 0.5
    ys = (0.5 - (phi / np.pi)) * height - 0.5
    return xs.astype(np.float32), ys.astype(np.float32)


def build_low_frequency_fill(fill_rgb: np.ndarray) -> np.ndarray:
    image = Image.fromarray((np.clip(fill_rgb, 0.0, 1.0) * 255.0).round().astype(np.uint8), mode="RGB")
    reduced_width = max(32, image.width // 8)
    reduced_height = max(16, image.height // 8)
    reduced = image.resize((reduced_width, reduced_height), resample=Image.Resampling.BILINEAR)
    blurred = reduced.filter(ImageFilter.GaussianBlur(radius=4))
    expanded = blurred.resize(image.size, resample=Image.Resampling.BILINEAR)
    return np.asarray(expanded, dtype=np.float32) / 255.0


def _resize_for_projection(
    rgb: np.ndarray,
    sky_mask: np.ndarray,
    confidence: Optional[np.ndarray],
    intrinsics: tuple[float, float, float, float, int, int],
    max_long_side: int,
) -> tuple[np.ndarray, np.ndarray, Optional[np.ndarray], tuple[float, float, float, float, int, int], float]:
    fx, fy, cx, cy, width, height = intrinsics
    scale = min(1.0, float(max_long_side) / float(max(width, height, 1)))
    if scale >= 0.999:
        return rgb, sky_mask, confidence, intrinsics, 1.0

    target_width = max(1, int(round(width * scale)))
    target_height = max(1, int(round(height * scale)))

    rgb_image = Image.fromarray((np.clip(rgb, 0.0, 1.0) * 255.0).round().astype(np.uint8), mode="RGB")
    resized_rgb = np.asarray(
        rgb_image.resize((target_width, target_height), resample=Image.Resampling.BILINEAR),
        dtype=np.float32,
    ) / 255.0
    mask_image = Image.fromarray((sky_mask.astype(np.uint8) * 255), mode="L")
    resized_mask = np.asarray(
        mask_image.resize((target_width, target_height), resample=Image.Resampling.NEAREST),
        dtype=np.uint8,
    ) >= 128
    resized_confidence = None
    if confidence is not None:
        confidence_image = Image.fromarray((np.clip(confidence, 0.0, 1.0) * 255.0).round().astype(np.uint8), mode="L")
        resized_confidence = (
            np.asarray(
                confidence_image.resize((target_width, target_height), resample=Image.Resampling.BILINEAR),
                dtype=np.float32,
            )
            / 255.0
        )

    scaled_intrinsics = (
        fx * scale,
        fy * scale,
        cx * scale,
        cy * scale,
        target_width,
        target_height,
    )
    return resized_rgb, resized_mask, resized_confidence, scaled_intrinsics, scale


def _edge_feather_weights(sky_mask: np.ndarray, feather_px: int) -> np.ndarray:
    if feather_px <= 0 or cv2 is None:
        return sky_mask.astype(np.float32)
    distance = cv2.distanceTransform(sky_mask.astype(np.uint8), cv2.DIST_L2, 3)
    return np.clip(distance / float(feather_px), 0.0, 1.0).astype(np.float32)


def _center_weights(width: int, height: int) -> np.ndarray:
    xs = (np.arange(width, dtype=np.float32) + 0.5 - (width / 2.0)) / max(width / 2.0, 1.0)
    ys = (np.arange(height, dtype=np.float32) + 0.5 - (height / 2.0)) / max(height / 2.0, 1.0)
    grid_x, grid_y = np.meshgrid(xs, ys, indexing="xy")
    radial = np.sqrt((grid_x ** 2) + (grid_y ** 2))
    return np.clip(1.0 - (0.6 * radial), 0.1, 1.0).astype(np.float32)


def _camera_rays_for_pixels(
    xs: np.ndarray,
    ys: np.ndarray,
    intrinsics: tuple[float, float, float, float, int, int],
    c2w: np.ndarray,
) -> np.ndarray:
    fx, fy, cx, cy, _, _ = intrinsics
    x_camera = (xs - cx) / max(fx, 1e-6)
    y_camera = (ys - cy) / max(fy, 1e-6)
    camera_dirs = np.stack([x_camera, y_camera, -np.ones_like(x_camera)], axis=1).astype(np.float32)
    camera_dirs /= np.clip(np.linalg.norm(camera_dirs, axis=1, keepdims=True), 1e-8, None)
    return (c2w[:3, :3] @ camera_dirs.T).T.astype(np.float32)


def _accumulate_bilinear(
    xs: np.ndarray,
    ys: np.ndarray,
    colors: np.ndarray,
    weights: np.ndarray,
    width: int,
    height: int,
    color_accum: np.ndarray,
    weight_accum: np.ndarray,
    support_accum: np.ndarray,
) -> None:
    x0 = np.floor(xs).astype(np.int32)
    y0 = np.floor(ys).astype(np.int32)
    dx = (xs - x0).astype(np.float32)
    dy = (ys - y0).astype(np.float32)
    nearest_x = np.mod(np.round(xs).astype(np.int32), width)
    nearest_y = np.clip(np.round(ys).astype(np.int32), 0, height - 1)
    np.add.at(support_accum, (nearest_y, nearest_x), 1.0)

    for offset_x, offset_y, contribution in (
        (0, 0, (1.0 - dx) * (1.0 - dy)),
        (1, 0, dx * (1.0 - dy)),
        (0, 1, (1.0 - dx) * dy),
        (1, 1, dx * dy),
    ):
        dest_x = np.mod(x0 + offset_x, width)
        dest_y = y0 + offset_y
        valid = (dest_y >= 0) & (dest_y < height) & (contribution > 0.0)
        if not np.any(valid):
            continue
        weighted = weights[valid] * contribution[valid]
        np.add.at(weight_accum, (dest_y[valid], dest_x[valid]), weighted)
        for channel in range(3):
            np.add.at(
                color_accum[..., channel],
                (dest_y[valid], dest_x[valid]),
                colors[valid, channel] * weighted,
            )


def build_projected_photo_skybox(
    data_dir: Path,
    output_dir: Path,
    width: int,
    height: int,
    quality: int,
    fill_rgb: np.ndarray,
    settings: ProjectedSkyboxSettings,
) -> dict[str, Any]:
    transforms = _load_transforms(data_dir)
    frames = transforms.get("frames", [])
    basis = build_projection_basis(frames)
    world_to_sky = basis["world_to_sky"]

    color_accum = np.zeros((height, width, 3), dtype=np.float32)
    weight_accum = np.zeros((height, width), dtype=np.float32)
    support_accum = np.zeros((height, width), dtype=np.float32)
    contributing_frames = 0
    sampled_frames = 0

    for frame in frames:
        mask_path = frame.get("mask_path")
        if not mask_path:
            continue
        image_path = _resolve_frame_path(data_dir, str(frame["file_path"]))
        training_mask_path = _resolve_frame_path(data_dir, str(mask_path))
        if not image_path.exists() or not training_mask_path.exists():
            continue

        rgb = np.asarray(Image.open(image_path).convert("RGB"), dtype=np.float32) / 255.0
        training_mask = np.asarray(Image.open(training_mask_path).convert("L"), dtype=np.uint8)
        sky_mask = derive_sky_mask_from_training_mask(training_mask, settings.training_mask_mode)
        sky_ratio = float(sky_mask.mean()) if sky_mask.size else 0.0
        if sky_ratio < float(settings.min_sky_mask_ratio):
            continue

        confidence = None
        confidence_path = frame.get("semantic_sky_confidence_path")
        if confidence_path:
            resolved_confidence = _resolve_frame_path(data_dir, str(confidence_path))
            if resolved_confidence.exists():
                confidence = (
                    np.asarray(Image.open(resolved_confidence).convert("L"), dtype=np.float32)
                    / 255.0
                )

        intrinsics = _frame_intrinsics(frame, transforms)
        rgb, sky_mask, confidence, intrinsics, _ = _resize_for_projection(
            rgb=rgb,
            sky_mask=sky_mask,
            confidence=confidence,
            intrinsics=intrinsics,
            max_long_side=int(settings.projection_max_long_side),
        )
        sampled_frames += 1
        active = np.flatnonzero(sky_mask.reshape(-1))
        if active.size == 0:
            continue

        height_local, width_local = sky_mask.shape
        grid_x, grid_y = np.meshgrid(
            np.arange(width_local, dtype=np.float32) + 0.5,
            np.arange(height_local, dtype=np.float32) + 0.5,
            indexing="xy",
        )
        pixel_x = grid_x.reshape(-1)[active]
        pixel_y = grid_y.reshape(-1)[active]
        colors = rgb.reshape(-1, 3)[active]

        edge_weights = _edge_feather_weights(sky_mask, int(settings.blend_edge_feather_px)).reshape(-1)[active]
        center_weights = _center_weights(width_local, height_local).reshape(-1)[active]
        if confidence is not None:
            confidence_weights = np.clip(confidence.reshape(-1)[active], 0.0, 1.0)
        else:
            confidence_weights = np.ones_like(center_weights, dtype=np.float32)

        combined_weights = edge_weights * center_weights * np.clip(confidence_weights, 0.05, 1.0)
        active_weight_mask = combined_weights > 1e-4
        if not np.any(active_weight_mask):
            continue

        contributing_frames += 1
        world_dirs = _camera_rays_for_pixels(
            xs=pixel_x[active_weight_mask],
            ys=pixel_y[active_weight_mask],
            intrinsics=intrinsics,
            c2w=np.asarray(frame["transform_matrix"], dtype=np.float32),
        )
        eq_x, eq_y = world_dirs_to_equirectangular(
            world_directions=world_dirs,
            world_to_sky=world_to_sky,
            width=width,
            height=height,
        )
        _accumulate_bilinear(
            xs=eq_x,
            ys=eq_y,
            colors=colors[active_weight_mask],
            weights=combined_weights[active_weight_mask],
            width=width,
            height=height,
            color_accum=color_accum,
            weight_accum=weight_accum,
            support_accum=support_accum,
        )

    observed_mask = support_accum >= float(max(settings.min_observations_per_pixel, 1))
    safe_weights = np.clip(weight_accum[..., None], 1e-6, None)
    observed_rgb = color_accum / safe_weights
    fill_base = build_low_frequency_fill(fill_rgb) if settings.low_frequency_fill else np.clip(fill_rgb, 0.0, 1.0)
    final_rgb = fill_base.copy()
    final_rgb[observed_mask] = np.clip(observed_rgb[observed_mask], 0.0, 1.0)

    skybox_path = output_dir / "background_skybox.webp"
    Image.fromarray((final_rgb * 255.0).round().astype(np.uint8), mode="RGB").save(
        skybox_path,
        format="WEBP",
        quality=quality,
        method=6,
    )
    Image.fromarray((np.clip(observed_rgb, 0.0, 1.0) * 255.0).round().astype(np.uint8), mode="RGB").save(
        output_dir / "background_skybox_observed.webp",
        format="WEBP",
        quality=min(quality, 90),
        method=6,
    )
    Image.fromarray((fill_base * 255.0).round().astype(np.uint8), mode="RGB").save(
        output_dir / "background_skybox_fill.webp",
        format="WEBP",
        quality=min(quality, 90),
        method=6,
    )
    normalized_coverage = np.clip(support_accum / np.maximum(support_accum.max(), 1.0), 0.0, 1.0)
    Image.fromarray((normalized_coverage * 255.0).round().astype(np.uint8), mode="L").save(
        output_dir / "background_skybox_coverage.png"
    )

    manifest = {
        "version": 2,
        "asset": skybox_path.name,
        "width": width,
        "height": height,
        "background_skybox_generation_method": settings.composition_mode,
        "projection_mode": settings.composition_mode,
        "world_up_source": settings.world_up_source,
        "training_mask_mode": settings.training_mask_mode,
        "min_sky_mask_ratio": float(settings.min_sky_mask_ratio),
        "min_observations_per_pixel": int(settings.min_observations_per_pixel),
        "blend_edge_feather_px": int(settings.blend_edge_feather_px),
        "projection_max_long_side": int(settings.projection_max_long_side),
        "low_frequency_fill": bool(settings.low_frequency_fill),
        "observed_coverage_ratio": float(observed_mask.mean()) if observed_mask.size else 0.0,
        "filled_coverage_ratio": float(1.0 - observed_mask.mean()) if observed_mask.size else 1.0,
        "contributing_frame_count": int(contributing_frames),
        "sampled_frame_count": int(sampled_frames),
        "alignment_basis": {
            "right": basis["right"].tolist(),
            "up": basis["up"].tolist(),
            "forward": basis["forward"].tolist(),
        },
    }
    (output_dir / "background_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
