"""Runtime scaling helpers for large SfM datasets."""

from __future__ import annotations

from typing import Dict, Optional


DEFAULT_PROFILE_OVERRIDE = "auto"
DEFAULT_TARGET_PAIRS = 9000
PROFILE_OVERRIDES = {"auto", "quality", "large_dataset"}


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


def _bounded_neighbors(
    image_count: int,
    *,
    minimum: int,
    maximum: int,
    target_pairs: int = DEFAULT_TARGET_PAIRS,
) -> int:
    if image_count <= 0:
        return maximum
    return max(minimum, min(maximum, target_pairs // image_count))


def build_stage_timeouts(image_count: int) -> Dict[str, int]:
    """Return per-stage time budgets in seconds."""
    if image_count > 700:
        return {
            "match_features": 4 * 60 * 60,
            # Large reconstructions stayed memory-stable at 898 images but were still
            # actively registering shots when the 4 hour cap fired, so allow a longer
            # reconstruction window without changing the cheaper matching budget.
            "reconstruct": 6 * 60 * 60,
        }
    if image_count > 350:
        return {
            "match_features": 2 * 60 * 60,
            "reconstruct": 2 * 60 * 60,
        }
    return {
        "match_features": 40 * 60,
        "reconstruct": 2 * 60 * 60,
    }


def select_sfm_runtime_plan(
    image_count: int,
    *,
    has_gps_priors: bool,
    profile_override: Optional[str] = None,
    cpu_count: Optional[int] = None,
) -> Dict[str, object]:
    """Choose the runtime profile, config, and timeout budgets."""
    profile_override = normalize_profile_override(profile_override)
    cpu_count = max(1, cpu_count or 1)

    base_config = {
        "feature_type": "SIFT",
        "min_ray_angle_degrees": 1.0,
        "reconstruction_min_ratio": 0.6,
        "triangulation_min_ray_angle_degrees": 1.0,
        "use_altitude_tag": True,
        "gps_accuracy": 5.0,
        "bundle_use_gps": has_gps_priors,
        "bundle_use_gcp": False,
        "optimize_camera_parameters": True,
        "bundle_max_iterations": 100,
        "reconstruction_split_ratio": 0.8,
        "reconstruction_split_method": "sequential",
        "save_partial_reconstructions": True,
    }

    if has_gps_priors:
        profile_name = "quality"
        profile_config = {
            "feature_process_size": 2048,
            "feature_max_num_features": 20000,
            "feature_min_frames": 4000,
            "sift_peak_threshold": 0.006,
            "matching_gps_neighbors": 30,
            "matching_gps_distance": 300,
            "matching_graph_rounds": 80,
            "robust_matching_min_match": 8,
            "processes": 4,
        }

        if profile_override == "large_dataset" or (profile_override == "auto" and image_count > 600):
            profile_name = "large_dataset"
            profile_config.update(
                {
                    "feature_process_size": 1400,
                    "feature_max_num_features": 8000,
                    "feature_min_frames": 1600,
                    "sift_peak_threshold": 0.009,
                    "matching_gps_neighbors": _bounded_neighbors(
                        image_count,
                        minimum=8,
                        maximum=12,
                    ),
                    "matching_gps_distance": 180,
                    "matching_graph_rounds": 28,
                    "robust_matching_min_match": 10,
                    "processes": min(4, cpu_count),
                }
            )
        elif profile_override == "auto" and image_count > 350:
            profile_name = "medium_dataset"
            profile_config.update(
                {
                    "feature_process_size": 1800,
                    "feature_max_num_features": 12000,
                    "feature_min_frames": 2500,
                    "sift_peak_threshold": 0.008,
                    "matching_gps_neighbors": _bounded_neighbors(
                        image_count,
                        minimum=10,
                        maximum=20,
                    ),
                    "matching_gps_distance": 240,
                    "matching_graph_rounds": 48,
                    "robust_matching_min_match": 10,
                    "processes": min(6, cpu_count),
                }
            )
    else:
        profile_name = "no_gps_small"
        profile_config = {
            "feature_process_size": 1200,
            "feature_max_num_features": 6000,
            "feature_min_frames": 1200,
            "sift_peak_threshold": 0.01,
            "matching_gps_neighbors": 10,
            "matching_gps_distance": 120,
            "matching_graph_rounds": 16,
            "robust_matching_min_match": 12,
            "processes": max(4, min(16, cpu_count)),
        }

        if profile_override == "quality":
            profile_name = "no_gps_quality"
            profile_config.update(
                {
                    "feature_process_size": 1600,
                    "feature_max_num_features": 10000,
                    "feature_min_frames": 2000,
                    "sift_peak_threshold": 0.008,
                    "matching_gps_neighbors": 12,
                    "matching_gps_distance": 180,
                    "matching_graph_rounds": 24,
                    "robust_matching_min_match": 10,
                    "processes": max(4, min(12, cpu_count)),
                }
            )
        elif profile_override == "large_dataset" or (profile_override == "auto" and image_count > 600):
            profile_name = "no_gps_large_dataset"
            profile_config.update(
                {
                    "feature_process_size": 1100,
                    "feature_max_num_features": 5000,
                    "feature_min_frames": 1000,
                    "sift_peak_threshold": 0.011,
                    "matching_gps_neighbors": _bounded_neighbors(
                        image_count,
                        minimum=6,
                        maximum=8,
                        target_pairs=6000,
                    ),
                    "matching_gps_distance": 100,
                    "matching_graph_rounds": 12,
                    "robust_matching_min_match": 12,
                    "processes": max(4, min(6, cpu_count)),
                }
            )
        elif profile_override == "auto" and image_count > 350:
            profile_name = "no_gps_medium_dataset"
            profile_config.update(
                {
                    "feature_process_size": 1150,
                    "feature_max_num_features": 5500,
                    "feature_min_frames": 1100,
                    "sift_peak_threshold": 0.0105,
                    "matching_gps_neighbors": _bounded_neighbors(
                        image_count,
                        minimum=8,
                        maximum=10,
                        target_pairs=7000,
                    ),
                    "matching_gps_distance": 110,
                    "matching_graph_rounds": 14,
                    "robust_matching_min_match": 12,
                    "processes": max(4, min(8, cpu_count)),
                }
            )

    config = {
        **base_config,
        **profile_config,
    }
    neighbors = int(config.get("matching_gps_neighbors", 0) or 0)
    estimated_pairs = image_count * neighbors

    return {
        "selected_profile": profile_name,
        "image_count": image_count,
        "has_gps_priors": has_gps_priors,
        "config": config,
        "selected_neighbors": neighbors,
        "estimated_pairs": estimated_pairs,
        "stage_timeouts": build_stage_timeouts(image_count),
    }
