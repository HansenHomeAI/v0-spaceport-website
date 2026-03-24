#!/usr/bin/env python3
"""
NerfStudio-based 3D Gaussian Splatting training entrypoint.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, Optional, Sequence

import numpy as np
import yaml
try:
    import boto3
except ImportError:  # pragma: no cover - only used in local dry-run environments
    boto3 = None

try:
    import torch
except ImportError:  # pragma: no cover - only used in local dry-run environments
    torch = None

from utils.ply_ops import clip_ply_to_bounds, merge_clipped_tiles, write_mock_gaussian_ply
from utils.segmented_training import SparseScene, TileSpec, build_tiles, load_profile, write_tile_dataset


if torch is not None:
    try:
        torch._dynamo.config.suppress_errors = True
        print("✅ PyTorch dynamo error suppression enabled")
    except AttributeError:
        print("✅ PyTorch version doesn't have dynamo module")
else:
    print("⚠️ PyTorch not available; local dry-run mode only")

os.environ["TORCH_COMPILE_DISABLE"] = "1"
print("✅ TORCH_COMPILE_DISABLE=1 set")

os.environ.setdefault("TORCH_CUDA_ARCH_LIST", "8.0 8.6")
print(f"✅ TORCH_CUDA_ARCH_LIST={os.environ['TORCH_CUDA_ARCH_LIST']}")

cuda_home = os.environ.setdefault("CUDA_HOME", "/usr/local/cuda")
cuda_lib_paths = [f"{cuda_home}/lib64", f"{cuda_home}/lib"]
for variable_name in ("LD_LIBRARY_PATH", "LIBRARY_PATH"):
    existing = os.environ.get(variable_name, "")
    parts = [path for path in existing.split(":") if path]
    for path in cuda_lib_paths:
        if path not in parts and os.path.isdir(path):
            parts.insert(0, path)
    os.environ[variable_name] = ":".join(parts) if parts else ":".join(cuda_lib_paths)
    print(f"✅ {variable_name}={os.environ[variable_name]}")


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Unsupported S3 URI: {uri}")
    bucket_key = uri[5:]
    bucket, _, key = bucket_key.partition("/")
    return bucket, key


def join_s3_uri(prefix: str, suffix: str) -> str:
    return f"{prefix.rstrip('/')}/{suffix.lstrip('/')}"


def json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "tolist"):
        return value.tolist()
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def read_ply_vertex_count(ply_path: Path) -> int:
    with open(ply_path, "rb") as handle:
        for raw_line in handle:
            line = raw_line.decode("utf-8", errors="ignore").strip()
            if line.startswith("element vertex"):
                return int(line.split()[-1])
            if line == "end_header":
                break
    raise ValueError(f"Could not read vertex count from {ply_path}")


class NerfStudioTrainer:
    """Production NerfStudio trainer with segmented training support."""

    HOURLY_RATES_USD = {
        "ml.g5.xlarge": 1.006,
        "ml.g5.2xlarge": 1.212,
        "ml.g4dn.xlarge": 0.526,
    }

    def __init__(self, config_path: str):
        with open(config_path, "r", encoding="utf-8") as handle:
            self.config = yaml.safe_load(handle)

        self.input_dir = Path(os.environ.get("SM_CHANNEL_TRAINING", "/opt/ml/input/data/training"))
        self.output_dir = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
        self.temp_dir = Path("/tmp/nerfstudio_training")
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.temp_dir.mkdir(exist_ok=True, parents=True)

        self.start_time = time.time()
        self.training_mode = os.environ.get("TRAINING_MODE", "monolithic").strip().lower()
        self.segmented_profile_name = os.environ.get("SEGMENTED_PROFILE", "landscape_v1").strip()
        self.segmented_profile = load_profile(self.segmented_profile_name)
        self.segment_target_gaussians = int(os.environ.get("SEG_TARGET_TOTAL_GAUSSIANS", "15000000"))
        self.segment_target_min = int(self.segment_target_gaussians * 0.9)
        self.segment_target_max = int(self.segment_target_gaussians * 1.1)
        self.segment_max_tiles = int(os.environ.get("SEG_MAX_TILES", str(self.segmented_profile.max_tiles)))
        self.segment_tile_iteration_cap = int(
            os.environ.get("SEG_TILE_MAX_ITERATIONS", str(self.segmented_profile.heavy_tile_iterations))
        )
        self.segmented_dry_run = bool_env("SEGMENTED_DRY_RUN", False)
        self.write_proof_artifacts = bool_env("WRITE_PROOF_ARTIFACTS", False)

        self.model_output_s3_uri = os.environ.get("MODEL_OUTPUT_S3_URI")
        self.compressed_output_s3_uri = os.environ.get("COMPRESSED_OUTPUT_S3_URI")
        self.training_job_name = os.environ.get("TRAINING_JOB_NAME") or os.environ.get("SAGEMAKER_JOB_NAME")
        self.instance_type = os.environ.get("INSTANCE_TYPE", "ml.g5.xlarge")
        self.aws_region = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")
        self.s3_client = (
            boto3.client("s3", region_name=self.aws_region)
            if self.model_output_s3_uri and boto3 is not None
            else None
        )
        if self.model_output_s3_uri and self.s3_client is None:
            logger.warning("⚠️ boto3 unavailable; S3 proof uploads are disabled in this environment")

        self.apply_step_functions_params()

        if self.segment_max_tiles != self.segmented_profile.max_tiles:
            self.segmented_profile.max_tiles = self.segment_max_tiles  # type: ignore[misc]

        logger.info("🚀 NerfStudio Trainer initialized")
        logger.info(f"📁 Input directory: {self.input_dir}")
        logger.info(f"📁 Output directory: {self.output_dir}")
        logger.info(f"📁 Temp directory: {self.temp_dir}")
        logger.info(f"🎛️  Training mode: {self.training_mode}")
        logger.info(f"🧩 Segmented profile: {self.segmented_profile_name}")
        logger.info(f"🎯 Segmented target gaussians: {self.segment_target_gaussians:,}")
        logger.info(f"📦 Proof artifact uploads: {self.write_proof_artifacts}")

    def apply_step_functions_params(self) -> None:
        env_params = {
            "MAX_ITERATIONS": "training.max_iterations",
            "TARGET_PSNR": "training.target_psnr",
            "SH_DEGREE": "model.sh_degree",
            "BILATERAL_PROCESSING": "model.bilateral_processing",
            "LOG_INTERVAL": "training.log_interval",
            "MODEL_VARIANT": "model.variant",
        }

        for env_var, config_path in env_params.items():
            value = os.environ.get(env_var)
            if value is None:
                continue

            if env_var == "BILATERAL_PROCESSING":
                converted: Any = value.lower() in ("true", "1", "yes", "on")
            elif env_var in {"MAX_ITERATIONS", "SH_DEGREE", "LOG_INTERVAL"}:
                converted = int(value)
            elif env_var == "TARGET_PSNR":
                converted = float(value)
            else:
                converted = value

            keys = config_path.split(".")
            section = self.config
            for key in keys[:-1]:
                section = section.setdefault(key, {})
            section[keys[-1]] = converted
            logger.info(f"📝 Override {config_path} = {converted} (from {env_var})")

    def validate_colmap_structure(self, input_dir: Path) -> Dict[str, int]:
        logger.info(f"🔍 Validating COLMAP data at {input_dir}")
        required_paths = [
            input_dir / "sparse" / "0" / "cameras.txt",
            input_dir / "sparse" / "0" / "images.txt",
            input_dir / "sparse" / "0" / "points3D.txt",
            input_dir / "images",
        ]
        for required_path in required_paths:
            if not required_path.exists():
                raise FileNotFoundError(f"Required file or directory missing: {required_path}")

        cameras_file = input_dir / "sparse" / "0" / "cameras.txt"
        images_file = input_dir / "sparse" / "0" / "images.txt"
        points_file = input_dir / "sparse" / "0" / "points3D.txt"
        images_dir = input_dir / "images"

        with open(cameras_file, "r", encoding="utf-8") as handle:
            camera_count = sum(1 for line in handle if line.strip() and not line.startswith("#"))
        with open(images_file, "r", encoding="utf-8") as handle:
            image_lines = [line for line in handle if line.strip() and not line.startswith("#")]
            image_count = len(image_lines) // 2
        with open(points_file, "r", encoding="utf-8") as handle:
            point_count = sum(1 for line in handle if line.strip() and not line.startswith("#"))
        image_files = list(images_dir.glob("*"))
        image_file_count = sum(1 for path in image_files if path.is_file())

        stats = {
            "camera_count": camera_count,
            "image_count": image_count,
            "point_count": point_count,
            "image_file_count": image_file_count,
        }
        logger.info(f"📊 COLMAP stats: {stats}")

        if camera_count == 0:
            raise ValueError("No cameras found in COLMAP data")
        if image_count == 0:
            raise ValueError("No images found in COLMAP data")
        minimum_points = 10 if self.segmented_dry_run else 1000
        if point_count < minimum_points:
            raise ValueError(f"Insufficient 3D points for training: {point_count}")
        if image_file_count < int(image_count * 0.8):
            raise ValueError(
                f"Insufficient image files for training: {image_file_count} files for {image_count} registered images"
            )

        return stats

    def convert_colmap_to_nerfstudio(self, source_input_dir: Path, work_dir: Path) -> Path:
        logger.info(f"🔄 Converting COLMAP data under {source_input_dir} to NerfStudio format")
        converted_dir = work_dir / "converted_data"
        converted_dir.mkdir(parents=True, exist_ok=True)

        sparse_txt_dir = source_input_dir / "sparse" / "0"
        sparse_bin_dir = work_dir / "colmap_bin" / "0"
        sparse_bin_dir.mkdir(parents=True, exist_ok=True)
        self.convert_colmap_text_to_binary(sparse_txt_dir, sparse_bin_dir)

        command = [
            "ns-process-data",
            "images",
            "--data",
            str(source_input_dir / "images"),
            "--output-dir",
            str(converted_dir),
            "--skip-colmap",
            "--colmap-model-path",
            str(sparse_bin_dir),
        ]
        self.run_subprocess(command, timeout=600, description="COLMAP to NerfStudio conversion")

        transforms_file = converted_dir / "transforms.json"
        if not transforms_file.exists():
            raise FileNotFoundError("transforms.json was not created during NerfStudio conversion")
        self.validate_transforms_json(transforms_file, converted_dir)
        return converted_dir

    def convert_colmap_text_to_binary(self, sparse_txt_dir: Path, sparse_bin_dir: Path) -> None:
        cameras_bin = sparse_bin_dir / "cameras.bin"
        images_bin = sparse_bin_dir / "images.bin"
        points3d_bin = sparse_bin_dir / "points3D.bin"
        if cameras_bin.exists() and images_bin.exists() and points3d_bin.exists():
            logger.info("✅ Binary COLMAP files already exist, skipping conversion")
            return

        command = [
            "colmap",
            "model_converter",
            "--input_path",
            str(sparse_txt_dir),
            "--output_path",
            str(sparse_bin_dir),
            "--output_type",
            "BIN",
        ]
        self.run_subprocess(command, timeout=300, description="COLMAP text to binary conversion")
        for path in (cameras_bin, images_bin, points3d_bin):
            if not path.exists():
                raise FileNotFoundError(f"Expected binary file missing after conversion: {path}")

    def validate_transforms_json(self, transforms_file: Path, dataset_dir: Path) -> None:
        logger.info(f"🔍 Validating transforms file {transforms_file}")
        with open(transforms_file, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        frames = payload.get("frames", [])
        if len(frames) < 2:
            raise ValueError("transforms.json must contain at least two frames")

        valid_frames = 0
        for frame in frames:
            file_path = frame.get("file_path")
            transform_matrix = frame.get("transform_matrix")
            if not file_path or not transform_matrix:
                continue
            if (dataset_dir / file_path).exists():
                valid_frames += 1

        if valid_frames < 2:
            raise ValueError("NerfStudio conversion produced fewer than two valid frames")

    def run_subprocess(
        self,
        command: Sequence[str],
        timeout: int,
        description: str,
        cwd: Optional[Path] = None,
    ) -> subprocess.CompletedProcess[str]:
        logger.info(f"🚀 {description}: {' '.join(command)}")
        result = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
        )

        if result.stdout:
            for line in result.stdout.splitlines():
                logger.info(f"   STDOUT: {line}")
        if result.stderr:
            for line in result.stderr.splitlines():
                logger.info(f"   STDERR: {line}")

        if result.returncode != 0:
            raise RuntimeError(f"{description} failed with exit code {result.returncode}")

        return result

    def build_train_command(
        self,
        data_dir: Path,
        output_root: Path,
        max_iterations: int,
        log_interval: Optional[int] = None,
    ) -> list[str]:
        model_config = self.config.get("model", {})
        training_config = self.config.get("training", {})

        model_variant = model_config.get("variant", "splatfacto-big")
        sh_degree = int(model_config.get("sh_degree", 3))
        bilateral_processing = bool(model_config.get("bilateral_processing", True))
        log_interval = log_interval or int(training_config.get("log_interval", 100))

        command = [
            "ns-train",
            model_variant,
            "--data",
            str(data_dir),
            "--output-dir",
            str(output_root),
            "--max_num_iterations",
            str(max_iterations),
            "--pipeline.model.sh_degree",
            str(sh_degree),
            "--pipeline.model.max-gauss-ratio",
            "10.0",
            "--viewer.quit_on_train_completion",
            "True",
            "--viewer.websocket_port",
            "7007",
            "--logging.steps_per_log",
            str(log_interval),
        ]
        if bilateral_processing:
            command.extend(["--pipeline.model.use-bilateral-grid", "True"])
        return command

    def run_nerfstudio_training(
        self,
        data_dir: Path,
        output_root: Path,
        max_iterations: int,
        log_interval: Optional[int] = None,
    ) -> None:
        command = self.build_train_command(data_dir, output_root, max_iterations, log_interval)
        self.run_subprocess(command, timeout=7200, description="NerfStudio training")

    def export_trained_model(self, training_root: Path, output_dir: Path) -> Path:
        config_files = list(training_root.glob("**/config.yml"))
        if not config_files:
            raise FileNotFoundError(f"No config.yml found under {training_root}")

        config_file = max(config_files, key=lambda path: path.stat().st_mtime)
        command = [
            "ns-export",
            "gaussian-splat",
            "--load-config",
            str(config_file),
            "--output-dir",
            str(output_dir),
        ]
        self.run_subprocess(command, timeout=600, description="Gaussian export")

        ply_files = list(output_dir.glob("*.ply"))
        if not ply_files:
            raise FileNotFoundError(f"No PLY files were exported under {output_dir}")
        return max(ply_files, key=lambda path: path.stat().st_mtime)

    def train_single_scene(
        self,
        source_input_dir: Path,
        output_dir: Path,
        work_dir: Path,
        max_iterations: int,
    ) -> Path:
        converted_dir = self.convert_colmap_to_nerfstudio(source_input_dir, work_dir)
        self.run_nerfstudio_training(converted_dir, work_dir, max_iterations=max_iterations)
        return self.export_trained_model(work_dir, output_dir)

    def _elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    def _hourly_rate_usd(self) -> float:
        return self.HOURLY_RATES_USD.get(self.instance_type, self.HOURLY_RATES_USD["ml.g5.xlarge"])

    def _estimated_cost_usd(self) -> float:
        return self._elapsed_seconds() * self._hourly_rate_usd() / 3600.0

    def generate_training_metadata(
        self,
        training_mode: str,
        gaussian_count: int,
        input_summary: Dict[str, int],
        segmentation_manifest: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata = {
            "training_mode": training_mode,
            "training_methodology": "Vincent Woo Sutro Tower",
            "framework": "NerfStudio",
            "model_variant": self.config.get("model", {}).get("variant", "splatfacto-big"),
            "bilateral_guided_processing": self.config.get("model", {}).get("bilateral_processing", True),
            "sh_degree": self.config.get("model", {}).get("sh_degree", 3),
            "max_iterations": self.config.get("training", {}).get("max_iterations", 30000),
            "commercial_license": "Apache 2.0",
            "sogs_compatible": True,
            "playcanvas_ready": True,
            "training_completed": True,
            "version": "2.0.0",
            "timestamp": time.time(),
            "instance_type": self.instance_type,
            "pricing_hourly_usd": self._hourly_rate_usd(),
            "estimated_elapsed_seconds": round(self._elapsed_seconds(), 3),
            "estimated_cost_usd": round(self._estimated_cost_usd(), 4),
            "input_summary": input_summary,
            "gaussian_count": gaussian_count,
        }
        if segmentation_manifest is not None:
            metadata["segmented_profile"] = self.segmented_profile_name
            metadata["tile_count"] = segmentation_manifest["tile_count"]
            metadata["seam_density_ratio"] = segmentation_manifest["merge"]["seam_density_ratio"]
        return metadata

    def write_json_file(self, path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, default=json_default)

    def upload_proof_artifacts(
        self,
        splat_path: Path,
        metadata_path: Path,
        proof_links_path: Path,
        segmentation_manifest_path: Optional[Path],
    ) -> Dict[str, Optional[str]]:
        if not self.write_proof_artifacts or not self.model_output_s3_uri or not self.s3_client:
            return {}

        uploaded_uris: Dict[str, Optional[str]] = {
            "raw_model_s3_uri": join_s3_uri(self.model_output_s3_uri, "extracted/splat.ply"),
            "training_metadata_s3_uri": join_s3_uri(self.model_output_s3_uri, "training_metadata.json"),
            "proof_links_s3_uri": join_s3_uri(self.model_output_s3_uri, "proof/proof_links.json"),
            "segmentation_manifest_s3_uri": None,
        }
        if segmentation_manifest_path:
            uploaded_uris["segmentation_manifest_s3_uri"] = join_s3_uri(
                self.model_output_s3_uri, "segmentation_manifest.json"
            )

        uploads = [
            (splat_path, uploaded_uris["raw_model_s3_uri"], "application/octet-stream"),
            (metadata_path, uploaded_uris["training_metadata_s3_uri"], "application/json"),
            (proof_links_path, uploaded_uris["proof_links_s3_uri"], "application/json"),
        ]
        if segmentation_manifest_path and uploaded_uris["segmentation_manifest_s3_uri"]:
            uploads.append(
                (
                    segmentation_manifest_path,
                    uploaded_uris["segmentation_manifest_s3_uri"],
                    "application/json",
                )
            )

        for local_path, s3_uri, content_type in uploads:
            bucket, key = parse_s3_uri(s3_uri)
            self.s3_client.upload_file(
                str(local_path),
                bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
            logger.info(f"☁️ Uploaded {local_path.name} to {s3_uri}")

        return uploaded_uris

    def build_proof_links(
        self,
        training_mode: str,
        uploaded_uris: Dict[str, Optional[str]],
        segmentation_manifest: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        proof_links = {
            "training_mode": training_mode,
            "job_name": self.training_job_name,
            "raw_model_s3_uri": uploaded_uris.get("raw_model_s3_uri")
            or ("splat.ply" if not self.model_output_s3_uri else join_s3_uri(self.model_output_s3_uri, "extracted/splat.ply")),
            "training_metadata_s3_uri": uploaded_uris.get("training_metadata_s3_uri")
            or (
                "training_metadata.json"
                if not self.model_output_s3_uri
                else join_s3_uri(self.model_output_s3_uri, "training_metadata.json")
            ),
            "segmentation_manifest_s3_uri": uploaded_uris.get("segmentation_manifest_s3_uri")
            if segmentation_manifest
            else None,
            "compressed_bundle_s3_uri": (
                join_s3_uri(self.compressed_output_s3_uri, "supersplat_bundle/")
                if self.compressed_output_s3_uri
                else None
            ),
            "proof_metrics_s3_uri": uploaded_uris.get("training_metadata_s3_uri")
            or (
                "training_metadata.json"
                if not self.model_output_s3_uri
                else join_s3_uri(self.model_output_s3_uri, "training_metadata.json")
            ),
            "generated_at_epoch_seconds": time.time(),
        }
        return proof_links

    def write_proof_bundle(
        self,
        training_mode: str,
        splat_path: Path,
        metadata: Dict[str, Any],
        segmentation_manifest: Optional[Dict[str, Any]] = None,
    ) -> None:
        metadata_path = self.output_dir / "training_metadata.json"
        self.write_json_file(metadata_path, metadata)

        segmentation_manifest_path: Optional[Path] = None
        if segmentation_manifest is not None:
            segmentation_manifest_path = self.output_dir / "segmentation_manifest.json"
            self.write_json_file(segmentation_manifest_path, segmentation_manifest)

        placeholder_links = self.build_proof_links(training_mode, {}, segmentation_manifest)
        proof_links_path = self.output_dir / "proof" / "proof_links.json"
        self.write_json_file(proof_links_path, placeholder_links)

        uploaded_uris = self.upload_proof_artifacts(
            splat_path=splat_path,
            metadata_path=metadata_path,
            proof_links_path=proof_links_path,
            segmentation_manifest_path=segmentation_manifest_path,
        )

        if uploaded_uris:
            proof_links = self.build_proof_links(training_mode, uploaded_uris, segmentation_manifest)
            self.write_json_file(proof_links_path, proof_links)
            if self.write_proof_artifacts and self.model_output_s3_uri and self.s3_client:
                bucket, key = parse_s3_uri(join_s3_uri(self.model_output_s3_uri, "proof/proof_links.json"))
                self.s3_client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=json.dumps(proof_links, indent=2, default=json_default).encode("utf-8"),
                    ContentType="application/json",
                )
                logger.info(f"☁️ Updated proof links at s3://{bucket}/{key}")

    def run_monolithic_training_pipeline(self) -> bool:
        input_summary = self.validate_colmap_structure(self.input_dir)
        max_iterations = int(self.config.get("training", {}).get("max_iterations", 30000))
        monolithic_work_dir = self.temp_dir / "monolithic"
        monolithic_work_dir.mkdir(parents=True, exist_ok=True)

        splat_path = self.train_single_scene(
            source_input_dir=self.input_dir,
            output_dir=self.output_dir,
            work_dir=monolithic_work_dir,
            max_iterations=max_iterations,
        )
        gaussian_count = read_ply_vertex_count(splat_path)
        metadata = self.generate_training_metadata(
            training_mode="monolithic",
            gaussian_count=gaussian_count,
            input_summary=input_summary,
        )
        self.write_proof_bundle("monolithic", splat_path, metadata)
        return True

    def _resolve_tile_iterations(self, tile: TileSpec) -> int:
        return min(tile.iterations, self.segment_tile_iteration_cap)

    def _dry_run_tile_count(self, tile: TileSpec, tiles: Sequence[TileSpec]) -> int:
        total_points = sum(max(len(candidate.expanded_point_ids), 1) for candidate in tiles)
        tile_weight = max(len(tile.expanded_point_ids), 1) / max(total_points, 1)
        count = int(max(self.segment_target_gaussians * tile_weight * 1.2, 64))
        return min(count, int(max(self.segment_target_gaussians * 1.2, 64)))

    def _tile_centers_xyz(self, scene: SparseScene, tile: TileSpec) -> Any:
        if tile.expanded_point_ids:
            indices = [scene.point_id_to_index[point_id] for point_id in tile.expanded_point_ids]
            return scene.point_xyz[indices]
        return np.asarray(
            [
                scene.camera_centers[image_id]
                for image_id in tile.image_ids
                if image_id in scene.camera_centers
            ],
            dtype=float,
        )

    def run_segmented_training_pipeline(self) -> bool:
        input_summary = self.validate_colmap_structure(self.input_dir)
        scene = SparseScene.from_training_root(self.input_dir)
        projector, tiles, tile_summary = build_tiles(scene, self.segmented_profile)

        if len(tiles) > self.segment_max_tiles:
            raise ValueError(f"Segmenter produced {len(tiles)} tiles, exceeding max of {self.segment_max_tiles}")

        tile_root = self.temp_dir / "tiles"
        clipped_tiles = []
        tile_manifest_entries = []

        for tile in tiles:
            logger.info(
                "🧩 Tile %s: %s images, %s expanded points, %s iterations",
                tile.tile_id,
                len(tile.image_ids),
                len(tile.expanded_point_ids),
                self._resolve_tile_iterations(tile),
            )
            dataset_root = tile_root / tile.tile_id / "dataset"
            output_root = tile_root / tile.tile_id / "output"
            work_root = tile_root / tile.tile_id / "work"
            write_tile_dataset(scene, tile, dataset_root)

            raw_tile_ply = output_root / "splat.ply"
            if self.segmented_dry_run:
                centers = self._tile_centers_xyz(scene, tile)
                if centers.size == 0:
                    raise ValueError(f"Dry-run tile {tile.tile_id} has no centers for mock output")
                write_mock_gaussian_ply(
                    output_path=raw_tile_ply,
                    centers_xyz=centers,
                    count=self._dry_run_tile_count(tile, tiles),
                    seed=abs(hash(tile.tile_id)) % (2**32),
                )
            else:
                raw_tile_ply = self.train_single_scene(
                    source_input_dir=dataset_root,
                    output_dir=output_root,
                    work_dir=work_root,
                    max_iterations=self._resolve_tile_iterations(tile),
                )

            clipped_path = output_root / "splat_core.ply"
            clipped_result = clip_ply_to_bounds(
                raw_tile_ply,
                projector,
                tile.core_bounds,
                clipped_path,
                tile.tile_id,
            )
            clipped_tiles.append(clipped_result)

            tile_entry = tile.to_manifest_entry()
            tile_entry.update(
                {
                    "iterations": self._resolve_tile_iterations(tile),
                    "raw_gaussian_count": clipped_result.input_count,
                    "clipped_gaussian_count": clipped_result.clipped_count,
                }
            )
            tile_manifest_entries.append(tile_entry)

        merge_result = merge_clipped_tiles(
            clipped_tiles=clipped_tiles,
            target_total_gaussians=self.segment_target_gaussians,
            output_path=self.output_dir / "splat.ply",
        )
        if not (self.segment_target_min <= merge_result.merged_count <= self.segment_target_max):
            raise ValueError(
                f"Merged gaussian count {merge_result.merged_count:,} is outside accepted range "
                f"{self.segment_target_min:,}-{self.segment_target_max:,}"
            )

        segmentation_manifest = {
            "training_mode": "segmented",
            "profile": self.segmented_profile_name,
            "profile_settings": {
                "max_tiles": self.segment_max_tiles,
                "max_cameras_per_tile": self.segmented_profile.max_cameras_per_tile,
                "max_points_per_tile": self.segmented_profile.max_points_per_tile,
                "min_cameras_per_tile": self.segmented_profile.min_cameras_per_tile,
                "min_points_per_tile": self.segmented_profile.min_points_per_tile,
                "overlap_ratio": self.segmented_profile.overlap_ratio,
                "target_total_gaussians": self.segment_target_gaussians,
                "tile_iteration_cap": self.segment_tile_iteration_cap,
            },
            "tile_count": len(tiles),
            "input_summary": input_summary,
            "partition_summary": tile_summary,
            "tiles": tile_manifest_entries,
            "merge": {
                "pre_prune_count": merge_result.pre_prune_count,
                "merged_count": merge_result.merged_count,
                "seam_density_ratio": merge_result.seam_density_ratio,
                "tile_counts": merge_result.tile_counts,
            },
        }

        metadata = self.generate_training_metadata(
            training_mode="segmented",
            gaussian_count=merge_result.merged_count,
            input_summary=input_summary,
            segmentation_manifest=segmentation_manifest,
        )
        self.write_proof_bundle("segmented", self.output_dir / "splat.ply", metadata, segmentation_manifest)
        return True

    def cleanup_temp_files(self) -> None:
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info("🧹 Temporary files cleaned up")
        except Exception as exc:
            logger.warning(f"⚠️ Cleanup failed: {exc}")

    def run_full_training_pipeline(self) -> bool:
        logger.info("🚀 Starting training pipeline")
        logger.info(f"📅 Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        try:
            if self.training_mode == "segmented":
                success = self.run_segmented_training_pipeline()
            else:
                success = self.run_monolithic_training_pipeline()

            if success:
                logger.info("=" * 80)
                logger.info("🎉 TRAINING PIPELINE COMPLETED SUCCESSFULLY")
                logger.info(f"📁 Output directory: {self.output_dir}")
                logger.info("=" * 80)
                self.cleanup_temp_files()
            return success
        except Exception as exc:
            logger.error(f"❌ Pipeline failed with exception: {exc}")
            self.cleanup_temp_files()
            return False


def main() -> None:
    parser = argparse.ArgumentParser(description="NerfStudio 3D Gaussian Splatting Trainer")
    parser.add_argument("--config", type=str, default="/opt/ml/code/nerfstudio_config.yaml")
    parser.add_argument("train", nargs="?", help="SageMaker training argument (ignored)")
    args = parser.parse_args()

    try:
        logger.info("🚀 NerfStudio Production Training Started")
        trainer = NerfStudioTrainer(args.config)
        success = trainer.run_full_training_pipeline()
        sys.exit(0 if success else 1)
    except Exception as exc:
        logger.error(f"❌ Fatal error in training pipeline: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
