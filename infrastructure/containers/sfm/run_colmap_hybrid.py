#!/usr/bin/env python3
"""COLMAP-based segmented SfM pipeline for large DJI landscape datasets."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Callable, Dict, List, Optional

from colmap_runner import ColmapRunner, SegmentRunResult
from cost_estimator import estimate_processing_cost, project_large_landscape_cost
from exif_manifest import ExifManifestBuilder, ImageRecord
from model_analyzer import analyze_sparse_text_model, quality_check_passed
from model_merge import MergeResult, ModelMerger
from segmenter import Segment, build_segments, segments_to_manifest
from sfm_scaling import normalize_profile_override, select_sfm_runtime_plan


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def log_memory_usage(stage: str) -> Dict[str, Optional[float]]:
    """Log current process and system memory usage in MB."""
    rss_mb = None
    mem_total_mb = None
    mem_avail_mb = None

    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss_mb = usage.ru_maxrss / 1024.0
    except Exception:
        pass

    try:
        meminfo = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            for line in handle:
                parts = line.split()
                if len(parts) >= 2:
                    meminfo[parts[0].rstrip(":")] = float(parts[1])
        if "MemTotal" in meminfo:
            mem_total_mb = meminfo["MemTotal"] / 1024.0
        if "MemAvailable" in meminfo:
            mem_avail_mb = meminfo["MemAvailable"] / 1024.0
    except Exception:
        pass

    pieces = []
    if rss_mb is not None:
        pieces.append(f"rss={rss_mb:.1f}MB")
    if mem_total_mb is not None:
        pieces.append(f"total={mem_total_mb:.0f}MB")
    if mem_avail_mb is not None:
        pieces.append(f"avail={mem_avail_mb:.0f}MB")
    if pieces:
        message = " | ".join(pieces)
        print(f"MEMORY_PROBE [{stage}]: {message}", flush=True)
        logger.info("🧠 Memory (%s): %s", stage, message)

    return {
        "rss_mb": rss_mb,
        "mem_total_mb": mem_total_mb,
        "mem_avail_mb": mem_avail_mb,
    }


class ColmapHybridPipeline:
    """Main COLMAP SfM orchestration pipeline."""

    def __init__(self, input_dir: Path, output_dir: Path, gps_csv_path: Path = None):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.gps_csv_path = Path(gps_csv_path) if gps_csv_path else None
        self.work_dir: Optional[Path] = None
        self.images_dir: Optional[Path] = None
        self.extracted_image_count = 0
        self.exif_records: List[ImageRecord] = []
        self.exif_diagnostics: Dict[str, object] = {}
        self.segments: List[Segment] = []
        self.segment_results: List[SegmentRunResult] = []
        self.runtime_plan: Dict[str, object] = {}
        self.merge_result: Optional[MergeResult] = None
        self.stage_metrics: Dict[str, Dict[str, object]] = {}
        self.peak_memory_mb = 0.0
        self.sfm_only = os.environ.get("SPACEPORT_SFM_ONLY", "").strip().lower() == "true"
        self.profile_override = normalize_profile_override(
            os.environ.get("SPACEPORT_SFM_PROFILE_OVERRIDE")
        )
        self.sfm_instance_type = os.environ.get("SPACEPORT_SFM_INSTANCE_TYPE", "").strip() or "unknown"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _sample_memory(self, stage: str, *, stage_key: Optional[str] = None) -> None:
        sample = log_memory_usage(stage)
        peak_candidate = sample.get("rss_mb") or 0.0
        self.peak_memory_mb = max(self.peak_memory_mb, float(peak_candidate))
        if stage_key:
            metrics = self.stage_metrics.setdefault(stage_key, {})
            metrics["peak_memory_mb"] = max(float(metrics.get("peak_memory_mb") or 0.0), float(peak_candidate))

    def _run_timed(self, stage_key: str, description: str, callback: Callable[[], object]) -> object:
        logger.info("🔧 %s", description)
        self._sample_memory(f"before_{stage_key}", stage_key=stage_key)
        started = time.time()
        result = callback()
        duration_seconds = round(time.time() - started, 2)
        self.stage_metrics.setdefault(stage_key, {})["duration_seconds"] = duration_seconds
        self.stage_metrics[stage_key]["description"] = description
        self._sample_memory(f"after_{stage_key}", stage_key=stage_key)
        return result

    def setup_workspace(self) -> Path:
        self.work_dir = Path(tempfile.mkdtemp(prefix="colmap_hybrid_"))
        self.images_dir = self.work_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        logger.info("🏗️ Created workspace: %s", self.work_dir)
        return self.work_dir

    def extract_images(self) -> int:
        if self.images_dir is None:
            raise RuntimeError("Workspace is not initialized")

        image_count = 0
        zip_files = list(self.input_dir.glob("*.zip"))
        if zip_files:
            zip_path = zip_files[0]
            logger.info("📦 Extracting ZIP: %s", zip_path)
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

        self.extracted_image_count = image_count
        logger.info("📷 Extracted %s images", image_count)
        return image_count

    def build_exif_manifest(self) -> List[ImageRecord]:
        if self.images_dir is None:
            raise RuntimeError("Workspace is not initialized")

        manifest_builder = ExifManifestBuilder(self.images_dir)
        records, diagnostics = manifest_builder.extract_manifest()
        self.exif_records = records
        self.exif_diagnostics = diagnostics
        skipped = diagnostics.get("skipped_images", [])
        if skipped:
            logger.warning(
                "⚠️ Excluding %s images that are missing GPS EXIF metadata",
                len(skipped),
            )
        if not records:
            raise RuntimeError("No valid EXIF GPS records were found in the input imagery")
        return records

    def plan_runtime(self) -> Dict[str, object]:
        self.runtime_plan = select_sfm_runtime_plan(
            len(self.exif_records),
            has_gps_priors=bool(self.exif_records),
            profile_override=self.profile_override,
            cpu_count=os.cpu_count() or 1,
            median_relative_altitude_m=self.exif_diagnostics.get("median_relative_altitude_m"),
        )
        logger.info(
            "📈 Runtime plan: profile=%s segments≈%s workers=%s neighbors=%s radius=%sm",
            self.runtime_plan["selected_profile"],
            self.runtime_plan["segment_count_estimate"],
            self.runtime_plan["segment_worker_count"],
            self.runtime_plan["spatial_matcher_neighbors"],
            self.runtime_plan["spatial_matcher_distance_m"],
        )
        return self.runtime_plan

    def create_segments(self) -> List[Segment]:
        self.segments = build_segments(
            self.exif_records,
            target_size=int(self.runtime_plan["segment_target_size"]),
            overlap=int(self.runtime_plan["segment_overlap"]),
            max_size=int(self.runtime_plan["segment_max_size"]),
            min_size=int(self.runtime_plan["segment_min_size"]),
        )
        logger.info("🧩 Created %s segments", len(self.segments))
        return self.segments

    def reconstruct_segments(self) -> List[SegmentRunResult]:
        if self.work_dir is None or self.images_dir is None:
            raise RuntimeError("Workspace is not initialized")

        runner = ColmapRunner(
            work_dir=self.work_dir,
            source_images_dir=self.images_dir,
            runtime_plan=self.runtime_plan,
        )
        record_lookup = {record.name: record for record in self.exif_records}
        self.segment_results = runner.run_segments(self.segments, record_lookup)
        self._runner = runner
        return self.segment_results

    def merge_models(self) -> MergeResult:
        if self.work_dir is None or self.images_dir is None:
            raise RuntimeError("Workspace is not initialized")
        if not self.segment_results:
            raise RuntimeError("No segment results are available")

        if len(self.segment_results) == 1:
            result = self.segment_results[0]
            self.merge_result = MergeResult(
                binary_model_dir=result.binary_model_dir,
                text_model_dir=result.text_model_dir,
                metrics=result.metrics,
                merge_steps=[],
            )
            return self.merge_result

        record_lookup = {record.name: record for record in self.exif_records}
        merger = ModelMerger(
            runner=self._runner,
            work_dir=self.work_dir,
            source_images_dir=self.images_dir,
        )
        self.merge_result = merger.merge_segments(
            segments=self.segments,
            segment_results=self.segment_results,
            record_lookup=record_lookup,
        )
        return self.merge_result

    def export_outputs(self) -> None:
        if self.merge_result is None:
            raise RuntimeError("Merged model is not available")

        sparse_output_dir = self.output_dir / "sparse" / "0"
        if sparse_output_dir.exists():
            shutil.rmtree(sparse_output_dir)
        sparse_output_dir.parent.mkdir(parents=True, exist_ok=True)
        self._runner.copy_text_model(Path(self.merge_result.text_model_dir), sparse_output_dir)
        self._create_compatibility_database(sparse_output_dir, self.output_dir / "database.db")

        final_metrics = analyze_sparse_text_model(sparse_output_dir)
        if self.sfm_only:
            logger.info("⏭️ Skipping image export because SfM-only mode is enabled")
        else:
            self._export_registered_images(final_metrics.registered_image_names)

        self._write_segment_manifest()
        self._write_metadata(final_metrics)
        self._write_cost_report()

    def _export_registered_images(self, registered_image_names: List[str]) -> None:
        if self.images_dir is None:
            raise RuntimeError("Workspace is not initialized")
        output_images_dir = self.output_dir / "images"
        if output_images_dir.exists():
            shutil.rmtree(output_images_dir)
        output_images_dir.mkdir(parents=True, exist_ok=True)

        for image_name in registered_image_names:
            source = self.images_dir / image_name
            target = output_images_dir / image_name
            try:
                os.link(source, target)
            except OSError:
                shutil.copy2(source, target)
        logger.info("✅ Exported %s registered images for 3DGS", len(registered_image_names))

    def _write_segment_manifest(self) -> None:
        manifest = {
            "inputImages": self.extracted_image_count,
            "imagesWithGpsPriors": len(self.exif_records),
            "skippedImages": self.exif_diagnostics.get("skipped_images", []),
            "segments": segments_to_manifest(self.segments),
            "segmentRuns": [result.to_manifest_entry() for result in self.segment_results],
        }
        with open(self.output_dir / "segment_manifest.json", "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)

    def _write_metadata(self, final_metrics) -> None:
        processing_time = time.time() - self._start_time
        quality_passed = quality_check_passed(
            final_metrics,
            input_image_count=max(1, len(self.exif_records)),
        )
        metadata = {
            "pipeline": "COLMAP Hybrid EXIF-First Structure-from-Motion",
            "sfm_engine": "colmap_hybrid",
            "processing_time_seconds": round(processing_time, 2),
            "input_images": self.extracted_image_count,
            "images_with_gps_priors": len(self.exif_records),
            "images_excluded_missing_gps": len(self.exif_diagnostics.get("skipped_images", [])),
            "cameras_registered": final_metrics.camera_count,
            "images_registered": final_metrics.image_count,
            "points_3d": final_metrics.point_count,
            "mean_observations_per_image": round(final_metrics.mean_observations_per_image, 4),
            "mean_track_length": round(final_metrics.mean_track_length, 4),
            "mean_reprojection_error": round(final_metrics.mean_reprojection_error, 6),
            "gps_enhanced": True,
            "gps_source": "exif",
            "gps_csv_supplied": bool(self.gps_csv_path and self.gps_csv_path.exists()),
            "sfm_only": self.sfm_only,
            "quality_check_passed": quality_passed,
            "colmap_format": True,
            "instance_type": self.sfm_instance_type,
            "selected_profile": self.runtime_plan.get("selected_profile"),
            "selected_neighbors": self.runtime_plan.get("spatial_matcher_neighbors"),
            "estimated_pairs": self.runtime_plan.get("estimated_pairs"),
            "segment_count": len(self.segments),
            "segment_worker_count": self.runtime_plan.get("segment_worker_count"),
            "stage_timeouts_seconds": self.runtime_plan.get("stage_timeouts", {}),
            "stage_metrics": self.stage_metrics,
            "merge_steps": self.merge_result.merge_steps if self.merge_result else [],
            "peak_memory_mb": round(self.peak_memory_mb, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        }
        with open(self.output_dir / "sfm_metadata.json", "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)

    def _write_cost_report(self) -> None:
        processing_time = time.time() - self._start_time
        runtime_report = estimate_processing_cost(self.sfm_instance_type, processing_time)
        projection_defaults = self.runtime_plan.get("projection_defaults", {})
        projected = project_large_landscape_cost(
            records=self.exif_records,
            segment_durations_seconds=[result.duration_seconds for result in self.segment_results],
            target_image_count=int(projection_defaults.get("target_image_count", 4750)),
            target_instance_type=str(projection_defaults.get("projection_instance_type", "ml.c6i.8xlarge")),
            target_worker_count=int(projection_defaults.get("projection_segment_worker_count", 4)),
            target_size=int(self.runtime_plan["segment_target_size"]),
            overlap=int(self.runtime_plan["segment_overlap"]),
            max_size=int(self.runtime_plan["segment_max_size"]),
            min_size=int(self.runtime_plan["segment_min_size"]),
        )
        report = {
            "runtimeEstimate": runtime_report,
            "largeLandscapeProjection": projected,
        }
        with open(self.output_dir / "cost_report.json", "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)

    def _create_compatibility_database(self, sparse_dir: Path, database_path: Path) -> None:
        if database_path.exists():
            database_path.unlink()
        connection = sqlite3.connect(str(database_path))
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cameras (
                    camera_id INTEGER PRIMARY KEY,
                    model INTEGER NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    params BLOB,
                    prior_focal_length INTEGER NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS images (
                    image_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    camera_id INTEGER NOT NULL,
                    prior_qw REAL,
                    prior_qx REAL,
                    prior_qy REAL,
                    prior_qz REAL,
                    prior_tx REAL,
                    prior_ty REAL,
                    prior_tz REAL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS keypoints (
                    image_id INTEGER NOT NULL,
                    rows INTEGER NOT NULL,
                    cols INTEGER NOT NULL,
                    data BLOB
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS matches (
                    pair_id INTEGER PRIMARY KEY,
                    rows INTEGER NOT NULL,
                    cols INTEGER NOT NULL,
                    data BLOB
                )
                """
            )

            cameras_file = sparse_dir / "cameras.txt"
            with open(cameras_file, "r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip() or line.startswith("#"):
                        continue
                    parts = line.split()
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO cameras
                        (camera_id, model, width, height, params, prior_focal_length)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            int(parts[0]),
                            1,
                            int(parts[2]),
                            int(parts[3]),
                            b"",
                            0,
                        ),
                    )

            images_file = sparse_dir / "images.txt"
            with open(images_file, "r", encoding="utf-8") as handle:
                lines = [line.strip() for line in handle if line.strip() and not line.startswith("#")]
            image_id = 1
            for index in range(0, len(lines), 2):
                parts = lines[index].split()
                if len(parts) < 10:
                    continue
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO images
                    (image_id, name, camera_id, prior_qw, prior_qx, prior_qy, prior_qz, prior_tx, prior_ty, prior_tz)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        image_id,
                        parts[9],
                        int(parts[8]),
                        float(parts[1]),
                        float(parts[2]),
                        float(parts[3]),
                        float(parts[4]),
                        float(parts[5]),
                        float(parts[6]),
                        float(parts[7]),
                    ),
                )
                image_id += 1
            connection.commit()
        finally:
            connection.close()

    def cleanup(self) -> None:
        if self.work_dir and self.work_dir.exists():
            shutil.rmtree(self.work_dir)
            logger.info("🧹 Cleanup completed")

    def run(self) -> int:
        try:
            self._start_time = time.time()
            self._run_timed("setup_workspace", "Create temporary workspace", self.setup_workspace)
            extracted = self._run_timed("extract_images", "Extract images", self.extract_images)
            if int(extracted) == 0:
                raise RuntimeError("No input images were extracted from the request")
            self._run_timed("build_exif_manifest", "Build EXIF manifest", self.build_exif_manifest)
            self._run_timed("plan_runtime", "Plan runtime", self.plan_runtime)
            self._run_timed("create_segments", "Create geo-temporal segments", self.create_segments)
            self._run_timed("reconstruct_segments", "Reconstruct segments with COLMAP", self.reconstruct_segments)
            self._run_timed("merge_models", "Merge segment models", self.merge_models)
            self._run_timed("export_outputs", "Export final COLMAP outputs", self.export_outputs)
            logger.info("✅ COLMAP hybrid pipeline completed successfully")
            return 0
        except Exception as error:
            logger.error("❌ Pipeline failed: %s", error)
            import traceback

            traceback.print_exc()
            return 1
        finally:
            self.cleanup()


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python run_colmap_hybrid.py <input_dir> <output_dir> [gps_csv]")
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    gps_csv = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    pipeline = ColmapHybridPipeline(input_dir, output_dir, gps_csv)
    exit_code = pipeline.run()
    logger.info("🏁 Pipeline finished with exit code: %s", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
