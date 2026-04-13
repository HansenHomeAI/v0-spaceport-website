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
        self.background_selection_result: Optional[BackgroundSelectionResult] = None
        self.floater_pruning_result: Optional[FloaterPruningResult] = None
        
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
            'FLOATER_PRUNING_MAX_OPACITY': 'output.floater_pruning.max_opacity',
            'FLOATER_PRUNING_MAX_COLOR_DISTANCE': 'output.floater_pruning.max_color_distance',
            'FLOATER_PRUNING_MIN_EDGE_SUPPORT': 'output.floater_pruning.min_edge_support',
        }
        
        for env_var, config_path in env_params.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if env_var in ['BILATERAL_PROCESSING', 'USE_SCALE_REGULARIZATION', 'ENABLE_BG_MODEL', 'ENABLE_ALPHA_LOSS', 'ENABLE_ROBUST_MASK', 'FLOATER_PRUNING_ENABLED']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif env_var in ['MAX_ITERATIONS', 'SH_DEGREE', 'LOG_INTERVAL', 'BG_SH_DEGREE', 'APPEARANCE_EMBED_DIM', 'BACKGROUND_SKYBOX_WIDTH', 'BACKGROUND_SKYBOX_HEIGHT', 'BACKGROUND_SKYBOX_QUALITY', 'BACKGROUND_SELECTION_STRIDE', 'BACKGROUND_SELECTION_MAX_FRAMES', 'FLOATER_PRUNING_MIN_VIEWS', 'FLOATER_PRUNING_MIN_EDGE_SUPPORT']:
                    value = int(value)
                elif env_var in ['TARGET_PSNR', 'CULL_ALPHA_THRESH', 'CULL_SCALE_THRESH', 'NEVER_MASK_UPPER', 'FLOATER_PRUNING_TOP_REGION_RATIO', 'FLOATER_PRUNING_TOP_VIEW_FRACTION', 'FLOATER_PRUNING_MAX_OPACITY', 'FLOATER_PRUNING_MAX_COLOR_DISTANCE']:
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
        logger.info(f"   Dataparser: transforms.json (via ns-process-data conversion)")
        
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
            "--pipeline.model.max-gauss-ratio", "10.0"  # Conservative ratio for A10G
        ])
        logger.info("🖥️  A10G GPU optimization enabled (max-gauss-ratio: 10.0)")
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
        skybox_config = self.config.get('output', {}).get('background_skybox', {})
        background_selection = self.resolve_background_selection()

        if model_variant in {"splatfacto-w-light", "splatfacto-w"}:
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
