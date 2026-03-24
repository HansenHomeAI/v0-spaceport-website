"""Runtime planning helpers for segmented COLMAP SfM jobs."""

from __future__ import annotations

import math
from typing import Dict, Optional


DEFAULT_PROFILE_OVERRIDE = "auto"
PROFILE_OVERRIDES = {"auto", "quality", "large_dataset"}

DEFAULT_SEGMENT_TARGET_SIZE = 450
DEFAULT_SEGMENT_OVERLAP = 90
DEFAULT_SEGMENT_MAX_SIZE = 600
DEFAULT_SEGMENT_MIN_SIZE = 250


def normalize_profile_override(raw_value: Optional[str]) -> str:
    """Normalize the optional profile override value."""
    if raw_value is None:
        return DEFAULT_PROFILE_OVERRIDE

    normalized = str(raw_value).strip().lower()
    if not normalized:
        return DEFAULT_PROFILE_OVERRIDE
    if normalized not in PROFILE_OVERRIDES:
        raise ValueError(
            f"Unsupported SfM profile override: {raw_value!r}. "
            f"Expected one of {sorted(PROFILE_OVERRIDES)}."
        )
    return normalized


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def estimate_segment_count(
    image_count: int,
    *,
    target_size: int = DEFAULT_SEGMENT_TARGET_SIZE,
    overlap: int = DEFAULT_SEGMENT_OVERLAP,
    max_size: int = DEFAULT_SEGMENT_MAX_SIZE,
) -> int:
    """Estimate the number of sliding-window segments for planning purposes."""
    if image_count <= 0:
        return 0
    if image_count <= max_size:
        return 1

    step = max(1, target_size - overlap)
    remaining = image_count
    segments = 0
    start = 0
    while start < image_count:
        remaining = image_count - start
        if remaining <= max_size:
            segments += 1
            break
        segments += 1
        start += step
    return segments


def build_stage_timeouts(
    image_count: int,
    *,
    segment_count: int,
) -> Dict[str, int]:
    """Return coarse stage budgets in seconds for metadata and watchdogs."""
    if image_count > 1200:
        return {
            "feature_matching": 90 * 60,
            "mapping_per_segment": 60 * 60,
            "merge_models": 30 * 60,
            "job_total": 3 * 60 * 60,
        }
    if image_count > 350:
        return {
            "feature_matching": 60 * 60,
            "mapping_per_segment": 45 * 60,
            "merge_models": 20 * 60,
            "job_total": 2 * 60 * 60,
        }
    return {
        "feature_matching": 45 * 60,
        "mapping_per_segment": 30 * 60,
        "merge_models": 15 * 60,
        "job_total": 90 * 60,
    }


def select_sfm_runtime_plan(
    image_count: int,
    *,
    has_gps_priors: bool,
    profile_override: Optional[str] = None,
    cpu_count: Optional[int] = None,
    median_relative_altitude_m: Optional[float] = None,
) -> Dict[str, object]:
    """Choose the segmented COLMAP runtime profile and planner knobs."""
    profile_override = normalize_profile_override(profile_override)
    cpu_count = max(2, cpu_count or 2)
    altitude_for_radius = float(median_relative_altitude_m or 48.0)
    spatial_radius_m = int(round(clamp(2.5 * altitude_for_radius, 80.0, 180.0)))

    if has_gps_priors:
        if profile_override == "quality":
            profile_name = "quality"
            spatial_neighbors = 12
            segment_target_size = 400
            segment_overlap = 120
            segment_worker_count = 1
        elif profile_override == "large_dataset" or image_count > 1200:
            profile_name = "large_dataset"
            spatial_neighbors = 12
            segment_target_size = DEFAULT_SEGMENT_TARGET_SIZE
            segment_overlap = DEFAULT_SEGMENT_OVERLAP
            segment_worker_count = min(4, max(1, cpu_count // 6))
        elif image_count > 350:
            profile_name = "medium_dataset"
            spatial_neighbors = 12
            segment_target_size = DEFAULT_SEGMENT_TARGET_SIZE
            segment_overlap = DEFAULT_SEGMENT_OVERLAP
            segment_worker_count = min(2, max(1, cpu_count // 6))
        else:
            profile_name = "quality"
            spatial_neighbors = 12
            segment_target_size = 400
            segment_overlap = 120
            segment_worker_count = 1
    else:
        if profile_override == "quality":
            profile_name = "no_gps_quality"
            spatial_neighbors = 10
            segment_target_size = 380
            segment_overlap = 100
            segment_worker_count = 1
        elif profile_override == "large_dataset" or image_count > 1200:
            profile_name = "no_gps_large_dataset"
            spatial_neighbors = 8
            segment_target_size = DEFAULT_SEGMENT_TARGET_SIZE
            segment_overlap = DEFAULT_SEGMENT_OVERLAP
            segment_worker_count = min(4, max(1, cpu_count // 6))
        elif image_count > 350:
            profile_name = "no_gps_medium_dataset"
            spatial_neighbors = 10
            segment_target_size = DEFAULT_SEGMENT_TARGET_SIZE
            segment_overlap = DEFAULT_SEGMENT_OVERLAP
            segment_worker_count = min(2, max(1, cpu_count // 6))
        else:
            profile_name = "no_gps_small"
            spatial_neighbors = 8
            segment_target_size = 380
            segment_overlap = 100
            segment_worker_count = 1

    segment_worker_count = max(1, segment_worker_count)
    worker_threads = max(2, cpu_count // segment_worker_count)
    segment_count = estimate_segment_count(
        image_count,
        target_size=segment_target_size,
        overlap=segment_overlap,
    )
    estimated_pairs = image_count * spatial_neighbors

    return {
        "selected_profile": profile_name,
        "image_count": image_count,
        "has_gps_priors": has_gps_priors,
        "segment_target_size": segment_target_size,
        "segment_overlap": segment_overlap,
        "segment_max_size": DEFAULT_SEGMENT_MAX_SIZE,
        "segment_min_size": DEFAULT_SEGMENT_MIN_SIZE,
        "segment_count_estimate": segment_count,
        "segment_worker_count": segment_worker_count,
        "worker_threads": worker_threads,
        "spatial_matcher_neighbors": spatial_neighbors,
        "spatial_matcher_distance_m": spatial_radius_m,
        "sequential_matcher_overlap": 10,
        "transitive_matcher_enabled": True,
        "global_mapper_min_registered_ratio": 0.85,
        "estimated_pairs": estimated_pairs,
        "stage_timeouts": build_stage_timeouts(
            image_count,
            segment_count=segment_count,
        ),
        "projection_defaults": {
            "target_image_count": 4750,
            "projection_instance_type": "ml.c6i.8xlarge",
            "projection_segment_worker_count": 4,
        },
    }
