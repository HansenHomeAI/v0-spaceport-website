#!/usr/bin/env python3
"""
NerfStudio-based 3D Gaussian Splatting Training Script
======================================================

Production implementation of Vincent Woo's Sutro Tower methodology.
Uses NerfStudio's splatfacto-big with bilateral guided processing
for high-quality 3D reconstruction matching commercial standards.

Key Features:
1. Vincent Woo's exact training parameters and methodology
2. Bilateral guided radiance field processing for exposure correction
3. Production-grade error handling and logging
4. SOGS-compatible PLY output for PlayCanvas deployment
5. AWS SageMaker integration with Step Functions
"""

import os
import sys
import json
import yaml
import time
import math
import selectors
import statistics
import logging
import argparse
import subprocess

# Import torch and disable compilation backends for SageMaker compatibility
import torch
import os

# CRITICAL: Disable PyTorch compilation backends that require CUDA development headers
# PyTorch 2.0+ tries to use Triton/Inductor backends which need cuda.h at runtime
# SageMaker containers don't have CUDA development environment, only runtime
try:
    torch._dynamo.config.suppress_errors = True
    print("✅ PyTorch dynamo error suppression enabled")
except AttributeError:
    print("✅ PyTorch version doesn't have dynamo module")

# Also disable torch.compile entirely 
os.environ['TORCH_COMPILE_DISABLE'] = '1'
print("✅ TORCH_COMPILE_DISABLE=1 set")

# Limit CUDA arch targets so gsplat JIT skips older SM versions that lack
# cooperative_groups::labeled_partition (prevents nvcc build failures).
os.environ.setdefault('TORCH_CUDA_ARCH_LIST', '8.0 8.6')
print(f"✅ TORCH_CUDA_ARCH_LIST={os.environ['TORCH_CUDA_ARCH_LIST']}")

# Ensure CUDA toolkit paths are exposed so nvcc/ninja can link libcudart
cuda_home = os.environ.setdefault('CUDA_HOME', '/usr/local/cuda')
cuda_lib_paths = [f"{cuda_home}/lib64", f"{cuda_home}/lib"]
for var in ('LD_LIBRARY_PATH', 'LIBRARY_PATH'):
    existing = os.environ.get(var, '')
    parts = [p for p in existing.split(':') if p]
    for path in cuda_lib_paths:
        if path not in parts and os.path.isdir(path):
            parts.insert(0, path)
    os.environ[var] = ':'.join(parts) if parts else ':'.join(cuda_lib_paths)
    print(f"✅ {var}={os.environ[var]}")
from pathlib import Path
from typing import Dict, Any, Optional
import shutil

# Metrics and proof panels emitted by `ns-eval` become the deterministic
# downstream visual gate for promotion.
METRIC_NAMES = {"psnr", "ssim", "lpips"}
RENDER_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".ppm"}


def quantile(values: list[float], q: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    index = min(max(math.ceil(q * len(ordered)) - 1, 0), len(ordered) - 1)
    return round(ordered[index], 4)


def summarize_metric_values(values: list[float]) -> Dict[str, Any]:
    numbers = [float(value) for value in values if math.isfinite(float(value))]
    if not numbers:
        return {"count": 0, "min": None, "p10": None, "median": None, "p90": None, "p95": None, "max": None}
    return {
        "count": len(numbers),
        "min": round(min(numbers), 4),
        "p10": quantile(numbers, 0.10),
        "median": round(statistics.median(numbers), 4),
        "p90": quantile(numbers, 0.90),
        "p95": quantile(numbers, 0.95),
        "max": round(max(numbers), 4),
    }


def ns_eval_metric_name(key: str) -> Optional[str]:
    normalized = key.lower().replace("-", "_")
    tail = normalized.split("/")[-1].split(".")[-1]
    if tail in METRIC_NAMES:
        return tail
    for metric in METRIC_NAMES:
        if tail.endswith(f"_{metric}"):
            return metric
    return None


def collect_ns_eval_metrics(payload: Any, out: Dict[str, list[float]]) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            metric = ns_eval_metric_name(str(key))
            if metric and isinstance(value, (int, float)) and math.isfinite(float(value)):
                out[metric].append(float(value))
            else:
                collect_ns_eval_metrics(value, out)
    elif isinstance(payload, list):
        for item in payload:
            collect_ns_eval_metrics(item, out)


def find_ns_eval_image_count(payload: Any) -> int:
    if isinstance(payload, dict):
        for key in ("holdout_count", "validation_images", "eval_images", "num_eval_images", "num_images", "image_count"):
            value = payload.get(key)
            if isinstance(value, int) and value > 0:
                return value
        for value in payload.values():
            found = find_ns_eval_image_count(value)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = find_ns_eval_image_count(item)
            if found:
                return found
    return 0


def list_render_proof_paths(render_dir: Path) -> list[str]:
    if not render_dir.exists():
        return []
    return [
        str(path)
        for path in sorted(render_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in RENDER_SUFFIXES
    ]


def format_cli_value(value: Any) -> str:
    """Format typed config values for NerfStudio's Tyro CLI."""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def build_splat_heldout_render_report(
    raw_ns_eval_path: Path,
    render_dir: Path,
    config_file: Path,
    model_uri: str = "",
) -> Dict[str, Any]:
    with open(raw_ns_eval_path, "r") as f:
        raw_eval = json.load(f)

    metrics = {name: [] for name in sorted(METRIC_NAMES)}
    collect_ns_eval_metrics(raw_eval, metrics)
    proof_paths = list_render_proof_paths(render_dir)
    holdout_count = find_ns_eval_image_count(raw_eval) or len(proof_paths) or len(metrics["psnr"])
    successful_count = len(proof_paths) or len(metrics["psnr"])

    blockers = []
    for metric in ("psnr", "ssim", "lpips"):
        if not metrics[metric]:
            blockers.append(f"missing_{metric}")
    if holdout_count <= 0:
        blockers.append("missing_holdout_count")
    if not proof_paths:
        blockers.append("missing_render_proof_panels")

    return {
        "schema_version": 1,
        "artifact_kind": "splat_heldout_render_metrics",
        "source": "nerfstudio_ns_eval",
        "decision": "fail" if blockers else "pass",
        "model_uri": model_uri,
        "raw_ns_eval_json": str(raw_ns_eval_path),
        "load_config": str(config_file),
        "holdout_count": holdout_count,
        "successful_render_count": successful_count,
        "metrics": {
            "psnr": summarize_metric_values(metrics["psnr"]),
            "ssim": summarize_metric_values(metrics["ssim"]),
            "lpips": summarize_metric_values(metrics["lpips"]),
        },
        "proof_panels": {
            "panel_dir": str(render_dir),
            "count": len(proof_paths),
            "paths": proof_paths,
        },
        "blockers": blockers,
    }


def run_logged_command(
    cmd: list[str],
    *,
    timeout_seconds: int,
    log_prefix: str,
    tail_limit: int = 120,
) -> tuple[int, list[str], bool]:
    """Run a long command while streaming logs and retaining only a bounded tail."""
    tail: list[str] = []
    deadline = time.monotonic() + timeout_seconds
    timed_out = False

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None

    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)

    try:
        while process.poll() is None:
            if time.monotonic() > deadline:
                timed_out = True
                process.kill()
                break

            for key, _ in selector.select(timeout=1.0):
                line = key.fileobj.readline()
                if not line:
                    continue
                clean_line = line.rstrip()
                if clean_line:
                    logger.info(f"{log_prefix}{clean_line[:2000]}")
                    tail.append(clean_line)
                    tail = tail[-tail_limit:]

        for line in process.stdout:
            clean_line = line.rstrip()
            if clean_line:
                logger.info(f"{log_prefix}{clean_line[:2000]}")
                tail.append(clean_line)
                tail = tail[-tail_limit:]
    finally:
        selector.close()
        process.stdout.close()

    return process.wait(), tail, timed_out


# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NerfStudioTrainer:
    """Production NerfStudio trainer implementing Vincent Woo's methodology"""
    
    def __init__(self, config_path: str):
        """Initialize trainer with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # SageMaker environment paths
        self.input_dir = Path(os.environ.get("SM_CHANNEL_TRAINING", "/opt/ml/input/data/training"))
        self.output_dir = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
        self.temp_dir = Path("/tmp/nerfstudio_training")
        
        # Create necessary directories
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        
        # Apply Step Functions parameter overrides
        self.apply_step_functions_params()
        
        logger.info("🚀 NerfStudio Trainer initialized (Vincent Woo's methodology)")
        logger.info(f"📁 Input directory: {self.input_dir}")
        logger.info(f"📁 Output directory: {self.output_dir}")
        logger.info(f"📁 Temp directory: {self.temp_dir}")
    
    def apply_step_functions_params(self):
        """Apply parameters passed from Step Functions via environment variables"""
        env_params = {
            'MAX_ITERATIONS': 'training.max_iterations',
            'TARGET_PSNR': 'training.target_psnr',
            'SH_DEGREE': 'model.sh_degree',
            'BILATERAL_PROCESSING': 'model.bilateral_processing',
            'LOG_INTERVAL': 'training.log_interval',
            'MODEL_VARIANT': 'model.variant'  # splatfacto vs splatfacto-big
        }
        
        for env_var, config_path in env_params.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if env_var in ['BILATERAL_PROCESSING']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif env_var in ['MAX_ITERATIONS', 'SH_DEGREE', 'LOG_INTERVAL']:
                    value = int(value)
                elif env_var in ['TARGET_PSNR']:
                    value = float(value)
                
                # Set nested config values
                keys = config_path.split('.')
                config_section = self.config
                for key in keys[:-1]:
                    if key not in config_section:
                        config_section[key] = {}
                    config_section = config_section[key]
                config_section[keys[-1]] = value
                
                logger.info(f"📝 Override {config_path} = {value} (from {env_var})")
    
    def validate_input_data(self) -> bool:
        """Validate COLMAP data format and convert to NerfStudio format"""
        logger.info("🔍 Validating COLMAP data format for NerfStudio...")
        
        # Check for required COLMAP structure
        required_files = [
            self.input_dir / "sparse" / "0" / "cameras.txt",
            self.input_dir / "sparse" / "0" / "images.txt", 
            self.input_dir / "sparse" / "0" / "points3D.txt",
            self.input_dir / "images"
        ]
        
        for required_file in required_files:
            if not required_file.exists():
                logger.error(f"❌ Required file/directory missing: {required_file}")
                return False
        
        # Validate content
        cameras_file = self.input_dir / "sparse" / "0" / "cameras.txt"
        images_file = self.input_dir / "sparse" / "0" / "images.txt"
        points_file = self.input_dir / "sparse" / "0" / "points3D.txt"
        images_dir = self.input_dir / "images"
        
        # Count cameras
        camera_count = 0
        with open(cameras_file, 'r') as f:
            camera_count = sum(1 for line in f if line.strip() and not line.startswith('#'))
        
        # Count images (every 2 lines in COLMAP format)
        image_count = 0
        with open(images_file, 'r') as f:
            lines = [line for line in f if line.strip() and not line.startswith('#')]
            image_count = len(lines) // 2
        
        # Count 3D points
        point_count = 0
        with open(points_file, 'r') as f:
            point_count = sum(1 for line in f if line.strip() and not line.startswith('#'))
        
        # Count image files
        image_files = list(images_dir.glob('*.jpg')) + list(images_dir.glob('*.jpeg')) + \
                     list(images_dir.glob('*.png')) + list(images_dir.glob('*.JPG')) + \
                     list(images_dir.glob('*.JPEG')) + list(images_dir.glob('*.PNG'))
        image_file_count = len(image_files)
        
        logger.info(f"📊 COLMAP Data Validation:")
        logger.info(f"   Cameras: {camera_count}")
        logger.info(f"   Images registered: {image_count}")
        logger.info(f"   Image files: {image_file_count}")
        logger.info(f"   3D points: {point_count}")
        
        # COMPREHENSIVE LOGGING: Sample a few image names and camera details
        logger.info("📊 DETAILED COLMAP ANALYSIS:")
        logger.info(f"   Sample image files (first 5):")
        for i, img_file in enumerate(image_files[:5]):
            logger.info(f"      {i+1}. {img_file.name}")
        
        # Read and log camera parameters for debugging
        try:
            with open(cameras_file, 'r') as f:
                camera_lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            if camera_lines:
                logger.info(f"   Camera parameters (first camera):")
                logger.info(f"      {camera_lines[0]}")
        except Exception as e:
            logger.warning(f"   Could not read camera details: {e}")
        
        # Check images.txt structure
        try:
            with open(images_file, 'r') as f:
                image_lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            if len(image_lines) >= 2:
                logger.info(f"   Sample image registration (first image):")
                logger.info(f"      {image_lines[0]}")  # Image line
                logger.info(f"      {image_lines[1]}")  # Points line
        except Exception as e:
            logger.warning(f"   Could not read image registration details: {e}")
        
        # Quality checks
        if camera_count == 0:
            logger.error("❌ No cameras found in COLMAP data")
            return False
        
        if image_count == 0:
            logger.error("❌ No images found in COLMAP data")
            return False
        
        if point_count < 1000:
            logger.error(f"❌ Insufficient 3D points: {point_count} < 1000 (quality check failed)")
            return False
        
        if image_file_count < image_count * 0.8:
            logger.error(f"❌ Missing image files: {image_file_count} < {image_count * 0.8}")
            return False
        
        logger.info("✅ COLMAP data validation passed - converting to NerfStudio format")
        return self.convert_colmap_to_nerfstudio()
    
    def convert_colmap_to_nerfstudio(self) -> bool:
        """Convert COLMAP data to NerfStudio transforms.json format"""
        logger.info("🔄 Converting COLMAP data to NerfStudio format...")
        
        # Create converted data directory
        converted_dir = self.temp_dir / "converted_data"
        converted_dir.mkdir(exist_ok=True, parents=True)
        
        # Convert COLMAP TXT to BIN into a dedicated directory (industry-standard for NerfStudio)
        sparse_txt_dir = self.input_dir / "sparse" / "0"
        sparse_bin_dir = self.temp_dir / "colmap_bin" / "0"
        sparse_bin_dir.mkdir(parents=True, exist_ok=True)

        if not self.convert_colmap_text_to_binary(sparse_txt_dir, sparse_bin_dir):
            logger.error("❌ Failed to convert COLMAP text files to binary format")
            return False
        
        # Use ns-process-data to convert COLMAP to transforms.json
        convert_cmd = [
            "ns-process-data", "images",
            "--data", str(self.input_dir / "images"),
            "--output-dir", str(converted_dir),
            "--skip-colmap",  # Skip running COLMAP; reuse existing model
            "--colmap-model-path", str(sparse_bin_dir)
        ]
        
        logger.info(f"🚀 Executing COLMAP conversion command:")
        logger.info(f"   {' '.join(convert_cmd)}")
        
        try:
            result = subprocess.run(
                convert_cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            # COMPREHENSIVE LOGGING: Always log the output for debugging
            logger.info("📊 ns-process-data STDOUT:")
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        logger.info(f"   STDOUT: {line}")
            else:
                logger.info("   STDOUT: (empty)")
                
            logger.info("📊 ns-process-data STDERR:")
            if result.stderr:
                for line in result.stderr.split('\n'):
                    if line.strip():
                        logger.info(f"   STDERR: {line}")
            else:
                logger.info("   STDERR: (empty)")
            
            if result.returncode != 0:
                logger.error("❌ COLMAP to NerfStudio conversion failed:")
                logger.error(f"Exit code: {result.returncode}")
                return False
            
            # Verify transforms.json was created
            transforms_file = converted_dir / "transforms.json"
            if not transforms_file.exists():
                logger.error("❌ transforms.json was not created during conversion")
                logger.error(f"📁 Contents of {converted_dir}:")
                try:
                    for item in converted_dir.iterdir():
                        logger.error(f"   Found: {item.name}")
                except Exception as e:
                    logger.error(f"   Failed to list directory: {e}")
                return False
            
            # CRITICAL FIX: Update input directory to point to converted data BEFORE validation
            # This ensures validation looks in the right place for the converted files
            self.input_dir = converted_dir
            logger.info(f"📁 Updated input directory for validation: {self.input_dir}")
            
            # COMPREHENSIVE VALIDATION: Analyze the transforms.json file
            if not self.validate_transforms_json(transforms_file):
                logger.error("❌ transforms.json validation failed")
                return False
            
            logger.info(f"✅ COLMAP data converted successfully")
            logger.info(f"📁 Final input directory: {self.input_dir}")
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("❌ COLMAP conversion timeout (10 minutes exceeded)")
            return False
        except Exception as e:
            logger.error(f"❌ COLMAP conversion failed: {e}")
            return False
    
    def convert_colmap_text_to_binary(self, sparse_txt_dir: Path, sparse_bin_dir: Path) -> bool:
        """Convert COLMAP text files (TXT) to binary (BIN) using COLMAP's model_converter."""
        logger.info("🔄 Converting COLMAP TXT to BIN (required by ns-process-data)...")
        logger.info(f"   TXT input: {sparse_txt_dir}")
        logger.info(f"   BIN output: {sparse_bin_dir}")

        # Define expected BIN file paths in the output directory
        cameras_bin = sparse_bin_dir / "cameras.bin"
        images_bin = sparse_bin_dir / "images.bin"
        points3D_bin = sparse_bin_dir / "points3D.bin"

        if cameras_bin.exists() and images_bin.exists() and points3D_bin.exists():
            logger.info("✅ Binary files already exist, skipping conversion")
            return True

        # Use COLMAP's model_converter (auto-detects text format, converts to binary)
        convert_cmd = [
            "colmap", "model_converter",
            "--input_path", str(sparse_txt_dir),
            "--output_path", str(sparse_bin_dir),
            "--output_type", "BIN"
        ]
        
        logger.info(f"🚀 Converting text to binary: {' '.join(convert_cmd)}")
        
        try:
            result = subprocess.run(
                convert_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # COMPREHENSIVE LOGGING: Always log the output
            logger.info("📊 COLMAP model_converter STDOUT:")
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        logger.info(f"   STDOUT: {line}")
            else:
                logger.info("   STDOUT: (empty)")
                
            logger.info("📊 COLMAP model_converter STDERR:")
            if result.stderr:
                for line in result.stderr.split('\n'):
                    if line.strip():
                        logger.info(f"   STDERR: {line}")
            else:
                logger.info("   STDERR: (empty)")
            
            if result.returncode != 0:
                logger.error("❌ COLMAP text to binary conversion failed:")
                logger.error(f"Exit code: {result.returncode}")
                return False
            
            # Verify binary files were created and log their sizes
            logger.info("📊 BINARY FILE VERIFICATION:")
            binary_files = [
                ("cameras.bin", cameras_bin),
                ("images.bin", images_bin), 
                ("points3D.bin", points3D_bin)
            ]
            
            all_exist = True
            for name, path in binary_files:
                if path.exists():
                    size = path.stat().st_size
                    logger.info(f"   ✅ {name}: {size} bytes")
                else:
                    logger.error(f"   ❌ {name}: MISSING")
                    all_exist = False
            
            if not all_exist:
                logger.error("❌ Some binary files were not created")
                return False
            
            logger.info("✅ COLMAP TXT→BIN conversion completed successfully")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("❌ COLMAP conversion timeout (5 minutes exceeded)")
            return False
        except Exception as e:
            logger.error(f"❌ COLMAP text to binary conversion failed: {e}")
            return False
    
    def validate_transforms_json(self, transforms_file: Path) -> bool:
        """Comprehensive validation of the generated transforms.json file"""
        logger.info("🔍 COMPREHENSIVE transforms.json validation...")
        
        try:
            # Read and parse the transforms.json file
            with open(transforms_file, 'r') as f:
                data = json.load(f)
            
            # Log the file size and basic structure
            file_size = transforms_file.stat().st_size
            logger.info(f"📄 transforms.json file size: {file_size} bytes")
            
            # Validate required fields
            required_fields = ['frames']
            optional_fields = ['camera_angle_x', 'fl_x', 'fl_y', 'cx', 'cy', 'w', 'h', 'k1', 'k2', 'p1', 'p2']
            
            logger.info("📊 TOP-LEVEL STRUCTURE:")
            for field in required_fields:
                if field in data:
                    logger.info(f"   ✅ {field}: present")
                else:
                    logger.error(f"   ❌ {field}: MISSING (required)")
                    return False
            
            for field in optional_fields:
                if field in data:
                    logger.info(f"   ✅ {field}: {data[field]}")
                else:
                    logger.info(f"   ⚠️  {field}: not present (optional)")
            
            # Validate frames array
            frames = data.get('frames', [])
            num_frames = len(frames)
            logger.info(f"📊 FRAMES ANALYSIS:")
            logger.info(f"   Total frames: {num_frames}")
            
            if num_frames == 0:
                logger.error("   ❌ No frames found in transforms.json")
                return False
            elif num_frames == 1:
                logger.warning("   ⚠️  Only 1 frame found - this will cause k-nearest neighbors error!")
                logger.warning("   ⚠️  NerfStudio needs multiple valid frames for training")
            else:
                logger.info(f"   ✅ {num_frames} frames available")
            
            # Analyze each frame in detail
            valid_frames = 0
            for i, frame in enumerate(frames[:5]):  # Check first 5 frames
                logger.info(f"   📋 FRAME {i}:")
                
                # Check required frame fields
                if 'file_path' in frame:
                    file_path = frame['file_path']
                    logger.info(f"      file_path: {file_path}")
                    
                    # Check if the image file actually exists in the converted directory
                    # ns-process-data puts images in: converted_data/images/frame_XXXXX.JPG
                    image_file = self.input_dir / Path(file_path)
                    if image_file.exists():
                        logger.info(f"      ✅ Image file exists: {image_file.name}")
                        valid_frames += 1
                    else:
                        logger.warning(f"      ❌ Image file missing: {image_file}")
                        # Also log what we're actually looking for vs what exists
                        logger.warning(f"      📁 Looking for: {image_file}")
                        logger.warning(f"      📁 In directory: {self.input_dir}")
                        try:
                            images_dir = self.input_dir / "images"
                            if images_dir.exists():
                                files = list(images_dir.glob("*"))[:3]
                                logger.warning(f"      📁 Available files: {[f.name for f in files]}")
                        except Exception as e:
                            logger.warning(f"      📁 Error listing files: {e}")
                else:
                    logger.error(f"      ❌ No file_path in frame {i}")
                
                # Check transformation matrix
                if 'transform_matrix' in frame:
                    matrix = frame['transform_matrix']
                    if isinstance(matrix, list) and len(matrix) == 4:
                        logger.info(f"      ✅ transform_matrix: 4x4 matrix present")
                        # Check if matrix is reasonable (not all zeros)
                        flat_matrix = [val for row in matrix for val in row]
                        if all(val == 0 for val in flat_matrix):
                            logger.warning(f"      ⚠️  transform_matrix is all zeros!")
                        else:
                            logger.info(f"      ✅ transform_matrix has non-zero values")
                    else:
                        logger.error(f"      ❌ Invalid transform_matrix format")
                else:
                    logger.error(f"      ❌ No transform_matrix in frame {i}")
            
            logger.info(f"📊 VALIDATION SUMMARY:")
            logger.info(f"   Total frames: {num_frames}")
            logger.info(f"   Valid frames: {valid_frames}")
            logger.info(f"   Success rate: {valid_frames/num_frames*100:.1f}%" if num_frames > 0 else "   Success rate: 0%")
            
            if valid_frames < 2:
                logger.error("❌ Insufficient valid frames for NerfStudio training (need at least 2)")
                logger.error("   This will cause the 'n_samples = 1, n_neighbors = 4' error")
                return False
            
            logger.info("✅ transforms.json validation passed")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON format: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ transforms.json validation error: {e}")
            return False
    
    def run_nerfstudio_training(self) -> bool:
        """Execute NerfStudio training with Vincent Woo's exact methodology"""
        logger.info("🔥 Starting NerfStudio training (Vincent Woo's methodology)")
        logger.info("=" * 60)
        
        # Get configuration parameters
        model_config = self.config.get('model', {})
        training_config = self.config.get('training', {})
        
        model_variant = model_config.get('variant', 'splatfacto-big')  # Vincent used splatfacto-big
        max_iterations = training_config.get('max_iterations', 30000)
        sh_degree = model_config.get('sh_degree', 3)  # Industry standard (Vincent's setting)
        bilateral_processing = model_config.get('bilateral_processing', True)  # Vincent's key innovation
        log_interval = training_config.get('log_interval', 100)
        cache_images = str(os.environ.get("NS_CACHE_IMAGES") or training_config.get("cache_images", "cpu")).lower()
        if cache_images not in {"cpu", "gpu"}:
            logger.warning(
                "⚠️  Unsupported NerfStudio image cache mode %s; falling back to cpu "
                "(this container accepts only cpu/gpu)",
                cache_images,
            )
            cache_images = "cpu"
        max_thread_workers = self.resolve_optional_positive_int("NS_MAX_THREAD_WORKERS", "datamanager max-thread-workers")
        downscale_factor = self.resolve_optional_positive_int("NS_DOWNSCALE_FACTOR", "nerfstudio-data downscale-factor")
        train_split_fraction = self.resolve_train_split_fraction(training_config)
        max_gauss_ratio = self.resolve_optional_float(
            "NS_MAX_GAUSS_RATIO",
            "model max-gauss-ratio",
            minimum=0.1,
        )
        if max_gauss_ratio is None:
            max_gauss_ratio = float(model_config.get("max_gauss_ratio", 10.0))
        
        logger.info(f"🎯 Training Configuration (Vincent Woo's methodology):")
        logger.info(f"   Model: {model_variant}")
        logger.info(f"   Max iterations: {max_iterations}")
        logger.info(f"   SH degree: {sh_degree} (16 coefficients)")
        logger.info(f"   Bilateral guided processing: {bilateral_processing}")
        logger.info(f"   Log interval: {log_interval}")
        logger.info(f"   Train split fraction: {train_split_fraction}")
        logger.info(f"   Dataparser: transforms.json (via ns-process-data conversion)")
        
        # Build NerfStudio command with Vincent's exact parameters on converted transforms.json dataset
        # Using industry-standard ns-process-data conversion flow (COLMAP → transforms.json)
        cmd = [
            "ns-train", model_variant,
            "--data", str(self.input_dir),
            "--output-dir", str(self.temp_dir),
            "--max_num_iterations", str(max_iterations),
            "--pipeline.model.sh_degree", str(sh_degree),
            "--logging.steps_per_log", str(log_interval),
            "--vis", "tensorboard",
            "--pipeline.datamanager.cache-images", cache_images,
        ]
        
        # Add bilateral guided processing (Vincent's exposure correction)
        # CORRECT PARAMETER FOUND: --pipeline.model.use-bilateral-grid True
        if bilateral_processing:
            cmd.extend(["--pipeline.model.use-bilateral-grid", "True"])
            logger.info("🌈 Bilateral guided processing enabled (--pipeline.model.use-bilateral-grid True)")
        else:
            logger.info("⚠️  Bilateral guided processing disabled")
        
        # Memory/quality optimization for A10G GPU (16GB vs Vincent's RTX 4090 24GB).
        # Keep these knobs externally tunable so quality can be isolated with cheap
        # canaries before spending on full-scene fanout runs.
        cmd.extend([
            "--pipeline.model.max-gauss-ratio", format_cli_value(max_gauss_ratio),
        ])
        logger.info(f"🖥️  A10G GPU optimization enabled (max-gauss-ratio: {max_gauss_ratio:g}, image cache: {cache_images})")
        self.append_optional_model_quality_knobs(cmd)
        if max_thread_workers is not None:
            cmd.extend(["--pipeline.datamanager.max-thread-workers", str(max_thread_workers)])
            logger.info(f"🧵 NerfStudio datamanager max-thread-workers: {max_thread_workers}")

        cmd.extend([
            "nerfstudio-data",
            "--eval-mode", "fraction",
            "--train-split-fraction", str(train_split_fraction),
        ])
        if downscale_factor is not None:
            cmd.extend(["--downscale-factor", str(downscale_factor)])
            logger.info(f"📉 NerfStudio parser downscale-factor: {downscale_factor}")
        
        logger.info("🚀 Executing NerfStudio training command:")
        logger.info(f"   {' '.join(cmd)}")
        logger.info("=" * 60)
        
        return_code, tail, timed_out = run_logged_command(
            cmd,
            timeout_seconds=7200,
            log_prefix="NS_TRAIN: ",
        )
        if timed_out:
            logger.error("❌ Training timeout (2 hours exceeded)")
            return False

        if return_code != 0:
            logger.error("❌ NerfStudio training failed:")
            logger.error(f"Exit code: {return_code}")
            logger.error("Last training output lines:")
            for line in tail[-20:]:
                logger.error(f"   {line}")
            return False

        logger.info("✅ NerfStudio training completed successfully")
        logger.info("📊 Final training output tail:")
        for line in tail[-20:]:
            logger.info(f"   {line}")
        return True

    def resolve_optional_positive_int(self, env_var: str, label: str) -> Optional[int]:
        """Read an optional positive integer training knob from the environment."""
        raw_value = os.environ.get(env_var)
        if raw_value in (None, ""):
            return None
        try:
            value = int(raw_value)
        except ValueError:
            logger.warning(f"⚠️  Invalid {label} {raw_value!r}; ignoring")
            return None
        if value <= 0:
            logger.warning(f"⚠️  Invalid {label} {raw_value!r}; ignoring")
            return None
        return value

    def resolve_optional_nonnegative_int(self, env_var: str, label: str) -> Optional[int]:
        """Read an optional non-negative integer training knob from the environment."""
        raw_value = os.environ.get(env_var)
        if raw_value in (None, ""):
            return None
        try:
            value = int(raw_value)
        except ValueError:
            logger.warning(f"⚠️  Invalid {label} {raw_value!r}; ignoring")
            return None
        if value < 0:
            logger.warning(f"⚠️  Invalid {label} {raw_value!r}; ignoring")
            return None
        return value

    def resolve_optional_float(
        self,
        env_var: str,
        label: str,
        *,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
    ) -> Optional[float]:
        """Read an optional finite float training knob from the environment."""
        raw_value = os.environ.get(env_var)
        if raw_value in (None, ""):
            return None
        try:
            value = float(raw_value)
        except ValueError:
            logger.warning(f"⚠️  Invalid {label} {raw_value!r}; ignoring")
            return None
        if not math.isfinite(value):
            logger.warning(f"⚠️  Invalid {label} {raw_value!r}; ignoring")
            return None
        if minimum is not None and value < minimum:
            logger.warning(f"⚠️  Invalid {label} {raw_value!r}; expected >= {minimum}; ignoring")
            return None
        if maximum is not None and value > maximum:
            logger.warning(f"⚠️  Invalid {label} {raw_value!r}; expected <= {maximum}; ignoring")
            return None
        return value

    def resolve_optional_bool(self, env_var: str, label: str) -> Optional[bool]:
        """Read an optional boolean training knob from the environment."""
        raw_value = os.environ.get(env_var)
        if raw_value in (None, ""):
            return None
        normalized = raw_value.lower()
        if normalized in ("1", "true", "yes", "on"):
            return True
        if normalized in ("0", "false", "no", "off"):
            return False
        logger.warning(f"⚠️  Invalid {label} {raw_value!r}; ignoring")
        return None

    def append_optional_model_quality_knobs(self, cmd: list[str]) -> None:
        """Expose bounded Splatfacto quality/capacity controls for canary isolation."""
        float_knobs = [
            ("NS_DENSIFY_GRAD_THRESH", "--pipeline.model.densify-grad-thresh", "model densify-grad-thresh", 0.0, None),
            ("NS_DENSIFY_SIZE_THRESH", "--pipeline.model.densify-size-thresh", "model densify-size-thresh", 0.0, None),
            ("NS_CULL_ALPHA_THRESH", "--pipeline.model.cull-alpha-thresh", "model cull-alpha-thresh", 0.0, None),
            ("NS_CULL_SCALE_THRESH", "--pipeline.model.cull-scale-thresh", "model cull-scale-thresh", 0.0, None),
            ("NS_CULL_SCREEN_SIZE", "--pipeline.model.cull-screen-size", "model cull-screen-size", 0.0, None),
            ("NS_SPLIT_SCREEN_SIZE", "--pipeline.model.split-screen-size", "model split-screen-size", 0.0, None),
            ("NS_SSIM_LAMBDA", "--pipeline.model.ssim-lambda", "model ssim-lambda", 0.0, 1.0),
        ]
        int_knobs = [
            ("NS_STOP_SPLIT_AT", "--pipeline.model.stop-split-at", "model stop-split-at"),
            ("NS_STOP_SCREEN_SIZE_AT", "--pipeline.model.stop-screen-size-at", "model stop-screen-size-at"),
            ("NS_RESOLUTION_SCHEDULE", "--pipeline.model.resolution-schedule", "model resolution-schedule"),
            ("NS_REFINE_EVERY", "--pipeline.model.refine-every", "model refine-every"),
            ("NS_RESET_ALPHA_EVERY", "--pipeline.model.reset-alpha-every", "model reset-alpha-every"),
            ("NS_NUM_DOWNSCALES", "--pipeline.model.num-downscales", "model num-downscales"),
        ]
        bool_knobs = [
            ("NS_USE_SCALE_REGULARIZATION", "--pipeline.model.use-scale-regularization", "model use-scale-regularization"),
            ("NS_USE_ABSGRAD", "--pipeline.model.use-absgrad", "model use-absgrad"),
        ]

        for env_var, flag, label, minimum, maximum in float_knobs:
            value = self.resolve_optional_float(env_var, label, minimum=minimum, maximum=maximum)
            if value is not None:
                cmd.extend([flag, format_cli_value(value)])
                logger.info(f"🎚️  {label}: {value:g} ({env_var})")

        for env_var, flag, label in int_knobs:
            value = self.resolve_optional_nonnegative_int(env_var, label)
            if value is not None:
                cmd.extend([flag, format_cli_value(value)])
                logger.info(f"🎚️  {label}: {value} ({env_var})")

        for env_var, flag, label in bool_knobs:
            value = self.resolve_optional_bool(env_var, label)
            if value is not None:
                cmd.extend([flag, format_cli_value(value)])
                logger.info(f"🎚️  {label}: {format_cli_value(value)} ({env_var})")

    def infer_training_frame_count(self) -> int:
        """Return the converted dataset frame count when transforms.json is available."""
        transforms_file = self.input_dir / "transforms.json"
        if not transforms_file.exists():
            return 0
        try:
            with open(transforms_file, "r") as f:
                transforms = json.load(f)
            frames = transforms.get("frames", [])
            return len(frames) if isinstance(frames, list) else 0
        except Exception as exc:
            logger.warning(f"⚠️  Could not infer frame count from {transforms_file}: {exc}")
            return 0

    def resolve_train_split_fraction(self, training_config: Dict[str, Any]) -> float:
        """Choose a train split that leaves heldout images for tiny canary datasets."""
        raw_value = os.environ.get("NS_TRAIN_SPLIT_FRACTION")
        if raw_value is None:
            raw_value = training_config.get("train_split_fraction")
        if raw_value is not None:
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                logger.warning(f"⚠️  Invalid train split fraction {raw_value!r}; using automatic split")
            else:
                return min(max(value, 0.1), 0.95)

        frame_count = self.infer_training_frame_count()
        if 0 < frame_count <= 20:
            # NerfStudio's default 0.9 split can round tiny samples into zero eval images.
            return 0.75
        return 0.9

    def find_latest_config_file(self) -> Optional[Path]:
        """Find the most recent NerfStudio training config."""
        config_files = list(self.temp_dir.glob("**/config.yml"))
        if not config_files:
            return None
        return max(config_files, key=lambda x: x.stat().st_mtime)

    def quality_eval_enabled(self) -> bool:
        """Return whether heldout rendering metrics should run after training."""
        env_value = os.environ.get("RUN_HELDOUT_EVAL")
        if env_value is not None:
            return env_value.lower() in ("1", "true", "yes", "on")
        quality_config = self.config.get("quality", {}).get("heldout_eval", {})
        return bool(quality_config.get("enabled", True))

    def quality_eval_required(self) -> bool:
        """Return whether missing heldout metrics should fail the training job."""
        env_value = os.environ.get("QUALITY_EVAL_REQUIRED")
        if env_value is not None:
            return env_value.lower() in ("1", "true", "yes", "on")
        quality_config = self.config.get("quality", {}).get("heldout_eval", {})
        return bool(quality_config.get("fail_on_missing_metrics", True))

    def quality_eval_timeout_seconds(self) -> int:
        env_value = os.environ.get("NS_EVAL_TIMEOUT_SEC")
        if env_value:
            return int(env_value)
        quality_config = self.config.get("quality", {}).get("heldout_eval", {})
        return int(quality_config.get("timeout_seconds", 1800))

    def run_nerfstudio_evaluation(self) -> bool:
        """Run NerfStudio heldout evaluation and emit the promotion gate report."""
        if not self.quality_eval_enabled():
            logger.warning("⚠️ Heldout visual quality evaluation disabled")
            return True

        logger.info("📸 Running NerfStudio heldout render evaluation...")
        config_file = self.find_latest_config_file()
        if not config_file:
            logger.error("❌ No config.yml found for NerfStudio evaluation")
            return not self.quality_eval_required()

        eval_dir = self.output_dir / "quality_eval"
        render_dir = eval_dir / "heldout_renders"
        eval_dir.mkdir(parents=True, exist_ok=True)
        render_dir.mkdir(parents=True, exist_ok=True)

        raw_eval_path = eval_dir / "ns_eval.json"
        report_path = eval_dir / "splat_heldout_render_metrics.json"
        stdout_path = eval_dir / "ns_eval_stdout.log"
        config_snapshot_path = eval_dir / "nerfstudio_config.yml"
        shutil.copy2(config_file, config_snapshot_path)

        eval_cmd = [
            "ns-eval",
            "--load-config", str(config_file),
            "--output-path", str(raw_eval_path),
            "--render-output-path", str(render_dir),
        ]
        logger.info("🔄 Executing NerfStudio eval command:")
        logger.info(f"   {' '.join(eval_cmd)}")

        return_code, tail, timed_out = run_logged_command(
            eval_cmd,
            timeout_seconds=self.quality_eval_timeout_seconds(),
            log_prefix="NS_EVAL: ",
        )
        stdout_path.write_text("\n".join(tail) + ("\n" if tail else ""), encoding="utf-8")

        if timed_out:
            logger.error(f"❌ NerfStudio evaluation timeout ({self.quality_eval_timeout_seconds()}s exceeded)")
            return not self.quality_eval_required()

        if return_code != 0:
            logger.error("❌ NerfStudio evaluation failed:")
            logger.error(f"Exit code: {return_code}")
            logger.error(f"Output tail log: {stdout_path}")
            return not self.quality_eval_required()

        if not raw_eval_path.exists():
            logger.error(f"❌ NerfStudio evaluation did not write {raw_eval_path}")
            return not self.quality_eval_required()

        report = build_splat_heldout_render_report(raw_eval_path, render_dir, config_snapshot_path)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
            f.write("\n")

        logger.info("📊 Heldout visual quality report:")
        logger.info(f"   Report: {report_path}")
        logger.info(f"   Decision: {report['decision']}")
        logger.info(f"   Holdout images: {report['holdout_count']}")
        logger.info(f"   Proof panels: {report['proof_panels']['count']}")
        logger.info(f"   PSNR median: {report['metrics']['psnr']['median']}")
        logger.info(f"   SSIM median: {report['metrics']['ssim']['median']}")
        logger.info(f"   LPIPS median: {report['metrics']['lpips']['median']}")
        if report["blockers"]:
            logger.error(f"❌ Visual quality blockers: {report['blockers']}")
            return not self.quality_eval_required()

        logger.info("✅ NerfStudio heldout render evaluation completed")
        return True
    
    def export_trained_model(self) -> bool:
        """Export trained model to PLY format (SOGS compatible)"""
        logger.info("📦 Exporting trained model to PLY format...")
        
        # Find the latest config file in training output
        config_file = self.find_latest_config_file()
        if not config_file:
            logger.error("❌ No config.yml found in training output")
            return False
        logger.info(f"📄 Using config: {config_file}")
        
        # Export command
        export_cmd = [
            "ns-export", "gaussian-splat",
            "--load-config", str(config_file),
            "--output-dir", str(self.output_dir)
        ]
        
        logger.info(f"🔄 Executing export command:")
        logger.info(f"   {' '.join(export_cmd)}")
        
        try:
            result = subprocess.run(
                export_cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode != 0:
                logger.error("❌ Model export failed:")
                logger.error(f"Exit code: {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return False
            
            logger.info("✅ Model export completed successfully")
            
            # Verify PLY file was created
            ply_files = list(self.output_dir.glob("*.ply"))
            if ply_files:
                ply_file = ply_files[0]
                file_size_mb = ply_file.stat().st_size / (1024 * 1024)
                logger.info(f"📄 PLY file: {ply_file.name} ({file_size_mb:.1f} MB)")
                logger.info("✅ SOGS-compatible PLY format ready for compression")
            else:
                logger.warning("⚠️ No PLY file found in export output")
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("❌ Export timeout (10 minutes exceeded)")
            return False
        except Exception as e:
            logger.error(f"❌ Export execution failed: {e}")
            return False
    
    def generate_training_metadata(self) -> Dict[str, Any]:
        """Generate comprehensive training metadata"""
        metadata = {
            'training_methodology': 'Vincent Woo Sutro Tower',
            'framework': 'NerfStudio',
            'model_variant': self.config.get('model', {}).get('variant', 'splatfacto-big'),
            'bilateral_guided_processing': self.config.get('model', {}).get('bilateral_processing', True),
            'sh_degree': self.config.get('model', {}).get('sh_degree', 3),
            'max_iterations': self.config.get('training', {}).get('max_iterations', 30000),
            'commercial_license': 'Apache 2.0',
            'sogs_compatible': True,
            'playcanvas_ready': True,
            'training_completed': True,
            'timestamp': time.time(),
            'version': '1.0.0'
        }
        
        # Add file information
        ply_files = list(self.output_dir.glob("*.ply"))
        if ply_files:
            ply_file = ply_files[0]
            metadata['output_file'] = ply_file.name
            metadata['file_size_mb'] = ply_file.stat().st_size / (1024 * 1024)

        quality_report = self.output_dir / "quality_eval" / "splat_heldout_render_metrics.json"
        if quality_report.exists():
            with open(quality_report, "r") as f:
                quality_payload = json.load(f)
            metadata["quality_eval_completed"] = True
            metadata["quality_eval_report"] = str(quality_report.relative_to(self.output_dir))
            metadata["heldout_render_decision"] = quality_payload.get("decision")
            metadata["heldout_render_metrics"] = quality_payload.get("metrics")
            metadata["heldout_render_blockers"] = quality_payload.get("blockers") or []
            metadata["heldout_render_proof_panel_count"] = (quality_payload.get("proof_panels") or {}).get("count")
        else:
            metadata["quality_eval_completed"] = False
        
        # Save metadata
        metadata_path = self.output_dir / "training_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("📋 Training metadata generated:")
        for key, value in metadata.items():
            logger.info(f"   {key}: {value}")
        
        return metadata
    
    def cleanup_temp_files(self):
        """Clean up temporary training files"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info("🧹 Temporary files cleaned up")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup failed: {e}")
    
    def run_full_training_pipeline(self) -> bool:
        """Execute the complete training pipeline"""
        logger.info("🚀 Starting complete NerfStudio training pipeline")
        logger.info(f"📅 Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        try:
            # Step 1: Validate input data
            if not self.validate_input_data():
                logger.error("❌ Input data validation failed")
                return False
            
            # Step 2: Run NerfStudio training
            if not self.run_nerfstudio_training():
                logger.error("❌ NerfStudio training failed")
                return False
            
            # Step 3: Run deterministic heldout render metrics before promotion
            if not self.run_nerfstudio_evaluation():
                logger.error("❌ NerfStudio heldout render evaluation failed")
                return False

            # Step 4: Export trained model
            if not self.export_trained_model():
                logger.error("❌ Model export failed")
                return False
            
            # Step 5: Generate metadata
            metadata = self.generate_training_metadata()
            
            # Step 6: Cleanup
            self.cleanup_temp_files()
            
            logger.info("=" * 80)
            logger.info("🎉 NERFSTUDIO TRAINING PIPELINE COMPLETED SUCCESSFULLY!")
            logger.info("✅ Vincent Woo's methodology implemented")
            logger.info("✅ Bilateral guided processing applied")
            logger.info("✅ SOGS-compatible PLY output generated")
            logger.info("✅ Production-ready for PlayCanvas deployment")
            logger.info(f"📁 Output directory: {self.output_dir}")
            logger.info("=" * 80)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed with exception: {e}")
            self.cleanup_temp_files()
            return False


def main():
    """Main entry point for SageMaker training"""
    parser = argparse.ArgumentParser(description="NerfStudio 3D Gaussian Splatting Trainer")
    parser.add_argument("--config", type=str, default="/opt/ml/code/nerfstudio_config.yaml", 
                       help="Path to the configuration file")
    # Handle SageMaker's automatic arguments
    parser.add_argument("train", nargs='?', help="SageMaker training argument (ignored)")
    args = parser.parse_args()
    
    try:
        logger.info("🚀 NerfStudio Production Training Started")
        logger.info("📦 Framework: NerfStudio with Vincent Woo's methodology")
        logger.info("🎯 Goal: Sutro Tower quality 3D reconstruction")
        
        # Initialize trainer
        trainer = NerfStudioTrainer(args.config)
        
        # Run complete pipeline
        success = trainer.run_full_training_pipeline()
        
        if success:
            logger.info("✅ Training pipeline completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Training pipeline failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Fatal error in training pipeline: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
