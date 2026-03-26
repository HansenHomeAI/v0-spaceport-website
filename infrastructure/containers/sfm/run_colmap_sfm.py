#!/usr/bin/env python3
"""GPU COLMAP SfM pipeline that exports the 3DGS-compatible sparse handoff."""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


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


class ColmapPipeline:
    def __init__(self, input_dir: Path, output_dir: Path) -> None:
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.work_dir = Path(tempfile.mkdtemp(prefix="colmap_sfm_"))
        self.images_dir = self.work_dir / "images"
        self.database_path = self.work_dir / "database.db"
        self.sparse_root = self.work_dir / "sparse"
        self.vocab_tree_path = Path(
            os.environ.get(
                "COLMAP_VOCAB_TREE_PATH",
                "/opt/ml/code/resources/vocab_tree_faiss_flickr100K_words256K.bin",
            )
        )
        self.generated_vocab_tree_path = self.work_dir / "vocab_tree_faiss.bin"
        self.active_vocab_tree_path: Path | None = None
        self.vocab_tree_url = os.environ.get(
            "COLMAP_VOCAB_TREE_URL",
            "https://github.com/colmap/colmap/releases/download/3.11.1/"
            "vocab_tree_faiss_flickr100K_words256K.bin",
        )
        self.use_gpu = os.environ.get("COLMAP_USE_GPU", "1") != "0"
        self.enable_spatial_matcher = os.environ.get("COLMAP_ENABLE_SPATIAL_MATCHER", "1") != "0"
        self.max_features = int(os.environ.get("COLMAP_SIFT_MAX_NUM_FEATURES", "8192"))
        self.vocab_num_images = int(os.environ.get("COLMAP_VOCAB_NUM_IMAGES", "40"))
        self.vocab_num_visual_words = int(
            os.environ.get("COLMAP_VOCAB_BUILD_NUM_VISUAL_WORDS", "32768")
        )
        self.vocab_max_num_descriptors = int(
            os.environ.get("COLMAP_VOCAB_BUILD_MAX_NUM_DESCRIPTORS", "250000")
        )
        self.vocab_build_threads = os.environ.get(
            "COLMAP_VOCAB_BUILD_THREADS",
            os.environ.get("COLMAP_MAPPER_THREADS", "-1"),
        )
        self.spatial_neighbors = int(os.environ.get("COLMAP_SPATIAL_MAX_NEIGHBORS", "24"))
        self.spatial_distance_m = float(os.environ.get("COLMAP_SPATIAL_MAX_DISTANCE_METERS", "150"))
        self.mapper_threads = os.environ.get("COLMAP_MAPPER_THREADS", "-1")
        self.start_time = time.time()
        self.timings: Dict[str, float] = {}
        self.gps_image_count = 0
        self.matchers_run: List[str] = []
        self.matcher_pair_deltas: Dict[str, int] = {}
        self.vocab_tree_source = "uninitialized"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.sparse_root.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> int:
        try:
            self.extract_images()
            self.gps_image_count = self.count_images_with_gps()
            self.ensure_vocab_tree()
            self.run_feature_extraction()
            self.run_matching()
            best_text_dir = self.run_mapper()
            self.export_output(best_text_dir)
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

    def count_images_with_gps(self) -> int:
        command = [
            "exiftool",
            "-j",
            "-n",
            "-r",
            "-GPSLatitude",
            "-GPSLongitude",
            "-GPSAltitude",
            str(self.images_dir),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        records = json.loads(result.stdout or "[]")
        count = sum(
            1
            for record in records
            if "GPSLatitude" in record and "GPSLongitude" in record
        )
        logger.info("Detected GPS EXIF priors on %s images", count)
        return count

    def count_verified_pairs(self) -> int:
        if not self.database_path.exists():
            return 0
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute("SELECT COUNT(*) FROM two_view_geometries").fetchone()
        return int(row[0] if row else 0)

    def ensure_vocab_tree(self) -> None:
        started = time.time()
        if self.vocab_tree_path.exists() and self.vocab_tree_path.stat().st_size > 0:
            logger.info("Using cached vocab tree at %s", self.vocab_tree_path)
            self.timings["download_vocab_tree_seconds"] = 0.0
            self.active_vocab_tree_path = self.vocab_tree_path
            self.vocab_tree_source = "downloaded_cached"
            return
        if not self.vocab_tree_url:
            logger.info("No external vocab tree configured; will build a FAISS tree from descriptors")
            self.timings["download_vocab_tree_seconds"] = 0.0
            self.vocab_tree_source = "built_from_database"
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
        if self.active_vocab_tree_path is None:
            self.build_vocab_tree()
        assert self.active_vocab_tree_path is not None
        stream_command(
            [
                "colmap",
                "vocab_tree_matcher",
                "--database_path",
                str(self.database_path),
                "--SiftMatching.use_gpu",
                "1" if self.use_gpu else "0",
                "--SiftMatching.guided_matching",
                "1",
                "--VocabTreeMatching.vocab_tree_path",
                str(self.active_vocab_tree_path),
                "--VocabTreeMatching.num_images",
                str(self.vocab_num_images),
            ],
            stage="vocab_tree_matcher",
        )

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
            "--SiftExtraction.use_gpu",
            "1" if self.use_gpu else "0",
            "--SiftExtraction.max_num_features",
            str(self.max_features),
        ]
        max_image_size = os.environ.get("COLMAP_FEATURE_MAX_IMAGE_SIZE")
        if max_image_size:
            command.extend(["--SiftExtraction.max_image_size", max_image_size])
        stream_command(command, stage="feature_extractor")
        self.timings["feature_extraction_seconds"] = round(time.time() - started, 2)

    def run_matching(self) -> None:
        if self.enable_spatial_matcher and self.gps_image_count > 0:
            started = time.time()
            pairs_before = self.count_verified_pairs()
            stream_command(
                [
                    "colmap",
                    "spatial_matcher",
                    "--database_path",
                    str(self.database_path),
                    "--SiftMatching.use_gpu",
                    "1" if self.use_gpu else "0",
                    "--SiftMatching.guided_matching",
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
            logger.info(
                "Spatial matcher added %s verified image pairs",
                self.matcher_pair_deltas["spatial_matcher"],
            )

        started = time.time()
        pairs_before = self.count_verified_pairs()
        try:
            self.run_vocab_tree_matcher()
        except RuntimeError as exc:
            if "Failed to read faiss index" not in str(exc):
                raise
            logger.warning(
                "Downloaded vocab tree is a legacy FLANN index; rebuilding a FAISS tree locally"
            )
            self.build_vocab_tree()
            self.run_vocab_tree_matcher()
        pairs_after = self.count_verified_pairs()
        self.timings["vocab_tree_matching_seconds"] = round(time.time() - started, 2)
        self.matcher_pair_deltas["vocab_tree_matcher"] = pairs_after - pairs_before
        self.matchers_run.append("vocab_tree_matcher")
        logger.info(
            "Vocab tree matcher added %s verified image pairs",
            self.matcher_pair_deltas["vocab_tree_matcher"],
        )

    def run_mapper(self) -> Path:
        started = time.time()
        stream_command(
            [
                "colmap",
                "mapper",
                "--database_path",
                str(self.database_path),
                "--image_path",
                str(self.images_dir),
                "--output_path",
                str(self.sparse_root),
                "--Mapper.num_threads",
                str(self.mapper_threads),
                "--Mapper.ba_refine_principal_point",
                "0",
            ],
            stage="mapper",
        )
        self.timings["mapper_seconds"] = round(time.time() - started, 2)

        candidate_dirs = [
            path for path in sorted(self.sparse_root.iterdir()) if path.is_dir()
        ]
        if not candidate_dirs:
            raise RuntimeError("COLMAP mapper did not produce any sparse models")

        best_dir: Path | None = None
        best_text_dir: Path | None = None
        best_registered = -1
        for candidate_dir in candidate_dirs:
            text_dir = self.work_dir / "text_models" / candidate_dir.name
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
                stage=f"model_converter_{candidate_dir.name}",
            )
            registered = count_registered_images(text_dir / "images.txt")
            logger.info("Model %s registered %s images", candidate_dir.name, registered)
            if registered > best_registered:
                best_registered = registered
                best_dir = candidate_dir
                best_text_dir = text_dir
        if best_dir is None or best_text_dir is None:
            raise RuntimeError("Unable to choose a sparse model for export")
        logger.info("Selected sparse model %s with %s registered images", best_dir.name, best_registered)
        return best_text_dir

    def export_output(self, best_text_dir: Path) -> None:
        sparse_output = self.output_dir / "sparse" / "0"
        images_output = self.output_dir / "images"

        if sparse_output.exists():
            shutil.rmtree(sparse_output)
        if images_output.exists():
            shutil.rmtree(images_output)

        sparse_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(best_text_dir, sparse_output)
        shutil.copytree(self.images_dir, images_output)
        shutil.copy2(self.database_path, self.output_dir / "database.db")

        cameras = count_text_rows(sparse_output / "cameras.txt")
        images = count_registered_images(sparse_output / "images.txt")
        points = count_text_rows(sparse_output / "points3D.txt")
        metadata = {
            "pipeline": "colmap_gpu_vocab_tree",
            "processing_time_seconds": round(time.time() - self.start_time, 2),
            "timings": self.timings,
            "cameras_registered": cameras,
            "images_registered": images,
            "points_3d": points,
            "quality_check_passed": points >= 1000 and images > 0 and cameras > 0,
            "gpu_enabled": self.use_gpu,
            "gps_priors_detected": self.gps_image_count,
            "spatial_matcher_enabled": self.enable_spatial_matcher,
            "matchers_run": self.matchers_run,
            "matcher_pair_deltas": self.matcher_pair_deltas,
            "verified_pairs_total": self.count_verified_pairs(),
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
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with open(self.output_dir / "sfm_metadata.json", "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)

        if not metadata["quality_check_passed"]:
            raise RuntimeError(
                f"Exported sparse model failed quality gate: "
                f"cameras={cameras}, images={images}, points={points}"
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
