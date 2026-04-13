#!/usr/bin/env python3
"""
NerfStudio-based 3D Gaussian Splatting Training Script
======================================================

Production implementation of Vincent Woo's Sutro Tower methodology.
Uses NerfStudio with splatfacto-w-light for high-quality foreground splats
plus a lightweight learned background that we bake into the final viewer
skybox.

Key Features:
1. Vincent Woo's exact training parameters and methodology
2. Bilateral guided radiance field processing for exposure correction
3. Production-grade error handling and logging
4. SOGS-compatible PLY output plus baked skybox for PlayCanvas deployment
5. AWS SageMaker integration with Step Functions
"""

import os
import sys
import json
import yaml
import time
import hashlib
import logging
import argparse
import subprocess

# Force modern CUDA targets before torch/cpp_extension is imported anywhere.
os.environ.setdefault('TORCH_CUDA_ARCH_LIST', '7.0;8.0;8.6+PTX')
os.environ.setdefault('CUDAARCHS', '70;80;86')

# Import torch and disable compilation backends for SageMaker compatibility
import torch

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
print(f"✅ TORCH_CUDA_ARCH_LIST={os.environ['TORCH_CUDA_ARCH_LIST']}")
print(f"✅ CUDAARCHS={os.environ['CUDAARCHS']}")

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

from sky_quality import (
    BackgroundSelectionResult,
    FloaterPruningResult,
    prune_foreground_floaters,
    select_background_camera,
)
from tile_pipeline import (
    filter_transforms_frames,
    load_json,
    merge_tile_outputs,
    selection_counts_for_buckets,
    select_manifest_tile_ids,
    select_training_image_names,
    subset_tile_manifest,
)

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_colmap_image_id_name_map(images_txt: Path) -> dict[str, str]:
    """Map COLMAP image ids to original image names from images.txt."""
    mapping: dict[str, str] = {}
    if not images_txt.exists():
        return mapping

    with open(images_txt, 'r', encoding='utf-8') as handle:
        lines = handle.readlines()

    line_index = 0
    while line_index < len(lines):
        line = lines[line_index].strip()
        if not line or line.startswith('#'):
            line_index += 1
            continue
        parts = line.split()
        if len(parts) >= 10:
            mapping[str(int(parts[0]))] = parts[9]
            line_index += 2
        else:
            line_index += 1
    return mapping


def build_converted_image_name_map(
    transforms: Dict[str, Any],
    original_images_txt: Path,
) -> dict[str, Any]:
    """Persist a stable mapping from original COLMAP image names to converted frame files."""
    colmap_name_map = load_colmap_image_id_name_map(original_images_txt)
    by_colmap_im_id: dict[str, dict[str, Any]] = {}
    by_converted_name: dict[str, dict[str, Any]] = {}
    by_original_name: dict[str, dict[str, Any]] = {}

    for frame in transforms.get('frames', []):
        colmap_im_id = frame.get('colmap_im_id')
        file_path = str(frame.get('file_path', '')).strip()
        if not file_path or colmap_im_id is None:
            continue

        image_id = str(colmap_im_id)
        original_image_name = colmap_name_map.get(image_id)
        if not original_image_name:
            continue

        converted_name = Path(file_path).name
        entry = {
            'colmap_im_id': int(colmap_im_id),
            'original_image_name': original_image_name,
            'converted_file_path': file_path,
            'converted_image_name': converted_name,
        }
        by_colmap_im_id[image_id] = entry
        by_converted_name[converted_name] = entry
        by_original_name[Path(original_image_name).name] = entry

    return {
        'version': 1,
        'image_count': len(by_colmap_im_id),
        'by_colmap_im_id': by_colmap_im_id,
        'by_converted_name': by_converted_name,
        'by_original_name': by_original_name,
    }

class NerfStudioTrainer:
    """Production NerfStudio trainer implementing Vincent Woo's methodology"""
    
    def __init__(self, config_path: str):
        """Initialize trainer with configuration"""
        self.config_path = config_path
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # SageMaker environment paths
        self.input_dir = Path(os.environ.get("SM_CHANNEL_TRAINING", "/opt/ml/input/data/training"))
        self.output_dir = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
        self.temp_dir = Path("/tmp/nerfstudio_training")
        
        # Create necessary directories
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        self.background_selection_result: Optional[BackgroundSelectionResult] = None
        self.floater_pruning_result: Optional[FloaterPruningResult] = None
        self.training_selection_result: Optional[Dict[str, Any]] = None
        
        # Apply Step Functions parameter overrides
        self.apply_step_functions_params()
        
        logger.info("🚀 NerfStudio Trainer initialized (Spaceport splatfacto-w-light)")
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
            'MODEL_VARIANT': 'model.variant',
            'RASTERIZE_MODE': 'model.rasterize_mode',
            'USE_SCALE_REGULARIZATION': 'model.use_scale_regularization',
            'CULL_ALPHA_THRESH': 'model.cull_alpha_thresh',
            'CULL_SCALE_THRESH': 'model.cull_scale_thresh',
            'ENABLE_BG_MODEL': 'model.enable_bg_model',
            'ENABLE_ALPHA_LOSS': 'model.enable_alpha_loss',
            'ENABLE_ROBUST_MASK': 'model.enable_robust_mask',
            'BG_SH_DEGREE': 'model.bg_sh_degree',
            'APPEARANCE_EMBED_DIM': 'model.appearance_embed_dim',
            'NEVER_MASK_UPPER': 'model.never_mask_upper',
            'BACKGROUND_APPEARANCE_MODE': 'output.background_skybox.appearance_mode',
            'BACKGROUND_SKYBOX_WIDTH': 'output.background_skybox.width',
            'BACKGROUND_SKYBOX_HEIGHT': 'output.background_skybox.height',
            'BACKGROUND_SKYBOX_QUALITY': 'output.background_skybox.quality',
            'BACKGROUND_SELECTION_STRIDE': 'output.background_skybox.selection_stride',
            'BACKGROUND_SELECTION_MAX_FRAMES': 'output.background_skybox.selection_max_frames',
            'FLOATER_PRUNING_ENABLED': 'output.floater_pruning.enabled',
            'FLOATER_PRUNING_MIN_VIEWS': 'output.floater_pruning.min_views',
            'FLOATER_PRUNING_TOP_REGION_RATIO': 'output.floater_pruning.top_region_ratio',
            'FLOATER_PRUNING_TOP_VIEW_FRACTION': 'output.floater_pruning.top_view_fraction',
            'FLOATER_PRUNING_MIN_SKY_VIEWS': 'output.floater_pruning.min_sky_views',
            'FLOATER_PRUNING_SKY_MIN_LUMINANCE': 'output.floater_pruning.sky_min_luminance',
            'FLOATER_PRUNING_SKY_MIN_SATURATION': 'output.floater_pruning.sky_min_saturation',
            'FLOATER_PRUNING_SKY_BLUE_DOMINANCE_MARGIN': 'output.floater_pruning.sky_blue_dominance_margin',
            'FLOATER_PRUNING_MAX_OPACITY': 'output.floater_pruning.max_opacity',
            'FLOATER_PRUNING_MAX_COLOR_DISTANCE': 'output.floater_pruning.max_color_distance',
            'FLOATER_PRUNING_MIN_EDGE_SUPPORT': 'output.floater_pruning.min_edge_support',
            'TRAINING_MODE': 'tiling.training_mode',
            'TILE_MANIFEST_PATH': 'tiling.tile_manifest_path',
            'VIEW_BUCKET_MANIFEST_PATH': 'tiling.view_bucket_manifest_path',
            'TILE_ID': 'tiling.tile_id',
            'MERGE_MODE': 'tiling.merge.mode',
            'GLOBAL_SCAFFOLD_MAX_IMAGES': 'tiling.global_scaffold.max_images',
            'GLOBAL_SCAFFOLD_FRAME_STRIDE': 'tiling.global_scaffold.frame_stride',
            'GLOBAL_SCAFFOLD_MAX_ITERATIONS': 'tiling.global_scaffold.max_iterations',
            'GLOBAL_SCAFFOLD_SH_DEGREE': 'tiling.global_scaffold.sh_degree',
            'GLOBAL_SCAFFOLD_MAX_GAUSS_RATIO': 'tiling.global_scaffold.max_gauss_ratio',
            'TILED_MAX_TILES': 'tiling.pipeline.max_tiles',
            'TILED_TILE_IDS': 'tiling.pipeline.tile_ids',
            'TILED_INCLUDE_SCAFFOLD': 'tiling.pipeline.include_scaffold',
            'TILED_INCLUDE_MERGE': 'tiling.pipeline.include_merge',
            'TILED_RESUME_EXISTING': 'tiling.pipeline.resume_existing',
        }
        
        for env_var, config_path in env_params.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if env_var in ['BILATERAL_PROCESSING', 'USE_SCALE_REGULARIZATION', 'ENABLE_BG_MODEL', 'ENABLE_ALPHA_LOSS', 'ENABLE_ROBUST_MASK', 'FLOATER_PRUNING_ENABLED', 'TILED_INCLUDE_SCAFFOLD', 'TILED_INCLUDE_MERGE', 'TILED_RESUME_EXISTING']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif env_var in ['MAX_ITERATIONS', 'SH_DEGREE', 'LOG_INTERVAL', 'BG_SH_DEGREE', 'APPEARANCE_EMBED_DIM', 'BACKGROUND_SKYBOX_WIDTH', 'BACKGROUND_SKYBOX_HEIGHT', 'BACKGROUND_SKYBOX_QUALITY', 'BACKGROUND_SELECTION_STRIDE', 'BACKGROUND_SELECTION_MAX_FRAMES', 'FLOATER_PRUNING_MIN_VIEWS', 'FLOATER_PRUNING_MIN_SKY_VIEWS', 'FLOATER_PRUNING_MIN_EDGE_SUPPORT', 'GLOBAL_SCAFFOLD_MAX_IMAGES', 'GLOBAL_SCAFFOLD_FRAME_STRIDE', 'GLOBAL_SCAFFOLD_MAX_ITERATIONS', 'GLOBAL_SCAFFOLD_SH_DEGREE', 'TILED_MAX_TILES']:
                    value = int(value)
                elif env_var in ['TARGET_PSNR', 'CULL_ALPHA_THRESH', 'CULL_SCALE_THRESH', 'NEVER_MASK_UPPER', 'FLOATER_PRUNING_TOP_REGION_RATIO', 'FLOATER_PRUNING_TOP_VIEW_FRACTION', 'FLOATER_PRUNING_SKY_MIN_LUMINANCE', 'FLOATER_PRUNING_SKY_MIN_SATURATION', 'FLOATER_PRUNING_SKY_BLUE_DOMINANCE_MARGIN', 'FLOATER_PRUNING_MAX_OPACITY', 'FLOATER_PRUNING_MAX_COLOR_DISTANCE', 'GLOBAL_SCAFFOLD_MAX_GAUSS_RATIO']:
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
        source_input_dir = self.input_dir
        
        # Create converted data directory
        converted_dir = self.temp_dir / "converted_data"
        if converted_dir.exists():
            shutil.rmtree(converted_dir)
        converted_dir.mkdir(exist_ok=True, parents=True)
        
        # Convert COLMAP TXT to BIN into a dedicated directory (industry-standard for NerfStudio)
        sparse_txt_dir = self.input_dir / "sparse" / "0"
        sparse_bin_dir = self.temp_dir / "colmap_bin" / "0"
        if sparse_bin_dir.parent.exists():
            shutil.rmtree(sparse_bin_dir.parent)
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

            try:
                with open(transforms_file, 'r', encoding='utf-8') as f:
                    transforms_payload = json.load(f)
                image_name_map = build_converted_image_name_map(
                    transforms_payload,
                    source_input_dir / "sparse" / "0" / "images.txt",
                )
                image_name_map_path = converted_dir / "colmap_image_name_map.json"
                with open(image_name_map_path, 'w', encoding='utf-8') as f:
                    json.dump(image_name_map, f, indent=2)
                logger.info(
                    "🗺️ Saved converted image name map with %s entries",
                    image_name_map.get('image_count', 0),
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to save converted image name map: {e}")
            
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

    def resolve_training_mode(self) -> str:
        return str(self.config.get('tiling', {}).get('training_mode', 'monolithic')).strip().lower() or 'monolithic'

    def load_tile_selection_inputs(self) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        tiling_config = self.config.get('tiling', {})
        tile_manifest_path = str(tiling_config.get('tile_manifest_path', '')).strip()
        view_bucket_manifest_path = str(tiling_config.get('view_bucket_manifest_path', '')).strip()

        def resolve_input_path(raw_path: str) -> Path | None:
            if not raw_path:
                return None
            candidate = Path(raw_path)
            if candidate.is_absolute():
                return candidate
            return self.input_dir / candidate

        tile_manifest_resolved = resolve_input_path(tile_manifest_path)
        view_bucket_manifest_resolved = resolve_input_path(view_bucket_manifest_path)
        tile_manifest = load_json(tile_manifest_resolved) if tile_manifest_resolved else None
        view_buckets = load_json(view_bucket_manifest_resolved) if view_bucket_manifest_resolved else None
        return tile_manifest, view_buckets

    def resolve_tiled_pipeline_options(self, tile_manifest: dict[str, Any]) -> dict[str, Any]:
        tiling_config = self.config.get('tiling', {})
        pipeline_config = tiling_config.get('pipeline', {})
        raw_tile_ids = pipeline_config.get('tile_ids', '')
        if isinstance(raw_tile_ids, str):
            explicit_tile_ids = [value.strip() for value in raw_tile_ids.split(',') if value.strip()]
        elif isinstance(raw_tile_ids, list):
            explicit_tile_ids = [str(value).strip() for value in raw_tile_ids if str(value).strip()]
        else:
            explicit_tile_ids = []
        max_tiles = int(pipeline_config.get('max_tiles', 0) or 0)
        selected_tile_ids = select_manifest_tile_ids(
            tile_manifest,
            explicit_tile_ids=explicit_tile_ids,
            max_tiles=max_tiles or None,
        )
        return {
            'selected_tile_ids': selected_tile_ids,
            'include_scaffold': bool(pipeline_config.get('include_scaffold', True)),
            'include_merge': bool(pipeline_config.get('include_merge', True)),
            'resume_existing': bool(pipeline_config.get('resume_existing', True)),
        }

    def resolve_source_input_path(self, source_root: Path, raw_path: str, default_name: str) -> Path:
        candidate = Path(raw_path.strip()) if raw_path.strip() else Path(default_name)
        return candidate if candidate.is_absolute() else source_root / candidate

    @staticmethod
    def build_resume_fingerprint(payload: Dict[str, Any]) -> str:
        normalized = json.dumps(payload, sort_keys=True, default=str).encode('utf-8')
        return hashlib.sha256(normalized).hexdigest()

    @staticmethod
    def resume_artifacts_present(stage_output_dir: Path, summary_payload: Dict[str, Any]) -> bool:
        metadata_path = stage_output_dir / "training_metadata.json"
        if not metadata_path.exists():
            return False
        training_metadata = summary_payload.get('training_metadata') or {}
        output_file = str(training_metadata.get('output_file', '')).strip()
        if output_file and not (stage_output_dir / output_file).exists():
            return False
        return True

    def prepare_tiled_stage_dataset(
        self,
        *,
        canonical_input_dir: Path,
        stage_input_dir: Path,
        tile_manifest: dict[str, Any],
        view_buckets: dict[str, Any],
        tile_manifest_name: str,
        view_bucket_name: str,
    ) -> None:
        if stage_input_dir.exists():
            shutil.rmtree(stage_input_dir)
        stage_input_dir.mkdir(parents=True, exist_ok=True)

        canonical_images_dir = canonical_input_dir / "images"
        if canonical_images_dir.exists():
            os.symlink(canonical_images_dir, stage_input_dir / "images")

        transforms_source = canonical_input_dir / "transforms.full.json"
        if not transforms_source.exists():
            transforms_source = canonical_input_dir / "transforms.json"
        shutil.copy2(transforms_source, stage_input_dir / "transforms.json")
        image_name_map_source = canonical_input_dir / "colmap_image_name_map.json"
        if image_name_map_source.exists():
            shutil.copy2(image_name_map_source, stage_input_dir / "colmap_image_name_map.json")

        with open(stage_input_dir / tile_manifest_name, 'w', encoding='utf-8') as f:
            json.dump(tile_manifest, f, indent=2)
        with open(stage_input_dir / view_bucket_name, 'w', encoding='utf-8') as f:
            json.dump(view_buckets, f, indent=2)

    def run_prepared_training_stage(
        self,
        *,
        stage_name: str,
        stage_input_dir: Path,
        stage_output_dir: Path,
        stage_temp_dir: Path,
        training_mode: str,
        tile_id: str | None = None,
        resume_existing: bool = True,
        resume_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        original_input_dir = self.input_dir
        original_output_dir = self.output_dir
        original_temp_dir = self.temp_dir
        tiling_config = self.config.setdefault('tiling', {})
        original_training_mode = tiling_config.get('training_mode', 'monolithic')
        original_tile_id = tiling_config.get('tile_id', '')

        started_at = time.time()
        try:
            stage_summary_path = stage_output_dir / "stage_summary.json"
            if resume_existing and stage_summary_path.exists():
                with open(stage_summary_path, 'r', encoding='utf-8') as f:
                    cached_summary = json.load(f)
                cached_fingerprint = str(cached_summary.get('resume_fingerprint', ''))
                if (
                    resume_fingerprint
                    and cached_fingerprint == resume_fingerprint
                    and self.resume_artifacts_present(stage_output_dir, cached_summary)
                ):
                    return cached_summary

            self.input_dir = stage_input_dir
            self.output_dir = stage_output_dir
            self.temp_dir = stage_temp_dir
            if self.output_dir.exists():
                shutil.rmtree(self.output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            tiling_config['training_mode'] = training_mode
            tiling_config['tile_id'] = tile_id or ""
            self.background_selection_result = None
            self.floater_pruning_result = None
            self.training_selection_result = None

            if not self.apply_training_selection():
                raise RuntimeError(f"Manifest-driven selection failed for {stage_name}")
            if not self.run_nerfstudio_training():
                raise RuntimeError(f"NerfStudio training failed for {stage_name}")
            if not self.export_trained_model():
                raise RuntimeError(f"Model export failed for {stage_name}")
            metadata = self.generate_training_metadata()
            elapsed_seconds = round(time.time() - started_at, 3)
            stage_summary = {
                'stage_name': stage_name,
                'training_mode': training_mode,
                'tile_id': tile_id,
                'output_dir': str(stage_output_dir),
                'elapsed_seconds': elapsed_seconds,
                'resume_fingerprint': resume_fingerprint,
                'training_metadata': metadata,
                'training_selection': self.training_selection_result,
            }
            with open(stage_summary_path, 'w', encoding='utf-8') as f:
                json.dump(stage_summary, f, indent=2)
            return stage_summary
        finally:
            try:
                if self.temp_dir == stage_temp_dir:
                    self.cleanup_temp_files()
            finally:
                self.input_dir = original_input_dir
                self.output_dir = original_output_dir
                self.temp_dir = original_temp_dir
                self.background_selection_result = None
                self.floater_pruning_result = None
                self.training_selection_result = None
                tiling_config['training_mode'] = original_training_mode
                tiling_config['tile_id'] = original_tile_id

    def run_tiled_training_pipeline(self) -> bool:
        source_input_dir = self.input_dir
        tiling_config = self.config.get('tiling', {})
        tile_manifest_source = self.resolve_source_input_path(
            source_input_dir,
            str(tiling_config.get('tile_manifest_path', '')),
            "3dgs_tile_manifest.json",
        )
        view_bucket_source = self.resolve_source_input_path(
            source_input_dir,
            str(tiling_config.get('view_bucket_manifest_path', '')),
            "3dgs_view_buckets.json",
        )
        if not tile_manifest_source.exists() or not view_bucket_source.exists():
            logger.error("❌ Tiled pipeline requires 3DGS tile manifests from the SfM stage")
            logger.error(f"   tile_manifest: {tile_manifest_source}")
            logger.error(f"   view_buckets: {view_bucket_source}")
            return False

        tile_manifest = load_json(tile_manifest_source)
        view_buckets = load_json(view_bucket_source)
        pipeline_options = self.resolve_tiled_pipeline_options(tile_manifest)
        selected_tile_ids = pipeline_options['selected_tile_ids']
        selected_tile_manifest = subset_tile_manifest(
            tile_manifest,
            selected_tile_ids=selected_tile_ids,
        )
        if not selected_tile_ids:
            logger.error("❌ Tiled pipeline resolved zero selected tiles")
            return False

        if not self.validate_input_data():
            logger.error("❌ Input data validation failed")
            return False

        canonical_input_dir = self.input_dir
        pipeline_root = self.output_dir / "tiled_pipeline"
        pipeline_root.mkdir(parents=True, exist_ok=True)
        tile_manifest_name = tile_manifest_source.name
        view_bucket_name = view_bucket_source.name

        summary: dict[str, Any] = {
            'mode': 'tiled_pipeline',
            'selected_tile_ids': selected_tile_ids,
            'include_scaffold': pipeline_options['include_scaffold'],
            'include_merge': pipeline_options['include_merge'],
            'resume_existing': pipeline_options['resume_existing'],
            'source_tile_manifest': str(tile_manifest_source),
            'source_view_bucket_manifest': str(view_bucket_source),
            'stages': [],
        }
        config_fingerprint = self.build_resume_fingerprint(
            {
                'config': self.config,
                'selected_tile_manifest': selected_tile_manifest,
                'view_buckets': view_buckets,
            }
        )

        try:
            if pipeline_options['include_scaffold']:
                scaffold_input_dir = pipeline_root / "inputs" / "scaffold"
                self.prepare_tiled_stage_dataset(
                    canonical_input_dir=canonical_input_dir,
                    stage_input_dir=scaffold_input_dir,
                    tile_manifest=selected_tile_manifest,
                    view_buckets=view_buckets,
                    tile_manifest_name=tile_manifest_name,
                    view_bucket_name=view_bucket_name,
                )
                scaffold_summary = self.run_prepared_training_stage(
                    stage_name="scaffold",
                    stage_input_dir=scaffold_input_dir,
                    stage_output_dir=self.output_dir / "scaffold",
                    stage_temp_dir=pipeline_root / "tmp" / "scaffold",
                    training_mode='global_scaffold',
                    resume_existing=pipeline_options['resume_existing'],
                    resume_fingerprint=self.build_resume_fingerprint(
                        {
                            'stage_name': 'scaffold',
                            'training_mode': 'global_scaffold',
                            'config_fingerprint': config_fingerprint,
                        }
                    ),
                )
                summary['stages'].append(scaffold_summary)

            tile_output_dirs: Dict[str, Path] = {}
            for tile_id in selected_tile_ids:
                tile_input_dir = pipeline_root / "inputs" / tile_id
                self.prepare_tiled_stage_dataset(
                    canonical_input_dir=canonical_input_dir,
                    stage_input_dir=tile_input_dir,
                    tile_manifest=selected_tile_manifest,
                    view_buckets=view_buckets,
                    tile_manifest_name=tile_manifest_name,
                    view_bucket_name=view_bucket_name,
                )
                tile_output_dir = self.output_dir / "tiles" / tile_id
                tile_summary = self.run_prepared_training_stage(
                    stage_name=tile_id,
                    stage_input_dir=tile_input_dir,
                    stage_output_dir=tile_output_dir,
                    stage_temp_dir=pipeline_root / "tmp" / tile_id,
                    training_mode='leaf_tile',
                    tile_id=tile_id,
                    resume_existing=pipeline_options['resume_existing'],
                    resume_fingerprint=self.build_resume_fingerprint(
                        {
                            'stage_name': tile_id,
                            'training_mode': 'leaf_tile',
                            'tile_id': tile_id,
                            'config_fingerprint': config_fingerprint,
                        }
                    ),
                )
                summary['stages'].append(tile_summary)
                tile_output_dirs[tile_id] = tile_output_dir

            if pipeline_options['include_merge']:
                merge_output_dir = self.output_dir / "merged"
                merge_output_dir.mkdir(parents=True, exist_ok=True)
                merge_report_path = merge_output_dir / "merge_report.json"
                merge_fingerprint = self.build_resume_fingerprint(
                    {
                        'merge_mode': str(tiling_config.get('merge', {}).get('mode', 'strict_core')),
                        'selected_tile_ids': selected_tile_ids,
                        'config_fingerprint': config_fingerprint,
                    }
                )
                merged_splat_path = merge_output_dir / "merged_splat.ply"
                if pipeline_options['resume_existing'] and merge_report_path.exists() and merged_splat_path.exists():
                    merge_report = load_json(merge_report_path)
                    if str(merge_report.get('resume_fingerprint', '')) != merge_fingerprint:
                        merge_report = merge_tile_outputs(
                            tile_manifest=selected_tile_manifest,
                            tile_output_dirs=tile_output_dirs,
                            output_dir=merge_output_dir,
                            merge_mode=str(tiling_config.get('merge', {}).get('mode', 'strict_core')),
                        )
                        merge_report['resume_fingerprint'] = merge_fingerprint
                        with open(merge_report_path, 'w', encoding='utf-8') as f:
                            json.dump(merge_report, f, indent=2)
                else:
                    merge_report = merge_tile_outputs(
                        tile_manifest=selected_tile_manifest,
                        tile_output_dirs=tile_output_dirs,
                        output_dir=merge_output_dir,
                        merge_mode=str(tiling_config.get('merge', {}).get('mode', 'strict_core')),
                    )
                    merge_report['resume_fingerprint'] = merge_fingerprint
                    with open(merge_report_path, 'w', encoding='utf-8') as f:
                        json.dump(merge_report, f, indent=2)
                summary['merge'] = merge_report

            with open(self.output_dir / "tiled_pipeline_summary.json", 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            with open(self.output_dir / "training_metadata.json", 'w', encoding='utf-8') as f:
                json.dump(
                    {
                        'training_methodology': 'Spaceport tiled splatfacto-w-light pipeline',
                        'framework': 'NerfStudio',
                        'training_mode': 'tiled_pipeline',
                        'selected_tile_ids': selected_tile_ids,
                        'include_scaffold': pipeline_options['include_scaffold'],
                        'include_merge': pipeline_options['include_merge'],
                        'resume_existing': pipeline_options['resume_existing'],
                        'merge': summary.get('merge'),
                        'stages': summary['stages'],
                        'training_completed': True,
                        'timestamp': time.time(),
                        'version': '1.0.0',
                    },
                    f,
                    indent=2,
                )
            return True
        finally:
            self.input_dir = canonical_input_dir

    def apply_training_selection(self) -> bool:
        training_mode = self.resolve_training_mode()
        tile_manifest, view_buckets = self.load_tile_selection_inputs()

        if training_mode == 'monolithic' and tile_manifest is None:
            self.training_selection_result = {
                'training_mode': training_mode,
                'selected_image_count': None,
                'view_bucket_counts': selection_counts_for_buckets([], view_buckets),
            }
            return True

        tiling_config = self.config.get('tiling', {})
        scaffold_config = tiling_config.get('global_scaffold', {})
        tile_id = str(tiling_config.get('tile_id', '')).strip() or None
        max_images = int(scaffold_config.get('max_images', 0)) if training_mode == 'global_scaffold' else None
        frame_stride = int(scaffold_config.get('frame_stride', 1)) if training_mode == 'global_scaffold' else 1

        selected_image_names = select_training_image_names(
            training_mode=training_mode,
            tile_manifest=tile_manifest,
            tile_id=tile_id,
            max_images=max_images,
            stride=frame_stride,
        )
        if not selected_image_names:
            logger.error("❌ Manifest-driven selection resolved zero frames")
            return False

        transforms_path = self.input_dir / "transforms.json"
        with open(transforms_path, 'r', encoding='utf-8') as f:
            transforms = json.load(f)
        image_name_map_path = self.input_dir / "colmap_image_name_map.json"
        image_name_map = load_json(image_name_map_path) if image_name_map_path.exists() else None
        filtered_transforms = filter_transforms_frames(
            transforms,
            selected_image_names,
            image_name_map=image_name_map,
        )
        selected_frame_count = len(filtered_transforms.get('frames', []))
        if selected_frame_count < 2:
            logger.error(
                "❌ Manifest-driven selection kept fewer than 2 frames (selected_names=%s, image_map=%s)",
                len(selected_image_names),
                image_name_map_path.exists(),
            )
            logger.error("   Sample selected image names: %s", selected_image_names[:5])
            return False

        backup_path = self.input_dir / "transforms.full.json"
        if not backup_path.exists():
            shutil.copy2(transforms_path, backup_path)
        with open(transforms_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_transforms, f, indent=2)

        bucket_payload = {
            bucket_name.replace('_camera_ids', ''): image_names
            for bucket_name, image_names in (view_buckets or {}).items()
        }
        self.training_selection_result = {
            'training_mode': training_mode,
            'tile_id': tile_id,
            'selected_image_names': selected_image_names,
            'selected_image_count': selected_frame_count,
            'view_bucket_counts': selection_counts_for_buckets(selected_image_names, bucket_payload),
            'tile_manifest_path': str(tiling_config.get('tile_manifest_path', '')).strip() or None,
            'view_bucket_manifest_path': str(tiling_config.get('view_bucket_manifest_path', '')).strip() or None,
            'image_name_map_path': str(image_name_map_path) if image_name_map_path.exists() else None,
        }

        selection_path = self.output_dir / "training_selection.json"
        with open(selection_path, 'w', encoding='utf-8') as f:
            json.dump(self.training_selection_result, f, indent=2)

        logger.info("🧩 Applied manifest-driven training selection:")
        logger.info(f"   Mode: {training_mode}")
        if tile_id:
            logger.info(f"   Tile ID: {tile_id}")
        logger.info(f"   Selected images: {selected_frame_count}")
        logger.info(f"   Selection summary: {self.training_selection_result['view_bucket_counts']}")
        return True
    
    def run_nerfstudio_training(self) -> bool:
        """Execute NerfStudio training with splatfacto-w-light and background export support"""
        logger.info("🔥 Starting NerfStudio training (splatfacto-w-light)")
        logger.info("=" * 60)
        
        # Get configuration parameters
        model_config = self.config.get('model', {})
        training_config = self.config.get('training', {})
        
        model_variant = model_config.get('variant', 'splatfacto-w-light')
        max_iterations = training_config.get('max_iterations', 30000)
        sh_degree = model_config.get('sh_degree', 3)
        bilateral_processing = model_config.get('bilateral_processing', False)
        rasterize_mode = model_config.get('rasterize_mode', 'classic')
        use_scale_regularization = model_config.get('use_scale_regularization', True)
        cull_alpha_thresh = model_config.get('cull_alpha_thresh', 0.12)
        cull_scale_thresh = model_config.get('cull_scale_thresh', 0.35)
        enable_bg_model = model_config.get('enable_bg_model', True)
        enable_alpha_loss = model_config.get('enable_alpha_loss', True)
        enable_robust_mask = model_config.get('enable_robust_mask', True)
        bg_sh_degree = model_config.get('bg_sh_degree', 4)
        appearance_embed_dim = model_config.get('appearance_embed_dim', 48)
        never_mask_upper = model_config.get('never_mask_upper', 0.4)
        log_interval = training_config.get('log_interval', 100)
        training_mode = self.resolve_training_mode()
        tiling_config = self.config.get('tiling', {})
        scaffold_config = tiling_config.get('global_scaffold', {})

        if training_mode == 'global_scaffold':
            max_iterations = min(max_iterations, int(scaffold_config.get('max_iterations', 4000)))
            sh_degree = min(sh_degree, int(scaffold_config.get('sh_degree', 1)))
            max_gauss_ratio = float(scaffold_config.get('max_gauss_ratio', 4.0))
        else:
            max_gauss_ratio = 10.0
        
        logger.info("🎯 Training Configuration:")
        logger.info(f"   Model: {model_variant}")
        logger.info(f"   Max iterations: {max_iterations}")
        logger.info(f"   SH degree: {sh_degree}")
        logger.info(f"   Rasterize mode: {rasterize_mode}")
        logger.info(f"   Scale regularization: {use_scale_regularization}")
        logger.info(f"   Cull alpha threshold: {cull_alpha_thresh}")
        logger.info(f"   Cull scale threshold: {cull_scale_thresh}")
        logger.info(f"   Background model: {enable_bg_model}")
        logger.info(f"   Alpha loss: {enable_alpha_loss}")
        logger.info(f"   Robust sky masking: {enable_robust_mask}")
        logger.info(f"   Background SH degree: {bg_sh_degree}")
        logger.info(f"   Appearance embedding dim: {appearance_embed_dim}")
        logger.info(f"   Log interval: {log_interval}")
        logger.info(f"   Training mode: {training_mode}")
        logger.info(f"   Dataparser: transforms.json (via ns-process-data conversion)")
        if self.training_selection_result is not None:
            logger.info(f"   Selected images: {self.training_selection_result.get('selected_image_count')}")
            if self.training_selection_result.get('tile_id'):
                logger.info(f"   Tile ID: {self.training_selection_result['tile_id']}")
        
        # Build NerfStudio command with Vincent's exact parameters on converted transforms.json dataset
        # Using industry-standard ns-process-data conversion flow (COLMAP → transforms.json)
        cmd = [
            "ns-train", model_variant,
            "--data", str(self.input_dir),
            "--output-dir", str(self.temp_dir),
            "--vis", "tensorboard",
            "--max_num_iterations", str(max_iterations),
            "--pipeline.model.sh_degree", str(sh_degree),
            "--logging.steps_per_log", str(log_interval)
        ]
        
        if bilateral_processing:
            cmd.extend(["--pipeline.model.use-bilateral-grid", "True"])
            logger.info("🌈 Bilateral guided processing enabled (--pipeline.model.use-bilateral-grid True)")
        else:
            logger.info("ℹ️  Bilateral guided processing disabled")

        if model_variant in {"splatfacto-w-light", "splatfacto-w"}:
            cmd.extend([
                "--pipeline.model.rasterize_mode", str(rasterize_mode),
                "--pipeline.model.use_scale_regularization", str(use_scale_regularization),
                "--pipeline.model.cull_alpha_thresh", str(cull_alpha_thresh),
                "--pipeline.model.cull_scale_thresh", str(cull_scale_thresh),
                "--pipeline.model.enable_bg_model", str(enable_bg_model),
                "--pipeline.model.enable_alpha_loss", str(enable_alpha_loss),
                "--pipeline.model.enable_robust_mask", str(enable_robust_mask),
                "--pipeline.model.bg_sh_degree", str(bg_sh_degree),
                "--pipeline.model.appearance_embed_dim", str(appearance_embed_dim),
                "--pipeline.model.never_mask_upper", str(never_mask_upper),
            ])
        
        # Memory optimization for A10G GPU (16GB vs Vincent's RTX 4090 24GB)
        # Using max-gauss-ratio instead of max_num_gaussians (suggested by NerfStudio error)
        cmd.extend([
            "--pipeline.model.max-gauss-ratio", str(max_gauss_ratio)
        ])
        logger.info(f"🖥️  A10G GPU optimization enabled (max-gauss-ratio: {max_gauss_ratio})")
        logger.info("🪟 Viewer disabled for headless SageMaker training (--vis tensorboard)")
        
        logger.info("🚀 Executing NerfStudio training command:")
        logger.info(f"   {' '.join(cmd)}")
        logger.info("=" * 60)

        training_timeout_seconds = int(os.environ.get("TRAINING_TIMEOUT_SECONDS", "14400"))
        logger.info(f"⏱️  Training timeout: {training_timeout_seconds} seconds")
        
        # Execute training
        try:
            train_env = os.environ.copy()
            pythonpath_parts = ["/opt/ml/code"]
            existing_pythonpath = train_env.get("PYTHONPATH", "")
            if existing_pythonpath:
                pythonpath_parts.append(existing_pythonpath)
            train_env["PYTHONPATH"] = ":".join(part for part in pythonpath_parts if part)
            logger.info(f"🐍 PYTHONPATH for ns-train: {train_env['PYTHONPATH']}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=train_env,
                timeout=training_timeout_seconds,
            )
            
            if result.returncode != 0:
                logger.error("❌ NerfStudio training failed:")
                logger.error(f"Exit code: {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return False
            
            logger.info("✅ NerfStudio training completed successfully")
            logger.info("📊 Training output:")
            
            # Log relevant output (last 20 lines)
            stdout_lines = result.stdout.split('\n')
            for line in stdout_lines[-20:]:
                if line.strip():
                    logger.info(f"   {line}")
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Training timeout ({training_timeout_seconds} seconds exceeded)")
            return False
        except Exception as e:
            logger.error(f"❌ Training execution failed: {e}")
            return False

    def resolve_background_selection(self) -> BackgroundSelectionResult:
        """Resolve the background export mode before we bake the skybox."""
        skybox_config = self.config.get('output', {}).get('background_skybox', {})
        requested_mode = str(skybox_config.get('appearance_mode', 'auto_camera'))
        selection_stride = int(skybox_config.get('selection_stride', 5))
        selection_max_frames = int(skybox_config.get('selection_max_frames', 32))

        selection = select_background_camera(
            data_dir=self.input_dir,
            requested_mode=requested_mode,
            stride=selection_stride,
            max_frames=selection_max_frames,
            default_camera_idx=0,
        )
        logger.info("🌤️ Background camera selection:")
        logger.info(f"   Requested mode: {selection.requested_mode}")
        logger.info(f"   Resolved mode: {selection.resolved_mode}")
        logger.info(f"   Camera index: {selection.camera_idx}")
        logger.info(f"   Sampled candidates: {selection.sampled_candidates}")
        if selection.image_path:
            logger.info(f"   Source image: {selection.image_path}")
        if selection.score is not None:
            logger.info(f"   Selection score: {selection.score:.4f}")

        self.background_selection_result = selection
        return selection

    def prune_exported_foreground(self) -> Optional[FloaterPruningResult]:
        """Prune sky floaters from the exported foreground PLY before compression."""
        pruning_config = self.config.get('output', {}).get('floater_pruning', {})
        if not pruning_config.get('enabled', True):
            self.floater_pruning_result = FloaterPruningResult(
                enabled=False,
                evaluated_gaussians=0,
                candidate_gaussians=0,
                removed_gaussians=0,
                remaining_gaussians=0,
                sampled_views=0,
                min_views=int(pruning_config.get('min_views', 4)),
                top_region_ratio=float(pruning_config.get('top_region_ratio', 0.35)),
                top_view_fraction=float(pruning_config.get('top_view_fraction', 0.8)),
                min_sky_views=int(pruning_config.get('min_sky_views', 0)),
                sky_min_luminance=float(pruning_config.get('sky_min_luminance', 0.3)),
                sky_min_saturation=float(pruning_config.get('sky_min_saturation', 0.08)),
                sky_blue_dominance_margin=float(pruning_config.get('sky_blue_dominance_margin', 0.02)),
                max_opacity=float(pruning_config.get('max_opacity', 0.25)),
                max_color_distance=float(pruning_config.get('max_color_distance', 0.12)),
                min_edge_support=int(pruning_config.get('min_edge_support', 2)),
                patch_size=int(pruning_config.get('patch_size', 9)),
            )
            return self.floater_pruning_result

        ply_path = self.output_dir / "splat.ply"
        if not ply_path.exists():
            logger.warning("⚠️ Floater pruning skipped because splat.ply was not found")
            return None

        result = prune_foreground_floaters(
            ply_path=ply_path,
            data_dir=self.input_dir,
            sampled_views=24,
            min_views=int(pruning_config.get('min_views', 4)),
            top_region_ratio=float(pruning_config.get('top_region_ratio', 0.35)),
            top_view_fraction=float(pruning_config.get('top_view_fraction', 0.8)),
            min_sky_views=int(pruning_config.get('min_sky_views', 0)),
            sky_min_luminance=float(pruning_config.get('sky_min_luminance', 0.3)),
            sky_min_saturation=float(pruning_config.get('sky_min_saturation', 0.08)),
            sky_blue_dominance_margin=float(pruning_config.get('sky_blue_dominance_margin', 0.02)),
            max_opacity=float(pruning_config.get('max_opacity', 0.25)),
            max_color_distance=float(pruning_config.get('max_color_distance', 0.12)),
            min_edge_support=int(pruning_config.get('min_edge_support', 2)),
            patch_size=int(pruning_config.get('patch_size', 9)),
        )
        self.floater_pruning_result = result

        summary_path = self.output_dir / "floater_pruning_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        logger.info("🧹 Floater pruning summary:")
        logger.info(f"   Evaluated gaussians: {result.evaluated_gaussians}")
        logger.info(f"   Low-opacity candidates: {result.candidate_gaussians}")
        logger.info(f"   Removed gaussians: {result.removed_gaussians}")
        logger.info(f"   Remaining gaussians: {result.remaining_gaussians}")
        return result

    def patch_export_manifests(self) -> None:
        """Annotate export manifests with resolved camera selection and pruning metadata."""
        export_manifest_path = self.output_dir / "export_manifest.json"
        background_manifest_path = self.output_dir / "background_manifest.json"

        selection_dict = self.background_selection_result.to_dict() if self.background_selection_result else None
        pruning_dict = self.floater_pruning_result.to_dict() if self.floater_pruning_result else None

        if export_manifest_path.exists():
            with open(export_manifest_path, 'r', encoding='utf-8') as f:
                export_manifest = json.load(f)
            export_manifest['background_selection'] = selection_dict
            export_manifest['floater_pruning'] = pruning_dict
            with open(export_manifest_path, 'w', encoding='utf-8') as f:
                json.dump(export_manifest, f, indent=2)

        if background_manifest_path.exists():
            with open(background_manifest_path, 'r', encoding='utf-8') as f:
                background_manifest = json.load(f)
            if selection_dict:
                background_manifest['selection'] = selection_dict
            if pruning_dict:
                background_manifest['floater_pruning'] = pruning_dict
            with open(background_manifest_path, 'w', encoding='utf-8') as f:
                json.dump(background_manifest, f, indent=2)
    
    def export_trained_model(self, source_config: Optional[Path] = None) -> bool:
        """Export trained model to PLY format and bake the background skybox when available."""
        logger.info("📦 Exporting trained model artifacts...")

        if source_config is not None:
            config_file = source_config
        else:
            # Find the latest config file in training output
            config_files = list(self.temp_dir.glob("**/config.yml"))
            if not config_files:
                logger.error("❌ No config.yml found in training output")
                return False

            # Use the most recent config file
            config_file = max(config_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"📄 Using config: {config_file}")
        
        model_variant = self.config.get('model', {}).get('variant', 'splatfacto-w-light')
        training_mode = self.resolve_training_mode()
        skybox_config = self.config.get('output', {}).get('background_skybox', {})
        background_selection = None if training_mode == 'global_scaffold' else self.resolve_background_selection()

        if training_mode == 'global_scaffold':
            export_cmd = [
                "ns-export", "gaussian-splat",
                "--load-config", str(config_file),
                "--output-dir", str(self.output_dir)
            ]
        elif model_variant in {"splatfacto-w-light", "splatfacto-w"}:
            export_cmd = [
                "python", "/opt/ml/code/export_splatfacto_w_assets.py",
                "--load-config", str(config_file),
                "--output-dir", str(self.output_dir),
                "--camera-idx", str(background_selection.camera_idx or 0),
                "--background-width", str(skybox_config.get('width', 2048)),
                "--background-height", str(skybox_config.get('height', 1024)),
                "--background-quality", str(skybox_config.get('quality', 95)),
                "--background-appearance-mode", str(background_selection.resolved_mode),
            ]
        else:
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

            skybox_path = self.output_dir / "background_skybox.webp"
            if skybox_path.exists():
                logger.info(
                    f"🌤️ Background skybox: {skybox_path.name} "
                    f"({skybox_path.stat().st_size / (1024 * 1024):.2f} MB)"
                )

            if training_mode != 'global_scaffold':
                self.prune_exported_foreground()
                self.patch_export_manifests()
            
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
            'training_methodology': 'Spaceport splatfacto-w-light skybox export',
            'framework': 'NerfStudio',
            'model_variant': self.config.get('model', {}).get('variant', 'splatfacto-w-light'),
            'training_mode': self.resolve_training_mode(),
            'bilateral_guided_processing': self.config.get('model', {}).get('bilateral_processing', False),
            'sh_degree': self.config.get('model', {}).get('sh_degree', 3),
            'enable_bg_model': self.config.get('model', {}).get('enable_bg_model', True),
            'enable_alpha_loss': self.config.get('model', {}).get('enable_alpha_loss', True),
            'enable_robust_mask': self.config.get('model', {}).get('enable_robust_mask', True),
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

        skybox_path = self.output_dir / "background_skybox.webp"
        if skybox_path.exists():
            metadata['background_skybox'] = skybox_path.name
            metadata['background_skybox_size_mb'] = skybox_path.stat().st_size / (1024 * 1024)
        if self.background_selection_result is not None:
            metadata['background_selection'] = self.background_selection_result.to_dict()
        if self.floater_pruning_result is not None:
            metadata['floater_pruning'] = self.floater_pruning_result.to_dict()
        if self.training_selection_result is not None:
            metadata['training_selection'] = self.training_selection_result
        
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
            if self.resolve_training_mode() == 'tiled_pipeline':
                return self.run_tiled_training_pipeline()

            # Step 1: Validate input data
            if not self.validate_input_data():
                logger.error("❌ Input data validation failed")
                return False

            # Step 1.5: Apply manifest-driven image selection after transforms.json conversion
            if not self.apply_training_selection():
                logger.error("❌ Manifest-driven training selection failed")
                return False
            
            # Step 2: Run NerfStudio training
            if not self.run_nerfstudio_training():
                logger.error("❌ NerfStudio training failed")
                return False
            
            # Step 3: Export trained model
            if not self.export_trained_model():
                logger.error("❌ Model export failed")
                return False
            
            # Step 4: Generate metadata
            metadata = self.generate_training_metadata()
            
            # Step 5: Cleanup
            self.cleanup_temp_files()
            
            logger.info("=" * 80)
            logger.info("🎉 NERFSTUDIO TRAINING PIPELINE COMPLETED SUCCESSFULLY!")
            logger.info("✅ splatfacto-w-light foreground training completed")
            logger.info("✅ SOGS-compatible PLY output generated")
            logger.info("✅ Background skybox baked for the viewer")
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
        logger.info("📦 Framework: NerfStudio with splatfacto-w-light")
        logger.info("🎯 Goal: high-quality 3D splats with full sky background coverage")
        
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
