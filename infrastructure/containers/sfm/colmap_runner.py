"""COLMAP command orchestration for segmented SfM jobs."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from exif_manifest import ImageRecord
from model_analyzer import SparseModelMetrics, analyze_sparse_text_model
from segmenter import Segment


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SegmentRunResult:
    """Output metadata for a single reconstructed segment."""

    segment_id: str
    image_count: int
    engine: str
    duration_seconds: float
    workspace_dir: str
    database_path: str
    binary_model_dir: str
    text_model_dir: str
    metrics: Dict[str, object]

    @property
    def registered_ratio(self) -> float:
        image_count = max(1, self.image_count)
        return float(self.metrics.get("image_count", 0)) / image_count

    def to_manifest_entry(self) -> Dict[str, object]:
        return {
            "segmentId": self.segment_id,
            "imageCount": self.image_count,
            "engine": self.engine,
            "durationSeconds": round(self.duration_seconds, 2),
            "registeredRatio": round(self.registered_ratio, 4),
            "workspaceDir": self.workspace_dir,
            "databasePath": self.database_path,
            "binaryModelDir": self.binary_model_dir,
            "textModelDir": self.text_model_dir,
            "metrics": self.metrics,
        }


class ColmapRunner:
    """Drive COLMAP feature extraction, matching, and mapping."""

    def __init__(
        self,
        *,
        work_dir: Path,
        source_images_dir: Path,
        runtime_plan: Dict[str, object],
    ):
        self.work_dir = Path(work_dir)
        self.source_images_dir = Path(source_images_dir)
        self.runtime_plan = runtime_plan
        self._command_cache: Optional[List[str]] = None

    def run_segments(
        self,
        segments: Sequence[Segment],
        record_lookup: Dict[str, ImageRecord],
    ) -> List[SegmentRunResult]:
        if not segments:
            return []

        max_workers = min(
            int(self.runtime_plan.get("segment_worker_count", 1) or 1),
            len(segments),
        )
        if max_workers <= 1:
            return [self.run_segment(segment, record_lookup) for segment in segments]

        results: Dict[str, SegmentRunResult] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(self.run_segment, segment, record_lookup): segment.segment_id
                for segment in segments
            }
            for future in as_completed(future_map):
                segment_id = future_map[future]
                results[segment_id] = future.result()
                logger.info("Completed %s", segment_id)
        return [results[segment.segment_id] for segment in segments]

    def run_segment(
        self,
        segment: Segment,
        record_lookup: Dict[str, ImageRecord],
        *,
        force_engine: Optional[str] = None,
        boundary_mode: bool = False,
    ) -> SegmentRunResult:
        start_time = time.time()
        records = [record_lookup[name] for name in segment.image_names]
        workspace_dir = self._prepare_segment_workspace(segment.segment_id, records)
        database_path = workspace_dir / "database.db"

        self._run_feature_extraction(database_path, workspace_dir / "images", records, segment.segment_id)
        self._inject_image_priors(database_path, records)
        self._run_matching(
            database_path,
            segment.segment_id,
            boundary_mode=boundary_mode,
        )
        engine, binary_model_dir = self._run_mapper_chain(
            database_path,
            workspace_dir / "images",
            workspace_dir / "sparse",
            len(records),
            segment.segment_id,
            force_engine=force_engine,
        )
        text_model_dir = workspace_dir / "text_model"
        self._run_command(
            [
                "colmap",
                "model_converter",
                "--input_path",
                str(binary_model_dir),
                "--output_path",
                str(text_model_dir),
                "--output_type",
                "TXT",
            ],
            segment_id=segment.segment_id,
            stage="model_converter",
        )
        metrics = analyze_sparse_text_model(text_model_dir).to_dict()
        return SegmentRunResult(
            segment_id=segment.segment_id,
            image_count=len(records),
            engine=engine,
            duration_seconds=time.time() - start_time,
            workspace_dir=str(workspace_dir),
            database_path=str(database_path),
            binary_model_dir=str(binary_model_dir),
            text_model_dir=str(text_model_dir),
            metrics=metrics,
        )

    def run_boundary_segment(
        self,
        *,
        segment_id: str,
        image_names: Sequence[str],
        record_lookup: Dict[str, ImageRecord],
    ) -> SegmentRunResult:
        boundary_segment = Segment(
            segment_id=segment_id,
            image_names=list(image_names),
            start_name=image_names[0],
            end_name=image_names[-1],
            image_count=len(image_names),
            overlap_with_previous=0,
            overlap_with_next=0,
            hard_break_before=False,
        )
        return self.run_segment(
            boundary_segment,
            record_lookup,
            force_engine="mapper",
            boundary_mode=True,
        )

    def command_available(self, command_name: str) -> bool:
        if self._command_cache is None:
            try:
                result = subprocess.run(
                    ["colmap", "help"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self._command_cache = result.stdout.split()
            except Exception:
                self._command_cache = []
        return command_name in self._command_cache

    def _prepare_segment_workspace(
        self,
        segment_id: str,
        records: Sequence[ImageRecord],
    ) -> Path:
        workspace_dir = self.work_dir / "segments" / segment_id
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)
        images_dir = workspace_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        for record in records:
            source = Path(record.path)
            target = images_dir / record.name
            try:
                os.symlink(source, target)
            except FileExistsError:
                continue
            except OSError:
                shutil.copy2(source, target)
        return workspace_dir

    def _run_feature_extraction(
        self,
        database_path: Path,
        images_dir: Path,
        records: Sequence[ImageRecord],
        segment_id: str,
    ) -> None:
        image_lists_dir = images_dir.parent / "image_lists"
        image_lists_dir.mkdir(parents=True, exist_ok=True)
        grouped_records: Dict[str, List[ImageRecord]] = {}
        for record in records:
            grouped_records.setdefault(record.camera_group, []).append(record)

        for camera_group, grouped in grouped_records.items():
            image_list_path = image_lists_dir / f"{camera_group}.txt"
            image_list_path.write_text(
                "".join(f"{record.name}\n" for record in grouped),
                encoding="utf-8",
            )
            self._run_command(
                [
                    "colmap",
                    "feature_extractor",
                    "--database_path",
                    str(database_path),
                    "--image_path",
                    str(images_dir),
                    "--image_list_path",
                    str(image_list_path),
                    "--ImageReader.single_camera",
                    "1",
                    "--ImageReader.camera_model",
                    "SIMPLE_RADIAL",
                ],
                segment_id=segment_id,
                stage=f"feature_extractor[{camera_group}]",
            )

    def _inject_image_priors(
        self,
        database_path: Path,
        records: Sequence[ImageRecord],
    ) -> None:
        connection = sqlite3.connect(str(database_path))
        try:
            cursor = connection.cursor()
            for record in records:
                cursor.execute(
                    """
                    UPDATE images
                    SET prior_tx = ?, prior_ty = ?, prior_tz = ?
                    WHERE name = ?
                    """,
                    (record.enu_x_m, record.enu_y_m, record.enu_z_m, record.name),
                )
            connection.commit()
        finally:
            connection.close()

    def _run_matching(
        self,
        database_path: Path,
        segment_id: str,
        *,
        boundary_mode: bool = False,
    ) -> None:
        if boundary_mode:
            self._run_command(
                [
                    "colmap",
                    "exhaustive_matcher",
                    "--database_path",
                    str(database_path),
                ],
                segment_id=segment_id,
                stage="exhaustive_matcher",
            )
            return

        self._run_command(
            [
                "colmap",
                "spatial_matcher",
                "--database_path",
                str(database_path),
                "--SpatialMatching.max_num_neighbors",
                str(self.runtime_plan["spatial_matcher_neighbors"]),
                "--SpatialMatching.max_distance",
                str(self.runtime_plan["spatial_matcher_distance_m"]),
                "--SpatialMatching.is_gps",
                "0",
                "--SpatialMatching.ignore_z",
                "0",
            ],
            segment_id=segment_id,
            stage="spatial_matcher",
        )
        self._run_command(
            [
                "colmap",
                "sequential_matcher",
                "--database_path",
                str(database_path),
                "--SequentialMatching.overlap",
                str(self.runtime_plan["sequential_matcher_overlap"]),
            ],
            segment_id=segment_id,
            stage="sequential_matcher",
        )
        if self.runtime_plan.get("transitive_matcher_enabled"):
            self._run_command(
                [
                    "colmap",
                    "transitive_matcher",
                    "--database_path",
                    str(database_path),
                ],
                segment_id=segment_id,
                stage="transitive_matcher",
            )

    def _run_mapper_chain(
        self,
        database_path: Path,
        images_dir: Path,
        sparse_root: Path,
        image_count: int,
        segment_id: str,
        *,
        force_engine: Optional[str] = None,
    ) -> tuple[str, Path]:
        candidates = []
        if force_engine:
            candidates.append(force_engine)
        else:
            candidates.extend(["global_mapper", "pose_prior_mapper", "mapper"])

        for engine in candidates:
            if engine != "mapper" and not self.command_available(engine):
                logger.warning("%s is unavailable in this COLMAP build; skipping", engine)
                continue

            output_dir = sparse_root / engine
            output_dir.mkdir(parents=True, exist_ok=True)
            self._run_command(
                [
                    "colmap",
                    engine,
                    "--database_path",
                    str(database_path),
                    "--image_path",
                    str(images_dir),
                    "--output_path",
                    str(output_dir),
                ],
                segment_id=segment_id,
                stage=engine,
            )
            model_dir = self._resolve_model_dir(output_dir)
            if model_dir is None:
                continue

            text_dir = output_dir / "metrics_text"
            self._run_command(
                [
                    "colmap",
                    "model_converter",
                    "--input_path",
                    str(model_dir),
                    "--output_path",
                    str(text_dir),
                    "--output_type",
                    "TXT",
                ],
                segment_id=segment_id,
                stage=f"{engine}_metrics",
            )
            metrics = analyze_sparse_text_model(text_dir)
            ratio = metrics.image_count / max(1, image_count)
            if engine in {"global_mapper", "pose_prior_mapper"}:
                minimum_ratio = float(self.runtime_plan["global_mapper_min_registered_ratio"])
                if ratio < minimum_ratio and force_engine is None:
                    logger.warning(
                        "%s registered %.1f%% of %s images; trying fallback mapper",
                        engine,
                        ratio * 100.0,
                        image_count,
                    )
                    continue
            return engine, model_dir
        raise RuntimeError(f"No mapping engine produced a valid model for {segment_id}")

    def _resolve_model_dir(self, output_dir: Path) -> Optional[Path]:
        candidates = [output_dir] + sorted(path for path in output_dir.iterdir() if path.is_dir())
        for candidate in candidates:
            if any((candidate / name).exists() for name in ("cameras.bin", "cameras.txt")) and any(
                (candidate / name).exists() for name in ("images.bin", "images.txt")
            ) and any((candidate / name).exists() for name in ("points3D.bin", "points3D.txt")):
                return candidate
        return None

    def _run_command(
        self,
        command: List[str],
        *,
        segment_id: str,
        stage: str,
    ) -> None:
        env = os.environ.copy()
        thread_count = str(self.runtime_plan.get("worker_threads", 2))
        env["OMP_NUM_THREADS"] = thread_count
        env["OPENBLAS_NUM_THREADS"] = thread_count
        env["MKL_NUM_THREADS"] = thread_count
        env["NUMEXPR_NUM_THREADS"] = thread_count
        env["VECLIB_MAXIMUM_THREADS"] = thread_count

        logger.info("[%s:%s] %s", segment_id, stage, " ".join(command))
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
            print(f"COLMAP[{segment_id}:{stage}] {message}", flush=True)
        return_code = process.wait()
        if return_code != 0:
            tail = "\n".join(lines[-20:])
            raise RuntimeError(
                f"COLMAP command failed for {segment_id}:{stage} "
                f"with exit code {return_code}\n{tail}"
            )

    def copy_text_model(self, source_dir: Path, destination_dir: Path) -> None:
        if destination_dir.exists():
            shutil.rmtree(destination_dir)
        shutil.copytree(source_dir, destination_dir)

    def write_segment_report(self, results: Sequence[SegmentRunResult], path: Path) -> None:
        path.write_text(
            json.dumps([result.to_manifest_entry() for result in results], indent=2),
            encoding="utf-8",
        )
