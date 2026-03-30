#!/usr/bin/env python3
"""GPU COLMAP SfM pipeline that exports the 3DGS-compatible sparse handoff."""

from __future__ import annotations

import json
import logging
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
from typing import Dict, Iterable, List


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

WGS84_COORDINATE_SYSTEM = 0
INF_COVARIANCE_BLOB = struct.pack("<9d", *([float("inf")] * 9))


@dataclass
class ModelSummary:
    stage: str
    text_dir: Path
    cameras_registered: int
    images_registered: int
    points_3d: int


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


def pack_float64_blob(values: Iterable[float]) -> bytes:
    packed_values = [float(value) for value in values]
    return struct.pack(f"<{len(packed_values)}d", *packed_values)


def model_sort_key(model: ModelSummary) -> tuple[int, int, int]:
    return (model.images_registered, model.points_3d, model.cameras_registered)


class ColmapPipeline:
    def __init__(self, input_dir: Path, output_dir: Path) -> None:
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.work_dir = Path(tempfile.mkdtemp(prefix="colmap_sfm_"))
        self.images_dir = self.work_dir / "images"
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
        self.enable_spatial_matcher = os.environ.get("COLMAP_ENABLE_SPATIAL_MATCHER", "1") != "0"
        self.force_gps_first = os.environ.get("COLMAP_FORCE_GPS_FIRST", "1") != "0"
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
        self.spatial_neighbors = int(os.environ.get("COLMAP_SPATIAL_MAX_NEIGHBORS", "12"))
        self.spatial_distance_m = float(os.environ.get("COLMAP_SPATIAL_MAX_DISTANCE_METERS", "120"))
        self.gps_min_prior_coverage = float(os.environ.get("COLMAP_GPS_MIN_PRIOR_COVERAGE", "0.95"))
        self.gps_min_registered_ratio = float(
            os.environ.get("COLMAP_GPS_MIN_REGISTERED_RATIO", "0.98")
        )
        self.mapper_threads = os.environ.get("COLMAP_MAPPER_THREADS", "-1")
        self.start_time = time.time()
        self.timings: Dict[str, float] = {}
        self.gps_image_count = 0
        self.pose_priors_written_count = 0
        self.gps_prior_coverage = 0.0
        self.pose_priors_source = "none"
        self.exif_records: Dict[str, Dict[str, float | str]] = {}
        self.matchers_run: List[str] = []
        self.matcher_pair_deltas: Dict[str, int] = {}
        self.verified_pairs_total = 0
        self.vocab_tree_source = "uninitialized"
        self.fallback_triggered = False
        self.final_matcher_mode = "uninitialized"
        self.gps_first_attempted = False
        self.gps_first_skipped_reason = "uninitialized"
        self.model_summaries: List[Dict[str, int | str]] = []
        self.benchmark_subset_strategy = os.environ.get("SFM_BENCHMARK_SUBSET_STRATEGY", "")
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> int:
        try:
            self.extract_images()
            self.exif_records = self.load_exif_records()
            self.gps_image_count = len(self.exif_records)
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
        self.timings["extract_images_seconds"] = round(time.time() - started, 2)
        logger.info("Extracted %s images", image_count)

    def load_exif_records(self) -> Dict[str, Dict[str, float | str]]:
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
            str(self.images_dir),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        records = json.loads(result.stdout or "[]")
        exif_records: Dict[str, Dict[str, float | str]] = {}
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
            }
        logger.info("Detected GPS EXIF priors on %s images", len(exif_records))
        return exif_records

    def count_verified_pairs(self) -> int:
        if not self.database_path.exists():
            return 0
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute("SELECT COUNT(*) FROM two_view_geometries").fetchone()
        return int(row[0] if row else 0)

    def count_pose_priors(self) -> int:
        if not self.database_path.exists():
            return 0
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute("SELECT COUNT(*) FROM pose_priors").fetchone()
        return int(row[0] if row else 0)

    def get_image_ids_by_name(self) -> Dict[str, int]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute("SELECT image_id, name FROM images").fetchall()
        return {str(name): int(image_id) for image_id, name in rows}

    def get_table_columns(self, table_name: str) -> set[str]:
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row[1]) for row in rows}

    def pose_priors_columns(self) -> set[str]:
        return self.get_table_columns("pose_priors")

    def supports_pose_prior_image_backfill(self) -> bool:
        return "image_id" in self.pose_priors_columns()

    def pose_prior_schema_variant(self) -> str:
        columns = self.pose_priors_columns()
        if "image_id" in columns:
            return "image_id"
        if "pose_prior_id" in columns:
            return "pose_prior_id"
        return "unknown"

    def log_pose_prior_schema(self) -> None:
        logger.info(
            "COLMAP pose_priors schema variant=%s columns=%s",
            self.pose_prior_schema_variant(),
            sorted(self.pose_priors_columns()),
        )

    def get_pose_prior_image_names(self) -> set[str]:
        columns = self.pose_priors_columns()
        if "image_id" not in columns:
            logger.warning("COLMAP pose_priors table is missing image_id; columns=%s", sorted(columns))
            return set()
        with sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT images.name
                FROM images
                INNER JOIN pose_priors USING(image_id)
                """
            ).fetchall()
        return {str(row[0]) for row in rows}

    def backfill_pose_priors_from_exif(self) -> int:
        if not self.exif_records:
            return 0
        if not self.supports_pose_prior_image_backfill():
            logger.info("Skipping manual pose prior backfill for schema columns=%s", sorted(self.pose_priors_columns()))
            return 0
        image_ids_by_name = self.get_image_ids_by_name()
        existing_names = self.get_pose_prior_image_names()
        rows_to_insert: List[tuple[int, sqlite3.Binary, int, sqlite3.Binary]] = []
        for file_name, record in self.exif_records.items():
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
        with sqlite3.connect(self.database_path) as connection:
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

    def validate_or_backfill_pose_priors(self) -> None:
        if self.gps_image_count == 0:
            self.pose_priors_source = "no_gps_exif"
            self.pose_priors_written_count = 0
            self.gps_prior_coverage = 0.0
            return

        before_backfill = self.count_pose_priors()
        if before_backfill == 0 and self.supports_pose_prior_image_backfill():
            backfilled_count = self.backfill_pose_priors_from_exif()
            after_backfill = self.count_pose_priors()
        else:
            backfilled_count = 0
            after_backfill = before_backfill

        self.pose_priors_written_count = after_backfill
        self.gps_prior_coverage = round(after_backfill / self.gps_image_count, 4)
        if backfilled_count > 0 and before_backfill > 0:
            self.pose_priors_source = "feature_extractor_plus_backfill"
        elif backfilled_count > 0:
            self.pose_priors_source = "backfilled_from_exif"
        elif before_backfill > 0:
            self.pose_priors_source = "feature_extractor"
        elif after_backfill == 0 and not self.supports_pose_prior_image_backfill():
            self.pose_priors_source = "unsupported_pose_prior_schema"
        else:
            self.pose_priors_source = "missing"

        logger.info(
            "COLMAP pose priors available for %s/%s GPS-tagged images (coverage %.2f%%, source=%s)",
            self.pose_priors_written_count,
            self.gps_image_count,
            self.gps_prior_coverage * 100.0,
            self.pose_priors_source,
        )

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

    def build_vocab_tree(self) -> None:
        started = time.time()
        logger.info(
            "Building a FAISS-compatible vocab tree with %s visual words from up to %s descriptors",
            self.vocab_num_visual_words,
            self.vocab_max_num_descriptors,
        )
        stream_command(
            [
                "colmap",
                "vocab_tree_builder",
                "--database_path",
                str(self.database_path),
                "--vocab_tree_path",
                str(self.generated_vocab_tree_path),
                "--num_visual_words",
                str(self.vocab_num_visual_words),
                "--max_num_descriptors",
                str(self.vocab_max_num_descriptors),
                "--num_threads",
                str(self.vocab_build_threads),
            ],
            stage="vocab_tree_builder",
        )
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

    def run_vocab_tree_matcher(self) -> None:
        self.ensure_vocab_tree()
        command = [
            "colmap",
            "vocab_tree_matcher",
            "--database_path",
            str(self.database_path),
            "--FeatureMatching.use_gpu",
            "1" if self.use_gpu else "0",
            "--FeatureMatching.guided_matching",
            "1",
            "--VocabTreeMatching.num_images",
            str(self.vocab_num_images),
        ]
        if self.active_vocab_tree_path is not None:
            command.extend(
                [
                    "--VocabTreeMatching.vocab_tree_path",
                    str(self.active_vocab_tree_path),
                ]
            )
        stream_command(command, stage="vocab_tree_matcher")

    def run_feature_extraction(self) -> None:
        started = time.time()
        command = [
            "colmap",
            "feature_extractor",
            "--database_path",
            str(self.database_path),
            "--image_path",
            str(self.images_dir),
            "--ImageReader.single_camera",
            "1",
            "--ImageReader.camera_model",
            "SIMPLE_RADIAL",
            "--FeatureExtraction.use_gpu",
            "1" if self.use_gpu else "0",
            "--SiftExtraction.max_num_features",
            str(self.max_features),
        ]
        max_image_size = os.environ.get("COLMAP_FEATURE_MAX_IMAGE_SIZE")
        if max_image_size:
            command.extend(["--FeatureExtraction.max_image_size", max_image_size])
        stream_command(command, stage="feature_extractor")
        self.timings["feature_extraction_seconds"] = round(time.time() - started, 2)

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

    def run_spatial_matcher(self) -> None:
        started = time.time()
        pairs_before = self.count_verified_pairs()
        stream_command(
            [
                "colmap",
                "spatial_matcher",
                "--database_path",
                str(self.database_path),
                "--FeatureMatching.use_gpu",
                "1" if self.use_gpu else "0",
                "--FeatureMatching.guided_matching",
                "1",
                "--SpatialMatching.ignore_z",
                "0",
                "--SpatialMatching.max_num_neighbors",
                str(self.spatial_neighbors),
                "--SpatialMatching.max_distance",
                str(self.spatial_distance_m),
            ],
            stage="spatial_matcher",
        )
        pairs_after = self.count_verified_pairs()
        self.timings["spatial_matching_seconds"] = round(time.time() - started, 2)
        self.matcher_pair_deltas["spatial_matcher"] = pairs_after - pairs_before
        self.matchers_run.append("spatial_matcher")
        self.verified_pairs_total = pairs_after
        logger.info(
            "Spatial matcher added %s verified image pairs",
            self.matcher_pair_deltas["spatial_matcher"],
        )

    def run_vocab_matching(self) -> None:
        started = time.time()
        pairs_before = self.count_verified_pairs()
        try:
            self.run_vocab_tree_matcher()
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
            self.build_vocab_tree()
            self.run_vocab_tree_matcher()
        pairs_after = self.count_verified_pairs()
        self.timings["vocab_tree_matching_seconds"] = round(time.time() - started, 2)
        self.matcher_pair_deltas["vocab_tree_matcher"] = pairs_after - pairs_before
        self.matchers_run.append("vocab_tree_matcher")
        self.verified_pairs_total = pairs_after
        logger.info(
            "Vocab tree matcher added %s verified image pairs",
            self.matcher_pair_deltas["vocab_tree_matcher"],
        )

    def run_mapper(self, *, stage: str, sparse_root: Path) -> ModelSummary:
        started = time.time()
        sparse_root.mkdir(parents=True, exist_ok=True)
        stream_command(
            [
                "colmap",
                "mapper",
                "--database_path",
                str(self.database_path),
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
            text_dir = self.work_dir / "text_models" / stage / candidate_dir.name
            text_dir.mkdir(parents=True, exist_ok=True)
            stream_command(
                [
                    "colmap",
                    "model_converter",
                    "--input_path",
                    str(candidate_dir),
                    "--output_path",
                    str(text_dir),
                    "--output_type",
                    "TXT",
                ],
                stage=f"{stage}_model_converter_{candidate_dir.name}",
            )
            model = ModelSummary(
                stage=stage,
                text_dir=text_dir,
                cameras_registered=count_text_rows(text_dir / "cameras.txt"),
                images_registered=count_registered_images(text_dir / "images.txt"),
                points_3d=count_text_rows(text_dir / "points3D.txt"),
            )
            logger.info(
                "%s model %s registered %s images and %s points",
                stage,
                candidate_dir.name,
                model.images_registered,
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

    def run_vocab_only_path(self) -> ModelSummary:
        self.run_vocab_matching()
        self.final_matcher_mode = "vocab_only"
        return self.run_mapper(stage="mapper_vocab_only", sparse_root=self.work_dir / "sparse_vocab_only")

    def run_spatial_plus_vocab_path(self) -> ModelSummary:
        self.run_spatial_matcher()
        self.run_vocab_matching()
        self.final_matcher_mode = "spatial_plus_vocab"
        return self.run_mapper(
            stage="mapper_spatial_plus_vocab",
            sparse_root=self.work_dir / "sparse_spatial_plus_vocab",
        )

    def run_matching_and_mapping(self) -> ModelSummary:
        if not self.should_attempt_gps_first():
            if (
                self.enable_spatial_matcher
                and self.gps_image_count > 0
                and self.gps_prior_coverage >= self.gps_min_prior_coverage
            ):
                return self.run_spatial_plus_vocab_path()
            return self.run_vocab_only_path()

        self.gps_first_attempted = True
        spatial_model: ModelSummary | None = None
        try:
            self.run_spatial_matcher()
            spatial_model = self.run_mapper(
                stage="mapper_spatial_only",
                sparse_root=self.work_dir / "sparse_spatial_only",
            )
        except RuntimeError as exc:
            self.fallback_triggered = True
            logger.warning("GPS-first spatial-only pass failed, falling back to vocab tree: %s", exc)

        if spatial_model is not None:
            registered_ratio = spatial_model.images_registered / max(1, len(list(self.images_dir.iterdir())))
            logger.info(
                "Spatial-only mapper registered %.2f%% of extracted images",
                registered_ratio * 100.0,
            )
            if registered_ratio >= self.gps_min_registered_ratio:
                self.final_matcher_mode = "spatial_only"
                return spatial_model
            self.fallback_triggered = True
            logger.info(
                "Spatial-only registration ratio %.4f is below threshold %.4f; adding vocab-tree matches",
                registered_ratio,
                self.gps_min_registered_ratio,
            )

        self.run_vocab_matching()
        fallback_model = self.run_mapper(
            stage="mapper_spatial_plus_vocab",
            sparse_root=self.work_dir / "sparse_spatial_plus_vocab",
        )
        if spatial_model is not None and model_sort_key(spatial_model) > model_sort_key(fallback_model):
            self.final_matcher_mode = "spatial_only_better_than_fallback"
            return spatial_model
        self.final_matcher_mode = "spatial_plus_vocab"
        return fallback_model

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

        metadata = {
            "pipeline": "colmap_gpu_adaptive_matching",
            "processing_time_seconds": round(time.time() - self.start_time, 2),
            "timings": self.timings,
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
            "pose_priors_written_count": self.pose_priors_written_count,
            "pose_priors_source": self.pose_priors_source,
            "gps_prior_coverage": self.gps_prior_coverage,
            "matchers_run": self.matchers_run,
            "matcher_pair_deltas": self.matcher_pair_deltas,
            "verified_pairs_total": self.verified_pairs_total,
            "spatial_matcher_enabled": self.enable_spatial_matcher,
            "gps_first_attempted": self.gps_first_attempted,
            "gps_first_skipped_reason": self.gps_first_skipped_reason,
            "fallback_triggered": self.fallback_triggered,
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
