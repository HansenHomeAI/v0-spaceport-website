#!/usr/bin/env python3
"""GPU COLMAP SfM pipeline that exports the 3DGS-compatible sparse handoff."""

from __future__ import annotations

import json
import logging
import math
import os
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set


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


@dataclass
class ChunkPlan:
    index: int
    core_names: List[str]
    image_names: List[str]
    overlap_names: List[str]


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


def stream_command(command: List[str], *, stage: str, env: Dict[str, str] | None = None) -> None:
    logger.info("[%s] %s", stage, " ".join(command))
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        bufsize=1,
    )
    assert process.stdout is not None
    lines: List[str] = []
    for line in process.stdout:
        message = line.rstrip()
        lines.append(message)
        print(f"COLMAP[{stage}] {message}", flush=True)
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
        self.chunk_boundary_max_neighbors = int(
            os.environ.get(
                "COLMAP_CHUNK_BOUNDARY_MAX_NEIGHBORS",
                str(max(self.spatial_neighbors + 4, 18)),
            )
        )
        self.chunk_boundary_vocab_num_images = int(
            os.environ.get("COLMAP_CHUNK_BOUNDARY_VOCAB_NUM_IMAGES", "12")
        )
        self.chunk_min_core_registered_ratio = float(
            os.environ.get("COLMAP_CHUNK_MIN_CORE_REGISTERED_RATIO", "0.90")
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
        self.merged_component_count = 0
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> int:
        try:
            self.extract_images()
            self.exif_records = self.load_exif_records()
            self.gps_image_count = len(self.exif_records)
            self.orientation_prior_count = sum(
                1 for record in self.exif_records.values() if record.get("heading_deg") is not None
            )
            self.prepare_capture_ordered_image_list()
            self.run_feature_extraction()
            self.log_pose_prior_schema()
            self.validate_or_backfill_pose_priors()
            best_model = self.run_matching_and_mapping()
            self.export_output(best_model)
            return 0
        except Exception as exc:
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
            "-GPSImgDirection",
            "-GimbalYawDegree",
            "-GimbalPitchDegree",
            "-GimbalRollDegree",
            "-FlightYawDegree",
            "-FlightPitchDegree",
            "-FlightRollDegree",
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
            exif_records[file_name] = {
                "file_name": file_name,
                "gps_latitude": float(record["GPSLatitude"]),
                "gps_longitude": float(record["GPSLongitude"]),
                "gps_altitude": float(record.get("GPSAltitude", 0.0)),
                "capture_time": (
                    record.get("SubSecDateTimeOriginal")
                    or record.get("DateTimeOriginal")
                    or record.get("CreateDate")
                    or ""
                ),
                "heading_deg": normalize_heading(
                    parse_optional_float(record, ["GimbalYawDegree", "GPSImgDirection", "FlightYawDegree"])
                ),
                "gimbal_pitch_deg": parse_optional_float(record, ["GimbalPitchDegree"]),
                "gimbal_roll_deg": parse_optional_float(record, ["GimbalRollDegree"]),
                "flight_yaw_deg": normalize_heading(parse_optional_float(record, ["FlightYawDegree"])),
                "flight_pitch_deg": parse_optional_float(record, ["FlightPitchDegree"]),
                "flight_roll_deg": parse_optional_float(record, ["FlightRollDegree"]),
            }
        self.populate_local_coordinates(exif_records)
        logger.info(
            "Detected GPS EXIF priors on %s images; orientation priors present on %s images",
            len(exif_records),
            sum(1 for record in exif_records.values() if record.get("heading_deg") is not None),
        )
        return exif_records

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
        stream_command(
            [
                "curl",
                "-fL",
                self.vocab_tree_url,
                "-o",
                str(self.vocab_tree_path),
            ],
            stage="download_vocab_tree",
        )
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
                stream_command(command, stage="vocab_tree_builder")
                break
            except RuntimeError as error:
                if "--max_num_images" in command and unrecognized_option_error(error, ["--max_num_images"]):
                    logger.warning(
                        "vocab_tree_builder rejected --max_num_images; retrying with older COLMAP-compatible flags"
                    )
                    last_error = error
                    continue
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

    def run_with_option_family_fallback(
        self,
        *,
        stage: str,
        families: Sequence[str],
        preferred_family: str,
        build_command,
    ) -> str:
        last_error: RuntimeError | None = None
        for family in self.ordered_option_families(preferred_family, families):
            command, option_markers = build_command(family)
            try:
                stream_command(command, stage=stage)
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
        )
        pairs_after = self.count_verified_pairs(active_database_path)
        self.timings[f"{stage}_seconds"] = round(time.time() - started, 2)
        self.record_matcher_delta(label, pairs_after - pairs_before)
        self.verified_pairs_total = max(self.verified_pairs_total, pairs_after)
        logger.info("%s added %s verified image pairs", stage, pairs_after - pairs_before)

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
            stage=f"{stage}_model_converter_{binary_dir.name}",
        )
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
    ) -> ModelSummary:
        active_database_path = database_path or self.database_path
        active_image_count = image_count if image_count is not None else self.dataset_image_count
        started = time.time()
        sparse_root.mkdir(parents=True, exist_ok=True)
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
        )
        self.timings[f"{stage}_seconds"] = round(time.time() - started, 2)

        candidate_dirs = [path for path in sorted(sparse_root.iterdir()) if path.is_dir()]
        if not candidate_dirs:
            raise RuntimeError(f"{stage} did not produce any sparse models")

        best_model: ModelSummary | None = None
        for candidate_dir in candidate_dirs:
            model = self.summarize_model(stage=stage, binary_dir=candidate_dir, image_count=active_image_count)
            logger.info(
                "%s model %s registered %s/%s images and %s points",
                stage,
                candidate_dir.name,
                model.images_registered,
                active_image_count,
                model.points_3d,
            )
            if best_model is None or model_sort_key(model) > model_sort_key(best_model):
                best_model = model
        if best_model is None:
            raise RuntimeError(f"Unable to choose a sparse model for {stage}")
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
            stream_command(command, stage=stage)
        except RuntimeError as exc:
            error_text = str(exc)
            if "unrecognised option '--BundleAdjustment.use_gpu'" not in error_text:
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
            stream_command(fallback_command, stage=stage)
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

    def cluster_score(
        self,
        record: Dict[str, float | str | None],
        center_x: float,
        center_y: float,
        center_heading: float | None,
    ) -> float:
        delta_x = float(record["local_x_m"]) - center_x
        delta_y = float(record["local_y_m"]) - center_y
        distance = math.hypot(delta_x, delta_y)
        heading_factor = 1.0 + (
            self.chunk_heading_weight
            * angular_distance_degrees(record.get("heading_deg"), center_heading)
            / 180.0
        )
        return distance * heading_factor

    def cluster_heading(self, image_names: Sequence[str]) -> float | None:
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

    def dominant_spatial_axis(self, image_names: Sequence[str]) -> tuple[float, float]:
        if len(image_names) <= 1:
            return (1.0, 0.0)
        centroid_x, centroid_y = self.centroid_for_names(image_names)
        xx = 0.0
        xy = 0.0
        yy = 0.0
        for image_name in image_names:
            record = self.exif_records[image_name]
            delta_x = float(record["local_x_m"]) - centroid_x
            delta_y = float(record["local_y_m"]) - centroid_y
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

    def spatial_projection(self, image_name: str, axis_x: float, axis_y: float) -> tuple[float, float, float]:
        record = self.exif_records[image_name]
        x_coord = float(record["local_x_m"])
        y_coord = float(record["local_y_m"])
        along_axis = x_coord * axis_x + y_coord * axis_y
        across_axis = (-axis_y * x_coord) + (axis_x * y_coord)
        heading_deg = record.get("heading_deg")
        return (
            along_axis,
            across_axis,
            normalize_heading(float(heading_deg)) if heading_deg is not None else -1.0,
        )

    def split_projection_clusters(
        self, ordered_names: Sequence[str], cluster_count: int
    ) -> List[List[str]]:
        if cluster_count <= 1:
            return [list(ordered_names)]
        max_cluster_count = max(1, len(ordered_names) // max(self.chunk_min_images, 1))
        effective_cluster_count = max(1, min(cluster_count, max_cluster_count, len(ordered_names)))
        axis_x, axis_y = self.dominant_spatial_axis(ordered_names)
        spatially_sorted_names = sorted(
            ordered_names,
            key=lambda image_name: self.spatial_projection(image_name, axis_x, axis_y),
        )
        base_size = len(spatially_sorted_names) // effective_cluster_count
        remainder = len(spatially_sorted_names) % effective_cluster_count
        clusters: List[List[str]] = []
        start = 0
        for index in range(effective_cluster_count):
            cluster_size = base_size + (1 if index < remainder else 0)
            end = start + cluster_size
            if end > len(spatially_sorted_names):
                break
            clusters.append(spatially_sorted_names[start:end])
            start = end
        if start < len(spatially_sorted_names):
            if clusters:
                clusters[-1].extend(spatially_sorted_names[start:])
            else:
                clusters.append(spatially_sorted_names[start:])
        return [cluster for cluster in clusters if cluster]

    def boundary_candidate_score(
        self, image_name: str, midpoint_x: float, midpoint_y: float, boundary_heading: float
    ) -> float:
        record = self.exif_records[image_name]
        distance = math.hypot(
            float(record["local_x_m"]) - midpoint_x,
            float(record["local_y_m"]) - midpoint_y,
        )
        heading_factor = 1.0 + (
            self.chunk_heading_weight
            * min(
                angular_distance_degrees(record.get("heading_deg"), boundary_heading),
                angular_distance_degrees(record.get("heading_deg"), normalize_heading(boundary_heading + 180.0)),
            )
            / 180.0
        )
        return distance * heading_factor

    def build_spatial_heading_chunks(self) -> List[ChunkPlan]:
        ordered_names = sorted(self.exif_records.keys())
        if not ordered_names:
            return []
        core_chunk_size = max(self.chunk_target_images - self.chunk_overlap_images, self.chunk_min_images)
        spatial_span_x = max(float(record["local_x_m"]) for record in self.exif_records.values()) - min(
            float(record["local_x_m"]) for record in self.exif_records.values()
        )
        spatial_span_y = max(float(record["local_y_m"]) for record in self.exif_records.values()) - min(
            float(record["local_y_m"]) for record in self.exif_records.values()
        )
        max_spatial_span = max(spatial_span_x, spatial_span_y)
        cluster_count = max(
            1,
            math.ceil(len(ordered_names) / core_chunk_size),
            math.ceil(max_spatial_span / max(self.chunk_max_radius_m, 1.0)),
        )
        core_clusters = self.split_projection_clusters(ordered_names, cluster_count)
        if len(core_clusters) <= 1:
            self.chunk_overlap_image_count = 0
            self.chunk_sizes = [len(core_clusters[0])] if core_clusters else []
            return [
                ChunkPlan(index=0, core_names=core_clusters[0], image_names=core_clusters[0], overlap_names=[])
            ] if core_clusters else []

        use_x_axis = spatial_span_x >= spatial_span_y
        core_clusters.sort(
            key=lambda image_names: self.centroid_for_names(image_names)[0 if use_x_axis else 1]
        )

        final_chunk_sets = [set(image_names) for image_names in core_clusters]
        overlap_totals = [set() for _ in core_clusters]
        total_overlap_assignments = 0
        for index in range(len(core_clusters) - 1):
            current_centroid = self.centroid_for_names(core_clusters[index])
            next_centroid = self.centroid_for_names(core_clusters[index + 1])
            midpoint_x = (current_centroid[0] + next_centroid[0]) / 2.0
            midpoint_y = (current_centroid[1] + next_centroid[1]) / 2.0
            boundary_heading = normalize_heading(
                math.degrees(math.atan2(next_centroid[1] - current_centroid[1], next_centroid[0] - current_centroid[0]))
            ) or 0.0
            candidate_names = sorted(
                set(core_clusters[index]).union(core_clusters[index + 1]),
                key=lambda image_name: self.boundary_candidate_score(
                    image_name,
                    midpoint_x,
                    midpoint_y,
                    boundary_heading,
                ),
            )
            shared_names = candidate_names[: min(self.chunk_overlap_images, len(candidate_names))]
            final_chunk_sets[index].update(shared_names)
            final_chunk_sets[index + 1].update(shared_names)
            overlap_totals[index].update(shared_names)
            overlap_totals[index + 1].update(shared_names)
            total_overlap_assignments += len(shared_names)

        capture_order_index = {
            image_name: position for position, image_name in enumerate(self.capture_ordered_names)
        }
        chunk_plans = [
            ChunkPlan(
                index=index,
                core_names=sorted(
                    core_clusters[index],
                    key=lambda image_name: capture_order_index.get(image_name, sys.maxsize),
                ),
                image_names=sorted(
                    final_chunk_sets[index],
                    key=lambda image_name: capture_order_index.get(image_name, sys.maxsize),
                ),
                overlap_names=sorted(
                    overlap_totals[index],
                    key=lambda image_name: capture_order_index.get(image_name, sys.maxsize),
                ),
            )
            for index in range(len(core_clusters))
        ]
        self.chunk_overlap_image_count = total_overlap_assignments
        self.chunk_sizes = [len(chunk_plan.image_names) for chunk_plan in chunk_plans]
        return chunk_plans

    def write_chunk_image_list(self, chunk_plan: ChunkPlan) -> Path:
        chunk_dir = self.work_dir / f"chunk_{chunk_plan.index:02d}"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        image_list_path = chunk_dir / "image_list.txt"
        with open(image_list_path, "w", encoding="utf-8") as handle:
            for image_name in chunk_plan.image_names:
                handle.write(f"{image_name}\n")
        return image_list_path

    def prepare_chunk_database(self, chunk_plan: ChunkPlan) -> Path:
        chunk_dir = self.work_dir / f"chunk_{chunk_plan.index:02d}"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        chunk_database_path = chunk_dir / "database.db"
        shutil.copy2(self.database_path, chunk_database_path)

        keep_image_names = set(chunk_plan.image_names)
        with sqlite3.connect(chunk_database_path) as connection:
            rows = connection.execute("SELECT image_id, name, camera_id FROM images").fetchall()
            remove_image_ids = [int(image_id) for image_id, name, _ in rows if str(name) not in keep_image_names]
            if remove_image_ids:
                placeholders = ",".join("?" for _ in remove_image_ids)
                connection.execute(f"DELETE FROM keypoints WHERE image_id IN ({placeholders})", remove_image_ids)
                connection.execute(f"DELETE FROM descriptors WHERE image_id IN ({placeholders})", remove_image_ids)
                if self.supports_pose_prior_image_backfill(database_path=chunk_database_path):
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

    def run_chunk_pipeline(self, chunk_plan: ChunkPlan) -> ModelSummary:
        chunk_dir = self.work_dir / f"chunk_{chunk_plan.index:02d}"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        chunk_database_path = self.prepare_chunk_database(chunk_plan)
        chunk_image_list_path = self.write_chunk_image_list(chunk_plan)
        chunk_stage_prefix = f"chunk_{chunk_plan.index:02d}"
        self.run_spatial_matcher(
            database_path=chunk_database_path,
            stage=f"{chunk_stage_prefix}_spatial_matcher",
            label="chunk_spatial_matcher",
        )
        if self.enable_sequential_matcher:
            self.run_sequential_matcher(
                database_path=chunk_database_path,
                stage=f"{chunk_stage_prefix}_sequential_matcher",
                label="chunk_sequential_matcher",
            )
        initial_model = self.run_mapper(
            database_path=chunk_database_path,
            stage=f"{chunk_stage_prefix}_mapper_initial",
            sparse_root=chunk_dir / "sparse_initial",
            image_count=len(chunk_plan.image_names),
        )
        self.chunk_mapper_seconds += self.timings[f"{chunk_stage_prefix}_mapper_initial_seconds"]
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
        try:
            self.run_spatial_matcher(
                database_path=chunk_database_path,
                stage=f"{chunk_stage_prefix}_spatial_matcher_recovery",
                label="chunk_spatial_matcher",
                max_neighbors=self.chunk_boundary_max_neighbors,
                max_distance_m=max(self.spatial_distance_m * 1.5, self.chunk_max_radius_m),
            )
            self.run_vocab_matching(
                database_path=chunk_database_path,
                stage=f"{chunk_stage_prefix}_vocab_tree_matcher_recovery",
                label="chunk_vocab_tree_matcher",
                num_images=self.chunk_boundary_vocab_num_images,
            )
            recovered_model = self.run_mapper(
                database_path=chunk_database_path,
                stage=f"{chunk_stage_prefix}_mapper_recovery",
                sparse_root=chunk_dir / "sparse_recovery",
                image_count=len(chunk_plan.image_names),
            )
        except RuntimeError as exc:
            logger.warning(
                "Chunk %s boundary recovery failed; keeping initial chunk model instead: %s",
                chunk_plan.index,
                exc,
            )
            return initial_model
        self.chunk_mapper_seconds += self.timings[f"{chunk_stage_prefix}_mapper_recovery_seconds"]
        return recovered_model if model_sort_key(recovered_model) >= model_sort_key(initial_model) else initial_model

    def merge_chunk_models(self, chunk_models: Sequence[ModelSummary]) -> ModelSummary:
        if not chunk_models:
            raise RuntimeError("No chunk models available to merge")
        if len(chunk_models) == 1:
            self.merged_component_count = 1
            return chunk_models[0]

        merge_started = time.time()
        merged_path = chunk_models[0].binary_dir
        merged_components = 1
        for index, next_model in enumerate(chunk_models[1:], start=1):
            output_path = self.work_dir / f"merged_chunk_model_{index:02d}"
            output_path.mkdir(parents=True, exist_ok=True)
            try:
                stream_command(
                    [
                        "colmap",
                        "model_merger",
                        "--input_path1",
                        str(merged_path),
                        "--input_path2",
                        str(next_model.binary_dir),
                        "--output_path",
                        str(output_path),
                        "--max_reproj_error",
                        "64",
                    ],
                    stage=f"chunk_model_merger_{index:02d}",
                )
            except RuntimeError as exc:
                merged_components += 1
                self.merged_component_count = merged_components
                raise RuntimeError(f"Failed to merge chunk model {index}: {exc}") from exc
            merged_path = output_path
        self.chunk_merge_seconds = round(time.time() - merge_started, 2)
        self.timings["chunk_model_merge_seconds"] = self.chunk_merge_seconds
        self.merged_component_count = 1
        self.pipeline_name = "colmap_gpu_spatial_heading_chunked"
        return self.run_bundle_adjuster(input_path=merged_path, stage="chunk_bundle_adjuster")

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
        spatial_model: ModelSummary | None = None
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
            self.fallback_triggered = True
            self.fallback_reason = "mapper_failed"
            logger.warning("GPS-first first-pass mapper failed, falling back to vocab tree: %s", exc)

        if spatial_model is not None:
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
            self.fallback_triggered = True
            self.fallback_reason = "below_registered_ratio_threshold"
            logger.info(
                "First-pass mapper registered %s/%s images (%.2f%%), below %.2f%% threshold; adding vocab-tree recovery",
                spatial_model.images_registered,
                self.dataset_image_count,
                registered_ratio * 100.0,
                self.gps_min_registered_ratio * 100.0,
            )

        self.run_vocab_matching()
        fallback_model = self.run_mapper(
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
        if spatial_model is not None and model_sort_key(spatial_model) > model_sort_key(fallback_model):
            self.final_matcher_mode = (
                "spatial_sequential_only_better_than_fallback"
                if self.enable_sequential_matcher
                else "spatial_only_better_than_fallback"
            )
            return spatial_model
        self.final_matcher_mode = (
            "spatial_sequential_plus_vocab"
            if self.enable_sequential_matcher
            else "spatial_plus_vocab"
        )
        return fallback_model

    def run_spatial_heading_chunked_path(self) -> ModelSummary:
        self.chunking_attempted = True
        self.chunk_plans = self.build_spatial_heading_chunks()
        if len(self.chunk_plans) <= 1:
            self.chunking_skipped_reason = "single_chunk_only"
            raise RuntimeError("Spatial-heading chunking produced only one chunk")
        chunk_models: List[ModelSummary] = []
        for chunk_plan in self.chunk_plans:
            chunk_model = self.run_chunk_pipeline(chunk_plan)
            chunk_models.append(chunk_model)
        merged_model = self.merge_chunk_models(chunk_models)
        merged_ratio = (
            merged_model.images_registered / self.dataset_image_count
            if self.dataset_image_count
            else 0.0
        )
        if merged_ratio < self.chunk_registered_ratio_threshold():
            raise RuntimeError(
                f"Chunked merge registered {merged_model.images_registered}/{self.dataset_image_count} images"
            )
        self.final_matcher_mode = "spatial_heading_chunked"
        return merged_model

    def run_matching_and_mapping(self) -> ModelSummary:
        if self.should_attempt_spatial_chunking():
            try:
                return self.run_spatial_heading_chunked_path()
            except RuntimeError as exc:
                self.fallback_triggered = True
                self.fallback_reason = "chunked_path_failed"
                logger.warning("Spatial-heading chunked path failed; falling back to monolithic GPS-first flow: %s", exc)
                self.final_matcher_mode = "chunked_fallback_to_monolithic"

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
        if self.final_matcher_mode == "spatial_heading_chunked":
            return round(self.chunk_mapper_seconds, 2)
        mapper_timings = [
            value for key, value in self.timings.items() if key.startswith("mapper_") and key.endswith("_seconds")
        ]
        return round(max(mapper_timings), 2) if mapper_timings else 0.0

    def export_output(self, best_model: ModelSummary) -> None:
        sparse_output = self.output_dir / "sparse" / "0"
        images_output = self.output_dir / "images"

        if sparse_output.exists():
            shutil.rmtree(sparse_output)
        if images_output.exists():
            shutil.rmtree(images_output)

        sparse_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(best_model.text_dir, sparse_output)
        shutil.copytree(self.images_dir, images_output)
        shutil.copy2(self.database_path, self.output_dir / "database.db")

        mapper_seconds = self.resolve_mapper_seconds()
        final_points_per_registered_image = round(
            best_model.points_3d / best_model.images_registered,
            2,
        ) if best_model.images_registered else 0.0
        mapper_seconds_per_registered_image = round(
            mapper_seconds / best_model.images_registered,
            2,
        ) if best_model.images_registered else 0.0
        metadata = {
            "pipeline": self.pipeline_name,
            "processing_time_seconds": round(time.time() - self.start_time, 2),
            "timings": self.timings,
            "dataset_image_count": self.dataset_image_count,
            "cameras_registered": best_model.cameras_registered,
            "images_registered": best_model.images_registered,
            "points_3d": best_model.points_3d,
            "quality_check_passed": (
                best_model.points_3d >= 1000
                and best_model.images_registered > 0
                and best_model.cameras_registered > 0
            ),
            "gpu_enabled": self.use_gpu,
            "gps_priors_detected": self.gps_image_count,
            "gps_exif_count": self.gps_image_count,
            "orientation_prior_count": self.orientation_prior_count,
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
            "chunk_count": len(self.chunk_plans),
            "chunk_sizes": self.chunk_sizes,
            "chunk_overlap_image_count": self.chunk_overlap_image_count,
            "chunk_mapper_seconds": round(self.chunk_mapper_seconds, 2),
            "chunk_merge_seconds": round(self.chunk_merge_seconds, 2),
            "boundary_recovery_triggered": self.boundary_recovery_triggered,
            "merged_component_count": self.merged_component_count,
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
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with open(self.output_dir / "sfm_metadata.json", "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)

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
