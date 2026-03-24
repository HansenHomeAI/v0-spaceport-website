"""Static-cost estimation helpers for SfM processing jobs."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from segmenter import build_segments
from exif_manifest import ImageRecord


INSTANCE_HOURLY_RATES_USD = {
    "ml.c6i.2xlarge": 0.34,
    "ml.c6i.4xlarge": 0.68,
    "ml.c6i.8xlarge": 1.36,
}


def estimate_processing_cost(instance_type: str, runtime_seconds: float) -> Dict[str, object]:
    rate = INSTANCE_HOURLY_RATES_USD.get(instance_type)
    return {
        "instance_type": instance_type,
        "hourly_rate_usd": rate,
        "processing_time_seconds": round(float(runtime_seconds), 2),
        "estimated_processing_cost_usd": round(((rate or 0.0) * runtime_seconds) / 3600.0, 4),
        "pricing_source": "repo_static_rate_table",
    }


def project_large_landscape_cost(
    *,
    records: List[ImageRecord],
    segment_durations_seconds: Iterable[float],
    target_image_count: int,
    target_instance_type: str,
    target_worker_count: int,
    target_size: int,
    overlap: int,
    max_size: int,
    min_size: int,
) -> Dict[str, object]:
    durations = [float(value) for value in segment_durations_seconds if value]
    average_segment_duration = sum(durations) / len(durations) if durations else 0.0
    template_records = _synthetic_records(records, target_image_count)
    projected_segments = build_segments(
        template_records,
        target_size=target_size,
        overlap=overlap,
        max_size=max_size,
        min_size=min_size,
    )
    merge_overhead_seconds = max(600.0, len(projected_segments) * 45.0)
    projected_runtime = (
        ((len(projected_segments) + max(1, target_worker_count) - 1) // max(1, target_worker_count))
        * average_segment_duration
        + merge_overhead_seconds
    )
    base = estimate_processing_cost(target_instance_type, projected_runtime)
    base.update(
        {
            "target_image_count": target_image_count,
            "segment_count_estimate": len(projected_segments),
            "worker_count": target_worker_count,
            "average_segment_duration_seconds": round(average_segment_duration, 2),
            "projected_runtime_seconds": round(projected_runtime, 2),
            "within_budget_goal": base["estimated_processing_cost_usd"] <= 1.75,
        }
    )
    return base


def _synthetic_records(records: List[ImageRecord], target_image_count: int) -> List[ImageRecord]:
    if not records:
        return []
    if len(records) >= target_image_count:
        return records[:target_image_count]

    synthetic = list(records)
    base = records[-1]
    for index in range(len(records), target_image_count):
        synthetic.append(
            ImageRecord(
                name=f"synthetic_{index:05d}.jpg",
                path=base.path,
                capture_time=base.capture_time,
                capture_sort_key=f"synthetic_{index:05d}",
                latitude=base.latitude,
                longitude=base.longitude,
                absolute_altitude_m=base.absolute_altitude_m,
                relative_altitude_m=base.relative_altitude_m,
                chosen_altitude_m=base.chosen_altitude_m,
                flight_yaw_deg=base.flight_yaw_deg,
                gimbal_pitch_deg=base.gimbal_pitch_deg,
                focal_length_mm=base.focal_length_mm,
                model=base.model,
                width=base.width,
                height=base.height,
                camera_group=base.camera_group,
                gps_accuracy_m=base.gps_accuracy_m,
                enu_x_m=base.enu_x_m,
                enu_y_m=base.enu_y_m,
                enu_z_m=base.enu_z_m,
            )
        )
    return synthetic
