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

from semantic_sky_masks import keep_top_connected_components

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
    projection_mask_mode: str = "semantic_horizon_fill"
    projection_confidence_threshold: float = 0.25
    projection_horizon_smoothing_px: int = 31
    photometric_alignment_strength: float = 0.65
    base_saturation_scale: float = 0.78
    detail_luma_strength: float = 0.85
    detail_chroma_strength: float = 0.12
    detail_horizon_margin_px: int = 24
    detail_mask_erosion_px: int = 3
    min_projected_elevation: float = 0.0
    observed_blur_radius_px: int = 20
    detail_blur_radius_px: int = 10
    fill_edge_horizontal_blur_px: int = 40
    fill_edge_vertical_blur_px: int = 120
    seam_blend_width_px: int = 56
    detail_boundary_fade_px: int = 32
    detail_negative_luma_scale: float = 0.18


@dataclass
class PreparedProjectionFrame:
    c2w: np.ndarray
    intrinsics: tuple[float, float, float, float, int, int]
    rgb: np.ndarray
    projection_mask: np.ndarray
    detail_mask: np.ndarray
    confidence: Optional[np.ndarray]
    semantic_mask_ratio: float
    projection_mask_ratio: float
    detail_mask_ratio: float
    sky_median_rgb: Optional[np.ndarray]


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-8:
        return vector.astype(np.float32)
    return (vector / norm).astype(np.float32)


def _luminance(rgb: np.ndarray) -> np.ndarray:
    rgb_array = np.asarray(rgb, dtype=np.float32)
    return (
        (0.2126 * rgb_array[..., 0])
        + (0.7152 * rgb_array[..., 1])
        + (0.0722 * rgb_array[..., 2])
    ).astype(np.float32)


def _scale_saturation(rgb: np.ndarray, scale: float) -> np.ndarray:
    rgb_array = np.asarray(rgb, dtype=np.float32)
    luma = _luminance(rgb_array)[..., None]
    return np.clip(luma + ((rgb_array - luma) * float(scale)), 0.0, 1.0).astype(np.float32)


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


def _odd_kernel_size(kernel_size: int, max_size: int) -> int:
    kernel = max(1, int(kernel_size))
    limit = max(1, int(max_size))
    if limit % 2 == 0:
        limit = max(1, limit - 1)
    kernel = min(kernel, limit)
    if kernel % 2 == 0:
        kernel = max(1, kernel - 1)
    return kernel


def _smooth_horizon_series(values: np.ndarray, kernel_size: int) -> np.ndarray:
    if values.size <= 1:
        return values.astype(np.float32)
    kernel = _odd_kernel_size(kernel_size, values.size)
    if kernel <= 1:
        return values.astype(np.float32)
    pad = kernel // 2
    padded = np.pad(values.astype(np.float32), (pad, pad), mode="edge")
    weights = np.full(kernel, 1.0 / float(kernel), dtype=np.float32)
    return np.convolve(padded, weights, mode="valid").astype(np.float32)


def derive_projection_sky_mask(
    sky_mask: np.ndarray,
    confidence: Optional[np.ndarray],
    confidence_threshold: float,
    horizon_smoothing_px: int,
    projection_mask_mode: str,
) -> np.ndarray:
    binary_sky = np.asarray(sky_mask, dtype=bool)
    normalized_mode = str(projection_mask_mode).strip().lower()
    if normalized_mode == "semantic_mask_only":
        return binary_sky
    if normalized_mode != "semantic_horizon_fill":
        raise ValueError(f"Unsupported projection mask mode: {projection_mask_mode}")

    seed_mask = binary_sky.copy()
    if confidence is not None:
        seed_mask |= np.asarray(confidence, dtype=np.float32) >= float(confidence_threshold)
    seed_mask = keep_top_connected_components(seed_mask).astype(bool)
    if not np.any(seed_mask):
        return binary_sky

    height, width = seed_mask.shape
    horizon_rows = np.full(width, np.nan, dtype=np.float32)
    active_columns = np.flatnonzero(seed_mask.any(axis=0))
    if active_columns.size == 0:
        return binary_sky

    for column in active_columns:
        ys = np.flatnonzero(seed_mask[:, column])
        if ys.size == 0:
            continue
        horizon_rows[column] = float(np.quantile(ys.astype(np.float32), 0.95))

    start_column = int(active_columns[0])
    end_column = int(active_columns[-1])
    interpolated_columns = np.arange(start_column, end_column + 1, dtype=np.float32)
    interpolated_rows = np.interp(
        interpolated_columns,
        active_columns.astype(np.float32),
        horizon_rows[active_columns].astype(np.float32),
    )
    smoothed_rows = _smooth_horizon_series(interpolated_rows, int(horizon_smoothing_px))

    projection_mask = np.zeros_like(seed_mask, dtype=bool)
    row_indices = np.arange(height, dtype=np.float32)[:, None]
    projection_mask[:, start_column : end_column + 1] = row_indices <= smoothed_rows[None, :]
    projection_mask |= seed_mask
    projection_mask = keep_top_connected_components(projection_mask).astype(bool)
    return projection_mask


def _erode_binary_mask(binary_mask: np.ndarray, erosion_px: int) -> np.ndarray:
    mask = np.asarray(binary_mask, dtype=bool)
    if erosion_px <= 0 or not np.any(mask):
        return mask

    radius = max(1, int(erosion_px))
    if cv2 is not None:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1))
        eroded = cv2.erode(mask.astype(np.uint8), kernel, iterations=1)
        return eroded.astype(bool)

    filter_size = max(3, (radius * 2) + 1)
    if filter_size % 2 == 0:
        filter_size += 1
    image = Image.fromarray(mask.astype(np.uint8) * 255, mode="L")
    eroded = image.filter(ImageFilter.MinFilter(size=filter_size))
    return (np.asarray(eroded, dtype=np.uint8) >= 128)


def derive_detail_sky_mask(
    sky_mask: np.ndarray,
    projection_mask: np.ndarray,
    confidence: Optional[np.ndarray],
    confidence_threshold: float,
    horizon_margin_px: int,
    erosion_px: int,
) -> np.ndarray:
    detail_mask = np.asarray(sky_mask, dtype=bool).copy()
    if confidence is not None:
        detail_mask &= np.asarray(confidence, dtype=np.float32) >= float(max(confidence_threshold, 0.35))
    if not np.any(detail_mask):
        return detail_mask

    height, width = detail_mask.shape
    margin = max(0, int(horizon_margin_px))
    if margin > 0:
        horizon_rows = np.full(width, np.nan, dtype=np.float32)
        active_columns = np.flatnonzero(np.asarray(projection_mask, dtype=bool).any(axis=0))
        for column in active_columns:
            ys = np.flatnonzero(projection_mask[:, column])
            if ys.size > 0:
                horizon_rows[column] = float(ys.max())

        valid_columns = np.flatnonzero(~np.isnan(horizon_rows))
        if valid_columns.size > 0:
            interpolated_rows = np.interp(
                np.arange(width, dtype=np.float32),
                valid_columns.astype(np.float32),
                horizon_rows[valid_columns].astype(np.float32),
                left=float(horizon_rows[valid_columns[0]]),
                right=float(horizon_rows[valid_columns[-1]]),
            )
            row_indices = np.arange(height, dtype=np.float32)[:, None]
            detail_mask &= row_indices <= np.maximum(interpolated_rows[None, :] - float(margin), 0.0)

    detail_mask = keep_top_connected_components(detail_mask).astype(bool)
    detail_mask = _erode_binary_mask(detail_mask, erosion_px)
    return keep_top_connected_components(detail_mask).astype(bool)


def build_projection_basis(frames: list[dict[str, Any]]) -> dict[str, Any]:
    if not frames:
        raise RuntimeError("No frames available for projected skybox composition")

    positions: list[np.ndarray] = []
    up_vectors: list[np.ndarray] = []
    forward_vectors: list[np.ndarray] = []
    up_reference: Optional[np.ndarray] = None

    for frame in frames:
        c2w = np.asarray(frame["transform_matrix"], dtype=np.float32)
        positions.append(np.asarray(c2w[:3, 3], dtype=np.float32))
        up = _normalize(c2w[:3, 1])
        if up_reference is None:
            up_reference = up
        elif float(np.dot(up, up_reference)) < 0.0:
            up = -up
        up_vectors.append(up)

    camera_up_consensus = _normalize(np.mean(np.stack(up_vectors, axis=0), axis=0))
    up_consensus = camera_up_consensus

    if len(positions) >= 3:
        positions_array = np.stack(positions, axis=0).astype(np.float32)
        centered_positions = positions_array - np.mean(positions_array, axis=0, keepdims=True)
        covariance = np.cov(centered_positions.T)
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        if eigenvalues.shape[0] >= 2 and float(eigenvalues[1]) > 1e-8:
            planarity_confidence = 1.0 - (float(eigenvalues[0]) / float(eigenvalues[1]))
            if planarity_confidence >= 0.15:
                position_normal = _normalize(eigenvectors[:, 0].astype(np.float32))
                if float(np.dot(position_normal, camera_up_consensus)) < 0.0:
                    position_normal = -position_normal
                up_consensus = position_normal

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


def _gaussian_blur_array(array: np.ndarray, radius_px: int) -> np.ndarray:
    array_f32 = np.asarray(array, dtype=np.float32)
    if radius_px <= 0:
        return array_f32
    if cv2 is not None:
        return cv2.GaussianBlur(
            array_f32,
            ksize=(0, 0),
            sigmaX=float(radius_px),
            sigmaY=float(radius_px),
            borderType=cv2.BORDER_REPLICATE,
        ).astype(np.float32)

    scale = float(max(np.max(array_f32), 1.0))
    if array_f32.ndim == 2:
        image = Image.fromarray((np.clip(array_f32 / scale, 0.0, 1.0) * 255.0).round().astype(np.uint8), mode="L")
        blurred = np.asarray(image.filter(ImageFilter.GaussianBlur(radius=float(radius_px))), dtype=np.float32) / 255.0
        return (blurred * scale).astype(np.float32)

    image = Image.fromarray((np.clip(array_f32 / scale, 0.0, 1.0) * 255.0).round().astype(np.uint8), mode="RGB")
    blurred = np.asarray(image.filter(ImageFilter.GaussianBlur(radius=float(radius_px))), dtype=np.float32) / 255.0
    return (blurred * scale).astype(np.float32)


def _gaussian_blur_array_anisotropic(
    array: np.ndarray,
    radius_x_px: int,
    radius_y_px: int,
) -> np.ndarray:
    array_f32 = np.asarray(array, dtype=np.float32)
    sigma_x = max(0, int(radius_x_px))
    sigma_y = max(0, int(radius_y_px))
    if sigma_x <= 0 and sigma_y <= 0:
        return array_f32
    if cv2 is not None:
        return cv2.GaussianBlur(
            array_f32,
            ksize=(0, 0),
            sigmaX=float(max(sigma_x, 1e-6)),
            sigmaY=float(max(sigma_y, 1e-6)),
            borderType=cv2.BORDER_REPLICATE,
        ).astype(np.float32)
    return _gaussian_blur_array(array_f32, max(sigma_x, sigma_y))


def _pad_equirectangular(array: np.ndarray, pad: int) -> np.ndarray:
    if pad <= 0:
        return np.asarray(array, dtype=np.float32)
    array_f32 = np.asarray(array, dtype=np.float32)
    wrapped = np.concatenate([array_f32[:, -pad:], array_f32, array_f32[:, :pad]], axis=1)
    if array_f32.ndim == 2:
        return np.pad(wrapped, ((pad, pad), (0, 0)), mode="edge").astype(np.float32)
    return np.pad(wrapped, ((pad, pad), (0, 0), (0, 0)), mode="edge").astype(np.float32)


def _blur_scalar_equirectangular(values: np.ndarray, radius_px: int) -> np.ndarray:
    scalar = np.asarray(values, dtype=np.float32)
    if radius_px <= 0:
        return scalar
    pad = min(
        scalar.shape[1],
        max(2, int(np.ceil(float(radius_px) * 2.5))),
    )
    padded = _pad_equirectangular(scalar, pad)
    blurred = _gaussian_blur_array(padded, radius_px)
    return blurred[pad:-pad, pad:-pad].astype(np.float32)


def _blur_equirectangular_anisotropic(
    values: np.ndarray,
    radius_x_px: int,
    radius_y_px: int,
) -> np.ndarray:
    scalar_or_rgb = np.asarray(values, dtype=np.float32)
    sigma_x = max(0, int(radius_x_px))
    sigma_y = max(0, int(radius_y_px))
    if sigma_x <= 0 and sigma_y <= 0:
        return scalar_or_rgb
    pad = min(
        scalar_or_rgb.shape[1],
        max(2, int(np.ceil(float(max(sigma_x, sigma_y, 1)) * 2.5))),
    )
    padded = _pad_equirectangular(scalar_or_rgb, pad)
    blurred = _gaussian_blur_array_anisotropic(padded, sigma_x, sigma_y)
    return blurred[pad:-pad, pad:-pad].astype(np.float32)


def _weighted_equirectangular_blur(
    rgb: np.ndarray,
    weights: np.ndarray,
    radius_px: int,
) -> tuple[np.ndarray, np.ndarray]:
    rgb_f32 = np.asarray(rgb, dtype=np.float32)
    weight_f32 = np.clip(np.asarray(weights, dtype=np.float32), 0.0, None)
    if radius_px <= 0:
        return np.clip(rgb_f32, 0.0, 1.0).astype(np.float32), weight_f32

    pad = min(
        rgb_f32.shape[1],
        max(2, int(np.ceil(float(radius_px) * 2.5))),
    )
    padded_rgb = _pad_equirectangular(rgb_f32 * weight_f32[..., None], pad)
    padded_weights = _pad_equirectangular(weight_f32, pad)
    blurred_rgb = _gaussian_blur_array(padded_rgb, radius_px)
    blurred_weights = _gaussian_blur_array(padded_weights, radius_px)
    cropped_rgb = blurred_rgb[pad:-pad, pad:-pad]
    cropped_weights = blurred_weights[pad:-pad, pad:-pad]
    normalized_rgb = cropped_rgb / np.clip(cropped_weights[..., None], 1e-6, None)
    return np.clip(normalized_rgb, 0.0, 1.0).astype(np.float32), np.clip(cropped_weights, 0.0, None).astype(np.float32)


def _nearest_valid_columns(valid_columns: np.ndarray, width: int) -> np.ndarray:
    all_columns = np.arange(width, dtype=np.int32)
    valid = np.asarray(valid_columns, dtype=np.int32)
    if valid.size == 0:
        return np.full(width, -1, dtype=np.int32)

    valid = np.unique(np.mod(valid, width))
    insert_left = np.searchsorted(valid, all_columns, side="left")
    next_columns = valid[np.mod(insert_left, valid.size)]
    previous_columns = valid[np.mod(insert_left - 1, valid.size)]
    next_distance = np.mod(next_columns - all_columns, width)
    previous_distance = np.mod(all_columns - previous_columns, width)
    choose_next = next_distance < previous_distance
    return np.where(choose_next, next_columns, previous_columns).astype(np.int32)


def _interpolate_circular_profile(
    profile: np.ndarray,
    valid_columns: np.ndarray,
    width: int,
) -> np.ndarray:
    valid = np.unique(np.mod(np.asarray(valid_columns, dtype=np.int32), max(width, 1)))
    profile_f32 = np.asarray(profile, dtype=np.float32)
    if valid.size == 0:
        raise ValueError("At least one valid column is required for circular interpolation")
    if valid.size == 1:
        if profile_f32.ndim == 1:
            return np.full(width, float(profile_f32[valid[0]]), dtype=np.float32)
        return np.repeat(profile_f32[valid[0] : valid[0] + 1, :], width, axis=0).astype(np.float32)

    sample_positions = valid.astype(np.float32)
    interp_positions = np.arange(width, dtype=np.float32)
    extended_positions = np.concatenate(
        [
            sample_positions[-1:] - float(width),
            sample_positions,
            sample_positions[:1] + float(width),
        ]
    ).astype(np.float32)

    if profile_f32.ndim == 1:
        samples = profile_f32[valid]
        extended_samples = np.concatenate([samples[-1:], samples, samples[:1]], axis=0)
        return np.interp(interp_positions, extended_positions, extended_samples).astype(np.float32)

    channels = profile_f32.shape[1]
    interpolated = np.zeros((width, channels), dtype=np.float32)
    for channel in range(channels):
        samples = profile_f32[valid, channel]
        extended_samples = np.concatenate([samples[-1:], samples, samples[:1]], axis=0)
        interpolated[:, channel] = np.interp(interp_positions, extended_positions, extended_samples).astype(np.float32)
    return interpolated.astype(np.float32)


def _smooth_circular_scalar_profile(values: np.ndarray, radius_px: int) -> np.ndarray:
    profile = np.asarray(values, dtype=np.float32)
    if profile.size <= 1 or radius_px <= 0:
        return profile
    return _blur_scalar_equirectangular(profile[None, :], radius_px=int(radius_px))[0].astype(np.float32)


def _smooth_circular_rgb_profile(values: np.ndarray, radius_px: int) -> np.ndarray:
    profile = np.asarray(values, dtype=np.float32)
    if profile.shape[0] <= 1 or radius_px <= 0:
        return profile
    return _blur_equirectangular_anisotropic(
        profile[None, :, :],
        radius_x_px=int(radius_px),
        radius_y_px=0,
    )[0].astype(np.float32)


def _interior_distance_fade(binary_mask: np.ndarray, fade_px: int) -> np.ndarray:
    mask = np.asarray(binary_mask, dtype=bool)
    if fade_px <= 0:
        return mask.astype(np.float32)
    if not np.any(mask):
        return np.zeros_like(mask, dtype=np.float32)

    if cv2 is not None:
        distance = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 3)
        return np.clip(distance / float(max(fade_px, 1)), 0.0, 1.0).astype(np.float32)

    eroded = mask.copy()
    fade = np.zeros_like(mask, dtype=np.float32)
    for step in range(1, max(1, int(fade_px)) + 1):
        eroded = _erode_binary_mask(eroded, 1)
        if not np.any(eroded):
            break
        fade[eroded] = np.maximum(fade[eroded], step / float(max(fade_px, 1)))
    fade[mask] = np.maximum(fade[mask], 1e-3)
    return np.clip(fade, 0.0, 1.0).astype(np.float32)


def _robust_median_rgb(rgb: np.ndarray, mask: np.ndarray) -> Optional[np.ndarray]:
    binary_mask = np.asarray(mask, dtype=bool)
    if not np.any(binary_mask):
        return None
    pixels = np.asarray(rgb, dtype=np.float32)[binary_mask]
    if pixels.size == 0:
        return None
    return np.median(pixels, axis=0).astype(np.float32)


def _apply_frame_alignment(
    rgb: np.ndarray,
    reference_mask: np.ndarray,
    target_rgb: Optional[np.ndarray],
    strength: float,
) -> tuple[np.ndarray, Optional[dict[str, Any]]]:
    if target_rgb is None or strength <= 1e-4:
        return np.asarray(rgb, dtype=np.float32), None
    current_rgb = _robust_median_rgb(rgb, reference_mask)
    if current_rgb is None:
        return np.asarray(rgb, dtype=np.float32), None

    safe_current = np.clip(current_rgb, 1e-3, None)
    safe_target = np.clip(np.asarray(target_rgb, dtype=np.float32), 1e-3, 1.0)
    channel_gain = np.clip(safe_target / safe_current, 0.7, 1.3)
    applied_gain = 1.0 + (float(strength) * (channel_gain - 1.0))
    aligned = np.clip(np.asarray(rgb, dtype=np.float32) * applied_gain[None, None, :], 0.0, 1.0).astype(np.float32)
    return aligned, {
        "current_median_rgb": current_rgb.tolist(),
        "target_median_rgb": safe_target.tolist(),
        "applied_gain_rgb": applied_gain.astype(np.float32).tolist(),
    }


def _equirectangular_local_directions(width: int, height: int) -> np.ndarray:
    xs = (np.arange(width, dtype=np.float32) + 0.5) / max(width, 1)
    ys = (np.arange(height, dtype=np.float32) + 0.5) / max(height, 1)
    theta = (xs - 0.5) * (2.0 * np.pi)
    phi = (0.5 - ys) * np.pi
    cos_theta = np.cos(theta)[None, :]
    sin_theta = np.sin(theta)[None, :]
    cos_phi = np.cos(phi)[:, None]
    sin_phi = np.sin(phi)[:, None]
    x = sin_theta * cos_phi
    y = sin_phi * np.ones((1, width), dtype=np.float32)
    z = cos_theta * cos_phi
    return np.stack([x, y, z], axis=-1).astype(np.float32)


def build_photo_guided_fill(
    observed_rgb: np.ndarray,
    observed_mask: np.ndarray,
    weight_accum: np.ndarray,
    fallback_fill_rgb: np.ndarray,
    horizontal_blur_px: int,
    vertical_blur_px: int,
    seam_blend_width_px: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    if not np.any(observed_mask):
        return build_low_frequency_fill(fallback_fill_rgb), {
            "fill_strategy": "learned_background_low_frequency",
            "fill_used_observed_projection": False,
        }

    height, width, _ = observed_rgb.shape
    valid_columns = np.flatnonzero(np.any(observed_mask, axis=0))
    if valid_columns.size == 0:
        return build_low_frequency_fill(fallback_fill_rgb), {
            "fill_strategy": "learned_background_low_frequency",
            "fill_used_observed_projection": False,
            "fill_edge_reason": "no_valid_columns",
        }

    source_rgb = np.clip(np.asarray(observed_rgb, dtype=np.float32), 0.0, 1.0)
    top_rows = np.full(width, np.nan, dtype=np.float32)
    bottom_rows = np.full(width, np.nan, dtype=np.float32)
    top_anchor_rgb = np.zeros((width, 3), dtype=np.float32)
    bottom_anchor_rgb = np.zeros((width, 3), dtype=np.float32)

    for column in valid_columns.tolist():
        column_mask = observed_mask[:, column]
        observed_rows = np.flatnonzero(column_mask)
        if observed_rows.size == 0:
            continue
        top_row = int(observed_rows[0])
        bottom_row = int(observed_rows[-1])
        top_rows[column] = float(top_row)
        bottom_rows[column] = float(bottom_row)

        edge_band = min(12, max(2, observed_rows.size // 4))
        top_samples = source_rgb[observed_rows[:edge_band], column, :]
        bottom_samples = source_rgb[observed_rows[-edge_band:], column, :]
        top_anchor_rgb[column, :] = np.median(top_samples, axis=0).astype(np.float32)
        bottom_anchor_rgb[column, :] = np.median(bottom_samples, axis=0).astype(np.float32)

    valid_profile_columns = np.flatnonzero(~np.isnan(top_rows))
    if valid_profile_columns.size == 0:
        return build_low_frequency_fill(fallback_fill_rgb), {
            "fill_strategy": "learned_background_low_frequency",
            "fill_used_observed_projection": False,
            "fill_edge_reason": "invalid_column_extension",
        }

    interpolated_top_rows = _interpolate_circular_profile(top_rows, valid_profile_columns, width)
    interpolated_bottom_rows = _interpolate_circular_profile(bottom_rows, valid_profile_columns, width)
    interpolated_top_rgb = _interpolate_circular_profile(top_anchor_rgb, valid_profile_columns, width)
    interpolated_bottom_rgb = _interpolate_circular_profile(bottom_anchor_rgb, valid_profile_columns, width)

    row_profile_blur_px = max(8, int(horizontal_blur_px) // 2)
    color_profile_blur_px = max(12, int(horizontal_blur_px))
    smoothed_top_rows = _smooth_circular_scalar_profile(interpolated_top_rows, row_profile_blur_px)
    smoothed_bottom_rows = _smooth_circular_scalar_profile(interpolated_bottom_rows, row_profile_blur_px)
    smoothed_top_rgb = _smooth_circular_rgb_profile(interpolated_top_rgb, color_profile_blur_px)
    smoothed_bottom_rgb = _smooth_circular_rgb_profile(interpolated_bottom_rgb, color_profile_blur_px)

    smoothed_top_rows = np.clip(smoothed_top_rows, 0.0, float(max(height - 1, 0)))
    smoothed_bottom_rows = np.clip(smoothed_bottom_rows, smoothed_top_rows, float(max(height - 1, 0)))
    vertical_mix = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None, None]
    vertical_mix = (0.5 - (0.5 * np.cos(np.pi * vertical_mix))).astype(np.float32)
    gradient_field = (
        (1.0 - vertical_mix) * smoothed_top_rgb[None, :, :]
        + vertical_mix * smoothed_bottom_rgb[None, :, :]
    ).astype(np.float32)
    extended_rgb = gradient_field.copy()

    for column in range(width):
        top_row = int(round(float(smoothed_top_rows[column])))
        bottom_row = int(round(float(smoothed_bottom_rows[column])))
        top_row = max(0, min(height - 1, top_row))
        bottom_row = max(top_row, min(height - 1, bottom_row))
        if top_row > 0:
            extended_rgb[:top_row, column, :] = smoothed_top_rgb[column, :]
        if bottom_row + 1 < height:
            extended_rgb[bottom_row + 1 :, column, :] = smoothed_bottom_rgb[column, :]

    extended_rgb[observed_mask] = source_rgb[observed_mask]

    smoothed_extension = _blur_equirectangular_anisotropic(
        extended_rgb,
        radius_x_px=max(0, int(horizontal_blur_px)),
        radius_y_px=max(0, int(vertical_blur_px)),
    )
    predicted = np.clip(smoothed_extension, 0.0, 1.0).astype(np.float32)

    return predicted, {
        "fill_strategy": "observed_edge_profile_smear",
        "fill_used_observed_projection": True,
        "fill_edge_horizontal_blur_px": int(horizontal_blur_px),
        "fill_edge_vertical_blur_px": int(vertical_blur_px),
        "fill_profile_horizontal_blur_px": int(color_profile_blur_px),
        "fill_profile_row_blur_px": int(row_profile_blur_px),
        "fill_seam_blend_width_px": int(seam_blend_width_px),
        "fill_observed_column_count": int(valid_columns.size),
        "fill_observed_sample_count": int(np.count_nonzero(np.clip(weight_accum, 0.0, None))),
        "fill_top_row_mean": float(np.mean(smoothed_top_rows.astype(np.float32))),
        "fill_bottom_row_mean": float(np.mean(smoothed_bottom_rows.astype(np.float32))),
    }


def harmonize_skybox_rgb(
    rgb: np.ndarray,
    detail_support: np.ndarray,
    low_frequency_horizontal_blur_px: int,
    low_frequency_vertical_blur_px: int,
    detail_residual_strength: float,
    detail_support_blur_px: int,
    detail_support_gamma: float = 1.6,
) -> tuple[np.ndarray, dict[str, Any]]:
    rgb_f32 = np.clip(np.asarray(rgb, dtype=np.float32), 0.0, 1.0)
    support_f32 = np.clip(np.asarray(detail_support, dtype=np.float32), 0.0, 1.0)
    low_x = max(1, int(low_frequency_horizontal_blur_px))
    low_y = max(1, int(low_frequency_vertical_blur_px))
    support_blur = max(1, int(detail_support_blur_px))
    residual_strength = float(np.clip(detail_residual_strength, 0.0, 1.0))
    gamma = float(max(detail_support_gamma, 1.0))

    low_frequency = _blur_equirectangular_anisotropic(
        rgb_f32,
        radius_x_px=low_x,
        radius_y_px=low_y,
    )
    medium_frequency = _blur_equirectangular_anisotropic(
        rgb_f32,
        radius_x_px=max(1, low_x // 8),
        radius_y_px=max(1, low_y // 4),
    )
    residual = rgb_f32 - medium_frequency
    harmonized_support = _blur_scalar_equirectangular(np.power(support_f32, gamma), radius_px=support_blur)
    harmonized = np.clip(
        low_frequency + (residual_strength * harmonized_support[..., None] * residual),
        0.0,
        1.0,
    ).astype(np.float32)
    return harmonized, {
        "sky_harmonization_enabled": True,
        "sky_harmonization_low_frequency_horizontal_blur_px": int(low_x),
        "sky_harmonization_low_frequency_vertical_blur_px": int(low_y),
        "sky_harmonization_detail_support_blur_px": int(support_blur),
        "sky_harmonization_detail_support_gamma": float(gamma),
        "sky_harmonization_detail_residual_strength": float(residual_strength),
    }


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


def _select_projected_elevation_mask(
    local_dirs: np.ndarray,
    min_projected_elevation: float,
) -> tuple[np.ndarray, str]:
    local_y = np.asarray(local_dirs, dtype=np.float32)[:, 1]
    if local_y.size == 0:
        return np.zeros((0,), dtype=bool), "empty"

    threshold = float(min_projected_elevation)
    if threshold <= -0.999:
        return np.ones(local_y.shape[0], dtype=bool), "disabled"

    positive_mask = local_y >= threshold
    positive_ratio = float(np.mean(positive_mask))
    if positive_ratio >= 0.02:
        return positive_mask, "positive"

    flipped_mask = local_y <= -threshold
    flipped_ratio = float(np.mean(flipped_mask))
    if flipped_ratio >= max(0.05, positive_ratio * 4.0):
        return flipped_mask, "flipped"

    return np.ones(local_y.shape[0], dtype=bool), "disabled_low_support"


def _prepare_projection_frame(
    data_dir: Path,
    transforms: dict[str, Any],
    frame: dict[str, Any],
    settings: ProjectedSkyboxSettings,
) -> Optional[PreparedProjectionFrame]:
    mask_path = frame.get("mask_path")
    if not mask_path:
        return None

    image_path = _resolve_frame_path(data_dir, str(frame["file_path"]))
    training_mask_path = _resolve_frame_path(data_dir, str(mask_path))
    if not image_path.exists() or not training_mask_path.exists():
        return None

    rgb = np.asarray(Image.open(image_path).convert("RGB"), dtype=np.float32) / 255.0
    training_mask = np.asarray(Image.open(training_mask_path).convert("L"), dtype=np.uint8)
    sky_mask = derive_sky_mask_from_training_mask(training_mask, settings.training_mask_mode)

    confidence = None
    confidence_path = frame.get("semantic_sky_confidence_path")
    if confidence_path:
        resolved_confidence = _resolve_frame_path(data_dir, str(confidence_path))
        if resolved_confidence.exists():
            confidence = np.asarray(Image.open(resolved_confidence).convert("L"), dtype=np.float32) / 255.0

    intrinsics = _frame_intrinsics(frame, transforms)
    rgb, sky_mask, confidence, intrinsics, _ = _resize_for_projection(
        rgb=rgb,
        sky_mask=sky_mask,
        confidence=confidence,
        intrinsics=intrinsics,
        max_long_side=int(settings.projection_max_long_side),
    )
    semantic_mask_ratio = float(sky_mask.mean()) if sky_mask.size else 0.0
    projection_mask = derive_projection_sky_mask(
        sky_mask=sky_mask,
        confidence=confidence,
        confidence_threshold=float(settings.projection_confidence_threshold),
        horizon_smoothing_px=int(settings.projection_horizon_smoothing_px),
        projection_mask_mode=str(settings.projection_mask_mode),
    )
    projection_mask_ratio = float(projection_mask.mean()) if projection_mask.size else 0.0
    if projection_mask_ratio < float(settings.min_sky_mask_ratio):
        return None

    detail_mask = derive_detail_sky_mask(
        sky_mask=sky_mask,
        projection_mask=projection_mask,
        confidence=confidence,
        confidence_threshold=float(settings.projection_confidence_threshold),
        horizon_margin_px=int(settings.detail_horizon_margin_px),
        erosion_px=int(settings.detail_mask_erosion_px),
    )
    detail_mask_ratio = float(detail_mask.mean()) if detail_mask.size else 0.0
    statistics_mask = detail_mask if np.any(detail_mask) else projection_mask

    return PreparedProjectionFrame(
        c2w=np.asarray(frame["transform_matrix"], dtype=np.float32),
        intrinsics=intrinsics,
        rgb=rgb,
        projection_mask=projection_mask,
        detail_mask=detail_mask,
        confidence=confidence,
        semantic_mask_ratio=semantic_mask_ratio,
        projection_mask_ratio=projection_mask_ratio,
        detail_mask_ratio=detail_mask_ratio,
        sky_median_rgb=_robust_median_rgb(rgb, statistics_mask),
    )


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
        np.add.at(support_accum, (dest_y[valid], dest_x[valid]), 1.0)
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

    base_color_accum = np.zeros((height, width, 3), dtype=np.float32)
    base_weight_accum = np.zeros((height, width), dtype=np.float32)
    base_support_accum = np.zeros((height, width), dtype=np.float32)
    detail_color_accum = np.zeros((height, width, 3), dtype=np.float32)
    detail_weight_accum = np.zeros((height, width), dtype=np.float32)
    detail_support_accum = np.zeros((height, width), dtype=np.float32)
    contributing_frames = 0
    detail_contributing_frames = 0
    sampled_frames = 0
    semantic_mask_ratios: list[float] = []
    projection_mask_ratios: list[float] = []
    detail_mask_ratios: list[float] = []
    frame_medians: list[np.ndarray] = []
    alignment_gains: list[np.ndarray] = []
    prepared_frames: list[PreparedProjectionFrame] = []
    elevation_mode_counts = {
        "positive": 0,
        "flipped": 0,
        "disabled": 0,
        "disabled_low_support": 0,
        "empty": 0,
    }
    detail_elevation_mode_counts = {
        "positive": 0,
        "flipped": 0,
        "disabled": 0,
        "disabled_low_support": 0,
        "empty": 0,
    }

    for frame in frames:
        prepared = _prepare_projection_frame(
            data_dir=data_dir,
            transforms=transforms,
            frame=frame,
            settings=settings,
        )
        if prepared is None:
            continue
        sampled_frames += 1
        semantic_mask_ratios.append(prepared.semantic_mask_ratio)
        projection_mask_ratios.append(prepared.projection_mask_ratio)
        detail_mask_ratios.append(prepared.detail_mask_ratio)
        prepared_frames.append(prepared)
        if prepared.sky_median_rgb is not None:
            frame_medians.append(prepared.sky_median_rgb)

    alignment_target_rgb = None
    if frame_medians:
        alignment_target_rgb = np.median(np.stack(frame_medians, axis=0), axis=0).astype(np.float32)

    for prepared in prepared_frames:
        alignment_mask = prepared.detail_mask if np.any(prepared.detail_mask) else prepared.projection_mask
        aligned_rgb, alignment_metadata = _apply_frame_alignment(
            rgb=prepared.rgb,
            reference_mask=alignment_mask,
            target_rgb=alignment_target_rgb,
            strength=float(settings.photometric_alignment_strength),
        )
        if alignment_metadata is not None:
            alignment_gains.append(np.asarray(alignment_metadata["applied_gain_rgb"], dtype=np.float32))

        projection_mask = prepared.projection_mask
        active = np.flatnonzero(projection_mask.reshape(-1))
        if active.size == 0:
            continue

        height_local, width_local = projection_mask.shape
        grid_x, grid_y = np.meshgrid(
            np.arange(width_local, dtype=np.float32) + 0.5,
            np.arange(height_local, dtype=np.float32) + 0.5,
            indexing="xy",
        )
        pixel_x = grid_x.reshape(-1)[active]
        pixel_y = grid_y.reshape(-1)[active]
        colors = aligned_rgb.reshape(-1, 3)[active]

        edge_weights = _edge_feather_weights(projection_mask, int(settings.blend_edge_feather_px)).reshape(-1)[active]
        center_weights = _center_weights(width_local, height_local).reshape(-1)[active]
        if prepared.confidence is not None:
            confidence_weights = np.clip(prepared.confidence.reshape(-1)[active], 0.0, 1.0)
        else:
            confidence_weights = np.ones_like(center_weights, dtype=np.float32)

        combined_weights = edge_weights * center_weights * np.clip(confidence_weights, 0.25, 1.0)
        active_weight_mask = combined_weights > 1e-4
        if not np.any(active_weight_mask):
            continue

        contributing_frames += 1
        world_dirs = _camera_rays_for_pixels(
            xs=pixel_x[active_weight_mask],
            ys=pixel_y[active_weight_mask],
            intrinsics=prepared.intrinsics,
            c2w=prepared.c2w,
        )
        local_dirs = (world_to_sky @ world_dirs.T).T
        projected_elevation_mask, elevation_mode = _select_projected_elevation_mask(
            local_dirs=local_dirs,
            min_projected_elevation=float(settings.min_projected_elevation),
        )
        elevation_mode_counts[elevation_mode] = elevation_mode_counts.get(elevation_mode, 0) + 1
        if not np.any(projected_elevation_mask):
            continue
        eq_x, eq_y = world_dirs_to_equirectangular(
            world_directions=world_dirs[projected_elevation_mask],
            world_to_sky=world_to_sky,
            width=width,
            height=height,
        )
        _accumulate_bilinear(
            xs=eq_x,
            ys=eq_y,
            colors=colors[active_weight_mask][projected_elevation_mask],
            weights=combined_weights[active_weight_mask][projected_elevation_mask],
            width=width,
            height=height,
            color_accum=base_color_accum,
            weight_accum=base_weight_accum,
            support_accum=base_support_accum,
        )

        if not np.any(prepared.detail_mask):
            continue
        detail_active = np.flatnonzero(prepared.detail_mask.reshape(-1))
        if detail_active.size == 0:
            continue

        detail_pixel_x = grid_x.reshape(-1)[detail_active]
        detail_pixel_y = grid_y.reshape(-1)[detail_active]
        detail_colors = aligned_rgb.reshape(-1, 3)[detail_active]
        detail_edge_weights = _edge_feather_weights(
            prepared.detail_mask,
            max(2, int(settings.blend_edge_feather_px) // 2),
        ).reshape(-1)[detail_active]
        detail_center_weights = _center_weights(width_local, height_local).reshape(-1)[detail_active]
        if prepared.confidence is not None:
            detail_confidence_weights = np.clip(prepared.confidence.reshape(-1)[detail_active], 0.0, 1.0)
        else:
            detail_confidence_weights = np.ones_like(detail_center_weights, dtype=np.float32)
        detail_combined_weights = detail_edge_weights * detail_center_weights * np.clip(detail_confidence_weights, 0.5, 1.0)
        detail_active_mask = detail_combined_weights > 1e-4
        if not np.any(detail_active_mask):
            continue

        detail_world_dirs = _camera_rays_for_pixels(
            xs=detail_pixel_x[detail_active_mask],
            ys=detail_pixel_y[detail_active_mask],
            intrinsics=prepared.intrinsics,
            c2w=prepared.c2w,
        )
        detail_local_dirs = (world_to_sky @ detail_world_dirs.T).T
        detail_elevation_mask, detail_elevation_mode = _select_projected_elevation_mask(
            local_dirs=detail_local_dirs,
            min_projected_elevation=float(settings.min_projected_elevation),
        )
        detail_elevation_mode_counts[detail_elevation_mode] = detail_elevation_mode_counts.get(
            detail_elevation_mode,
            0,
        )
        if not np.any(detail_elevation_mask):
            continue

        detail_contributing_frames += 1
        detail_eq_x, detail_eq_y = world_dirs_to_equirectangular(
            world_directions=detail_world_dirs[detail_elevation_mask],
            world_to_sky=world_to_sky,
            width=width,
            height=height,
        )
        _accumulate_bilinear(
            xs=detail_eq_x,
            ys=detail_eq_y,
            colors=detail_colors[detail_active_mask][detail_elevation_mask],
            weights=detail_combined_weights[detail_active_mask][detail_elevation_mask],
            width=width,
            height=height,
            color_accum=detail_color_accum,
            weight_accum=detail_weight_accum,
            support_accum=detail_support_accum,
        )

    observed_mask = base_support_accum >= float(max(settings.min_observations_per_pixel, 1))
    safe_weights = np.clip(base_weight_accum[..., None], 1e-6, None)
    observed_rgb = base_color_accum / safe_weights
    smoothed_observed_rgb, smoothed_observed_support = _weighted_equirectangular_blur(
        rgb=np.clip(observed_rgb, 0.0, 1.0),
        weights=base_weight_accum,
        radius_px=int(settings.observed_blur_radius_px),
    )
    base_observed_horizontal_blur_px = max(
        int(settings.observed_blur_radius_px) * 2,
        int(settings.fill_edge_horizontal_blur_px),
    )
    base_observed_vertical_blur_px = max(
        int(settings.observed_blur_radius_px),
        min(int(settings.fill_edge_vertical_blur_px) // 6, 48),
    )
    base_observed_rgb = _blur_equirectangular_anisotropic(
        smoothed_observed_rgb,
        radius_x_px=base_observed_horizontal_blur_px,
        radius_y_px=base_observed_vertical_blur_px,
    )
    if settings.low_frequency_fill:
        fill_base, fill_metadata = build_photo_guided_fill(
            observed_rgb=smoothed_observed_rgb,
            observed_mask=observed_mask,
            weight_accum=base_weight_accum,
            fallback_fill_rgb=fill_rgb,
            horizontal_blur_px=int(settings.fill_edge_horizontal_blur_px),
            vertical_blur_px=int(settings.fill_edge_vertical_blur_px),
            seam_blend_width_px=int(settings.seam_blend_width_px),
        )
    else:
        fill_base = np.clip(fill_rgb, 0.0, 1.0)
        fill_metadata = {
            "fill_strategy": "learned_background_direct",
            "fill_used_observed_projection": False,
        }

    if np.any(smoothed_observed_support > 1e-6):
        support_reference = float(np.percentile(smoothed_observed_support[smoothed_observed_support > 1e-6], 80))
    else:
        support_reference = 1.0
    interior_mix = _interior_distance_fade(
        observed_mask,
        fade_px=max(1, int(settings.seam_blend_width_px)),
    )
    interior_mix = _blur_scalar_equirectangular(
        interior_mix,
        radius_px=max(1, int(settings.seam_blend_width_px) // 3),
    )
    support_mix = np.clip(smoothed_observed_support / max(support_reference, 1e-6), 0.0, 1.0)
    base_mix = np.clip(interior_mix + (0.15 * support_mix), 0.0, 1.0)[..., None]
    base_rgb = (fill_base * (1.0 - base_mix)) + (base_observed_rgb * base_mix)
    base_rgb = _scale_saturation(base_rgb, float(settings.base_saturation_scale))
    base_rgb, _ = _weighted_equirectangular_blur(
        rgb=base_rgb,
        weights=np.ones((height, width), dtype=np.float32),
        radius_px=max(1, int(settings.observed_blur_radius_px) // 3),
    )

    detail_observed_mask = detail_support_accum >= float(max(settings.min_observations_per_pixel, 1))
    detail_rgb = detail_color_accum / np.clip(detail_weight_accum[..., None], 1e-6, None)
    detail_smoothed_rgb, _ = _weighted_equirectangular_blur(
        rgb=np.clip(detail_rgb, 0.0, 1.0),
        weights=detail_weight_accum,
        radius_px=int(settings.detail_blur_radius_px),
    )
    detail_support = _blur_scalar_equirectangular(
        detail_observed_mask.astype(np.float32),
        radius_px=max(1, int(settings.detail_blur_radius_px)),
    )
    if np.any(detail_support > 1e-6):
        detail_support_reference = float(np.percentile(detail_support[detail_support > 1e-6], 80))
    else:
        detail_support_reference = 1.0
    detail_support = np.clip(detail_support / max(detail_support_reference, 1e-6), 0.0, 1.0)
    detail_support *= _interior_distance_fade(
        detail_observed_mask,
        fade_px=max(1, int(settings.detail_boundary_fade_px)),
    )

    detail_observed_luma = _luminance(detail_rgb)
    detail_smoothed_luma = _luminance(detail_smoothed_rgb)
    detail_luma_residual = (detail_observed_luma - detail_smoothed_luma)[..., None]
    negative_luma_scale = float(np.clip(settings.detail_negative_luma_scale, 0.0, 1.0))
    detail_luma_residual = np.where(
        detail_luma_residual < 0.0,
        detail_luma_residual * negative_luma_scale,
        detail_luma_residual,
    ).astype(np.float32)
    detail_observed_chroma = detail_rgb - detail_observed_luma[..., None]
    detail_smoothed_chroma = detail_smoothed_rgb - detail_smoothed_luma[..., None]
    detail_chroma_residual = detail_observed_chroma - detail_smoothed_chroma

    final_rgb = base_rgb + (
        detail_support[..., None]
        * (
            (float(settings.detail_luma_strength) * detail_luma_residual)
            + (float(settings.detail_chroma_strength) * detail_chroma_residual)
        )
    )
    final_rgb = np.clip(final_rgb, 0.0, 1.0).astype(np.float32)
    pre_harmonize_rgb = final_rgb.copy()
    final_rgb, harmonization_metadata = harmonize_skybox_rgb(
        rgb=final_rgb,
        detail_support=detail_support,
        low_frequency_horizontal_blur_px=max(128, int(settings.fill_edge_horizontal_blur_px) * 4),
        low_frequency_vertical_blur_px=max(24, min(int(settings.fill_edge_vertical_blur_px) // 3, 64)),
        detail_residual_strength=float(np.clip(float(settings.detail_luma_strength) * 0.3, 0.1, 0.25)),
        detail_support_blur_px=max(24, min(int(settings.detail_boundary_fade_px), 48)),
    )

    skybox_path = output_dir / "background_skybox.webp"
    Image.fromarray((final_rgb * 255.0).round().astype(np.uint8), mode="RGB").save(
        skybox_path,
        format="WEBP",
        quality=quality,
        method=6,
    )
    Image.fromarray((pre_harmonize_rgb * 255.0).round().astype(np.uint8), mode="RGB").save(
        output_dir / "background_skybox_pre_harmonize.webp",
        format="WEBP",
        quality=min(quality, 92),
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
    Image.fromarray((np.clip(base_rgb, 0.0, 1.0) * 255.0).round().astype(np.uint8), mode="RGB").save(
        output_dir / "background_skybox_base.webp",
        format="WEBP",
        quality=min(quality, 92),
        method=6,
    )
    detail_preview = np.clip(0.5 + (
        (float(settings.detail_luma_strength) * detail_luma_residual)
        + (float(settings.detail_chroma_strength) * detail_chroma_residual)
    ), 0.0, 1.0)
    Image.fromarray((detail_preview * 255.0).round().astype(np.uint8), mode="RGB").save(
        output_dir / "background_skybox_detail.webp",
        format="WEBP",
        quality=min(quality, 90),
        method=6,
    )
    Image.fromarray((np.clip(detail_support, 0.0, 1.0) * 255.0).round().astype(np.uint8), mode="L").save(
        output_dir / "background_skybox_detail_support.png"
    )
    normalized_coverage = np.clip(base_support_accum / np.maximum(base_support_accum.max(), 1.0), 0.0, 1.0)
    Image.fromarray((normalized_coverage * 255.0).round().astype(np.uint8), mode="L").save(
        output_dir / "background_skybox_coverage.png"
    )

    mean_alignment_gain_rgb = None
    if alignment_gains:
        mean_alignment_gain_rgb = np.mean(np.stack(alignment_gains, axis=0), axis=0).astype(np.float32).tolist()

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
        "projection_mask_mode": str(settings.projection_mask_mode),
        "projection_confidence_threshold": float(settings.projection_confidence_threshold),
        "projection_horizon_smoothing_px": int(settings.projection_horizon_smoothing_px),
        "photometric_alignment_strength": float(settings.photometric_alignment_strength),
        "base_saturation_scale": float(settings.base_saturation_scale),
        "detail_luma_strength": float(settings.detail_luma_strength),
        "detail_chroma_strength": float(settings.detail_chroma_strength),
        "detail_horizon_margin_px": int(settings.detail_horizon_margin_px),
        "detail_mask_erosion_px": int(settings.detail_mask_erosion_px),
        "min_projected_elevation": float(settings.min_projected_elevation),
        "observed_blur_radius_px": int(settings.observed_blur_radius_px),
        "detail_blur_radius_px": int(settings.detail_blur_radius_px),
        "fill_edge_horizontal_blur_px": int(settings.fill_edge_horizontal_blur_px),
        "fill_edge_vertical_blur_px": int(settings.fill_edge_vertical_blur_px),
        "seam_blend_width_px": int(settings.seam_blend_width_px),
        "detail_boundary_fade_px": int(settings.detail_boundary_fade_px),
        "detail_negative_luma_scale": float(settings.detail_negative_luma_scale),
        "projection_elevation_mode_counts": elevation_mode_counts,
        "detail_projection_elevation_mode_counts": detail_elevation_mode_counts,
        "low_frequency_fill": bool(settings.low_frequency_fill),
        "observed_coverage_ratio": float(observed_mask.mean()) if observed_mask.size else 0.0,
        "filled_coverage_ratio": float(1.0 - observed_mask.mean()) if observed_mask.size else 1.0,
        "contributing_frame_count": int(contributing_frames),
        "detail_contributing_frame_count": int(detail_contributing_frames),
        "sampled_frame_count": int(sampled_frames),
        "mean_semantic_mask_ratio": float(np.mean(semantic_mask_ratios)) if semantic_mask_ratios else 0.0,
        "mean_projection_mask_ratio": float(np.mean(projection_mask_ratios)) if projection_mask_ratios else 0.0,
        "mean_detail_mask_ratio": float(np.mean(detail_mask_ratios)) if detail_mask_ratios else 0.0,
        "detail_coverage_ratio": float(detail_observed_mask.mean()) if detail_observed_mask.size else 0.0,
        "base_observed_horizontal_blur_px": int(base_observed_horizontal_blur_px),
        "base_observed_vertical_blur_px": int(base_observed_vertical_blur_px),
        "alignment_target_rgb": alignment_target_rgb.tolist() if alignment_target_rgb is not None else None,
        "alignment_frame_count": int(len(alignment_gains)),
        "mean_alignment_gain_rgb": mean_alignment_gain_rgb,
        **harmonization_metadata,
        **fill_metadata,
        "alignment_basis": {
            "right": basis["right"].tolist(),
            "up": basis["up"].tolist(),
            "forward": basis["forward"].tolist(),
        },
    }
    (output_dir / "background_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
