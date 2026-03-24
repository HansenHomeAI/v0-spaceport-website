"""Geo-temporal segmentation for large SfM jobs."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Sequence

from exif_manifest import ImageRecord


@dataclass(frozen=True)
class Segment:
    """A contiguous geo-temporal image segment with overlap metadata."""

    segment_id: str
    image_names: List[str]
    start_name: str
    end_name: str
    image_count: int
    overlap_with_previous: int
    overlap_with_next: int
    hard_break_before: bool


def build_segments(
    records: Sequence[ImageRecord],
    *,
    target_size: int,
    overlap: int,
    max_size: int,
    min_size: int,
) -> List[Segment]:
    """Split a manifest into overlapping segments."""
    if not records:
        return []

    hard_groups = _split_on_hard_gaps(records)
    segments: List[Segment] = []
    for group in hard_groups:
        windows = _window_group(
            group,
            target_size=target_size,
            overlap=overlap,
            max_size=max_size,
            min_size=min_size,
        )
        for window_index, window in enumerate(windows):
            overlap_with_previous = 0
            overlap_with_next = 0
            if window_index > 0:
                overlap_with_previous = min(overlap, len(window))
            if window_index < len(windows) - 1:
                overlap_with_next = min(overlap, len(window))
            segments.append(
                Segment(
                    segment_id=f"segment-{len(segments):03d}",
                    image_names=[record.name for record in window],
                    start_name=window[0].name,
                    end_name=window[-1].name,
                    image_count=len(window),
                    overlap_with_previous=overlap_with_previous,
                    overlap_with_next=overlap_with_next,
                    hard_break_before=window_index == 0 and segments != [],
                )
            )
    return segments


def segments_to_manifest(segments: Iterable[Segment]) -> List[Dict[str, object]]:
    """Serialize segments for JSON metadata."""
    return [
        {
            "segmentId": segment.segment_id,
            "imageCount": segment.image_count,
            "startImage": segment.start_name,
            "endImage": segment.end_name,
            "overlapWithPrevious": segment.overlap_with_previous,
            "overlapWithNext": segment.overlap_with_next,
            "hardBreakBefore": segment.hard_break_before,
            "imageNames": segment.image_names,
        }
        for segment in segments
    ]


def _split_on_hard_gaps(records: Sequence[ImageRecord]) -> List[List[ImageRecord]]:
    if len(records) <= 1:
        return [list(records)]

    distances = [_distance_m(records[index - 1], records[index]) for index in range(1, len(records))]
    time_gaps = [_time_gap_s(records[index - 1], records[index]) for index in range(1, len(records))]
    median_distance = _median([distance for distance in distances if distance > 0.0])
    median_time_gap = _median([gap for gap in time_gaps if gap > 0.0])
    relative_altitudes = [
        float(record.relative_altitude_m)
        for record in records
        if record.relative_altitude_m is not None
    ]
    median_relative_altitude = _median(relative_altitudes)

    distance_threshold = max(
        250.0,
        median_distance * 6.0 if median_distance else 0.0,
        median_relative_altitude * 8.0 if median_relative_altitude else 0.0,
    )
    time_threshold = max(45.0, median_time_gap * 8.0 if median_time_gap else 0.0)

    groups: List[List[ImageRecord]] = [[records[0]]]
    for previous, current in zip(records, records[1:]):
        distance = _distance_m(previous, current)
        time_gap = _time_gap_s(previous, current)
        if distance > distance_threshold or time_gap > time_threshold:
            groups.append([current])
            continue
        groups[-1].append(current)
    return groups


def _window_group(
    records: Sequence[ImageRecord],
    *,
    target_size: int,
    overlap: int,
    max_size: int,
    min_size: int,
) -> List[List[ImageRecord]]:
    count = len(records)
    if count <= max_size:
        return [list(records)]

    step = max(1, target_size - overlap)
    windows: List[List[ImageRecord]] = []
    start = 0
    while start < count:
        remaining = count - start
        if remaining <= max_size:
            window = list(records[start:])
            if windows and len(window) < min_size:
                start = max(0, count - max_size)
                window = list(records[start:])
                windows[-1] = window
            else:
                windows.append(window)
            break

        end = min(count, start + target_size)
        if count - end < min_size:
            end = count
        windows.append(list(records[start:end]))
        if end >= count:
            break
        start = max(0, end - overlap)

    deduped: List[List[ImageRecord]] = []
    seen = set()
    for window in windows:
        key = (window[0].name, window[-1].name, len(window))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(window)
    return deduped


def _distance_m(left: ImageRecord, right: ImageRecord) -> float:
    dx = right.enu_x_m - left.enu_x_m
    dy = right.enu_y_m - left.enu_y_m
    dz = right.enu_z_m - left.enu_z_m
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _time_gap_s(left: ImageRecord, right: ImageRecord) -> float:
    if not left.capture_time or not right.capture_time:
        return 0.0
    left_dt = datetime.fromisoformat(left.capture_time)
    right_dt = datetime.fromisoformat(right.capture_time)
    return abs((right_dt - left_dt).total_seconds())


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[midpoint])
    return float((ordered[midpoint - 1] + ordered[midpoint]) / 2.0)
