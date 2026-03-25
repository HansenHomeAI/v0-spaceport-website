#!/usr/bin/env python3

import json
import os
from typing import Dict


def select_sfm_execution_profile(image_count: int, total_input_bytes: int, has_gps_priors: bool) -> Dict[str, object]:
    """Select a processing profile based on dataset size and GPS availability."""
    total_mb = total_input_bytes / (1024 * 1024) if total_input_bytes else 0

    profile = {
        "name": "gps_standard" if has_gps_priors else "small_no_gps",
        "overrides": {},
        "timeouts": {
            "match_features": {"max_seconds": 2400, "stall_seconds": 900},
            "reconstruct": {"max_seconds": 7200, "stall_seconds": 1800},
        },
        "debug": json.dumps({
            "images": image_count,
            "payload_mb": round(total_mb, 1),
            "has_gps_priors": has_gps_priors,
        }),
    }

    if not has_gps_priors:
        profile["overrides"] = {
            "feature_process_size": 1200,
            "feature_max_num_features": 6000,
            "feature_min_frames": 1200,
            "sift_peak_threshold": 0.01,
            "matching_gps_neighbors": 10,
            "matching_gps_distance": 120,
            "matching_graph_rounds": 16,
            "robust_matching_min_match": 12,
            "processes": max(4, min(16, os.cpu_count() or 4)),
        }

        if image_count >= 300 or total_mb >= 1200:
            profile["name"] = "medium_no_gps"
            profile["overrides"].update({
                "feature_process_size": 1100,
                "feature_max_num_features": 5500,
                "feature_min_frames": 1100,
                "matching_gps_neighbors": 8,
                "matching_gps_distance": 100,
                "matching_graph_rounds": 12,
                "robust_matching_min_match": 14,
                "processes": max(4, min(8, os.cpu_count() or 4)),
            })
            profile["timeouts"] = {
                "match_features": {"max_seconds": 3600, "stall_seconds": 1200},
                "reconstruct": {"max_seconds": 10800, "stall_seconds": 2400},
            }

        if image_count >= 450 or total_mb >= 2000:
            profile["name"] = "large_no_gps"
            profile["overrides"].update({
                "feature_process_size": 1024,
                "feature_max_num_features": 5000,
                "feature_min_frames": 1000,
                "matching_gps_neighbors": 6,
                "matching_gps_distance": 80,
                "matching_graph_rounds": 8,
                "robust_matching_min_match": 16,
                "processes": max(4, min(6, os.cpu_count() or 4)),
            })
            profile["timeouts"] = {
                "match_features": {"max_seconds": 5400, "stall_seconds": 1500},
                "reconstruct": {"max_seconds": 18000, "stall_seconds": 3600},
            }

    return profile


def line_indicates_progress(command: str, line: str) -> bool:
    if command == "reconstruct":
        markers = (
            "Adding ",
            "Reconstruction now has",
            "Ran GLOBAL bundle",
            "Ran LOCAL bundle",
            "Re-triangulating",
            "Removed outliers",
        )
        return any(marker in line for marker in markers)

    if command == "match_features":
        return bool(line.strip())

    return False
