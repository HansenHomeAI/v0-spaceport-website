#!/usr/bin/env python3
"""GPU COLMAP SfM pipeline that exports the 3DGS-compatible sparse handoff."""

from __future__ import annotations

import json
import logging
import math
import os
import queue
import shutil
import signal
import sqlite3
import statistics
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, TextIO, Tuple


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

WGS84_COORDINATE_SYSTEM = 0
INF_COVARIANCE_BLOB = struct.pack("<9d", *([float("inf")] * 9))
EARTH_RADIUS_METERS = 6378137.0
MATCH_PROFILES = {
    "P1": {
        "spatial_neighbors": 12,
        "spatial_distance_m": 120.0,
        "sequential_overlap": 8,
    },
    "P2": {
        "spatial_neighbors": 14,
        "spatial_distance_m": 140.0,
        "sequential_overlap": 8,
    },
    "P3": {
        "spatial_neighbors": 16,
        "spatial_distance_m": 160.0,
        "sequential_overlap": 10,
    },
}
FEATURE_OPTION_FAMILIES = ("FeatureExtraction", "SiftExtraction")
MATCHING_OPTION_FAMILIES = ("FeatureMatching", "SiftMatching")


@dataclass
class ModelSummary:
    stage: str
    text_dir: Path
    cameras_registered: int
    images_registered: int
    points_3d: int
    binary_dir: Path = Path(".")
    image_count: int = 0
    partial_result: bool = False
    timed_out: bool = False
    image_names: List[str] = field(default_factory=list)


@dataclass
class ChunkPlan:
    index: int
    core_names: List[str]
    image_names: List[str]
    overlap_names: List[str]
    core_group_indices: List[int] = field(default_factory=list)
    group_indices: List[int] = field(default_factory=list)
    overlap_group_indices: List[int] = field(default_factory=list)
    segment_indices: List[int] = field(default_factory=list)


@dataclass
class ImageViewGeometry:
    file_name: str
    local_x_m: float
    local_y_m: float
    local_z_m: float
    heading_deg: float | None
    pitch_deg: float | None
    effective_altitude_m: float
    focal_length_mm: float | None
    focal_length_35mm_mm: float | None
    image_width_px: int | None
    image_height_px: int | None
    horizontal_fov_deg: float
    vertical_fov_deg: float
    is_shallow_view: bool


@dataclass
class CandidateEdge:
    first_name: str
    second_name: str
    score: float
    footprint_overlap: float
    scale_similarity: float
    viewpoint_complementarity: float
    distance_consistency: float
    temporal_bonus: float
    xy_distance_m: float
    xyz_distance_m: float
    view_delta_deg: float


@dataclass
class CaptureGroup:
    index: int
    image_names: List[str]
    centroid_x_m: float
    centroid_y_m: float
    centroid_z_m: float
    heading_deg: float | None
    pitch_deg: float | None
    start_capture_time_s: float | None
    end_capture_time_s: float | None

    @property
    def image_count(self) -> int:
        return len(self.image_names)


@dataclass
class FlightSegment:
    index: int
    group_indices: List[int]

    @property
    def start_group_index(self) -> int:
        return self.group_indices[0]

    @property
    def end_group_index(self) -> int:
        return self.group_indices[-1]


def log_memory(stage: str) -> None:
    """Emit lightweight memory diagnostics for SageMaker logs."""
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            header = "".join(next(handle) for _ in range(3))
        print(f"MEMORY_PROBE [{stage}]:\n{header}", flush=True)
    except Exception:
        pass


def count_text_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path, "r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip() and not line.startswith("#"))


def count_registered_images(images_txt: Path) -> int:
    return count_text_rows(images_txt) // 2


def load_registered_image_names(images_txt: Path) -> Set[str]:
    if not images_txt.exists():
        return set()
    registered_names: Set[str] = set()
    image_line = True
    with open(images_txt, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split()
            if image_line and len(parts) >= 10:
                registered_names.add(parts[9])
            image_line = not image_line
    return registered_names


def percentile(values: Sequence[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered_values = sorted(values)
    index = int(clamp(ratio, 0.0, 1.0) * (len(ordered_values) - 1))
    return float(ordered_values[index])


def point_track_length(parts: Sequence[str]) -> int:
    if len(parts) <= 8:
        return 0
    return max((len(parts) - 8) // 2, 0)


def rewrite_images_with_filtered_points(
    source_path: Path,
    output_path: Path,
    *,
    keep_point_ids: Set[int],
) -> None:
    image_line = True
    with open(source_path, "r", encoding="utf-8") as source, open(output_path, "w", encoding="utf-8") as target:
        for line in source:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                target.write(line)
                continue
            if image_line:
                target.write(line)
                image_line = False
                continue
            parts = stripped.split()
            if len(parts) % 3 != 0:
                target.write(line)
                image_line = True
                continue
            rewritten_parts: List[str] = []
            for index in range(0, len(parts), 3):
                rewritten_parts.extend(parts[index : index + 2])
                point_id_token = parts[index + 2]
                point_id = int(point_id_token)
                rewritten_parts.append(point_id_token if point_id < 0 or point_id in keep_point_ids else "-1")
            target.write(" ".join(rewritten_parts) + "\n")
            image_line = True


def stream_command(
    command: List[str],
    *,
    stage: str,
    env: Dict[str, str] | None = None,
    timeout_seconds: float | None = None,
    heartbeat_seconds: float | None = None,
) -> None:
    logger.info("[%s] %s", stage, " ".join(command))
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        bufsize=1,
        start_new_session=True,
    )
    assert process.stdout is not None
    output_queue: queue.Queue[str | None] = queue.Queue()

    def reader() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            output_queue.put(line.rstrip())
        output_queue.put(None)

    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    lines: List[str] = []
    started = time.monotonic()
    last_output_at = started
    next_heartbeat_at = (
        started + heartbeat_seconds if heartbeat_seconds is not None and heartbeat_seconds > 0 else None
    )
    timed_out_force_kill = False
    while True:
        now = time.monotonic()
        if timeout_seconds is not None and now - started > timeout_seconds:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                timed_out_force_kill = True
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            tail = "\n".join(lines[-50:])
            if timed_out_force_kill:
                tail = (
                    f"{tail}\n{stage} required SIGKILL after timeout and did not exit within the post-kill wait window"
                    if tail
                    else f"{stage} required SIGKILL after timeout and did not exit within the post-kill wait window"
                )
            raise RuntimeError(
                f"{stage} timed out after {timeout_seconds:.0f}s\n{tail}"
            )
        try:
            message = output_queue.get(timeout=1)
        except queue.Empty:
            if next_heartbeat_at is not None and now >= next_heartbeat_at:
                print(
                    f"COLMAP[{stage}] HEARTBEAT elapsed={int(now - started)}s "
                    f"idle={int(now - last_output_at)}s",
                    flush=True,
                )
                next_heartbeat_at = now + heartbeat_seconds
            if process.poll() is not None and not reader_thread.is_alive() and output_queue.empty():
                break
            continue
        if message is None:
            break
        lines.append(message)
        last_output_at = time.monotonic()
        print(f"COLMAP[{stage}] {message}", flush=True)
        if heartbeat_seconds is not None and heartbeat_seconds > 0:
            next_heartbeat_at = last_output_at + heartbeat_seconds
    return_code = process.wait()
    if return_code != 0:
        tail = "\n".join(lines[-50:])
        raise RuntimeError(f"{stage} failed with exit code {return_code}\n{tail}")


def unrecognized_option_error(error: RuntimeError, option_markers: Sequence[str]) -> bool:
    message = str(error)
    return "unrecognised option" in message and any(marker in message for marker in option_markers)


def pack_float64_blob(values: Iterable[float]) -> bytes:
    packed_values = [float(value) for value in values]
    return struct.pack(f"<{len(packed_values)}d", *packed_values)


def model_sort_key(model: ModelSummary) -> tuple[int, int, int]:
    return (model.images_registered, model.points_3d, model.cameras_registered)


def bridge_overlap_counts(
    registered_names: Set[str],
    target_name_sets: Sequence[Set[str]],
) -> tuple[int, int]:
    overlap_counts = [len(registered_names.intersection(target_names)) for target_names in target_name_sets]
    return (sum(1 for count in overlap_counts if count > 0), sum(overlap_counts))


def bridge_model_sort_key(
    model: ModelSummary,
    registered_names: Set[str],
    target_name_sets: Sequence[Set[str]],
) -> tuple[int, int, int, int, int]:
    target_count = len(target_name_sets)
    touched_targets, total_overlap = bridge_overlap_counts(registered_names, target_name_sets)
    return (
        1 if target_count > 0 and touched_targets >= target_count else 0,
        touched_targets,
        total_overlap,
        model.images_registered,
        model.points_3d,
    )


def is_bridge_model_stage(stage: str) -> bool:
    return "_merge_bridge_" in stage


def is_bridge_stage_prefix(stage_prefix: str) -> bool:
    return "_merge_bridge" in stage_prefix


def sort_capture_records(records: Iterable[dict[str, str]]) -> List[dict[str, str]]:
    def record_key(record: dict[str, str]) -> tuple[int, str, str]:
        capture_time = record.get("capture_time", "")
        file_name = record.get("file_name", "")
        if capture_time:
            return (0, capture_time, file_name.lower())
        return (1, file_name.lower(), "")

    return sorted(records, key=record_key)


def parse_optional_float(record: dict[str, object], keys: Sequence[str]) -> float | None:
    for key in keys:
        value = record.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def normalize_heading(angle_deg: float | None) -> float | None:
    if angle_deg is None:
        return None
    return float(angle_deg) % 360.0


def angular_distance_degrees(first_deg: float | None, second_deg: float | None) -> float:
    if first_deg is None or second_deg is None:
        return 90.0
    difference = abs(normalize_heading(first_deg) - normalize_heading(second_deg))
    return min(difference, 360.0 - difference)


def parse_capture_time_seconds(capture_time: str | None) -> float | None:
    if not capture_time:
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S.%f", "%Y:%m:%d %H:%M:%S"):
        try:
            return datetime.strptime(capture_time, fmt).timestamp()
        except ValueError:
            continue
    return None


def normalize_pitch(angle_deg: float | None) -> float | None:
    if angle_deg is None:
        return None
    return max(-90.0, min(90.0, float(angle_deg)))


def circular_dispersion_degrees(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    x_sum = 0.0
    y_sum = 0.0
    for value in values:
        radians = math.radians(normalize_heading(value) or 0.0)
        x_sum += math.cos(radians)
        y_sum += math.sin(radians)
    mean_heading = math.degrees(math.atan2(y_sum, x_sum))
    return max(angular_distance_degrees(value, mean_heading) for value in values)


def linear_dispersion(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return max(values) - min(values)


def view_vector(heading_deg: float | None, pitch_deg: float | None) -> tuple[float, float, float] | None:
    if heading_deg is None:
        return None
    yaw_radians = math.radians(normalize_heading(heading_deg) or 0.0)
    pitch_radians = math.radians(normalize_pitch(pitch_deg if pitch_deg is not None else 0.0) or 0.0)
    horizontal_scale = math.cos(pitch_radians)
    return (
        horizontal_scale * math.cos(yaw_radians),
        horizontal_scale * math.sin(yaw_radians),
        math.sin(pitch_radians),
    )


def angular_distance_between_vectors(
    first_vector: tuple[float, float, float] | None,
    second_vector: tuple[float, float, float] | None,
) -> float:
    if first_vector is None or second_vector is None:
        return 90.0
    dot_product = sum(first * second for first, second in zip(first_vector, second_vector))
    dot_product = max(-1.0, min(1.0, dot_product))
    return math.degrees(math.acos(dot_product))


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def normalize_unit_interval(value: float) -> float:
    return clamp(value, 0.0, 1.0)


def circle_overlap_score(
    first_center: tuple[float, float],
    first_radius: float,
    second_center: tuple[float, float],
    second_radius: float,
) -> float:
    if first_radius <= 0.0 or second_radius <= 0.0:
        return 0.0
    center_distance = math.hypot(first_center[0] - second_center[0], first_center[1] - second_center[1])
    return normalize_unit_interval(1.0 - (center_distance / max(first_radius + second_radius, 1e-6)))


def log_ratio_similarity(first_value: float, second_value: float) -> float:
    if first_value <= 0.0 or second_value <= 0.0:
        return 0.0
    return normalize_unit_interval(1.0 - abs(math.log(first_value / second_value)) / math.log(2.0))


class ColmapPipeline:
    def __init__(self, input_dir: Path, output_dir: Path) -> None:
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.work_dir = Path(tempfile.mkdtemp(prefix="colmap_sfm_"))
        self.images_dir = self.work_dir / "images"
        self.image_list_path = self.work_dir / "image_list.txt"
        self.database_path = self.work_dir / "database.db"
        self.vocab_tree_path = Path(
            os.environ.get(
                "COLMAP_VOCAB_TREE_PATH",
                "/opt/ml/code/resources/vocab_tree_flickr100K_words256K.bin",
            )
        )
        self.generated_vocab_tree_path = self.work_dir / "vocab_tree_faiss.bin"
        self.active_vocab_tree_path: Path | None = None
        self.vocab_tree_url = os.environ.get("COLMAP_VOCAB_TREE_URL", "")
        self.use_gpu = os.environ.get("COLMAP_USE_GPU", "1") != "0"
        self.feature_option_family = os.environ.get(
            "COLMAP_FEATURE_OPTION_FAMILY",
            FEATURE_OPTION_FAMILIES[0],
        )
        self.matching_option_family = os.environ.get(
            "COLMAP_MATCHING_OPTION_FAMILY",
            MATCHING_OPTION_FAMILIES[0],
        )
        self.enable_spatial_matcher = os.environ.get("COLMAP_ENABLE_SPATIAL_MATCHER", "1") != "0"
        self.enable_sequential_matcher = (
            os.environ.get("COLMAP_ENABLE_SEQUENTIAL_MATCHER", "1") != "0"
        )
        self.enable_spatial_chunking = (
            os.environ.get("COLMAP_ENABLE_SPATIAL_CHUNKING", "0") != "0"
        )
        self.chunk_planner = (
            os.environ.get("COLMAP_CHUNK_PLANNER", "legacy_spatial_heading").strip().lower()
            or "legacy_spatial_heading"
        )
        if self.chunk_planner not in {"legacy_spatial_heading", "footprint_graph_v1"}:
            raise RuntimeError(
                "Unsupported COLMAP_CHUNK_PLANNER="
                f"{self.chunk_planner}; expected one of legacy_spatial_heading, footprint_graph_v1"
            )
        self.force_gps_first = os.environ.get("COLMAP_FORCE_GPS_FIRST", "1") != "0"
        requested_match_profile = os.environ.get("COLMAP_MATCH_PROFILE", "P1").strip().upper() or "P1"
        if requested_match_profile not in MATCH_PROFILES:
            raise RuntimeError(
                f"Unsupported COLMAP_MATCH_PROFILE={requested_match_profile}; expected one of {sorted(MATCH_PROFILES)}"
            )
        profile_defaults = MATCH_PROFILES[requested_match_profile]
        self.max_features = int(os.environ.get("COLMAP_SIFT_MAX_NUM_FEATURES", "8192"))
        self.vocab_num_images = int(os.environ.get("COLMAP_VOCAB_NUM_IMAGES", "40"))
        self.vocab_num_visual_words = int(
            os.environ.get("COLMAP_VOCAB_BUILD_NUM_VISUAL_WORDS", "8192")
        )
        self.vocab_max_num_descriptors = int(
            os.environ.get("COLMAP_VOCAB_BUILD_MAX_NUM_DESCRIPTORS", "100000")
        )
        self.vocab_build_threads = os.environ.get(
            "COLMAP_VOCAB_BUILD_THREADS",
            os.environ.get("COLMAP_MAPPER_THREADS", "-1"),
        )
        self.spatial_neighbors = int(
            os.environ.get(
                "COLMAP_SPATIAL_MAX_NEIGHBORS",
                str(profile_defaults["spatial_neighbors"]),
            )
        )
        self.spatial_distance_m = float(
            os.environ.get(
                "COLMAP_SPATIAL_MAX_DISTANCE_METERS",
                str(profile_defaults["spatial_distance_m"]),
            )
        )
        self.sequential_overlap = int(
            os.environ.get(
                "COLMAP_SEQUENTIAL_OVERLAP",
                str(profile_defaults["sequential_overlap"]),
            )
        )
        self.chunk_target_images = int(os.environ.get("COLMAP_CHUNK_TARGET_IMAGES", "200"))
        self.chunk_min_images = int(os.environ.get("COLMAP_CHUNK_MIN_IMAGES", "120"))
        self.chunk_overlap_images = int(os.environ.get("COLMAP_CHUNK_OVERLAP_IMAGES", "30"))
        self.chunk_max_radius_m = float(os.environ.get("COLMAP_CHUNK_MAX_RADIUS_METERS", "300.0"))
        self.chunk_heading_weight = float(os.environ.get("COLMAP_CHUNK_HEADING_WEIGHT", "0.6"))
        self.chunk_hard_max_images = int(os.environ.get("COLMAP_CHUNK_HARD_MAX_IMAGES", "220"))
        self.chunk_pair_budget = int(os.environ.get("COLMAP_CHUNK_PAIR_BUDGET", "25000"))
        self.chunk_overlap_anchor_count = int(os.environ.get("COLMAP_CHUNK_OVERLAP_ANCHOR_COUNT", "20"))
        self.chunk_cross_edge_min_count = int(os.environ.get("COLMAP_CHUNK_CROSS_EDGE_MIN_COUNT", "12"))
        self.chunk_bridge_recovery_max_attempts = int(
            os.environ.get("COLMAP_CHUNK_BRIDGE_RECOVERY_MAX_ATTEMPTS", "2")
        )
        self.chunk_bridge_recovery_max_images = int(
            os.environ.get(
                "COLMAP_CHUNK_BRIDGE_RECOVERY_MAX_IMAGES",
                str(max(self.chunk_target_images * 3, 480)),
            )
        )
        self.chunk_bridge_representative_images = int(
            os.environ.get("COLMAP_CHUNK_BRIDGE_REPRESENTATIVE_IMAGES", "40")
        )
        self.chunk_bridge_cross_pairs_per_image = int(
            os.environ.get("COLMAP_CHUNK_BRIDGE_CROSS_PAIRS_PER_IMAGE", "6")
        )
        self.chunk_bridge_connector_images = int(
            os.environ.get("COLMAP_CHUNK_BRIDGE_CONNECTOR_IMAGES", "40")
        )
        self.chunk_bridge_connector_pairs_per_side = int(
            os.environ.get("COLMAP_CHUNK_BRIDGE_CONNECTOR_PAIRS_PER_SIDE", "4")
        )
        self.chunk_bridge_pair_score_threshold = float(
            os.environ.get("COLMAP_CHUNK_BRIDGE_PAIR_SCORE_THRESHOLD", "0.15")
        )
        self.parent_merge_mode = (
            os.environ.get("COLMAP_PARENT_MERGE_MODE", "seam_only_v1").strip().lower()
            or "seam_only_v1"
        )
        if self.parent_merge_mode not in {"legacy_rerun", "seam_only_v1"}:
            raise RuntimeError(
                "Unsupported COLMAP_PARENT_MERGE_MODE="
                f"{self.parent_merge_mode}; expected one of legacy_rerun, seam_only_v1"
            )
        self.parent_seam_registration_cycles = int(
            os.environ.get("COLMAP_PARENT_SEAM_REGISTRATION_CYCLES", "2")
        )
        self.parent_registrator_timeout_seconds = float(
            os.environ.get("COLMAP_PARENT_REGISTRATOR_TIMEOUT_SECONDS", "1800")
        )
        self.parent_triangulator_timeout_seconds = float(
            os.environ.get("COLMAP_PARENT_TRIANGULATOR_TIMEOUT_SECONDS", "3600")
        )
        self.filtered_sparse_core_min_track_len = int(
            os.environ.get("COLMAP_FILTERED_SPARSE_CORE_MIN_TRACK_LEN", "3")
        )
        self.filtered_sparse_core_max_reproj_error = float(
            os.environ.get("COLMAP_FILTERED_SPARSE_CORE_MAX_REPROJ_ERROR", "2.0")
        )
        self.filtered_sparse_far_context_max_reproj_error = float(
            os.environ.get("COLMAP_FILTERED_SPARSE_FAR_CONTEXT_MAX_REPROJ_ERROR", "1.0")
        )
        self.filtered_sparse_far_context_track_len = int(
            os.environ.get("COLMAP_FILTERED_SPARSE_FAR_CONTEXT_TRACK_LEN", "2")
        )
        self.filtered_sparse_absurd_outlier_multiplier = float(
            os.environ.get("COLMAP_FILTERED_SPARSE_ABSURD_OUTLIER_MULTIPLIER", "20.0")
        )
        self.filtered_sparse_absurd_outlier_floor = float(
            os.environ.get("COLMAP_FILTERED_SPARSE_ABSURD_OUTLIER_FLOOR", "1000.0")
        )
        self.graph_xy_neighbor_limit = int(os.environ.get("COLMAP_GRAPH_XY_NEIGHBOR_LIMIT", "60"))
        self.graph_xyz_neighbor_limit = int(os.environ.get("COLMAP_GRAPH_XYZ_NEIGHBOR_LIMIT", "20"))
        self.chunk_boundary_max_neighbors = int(
            os.environ.get(
                "COLMAP_CHUNK_BOUNDARY_MAX_NEIGHBORS",
                str(max(self.spatial_neighbors + 4, 18)),
            )
        )
        self.chunk_min_core_registered_ratio = float(
            os.environ.get("COLMAP_CHUNK_MIN_CORE_REGISTERED_RATIO", "0.90")
        )
        self.chunk_retry_group_context = int(
            os.environ.get("COLMAP_CHUNK_RETRY_GROUP_CONTEXT", "2")
        )
        self.enable_chunk_adjacent_merge_retry = (
            os.environ.get("COLMAP_CHUNK_ADJACENT_MERGE_RETRY", "1") != "0"
        )
        self.capture_group_max_time_gap_s = float(
            os.environ.get("COLMAP_CAPTURE_GROUP_MAX_TIME_GAP_SECONDS", "1.5")
        )
        self.capture_group_max_distance_m = float(
            os.environ.get("COLMAP_CAPTURE_GROUP_MAX_DISTANCE_METERS", "6.0")
        )
        self.capture_group_max_altitude_delta_m = float(
            os.environ.get("COLMAP_CAPTURE_GROUP_MAX_ALTITUDE_DELTA_METERS", "4.0")
        )
        self.capture_group_max_heading_delta_deg = float(
            os.environ.get("COLMAP_CAPTURE_GROUP_MAX_HEADING_DELTA_DEGREES", "12.0")
        )
        self.capture_group_max_pitch_delta_deg = float(
            os.environ.get("COLMAP_CAPTURE_GROUP_MAX_PITCH_DELTA_DEGREES", "10.0")
        )
        self.segment_break_heading_delta_deg = float(
            os.environ.get("COLMAP_SEGMENT_BREAK_HEADING_DELTA_DEGREES", "35.0")
        )
        self.segment_break_pitch_delta_deg = float(
            os.environ.get("COLMAP_SEGMENT_BREAK_PITCH_DELTA_DEGREES", "20.0")
        )
        self.segment_break_altitude_delta_m = float(
            os.environ.get("COLMAP_SEGMENT_BREAK_ALTITUDE_DELTA_METERS", "12.0")
        )
        self.segment_break_step_multiplier = float(
            os.environ.get("COLMAP_SEGMENT_BREAK_STEP_MULTIPLIER", "3.0")
        )
        raw_only_chunk_indexes = os.environ.get("COLMAP_ONLY_CHUNK_INDEXES", "").strip()
        self.only_chunk_indexes = {
            int(token.strip())
            for token in raw_only_chunk_indexes.split(",")
            if token.strip()
        }
        self.command_heartbeat_seconds = float(
            os.environ.get("COLMAP_COMMAND_HEARTBEAT_SECONDS", "60")
        )
        self.matcher_timeout_seconds = float(
            os.environ.get("COLMAP_MATCHER_TIMEOUT_SECONDS", "900")
        )
        self.chunk_mapper_timeout_seconds = float(
            os.environ.get("COLMAP_CHUNK_MAPPER_TIMEOUT_SECONDS", "2700")
        )
        self.bridge_mapper_timeout_seconds = float(
            os.environ.get("COLMAP_BRIDGE_MAPPER_TIMEOUT_SECONDS", "3600")
        )
        self.monolithic_mapper_timeout_seconds = float(
            os.environ.get("COLMAP_MONOLITHIC_MAPPER_TIMEOUT_SECONDS", "21600")
        )
        self.bundle_adjuster_timeout_seconds = float(
            os.environ.get("COLMAP_BUNDLE_ADJUSTER_TIMEOUT_SECONDS", "21600")
        )
        self.vocab_builder_timeout_seconds = float(
            os.environ.get("COLMAP_VOCAB_BUILDER_TIMEOUT_SECONDS", "900")
        )
        self.sqlite_busy_timeout_seconds = float(
            os.environ.get("COLMAP_SQLITE_BUSY_TIMEOUT_SECONDS", "60.0")
        )
        self.sqlite_lock_retry_count = int(
            os.environ.get("COLMAP_SQLITE_LOCK_RETRY_COUNT", "5")
        )
        self.sqlite_lock_retry_sleep_seconds = float(
            os.environ.get("COLMAP_SQLITE_LOCK_RETRY_SLEEP_SECONDS", "2.0")
        )
        if (
            self.enable_sequential_matcher
            and self.spatial_neighbors == profile_defaults["spatial_neighbors"]
            and self.spatial_distance_m == profile_defaults["spatial_distance_m"]
            and self.sequential_overlap == profile_defaults["sequential_overlap"]
        ):
            self.match_profile = requested_match_profile
        else:
            self.match_profile = "custom"
        self.gps_min_prior_coverage = float(os.environ.get("COLMAP_GPS_MIN_PRIOR_COVERAGE", "0.95"))
        self.gps_min_registered_ratio = float(
            os.environ.get("COLMAP_GPS_MIN_REGISTERED_RATIO", "0.98")
        )
        self.mapper_threads = os.environ.get("COLMAP_MAPPER_THREADS", "-1")
        self.start_time = time.time()
        self.timings: Dict[str, float] = {}
        self.dataset_image_count = 0
        self.gps_image_count = 0
        self.orientation_prior_count = 0
        self.pose_priors_written_count = 0
        self.gps_prior_coverage = 0.0
        self.pose_priors_source = "none"
        self.exif_records: Dict[str, Dict[str, float | str | None]] = {}
        self.capture_ordered_names: List[str] = []
        self.matchers_run: List[str] = []
        self.matcher_pair_deltas: Dict[str, int] = {}
        self.verified_pairs_total = 0
        self.vocab_tree_source = "uninitialized"
        self.fallback_triggered = False
        self.fallback_reason = "not_needed"
        self.final_matcher_mode = "uninitialized"
        self.chunk_matcher_strategy = "uninitialized"
        self.gps_first_attempted = False
        self.gps_first_skipped_reason = "uninitialized"
        self.chunking_attempted = False
        self.chunking_skipped_reason = "not_requested"
        self.pipeline_name = "colmap_gpu_adaptive_matching"
        self.model_summaries: List[Dict[str, int | str]] = []
        self.benchmark_subset_strategy = os.environ.get("SFM_BENCHMARK_SUBSET_STRATEGY", "")
        self.chunk_plans: List[ChunkPlan] = []
        self.chunk_sizes: List[int] = []
        self.chunk_overlap_image_count = 0
        self.chunk_mapper_seconds = 0.0
        self.chunk_merge_seconds = 0.0
        self.boundary_recovery_triggered = False
        self.adjacent_chunk_merge_triggered = False
        self.merge_bridge_recovery_triggered = False
        self.merged_component_count = 0
        self.chunk_groups: List[CaptureGroup] = []
        self.flight_segments: List[FlightSegment] = []
        self.image_group_indices: Dict[str, int] = {}
        self.chunk_group_count = 0
        self.chunk_segment_count = 0
        self.chunk_recovery_mode = "prior_aware_retry_no_vocab"
        self.failure_stage = ""
        self.failure_reason_detail = ""
        self.failed_chunk_index: int | None = None
        self.failed_chunk_registered_ratio = 0.0
        self.failed_chunk_core_registered_ratio = 0.0
        self.timed_out = False
        self.chunk_execution_image_count = 0
        self.capability_snapshot_only = os.environ.get("SFM_CAPABILITY_SNAPSHOT_ONLY", "0") == "1"
        self.planner_snapshot_only = os.environ.get("SFM_PLANNER_SNAPSHOT_ONLY", "0") == "1"
        self.heading_source_min_dispersion_deg = float(
            os.environ.get("COLMAP_HEADING_SOURCE_MIN_DISPERSION_DEGREES", "5.0")
        )
        self.pitch_source_min_dispersion_deg = float(
            os.environ.get("COLMAP_PITCH_SOURCE_MIN_DISPERSION_DEGREES", "3.0")
        )
        self.heading_prior_source = "uninitialized"
        self.pitch_prior_source = "uninitialized"
        self.heading_prior_dispersion_deg = 0.0
        self.pitch_prior_dispersion_deg = 0.0
        self.colmap_commands = self.detect_colmap_commands()
        self.colmap_capabilities = self.build_colmap_capabilities()
        self.view_geometries: Dict[str, ImageViewGeometry] = {}
        self.graph_neighbors: Dict[str, List[CandidateEdge]] = {}
        self.graph_edges_by_pair: Dict[Tuple[str, str], CandidateEdge] = {}
        self.chunk_role_by_image: Dict[str, str] = {}
        self.chunk_graph_probe_manifest: dict[str, object] = {}
        self.chunk_run_metrics: List[dict[str, object]] = []
        self.chunk_merge_proof: dict[str, object] = {}
        self.filtered_sparse_summary: dict[str, object] = {}
        self.probe_subset_details: Dict[str, dict[str, object]] = {}
        self.chunk_centroids: Dict[int, tuple[float, float]] = {}
        self.chunk_plans_by_index: Dict[int, ChunkPlan] = {}
        self.chunk_cross_edge_counts: Dict[Tuple[int, int], int] = {}
        self.probe_subsets: Dict[str, List[str]] = {}
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def resolve_timeout_seconds(self, timeout_seconds: float | None) -> float | None:
        if timeout_seconds is None or timeout_seconds <= 0:
            return None
        return timeout_seconds

    def mapper_timeout_seconds_for_stage(self, stage: str) -> float | None:
        if not stage.startswith("chunk_"):
            return self.resolve_timeout_seconds(self.monolithic_mapper_timeout_seconds)
        timeout_seconds = self.chunk_mapper_timeout_seconds
        if is_bridge_model_stage(stage):
            timeout_seconds = max(timeout_seconds, self.bridge_mapper_timeout_seconds)
        return self.resolve_timeout_seconds(timeout_seconds)

    def detect_colmap_commands(self) -> List[str]:
        try:
            result = subprocess.run(
                ["colmap", "help"],
                check=True,
                capture_output=True,
                text=True,
            )
        except Exception as exc:
            logger.warning("Unable to inspect COLMAP commands: %s", exc)
            return []
        commands: List[str] = []
        capture = False
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped == "Available commands:":
                capture = True
                continue
            if not capture or not stripped:
                continue
            if stripped.endswith(":"):
                continue
            if line.startswith("  "):
                commands.append(stripped.split()[0])
                continue
            break
        return sorted(set(commands))

    def build_colmap_capabilities(self) -> dict[str, object]:
        commands = set(self.colmap_commands)
        return {
            "available_commands": self.colmap_commands,
            "supports_matches_importer": "matches_importer" in commands,
            "supports_exhaustive_matcher": "exhaustive_matcher" in commands,
            "supports_pose_prior_mapper": "pose_prior_mapper" in commands,
            "supports_hierarchical_mapper": "hierarchical_mapper" in commands,
            "supports_global_mapper": "global_mapper" in commands,
        }

    def mark_failure(
        self,
        *,
        stage: str,
        reason: str,
        timed_out: bool = False,
        chunk_index: int | None = None,
        registered_ratio: float | None = None,
        core_registered_ratio: float | None = None,
    ) -> None:
        self.failure_stage = stage
        self.failure_reason_detail = reason
        self.timed_out = timed_out
        if chunk_index is not None:
            self.failed_chunk_index = chunk_index
        if registered_ratio is not None:
            self.failed_chunk_registered_ratio = round(registered_ratio, 4)
        if core_registered_ratio is not None:
            self.failed_chunk_core_registered_ratio = round(core_registered_ratio, 4)

    def write_failure_metadata(self) -> None:
        if self.chunk_planner == "footprint_graph_v1" and self.exif_records:
            self.write_chunk_planner_manifest()
        metadata = self.build_metadata(
            best_model=None,
            quality_check_passed=False,
        )
        metadata["failure_stage"] = self.failure_stage
        metadata["failure_reason_detail"] = self.failure_reason_detail
        metadata["timed_out"] = self.timed_out
        with open(self.output_dir / "sfm_metadata.json", "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)

    def clear_failure(self) -> None:
        self.failure_stage = ""
        self.failure_reason_detail = ""
        self.timed_out = False
        self.failed_chunk_index = None
        self.failed_chunk_registered_ratio = 0.0
        self.failed_chunk_core_registered_ratio = 0.0

    def run(self) -> int:
        try:
            if self.capability_snapshot_only:
                metadata = self.build_metadata(best_model=None, quality_check_passed=True)
                metadata["capability_snapshot_only"] = True
                metadata["planner_snapshot_only"] = False
                with open(self.output_dir / "sfm_metadata.json", "w", encoding="utf-8") as handle:
                    json.dump(metadata, handle, indent=2)
                return 0
            self.extract_images()
            self.exif_records = self.load_exif_records()
            self.gps_image_count = len(self.exif_records)
            self.orientation_prior_count = sum(
                1 for record in self.exif_records.values() if record.get("heading_deg") is not None
            )
            self.prepare_capture_ordered_image_list()
            if self.planner_snapshot_only:
                self.write_chunk_planner_manifest()
                metadata = self.build_metadata(best_model=None, quality_check_passed=True)
                metadata["capability_snapshot_only"] = False
                metadata["planner_snapshot_only"] = True
                with open(self.output_dir / "sfm_metadata.json", "w", encoding="utf-8") as handle:
                    json.dump(metadata, handle, indent=2)
                return 0
            self.run_feature_extraction()
            self.log_pose_prior_schema()
            self.validate_or_backfill_pose_priors()
            best_model = self.run_matching_and_mapping()
            self.export_output(best_model)
            return 0
        except Exception as exc:
            if not self.failure_stage:
                self.mark_failure(stage="pipeline", reason=str(exc), timed_out="timed out" in str(exc).lower())
            try:
                self.write_failure_metadata()
            except Exception:
                logger.exception("Failed to write failure metadata")
            logger.exception("COLMAP pipeline failed: %s", exc)
            return 1
        finally:
            if os.environ.get("COLMAP_KEEP_WORKDIR", "0") != "1":
                shutil.rmtree(self.work_dir, ignore_errors=True)

    def extract_images(self) -> None:
        started = time.time()
        zip_files = sorted(self.input_dir.glob("*.zip"))
        image_count = 0
        if zip_files:
            zip_path = zip_files[0]
            logger.info("Extracting archive %s", zip_path)
            with zipfile.ZipFile(zip_path, "r") as archive:
                for member in archive.namelist():
                    if not member.lower().endswith((".jpg", ".jpeg", ".png")):
                        continue
                    target_path = self.images_dir / Path(member).name
                    with archive.open(member) as source, open(target_path, "wb") as target:
                        shutil.copyfileobj(source, target)
                    image_count += 1
        else:
            for image_path in self.input_dir.rglob("*"):
                if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                    continue
                shutil.copy2(image_path, self.images_dir / image_path.name)
                image_count += 1
        if image_count == 0:
            raise RuntimeError("No images were found in the SfM input")
        self.dataset_image_count = image_count
        self.timings["extract_images_seconds"] = round(time.time() - started, 2)
        logger.info("Extracted %s images", image_count)

    def populate_local_coordinates(
        self, exif_records: Dict[str, Dict[str, float | str | None]]
    ) -> None:
        if not exif_records:
            return
        reference_record = next(iter(exif_records.values()))
        reference_lat = float(reference_record["gps_latitude"])
        reference_lon = float(reference_record["gps_longitude"])
        reference_alt = float(reference_record["gps_altitude"])
        cos_lat = math.cos(math.radians(reference_lat))
        for record in exif_records.values():
            latitude = float(record["gps_latitude"])
            longitude = float(record["gps_longitude"])
            altitude = float(record["gps_altitude"])
            delta_lat = math.radians(latitude - reference_lat)
            delta_lon = math.radians(longitude - reference_lon)
            record["local_x_m"] = EARTH_RADIUS_METERS * delta_lon * cos_lat
            record["local_y_m"] = EARTH_RADIUS_METERS * delta_lat
            record["local_z_m"] = altitude - reference_alt

    def load_exif_records(self) -> Dict[str, Dict[str, float | str | None]]:
        command = [
            "exiftool",
            "-j",
            "-n",
            "-r",
            "-FileName",
            "-DateTimeOriginal",
            "-SubSecDateTimeOriginal",
            "-CreateDate",
            "-GPSLatitude",
            "-GPSLongitude",
            "-GPSAltitude",
            "-AbsoluteAltitude",
            "-RelativeAltitude",
            "-GPSImgDirection",
            "-GimbalYawDegree",
            "-GimbalPitchDegree",
            "-GimbalRollDegree",
            "-FlightYawDegree",
            "-FlightPitchDegree",
            "-FlightRollDegree",
            "-FocalLength",
            "-FocalLengthIn35mmFormat",
            "-ExifImageWidth",
            "-ExifImageHeight",
            str(self.images_dir),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        records = json.loads(result.stdout or "[]")
        exif_records: Dict[str, Dict[str, float | str | None]] = {}
        for record in records:
            if "GPSLatitude" not in record or "GPSLongitude" not in record:
                continue
            file_name = record.get("FileName")
            if not file_name:
                continue
            gimbal_yaw_deg = normalize_heading(parse_optional_float(record, ["GimbalYawDegree"]))
            gps_img_direction_deg = normalize_heading(parse_optional_float(record, ["GPSImgDirection"]))
            flight_yaw_deg = normalize_heading(parse_optional_float(record, ["FlightYawDegree"]))
            gimbal_pitch_deg = normalize_pitch(parse_optional_float(record, ["GimbalPitchDegree"]))
            flight_pitch_deg = normalize_pitch(parse_optional_float(record, ["FlightPitchDegree"]))
            exif_records[file_name] = {
                "file_name": file_name,
                "gps_latitude": float(record["GPSLatitude"]),
                "gps_longitude": float(record["GPSLongitude"]),
                "gps_altitude": float(record.get("GPSAltitude", 0.0)),
                "absolute_altitude": parse_optional_float(record, ["AbsoluteAltitude"]),
                "relative_altitude": parse_optional_float(record, ["RelativeAltitude"]),
                "capture_time": (
                    record.get("SubSecDateTimeOriginal")
                    or record.get("DateTimeOriginal")
                    or record.get("CreateDate")
                    or ""
                ),
                "gimbal_yaw_deg": gimbal_yaw_deg,
                "gps_img_direction_deg": gps_img_direction_deg,
                "flight_yaw_deg": flight_yaw_deg,
                "heading_deg": None,
                "gimbal_pitch_deg": gimbal_pitch_deg,
                "gimbal_roll_deg": parse_optional_float(record, ["GimbalRollDegree"]),
                "flight_pitch_deg": flight_pitch_deg,
                "flight_roll_deg": parse_optional_float(record, ["FlightRollDegree"]),
                "focal_length_mm": parse_optional_float(record, ["FocalLength"]),
                "focal_length_35mm_mm": parse_optional_float(record, ["FocalLengthIn35mmFormat"]),
                "image_width_px": (
                    int(record["ExifImageWidth"])
                    if record.get("ExifImageWidth") not in (None, "")
                    else None
                ),
                "image_height_px": (
                    int(record["ExifImageHeight"])
                    if record.get("ExifImageHeight") not in (None, "")
                    else None
                ),
                "pitch_deg": None,
            }
            exif_records[file_name]["capture_time_s"] = parse_capture_time_seconds(
                str(exif_records[file_name]["capture_time"])
            )
        self.apply_orientation_prior_sources(exif_records)
        self.populate_local_coordinates(exif_records)
        logger.info(
            "Detected GPS EXIF priors on %s images; orientation priors present on %s images "
            "(heading_source=%s dispersion=%.2fdeg, pitch_source=%s dispersion=%.2fdeg)",
            len(exif_records),
            sum(1 for record in exif_records.values() if record.get("heading_deg") is not None),
            self.heading_prior_source,
            self.heading_prior_dispersion_deg,
            self.pitch_prior_source,
            self.pitch_prior_dispersion_deg,
        )
        return exif_records

    def select_orientation_source(
        self,
        exif_records: Dict[str, Dict[str, float | str | None]],
        *,
        candidates: Sequence[tuple[str, str]],
        circular: bool,
        min_dispersion_deg: float,
    ) -> tuple[str, float]:
        candidate_stats: List[tuple[str, str, float, float]] = []
        record_count = max(len(exif_records), 1)
        for record_key, source_name in candidates:
            values = [
                float(value)
                for record in exif_records.values()
                if (value := record.get(record_key)) is not None
            ]
            if not values:
                candidate_stats.append((record_key, source_name, 0.0, 0.0))
                continue
            dispersion_deg = (
                circular_dispersion_degrees(values)
                if circular
                else linear_dispersion(values)
            )
            coverage = len(values) / record_count
            candidate_stats.append((record_key, source_name, coverage, dispersion_deg))
        for record_key, source_name, coverage, dispersion_deg in candidate_stats:
            if coverage >= 0.5 and dispersion_deg >= min_dispersion_deg:
                return (record_key, dispersion_deg)
        best_record_key, best_source_name, best_coverage, best_dispersion_deg = max(
            candidate_stats,
            key=lambda item: (item[2], item[3], -candidates.index((item[0], item[1]))),
        )
        return (best_record_key, best_dispersion_deg)

    def apply_orientation_prior_sources(
        self,
        exif_records: Dict[str, Dict[str, float | str | None]],
    ) -> None:
        heading_record_key, heading_dispersion_deg = self.select_orientation_source(
            exif_records,
            candidates=(
                ("gps_img_direction_deg", "gps_img_direction"),
                ("gimbal_yaw_deg", "gimbal_yaw"),
                ("flight_yaw_deg", "flight_yaw"),
            ),
            circular=True,
            min_dispersion_deg=self.heading_source_min_dispersion_deg,
        )
        pitch_record_key, pitch_dispersion_deg = self.select_orientation_source(
            exif_records,
            candidates=(
                ("gimbal_pitch_deg", "gimbal_pitch"),
                ("flight_pitch_deg", "flight_pitch"),
            ),
            circular=False,
            min_dispersion_deg=self.pitch_source_min_dispersion_deg,
        )
        heading_source_names = {
            "gps_img_direction_deg": "gps_img_direction",
            "gimbal_yaw_deg": "gimbal_yaw",
            "flight_yaw_deg": "flight_yaw",
        }
        pitch_source_names = {
            "gimbal_pitch_deg": "gimbal_pitch",
            "flight_pitch_deg": "flight_pitch",
        }
        self.heading_prior_source = heading_source_names[heading_record_key]
        self.pitch_prior_source = pitch_source_names[pitch_record_key]
        self.heading_prior_dispersion_deg = round(heading_dispersion_deg, 2)
        self.pitch_prior_dispersion_deg = round(pitch_dispersion_deg, 2)
        for record in exif_records.values():
            record["heading_deg"] = record.get(heading_record_key)
            record["pitch_deg"] = record.get(pitch_record_key)

    def load_capture_records(self) -> List[dict[str, str]]:
        command = [
            "exiftool",
            "-j",
            "-FileName",
            "-DateTimeOriginal",
            "-SubSecDateTimeOriginal",
            "-CreateDate",
            str(self.images_dir),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        records = json.loads(result.stdout or "[]")
        capture_records: List[dict[str, str]] = []
        for record in records:
            file_name = record.get("FileName")
            if not file_name:
                continue
            capture_records.append(
                {
                    "file_name": file_name,
                    "capture_time": (
                        record.get("SubSecDateTimeOriginal")
                        or record.get("DateTimeOriginal")
                        or record.get("CreateDate")
                        or ""
                    ),
                }
            )
        return capture_records

    def prepare_capture_ordered_image_list(self) -> None:
        capture_records = sort_capture_records(self.load_capture_records())
        if capture_records:
            self.capture_ordered_names = [record["file_name"] for record in capture_records]
        else:
            self.capture_ordered_names = sorted(
                path.name
                for path in self.images_dir.iterdir()
                if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
            )
        if not self.capture_ordered_names:
            raise RuntimeError("Unable to determine image order for COLMAP processing")
        with open(self.image_list_path, "w", encoding="utf-8") as handle:
            for file_name in self.capture_ordered_names:
                handle.write(f"{file_name}\n")
        logger.info(
            "Prepared image list with %s entries ordered by capture time then filename",
            len(self.capture_ordered_names),
        )

    def estimate_field_of_view(
        self,
        *,
        focal_length_mm: float | None,
        focal_length_35mm_mm: float | None,
        sensor_extent_mm: float,
        image_extent_px: int | None,
    ) -> float:
        if focal_length_mm and focal_length_mm > 0.0:
            return math.degrees(2.0 * math.atan(sensor_extent_mm / (2.0 * focal_length_mm)))
        if focal_length_35mm_mm and focal_length_35mm_mm > 0.0:
            return math.degrees(2.0 * math.atan(36.0 / (2.0 * focal_length_35mm_mm)))
        if image_extent_px and image_extent_px > 0:
            return 73.74
        return 73.74

    def effective_altitude_for_record(self, record: Dict[str, float | str | None]) -> float:
        relative_altitude = record.get("relative_altitude")
        if relative_altitude is not None:
            return max(abs(float(relative_altitude)), 1.0)
        local_z_m = record.get("local_z_m")
        if local_z_m is not None:
            return max(abs(float(local_z_m)), 1.0)
        absolute_altitude = record.get("absolute_altitude")
        if absolute_altitude is not None:
            return max(abs(float(absolute_altitude)), 1.0)
        return 30.0

    def build_view_geometries(self) -> Dict[str, ImageViewGeometry]:
        if self.view_geometries:
            return self.view_geometries
        geometries: Dict[str, ImageViewGeometry] = {}
        for file_name, record in self.exif_records.items():
            focal_length_mm = (
                float(record["focal_length_mm"])
                if record.get("focal_length_mm") is not None
                else None
            )
            focal_length_35mm_mm = (
                float(record["focal_length_35mm_mm"])
                if record.get("focal_length_35mm_mm") is not None
                else None
            )
            image_width_px = (
                int(record["image_width_px"])
                if record.get("image_width_px") is not None
                else None
            )
            image_height_px = (
                int(record["image_height_px"])
                if record.get("image_height_px") is not None
                else None
            )
            horizontal_fov_deg = self.estimate_field_of_view(
                focal_length_mm=focal_length_mm,
                focal_length_35mm_mm=focal_length_35mm_mm,
                sensor_extent_mm=13.2,
                image_extent_px=image_width_px,
            )
            vertical_fov_deg = self.estimate_field_of_view(
                focal_length_mm=focal_length_mm,
                focal_length_35mm_mm=(
                    focal_length_35mm_mm * (24.0 / 36.0)
                    if focal_length_35mm_mm is not None
                    else None
                ),
                sensor_extent_mm=8.8,
                image_extent_px=image_height_px,
            )
            pitch_deg = float(record["pitch_deg"]) if record.get("pitch_deg") is not None else None
            geometries[file_name] = ImageViewGeometry(
                file_name=file_name,
                local_x_m=float(record["local_x_m"]),
                local_y_m=float(record["local_y_m"]),
                local_z_m=float(record.get("local_z_m", 0.0)),
                heading_deg=float(record["heading_deg"]) if record.get("heading_deg") is not None else None,
                pitch_deg=pitch_deg,
                effective_altitude_m=self.effective_altitude_for_record(record),
                focal_length_mm=focal_length_mm,
                focal_length_35mm_mm=focal_length_35mm_mm,
                image_width_px=image_width_px,
                image_height_px=image_height_px,
                horizontal_fov_deg=horizontal_fov_deg,
                vertical_fov_deg=vertical_fov_deg,
                is_shallow_view=(pitch_deg is not None and pitch_deg > -10.0),
            )
        self.view_geometries = geometries
        return geometries

    def footprint_circle_for_geometry(
        self,
        geometry: ImageViewGeometry,
        *,
        depth_factor: float,
    ) -> tuple[tuple[float, float], float]:
        effective_altitude_m = max(geometry.effective_altitude_m * depth_factor, 1.0)
        heading_radians = math.radians(normalize_heading(geometry.heading_deg) or 0.0)
        pitch_deg = geometry.pitch_deg if geometry.pitch_deg is not None else -35.0
        downward_pitch_deg = max(1.0, -pitch_deg) if pitch_deg <= -1.0 else 1.0
        shallow_cap_factor = 6.0 if geometry.is_shallow_view else 4.0
        forward_distance_m = min(
            effective_altitude_m / math.tan(math.radians(downward_pitch_deg)),
            geometry.effective_altitude_m * shallow_cap_factor,
        )
        center = (
            geometry.local_x_m + math.cos(heading_radians) * forward_distance_m,
            geometry.local_y_m + math.sin(heading_radians) * forward_distance_m,
        )
        radius_m = max(
            effective_altitude_m
            * math.tan(math.radians(max(geometry.horizontal_fov_deg, geometry.vertical_fov_deg) / 2.0)),
            geometry.effective_altitude_m * (2.0 if geometry.is_shallow_view else 0.75),
        )
        return center, radius_m

    def temporal_bonus_for_pair(
        self,
        first_name: str,
        second_name: str,
        *,
        view_delta_deg: float,
    ) -> float:
        first_record = self.exif_records[first_name]
        second_record = self.exif_records[second_name]
        first_time = first_record.get("capture_time_s")
        second_time = second_record.get("capture_time_s")
        if first_time is None or second_time is None:
            return 0.0
        time_gap_s = abs(float(first_time) - float(second_time))
        if time_gap_s > 2.0:
            return 0.0
        angular_velocity = view_delta_deg / max(time_gap_s, 0.1)
        if angular_velocity > 25.0:
            return 0.0
        return normalize_unit_interval(1.0 - time_gap_s / 2.0)

    def candidate_edge_for_names(
        self,
        first_name: str,
        second_name: str,
    ) -> CandidateEdge:
        pair_key = tuple(sorted((first_name, second_name)))
        cached = self.graph_edges_by_pair.get(pair_key)
        if cached is not None:
            return cached
        geometries = self.build_view_geometries()
        first_geometry = geometries[first_name]
        second_geometry = geometries[second_name]
        xy_distance_m = math.hypot(
            first_geometry.local_x_m - second_geometry.local_x_m,
            first_geometry.local_y_m - second_geometry.local_y_m,
        )
        xyz_distance_m = math.sqrt(
            (first_geometry.local_x_m - second_geometry.local_x_m) ** 2
            + (first_geometry.local_y_m - second_geometry.local_y_m) ** 2
            + (first_geometry.local_z_m - second_geometry.local_z_m) ** 2
        )
        footprint_overlap = max(
            circle_overlap_score(
                *self.footprint_circle_for_geometry(first_geometry, depth_factor=depth_factor),
                *self.footprint_circle_for_geometry(second_geometry, depth_factor=depth_factor),
            )
            for depth_factor in (0.75, 1.0, 1.5)
        )
        scale_similarity = log_ratio_similarity(
            max(first_geometry.effective_altitude_m, 1.0),
            max(second_geometry.effective_altitude_m, 1.0),
        )
        view_delta_deg = angular_distance_between_vectors(
            view_vector(first_geometry.heading_deg, first_geometry.pitch_deg),
            view_vector(second_geometry.heading_deg, second_geometry.pitch_deg),
        )
        if view_delta_deg <= 12.0:
            viewpoint_complementarity = 0.55 + 0.45 * (view_delta_deg / 12.0)
        elif view_delta_deg <= 70.0:
            viewpoint_complementarity = 1.0
        elif view_delta_deg <= 140.0:
            viewpoint_complementarity = max(0.15, 1.0 - ((view_delta_deg - 70.0) / 70.0))
        else:
            viewpoint_complementarity = 0.0
        target_distance_m = min(
            (first_geometry.effective_altitude_m + second_geometry.effective_altitude_m) / 2.0,
            120.0,
        )
        distance_consistency = normalize_unit_interval(
            1.0 - abs(xy_distance_m - target_distance_m) / max(target_distance_m, 1.0)
        )
        temporal_bonus = self.temporal_bonus_for_pair(first_name, second_name, view_delta_deg=view_delta_deg)
        score = (
            0.45 * footprint_overlap
            + 0.20 * scale_similarity
            + 0.20 * viewpoint_complementarity
            + 0.10 * distance_consistency
            + 0.05 * temporal_bonus
        )
        edge = CandidateEdge(
            first_name=pair_key[0],
            second_name=pair_key[1],
            score=round(score, 6),
            footprint_overlap=round(footprint_overlap, 6),
            scale_similarity=round(scale_similarity, 6),
            viewpoint_complementarity=round(viewpoint_complementarity, 6),
            distance_consistency=round(distance_consistency, 6),
            temporal_bonus=round(temporal_bonus, 6),
            xy_distance_m=round(xy_distance_m, 3),
            xyz_distance_m=round(xyz_distance_m, 3),
            view_delta_deg=round(view_delta_deg, 3),
        )
        self.graph_edges_by_pair[pair_key] = edge
        return edge

    def build_candidate_graph(self) -> Dict[str, List[CandidateEdge]]:
        if self.graph_neighbors:
            return self.graph_neighbors
        geometries = self.build_view_geometries()
        names = [name for name in self.capture_ordered_names if name in geometries]
        if not names:
            self.graph_neighbors = {}
            return self.graph_neighbors
        neighbors: Dict[str, List[CandidateEdge]] = {}
        for first_name in names:
            distances_xy: List[tuple[float, str]] = []
            distances_xyz: List[tuple[float, str]] = []
            first_geometry = geometries[first_name]
            for second_name in names:
                if second_name == first_name:
                    continue
                second_geometry = geometries[second_name]
                xy_distance_m = math.hypot(
                    first_geometry.local_x_m - second_geometry.local_x_m,
                    first_geometry.local_y_m - second_geometry.local_y_m,
                )
                xyz_distance_m = math.sqrt(
                    (first_geometry.local_x_m - second_geometry.local_x_m) ** 2
                    + (first_geometry.local_y_m - second_geometry.local_y_m) ** 2
                    + (first_geometry.local_z_m - second_geometry.local_z_m) ** 2
                )
                distances_xy.append((xy_distance_m, second_name))
                distances_xyz.append((xyz_distance_m, second_name))
            candidate_names = {
                second_name
                for _, second_name in sorted(distances_xy, key=lambda item: item[0])[: self.graph_xy_neighbor_limit]
            }
            candidate_names.update(
                second_name
                for _, second_name in sorted(distances_xyz, key=lambda item: item[0])[: self.graph_xyz_neighbor_limit]
            )
            candidate_edges = [
                self.candidate_edge_for_names(first_name, second_name)
                for second_name in sorted(candidate_names)
            ]
            neighbors[first_name] = sorted(candidate_edges, key=lambda edge: (-edge.score, edge.second_name, edge.first_name))
        self.graph_neighbors = neighbors
        return neighbors

    def classify_graph_roles(self) -> Dict[str, str]:
        if self.chunk_role_by_image:
            return self.chunk_role_by_image
        roles: Dict[str, str] = {}
        for image_name, edges in self.build_candidate_graph().items():
            strong_edges = [edge for edge in edges if edge.score >= 0.45]
            very_close_edges = [
                edge
                for edge in edges[:6]
                if edge.score >= 0.8 and edge.xy_distance_m <= 15.0 and edge.view_delta_deg <= 8.0
            ]
            max_view_delta = max((edge.view_delta_deg for edge in strong_edges), default=0.0)
            geometry = self.view_geometries[image_name]
            if len(very_close_edges) >= 3:
                roles[image_name] = "burst_redundant"
            elif len(strong_edges) >= 4 and max_view_delta >= 10.0:
                roles[image_name] = "geometry_anchor"
            elif geometry.is_shallow_view and len(strong_edges) < 3:
                roles[image_name] = "bridge_context"
            else:
                roles[image_name] = "bridge_context"
        self.chunk_role_by_image = roles
        return roles

    def representative_chunk_names(
        self,
        chunk_names: Sequence[str],
        roles: Dict[str, str],
        *,
        limit: int = 24,
    ) -> List[str]:
        if not chunk_names:
            return []
        centroid_x, centroid_y = self.centroid_for_names(chunk_names)
        ranked_names: List[tuple[int, float, float, int, str]] = []
        for image_name in chunk_names:
            if image_name not in self.exif_records or roles.get(image_name) == "burst_redundant":
                continue
            record = self.exif_records[image_name]
            edge_score = sum(edge.score for edge in self.graph_neighbors.get(image_name, [])[:12])
            distance_m = math.hypot(
                float(record["local_x_m"]) - centroid_x,
                float(record["local_y_m"]) - centroid_y,
            )
            ranked_names.append(
                (
                    0 if roles.get(image_name) == "geometry_anchor" else 1,
                    -edge_score,
                    distance_m,
                    self.capture_ordered_names.index(image_name),
                    image_name,
                )
            )
        if not ranked_names:
            return list(chunk_names[:limit])
        return [image_name for _, _, _, _, image_name in sorted(ranked_names)[:limit]]

    def bridge_anchor_scores(
        self,
        source_names: Sequence[str],
        target_names: Sequence[str],
        roles: Dict[str, str],
        *,
        limit: int = 24,
    ) -> List[tuple[float, str]]:
        if not source_names or not target_names:
            return []
        source_candidates = self.representative_chunk_names(source_names, roles, limit=max(limit * 2, 24))
        target_candidates = self.representative_chunk_names(target_names, roles, limit=max(limit * 2, 24))
        if not source_candidates or not target_candidates:
            return []
        ranked_scores: List[tuple[float, str]] = []
        for source_name in source_candidates:
            strongest_scores = sorted(
                (
                    self.candidate_edge_for_names(source_name, target_name).score
                    for target_name in target_candidates
                    if target_name != source_name
                ),
                reverse=True,
            )[:4]
            if not strongest_scores:
                continue
            ranked_scores.append((round(sum(strongest_scores), 6), source_name))
        return sorted(ranked_scores, key=lambda item: (-item[0], item[1]))

    def best_bridge_neighbor_index(
        self,
        *,
        chunk_index: int,
        core_chunks: Sequence[Sequence[str]],
        roles: Dict[str, str],
    ) -> int | None:
        if len(core_chunks) <= 1:
            return None
        source_names = core_chunks[chunk_index]
        source_centroid = self.centroid_for_names(source_names)
        ranked_neighbors: List[tuple[float, float, int]] = []
        for candidate_index, candidate_names in enumerate(core_chunks):
            if candidate_index == chunk_index:
                continue
            bridge_scores = self.bridge_anchor_scores(source_names, candidate_names, roles, limit=8)
            bridge_score = bridge_scores[0][0] if bridge_scores else 0.0
            candidate_centroid = self.centroid_for_names(candidate_names)
            centroid_distance = math.hypot(
                source_centroid[0] - candidate_centroid[0],
                source_centroid[1] - candidate_centroid[1],
            )
            ranked_neighbors.append((-bridge_score, centroid_distance, candidate_index))
        if not ranked_neighbors:
            return None
        return min(ranked_neighbors)[2]

    def ensure_chunk_overlap_connectivity(
        self,
        *,
        core_chunks: Sequence[Sequence[str]],
        overlap_assignments: Dict[int, Set[str]],
        image_membership_count: Dict[str, int],
        roles: Dict[str, str],
    ) -> None:
        if len(core_chunks) <= 1:
            return

        def chunk_image_name_sets() -> List[Set[str]]:
            return [set(chunk_names).union(overlap_assignments.get(index, set())) for index, chunk_names in enumerate(core_chunks)]

        iteration_budget = max(len(core_chunks) * 2, 1)
        while iteration_budget > 0:
            image_name_sets = chunk_image_name_sets()
            isolated_indexes = [
                index
                for index, image_names in enumerate(image_name_sets)
                if not any(image_names.intersection(other_names) for other_index, other_names in enumerate(image_name_sets) if other_index != index)
            ]
            if not isolated_indexes:
                return
            changed = False
            for chunk_index in isolated_indexes:
                neighbor_index = self.best_bridge_neighbor_index(
                    chunk_index=chunk_index,
                    core_chunks=core_chunks,
                    roles=roles,
                )
                if neighbor_index is None:
                    continue
                pair_anchor_target = max(
                    self.chunk_overlap_anchor_count,
                    min(max(min(len(core_chunks[chunk_index]), len(core_chunks[neighbor_index])) // 3, 24), 60),
                )
                candidate_sets = (
                    (
                        chunk_index,
                        neighbor_index,
                        self.bridge_anchor_scores(core_chunks[chunk_index], image_name_sets[neighbor_index], roles, limit=pair_anchor_target),
                    ),
                    (
                        neighbor_index,
                        chunk_index,
                        self.bridge_anchor_scores(core_chunks[neighbor_index], image_name_sets[chunk_index], roles, limit=pair_anchor_target),
                    ),
                )
                for source_index, target_index, candidate_scores in candidate_sets:
                    for _, image_name in candidate_scores:
                        if len(image_name_sets[chunk_index].intersection(image_name_sets[neighbor_index])) >= pair_anchor_target:
                            break
                        if image_membership_count[image_name] >= 3:
                            continue
                        if image_name in image_name_sets[target_index]:
                            continue
                        overlap_assignments[target_index].add(image_name)
                        image_membership_count[image_name] += 1
                        image_name_sets[target_index].add(image_name)
                        changed = True
            if not changed:
                return
            iteration_budget -= 1

    def count_verified_pairs(self, database_path: Path | None = None) -> int:
        active_database_path = database_path or self.database_path
        if not active_database_path.exists():
            return 0
        with sqlite3.connect(active_database_path) as connection:
            row = connection.execute("SELECT COUNT(*) FROM two_view_geometries").fetchone()
        return int(row[0] if row else 0)

    def count_pose_priors(self, database_path: Path | None = None) -> int:
        active_database_path = database_path or self.database_path
        if not active_database_path.exists():
            return 0
        with sqlite3.connect(active_database_path) as connection:
            row = connection.execute("SELECT COUNT(*) FROM pose_priors").fetchone()
        return int(row[0] if row else 0)

    def count_database_images(self, database_path: Path | None = None) -> int:
        active_database_path = database_path or self.database_path
        if not active_database_path.exists():
            return 0
        with sqlite3.connect(active_database_path) as connection:
            row = connection.execute("SELECT COUNT(*) FROM images").fetchone()
        return int(row[0] if row else 0)

    def get_image_ids_by_name(self, database_path: Path | None = None) -> Dict[str, int]:
        active_database_path = database_path or self.database_path
        with sqlite3.connect(active_database_path) as connection:
            rows = connection.execute("SELECT image_id, name FROM images").fetchall()
        return {str(name): int(image_id) for image_id, name in rows}

    def get_table_columns(self, table_name: str, database_path: Path | None = None) -> set[str]:
        active_database_path = database_path or self.database_path
        with sqlite3.connect(active_database_path) as connection:
            rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row[1]) for row in rows}

    def pose_priors_columns(self, database_path: Path | None = None) -> set[str]:
        return self.get_table_columns("pose_priors", database_path=database_path)

    def supports_pose_prior_image_backfill(self, database_path: Path | None = None) -> bool:
        return "image_id" in self.pose_priors_columns(database_path=database_path)

    def pose_prior_schema_variant(self, database_path: Path | None = None) -> str:
        columns = self.pose_priors_columns(database_path=database_path)
        if "image_id" in columns:
            return "image_id"
        if "pose_prior_id" in columns:
            return "pose_prior_id"
        return "unknown"

    def log_pose_prior_schema(self, database_path: Path | None = None) -> None:
        logger.info(
            "COLMAP pose_priors schema variant=%s columns=%s",
            self.pose_prior_schema_variant(database_path=database_path),
            sorted(self.pose_priors_columns(database_path=database_path)),
        )

    def get_pose_prior_image_names(self, database_path: Path | None = None) -> set[str]:
        active_database_path = database_path or self.database_path
        columns = self.pose_priors_columns(database_path=active_database_path)
        if "image_id" not in columns:
            logger.warning("COLMAP pose_priors table is missing image_id; columns=%s", sorted(columns))
            return set()
        with sqlite3.connect(active_database_path) as connection:
            rows = connection.execute(
                """
                SELECT images.name
                FROM images
                INNER JOIN pose_priors USING(image_id)
                """
            ).fetchall()
        return {str(row[0]) for row in rows}

    def backfill_pose_priors_from_exif(
        self,
        *,
        database_path: Path | None = None,
        exif_records: Dict[str, Dict[str, float | str | None]] | None = None,
    ) -> int:
        active_database_path = database_path or self.database_path
        active_exif_records = exif_records or self.exif_records
        if not active_exif_records:
            return 0
        if not self.supports_pose_prior_image_backfill(database_path=active_database_path):
            logger.info(
                "Skipping manual pose prior backfill for schema columns=%s",
                sorted(self.pose_priors_columns(database_path=active_database_path)),
            )
            return 0
        image_ids_by_name = self.get_image_ids_by_name(database_path=active_database_path)
        existing_names = self.get_pose_prior_image_names(database_path=active_database_path)
        rows_to_insert: List[tuple[int, sqlite3.Binary, int, sqlite3.Binary]] = []
        for file_name, record in active_exif_records.items():
            image_id = image_ids_by_name.get(file_name)
            if image_id is None or file_name in existing_names:
                continue
            position_blob = sqlite3.Binary(
                pack_float64_blob(
                    [
                        float(record["gps_latitude"]),
                        float(record["gps_longitude"]),
                        float(record["gps_altitude"]),
                    ]
                )
            )
            rows_to_insert.append(
                (
                    image_id,
                    position_blob,
                    WGS84_COORDINATE_SYSTEM,
                    sqlite3.Binary(INF_COVARIANCE_BLOB),
                )
            )
        if not rows_to_insert:
            return 0
        with sqlite3.connect(active_database_path) as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO pose_priors (
                    image_id,
                    position,
                    coordinate_system,
                    position_covariance
                ) VALUES (?, ?, ?, ?)
                """,
                rows_to_insert,
            )
            connection.commit()
        logger.info("Backfilled %s COLMAP pose priors from EXIF metadata", len(rows_to_insert))
        return len(rows_to_insert)

    def validate_or_backfill_pose_priors(
        self,
        *,
        database_path: Path | None = None,
        exif_records: Dict[str, Dict[str, float | str | None]] | None = None,
        gps_image_count: int | None = None,
    ) -> tuple[int, float, str]:
        active_database_path = database_path or self.database_path
        active_exif_records = exif_records or self.exif_records
        active_gps_image_count = (
            gps_image_count
            if gps_image_count is not None
            else (self.gps_image_count if active_database_path == self.database_path else len(active_exif_records))
        )
        if active_gps_image_count == 0:
            if active_database_path == self.database_path:
                self.pose_priors_source = "no_gps_exif"
                self.pose_priors_written_count = 0
                self.gps_prior_coverage = 0.0
            return (0, 0.0, "no_gps_exif")

        before_backfill = self.count_pose_priors(active_database_path)
        if before_backfill == 0 and self.supports_pose_prior_image_backfill(database_path=active_database_path):
            backfilled_count = self.backfill_pose_priors_from_exif(
                database_path=active_database_path,
                exif_records=active_exif_records,
            )
            after_backfill = self.count_pose_priors(active_database_path)
        else:
            backfilled_count = 0
            after_backfill = before_backfill

        gps_prior_coverage = round(after_backfill / active_gps_image_count, 4)
        if backfilled_count > 0 and before_backfill > 0:
            pose_priors_source = "feature_extractor_plus_backfill"
        elif backfilled_count > 0:
            pose_priors_source = "backfilled_from_exif"
        elif before_backfill > 0:
            pose_priors_source = "feature_extractor"
        elif after_backfill == 0 and not self.supports_pose_prior_image_backfill(database_path=active_database_path):
            pose_priors_source = "unsupported_pose_prior_schema"
        else:
            pose_priors_source = "missing"

        logger.info(
            "COLMAP pose priors available for %s/%s GPS-tagged images (coverage %.2f%%, source=%s)",
            after_backfill,
            active_gps_image_count,
            gps_prior_coverage * 100.0,
            pose_priors_source,
        )

        if active_database_path == self.database_path:
            self.pose_priors_written_count = after_backfill
            self.gps_prior_coverage = gps_prior_coverage
            self.pose_priors_source = pose_priors_source
        return (after_backfill, gps_prior_coverage, pose_priors_source)

    def ensure_vocab_tree(self) -> None:
        started = time.time()
        if self.vocab_tree_path.exists() and self.vocab_tree_path.stat().st_size > 0:
            logger.info("Using cached vocab tree at %s", self.vocab_tree_path)
            self.timings.setdefault("download_vocab_tree_seconds", 0.0)
            self.active_vocab_tree_path = self.vocab_tree_path
            self.vocab_tree_source = "downloaded_cached"
            return
        if not self.vocab_tree_url:
            logger.info(
                "No external vocab tree configured; letting COLMAP auto-download a compatible FAISS tree first"
            )
            self.timings.setdefault("download_vocab_tree_seconds", 0.0)
            self.vocab_tree_source = "colmap_auto_download"
            return
        self.vocab_tree_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading vocab tree from %s", self.vocab_tree_url)
        try:
            stream_command(
                [
                    "curl",
                    "-fL",
                    self.vocab_tree_url,
                    "-o",
                    str(self.vocab_tree_path),
                ],
                stage="download_vocab_tree",
                timeout_seconds=self.resolve_timeout_seconds(self.vocab_builder_timeout_seconds),
                heartbeat_seconds=self.command_heartbeat_seconds,
            )
        except RuntimeError as error:
            self.handle_stage_runtime_error("download_vocab_tree", error)
            raise
        if not self.vocab_tree_path.exists() or self.vocab_tree_path.stat().st_size == 0:
            raise RuntimeError("Vocabulary tree download produced an empty file")
        self.timings["download_vocab_tree_seconds"] = round(time.time() - started, 2)
        self.active_vocab_tree_path = self.vocab_tree_path
        self.vocab_tree_source = "downloaded"

    def build_vocab_tree(self, *, database_path: Path | None = None) -> None:
        active_database_path = database_path or self.database_path
        started = time.time()
        max_num_images = max(1, min(self.vocab_num_images, self.count_database_images(active_database_path)))
        logger.info(
            "Building a FAISS-compatible vocab tree with %s visual words from up to %s descriptors",
            self.vocab_num_visual_words,
            self.vocab_max_num_descriptors,
        )
        builder_commands = [
            [
                "colmap",
                "vocab_tree_builder",
                "--database_path",
                str(active_database_path),
                "--vocab_tree_path",
                str(self.generated_vocab_tree_path),
                "--num_visual_words",
                str(self.vocab_num_visual_words),
                "--max_num_images",
                str(max_num_images),
            ],
            [
                "colmap",
                "vocab_tree_builder",
                "--database_path",
                str(active_database_path),
                "--vocab_tree_path",
                str(self.generated_vocab_tree_path),
                "--num_visual_words",
                str(self.vocab_num_visual_words),
            ],
        ]
        last_error: RuntimeError | None = None
        for command in builder_commands:
            try:
                stream_command(
                    command,
                    stage="vocab_tree_builder",
                    timeout_seconds=self.resolve_timeout_seconds(self.vocab_builder_timeout_seconds),
                    heartbeat_seconds=self.command_heartbeat_seconds,
                )
                break
            except RuntimeError as error:
                if "--max_num_images" in command and unrecognized_option_error(error, ["--max_num_images"]):
                    logger.warning(
                        "vocab_tree_builder rejected --max_num_images; retrying with older COLMAP-compatible flags"
                    )
                    last_error = error
                    continue
                self.handle_stage_runtime_error("vocab_tree_builder", error)
                raise
        else:
            if last_error is not None:
                raise last_error
            raise RuntimeError("vocab_tree_builder failed before any command could be executed")
        if (
            not self.generated_vocab_tree_path.exists()
            or self.generated_vocab_tree_path.stat().st_size == 0
        ):
            raise RuntimeError("COLMAP vocab_tree_builder produced an empty index")
        self.timings["build_vocab_tree_seconds"] = round(time.time() - started, 2)
        if self.active_vocab_tree_path == self.vocab_tree_path:
            self.vocab_tree_source = "rebuilt_from_downloaded_legacy_tree"
        else:
            self.vocab_tree_source = "built_from_database"
        self.active_vocab_tree_path = self.generated_vocab_tree_path

    def run_vocab_tree_matcher(
        self, *, database_path: Path, stage: str, num_images: int | None = None
    ) -> None:
        self.ensure_vocab_tree()
        matching_family = self.run_with_option_family_fallback(
            stage=stage,
            families=MATCHING_OPTION_FAMILIES,
            preferred_family=self.matching_option_family,
            build_command=lambda family: (
                [
                    "colmap",
                    "vocab_tree_matcher",
                    "--database_path",
                    str(database_path),
                    f"--{family}.use_gpu",
                    "1" if self.use_gpu else "0",
                    f"--{family}.guided_matching",
                    "1",
                    "--VocabTreeMatching.num_images",
                    str(num_images if num_images is not None else self.vocab_num_images),
                    *(
                        [
                            "--VocabTreeMatching.vocab_tree_path",
                            str(self.active_vocab_tree_path),
                        ]
                        if self.active_vocab_tree_path is not None
                        else []
                    ),
                ],
                [f"--{family}.use_gpu", f"--{family}.guided_matching"],
            ),
            timeout_seconds=self.matcher_timeout_seconds,
        )
        self.matching_option_family = matching_family

    def run_feature_extraction(
        self,
        *,
        database_path: Path | None = None,
        image_list_path: Path | None = None,
        stage: str = "feature_extractor",
    ) -> None:
        active_database_path = database_path or self.database_path
        started = time.time()
        max_image_size = os.environ.get("COLMAP_FEATURE_MAX_IMAGE_SIZE")
        feature_family = self.run_with_option_family_fallback(
            stage=stage,
            families=FEATURE_OPTION_FAMILIES,
            preferred_family=self.feature_option_family,
            build_command=lambda family: (
                [
                    "colmap",
                    "feature_extractor",
                    "--database_path",
                    str(active_database_path),
                    "--image_path",
                    str(self.images_dir),
                    "--ImageReader.single_camera",
                    "1",
                    "--ImageReader.camera_model",
                    "SIMPLE_RADIAL",
                    f"--{family}.use_gpu",
                    "1" if self.use_gpu else "0",
                    "--SiftExtraction.max_num_features",
                    str(self.max_features),
                    *(["--image_list_path", str(image_list_path)] if image_list_path is not None else []),
                    *([f"--{family}.max_image_size", max_image_size] if max_image_size else []),
                ],
                [f"--{family}.use_gpu", f"--{family}.max_image_size"],
            ),
            timeout_seconds=self.monolithic_mapper_timeout_seconds,
        )
        self.feature_option_family = feature_family
        self.timings[f"{stage}_seconds"] = round(time.time() - started, 2)

    def should_attempt_gps_first(self) -> bool:
        if not self.enable_spatial_matcher:
            self.gps_first_skipped_reason = "spatial_matcher_disabled"
            return False
        if not self.force_gps_first:
            self.gps_first_skipped_reason = "gps_first_disabled"
            return False
        if self.gps_image_count == 0:
            self.gps_first_skipped_reason = "no_gps_exif"
            return False
        if self.gps_prior_coverage < self.gps_min_prior_coverage:
            self.gps_first_skipped_reason = "insufficient_pose_prior_coverage"
            return False
        self.gps_first_skipped_reason = "eligible"
        return True

    def should_attempt_spatial_chunking(self) -> bool:
        if not self.enable_spatial_chunking:
            self.chunking_skipped_reason = "chunking_disabled"
            return False
        if not self.should_attempt_gps_first():
            self.chunking_skipped_reason = self.gps_first_skipped_reason
            return False
        if self.dataset_image_count <= max(self.chunk_target_images, self.chunk_min_images):
            self.chunking_skipped_reason = "dataset_too_small"
            return False
        self.chunking_skipped_reason = "eligible"
        return True

    def record_matcher_delta(self, label: str, delta: int) -> None:
        self.matcher_pair_deltas[label] = self.matcher_pair_deltas.get(label, 0) + delta
        self.matchers_run.append(label)

    def ordered_option_families(self, preferred: str, families: Sequence[str]) -> List[str]:
        if preferred in families:
            return [preferred, *[family for family in families if family != preferred]]
        return list(families)

    def handle_stage_runtime_error(self, stage: str, error: RuntimeError) -> None:
        self.mark_failure(
            stage=stage,
            reason=str(error),
            timed_out="timed out" in str(error).lower(),
            chunk_index=self.failed_chunk_index,
        )

    def run_with_option_family_fallback(
        self,
        *,
        stage: str,
        families: Sequence[str],
        preferred_family: str,
        build_command,
        timeout_seconds: float | None,
    ) -> str:
        last_error: RuntimeError | None = None
        for family in self.ordered_option_families(preferred_family, families):
            command, option_markers = build_command(family)
            try:
                stream_command(
                    command,
                    stage=stage,
                    timeout_seconds=self.resolve_timeout_seconds(timeout_seconds),
                    heartbeat_seconds=self.command_heartbeat_seconds,
                )
                return family
            except RuntimeError as error:
                if unrecognized_option_error(error, option_markers):
                    logger.warning(
                        "%s rejected %s-style COLMAP flags; retrying with a different option family",
                        stage,
                        family,
                    )
                    last_error = error
                    continue
                self.handle_stage_runtime_error(stage, error)
                raise
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"{stage} failed before any COLMAP command could be attempted")

    def run_spatial_matcher(
        self,
        *,
        database_path: Path | None = None,
        stage: str = "spatial_matcher",
        label: str = "spatial_matcher",
        max_neighbors: int | None = None,
        max_distance_m: float | None = None,
    ) -> None:
        active_database_path = database_path or self.database_path
        started = time.time()
        pairs_before = self.count_verified_pairs(active_database_path)
        matching_family = self.run_with_option_family_fallback(
            stage=stage,
            families=MATCHING_OPTION_FAMILIES,
            preferred_family=self.matching_option_family,
            build_command=lambda family: (
                [
                    "colmap",
                    "spatial_matcher",
                    "--database_path",
                    str(active_database_path),
                    f"--{family}.use_gpu",
                    "1" if self.use_gpu else "0",
                    f"--{family}.guided_matching",
                    "1",
                    "--SpatialMatching.ignore_z",
                    "0",
                    "--SpatialMatching.max_num_neighbors",
                    str(max_neighbors if max_neighbors is not None else self.spatial_neighbors),
                    "--SpatialMatching.max_distance",
                    str(max_distance_m if max_distance_m is not None else self.spatial_distance_m),
                ],
                [f"--{family}.use_gpu", f"--{family}.guided_matching"],
            ),
            timeout_seconds=self.matcher_timeout_seconds,
        )
        self.matching_option_family = matching_family
        pairs_after = self.count_verified_pairs(active_database_path)
        self.timings[f"{stage}_seconds"] = round(time.time() - started, 2)
        self.record_matcher_delta(label, pairs_after - pairs_before)
        self.verified_pairs_total = max(self.verified_pairs_total, pairs_after)
        logger.info("%s added %s verified image pairs", stage, pairs_after - pairs_before)

    def run_sequential_matcher(
        self,
        *,
        database_path: Path | None = None,
        stage: str = "sequential_matcher",
        label: str = "sequential_matcher",
        overlap: int | None = None,
    ) -> None:
        active_database_path = database_path or self.database_path
        started = time.time()
        pairs_before = self.count_verified_pairs(active_database_path)
        try:
            stream_command(
                [
                    "colmap",
                    "sequential_matcher",
                    "--database_path",
                    str(active_database_path),
                    "--SequentialMatching.overlap",
                    str(overlap if overlap is not None else self.sequential_overlap),
                    "--SequentialMatching.quadratic_overlap",
                    "1",
                    "--SequentialMatching.loop_detection",
                    "0",
                ],
                stage=stage,
                timeout_seconds=self.resolve_timeout_seconds(self.matcher_timeout_seconds),
                heartbeat_seconds=self.command_heartbeat_seconds,
            )
        except RuntimeError as error:
            self.handle_stage_runtime_error(stage, error)
            raise
        pairs_after = self.count_verified_pairs(active_database_path)
        self.timings[f"{stage}_seconds"] = round(time.time() - started, 2)
        self.record_matcher_delta(label, pairs_after - pairs_before)
        self.verified_pairs_total = max(self.verified_pairs_total, pairs_after)
        logger.info("%s added %s verified image pairs", stage, pairs_after - pairs_before)

    def run_exhaustive_matcher(
        self,
        *,
        database_path: Path | None = None,
        stage: str = "exhaustive_matcher",
        label: str = "exhaustive_matcher",
    ) -> None:
        active_database_path = database_path or self.database_path
        started = time.time()
        pairs_before = self.count_verified_pairs(active_database_path)
        matching_family = self.run_with_option_family_fallback(
            stage=stage,
            families=MATCHING_OPTION_FAMILIES,
            preferred_family=self.matching_option_family,
            build_command=lambda family: (
                [
                    "colmap",
                    "exhaustive_matcher",
                    "--database_path",
                    str(active_database_path),
                    f"--{family}.use_gpu",
                    "1" if self.use_gpu else "0",
                    f"--{family}.guided_matching",
                    "1",
                ],
                [f"--{family}.use_gpu", f"--{family}.guided_matching"],
            ),
            timeout_seconds=self.matcher_timeout_seconds,
        )
        self.matching_option_family = matching_family
        pairs_after = self.count_verified_pairs(active_database_path)
        self.timings[f"{stage}_seconds"] = round(time.time() - started, 2)
        self.record_matcher_delta(label, pairs_after - pairs_before)
        self.verified_pairs_total = max(self.verified_pairs_total, pairs_after)
        logger.info("%s added %s verified image pairs", stage, pairs_after - pairs_before)

    def sorted_capture_names(self, names: Iterable[str]) -> List[str]:
        capture_order_index = {
            image_name: position for position, image_name in enumerate(self.capture_ordered_names)
        }
        return sorted(
            {name for name in names if name in self.exif_records},
            key=lambda image_name: capture_order_index.get(image_name, sys.maxsize),
        )

    def write_match_pair(
        self,
        handle: TextIO,
        seen_pairs: Set[tuple[str, str]],
        first_name: str,
        second_name: str,
    ) -> bool:
        if first_name == second_name:
            return False
        pair_key = tuple(sorted((first_name, second_name)))
        if pair_key in seen_pairs:
            return False
        seen_pairs.add(pair_key)
        handle.write(f"{pair_key[0]} {pair_key[1]}\n")
        return True

    def bridge_pair_candidates_for_source(
        self,
        source_name: str,
        target_names: Sequence[str],
        *,
        limit: int,
    ) -> List[tuple[float, str]]:
        if source_name not in self.exif_records:
            return []
        ranked_candidates = sorted(
            (
                (
                    self.candidate_edge_for_names(source_name, target_name).score,
                    target_name,
                )
                for target_name in target_names
                if target_name != source_name and target_name in self.exif_records
            ),
            key=lambda item: (-item[0], item[1]),
        )
        if not ranked_candidates:
            return []
        threshold = self.chunk_bridge_pair_score_threshold
        selected = [candidate for candidate in ranked_candidates[:limit] if candidate[0] >= threshold]
        if selected:
            return selected
        return ranked_candidates[: min(limit, 1)]

    def write_bridge_target_pairs(
        self,
        handle: TextIO,
        *,
        seen_pairs: Set[tuple[str, str]],
        chunk_name_set: Set[str],
        bridge_target_name_sets: Sequence[Set[str]],
    ) -> int:
        filtered_target_sets = [
            self.sorted_capture_names(set(target_names).intersection(chunk_name_set))
            for target_names in bridge_target_name_sets
        ]
        filtered_target_sets = [target_names for target_names in filtered_target_sets if target_names]
        if len(filtered_target_sets) < 2:
            return 0

        roles = self.classify_graph_roles()
        representative_sets = [
            self.representative_chunk_names(
                target_names,
                roles,
                limit=max(self.chunk_bridge_representative_images, 1),
            )
            for target_names in filtered_target_sets
        ]
        representative_sets = [target_names for target_names in representative_sets if target_names]
        if len(representative_sets) < 2:
            return 0

        added_pairs = 0
        pair_limit = max(self.chunk_bridge_cross_pairs_per_image, 1)
        for first_index, source_names in enumerate(representative_sets):
            for target_names in representative_sets[first_index + 1 :]:
                for source_name in source_names:
                    for _, target_name in self.bridge_pair_candidates_for_source(
                        source_name,
                        target_names,
                        limit=pair_limit,
                    ):
                        if self.write_match_pair(handle, seen_pairs, source_name, target_name):
                            added_pairs += 1
                for source_name in target_names:
                    for _, target_name in self.bridge_pair_candidates_for_source(
                        source_name,
                        source_names,
                        limit=pair_limit,
                    ):
                        if self.write_match_pair(handle, seen_pairs, source_name, target_name):
                            added_pairs += 1

        connector_names = self.sorted_capture_names(
            chunk_name_set.difference(set().union(*(set(target_names) for target_names in filtered_target_sets)))
        )
        if not connector_names:
            return added_pairs
        connector_representatives = self.representative_chunk_names(
            connector_names,
            roles,
            limit=max(self.chunk_bridge_connector_images, 1),
        )
        connector_pair_limit = max(self.chunk_bridge_connector_pairs_per_side, 1)
        for connector_name in connector_representatives:
            for target_names in representative_sets:
                for _, target_name in self.bridge_pair_candidates_for_source(
                    connector_name,
                    target_names,
                    limit=connector_pair_limit,
                ):
                    if self.write_match_pair(handle, seen_pairs, connector_name, target_name):
                        added_pairs += 1
        return added_pairs

    def write_chunk_match_list(
        self,
        chunk_plan: ChunkPlan,
        *,
        chunk_dir: Path,
        bridge_target_name_sets: Sequence[Set[str]] | None = None,
    ) -> Path:
        pair_list_path = chunk_dir / "match_list.txt"
        image_name_set = set(chunk_plan.image_names)
        seen_pairs: Set[tuple[str, str]] = set()
        with open(pair_list_path, "w", encoding="utf-8") as handle:
            for image_name in chunk_plan.image_names:
                for edge in self.graph_neighbors.get(image_name, []):
                    neighbor_name = edge.second_name if edge.first_name == image_name else edge.first_name
                    if neighbor_name not in image_name_set:
                        continue
                    pair_key = tuple(sorted((image_name, neighbor_name)))
                    self.write_match_pair(handle, seen_pairs, pair_key[0], pair_key[1])
            bridge_pairs_added = 0
            if bridge_target_name_sets:
                bridge_pairs_added = self.write_bridge_target_pairs(
                    handle,
                    seen_pairs=seen_pairs,
                    chunk_name_set=image_name_set,
                    bridge_target_name_sets=bridge_target_name_sets,
                )
        if bridge_pairs_added > 0:
            logger.info(
                "Added %s bridge-target pairs to chunk %s match list",
                bridge_pairs_added,
                chunk_plan.index,
            )
        return pair_list_path

    def run_matches_importer(
        self,
        *,
        database_path: Path | None = None,
        match_list_path: Path,
        stage: str = "matches_importer",
        label: str = "matches_importer",
    ) -> None:
        active_database_path = database_path or self.database_path
        started = time.time()
        pairs_before = self.count_verified_pairs(active_database_path)
        matching_family = self.run_with_option_family_fallback(
            stage=stage,
            families=MATCHING_OPTION_FAMILIES,
            preferred_family=self.matching_option_family,
            build_command=lambda family: (
                [
                    "colmap",
                    "matches_importer",
                    "--database_path",
                    str(active_database_path),
                    "--match_list_path",
                    str(match_list_path),
                    "--match_type",
                    "pairs",
                    f"--{family}.use_gpu",
                    "1" if self.use_gpu else "0",
                    f"--{family}.guided_matching",
                    "1",
                ],
                [f"--{family}.use_gpu", f"--{family}.guided_matching"],
            ),
            timeout_seconds=self.matcher_timeout_seconds,
        )
        self.matching_option_family = matching_family
        pairs_after = self.count_verified_pairs(active_database_path)
        self.timings[f"{stage}_seconds"] = round(time.time() - started, 2)
        self.record_matcher_delta(label, pairs_after - pairs_before)
        self.verified_pairs_total = max(self.verified_pairs_total, pairs_after)
        logger.info("%s added %s verified image pairs", stage, pairs_after - pairs_before)

    def run_chunk_matchers(
        self,
        chunk_plan: ChunkPlan,
        *,
        chunk_database_path: Path,
        chunk_dir: Path,
        stage_prefix: str,
        bridge_target_name_sets: Sequence[Set[str]] | None = None,
    ) -> None:
        if self.chunk_planner == "footprint_graph_v1":
            if self.colmap_capabilities.get("supports_matches_importer"):
                pair_list_path = self.write_chunk_match_list(
                    chunk_plan,
                    chunk_dir=chunk_dir,
                    bridge_target_name_sets=bridge_target_name_sets if is_bridge_stage_prefix(stage_prefix) else None,
                )
                self.run_matches_importer(
                    database_path=chunk_database_path,
                    match_list_path=pair_list_path,
                    stage=f"{stage_prefix}_matches_importer",
                    label="chunk_bridge_matches_importer"
                    if is_bridge_stage_prefix(stage_prefix)
                    else "chunk_matches_importer",
                )
                return
            self.run_exhaustive_matcher(
                database_path=chunk_database_path,
                stage=f"{stage_prefix}_exhaustive_matcher",
                label="chunk_bridge_exhaustive_matcher"
                if is_bridge_stage_prefix(stage_prefix)
                else "chunk_exhaustive_matcher",
            )
            return
        self.run_spatial_matcher(
            database_path=chunk_database_path,
            stage=f"{stage_prefix}_spatial_matcher",
            label="chunk_spatial_matcher",
        )
        if self.enable_sequential_matcher:
            self.run_sequential_matcher(
                database_path=chunk_database_path,
                stage=f"{stage_prefix}_sequential_matcher",
                label="chunk_sequential_matcher",
            )

    def run_chunk_recovery_matchers(
        self,
        *,
        chunk_database_path: Path,
        chunk_dir: Path,
        chunk_plan: ChunkPlan,
        stage_prefix: str,
    ) -> None:
        if self.chunk_planner == "footprint_graph_v1":
            self.run_chunk_matchers(
                chunk_plan,
                chunk_database_path=chunk_database_path,
                chunk_dir=chunk_dir,
                stage_prefix=f"{stage_prefix}_recovery",
            )
            return
        self.run_spatial_matcher(
            database_path=chunk_database_path,
            stage=f"{stage_prefix}_spatial_matcher_recovery",
            label="chunk_spatial_matcher",
            max_neighbors=self.chunk_boundary_max_neighbors,
            max_distance_m=max(self.spatial_distance_m * 1.5, self.chunk_max_radius_m),
        )
        if self.enable_sequential_matcher:
            self.run_sequential_matcher(
                database_path=chunk_database_path,
                stage=f"{stage_prefix}_sequential_matcher_recovery",
                label="chunk_sequential_matcher",
                overlap=max(self.sequential_overlap, 12),
            )

    def run_vocab_matching(
        self,
        *,
        database_path: Path | None = None,
        stage: str = "vocab_tree_matcher",
        label: str = "vocab_tree_matcher",
        num_images: int | None = None,
    ) -> None:
        active_database_path = database_path or self.database_path
        started = time.time()
        pairs_before = self.count_verified_pairs(active_database_path)
        try:
            if self.active_vocab_tree_path is None and not self.vocab_tree_path.exists():
                self.build_vocab_tree(database_path=active_database_path)
            self.run_vocab_tree_matcher(
                database_path=active_database_path,
                stage=stage,
                num_images=num_images,
            )
        except RuntimeError as exc:
            error_message = str(exc)
            if self.active_vocab_tree_path is None:
                logger.warning(
                    "COLMAP runtime vocab tree path failed; rebuilding a reduced FAISS tree locally"
                )
            elif "Failed to read faiss index" in error_message:
                logger.warning(
                    "Downloaded vocab tree is a legacy FLANN index; rebuilding a FAISS tree locally"
                )
            else:
                raise
            self.build_vocab_tree(database_path=active_database_path)
            self.run_vocab_tree_matcher(
                database_path=active_database_path,
                stage=stage,
                num_images=num_images,
            )
        pairs_after = self.count_verified_pairs(active_database_path)
        self.timings[f"{stage}_seconds"] = round(time.time() - started, 2)
        self.record_matcher_delta(label, pairs_after - pairs_before)
        self.verified_pairs_total = max(self.verified_pairs_total, pairs_after)
        logger.info("%s added %s verified image pairs", stage, pairs_after - pairs_before)

    def summarize_model(self, *, stage: str, binary_dir: Path, image_count: int) -> ModelSummary:
        text_dir = self.work_dir / "text_models" / stage / binary_dir.name
        text_dir.mkdir(parents=True, exist_ok=True)
        model_converter_stage = f"{stage}_model_converter_{binary_dir.name}"
        try:
            stream_command(
                [
                    "colmap",
                    "model_converter",
                    "--input_path",
                    str(binary_dir),
                    "--output_path",
                    str(text_dir),
                    "--output_type",
                    "TXT",
                ],
                stage=model_converter_stage,
                timeout_seconds=self.resolve_timeout_seconds(self.matcher_timeout_seconds),
                heartbeat_seconds=self.command_heartbeat_seconds,
            )
        except RuntimeError as error:
            self.handle_stage_runtime_error(model_converter_stage, error)
            raise
        return ModelSummary(
            stage=stage,
            text_dir=text_dir,
            cameras_registered=count_text_rows(text_dir / "cameras.txt"),
            images_registered=count_registered_images(text_dir / "images.txt"),
            points_3d=count_text_rows(text_dir / "points3D.txt"),
            binary_dir=binary_dir,
            image_count=image_count,
        )

    def run_mapper(
        self,
        *,
        database_path: Path | None = None,
        stage: str,
        sparse_root: Path,
        image_count: int | None = None,
        bridge_target_name_sets: Sequence[Set[str]] | None = None,
        allow_partial_timeout_result: bool = False,
    ) -> ModelSummary:
        active_database_path = database_path or self.database_path
        active_image_count = image_count if image_count is not None else self.dataset_image_count
        started = time.time()
        sparse_root.mkdir(parents=True, exist_ok=True)
        mapper_error: RuntimeError | None = None
        timed_out_error = False
        try:
            stream_command(
                [
                    "colmap",
                    "mapper",
                    "--database_path",
                    str(active_database_path),
                    "--image_path",
                    str(self.images_dir),
                    "--output_path",
                    str(sparse_root),
                    "--Mapper.num_threads",
                    str(self.mapper_threads),
                    "--Mapper.ba_refine_principal_point",
                    "0",
                ],
                stage=stage,
                timeout_seconds=self.mapper_timeout_seconds_for_stage(stage),
                heartbeat_seconds=self.command_heartbeat_seconds,
            )
        except RuntimeError as error:
            mapper_error = error
            timed_out_error = "timed out" in str(error).lower()
            if not allow_partial_timeout_result or not timed_out_error:
                self.handle_stage_runtime_error(stage, error)
                raise
        self.timings[f"{stage}_seconds"] = round(time.time() - started, 2)

        candidate_dirs = [path for path in sorted(sparse_root.iterdir()) if path.is_dir()]
        if not candidate_dirs:
            if mapper_error is not None:
                self.handle_stage_runtime_error(stage, mapper_error)
                raise mapper_error
            raise RuntimeError(f"{stage} did not produce any sparse models")

        best_model: ModelSummary | None = None
        best_sort_key: tuple[int, ...] | None = None
        for candidate_dir in candidate_dirs:
            try:
                model = self.summarize_model(
                    stage=stage,
                    binary_dir=candidate_dir,
                    image_count=active_image_count,
                )
            except RuntimeError as exc:
                if mapper_error is None:
                    raise
                logger.warning(
                    "Skipping incomplete partial mapper output for %s at %s after timeout: %s",
                    stage,
                    candidate_dir,
                    exc,
                )
                continue
            logger.info(
                "%s model %s registered %s/%s images and %s points",
                stage,
                candidate_dir.name,
                model.images_registered,
                active_image_count,
                model.points_3d,
            )
            if bridge_target_name_sets:
                registered_names = load_registered_image_names(model.text_dir / "images.txt")
                touched_targets, total_overlap = bridge_overlap_counts(
                    registered_names,
                    bridge_target_name_sets,
                )
                logger.info(
                    "%s model %s overlaps %s/%s bridge targets with %s shared registered images",
                    stage,
                    candidate_dir.name,
                    touched_targets,
                    len(bridge_target_name_sets),
                    total_overlap,
                )
                current_sort_key = bridge_model_sort_key(
                    model,
                    registered_names,
                    bridge_target_name_sets,
                )
            else:
                current_sort_key = model_sort_key(model)
            if best_model is None or best_sort_key is None or current_sort_key > best_sort_key:
                best_model = model
                best_sort_key = current_sort_key
        if best_model is None:
            if mapper_error is not None:
                self.handle_stage_runtime_error(stage, mapper_error)
                raise mapper_error
            raise RuntimeError(f"Unable to choose a sparse model for {stage}")
        if mapper_error is not None:
            if best_model.images_registered <= 0:
                self.handle_stage_runtime_error(stage, mapper_error)
                raise mapper_error
            best_model.partial_result = True
            best_model.timed_out = timed_out_error
            logger.warning(
                "%s timed out after %.2fs but produced a partial sparse model with %s/%s registered images; continuing with the best available partial result",
                stage,
                self.timings.get(f"{stage}_seconds", 0.0),
                best_model.images_registered,
                active_image_count,
            )
            self.clear_failure()
        self.model_summaries.append(
            {
                "stage": best_model.stage,
                "cameras_registered": best_model.cameras_registered,
                "images_registered": best_model.images_registered,
                "points_3d": best_model.points_3d,
            }
        )
        return best_model

    def run_bundle_adjuster(self, *, input_path: Path, stage: str) -> ModelSummary:
        started = time.time()
        output_path = self.work_dir / stage
        output_path.mkdir(parents=True, exist_ok=True)
        command = [
            "colmap",
            "bundle_adjuster",
            "--input_path",
            str(input_path),
            "--output_path",
            str(output_path),
            "--BundleAdjustment.refine_principal_point",
            "0",
            "--BundleAdjustment.use_gpu",
            "1" if self.use_gpu else "0",
        ]
        try:
            stream_command(
                command,
                stage=stage,
                timeout_seconds=self.resolve_timeout_seconds(self.bundle_adjuster_timeout_seconds),
                heartbeat_seconds=self.command_heartbeat_seconds,
            )
        except RuntimeError as exc:
            error_text = str(exc)
            if "unrecognised option '--BundleAdjustment.use_gpu'" not in error_text:
                self.handle_stage_runtime_error(stage, exc)
                raise
            logger.warning(
                "bundle_adjuster rejected BundleAdjustment.use_gpu; retrying with older COLMAP-compatible flags"
            )
            fallback_command = [
                "colmap",
                "bundle_adjuster",
                "--input_path",
                str(input_path),
                "--output_path",
                str(output_path),
                "--BundleAdjustment.refine_principal_point",
                "0",
            ]
            stream_command(
                fallback_command,
                stage=stage,
                timeout_seconds=self.resolve_timeout_seconds(self.bundle_adjuster_timeout_seconds),
                heartbeat_seconds=self.command_heartbeat_seconds,
            )
        self.timings[f"{stage}_seconds"] = round(time.time() - started, 2)
        return self.summarize_model(
            stage=stage,
            binary_dir=output_path,
            image_count=self.dataset_image_count,
        )

    def centroid_for_names(self, image_names: Sequence[str]) -> tuple[float, float]:
        if not image_names:
            return (0.0, 0.0)
        sum_x = 0.0
        sum_y = 0.0
        for image_name in image_names:
            record = self.exif_records[image_name]
            sum_x += float(record["local_x_m"])
            sum_y += float(record["local_y_m"])
        return (sum_x / len(image_names), sum_y / len(image_names))

    def centroid_xyz_for_names(self, image_names: Sequence[str]) -> tuple[float, float, float]:
        if not image_names:
            return (0.0, 0.0, 0.0)
        sum_x = 0.0
        sum_y = 0.0
        sum_z = 0.0
        for image_name in image_names:
            record = self.exif_records[image_name]
            sum_x += float(record["local_x_m"])
            sum_y += float(record["local_y_m"])
            sum_z += float(record.get("local_z_m", 0.0))
        image_count = len(image_names)
        return (sum_x / image_count, sum_y / image_count, sum_z / image_count)

    def mean_heading_for_names(self, image_names: Sequence[str]) -> float | None:
        x_sum = 0.0
        y_sum = 0.0
        sample_count = 0
        for image_name in image_names:
            heading_deg = self.exif_records[image_name].get("heading_deg")
            if heading_deg is None:
                continue
            radians = math.radians(float(heading_deg))
            x_sum += math.cos(radians)
            y_sum += math.sin(radians)
            sample_count += 1
        if sample_count == 0:
            return None
        return normalize_heading(math.degrees(math.atan2(y_sum, x_sum)))

    def mean_pitch_for_names(self, image_names: Sequence[str]) -> float | None:
        pitches = [
            float(record["pitch_deg"])
            for image_name in image_names
            if (record := self.exif_records[image_name]).get("pitch_deg") is not None
        ]
        if not pitches:
            return None
        return normalize_pitch(sum(pitches) / len(pitches))

    def should_group_adjacent_images(self, previous_name: str, current_name: str) -> bool:
        previous_record = self.exif_records[previous_name]
        current_record = self.exif_records[current_name]
        previous_time = previous_record.get("capture_time_s")
        current_time = current_record.get("capture_time_s")
        time_gap_s = (
            abs(float(current_time) - float(previous_time))
            if previous_time is not None and current_time is not None
            else 0.0
        )
        distance_m = math.hypot(
            float(current_record["local_x_m"]) - float(previous_record["local_x_m"]),
            float(current_record["local_y_m"]) - float(previous_record["local_y_m"]),
        )
        altitude_delta_m = abs(
            float(current_record.get("local_z_m", 0.0)) - float(previous_record.get("local_z_m", 0.0))
        )
        heading_delta_deg = angular_distance_degrees(
            previous_record.get("heading_deg"),
            current_record.get("heading_deg"),
        )
        previous_pitch = previous_record.get("pitch_deg")
        current_pitch = current_record.get("pitch_deg")
        pitch_delta_deg = (
            abs(float(current_pitch) - float(previous_pitch))
            if previous_pitch is not None and current_pitch is not None
            else 0.0
        )
        return (
            time_gap_s <= self.capture_group_max_time_gap_s
            and distance_m <= self.capture_group_max_distance_m
            and altitude_delta_m <= self.capture_group_max_altitude_delta_m
            and heading_delta_deg <= self.capture_group_max_heading_delta_deg
            and pitch_delta_deg <= self.capture_group_max_pitch_delta_deg
        )

    def build_capture_group(self, group_index: int, image_names: Sequence[str]) -> CaptureGroup:
        centroid_x, centroid_y, centroid_z = self.centroid_xyz_for_names(image_names)
        capture_times = [
            float(record["capture_time_s"])
            for image_name in image_names
            if (record := self.exif_records[image_name]).get("capture_time_s") is not None
        ]
        return CaptureGroup(
            index=group_index,
            image_names=list(image_names),
            centroid_x_m=centroid_x,
            centroid_y_m=centroid_y,
            centroid_z_m=centroid_z,
            heading_deg=self.mean_heading_for_names(image_names),
            pitch_deg=self.mean_pitch_for_names(image_names),
            start_capture_time_s=min(capture_times) if capture_times else None,
            end_capture_time_s=max(capture_times) if capture_times else None,
        )

    def build_capture_groups(self) -> List[CaptureGroup]:
        ordered_names = [
            image_name for image_name in self.capture_ordered_names if image_name in self.exif_records
        ]
        if not ordered_names:
            return []
        groups: List[CaptureGroup] = []
        current_group_names = [ordered_names[0]]
        for image_name in ordered_names[1:]:
            if self.should_group_adjacent_images(current_group_names[-1], image_name):
                current_group_names.append(image_name)
                continue
            groups.append(self.build_capture_group(len(groups), current_group_names))
            current_group_names = [image_name]
        groups.append(self.build_capture_group(len(groups), current_group_names))
        self.image_group_indices = {
            image_name: group.index
            for group in groups
            for image_name in group.image_names
        }
        self.chunk_groups = groups
        self.chunk_group_count = len(groups)
        return groups

    def dominant_spatial_axis_for_groups(self, groups: Sequence[CaptureGroup]) -> tuple[float, float]:
        if len(groups) <= 1:
            return (1.0, 0.0)
        centroid_x = sum(group.centroid_x_m for group in groups) / len(groups)
        centroid_y = sum(group.centroid_y_m for group in groups) / len(groups)
        xx = 0.0
        xy = 0.0
        yy = 0.0
        for group in groups:
            delta_x = group.centroid_x_m - centroid_x
            delta_y = group.centroid_y_m - centroid_y
            xx += delta_x * delta_x
            xy += delta_x * delta_y
            yy += delta_y * delta_y
        if abs(xy) < 1e-9 and abs(xx - yy) < 1e-9:
            return (1.0, 0.0)
        trace = xx + yy
        determinant = xx * yy - xy * xy
        eigenvalue = trace / 2.0 + math.sqrt(max((trace * trace) / 4.0 - determinant, 0.0))
        axis_x = xy
        axis_y = eigenvalue - xx
        if abs(axis_x) < 1e-9 and abs(axis_y) < 1e-9:
            return (1.0, 0.0) if xx >= yy else (0.0, 1.0)
        length = math.hypot(axis_x, axis_y)
        return (axis_x / length, axis_y / length)

    def group_projection(
        self,
        group: CaptureGroup,
        axis_x: float,
        axis_y: float,
    ) -> tuple[float, float, float, float]:
        along_axis = group.centroid_x_m * axis_x + group.centroid_y_m * axis_y
        across_axis = (-axis_y * group.centroid_x_m) + (axis_x * group.centroid_y_m)
        heading_value = group.heading_deg if group.heading_deg is not None else -1.0
        pitch_value = group.pitch_deg if group.pitch_deg is not None else 0.0
        return (along_axis, across_axis, heading_value, pitch_value)

    def ordered_groups_for_chunking(self, groups: Sequence[CaptureGroup]) -> List[CaptureGroup]:
        axis_x, axis_y = self.dominant_spatial_axis_for_groups(groups)
        return sorted(groups, key=lambda group: self.group_projection(group, axis_x, axis_y))

    def view_mismatch_between_groups(self, first_group: CaptureGroup, second_group: CaptureGroup) -> float:
        return angular_distance_between_vectors(
            view_vector(first_group.heading_deg, first_group.pitch_deg),
            view_vector(second_group.heading_deg, second_group.pitch_deg),
        )

    def build_flight_segments(self, ordered_groups: Sequence[CaptureGroup]) -> List[FlightSegment]:
        if not ordered_groups:
            return []
        segments: List[FlightSegment] = []
        current_group_indices = [ordered_groups[0].index]
        recent_step_distances: List[float] = []
        for previous_group, current_group in zip(ordered_groups, ordered_groups[1:]):
            step_distance_m = math.hypot(
                current_group.centroid_x_m - previous_group.centroid_x_m,
                current_group.centroid_y_m - previous_group.centroid_y_m,
            )
            altitude_delta_m = abs(current_group.centroid_z_m - previous_group.centroid_z_m)
            heading_delta_deg = angular_distance_degrees(previous_group.heading_deg, current_group.heading_deg)
            pitch_delta_deg = (
                abs(float(current_group.pitch_deg) - float(previous_group.pitch_deg))
                if current_group.pitch_deg is not None and previous_group.pitch_deg is not None
                else 0.0
            )
            rolling_step_distance_m = (
                statistics.median(recent_step_distances[-5:])
                if recent_step_distances
                else max(step_distance_m, 1.0)
            )
            should_break = (
                heading_delta_deg > self.segment_break_heading_delta_deg
                or pitch_delta_deg > self.segment_break_pitch_delta_deg
                or altitude_delta_m > self.segment_break_altitude_delta_m
                or (
                    recent_step_distances
                    and step_distance_m > rolling_step_distance_m * self.segment_break_step_multiplier
                )
            )
            if should_break:
                segments.append(FlightSegment(index=len(segments), group_indices=current_group_indices))
                current_group_indices = [current_group.index]
                recent_step_distances = [max(step_distance_m, 1e-6)]
                continue
            current_group_indices.append(current_group.index)
            recent_step_distances.append(max(step_distance_m, 1e-6))
        segments.append(FlightSegment(index=len(segments), group_indices=current_group_indices))
        self.flight_segments = segments
        self.chunk_segment_count = len(segments)
        return segments

    def group_indices_image_count(self, group_indices: Sequence[int]) -> int:
        return sum(self.chunk_groups[group_index].image_count for group_index in group_indices)

    def group_indices_radius_m(self, group_indices: Sequence[int]) -> float:
        if len(group_indices) <= 1:
            return 0.0
        centroid_x = sum(self.chunk_groups[group_index].centroid_x_m for group_index in group_indices) / len(group_indices)
        centroid_y = sum(self.chunk_groups[group_index].centroid_y_m for group_index in group_indices) / len(group_indices)
        return max(
            math.hypot(
                self.chunk_groups[group_index].centroid_x_m - centroid_x,
                self.chunk_groups[group_index].centroid_y_m - centroid_y,
            )
            for group_index in group_indices
        )

    def slice_segment_into_chunk_units(self, segment: FlightSegment) -> List[dict[str, List[int]]]:
        chunk_units: List[dict[str, List[int]]] = []
        current_group_indices: List[int] = []
        for group_index in segment.group_indices:
            candidate_group_indices = [*current_group_indices, group_index]
            candidate_image_count = self.group_indices_image_count(candidate_group_indices)
            candidate_radius_m = self.group_indices_radius_m(candidate_group_indices)
            if current_group_indices and (
                (
                    candidate_image_count > self.chunk_target_images
                    and self.group_indices_image_count(current_group_indices) >= self.chunk_min_images
                )
                or (
                    candidate_radius_m > self.chunk_max_radius_m
                    and self.group_indices_image_count(current_group_indices) >= self.chunk_min_images
                )
            ):
                chunk_units.append(
                    {
                        "core_group_indices": list(current_group_indices),
                        "segment_indices": [segment.index],
                    }
                )
                current_group_indices = [group_index]
                continue
            current_group_indices = candidate_group_indices
        if current_group_indices:
            if chunk_units and self.group_indices_image_count(current_group_indices) < self.chunk_min_images:
                chunk_units[-1]["core_group_indices"].extend(current_group_indices)
            else:
                chunk_units.append(
                    {
                        "core_group_indices": list(current_group_indices),
                        "segment_indices": [segment.index],
                    }
                )
        return chunk_units

    def chunk_unit_boundary_score(
        self,
        first_group_indices: Sequence[int],
        second_group_indices: Sequence[int],
    ) -> float:
        first_group = self.chunk_groups[first_group_indices[-1]]
        second_group = self.chunk_groups[second_group_indices[0]]
        distance_m = math.hypot(
            second_group.centroid_x_m - first_group.centroid_x_m,
            second_group.centroid_y_m - first_group.centroid_y_m,
        )
        altitude_delta_m = abs(second_group.centroid_z_m - first_group.centroid_z_m)
        view_delta_deg = self.view_mismatch_between_groups(first_group, second_group)
        return distance_m + altitude_delta_m * 0.5 + view_delta_deg * self.chunk_heading_weight

    def merge_small_chunk_units(self, chunk_units: List[dict[str, List[int]]]) -> List[dict[str, List[int]]]:
        while len(chunk_units) > 1:
            merge_index = next(
                (
                    index
                    for index, chunk_unit in enumerate(chunk_units)
                    if self.group_indices_image_count(chunk_unit["core_group_indices"]) < self.chunk_min_images
                ),
                None,
            )
            if merge_index is None:
                break
            candidate_neighbors: List[tuple[float, int]] = []
            if merge_index > 0:
                candidate_neighbors.append(
                    (
                        self.chunk_unit_boundary_score(
                            chunk_units[merge_index - 1]["core_group_indices"],
                            chunk_units[merge_index]["core_group_indices"],
                        ),
                        merge_index - 1,
                    )
                )
            if merge_index + 1 < len(chunk_units):
                candidate_neighbors.append(
                    (
                        self.chunk_unit_boundary_score(
                            chunk_units[merge_index]["core_group_indices"],
                            chunk_units[merge_index + 1]["core_group_indices"],
                        ),
                        merge_index + 1,
                    )
                )
            _, neighbor_index = min(candidate_neighbors, key=lambda item: item[0])
            first_index, second_index = sorted((merge_index, neighbor_index))
            chunk_units[first_index] = {
                "core_group_indices": [
                    *chunk_units[first_index]["core_group_indices"],
                    *chunk_units[second_index]["core_group_indices"],
                ],
                "segment_indices": sorted(
                    set(chunk_units[first_index]["segment_indices"]).union(chunk_units[second_index]["segment_indices"])
                ),
            }
            chunk_units.pop(second_index)
        return chunk_units

    def group_boundary_score(self, first_group: CaptureGroup, second_group: CaptureGroup) -> float:
        distance_m = math.hypot(
            second_group.centroid_x_m - first_group.centroid_x_m,
            second_group.centroid_y_m - first_group.centroid_y_m,
        )
        altitude_delta_m = abs(second_group.centroid_z_m - first_group.centroid_z_m)
        view_delta_deg = self.view_mismatch_between_groups(first_group, second_group)
        return distance_m + altitude_delta_m * 0.5 + view_delta_deg * self.chunk_heading_weight

    def build_chunk_plan_from_groups(
        self,
        *,
        index: int,
        core_group_indices: Sequence[int],
        overlap_group_indices: Sequence[int],
        segment_indices: Sequence[int],
    ) -> ChunkPlan:
        capture_order_index = {
            image_name: position for position, image_name in enumerate(self.capture_ordered_names)
        }
        core_names = [
            image_name
            for group_index in core_group_indices
            for image_name in self.chunk_groups[group_index].image_names
        ]
        overlap_names = [
            image_name
            for group_index in overlap_group_indices
            for image_name in self.chunk_groups[group_index].image_names
        ]
        image_names = sorted(
            set(core_names).union(overlap_names),
            key=lambda image_name: capture_order_index.get(image_name, sys.maxsize),
        )
        return ChunkPlan(
            index=index,
            core_names=sorted(
                core_names,
                key=lambda image_name: capture_order_index.get(image_name, sys.maxsize),
            ),
            image_names=image_names,
            overlap_names=sorted(
                set(overlap_names),
                key=lambda image_name: capture_order_index.get(image_name, sys.maxsize),
            ),
            core_group_indices=list(core_group_indices),
            group_indices=sorted(set(core_group_indices).union(overlap_group_indices)),
            overlap_group_indices=sorted(set(overlap_group_indices)),
            segment_indices=sorted(set(segment_indices)),
        )

    def build_spatial_heading_chunks(self) -> List[ChunkPlan]:
        capture_groups = self.build_capture_groups()
        if not capture_groups:
            return []
        ordered_groups = self.ordered_groups_for_chunking(capture_groups)
        segments = self.build_flight_segments(ordered_groups)
        chunk_units: List[dict[str, List[int]]] = []
        for segment in segments:
            chunk_units.extend(self.slice_segment_into_chunk_units(segment))
        chunk_units = self.merge_small_chunk_units(chunk_units)
        if len(chunk_units) <= 1:
            self.chunk_overlap_image_count = 0
            self.chunk_sizes = [
                self.group_indices_image_count(chunk_units[0]["core_group_indices"])
            ] if chunk_units else []
            return [
                self.build_chunk_plan_from_groups(
                    index=0,
                    core_group_indices=chunk_units[0]["core_group_indices"],
                    overlap_group_indices=[],
                    segment_indices=chunk_units[0]["segment_indices"],
                )
            ] if chunk_units else []

        overlap_group_indices_per_chunk: List[Set[int]] = [set() for _ in chunk_units]
        total_overlap_assignments = 0
        for index in range(len(chunk_units) - 1):
            left_core_group_indices = chunk_units[index]["core_group_indices"]
            right_core_group_indices = chunk_units[index + 1]["core_group_indices"]
            left_boundary_candidates = left_core_group_indices[-min(4, len(left_core_group_indices)):]
            right_boundary_candidates = right_core_group_indices[: min(4, len(right_core_group_indices))]
            left_boundary_group = self.chunk_groups[left_core_group_indices[-1]]
            right_boundary_group = self.chunk_groups[right_core_group_indices[0]]
            left_sorted_candidates = sorted(
                left_boundary_candidates,
                key=lambda group_index: self.group_boundary_score(
                    self.chunk_groups[group_index],
                    right_boundary_group,
                ),
            )
            right_sorted_candidates = sorted(
                right_boundary_candidates,
                key=lambda group_index: self.group_boundary_score(
                    left_boundary_group,
                    self.chunk_groups[group_index],
                ),
            )
            shared_group_indices: List[int] = []
            shared_group_indices.extend(left_sorted_candidates[: min(2, len(left_sorted_candidates))])
            shared_group_indices.extend(right_sorted_candidates[: min(2, len(right_sorted_candidates))])
            left_cursor = min(2, len(left_sorted_candidates))
            right_cursor = min(2, len(right_sorted_candidates))
            while (
                self.group_indices_image_count(shared_group_indices) < self.chunk_overlap_images
                and (left_cursor < len(left_sorted_candidates) or right_cursor < len(right_sorted_candidates))
            ):
                candidate_scores: List[tuple[float, int, str]] = []
                if left_cursor < len(left_sorted_candidates):
                    left_group_index = left_sorted_candidates[left_cursor]
                    candidate_scores.append(
                        (
                            self.group_boundary_score(self.chunk_groups[left_group_index], right_boundary_group),
                            left_group_index,
                            "left",
                        )
                    )
                if right_cursor < len(right_sorted_candidates):
                    right_group_index = right_sorted_candidates[right_cursor]
                    candidate_scores.append(
                        (
                            self.group_boundary_score(left_boundary_group, self.chunk_groups[right_group_index]),
                            right_group_index,
                            "right",
                        )
                    )
                _, group_index, side = min(candidate_scores, key=lambda item: item[0])
                shared_group_indices.append(group_index)
                if side == "left":
                    left_cursor += 1
                else:
                    right_cursor += 1
            shared_group_indices = sorted(set(shared_group_indices))
            overlap_group_indices_per_chunk[index].update(shared_group_indices)
            overlap_group_indices_per_chunk[index + 1].update(shared_group_indices)
            total_overlap_assignments += self.group_indices_image_count(shared_group_indices)

        chunk_plans = [
            self.build_chunk_plan_from_groups(
                index=index,
                core_group_indices=chunk_unit["core_group_indices"],
                overlap_group_indices=sorted(overlap_group_indices_per_chunk[index]),
                segment_indices=chunk_unit["segment_indices"],
            )
            for index, chunk_unit in enumerate(chunk_units)
        ]
        self.chunk_overlap_image_count = total_overlap_assignments
        self.chunk_sizes = [len(chunk_plan.image_names) for chunk_plan in chunk_plans]
        return chunk_plans

    def build_single_image_groups(self) -> List[CaptureGroup]:
        groups: List[CaptureGroup] = []
        self.image_group_indices = {}
        for index, image_name in enumerate(self.capture_ordered_names):
            if image_name not in self.exif_records:
                continue
            record = self.exif_records[image_name]
            group = CaptureGroup(
                index=len(groups),
                image_names=[image_name],
                centroid_x_m=float(record["local_x_m"]),
                centroid_y_m=float(record["local_y_m"]),
                centroid_z_m=float(record.get("local_z_m", 0.0)),
                heading_deg=float(record["heading_deg"]) if record.get("heading_deg") is not None else None,
                pitch_deg=float(record["pitch_deg"]) if record.get("pitch_deg") is not None else None,
                start_capture_time_s=(
                    float(record["capture_time_s"])
                    if record.get("capture_time_s") is not None
                    else None
                ),
                end_capture_time_s=(
                    float(record["capture_time_s"])
                    if record.get("capture_time_s") is not None
                    else None
                ),
            )
            groups.append(group)
            self.image_group_indices[image_name] = group.index
        self.chunk_groups = groups
        self.chunk_group_count = len(groups)
        self.flight_segments = []
        self.chunk_segment_count = 0
        return groups

    def chunk_plan_centroid_xy(self, chunk_plan: ChunkPlan) -> tuple[float, float]:
        if not chunk_plan.image_names:
            return (0.0, 0.0)
        centroid_x = sum(self.exif_records[name]["local_x_m"] for name in chunk_plan.image_names) / len(chunk_plan.image_names)
        centroid_y = sum(self.exif_records[name]["local_y_m"] for name in chunk_plan.image_names) / len(chunk_plan.image_names)
        return (float(centroid_x), float(centroid_y))

    def cross_chunk_edge_count(self, first_names: Sequence[str], second_names: Sequence[str]) -> int:
        second_set = set(second_names)
        count = 0
        for image_name in first_names:
            for edge in self.graph_neighbors.get(image_name, []):
                neighbor_name = edge.second_name if edge.first_name == image_name else edge.first_name
                if edge.score >= 0.45 and neighbor_name in second_set:
                    count += 1
        return count

    def build_footprint_graph_chunks(self) -> List[ChunkPlan]:
        self.build_single_image_groups()
        self.build_view_geometries()
        self.build_candidate_graph()
        roles = self.classify_graph_roles()
        image_membership_count: Dict[str, int] = defaultdict(int)
        assigned_core_names: Set[str] = set()
        core_chunks: List[List[str]] = []
        anchor_candidates = sorted(
            self.capture_ordered_names,
            key=lambda name: (
                0 if roles.get(name) == "geometry_anchor" else 1,
                -sum(edge.score for edge in self.graph_neighbors.get(name, [])[:12]),
                name,
            ),
        )
        for seed_name in anchor_candidates:
            if seed_name not in self.exif_records or seed_name in assigned_core_names:
                continue
            if roles.get(seed_name) == "burst_redundant":
                continue
            chunk_names: List[str] = [seed_name]
            chunk_name_set = {seed_name}
            frontier = [seed_name]
            while frontier:
                current_name = frontier.pop(0)
                for edge in self.graph_neighbors.get(current_name, []):
                    neighbor_name = edge.second_name if edge.first_name == current_name else edge.first_name
                    if neighbor_name in chunk_name_set or neighbor_name in assigned_core_names:
                        continue
                    if roles.get(neighbor_name) == "burst_redundant" and len(chunk_names) >= self.chunk_min_images:
                        continue
                    predicted_pair_count = (
                        len(chunk_names) * (len(chunk_names) - 1) // 2
                        if self.colmap_capabilities.get("supports_matches_importer") is not True
                        else sum(
                            1
                            for name in chunk_name_set
                            for candidate_edge in self.graph_neighbors.get(name, [])
                            if (
                                (candidate_edge.second_name if candidate_edge.first_name == name else candidate_edge.first_name)
                                in chunk_name_set
                            )
                        ) // 2
                    )
                    if (
                        len(chunk_names) >= self.chunk_hard_max_images
                        or predicted_pair_count >= self.chunk_pair_budget
                    ):
                        frontier = []
                        break
                    chunk_names.append(neighbor_name)
                    chunk_name_set.add(neighbor_name)
                    if len(chunk_names) < self.chunk_target_images:
                        frontier.append(neighbor_name)
            if len(chunk_names) < self.chunk_min_images:
                additional_names = [
                    name
                    for name in anchor_candidates
                    if name not in chunk_name_set and name not in assigned_core_names and roles.get(name) != "burst_redundant"
                ]
                for additional_name in additional_names:
                    if len(chunk_names) >= self.chunk_min_images:
                        break
                    chunk_names.append(additional_name)
                    chunk_name_set.add(additional_name)
            if len(chunk_names) < self.chunk_min_images:
                supplemental_scores: Dict[str, float] = {}
                for image_name in list(chunk_names):
                    for edge in self.graph_neighbors.get(image_name, []):
                        neighbor_name = edge.second_name if edge.first_name == image_name else edge.first_name
                        if neighbor_name in chunk_name_set or roles.get(neighbor_name) == "burst_redundant":
                            continue
                        supplemental_scores[neighbor_name] = supplemental_scores.get(neighbor_name, 0.0) + edge.score
                if len(chunk_names) < self.chunk_min_images:
                    centroid_x, centroid_y = self.centroid_for_names(chunk_names)
                    for candidate_name in self.capture_ordered_names:
                        if candidate_name not in self.exif_records or candidate_name in chunk_name_set:
                            continue
                        if roles.get(candidate_name) == "burst_redundant":
                            continue
                        candidate_record = self.exif_records[candidate_name]
                        distance_m = math.hypot(
                            float(candidate_record["local_x_m"]) - centroid_x,
                            float(candidate_record["local_y_m"]) - centroid_y,
                        )
                        view_delta_deg = angular_distance_between_vectors(
                            view_vector(
                                self.mean_heading_for_names(chunk_names),
                                self.mean_pitch_for_names(chunk_names),
                            ),
                            view_vector(
                                candidate_record.get("heading_deg"),
                                candidate_record.get("pitch_deg"),
                            ),
                        )
                        supplemental_scores.setdefault(
                            candidate_name,
                            1.0 / max(distance_m + view_delta_deg * self.chunk_heading_weight + 1.0, 1.0),
                        )
                for _, supplemental_name in sorted(
                    ((score, name) for name, score in supplemental_scores.items()),
                    key=lambda item: (-item[0], item[1]),
                ):
                    if len(chunk_names) >= min(self.chunk_min_images, self.chunk_hard_max_images):
                        break
                    if supplemental_name in chunk_name_set:
                        continue
                    chunk_names.append(supplemental_name)
                    chunk_name_set.add(supplemental_name)
            for image_name in chunk_names:
                assigned_core_names.add(image_name)
                image_membership_count[image_name] += 1
            core_chunks.append(sorted(chunk_names, key=lambda name: self.capture_ordered_names.index(name)))

        remaining_names = [
            name for name in self.capture_ordered_names
            if name in self.exif_records and name not in assigned_core_names
        ]
        if remaining_names:
            if core_chunks and len(remaining_names) < self.chunk_min_images:
                core_chunks[-1].extend(remaining_names)
            else:
                core_chunks.append(remaining_names)

        overlap_assignments: Dict[int, Set[str]] = defaultdict(set)
        self.chunk_cross_edge_counts = {}
        for left_index in range(len(core_chunks)):
            for right_index in range(left_index + 1, len(core_chunks)):
                cross_edge_count = self.cross_chunk_edge_count(core_chunks[left_index], core_chunks[right_index])
                if cross_edge_count < self.chunk_cross_edge_min_count:
                    continue
                self.chunk_cross_edge_counts[(left_index, right_index)] = cross_edge_count
                candidate_scores: List[tuple[float, str]] = []
                for image_name in core_chunks[left_index]:
                    if roles.get(image_name) == "burst_redundant":
                        continue
                    score = sum(
                        edge.score
                        for edge in self.graph_neighbors.get(image_name, [])
                        if (edge.second_name if edge.first_name == image_name else edge.first_name) in set(core_chunks[right_index])
                    )
                    if score > 0.0:
                        candidate_scores.append((score, image_name))
                for image_name in core_chunks[right_index]:
                    if roles.get(image_name) == "burst_redundant":
                        continue
                    score = sum(
                        edge.score
                        for edge in self.graph_neighbors.get(image_name, [])
                        if (edge.second_name if edge.first_name == image_name else edge.first_name) in set(core_chunks[left_index])
                    )
                    if score > 0.0:
                        candidate_scores.append((score, image_name))
                pair_anchor_target = self.chunk_overlap_anchor_count
                if self.chunk_planner == "footprint_graph_v1":
                    pair_anchor_target = max(
                        self.chunk_overlap_anchor_count,
                        min(max(min(len(core_chunks[left_index]), len(core_chunks[right_index])) // 3, 24), 60),
                    )
                for _, image_name in sorted(candidate_scores, key=lambda item: (-item[0], item[1])):
                    if len(overlap_assignments[left_index].union(overlap_assignments[right_index])) >= pair_anchor_target:
                        break
                    if image_membership_count[image_name] >= 3:
                        continue
                    overlap_assignments[left_index].add(image_name)
                    overlap_assignments[right_index].add(image_name)
                    image_membership_count[image_name] += 1
        if self.chunk_planner == "footprint_graph_v1":
            self.ensure_chunk_overlap_connectivity(
                core_chunks=core_chunks,
                overlap_assignments=overlap_assignments,
                image_membership_count=image_membership_count,
                roles=roles,
            )

        chunk_plans: List[ChunkPlan] = []
        self.chunk_centroids = {}
        total_overlap_assignments = 0
        for index, chunk_names in enumerate(core_chunks):
            core_names = [
                image_name
                for image_name in sorted(set(chunk_names), key=lambda name: self.capture_ordered_names.index(name))
            ]
            overlap_names = [
                image_name
                for image_name in sorted(
                    overlap_assignments.get(index, set()).difference(core_names),
                    key=lambda name: self.capture_ordered_names.index(name),
                )
            ]
            core_group_indices = [self.image_group_indices[name] for name in core_names if name in self.image_group_indices]
            overlap_group_indices = [
                self.image_group_indices[name] for name in overlap_names if name in self.image_group_indices
            ]
            chunk_plan = self.build_chunk_plan_from_groups(
                index=index,
                core_group_indices=core_group_indices,
                overlap_group_indices=overlap_group_indices,
                segment_indices=[],
            )
            chunk_plans.append(chunk_plan)
            self.chunk_centroids[index] = self.chunk_plan_centroid_xy(chunk_plan)
            total_overlap_assignments += len(overlap_names)
        chunk_plans.sort(key=lambda plan: (self.chunk_centroids.get(plan.index, (0.0, 0.0))[0], self.chunk_centroids.get(plan.index, (0.0, 0.0))[1], plan.index))
        reindexed_chunk_plans: List[ChunkPlan] = []
        old_to_new = {chunk_plan.index: new_index for new_index, chunk_plan in enumerate(chunk_plans)}
        for new_index, chunk_plan in enumerate(chunk_plans):
            reindexed_chunk_plans.append(
                ChunkPlan(
                    index=new_index,
                    core_names=chunk_plan.core_names,
                    image_names=chunk_plan.image_names,
                    overlap_names=chunk_plan.overlap_names,
                    core_group_indices=chunk_plan.core_group_indices,
                    group_indices=chunk_plan.group_indices,
                    overlap_group_indices=chunk_plan.overlap_group_indices,
                    segment_indices=chunk_plan.segment_indices,
                )
            )
        self.chunk_plans_by_index = {chunk_plan.index: chunk_plan for chunk_plan in reindexed_chunk_plans}
        self.chunk_sizes = [len(chunk_plan.image_names) for chunk_plan in reindexed_chunk_plans]
        self.chunk_overlap_image_count = total_overlap_assignments
        role_counts = defaultdict(int)
        for role in roles.values():
            role_counts[role] += 1
        self.chunk_graph_probe_manifest = {
            "planner": self.chunk_planner,
            "role_counts": dict(role_counts),
            "chunk_pair_budget": self.chunk_pair_budget,
            "chunk_count": len(reindexed_chunk_plans),
            "chunk_sizes": self.chunk_sizes,
            "image_roles": roles,
            "candidate_neighbor_count": {
                image_name: len(edges)
                for image_name, edges in self.graph_neighbors.items()
            },
            "chunks": [
                {
                    "index": chunk_plan.index,
                    "core_names": chunk_plan.core_names,
                    "overlap_names": chunk_plan.overlap_names,
                    "image_names": chunk_plan.image_names,
                    "predicted_pair_count": (
                        len(chunk_plan.image_names) * (len(chunk_plan.image_names) - 1) // 2
                        if self.colmap_capabilities.get("supports_matches_importer") is not True
                        else sum(
                            1
                            for image_name in chunk_plan.image_names
                            for edge in self.graph_neighbors.get(image_name, [])
                            if (edge.second_name if edge.first_name == image_name else edge.first_name) in set(chunk_plan.image_names)
                        ) // 2
                    ),
                }
                for chunk_plan in reindexed_chunk_plans
            ],
        }
        self.probe_subsets = self.select_probe_subsets(reindexed_chunk_plans)
        return reindexed_chunk_plans

    def select_probe_subsets(self, chunk_plans: Sequence[ChunkPlan]) -> Dict[str, List[str]]:
        if not chunk_plans:
            return {}
        geometries = self.build_view_geometries()
        chunk_plan_by_index = {chunk_plan.index: chunk_plan for chunk_plan in chunk_plans}

        def pitch_values_for_names(image_names: Sequence[str]) -> List[float]:
            return [
                float(geometries[name].pitch_deg)
                for name in image_names
                if name in geometries and geometries[name].pitch_deg is not None
            ]

        def time_span_for_names(image_names: Sequence[str]) -> float:
            capture_times = [
                float(self.exif_records[image_name]["capture_time_s"])
                for image_name in image_names
                if self.exif_records[image_name].get("capture_time_s") is not None
            ]
            if not capture_times:
                return 0.0
            return max(capture_times) - min(capture_times)

        def ranked_neighbor_indexes(seed_chunk_index: int) -> List[int]:
            seed_centroid = self.chunk_centroids.get(seed_chunk_index, (0.0, 0.0))
            ranked: List[tuple[float, float, float, int]] = []
            for candidate in chunk_plans:
                if candidate.index == seed_chunk_index:
                    continue
                pair_key = tuple(sorted((seed_chunk_index, candidate.index)))
                cross_edge_count = float(self.chunk_cross_edge_counts.get(pair_key, 0))
                candidate_centroid = self.chunk_centroids.get(candidate.index, (0.0, 0.0))
                centroid_distance = math.hypot(
                    candidate_centroid[0] - seed_centroid[0],
                    candidate_centroid[1] - seed_centroid[1],
                )
                ranked.append(
                    (
                        -cross_edge_count,
                        centroid_distance,
                        -float(len(candidate.image_names)),
                        candidate.index,
                    )
                )
            return [candidate_index for _, _, _, candidate_index in sorted(ranked)]

        def expand_probe(seed_chunk: ChunkPlan) -> tuple[List[str], List[int]]:
            selected_chunk_indexes = [seed_chunk.index]
            selected_names: Set[str] = set(seed_chunk.image_names)
            target_probe_images = min(
                max(self.chunk_target_images * 2, self.chunk_min_images * 2, 240),
                max(self.chunk_target_images * 3, 420),
            )
            for neighbor_index in ranked_neighbor_indexes(seed_chunk.index):
                if len(selected_names) >= target_probe_images and len(selected_chunk_indexes) >= 2:
                    break
                neighbor_plan = chunk_plan_by_index[neighbor_index]
                selected_chunk_indexes.append(neighbor_index)
                selected_names.update(neighbor_plan.image_names)
                if len(selected_chunk_indexes) >= 3:
                    break
            ordered_names = [
                image_name
                for image_name in self.capture_ordered_names
                if image_name in selected_names
            ]
            return ordered_names, selected_chunk_indexes

        geometry_mix = max(
            chunk_plans,
            key=lambda plan: (
                len(plan.image_names),
                len({round(value, 1) for value in pitch_values_for_names(plan.image_names)}),
            ),
        )
        cross_pass = max(
            chunk_plans,
            key=lambda plan: (
                time_span_for_names(plan.image_names),
                len(plan.image_names),
            ),
        )
        horizon_context = max(
            chunk_plans,
            key=lambda plan: (
                sum(
                    1
                    for image_name in plan.image_names
                    if image_name in geometries and geometries[image_name].is_shallow_view
                ),
                len(plan.image_names),
            ),
        )
        probe_subsets: Dict[str, List[str]] = {}
        self.probe_subset_details = {}
        for probe_name, seed_chunk in (
            ("geometry_mix", geometry_mix),
            ("cross_pass", cross_pass),
            ("horizon_context", horizon_context),
        ):
            probe_image_names, source_chunk_indexes = expand_probe(seed_chunk)
            probe_subsets[probe_name] = probe_image_names
            self.probe_subset_details[probe_name] = {
                "seed_chunk_index": seed_chunk.index,
                "source_chunk_indexes": source_chunk_indexes,
                "image_count": len(probe_image_names),
            }
        return probe_subsets

    def build_chunk_plans(self) -> List[ChunkPlan]:
        if self.chunk_planner == "footprint_graph_v1":
            self.chunk_matcher_strategy = (
                "pair_list" if self.colmap_capabilities.get("supports_matches_importer") else "exhaustive"
            )
            return self.build_footprint_graph_chunks()
        self.chunk_matcher_strategy = "spatial_sequential"
        return self.build_spatial_heading_chunks()

    def write_chunk_planner_manifest(self) -> None:
        if self.chunk_planner == "footprint_graph_v1":
            chunk_plans = self.build_chunk_plans()
        else:
            chunk_plans = self.build_chunk_plans()
        manifest = {
            "planner": self.chunk_planner,
            "chunk_matcher_strategy": self.chunk_matcher_strategy,
            "colmap_capabilities": self.colmap_capabilities,
            "chunk_count": len(chunk_plans),
            "chunk_sizes": self.chunk_sizes,
            "chunk_overlap_image_count": self.chunk_overlap_image_count,
            "chunk_group_count": self.chunk_group_count,
            "chunk_segment_count": self.chunk_segment_count,
            "image_roles": self.chunk_role_by_image,
            "probe_subsets": self.probe_subsets,
            "probe_subset_details": self.probe_subset_details,
            "chunks": [
                {
                    "index": chunk_plan.index,
                    "core_names": chunk_plan.core_names,
                    "overlap_names": chunk_plan.overlap_names,
                    "image_names": chunk_plan.image_names,
                }
                for chunk_plan in chunk_plans
            ],
        }
        if self.chunk_graph_probe_manifest:
            manifest["footprint_graph_manifest"] = self.chunk_graph_probe_manifest
        with open(self.output_dir / "chunk_planner_manifest.json", "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)
        if not self.probe_subsets:
            return
        probes_dir = self.output_dir / "probes"
        probes_dir.mkdir(parents=True, exist_ok=True)
        for probe_name, image_names in self.probe_subsets.items():
            probe_path = probes_dir / f"{probe_name}.zip"
            with zipfile.ZipFile(probe_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for image_name in image_names:
                    image_path = self.images_dir / image_name
                    if image_path.exists():
                        archive.write(image_path, arcname=image_name)

    def write_chunk_image_list(self, chunk_plan: ChunkPlan) -> Path:
        chunk_dir = self.work_dir / f"chunk_{chunk_plan.index:02d}"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        image_list_path = chunk_dir / "image_list.txt"
        with open(image_list_path, "w", encoding="utf-8") as handle:
            for image_name in chunk_plan.image_names:
                handle.write(f"{image_name}\n")
        return image_list_path

    def sqlite_sidecar_paths(self, database_path: Path) -> List[Path]:
        return [Path(f"{database_path}{suffix}") for suffix in ("-wal", "-shm", "-journal")]

    def sqlite_connect(
        self,
        database: str | os.PathLike[str],
        *,
        uri: bool = False,
    ) -> sqlite3.Connection:
        connection = sqlite3.connect(
            database,
            uri=uri,
            timeout=self.sqlite_busy_timeout_seconds,
        )
        connection.execute(f"PRAGMA busy_timeout={int(self.sqlite_busy_timeout_seconds * 1000)}")
        return connection

    def is_sqlite_lock_error(self, error: sqlite3.OperationalError) -> bool:
        return "database is locked" in str(error).lower()

    def run_sqlite_operation_with_retry(self, stage: str, operation):
        attempts = max(1, self.sqlite_lock_retry_count + 1)
        last_error: sqlite3.OperationalError | None = None
        for attempt_index in range(attempts):
            try:
                return operation()
            except sqlite3.OperationalError as error:
                if not self.is_sqlite_lock_error(error) or attempt_index == attempts - 1:
                    raise
                last_error = error
                sleep_seconds = self.sqlite_lock_retry_sleep_seconds * (attempt_index + 1)
                logger.warning(
                    "SQLite reported a transient lock during %s (attempt %s/%s): %s; retrying in %.1fs",
                    stage,
                    attempt_index + 1,
                    attempts,
                    error,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"SQLite operation {stage} exhausted retries without an error")

    def remove_sqlite_database_artifacts(self, database_path: Path) -> None:
        for path in [database_path, *self.sqlite_sidecar_paths(database_path)]:
            try:
                path.unlink()
            except FileNotFoundError:
                continue

    def normalize_sqlite_database_for_chunking(self, database_path: Path) -> None:
        if not database_path.exists():
            return

        def normalize() -> None:
            with self.sqlite_connect(database_path) as connection:
                current_mode_row = connection.execute("PRAGMA journal_mode").fetchone()
                current_mode = str(current_mode_row[0]).lower() if current_mode_row else "delete"
                if current_mode == "wal":
                    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                connection.execute("PRAGMA journal_mode=DELETE")
                connection.commit()

        self.run_sqlite_operation_with_retry(
            f"normalize_sqlite_database:{database_path.name}",
            normalize,
        )
        for sidecar_path in self.sqlite_sidecar_paths(database_path):
            try:
                sidecar_path.unlink()
            except FileNotFoundError:
                continue

    def clone_database_for_chunk(self, destination_path: Path) -> None:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        self.remove_sqlite_database_artifacts(destination_path)
        source_uri = f"file:{self.database_path.as_posix()}?mode=ro"

        def backup_database() -> None:
            with self.sqlite_connect(source_uri, uri=True) as source_connection:
                source_connection.execute("PRAGMA query_only=1")
                with self.sqlite_connect(destination_path) as destination_connection:
                    source_connection.backup(destination_connection, pages=2048, sleep=0.05)
                    destination_connection.execute("PRAGMA journal_mode=DELETE")
                    destination_connection.commit()

        self.run_sqlite_operation_with_retry(
            f"clone_database_for_chunk:{destination_path.parent.name}",
            backup_database,
        )
        self.normalize_sqlite_database_for_chunking(destination_path)

    def prune_chunk_database(
        self,
        chunk_database_path: Path,
        *,
        keep_image_names: Set[str],
        supports_pose_prior_image_backfill: bool,
    ) -> None:
        with self.sqlite_connect(chunk_database_path) as connection:
            connection.execute("PRAGMA journal_mode=DELETE")
            rows = connection.execute("SELECT image_id, name, camera_id FROM images").fetchall()
            remove_image_ids = [int(image_id) for image_id, name, _ in rows if str(name) not in keep_image_names]
            if remove_image_ids:
                placeholders = ",".join("?" for _ in remove_image_ids)
                connection.execute(f"DELETE FROM keypoints WHERE image_id IN ({placeholders})", remove_image_ids)
                connection.execute(f"DELETE FROM descriptors WHERE image_id IN ({placeholders})", remove_image_ids)
                if supports_pose_prior_image_backfill:
                    connection.execute(
                        f"DELETE FROM pose_priors WHERE image_id IN ({placeholders})",
                        remove_image_ids,
                    )
                connection.execute(f"DELETE FROM images WHERE image_id IN ({placeholders})", remove_image_ids)

            used_camera_ids = [row[0] for row in connection.execute("SELECT DISTINCT camera_id FROM images").fetchall()]
            if used_camera_ids:
                placeholders = ",".join("?" for _ in used_camera_ids)
                connection.execute(
                    f"DELETE FROM cameras WHERE camera_id NOT IN ({placeholders})",
                    used_camera_ids,
                )
            else:
                connection.execute("DELETE FROM cameras")

            # Always rebuild matches inside the chunk-specific database.
            connection.execute("DELETE FROM matches")
            connection.execute("DELETE FROM two_view_geometries")
            connection.commit()

    def prepare_chunk_database(self, chunk_plan: ChunkPlan, *, dir_name: str | None = None) -> Path:
        chunk_dir = self.work_dir / (dir_name or f"chunk_{chunk_plan.index:02d}")
        chunk_dir.mkdir(parents=True, exist_ok=True)
        chunk_database_path = chunk_dir / "database.db"
        # Chunk retries can reuse the same directory name; create a fresh SQLite clone so
        # stale WAL/SHM files from the previous attempt cannot corrupt the next retry.
        self.clone_database_for_chunk(chunk_database_path)
        supports_pose_prior_image_backfill = self.run_sqlite_operation_with_retry(
            f"inspect_chunk_database_schema:{chunk_plan.index:02d}",
            lambda: self.supports_pose_prior_image_backfill(database_path=chunk_database_path),
        )

        keep_image_names = set(chunk_plan.image_names)
        self.run_sqlite_operation_with_retry(
            f"prune_chunk_database:{chunk_plan.index:02d}",
            lambda: self.prune_chunk_database(
                chunk_database_path,
                keep_image_names=keep_image_names,
                supports_pose_prior_image_backfill=supports_pose_prior_image_backfill,
            ),
        )
        for sidecar_path in self.sqlite_sidecar_paths(chunk_database_path):
            if sidecar_path.exists():
                sidecar_path.unlink()

        logger.info(
            "Prepared chunk %s database by pruning global features down to %s images",
            chunk_plan.index,
            len(chunk_plan.image_names),
        )
        return chunk_database_path

    def chunk_registered_ratio_threshold(self) -> float:
        return self.gps_min_registered_ratio

    def chunk_core_registered_ratio(
        self,
        chunk_plan: ChunkPlan,
        model: ModelSummary,
    ) -> tuple[float, int, Set[str]]:
        registered_names = load_registered_image_names(model.text_dir / "images.txt")
        if not chunk_plan.core_names:
            return 0.0, 0, registered_names
        if not registered_names:
            return 0.0, 0, registered_names
        core_registered_count = len(set(chunk_plan.core_names).intersection(registered_names))
        return core_registered_count / len(chunk_plan.core_names), core_registered_count, registered_names

    def retry_group_indices_for_missing_core_names(self, missing_core_names: Sequence[str]) -> List[int]:
        missing_group_indices = sorted(
            {
                self.image_group_indices[image_name]
                for image_name in missing_core_names
                if image_name in self.image_group_indices
            }
        )
        if not missing_group_indices:
            return []
        expanded_group_indices: Set[int] = set()
        interval_start = missing_group_indices[0]
        interval_end = missing_group_indices[0]
        for group_index in missing_group_indices[1:]:
            if group_index == interval_end + 1:
                interval_end = group_index
                continue
            expanded_group_indices.update(
                range(
                    max(0, interval_start - self.chunk_retry_group_context),
                    min(len(self.chunk_groups), interval_end + self.chunk_retry_group_context + 1),
                )
            )
            interval_start = interval_end = group_index
        expanded_group_indices.update(
            range(
                max(0, interval_start - self.chunk_retry_group_context),
                min(len(self.chunk_groups), interval_end + self.chunk_retry_group_context + 1),
            )
        )
        return sorted(expanded_group_indices)

    def build_retry_chunk_plan(
        self,
        chunk_plan: ChunkPlan,
        missing_core_names: Sequence[str],
    ) -> ChunkPlan:
        if self.chunk_planner == "footprint_graph_v1":
            retry_names = set(chunk_plan.image_names)
            candidate_names: List[tuple[float, str]] = []
            for missing_name in missing_core_names:
                for edge in self.graph_neighbors.get(missing_name, []):
                    neighbor_name = edge.second_name if edge.first_name == missing_name else edge.first_name
                    if neighbor_name in retry_names:
                        continue
                    candidate_names.append((edge.score, neighbor_name))
            for _, neighbor_name in sorted(candidate_names, key=lambda item: (-item[0], item[1])):
                retry_names.add(neighbor_name)
                if len(retry_names) >= min(self.chunk_hard_max_images, len(chunk_plan.image_names) + 24):
                    break
            if retry_names == set(chunk_plan.image_names):
                return chunk_plan
            retry_ordered_names = sorted(retry_names, key=lambda name: self.capture_ordered_names.index(name))
            retry_core_names = list(chunk_plan.core_names)
            retry_overlap_names = [name for name in retry_ordered_names if name not in set(retry_core_names)]
            return ChunkPlan(
                index=chunk_plan.index,
                core_names=retry_core_names,
                image_names=retry_ordered_names,
                overlap_names=retry_overlap_names,
                core_group_indices=[
                    self.image_group_indices[name] for name in retry_core_names if name in self.image_group_indices
                ],
                group_indices=[
                    self.image_group_indices[name] for name in retry_ordered_names if name in self.image_group_indices
                ],
                overlap_group_indices=[
                    self.image_group_indices[name] for name in retry_overlap_names if name in self.image_group_indices
                ],
                segment_indices=list(chunk_plan.segment_indices),
            )
        retry_group_indices = sorted(
            set(chunk_plan.group_indices).union(self.retry_group_indices_for_missing_core_names(missing_core_names))
        )
        if not retry_group_indices:
            return chunk_plan
        retry_overlap_group_indices = sorted(
            set(retry_group_indices).difference(chunk_plan.core_group_indices)
        )
        retry_segment_indices = sorted(
            {
                segment.index
                for segment in self.flight_segments
                if set(segment.group_indices).intersection(retry_group_indices)
            }
        )
        return self.build_chunk_plan_from_groups(
            index=chunk_plan.index,
            core_group_indices=chunk_plan.core_group_indices or sorted(
                {
                    self.image_group_indices[image_name]
                    for image_name in chunk_plan.core_names
                    if image_name in self.image_group_indices
                }
            ),
            overlap_group_indices=retry_overlap_group_indices,
            segment_indices=retry_segment_indices or chunk_plan.segment_indices,
        )

    def build_adjacent_merged_chunk_plan(
        self,
        first_chunk_plan: ChunkPlan,
        second_chunk_plan: ChunkPlan,
        *,
        index: int,
    ) -> ChunkPlan:
        if self.chunk_planner == "footprint_graph_v1":
            merged_core_names = sorted(
                set(first_chunk_plan.core_names).union(second_chunk_plan.core_names),
                key=lambda name: self.capture_ordered_names.index(name),
            )
            merged_overlap_names = sorted(
                set(first_chunk_plan.overlap_names).union(second_chunk_plan.overlap_names).difference(merged_core_names),
                key=lambda name: self.capture_ordered_names.index(name),
            )
            merged_image_names = sorted(
                set(merged_core_names).union(merged_overlap_names),
                key=lambda name: self.capture_ordered_names.index(name),
            )
            return ChunkPlan(
                index=index,
                core_names=merged_core_names,
                image_names=merged_image_names,
                overlap_names=merged_overlap_names,
                core_group_indices=[
                    self.image_group_indices[name] for name in merged_core_names if name in self.image_group_indices
                ],
                group_indices=[
                    self.image_group_indices[name] for name in merged_image_names if name in self.image_group_indices
                ],
                overlap_group_indices=[
                    self.image_group_indices[name] for name in merged_overlap_names if name in self.image_group_indices
                ],
                segment_indices=[],
            )
        merged_core_group_indices = sorted(
            set(first_chunk_plan.core_group_indices).union(second_chunk_plan.core_group_indices)
        )
        merged_overlap_group_indices = sorted(
            set(first_chunk_plan.overlap_group_indices)
            .union(second_chunk_plan.overlap_group_indices)
            .difference(merged_core_group_indices)
        )
        merged_segment_indices = sorted(
            set(first_chunk_plan.segment_indices).union(second_chunk_plan.segment_indices)
        )
        return self.build_chunk_plan_from_groups(
            index=index,
            core_group_indices=merged_core_group_indices,
            overlap_group_indices=merged_overlap_group_indices,
            segment_indices=merged_segment_indices,
        )

    def build_chunk_plan_from_image_names(
        self,
        *,
        index: int,
        image_names: Sequence[str],
    ) -> ChunkPlan:
        ordered_names = self.sorted_capture_names(image_names)
        group_indices = [
            self.image_group_indices[name]
            for name in ordered_names
            if name in self.image_group_indices
        ]
        return ChunkPlan(
            index=index,
            core_names=list(ordered_names),
            image_names=list(ordered_names),
            overlap_names=[],
            core_group_indices=list(group_indices),
            group_indices=list(group_indices),
            overlap_group_indices=[],
            segment_indices=[],
        )

    def model_source_image_names(self, model: ModelSummary) -> List[str]:
        if model.image_names:
            return self.sorted_capture_names(model.image_names)
        return self.sorted_capture_names(self.merged_image_names(model))

    def run_image_registrator(
        self,
        *,
        database_path: Path,
        input_path: Path,
        stage: str,
        image_count: int,
    ) -> ModelSummary:
        started = time.time()
        output_path = self.work_dir / stage
        output_path.mkdir(parents=True, exist_ok=True)
        stream_command(
            [
                "colmap",
                "image_registrator",
                "--database_path",
                str(database_path),
                "--input_path",
                str(input_path),
                "--output_path",
                str(output_path),
                "--Mapper.num_threads",
                str(self.mapper_threads),
                "--Mapper.ba_refine_principal_point",
                "0",
                "--Mapper.fix_existing_images",
                "1",
            ],
            stage=stage,
            timeout_seconds=self.resolve_timeout_seconds(self.parent_registrator_timeout_seconds),
            heartbeat_seconds=self.command_heartbeat_seconds,
        )
        self.timings[f"{stage}_seconds"] = round(time.time() - started, 2)
        return self.summarize_model(
            stage=stage,
            binary_dir=output_path,
            image_count=image_count,
        )

    def run_point_triangulator(
        self,
        *,
        database_path: Path,
        input_path: Path,
        stage: str,
        image_count: int,
    ) -> ModelSummary:
        started = time.time()
        output_path = self.work_dir / stage
        output_path.mkdir(parents=True, exist_ok=True)
        stream_command(
            [
                "colmap",
                "point_triangulator",
                "--database_path",
                str(database_path),
                "--image_path",
                str(self.images_dir),
                "--input_path",
                str(input_path),
                "--output_path",
                str(output_path),
                "--clear_points",
                "1",
                "--Mapper.num_threads",
                str(self.mapper_threads),
                "--Mapper.ba_refine_principal_point",
                "0",
                "--Mapper.fix_existing_images",
                "1",
            ],
            stage=stage,
            timeout_seconds=self.resolve_timeout_seconds(self.parent_triangulator_timeout_seconds),
            heartbeat_seconds=self.command_heartbeat_seconds,
        )
        self.timings[f"{stage}_seconds"] = round(time.time() - started, 2)
        return self.summarize_model(
            stage=stage,
            binary_dir=output_path,
            image_count=image_count,
        )

    def run_parent_seam_registration(
        self,
        *,
        seed_model: ModelSummary,
        chunk_plan: ChunkPlan,
        stage_prefix: str,
        dir_name: str | None = None,
        bridge_target_name_sets: Sequence[Set[str]] | None = None,
        run_final_bundle_adjustment: bool = True,
    ) -> ModelSummary:
        seam_dir_name = dir_name or f"{stage_prefix}_seam"
        seam_dir = self.work_dir / seam_dir_name
        seam_dir.mkdir(parents=True, exist_ok=True)
        seam_database_path = self.prepare_chunk_database(chunk_plan, dir_name=seam_dir_name)
        self.run_chunk_matchers(
            chunk_plan,
            chunk_database_path=seam_database_path,
            chunk_dir=seam_dir,
            stage_prefix=stage_prefix,
            bridge_target_name_sets=bridge_target_name_sets,
        )
        current_model = seed_model
        current_model.image_names = list(chunk_plan.image_names)
        previous_registered_count = current_model.images_registered
        for cycle in range(1, max(self.parent_seam_registration_cycles, 0) + 1):
            registrator_model = self.run_image_registrator(
                database_path=seam_database_path,
                input_path=current_model.binary_dir,
                stage=f"{stage_prefix}_image_registrator_{cycle:02d}",
                image_count=len(chunk_plan.image_names),
            )
            registrator_model.image_names = list(chunk_plan.image_names)
            triangulated_model = self.run_point_triangulator(
                database_path=seam_database_path,
                input_path=registrator_model.binary_dir,
                stage=f"{stage_prefix}_point_triangulator_{cycle:02d}",
                image_count=len(chunk_plan.image_names),
            )
            triangulated_model.image_names = list(chunk_plan.image_names)
            current_model = triangulated_model
            if current_model.images_registered <= previous_registered_count:
                break
            previous_registered_count = current_model.images_registered
        if not run_final_bundle_adjustment:
            current_model.image_names = list(chunk_plan.image_names)
            return current_model
        adjusted_model = self.run_bundle_adjuster(
            input_path=current_model.binary_dir,
            stage=f"{stage_prefix}_bundle_adjuster",
        )
        adjusted_model.image_names = list(chunk_plan.image_names)
        return adjusted_model

    def run_chunk_pipeline(
        self,
        chunk_plan: ChunkPlan,
        *,
        stage_prefix: str | None = None,
        dir_name: str | None = None,
        allow_partial_result: bool = False,
        bridge_target_name_sets: Sequence[Set[str]] | None = None,
    ) -> ModelSummary:
        chunk_stage_prefix = stage_prefix or f"chunk_{chunk_plan.index:02d}"
        chunk_dir = self.work_dir / (dir_name or chunk_stage_prefix)
        chunk_dir.mkdir(parents=True, exist_ok=True)
        chunk_database_path = self.prepare_chunk_database(chunk_plan, dir_name=dir_name or chunk_stage_prefix)
        self.run_chunk_matchers(
            chunk_plan,
            chunk_database_path=chunk_database_path,
            chunk_dir=chunk_dir,
            stage_prefix=chunk_stage_prefix,
            bridge_target_name_sets=bridge_target_name_sets,
        )
        initial_model = self.run_mapper(
            database_path=chunk_database_path,
            stage=f"{chunk_stage_prefix}_mapper_initial",
            sparse_root=chunk_dir / "sparse_initial",
            image_count=len(chunk_plan.image_names),
            bridge_target_name_sets=bridge_target_name_sets,
            allow_partial_timeout_result=allow_partial_result,
        )
        self.chunk_mapper_seconds += self.timings[f"{chunk_stage_prefix}_mapper_initial_seconds"]
        initial_model.image_names = list(chunk_plan.image_names)
        registered_ratio = (
            initial_model.images_registered / len(chunk_plan.image_names)
            if chunk_plan.image_names
            else 0.0
        )
        core_registered_ratio, core_registered_count, registered_names = self.chunk_core_registered_ratio(
            chunk_plan,
            initial_model,
        )
        core_missing_names = sorted(set(chunk_plan.core_names).difference(registered_names))
        if registered_ratio >= self.chunk_registered_ratio_threshold():
            self.chunk_run_metrics.append(
                {
                    "chunk_index": chunk_plan.index,
                    "image_count": len(chunk_plan.image_names),
                    "registered_ratio": round(registered_ratio, 4),
                    "core_registered_ratio": round(core_registered_ratio, 4),
                    "recovered_registered_ratio": None,
                    "recovered_core_registered_ratio": None,
                    "failure": False,
                }
            )
            return initial_model
        if core_registered_ratio >= self.chunk_min_core_registered_ratio:
            logger.info(
                "Chunk %s registered %s/%s total images (%.2f%%) but %s/%s core images (%.2f%%); skipping boundary recovery",
                chunk_plan.index,
                initial_model.images_registered,
                len(chunk_plan.image_names),
                registered_ratio * 100.0,
                core_registered_count,
                len(chunk_plan.core_names),
                core_registered_ratio * 100.0,
            )
            self.chunk_run_metrics.append(
                {
                    "chunk_index": chunk_plan.index,
                    "image_count": len(chunk_plan.image_names),
                    "registered_ratio": round(registered_ratio, 4),
                    "core_registered_ratio": round(core_registered_ratio, 4),
                    "recovered_registered_ratio": None,
                    "recovered_core_registered_ratio": None,
                    "failure": False,
                }
            )
            return initial_model
        if allow_partial_result and initial_model.partial_result and initial_model.images_registered > 0:
            bridge_target_count = len(bridge_target_name_sets or [])
            touched_targets = 0
            if bridge_target_name_sets:
                touched_targets, _ = bridge_overlap_counts(
                    self.merged_image_names(initial_model),
                    bridge_target_name_sets,
                )
            logger.info(
                "Chunk %s mapper timed out after registering %s/%s images; returning the partial initial result for bridge evaluation (%s/%s target components touched)",
                chunk_plan.index,
                initial_model.images_registered,
                len(chunk_plan.image_names),
                touched_targets,
                bridge_target_count,
            )
            self.clear_failure()
            self.chunk_run_metrics.append(
                {
                    "chunk_index": chunk_plan.index,
                    "image_count": len(chunk_plan.image_names),
                    "registered_ratio": round(registered_ratio, 4),
                    "core_registered_ratio": round(core_registered_ratio, 4),
                    "recovered_registered_ratio": None,
                    "recovered_core_registered_ratio": None,
                    "failure": False,
                    "partial_result_accepted": True,
                    "partial_result_stage": "initial",
                    "partial_result_timed_out": True,
                }
            )
            return initial_model

        logger.info(
            "Chunk %s registered %s/%s images (%.2f%%) with %s/%s core images (%.2f%%); running targeted boundary recovery. Missing core images: %s",
            chunk_plan.index,
            initial_model.images_registered,
            len(chunk_plan.image_names),
            registered_ratio * 100.0,
            core_registered_count,
            len(chunk_plan.core_names),
            core_registered_ratio * 100.0,
            core_missing_names,
        )
        self.boundary_recovery_triggered = True
        retry_chunk_plan = self.build_retry_chunk_plan(chunk_plan, core_missing_names)
        if retry_chunk_plan.image_names != chunk_plan.image_names:
            logger.info(
                "Chunk %s retry expanded from %s to %s images across groups %s",
                chunk_plan.index,
                len(chunk_plan.image_names),
                len(retry_chunk_plan.image_names),
                retry_chunk_plan.group_indices,
            )
            chunk_database_path = self.prepare_chunk_database(
                retry_chunk_plan,
                dir_name=dir_name or chunk_stage_prefix,
            )
        self.run_chunk_recovery_matchers(
            chunk_database_path=chunk_database_path,
            chunk_dir=chunk_dir,
            chunk_plan=retry_chunk_plan,
            stage_prefix=chunk_stage_prefix,
        )
        recovered_model = self.run_mapper(
            database_path=chunk_database_path,
            stage=f"{chunk_stage_prefix}_mapper_recovery",
            sparse_root=chunk_dir / "sparse_recovery",
            image_count=len(retry_chunk_plan.image_names),
            bridge_target_name_sets=bridge_target_name_sets,
            allow_partial_timeout_result=allow_partial_result,
        )
        self.chunk_mapper_seconds += self.timings[f"{chunk_stage_prefix}_mapper_recovery_seconds"]
        recovered_model.image_names = list(retry_chunk_plan.image_names)
        recovered_ratio = (
            recovered_model.images_registered / len(retry_chunk_plan.image_names)
            if retry_chunk_plan.image_names
            else 0.0
        )
        recovered_core_ratio, recovered_core_count, recovered_registered_names = self.chunk_core_registered_ratio(
            retry_chunk_plan,
            recovered_model,
        )
        if recovered_ratio >= self.chunk_registered_ratio_threshold():
            self.chunk_run_metrics.append(
                {
                    "chunk_index": chunk_plan.index,
                    "image_count": len(chunk_plan.image_names),
                    "registered_ratio": round(registered_ratio, 4),
                    "core_registered_ratio": round(core_registered_ratio, 4),
                    "recovered_registered_ratio": round(recovered_ratio, 4),
                    "recovered_core_registered_ratio": round(recovered_core_ratio, 4),
                    "failure": False,
                }
            )
            return recovered_model
        if recovered_core_ratio >= self.chunk_min_core_registered_ratio:
            logger.info(
                "Chunk %s recovered to %s/%s total images (%.2f%%) with %s/%s core images (%.2f%%); accepting retry result",
                retry_chunk_plan.index,
                recovered_model.images_registered,
                len(retry_chunk_plan.image_names),
                recovered_ratio * 100.0,
                recovered_core_count,
                len(retry_chunk_plan.core_names),
                recovered_core_ratio * 100.0,
            )
            self.chunk_run_metrics.append(
                {
                    "chunk_index": chunk_plan.index,
                    "image_count": len(chunk_plan.image_names),
                    "registered_ratio": round(registered_ratio, 4),
                    "core_registered_ratio": round(core_registered_ratio, 4),
                    "recovered_registered_ratio": round(recovered_ratio, 4),
                    "recovered_core_registered_ratio": round(recovered_core_ratio, 4),
                    "failure": False,
                }
            )
            return recovered_model
        if allow_partial_result and recovered_model.images_registered > 0:
            bridge_target_count = len(bridge_target_name_sets or [])
            touched_targets = 0
            if bridge_target_name_sets:
                touched_targets, _ = bridge_overlap_counts(
                    self.merged_image_names(recovered_model),
                    bridge_target_name_sets,
                )
            logger.info(
                "Chunk %s remained below the standard retry threshold at %s/%s images and %s/%s core images; returning partial result for bridge evaluation (%s/%s target components touched)",
                retry_chunk_plan.index,
                recovered_model.images_registered,
                len(retry_chunk_plan.image_names),
                recovered_core_count,
                len(retry_chunk_plan.core_names),
                touched_targets,
                bridge_target_count,
            )
            self.clear_failure()
            self.chunk_run_metrics.append(
                {
                    "chunk_index": chunk_plan.index,
                    "image_count": len(chunk_plan.image_names),
                    "registered_ratio": round(registered_ratio, 4),
                    "core_registered_ratio": round(core_registered_ratio, 4),
                    "recovered_registered_ratio": round(recovered_ratio, 4),
                    "recovered_core_registered_ratio": round(recovered_core_ratio, 4),
                    "failure": False,
                    "partial_result_accepted": True,
                    "partial_result_stage": "recovery",
                    "partial_result_timed_out": recovered_model.timed_out,
                }
            )
            return recovered_model
        if (
            self.parent_merge_mode == "seam_only_v1"
            and self.chunk_planner == "footprint_graph_v1"
            and recovered_model.images_registered > 0
        ):
            logger.info(
                "Chunk %s remained below the standard retry threshold at %s/%s images and %s/%s core images; carrying the recovery model forward as a seam-only leaf seed instead of triggering an adjacent mapper rerun",
                retry_chunk_plan.index,
                recovered_model.images_registered,
                len(retry_chunk_plan.image_names),
                recovered_core_count,
                len(retry_chunk_plan.core_names),
            )
            self.chunk_recovery_mode = "seam_only_leaf_partial"
            self.clear_failure()
            self.chunk_run_metrics.append(
                {
                    "chunk_index": chunk_plan.index,
                    "image_count": len(chunk_plan.image_names),
                    "registered_ratio": round(registered_ratio, 4),
                    "core_registered_ratio": round(core_registered_ratio, 4),
                    "recovered_registered_ratio": round(recovered_ratio, 4),
                    "recovered_core_registered_ratio": round(recovered_core_ratio, 4),
                    "failure": False,
                    "partial_result_accepted": True,
                    "partial_result_stage": "recovery",
                    "partial_result_timed_out": recovered_model.timed_out,
                    "partial_result_reason": "seam_only_leaf_seed",
                }
            )
            return recovered_model
        self.mark_failure(
            stage=f"{chunk_stage_prefix}_recovery_failed",
            reason=(
                f"chunk {retry_chunk_plan.index} remained below threshold after prior-aware retry: "
                f"registered={recovered_model.images_registered}/{len(retry_chunk_plan.image_names)} "
                f"core={recovered_core_count}/{len(retry_chunk_plan.core_names)} "
                f"missing_core={sorted(set(retry_chunk_plan.core_names).difference(recovered_registered_names))}"
            ),
            chunk_index=retry_chunk_plan.index,
            registered_ratio=recovered_ratio,
            core_registered_ratio=recovered_core_ratio,
        )
        self.chunk_run_metrics.append(
            {
                "chunk_index": chunk_plan.index,
                "image_count": len(chunk_plan.image_names),
                "registered_ratio": round(registered_ratio, 4),
                "core_registered_ratio": round(core_registered_ratio, 4),
                "recovered_registered_ratio": round(recovered_ratio, 4),
                "recovered_core_registered_ratio": round(recovered_core_ratio, 4),
                "failure": True,
            }
        )
        raise RuntimeError(self.failure_reason_detail)

    def merged_image_names(self, model: ModelSummary) -> Set[str]:
        return load_registered_image_names(model.text_dir / "images.txt")

    def merge_result_is_usable(
        self,
        *,
        merged_names: Set[str],
        existing_names: Set[str],
        next_names: Set[str],
    ) -> bool:
        if not merged_names or len(merged_names) < max(len(existing_names), len(next_names)):
            return False
        existing_retained_ratio = (
            len(merged_names.intersection(existing_names)) / len(existing_names)
            if existing_names
            else 1.0
        )
        next_retained_ratio = (
            len(merged_names.intersection(next_names)) / len(next_names)
            if next_names
            else 1.0
        )
        new_from_next = len(merged_names.intersection(next_names.difference(existing_names)))
        if existing_retained_ratio < 0.95:
            return False
        if next_names.difference(existing_names) and new_from_next == 0:
            return False
        return next_retained_ratio >= 0.5

    def connector_merge_is_usable(
        self,
        *,
        merged_names: Set[str],
        first_model: ModelSummary,
        first_names: Set[str],
        second_model: ModelSummary,
        second_names: Set[str],
    ) -> bool:
        if is_bridge_model_stage(first_model.stage) == is_bridge_model_stage(second_model.stage):
            return False
        connector_names = first_names if is_bridge_model_stage(first_model.stage) else second_names
        primary_names = second_names if connector_names is first_names else first_names
        if not primary_names:
            return False
        primary_retained_ratio = len(merged_names.intersection(primary_names)) / len(primary_names)
        connector_unique_names = connector_names.difference(primary_names)
        connector_unique_retained = len(merged_names.intersection(connector_unique_names))
        return primary_retained_ratio >= 0.95 and connector_unique_retained > 0

    def auxiliary_bridge_model_is_usable(
        self,
        *,
        model: ModelSummary,
        target_name_sets: Sequence[Set[str]],
    ) -> bool:
        registered_names = self.merged_image_names(model)
        touched_name_sets = [
            target_name_set
            for target_name_set in target_name_sets
            if registered_names.intersection(target_name_set)
        ]
        if not touched_name_sets:
            return False
        touched_union = set().union(*touched_name_sets)
        return len(registered_names.difference(touched_union)) > 0

    def merge_chunk_models(self, chunk_models: Sequence[ModelSummary]) -> ModelSummary:
        if not chunk_models:
            raise RuntimeError("No chunk models available to merge")
        if len(chunk_models) == 1:
            self.merged_component_count = 1
            self.chunk_merge_proof = {
                "chunk_model_count": 1,
                "pre_merge_unique_registered_images": chunk_models[0].images_registered,
                "final_merged_registered_images": chunk_models[0].images_registered,
                "pre_merge_retention_ratio": 1.0,
            }
            return chunk_models[0]

        merge_started = time.time()
        pending_models = list(chunk_models)
        registered_names_by_stage = {
            model.stage: self.merged_image_names(model)
            for model in pending_models
        }
        merge_sequence = 1
        while len(pending_models) > 1:
            ranked_pairs: List[tuple[int, int, int, int, int]] = []
            for first_index, first_model in enumerate(pending_models):
                first_names = registered_names_by_stage[first_model.stage]
                for second_index in range(first_index + 1, len(pending_models)):
                    second_model = pending_models[second_index]
                    second_names = registered_names_by_stage[second_model.stage]
                    shared_count = len(first_names.intersection(second_names))
                    ranked_pairs.append(
                        (
                            -shared_count,
                            -min(len(first_names), len(second_names)),
                            -(len(first_names) + len(second_names)),
                            first_index,
                            second_index,
                        )
                    )
            ranked_pairs.sort()
            merge_error: RuntimeError | None = None
            merged_candidate: ModelSummary | None = None
            merged_pair_indexes: tuple[int, int] | None = None
            for _, _, _, first_index, second_index in ranked_pairs:
                current_model = pending_models[first_index]
                next_model = pending_models[second_index]
                existing_names = registered_names_by_stage[current_model.stage]
                next_names = registered_names_by_stage[next_model.stage]
                if not existing_names.intersection(next_names):
                    continue
                for attempt_index, (input_one, input_two) in enumerate(
                    (
                        (current_model, next_model),
                        (next_model, current_model),
                    ),
                    start=1,
                ):
                    output_path = self.work_dir / f"merged_chunk_model_{merge_sequence:02d}_attempt_{attempt_index:02d}"
                    output_path.mkdir(parents=True, exist_ok=True)
                    stage_name = f"chunk_model_merger_{merge_sequence:02d}"
                    if attempt_index > 1:
                        logger.warning(
                            "Retrying chunk model merge %s with swapped input order after weak merge retention",
                            merge_sequence,
                        )
                    try:
                        stream_command(
                            [
                                "colmap",
                                "model_merger",
                                "--input_path1",
                                str(input_one.binary_dir),
                                "--input_path2",
                                str(input_two.binary_dir),
                                "--output_path",
                                str(output_path),
                                "--max_reproj_error",
                                "64",
                            ],
                            stage=stage_name,
                            timeout_seconds=self.resolve_timeout_seconds(self.matcher_timeout_seconds),
                            heartbeat_seconds=self.command_heartbeat_seconds,
                        )
                    except RuntimeError as exc:
                        merge_error = exc
                        continue
                    merged_candidate = self.summarize_model(
                        stage=f"{stage_name}_output_attempt_{attempt_index:02d}",
                        binary_dir=output_path,
                        image_count=self.dataset_image_count,
                    )
                    merged_names = self.merged_image_names(merged_candidate)
                    if (
                        self.merge_result_is_usable(
                            merged_names=merged_names,
                            existing_names=existing_names,
                            next_names=next_names,
                        )
                        or self.merge_result_is_usable(
                            merged_names=merged_names,
                            existing_names=next_names,
                            next_names=existing_names,
                        )
                        or self.connector_merge_is_usable(
                            merged_names=merged_names,
                            first_model=current_model,
                            first_names=existing_names,
                            second_model=next_model,
                            second_names=next_names,
                        )
                    ):
                        merged_candidate.image_names = self.sorted_capture_names(
                            set(self.model_source_image_names(input_one)).union(
                                self.model_source_image_names(input_two)
                            )
                        )
                        if self.parent_merge_mode == "seam_only_v1" and merged_candidate.image_names:
                            try:
                                merged_candidate = self.run_parent_seam_registration(
                                    seed_model=merged_candidate,
                                    chunk_plan=self.build_chunk_plan_from_image_names(
                                        index=merge_sequence,
                                        image_names=merged_candidate.image_names,
                                    ),
                                    stage_prefix=f"chunk_model_seam_{merge_sequence:02d}",
                                    dir_name=f"merged_chunk_model_{merge_sequence:02d}_seam",
                                    run_final_bundle_adjustment=False,
                                )
                            except RuntimeError as seam_error:
                                logger.warning(
                                    "Parent seam refinement failed for merge %s; keeping raw model_merger result: %s",
                                    merge_sequence,
                                    seam_error,
                                )
                        merged_pair_indexes = (first_index, second_index)
                        break
                    merged_candidate = None
                if merged_candidate is not None:
                    break
            if merged_candidate is None or merged_pair_indexes is None:
                self.merged_component_count = len(pending_models)
                if merge_error is not None:
                    self.handle_stage_runtime_error(f"chunk_model_merger_{merge_sequence:02d}", merge_error)
                    raise RuntimeError(f"Failed to merge chunk model {merge_sequence}: {merge_error}") from merge_error
                raise RuntimeError(
                    "Failed to merge chunk models: no overlapping registered images produced a usable merge"
                )
            for removal_index in sorted(merged_pair_indexes, reverse=True):
                pending_models.pop(removal_index)
            pending_models.append(merged_candidate)
            registered_names_by_stage[merged_candidate.stage] = self.merged_image_names(merged_candidate)
            merge_sequence += 1
        self.chunk_merge_seconds = round(time.time() - merge_started, 2)
        self.timings["chunk_model_merge_seconds"] = self.chunk_merge_seconds
        self.merged_component_count = 1
        self.pipeline_name = "colmap_gpu_spatial_heading_chunked"
        current_model = pending_models[0]
        adjusted_model = self.run_bundle_adjuster(input_path=current_model.binary_dir, stage="chunk_bundle_adjuster")
        pre_merge_registered_names: Set[str] = set()
        for chunk_model in chunk_models:
            pre_merge_registered_names.update(load_registered_image_names(chunk_model.text_dir / "images.txt"))
        merged_registered_names = load_registered_image_names(adjusted_model.text_dir / "images.txt")
        retained_registered_names = pre_merge_registered_names.intersection(merged_registered_names)
        pre_merge_registered_count = len(pre_merge_registered_names)
        self.chunk_merge_proof = {
            "chunk_model_count": len(chunk_models),
            "pre_merge_unique_registered_images": pre_merge_registered_count,
            "final_merged_registered_images": len(merged_registered_names),
            "retained_registered_images": len(retained_registered_names),
            "pre_merge_retention_ratio": round(
                len(retained_registered_names) / pre_merge_registered_count,
                4,
            )
            if pre_merge_registered_count
            else 0.0,
        }
        return adjusted_model

    def registered_overlap_components(
        self,
        chunk_models: Sequence[ModelSummary],
    ) -> tuple[List[Set[int]], List[Set[str]]]:
        registered_name_sets = [self.merged_image_names(model) for model in chunk_models]
        unvisited = set(range(len(chunk_models)))
        components: List[Set[int]] = []
        while unvisited:
            seed_index = min(unvisited)
            unvisited.remove(seed_index)
            component = {seed_index}
            pending = [seed_index]
            while pending:
                current_index = pending.pop()
                current_names = registered_name_sets[current_index]
                for candidate_index in list(unvisited):
                    if current_names.intersection(registered_name_sets[candidate_index]):
                        unvisited.remove(candidate_index)
                        component.add(candidate_index)
                        pending.append(candidate_index)
            components.append(component)
        return components, registered_name_sets

    def component_registered_names(
        self,
        *,
        component: Set[int],
        registered_name_sets: Sequence[Set[str]],
    ) -> Set[str]:
        combined_names: Set[str] = set()
        for chunk_index in component:
            combined_names.update(registered_name_sets[chunk_index])
        return combined_names

    def model_connects_target_name_sets(
        self,
        *,
        model: ModelSummary,
        target_name_sets: Sequence[Set[str]],
    ) -> bool:
        if not target_name_sets:
            return False
        touched_targets, _ = bridge_overlap_counts(self.merged_image_names(model), target_name_sets)
        return touched_targets >= len(target_name_sets)

    def best_bridge_chunk_pair(
        self,
        *,
        chunk_plans: Sequence[ChunkPlan],
        components: Sequence[Set[int]],
        excluded_pairs: Set[tuple[int, int]] | None = None,
    ) -> tuple[int, int] | None:
        ranked_candidates: List[tuple[int, int, int, int, int, int]] = []
        excluded_pairs = excluded_pairs or set()
        for first_component_index, first_component in enumerate(components):
            for second_component in components[first_component_index + 1 :]:
                for first_index in sorted(first_component):
                    first_plan = chunk_plans[first_index]
                    first_names = set(first_plan.image_names)
                    for second_index in sorted(second_component):
                        pair_key = (min(first_index, second_index), max(first_index, second_index))
                        if pair_key in excluded_pairs:
                            continue
                        second_plan = chunk_plans[second_index]
                        planned_shared_images = len(first_names.intersection(second_plan.image_names))
                        cross_edge_count = (
                            self.cross_chunk_edge_count(first_plan.image_names, second_plan.image_names)
                            + self.cross_chunk_edge_count(second_plan.image_names, first_plan.image_names)
                        )
                        if planned_shared_images <= 0 and cross_edge_count <= 0:
                            continue
                        combined_image_count = len(first_names.union(second_plan.image_names))
                        if combined_image_count > self.chunk_bridge_recovery_max_images:
                            continue
                        ranked_candidates.append(
                            (
                                -planned_shared_images,
                                -cross_edge_count,
                                combined_image_count,
                                abs(first_plan.index - second_plan.index),
                                first_index,
                                second_index,
                            )
                        )
        if not ranked_candidates:
            return None
        _, _, _, _, first_index, second_index = min(ranked_candidates)
        return (first_index, second_index)

    def repair_disconnected_chunk_model_components(
        self,
        *,
        chunk_plans: Sequence[ChunkPlan],
        chunk_models: Sequence[ModelSummary],
    ) -> tuple[List[ChunkPlan], List[ModelSummary]]:
        if self.chunk_planner != "footprint_graph_v1" or len(chunk_models) <= 1:
            return list(chunk_plans), list(chunk_models)

        repaired_chunk_plans = list(chunk_plans)
        repaired_chunk_models = list(chunk_models)
        attempts_remaining = max(self.chunk_bridge_recovery_max_attempts, 0)
        attempted_bridge_pairs: Set[tuple[int, int]] = set()
        while attempts_remaining > 0:
            components, registered_name_sets = self.registered_overlap_components(repaired_chunk_models)
            if len(components) <= 1:
                self.merged_component_count = 1
                return repaired_chunk_plans, repaired_chunk_models
            bridge_pair = self.best_bridge_chunk_pair(
                chunk_plans=repaired_chunk_plans,
                components=components,
                excluded_pairs=attempted_bridge_pairs,
            )
            if bridge_pair is None:
                self.merged_component_count = len(components)
                return repaired_chunk_plans, repaired_chunk_models
            first_index, second_index = bridge_pair
            attempted_bridge_pairs.add((min(first_index, second_index), max(first_index, second_index)))
            first_chunk_plan = repaired_chunk_plans[first_index]
            second_chunk_plan = repaired_chunk_plans[second_index]
            first_component = next(component for component in components if first_index in component)
            second_component = next(component for component in components if second_index in component)
            bridge_target_name_sets = [
                self.component_registered_names(component=first_component, registered_name_sets=registered_name_sets),
                self.component_registered_names(component=second_component, registered_name_sets=registered_name_sets),
            ]
            merged_chunk_plan = self.build_adjacent_merged_chunk_plan(
                first_chunk_plan,
                second_chunk_plan,
                index=min(first_chunk_plan.index, second_chunk_plan.index),
            )
            logger.info(
                "Registered chunk overlap graph has %s components; rerunning bridge chunk %s-%s across %s images",
                len(components),
                first_chunk_plan.index,
                second_chunk_plan.index,
                len(merged_chunk_plan.image_names),
            )
            merged_stage_prefix = (
                f"chunk_{min(first_chunk_plan.index, second_chunk_plan.index):02d}_"
                f"{max(first_chunk_plan.index, second_chunk_plan.index):02d}_merge_bridge"
            )
            self.merge_bridge_recovery_triggered = True
            if self.chunk_recovery_mode == "prior_aware_retry_no_vocab":
                self.chunk_recovery_mode = (
                    "seam_only_bridge_registration"
                    if self.parent_merge_mode == "seam_only_v1"
                    else "prior_aware_retry_merge_bridge_no_vocab"
                )
            self.clear_failure()
            if self.parent_merge_mode == "seam_only_v1":
                seed_models = [repaired_chunk_models[first_index], repaired_chunk_models[second_index]]
                seed_models.sort(key=lambda model: (-model.images_registered, model.stage))
                merged_model = None
                for seed_attempt, seed_model in enumerate(seed_models, start=1):
                    candidate_model = self.run_parent_seam_registration(
                        seed_model=seed_model,
                        chunk_plan=merged_chunk_plan,
                        stage_prefix=merged_stage_prefix,
                        dir_name=f"{merged_stage_prefix}_seed_{seed_attempt:02d}",
                        bridge_target_name_sets=bridge_target_name_sets,
                    )
                    if self.model_connects_target_name_sets(
                        model=candidate_model,
                        target_name_sets=bridge_target_name_sets,
                    ) or self.auxiliary_bridge_model_is_usable(
                        model=candidate_model,
                        target_name_sets=bridge_target_name_sets,
                    ):
                        merged_model = candidate_model
                        break
                if merged_model is None:
                    merged_model = candidate_model
            else:
                merged_model = self.run_chunk_pipeline(
                    merged_chunk_plan,
                    stage_prefix=merged_stage_prefix,
                    dir_name=merged_stage_prefix,
                    allow_partial_result=True,
                    bridge_target_name_sets=bridge_target_name_sets,
                )
            if not self.model_connects_target_name_sets(
                model=merged_model,
                target_name_sets=bridge_target_name_sets,
            ):
                if self.auxiliary_bridge_model_is_usable(
                    model=merged_model,
                    target_name_sets=bridge_target_name_sets,
                ):
                    logger.info(
                        "Bridge chunk %s-%s produced %s registered images with one-sided but unique connector coverage; keeping it as an auxiliary connector",
                        first_chunk_plan.index,
                        second_chunk_plan.index,
                        merged_model.images_registered,
                    )
                    repaired_chunk_plans.append(merged_chunk_plan)
                    repaired_chunk_models.append(merged_model)
                    attempts_remaining -= 1
                    continue
                logger.warning(
                    "Bridge chunk %s-%s produced %s registered images but did not overlap both target components; keeping original chunk models",
                    first_chunk_plan.index,
                    second_chunk_plan.index,
                    merged_model.images_registered,
                )
                attempts_remaining -= 1
                continue
            repaired_chunk_plans.append(merged_chunk_plan)
            repaired_chunk_models.append(merged_model)
            attempts_remaining -= 1
        components, _ = self.registered_overlap_components(repaired_chunk_models)
        self.merged_component_count = len(components)
        return repaired_chunk_plans, repaired_chunk_models

    def run_vocab_only_path(self) -> ModelSummary:
        self.run_vocab_matching()
        self.final_matcher_mode = "vocab_only"
        return self.run_mapper(
            database_path=self.database_path,
            stage="mapper_vocab_only",
            sparse_root=self.work_dir / "sparse_vocab_only",
            image_count=self.dataset_image_count,
        )

    def run_spatial_sequential_plus_vocab_path(self) -> ModelSummary:
        self.run_spatial_matcher()
        if self.enable_sequential_matcher:
            self.run_sequential_matcher()
        self.run_vocab_matching()
        self.final_matcher_mode = (
            "spatial_sequential_plus_vocab"
            if self.enable_sequential_matcher
            else "spatial_plus_vocab"
        )
        return self.run_mapper(
            database_path=self.database_path,
            stage=(
                "mapper_spatial_sequential_plus_vocab"
                if self.enable_sequential_matcher
                else "mapper_spatial_plus_vocab"
            ),
            sparse_root=(
                self.work_dir / "sparse_spatial_sequential_plus_vocab"
                if self.enable_sequential_matcher
                else self.work_dir / "sparse_spatial_plus_vocab"
            ),
            image_count=self.dataset_image_count,
        )

    def run_monolithic_gps_first_path(self) -> ModelSummary:
        self.gps_first_attempted = True
        try:
            self.run_spatial_matcher()
            if self.enable_sequential_matcher:
                self.run_sequential_matcher()
            spatial_model = self.run_mapper(
                database_path=self.database_path,
                stage=(
                    "mapper_spatial_sequential_only"
                    if self.enable_sequential_matcher
                    else "mapper_spatial_only"
                ),
                sparse_root=(
                    self.work_dir / "sparse_spatial_sequential_only"
                    if self.enable_sequential_matcher
                    else self.work_dir / "sparse_spatial_only"
                ),
                image_count=self.dataset_image_count,
            )
        except RuntimeError as exc:
            self.mark_failure(
                stage=(
                    "mapper_spatial_sequential_only"
                    if self.enable_sequential_matcher
                    else "mapper_spatial_only"
                ),
                reason=f"GPS-first mapper failed: {exc}",
            )
            raise RuntimeError(self.failure_reason_detail) from exc

        registered_ratio = (
            spatial_model.images_registered / self.dataset_image_count
            if self.dataset_image_count
            else 0.0
        )
        logger.info(
            "First-pass mapper registered %s/%s extracted images (%.2f%%)",
            spatial_model.images_registered,
            self.dataset_image_count,
            registered_ratio * 100.0,
        )
        if registered_ratio >= self.gps_min_registered_ratio:
            self.final_matcher_mode = (
                "spatial_sequential_only"
                if self.enable_sequential_matcher
                else "spatial_only"
            )
            return spatial_model
        self.mark_failure(
            stage=(
                "mapper_spatial_sequential_plus_vocab"
                if self.enable_sequential_matcher
                else "mapper_spatial_plus_vocab"
            ),
            reason=(
                "GPS-first mapper registered "
                f"{spatial_model.images_registered}/{self.dataset_image_count} images "
                f"({registered_ratio * 100.0:.2f}%), below "
                f"{self.gps_min_registered_ratio * 100.0:.2f}% threshold"
            ),
            registered_ratio=registered_ratio,
        )
        raise RuntimeError(self.failure_reason_detail)

    def run_spatial_heading_chunked_path(self) -> ModelSummary:
        self.chunking_attempted = True
        self.pipeline_name = (
            "colmap_gpu_footprint_graph_chunked"
            if self.chunk_planner == "footprint_graph_v1"
            else "colmap_gpu_spatial_heading_chunked"
        )
        if self.chunk_planner == "footprint_graph_v1":
            self.enable_sequential_matcher = False
        self.chunk_plans = self.build_chunk_plans()
        self.chunk_plans_by_index = {chunk_plan.index: chunk_plan for chunk_plan in self.chunk_plans}
        if self.only_chunk_indexes:
            self.chunk_plans = [
                chunk_plan for chunk_plan in self.chunk_plans if chunk_plan.index in self.only_chunk_indexes
            ]
            if not self.chunk_plans:
                raise RuntimeError(
                    f"Requested COLMAP_ONLY_CHUNK_INDEXES={sorted(self.only_chunk_indexes)} but no chunks matched"
                )
            logger.info(
                "Restricting chunk execution to chunk indexes %s (%s chunks)",
                sorted(self.only_chunk_indexes),
                len(self.chunk_plans),
            )
            self.chunk_execution_image_count = len(
                {image_name for chunk_plan in self.chunk_plans for image_name in chunk_plan.image_names}
            )
        else:
            self.chunk_execution_image_count = self.dataset_image_count
        if len(self.chunk_plans) <= 1:
            self.chunking_skipped_reason = "single_chunk_only" if not self.only_chunk_indexes else "single_chunk_selected"
        chunk_models: List[ModelSummary] = []
        executed_chunk_plans: List[ChunkPlan] = []
        chunk_index = 0
        while chunk_index < len(self.chunk_plans):
            chunk_plan = self.chunk_plans[chunk_index]
            try:
                chunk_model = self.run_chunk_pipeline(chunk_plan)
                chunk_models.append(chunk_model)
                executed_chunk_plans.append(chunk_plan)
                chunk_index += 1
                continue
            except RuntimeError:
                if not (
                    self.enable_chunk_adjacent_merge_retry
                    and self.failure_stage.endswith("_recovery_failed")
                ):
                    raise
                merge_candidates: List[tuple[float, str, ChunkPlan]] = []
                if chunk_index > 0 and chunk_models:
                    previous_chunk_plan = self.chunk_plans[chunk_index - 1]
                    merge_candidates.append(
                        (
                            (
                                -self.cross_chunk_edge_count(previous_chunk_plan.image_names, chunk_plan.image_names)
                                if self.chunk_planner == "footprint_graph_v1"
                                else self.chunk_unit_boundary_score(
                                    previous_chunk_plan.core_group_indices,
                                    chunk_plan.core_group_indices,
                                )
                            ),
                            "previous",
                            previous_chunk_plan,
                        )
                    )
                if chunk_index + 1 < len(self.chunk_plans):
                    next_chunk_plan = self.chunk_plans[chunk_index + 1]
                    merge_candidates.append(
                        (
                            (
                                -self.cross_chunk_edge_count(chunk_plan.image_names, next_chunk_plan.image_names)
                                if self.chunk_planner == "footprint_graph_v1"
                                else self.chunk_unit_boundary_score(
                                    chunk_plan.core_group_indices,
                                    next_chunk_plan.core_group_indices,
                                )
                            ),
                            "next",
                            next_chunk_plan,
                        )
                    )
                if not merge_candidates:
                    raise
                if self.parent_merge_mode == "seam_only_v1" and chunk_models:
                    merge_candidates = [
                        candidate for candidate in merge_candidates if candidate[1] == "previous"
                    ] or merge_candidates
                _, merge_side, neighbor_chunk_plan = min(merge_candidates, key=lambda item: item[0])
                merged_chunk_plan = self.build_adjacent_merged_chunk_plan(
                    neighbor_chunk_plan if merge_side == "previous" else chunk_plan,
                    chunk_plan if merge_side == "previous" else neighbor_chunk_plan,
                    index=chunk_plan.index if merge_side == "previous" else neighbor_chunk_plan.index,
                )
                merged_stage_prefix = (
                    f"chunk_{min(chunk_plan.index, neighbor_chunk_plan.index):02d}_"
                    f"{max(chunk_plan.index, neighbor_chunk_plan.index):02d}_adjacent_merge"
                )
                logger.info(
                    "Chunk %s failed bounded retry; merging with %s chunk %s for one final local rerun across %s images",
                    chunk_plan.index,
                    merge_side,
                    neighbor_chunk_plan.index,
                    len(merged_chunk_plan.image_names),
                )
                self.adjacent_chunk_merge_triggered = True
                self.clear_failure()
                if self.parent_merge_mode == "seam_only_v1" and merge_side == "previous" and chunk_models:
                    self.chunk_recovery_mode = "seam_only_adjacent_registration"
                    seed_model = chunk_models.pop()
                    executed_chunk_plans.pop()
                    merged_model = self.run_parent_seam_registration(
                        seed_model=seed_model,
                        chunk_plan=merged_chunk_plan,
                        stage_prefix=merged_stage_prefix,
                        dir_name=merged_stage_prefix,
                        run_final_bundle_adjustment=False,
                    )
                    merged_model.image_names = list(merged_chunk_plan.image_names)
                    merged_names = self.merged_image_names(merged_model)
                    seed_names = self.merged_image_names(seed_model)
                    if not (
                        (
                            len(merged_names.intersection(seed_names)) / len(seed_names)
                            if seed_names
                            else 1.0
                        )
                        >= 0.95
                        and merged_names.intersection(set(chunk_plan.core_names))
                    ):
                        self.mark_failure(
                            stage=f"{merged_stage_prefix}_seam_registration_failed",
                            reason=(
                                f"seam-only adjacent registration retained "
                                f"{len(merged_names.intersection(seed_names))}/{len(seed_names)} prior images "
                                f"and registered "
                                f"{len(merged_names.intersection(set(chunk_plan.core_names)))}/"
                                f"{len(set(chunk_plan.core_names))} current core images"
                            ),
                            chunk_index=chunk_plan.index,
                        )
                        raise RuntimeError(self.failure_reason_detail)
                else:
                    self.chunk_recovery_mode = "prior_aware_retry_adjacent_merge_no_vocab"
                    if merge_side == "previous":
                        chunk_models.pop()
                        executed_chunk_plans.pop()
                    merged_model = self.run_chunk_pipeline(
                        merged_chunk_plan,
                        stage_prefix=merged_stage_prefix,
                        dir_name=merged_stage_prefix,
                    )
                chunk_models.append(merged_model)
                executed_chunk_plans.append(merged_chunk_plan)
                chunk_index += 1 if merge_side == "previous" else 2
        executed_chunk_plans, chunk_models = self.repair_disconnected_chunk_model_components(
            chunk_plans=executed_chunk_plans,
            chunk_models=chunk_models,
        )
        merged_model = self.merge_chunk_models(chunk_models)
        merged_ratio = (
            merged_model.images_registered / self.chunk_execution_image_count
            if self.chunk_execution_image_count
            else 0.0
        )
        if merged_ratio < self.chunk_registered_ratio_threshold():
            self.mark_failure(
                stage="chunked_merge_threshold",
                reason=(
                    f"Chunked merge registered {merged_model.images_registered}/"
                    f"{self.chunk_execution_image_count} images"
                ),
                chunk_index=self.failed_chunk_index,
                registered_ratio=merged_ratio,
            )
            raise RuntimeError(self.failure_reason_detail)
        self.final_matcher_mode = (
            (
                "footprint_graph_chunked_subset"
                if self.only_chunk_indexes
                else "footprint_graph_chunked"
            )
            if self.chunk_planner == "footprint_graph_v1"
            else (
                "spatial_heading_chunked_subset" if self.only_chunk_indexes else "spatial_heading_chunked"
            )
        )
        return merged_model

    def run_matching_and_mapping(self) -> ModelSummary:
        if self.should_attempt_spatial_chunking():
            return self.run_spatial_heading_chunked_path()

        if not self.should_attempt_gps_first():
            if (
                self.enable_spatial_matcher
                and self.gps_image_count > 0
                and self.gps_prior_coverage >= self.gps_min_prior_coverage
            ):
                return self.run_spatial_sequential_plus_vocab_path()
            return self.run_vocab_only_path()

        return self.run_monolithic_gps_first_path()

    def resolve_mapper_seconds(self) -> float:
        if self.final_matcher_mode in {
            "spatial_heading_chunked",
            "spatial_heading_chunked_subset",
            "footprint_graph_chunked",
            "footprint_graph_chunked_subset",
        }:
            return round(self.chunk_mapper_seconds, 2)
        mapper_timings = [
            value for key, value in self.timings.items() if key.startswith("mapper_") and key.endswith("_seconds")
        ]
        return round(max(mapper_timings), 2) if mapper_timings else 0.0

    def write_filtered_sparse_model(self, *, source_text_dir: Path, output_dir: Path) -> dict[str, object]:
        output_dir.mkdir(parents=True, exist_ok=True)
        points_path = source_text_dir / "points3D.txt"
        points_lines: List[str] = []
        point_scales: List[float] = []
        if points_path.exists():
            with open(points_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    points_lines.append(line)
                    parts = stripped.split()
                    if len(parts) >= 4:
                        point_scales.append(max(abs(float(parts[1])), abs(float(parts[2])), abs(float(parts[3]))))

        outlier_limit = max(
            self.filtered_sparse_absurd_outlier_floor,
            percentile(point_scales, 0.95) * self.filtered_sparse_absurd_outlier_multiplier,
        )
        keep_point_ids: Set[int] = set()
        core_point_count = 0
        far_context_point_count = 0
        absurd_outlier_count = 0
        kept_lines: List[str] = []
        for line in points_lines:
            parts = line.strip().split()
            point_id = int(parts[0])
            max_abs_coordinate = max(abs(float(parts[1])), abs(float(parts[2])), abs(float(parts[3])))
            reprojection_error = float(parts[7]) if len(parts) > 7 else 0.0
            track_len = point_track_length(parts)
            if max_abs_coordinate > outlier_limit:
                absurd_outlier_count += 1
                continue
            if (
                track_len >= self.filtered_sparse_core_min_track_len
                and reprojection_error <= self.filtered_sparse_core_max_reproj_error
            ):
                keep_point_ids.add(point_id)
                core_point_count += 1
                kept_lines.append(line)
                continue
            if (
                track_len == self.filtered_sparse_far_context_track_len
                and reprojection_error <= self.filtered_sparse_far_context_max_reproj_error
            ):
                keep_point_ids.add(point_id)
                far_context_point_count += 1
                kept_lines.append(line)

        for source_file in source_text_dir.iterdir():
            if source_file.name in {"images.txt", "points3D.txt"}:
                continue
            if source_file.is_file():
                shutil.copy2(source_file, output_dir / source_file.name)
        rewrite_images_with_filtered_points(
            source_text_dir / "images.txt",
            output_dir / "images.txt",
            keep_point_ids=keep_point_ids,
        )
        with open(output_dir / "points3D.txt", "w", encoding="utf-8") as target:
            if points_path.exists():
                with open(points_path, "r", encoding="utf-8") as source:
                    for line in source:
                        stripped = line.strip()
                        if not stripped or stripped.startswith("#"):
                            target.write(line)
                for line in kept_lines:
                    target.write(line)
        return {
            "raw_points_3d": len(points_lines),
            "filtered_points_3d": len(keep_point_ids),
            "core_filtered_points_3d": core_point_count,
            "far_context_points_3d": far_context_point_count,
            "absurd_outlier_points_removed": absurd_outlier_count,
            "outlier_limit": round(outlier_limit, 3),
            "core_min_track_len": self.filtered_sparse_core_min_track_len,
            "core_max_reproj_error": self.filtered_sparse_core_max_reproj_error,
            "far_context_track_len": self.filtered_sparse_far_context_track_len,
            "far_context_max_reproj_error": self.filtered_sparse_far_context_max_reproj_error,
        }

    def build_metadata(
        self,
        *,
        best_model: ModelSummary | None,
        quality_check_passed: bool,
    ) -> dict[str, object]:
        mapper_seconds = self.resolve_mapper_seconds()
        final_points_per_registered_image = (
            round(best_model.points_3d / best_model.images_registered, 2)
            if best_model is not None and best_model.images_registered
            else 0.0
        )
        mapper_seconds_per_registered_image = (
            round(mapper_seconds / best_model.images_registered, 2)
            if best_model is not None and best_model.images_registered
            else 0.0
        )
        role_counts = defaultdict(int)
        for role in self.chunk_role_by_image.values():
            role_counts[role] += 1
        return {
            "pipeline": self.pipeline_name,
            "processing_time_seconds": round(time.time() - self.start_time, 2),
            "timings": self.timings,
            "dataset_image_count": self.dataset_image_count,
            "chunk_execution_image_count": self.chunk_execution_image_count or self.dataset_image_count,
            "cameras_registered": best_model.cameras_registered if best_model is not None else 0,
            "images_registered": best_model.images_registered if best_model is not None else 0,
            "points_3d": best_model.points_3d if best_model is not None else 0,
            "quality_check_passed": quality_check_passed,
            "gpu_enabled": self.use_gpu,
            "gps_priors_detected": self.gps_image_count,
            "gps_exif_count": self.gps_image_count,
            "orientation_prior_count": self.orientation_prior_count,
            "heading_prior_source": self.heading_prior_source,
            "heading_prior_dispersion_deg": self.heading_prior_dispersion_deg,
            "pitch_prior_source": self.pitch_prior_source,
            "pitch_prior_dispersion_deg": self.pitch_prior_dispersion_deg,
            "pose_priors_written_count": self.pose_priors_written_count,
            "pose_priors_source": self.pose_priors_source,
            "gps_prior_coverage": self.gps_prior_coverage,
            "matchers_run": self.matchers_run,
            "matcher_pair_deltas": self.matcher_pair_deltas,
            "verified_pairs_total": self.verified_pairs_total,
            "spatial_matcher_enabled": self.enable_spatial_matcher,
            "sequential_matcher_enabled": self.enable_sequential_matcher,
            "sequential_pair_delta": self.matcher_pair_deltas.get("sequential_matcher", 0),
            "match_profile": self.match_profile,
            "gps_first_attempted": self.gps_first_attempted,
            "gps_first_skipped_reason": self.gps_first_skipped_reason,
            "chunking_enabled": self.enable_spatial_chunking,
            "chunking_attempted": self.chunking_attempted,
            "chunking_skipped_reason": self.chunking_skipped_reason,
            "chunk_planner": self.chunk_planner,
            "chunk_matcher_strategy": self.chunk_matcher_strategy,
            "chunk_count": len(self.chunk_plans),
            "chunk_sizes": self.chunk_sizes,
            "chunk_overlap_image_count": self.chunk_overlap_image_count,
            "chunk_group_count": self.chunk_group_count,
            "chunk_segment_count": self.chunk_segment_count,
            "chunk_pair_budget": self.chunk_pair_budget,
            "chunk_role_counts": dict(role_counts),
            "chunk_mapper_seconds": round(self.chunk_mapper_seconds, 2),
            "chunk_merge_seconds": round(self.chunk_merge_seconds, 2),
            "chunk_merge_proof": self.chunk_merge_proof,
            "parent_merge_mode": self.parent_merge_mode,
            "parent_seam_registration_cycles": self.parent_seam_registration_cycles,
            "chunk_recovery_mode": self.chunk_recovery_mode,
            "chunk_run_metrics": self.chunk_run_metrics,
            "boundary_recovery_triggered": self.boundary_recovery_triggered,
            "adjacent_chunk_merge_triggered": self.adjacent_chunk_merge_triggered,
            "merge_bridge_recovery_triggered": self.merge_bridge_recovery_triggered,
            "merged_component_count": self.merged_component_count,
            "filtered_sparse_summary": self.filtered_sparse_summary,
            "final_points_per_registered_image": final_points_per_registered_image,
            "mapper_seconds_per_registered_image": mapper_seconds_per_registered_image,
            "fallback_triggered": self.fallback_triggered,
            "fallback_reason": self.fallback_reason,
            "final_matcher_mode": self.final_matcher_mode,
            "model_summaries": self.model_summaries,
            "vocab_tree_path": str(self.active_vocab_tree_path or self.vocab_tree_path),
            "vocab_tree_bytes": (
                (self.active_vocab_tree_path or self.vocab_tree_path).stat().st_size
                if (self.active_vocab_tree_path or self.vocab_tree_path).exists()
                else 0
            ),
            "vocab_tree_source": self.vocab_tree_source,
            "sift_max_num_features": self.max_features,
            "spatial_matcher_neighbors": self.spatial_neighbors,
            "spatial_matcher_distance_m": self.spatial_distance_m,
            "vocab_tree_num_images": self.vocab_num_images,
            "vocab_tree_num_visual_words": self.vocab_num_visual_words,
            "vocab_tree_max_num_descriptors": self.vocab_max_num_descriptors,
            "benchmark_subset_strategy": self.benchmark_subset_strategy,
            "colmap_capabilities": self.colmap_capabilities,
            "failure_stage": self.failure_stage,
            "failure_reason_detail": self.failure_reason_detail,
            "failed_chunk_index": self.failed_chunk_index,
            "failed_chunk_registered_ratio": self.failed_chunk_registered_ratio,
            "failed_chunk_core_registered_ratio": self.failed_chunk_core_registered_ratio,
            "timed_out": self.timed_out,
            "selected_chunk_indexes": sorted(self.only_chunk_indexes),
            "planner_snapshot_only": self.planner_snapshot_only,
            "capability_snapshot_only": self.capability_snapshot_only,
            "probe_subsets": {
                probe_name: len(image_names)
                for probe_name, image_names in self.probe_subsets.items()
            },
            "probe_subset_details": self.probe_subset_details,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def export_output(self, best_model: ModelSummary) -> None:
        sparse_output = self.output_dir / "sparse" / "0"
        raw_sparse_output = self.output_dir / "sparse_raw" / "0"
        images_output = self.output_dir / "images"

        if sparse_output.exists():
            shutil.rmtree(sparse_output)
        if raw_sparse_output.exists():
            shutil.rmtree(raw_sparse_output)
        if images_output.exists():
            shutil.rmtree(images_output)

        sparse_output.parent.mkdir(parents=True, exist_ok=True)
        raw_sparse_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(best_model.text_dir, raw_sparse_output)
        self.filtered_sparse_summary = self.write_filtered_sparse_model(
            source_text_dir=best_model.text_dir,
            output_dir=sparse_output,
        )
        shutil.copytree(self.images_dir, images_output)
        shutil.copy2(self.database_path, self.output_dir / "database.db")
        quality_check_passed = (
            best_model.points_3d >= 1000
            and best_model.images_registered > 0
            and best_model.cameras_registered > 0
        )
        metadata = self.build_metadata(
            best_model=best_model,
            quality_check_passed=quality_check_passed,
        )
        with open(self.output_dir / "sfm_metadata.json", "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)
        if self.chunk_planner == "footprint_graph_v1":
            self.write_chunk_planner_manifest()

        if not metadata["quality_check_passed"]:
            raise RuntimeError(
                f"Exported sparse model failed quality gate: "
                f"cameras={best_model.cameras_registered}, "
                f"images={best_model.images_registered}, "
                f"points={best_model.points_3d}"
            )


def main(argv: Iterable[str]) -> int:
    args = list(argv)
    if len(args) != 3:
        print("Usage: run_colmap_sfm.py <input_dir> <output_dir>", file=sys.stderr)
        return 1

    input_dir = Path(args[1])
    output_dir = Path(args[2])
    pipeline = ColmapPipeline(input_dir, output_dir)
    log_memory("startup")
    return pipeline.run()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
