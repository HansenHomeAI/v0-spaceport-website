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
import tarfile

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
from typing import Dict, Any, Optional, Sequence
import shutil
try:
    from PIL import Image
except ImportError:  # pragma: no cover - local unit tests may run without Pillow installed
    Image = None

from sky_quality import (
    BackgroundSelectionResult,
    FloaterPruningResult,
    prune_foreground_floaters,
    select_background_camera,
)
from tile_pipeline import (
    filter_transforms_frames,
    write_point_cloud_ply_from_gaussians,
    load_json,
    merge_tile_outputs,
    resolve_tile_entry,
    resolve_tiled_input_manifests,
    selection_counts_for_buckets,
    select_review_image_names_by_bucket,
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

PROOF_PROFILE_NONE = "none"
PROOF_PROFILE_QUALITY_GATE_LOW_MEMORY = "quality_gate_low_memory"
QUALITY_GATE_LOW_MEMORY_STOP_SPLIT_AT = 8500


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


def unique_preserving_order(names: Sequence[str]) -> list[str]:
    """Drop duplicates while preserving the original order."""
    unique_names: list[str] = []
    seen: set[str] = set()
    for raw_name in names:
        name = str(raw_name).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        unique_names.append(name)
    return unique_names


def evenly_spaced_subset(names: Sequence[str], limit: int) -> list[str]:
    """Select up to limit names while preserving broad coverage."""
    unique_names = unique_preserving_order(names)
    if limit <= 0:
        return []
    if len(unique_names) <= limit:
        return unique_names
    if limit == 1:
        return [unique_names[len(unique_names) // 2]]

    sampled_indices = [
        round(index * (len(unique_names) - 1) / (limit - 1))
        for index in range(limit)
    ]
    sampled = unique_preserving_order(unique_names[index] for index in sampled_indices)
    if len(sampled) >= limit:
        return sampled[:limit]

    for name in unique_names:
        if name in sampled:
            continue
        sampled.append(name)
        if len(sampled) >= limit:
            break
    return sampled[:limit]


def limit_selected_image_names(
    selected_image_names: Sequence[str],
    *,
    view_buckets: Optional[Dict[str, Sequence[str]]] = None,
    max_images: int = 0,
    selection_stride: int = 1,
) -> list[str]:
    """Cap proof runs deterministically while preserving boundary/horizon coverage."""
    working_names = unique_preserving_order(selected_image_names)
    if selection_stride > 1:
        working_names = working_names[::selection_stride]
    if max_images <= 0 or len(working_names) <= max_images:
        return working_names

    resolved_view_buckets = view_buckets or {}
    chosen: list[str] = []
    chosen_set: set[str] = set()
    coverage_targets = (
        ("boundary_camera_ids", 2),
        ("horizon_camera_ids", 1),
        ("near_detail_camera_ids", 1),
    )

    for bucket_name, target in coverage_targets:
        if len(chosen) >= max_images:
            break
        bucket_candidates = [
            image_name
            for image_name in resolved_view_buckets.get(bucket_name, [])
            if image_name in working_names and image_name not in chosen_set
        ]
        bucket_limit = min(target, max_images - len(chosen), len(bucket_candidates))
        for image_name in evenly_spaced_subset(bucket_candidates, bucket_limit):
            if image_name in chosen_set:
                continue
            chosen.append(image_name)
            chosen_set.add(image_name)
            if len(chosen) >= max_images:
                break

    remaining_names = [image_name for image_name in working_names if image_name not in chosen_set]
    chosen.extend(evenly_spaced_subset(remaining_names, max_images - len(chosen)))
    return chosen[:max_images]


def run_command_with_log_file(
    cmd: Sequence[str],
    *,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
    log_path: Path,
) -> subprocess.CompletedProcess[str]:
    """Run a command without pipe buffering the child process output."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path = log_path
    stderr_output = ""
    stream_subprocess_output = str(os.environ.get("STREAM_SUBPROCESS_OUTPUT", "")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if stream_subprocess_output:
        started_at = time.monotonic()
        captured_lines: list[str] = []
        with open(stdout_path, "w", encoding="utf-8") as handle:
            process = subprocess.Popen(
                list(cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                bufsize=1,
            )
            try:
                while True:
                    if timeout is not None and (time.monotonic() - started_at) > timeout:
                        process.kill()
                        raise subprocess.TimeoutExpired(list(cmd), timeout)

                    if process.stdout is None:
                        break

                    line = process.stdout.readline()
                    if line:
                        captured_lines.append(line)
                        handle.write(line)
                        handle.flush()
                        sys.stdout.write(line)
                        sys.stdout.flush()
                        continue

                    if process.poll() is not None:
                        break
                    time.sleep(0.2)

                if process.stdout is not None:
                    remainder = process.stdout.read()
                    if remainder:
                        captured_lines.append(remainder)
                        handle.write(remainder)
                        handle.flush()
                        sys.stdout.write(remainder)
                        sys.stdout.flush()
            finally:
                if process.stdout is not None:
                    process.stdout.close()

            return subprocess.CompletedProcess(
                args=list(cmd),
                returncode=process.wait(),
                stdout="".join(captured_lines),
                stderr="",
            )

    with open(stdout_path, "w", encoding="utf-8") as handle:
        result = subprocess.run(
            list(cmd),
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            timeout=timeout,
        )

    stdout_output = getattr(result, "stdout", "") or ""
    stderr_output = getattr(result, "stderr", "") or ""
    if not stdout_output and stdout_path.exists():
        stdout_output = stdout_path.read_text(encoding="utf-8", errors="replace")

    return subprocess.CompletedProcess(
        args=list(cmd),
        returncode=result.returncode,
        stdout=stdout_output,
        stderr=stderr_output,
    )


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


def should_retry_with_explicit_dataparser(stderr: str) -> bool:
    error_text = stderr or ""
    return (
        "Unrecognized or misplaced options" in error_text
        and "Arguments are applied to the directly preceding subcommand" in error_text
    )


def supports_bilateral_processing(model_variant: str) -> bool:
    """Return whether the selected NerfStudio method exposes bilateral-grid args."""
    return model_variant not in {"splatfacto-w-light", "splatfacto-w"}


def get_nested_config_value(config: Dict[str, Any], dotted_path: str) -> Any:
    value: Any = config
    for key in dotted_path.split('.'):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def set_nested_config_value(config: Dict[str, Any], dotted_path: str, value: Any) -> None:
    section = config
    keys = dotted_path.split('.')
    for key in keys[:-1]:
        if key not in section or not isinstance(section[key], dict):
            section[key] = {}
        section = section[key]
    section[keys[-1]] = value


def apply_training_proof_profile_defaults(
    config: Dict[str, Any],
    proof_profile: str,
    environ: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    if proof_profile != PROOF_PROFILE_QUALITY_GATE_LOW_MEMORY:
        return {}

    environ = environ or os.environ
    training_config = config.setdefault("training", {})
    max_iterations = int(training_config.get("max_iterations", 12000))
    suppressed_step = max_iterations + 1
    defaults = {
        "TRAINING_VIS_MODE": ("training.vis_mode", "viewer"),
        "TRAINING_CACHE_IMAGES": ("training.cache_images", "disk"),
        "TRAINING_CACHE_IMAGES_TYPE": ("training.cache_images_type", "uint8"),
        "TRAINING_DATALOADER_NUM_WORKERS": ("training.dataloader_num_workers", 0),
        "TRAINING_STOP_SPLIT_AT": ("model.stop_split_at", min(max_iterations, QUALITY_GATE_LOW_MEMORY_STOP_SPLIT_AT)),
        "TRAINING_STEPS_PER_EVAL_IMAGE": ("training.steps_per_eval_image", suppressed_step),
        "TRAINING_STEPS_PER_EVAL_ALL_IMAGES": ("training.steps_per_eval_all_images", suppressed_step),
        "TRAINING_STEPS_PER_SAVE": ("training.steps_per_save", suppressed_step),
    }
    applied: Dict[str, Any] = {}

    for env_var, (config_path, default_value) in defaults.items():
        if environ.get(env_var) is not None:
            continue
        current_value = get_nested_config_value(config, config_path)
        if current_value not in (None, ""):
            continue
        set_nested_config_value(config, config_path, default_value)
        applied[config_path] = default_value

    return applied

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
        self.tile_manifest_resolution: Optional[Dict[str, Any]] = None
        
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
            'TRAINING_VIS_MODE': 'training.vis_mode',
            'TRAINING_CACHE_IMAGES': 'training.cache_images',
            'TRAINING_CACHE_IMAGES_TYPE': 'training.cache_images_type',
            'TRAINING_DATALOADER_NUM_WORKERS': 'training.dataloader_num_workers',
            'TRAINING_MAX_SELECTED_IMAGES': 'training.max_selected_images',
            'TRAINING_SELECTION_STRIDE': 'training.selection_stride',
            'TRAINING_REVIEW_IMAGES_PER_BUCKET': 'training.review_images_per_bucket',
            'TRAINING_STEPS_PER_EVAL_IMAGE': 'training.steps_per_eval_image',
            'TRAINING_STEPS_PER_EVAL_ALL_IMAGES': 'training.steps_per_eval_all_images',
            'TRAINING_STEPS_PER_SAVE': 'training.steps_per_save',
            'TRAINING_MAX_GAUSS_RATIO': 'training.max_gauss_ratio',
            'TRAINING_STOP_SPLIT_AT': 'model.stop_split_at',
            'VIEWER_QUIT_ON_TRAIN_COMPLETION': 'training.quit_on_train_completion',
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
            'TRAINING_DOWNSCALE_FACTOR': 'training.downscale_factor',
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
            'GLOBAL_SCAFFOLD_INIT_MAX_POINTS': 'tiling.global_scaffold.max_init_points',
            'GLOBAL_SCAFFOLD_SOURCE_DIR': 'tiling.global_scaffold.source_dir',
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
                if env_var in ['BILATERAL_PROCESSING', 'USE_SCALE_REGULARIZATION', 'ENABLE_BG_MODEL', 'ENABLE_ALPHA_LOSS', 'ENABLE_ROBUST_MASK', 'FLOATER_PRUNING_ENABLED', 'TILED_INCLUDE_SCAFFOLD', 'TILED_INCLUDE_MERGE', 'TILED_RESUME_EXISTING', 'VIEWER_QUIT_ON_TRAIN_COMPLETION']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif env_var in ['MAX_ITERATIONS', 'LOG_INTERVAL', 'TRAINING_DATALOADER_NUM_WORKERS', 'TRAINING_MAX_SELECTED_IMAGES', 'TRAINING_SELECTION_STRIDE', 'TRAINING_REVIEW_IMAGES_PER_BUCKET', 'TRAINING_STEPS_PER_EVAL_IMAGE', 'TRAINING_STEPS_PER_EVAL_ALL_IMAGES', 'TRAINING_STEPS_PER_SAVE', 'TRAINING_STOP_SPLIT_AT', 'SH_DEGREE', 'BG_SH_DEGREE', 'APPEARANCE_EMBED_DIM', 'TRAINING_DOWNSCALE_FACTOR', 'BACKGROUND_SKYBOX_WIDTH', 'BACKGROUND_SKYBOX_HEIGHT', 'BACKGROUND_SKYBOX_QUALITY', 'BACKGROUND_SELECTION_STRIDE', 'BACKGROUND_SELECTION_MAX_FRAMES', 'FLOATER_PRUNING_MIN_VIEWS', 'FLOATER_PRUNING_MIN_SKY_VIEWS', 'FLOATER_PRUNING_MIN_EDGE_SUPPORT', 'GLOBAL_SCAFFOLD_MAX_IMAGES', 'GLOBAL_SCAFFOLD_FRAME_STRIDE', 'GLOBAL_SCAFFOLD_MAX_ITERATIONS', 'GLOBAL_SCAFFOLD_SH_DEGREE', 'GLOBAL_SCAFFOLD_INIT_MAX_POINTS', 'TILED_MAX_TILES']:
                    value = int(value)
                elif env_var in ['TARGET_PSNR', 'CULL_ALPHA_THRESH', 'CULL_SCALE_THRESH', 'NEVER_MASK_UPPER', 'FLOATER_PRUNING_TOP_REGION_RATIO', 'FLOATER_PRUNING_TOP_VIEW_FRACTION', 'FLOATER_PRUNING_SKY_MIN_LUMINANCE', 'FLOATER_PRUNING_SKY_MIN_SATURATION', 'FLOATER_PRUNING_SKY_BLUE_DOMINANCE_MARGIN', 'FLOATER_PRUNING_MAX_OPACITY', 'FLOATER_PRUNING_MAX_COLOR_DISTANCE', 'GLOBAL_SCAFFOLD_MAX_GAUSS_RATIO']:
                    value = float(value)
                
                # Set nested config values
                set_nested_config_value(self.config, config_path, value)
                
                logger.info(f"📝 Override {config_path} = {value} (from {env_var})")

        # Mirror launcher proof profiles when the trainer is invoked outside the
        # benchmark orchestration path or receives only the profile marker.
        proof_profile = str(os.environ.get("TRAINING_PROOF_PROFILE", PROOF_PROFILE_NONE)).strip() or PROOF_PROFILE_NONE
        applied_defaults = apply_training_proof_profile_defaults(self.config, proof_profile)
        if applied_defaults:
            for config_path, value in applied_defaults.items():
                logger.info(
                    f"🧠 Proof profile default {config_path} = {value} "
                    f"(from TRAINING_PROOF_PROFILE={proof_profile})"
                )
    
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

    @staticmethod
    def build_sparse_point_cloud_ply(points_txt: Path, output_ply: Path) -> bool:
        """Write a lightweight sparse COLMAP point cloud PLY for NerfStudio startup."""
        if not points_txt.exists():
            return False

        vertices: list[tuple[float, float, float, int, int, int]] = []
        with open(points_txt, 'r', encoding='utf-8') as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) < 7:
                    continue
                try:
                    vertices.append(
                        (
                            float(parts[1]),
                            float(parts[2]),
                            float(parts[3]),
                            int(parts[4]),
                            int(parts[5]),
                            int(parts[6]),
                        )
                    )
                except ValueError:
                    continue

        if not vertices:
            return False

        output_ply.parent.mkdir(parents=True, exist_ok=True)
        with open(output_ply, 'w', encoding='utf-8') as handle:
            handle.write("ply\n")
            handle.write("format ascii 1.0\n")
            handle.write(f"element vertex {len(vertices)}\n")
            handle.write("property float x\n")
            handle.write("property float y\n")
            handle.write("property float z\n")
            handle.write("property uchar red\n")
            handle.write("property uchar green\n")
            handle.write("property uchar blue\n")
            handle.write("end_header\n")
            for x, y, z, red, green, blue in vertices:
                handle.write(f"{x} {y} {z} {red} {green} {blue}\n")
        return True
    
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
                sparse_pc_path = converted_dir / "sparse_pc.ply"
                if self.build_sparse_point_cloud_ply(
                    source_input_dir / "sparse" / "0" / "points3D.txt",
                    sparse_pc_path,
                ):
                    logger.info(f"☁️ Saved sparse point cloud PLY: {sparse_pc_path}")
                else:
                    logger.warning("⚠️ Failed to materialize sparse_pc.ply from COLMAP points")
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

    def load_tile_selection_inputs(
        self,
        *,
        manifest_root: Path | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        tiling_config = self.config.get('tiling', {})
        tile_manifest_path = str(tiling_config.get('tile_manifest_path', '')).strip()
        view_bucket_manifest_path = str(tiling_config.get('view_bucket_manifest_path', '')).strip()
        manifest_root = manifest_root or self.input_dir

        def resolve_input_path(raw_path: str) -> Path | None:
            if not raw_path:
                return None
            candidate = Path(raw_path)
            if candidate.is_absolute():
                return candidate
            return manifest_root / candidate

        tile_manifest_resolved = resolve_input_path(tile_manifest_path)
        view_bucket_manifest_resolved = resolve_input_path(view_bucket_manifest_path)
        chunk_planner_path = manifest_root / "chunk_planner_manifest.json"
        sfm_metadata_path = manifest_root / "sfm_metadata.json"
        transforms_path = self.input_dir / "transforms.full.json"
        if not transforms_path.exists():
            transforms_path = self.input_dir / "transforms.json"
        image_name_map_path = self.input_dir / "colmap_image_name_map.json"

        tile_manifest_payload = load_json(tile_manifest_resolved) if tile_manifest_resolved and tile_manifest_resolved.exists() else None
        view_bucket_payload = load_json(view_bucket_manifest_resolved) if view_bucket_manifest_resolved and view_bucket_manifest_resolved.exists() else None
        chunk_planner_payload = load_json(chunk_planner_path) if chunk_planner_path.exists() else None
        sfm_metadata_payload = load_json(sfm_metadata_path) if sfm_metadata_path.exists() else None
        transforms_payload = load_json(transforms_path) if transforms_path.exists() else None
        image_name_map_payload = load_json(image_name_map_path) if image_name_map_path.exists() else None

        if tile_manifest_payload is None and view_bucket_payload is None and chunk_planner_payload is None:
            self.tile_manifest_resolution = None
            return None, None

        scaffold_config = tiling_config.get('global_scaffold', {})
        tile_manifest, view_buckets, resolution = resolve_tiled_input_manifests(
            tile_manifest_payload=tile_manifest_payload,
            view_bucket_payload=view_bucket_payload,
            chunk_planner_manifest=chunk_planner_payload,
            sfm_metadata=sfm_metadata_payload,
            colmap_sparse_dir=self.input_dir / "sparse" / "0",
            transforms_payload=transforms_payload,
            image_name_map_payload=image_name_map_payload,
            global_scaffold_max_images=int(scaffold_config.get('max_images', 240) or 240),
            global_scaffold_stride=int(scaffold_config.get('frame_stride', 2) or 2),
            tile_context_images=int((sfm_metadata_payload or {}).get('tile_context_images', 12) or 12),
        )
        self.tile_manifest_resolution = resolution
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
        tile_id: str | None = None,
        scaffold_output_dir: Path | None = None,
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
        sparse_pc_source = canonical_input_dir / "sparse_pc.ply"
        if sparse_pc_source.exists():
            shutil.copy2(sparse_pc_source, stage_input_dir / "sparse_pc.ply")
        image_name_map_source = canonical_input_dir / "colmap_image_name_map.json"
        if image_name_map_source.exists():
            shutil.copy2(image_name_map_source, stage_input_dir / "colmap_image_name_map.json")

        with open(stage_input_dir / tile_manifest_name, 'w', encoding='utf-8') as f:
            json.dump(tile_manifest, f, indent=2)
        with open(stage_input_dir / view_bucket_name, 'w', encoding='utf-8') as f:
            json.dump(view_buckets, f, indent=2)

        if tile_id and scaffold_output_dir is not None:
            scaffold_ply = scaffold_output_dir / "splat.ply"
            if scaffold_ply.exists():
                tile_entry = resolve_tile_entry(tile_manifest, tile_id)
                scaffold_config = self.config.get("tiling", {}).get("global_scaffold", {})
                max_init_points = int(scaffold_config.get("max_init_points", 0) or 0)
                scaffold_init_path = stage_input_dir / "scaffold_init.ply"
                scaffold_metadata = write_point_cloud_ply_from_gaussians(
                    scaffold_ply,
                    scaffold_init_path,
                    bounds=tile_entry.get("overlap_bounds") or tile_entry.get("core_bounds"),
                    padding_ratio=0.1,
                    max_points=max_init_points or None,
                )
                transforms_path = stage_input_dir / "transforms.json"
                with open(transforms_path, "r", encoding="utf-8") as f:
                    transforms_payload = json.load(f)
                transforms_payload["ply_file_path"] = scaffold_init_path.name
                transforms_payload.setdefault("spaceport_metadata", {})[
                    "scaffold_initialization"
                ] = scaffold_metadata
                with open(transforms_path, "w", encoding="utf-8") as f:
                    json.dump(transforms_payload, f, indent=2)
                with open(stage_input_dir / "scaffold_init_metadata.json", "w", encoding="utf-8") as f:
                    json.dump(scaffold_metadata, f, indent=2)
                logger.info(
                    "🌐 Prepared scaffold point-cloud init for %s with %s inherited points",
                    tile_id,
                    scaffold_metadata.get("inherited_gaussian_count"),
                )

    @staticmethod
    def find_scaffold_output_dir(search_root: Path) -> Path | None:
        candidates = sorted(search_root.rglob("splat.ply"))
        if not candidates:
            return None

        def candidate_score(path: Path) -> tuple[int, int, str]:
            parts = {part.lower() for part in path.parts}
            if path.parent.name.lower() == "scaffold":
                scaffold_score = 0
            elif "scaffold" in parts:
                scaffold_score = 1
            else:
                scaffold_score = 2
            return scaffold_score, len(path.parts), str(path)

        return sorted(candidates, key=candidate_score)[0].parent

    @staticmethod
    def safe_extract_tar(artifact_path: Path, target_dir: Path) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        target_root = target_dir.resolve()
        with tarfile.open(artifact_path, "r:*") as archive:
            members = archive.getmembers()
            for member in members:
                if member.issym() or member.islnk():
                    raise RuntimeError(f"Refusing to extract linked tar member: {member.name}")
                destination = (target_dir / member.name).resolve()
                if destination != target_root and target_root not in destination.parents:
                    raise RuntimeError(f"Refusing to extract unsafe tar member: {member.name}")
            archive.extractall(target_dir, members=members)

    def resolve_external_scaffold_output_dir(
        self,
        pipeline_root: Path,
    ) -> tuple[Path | None, dict[str, Any] | None]:
        scaffold_config = self.config.get("tiling", {}).get("global_scaffold", {})
        source_raw = str(scaffold_config.get("source_dir", "") or "").strip()
        if not source_raw:
            return None, None

        source_path = Path(source_raw)
        if not source_path.exists():
            raise FileNotFoundError(f"Configured GLOBAL_SCAFFOLD_SOURCE_DIR does not exist: {source_path}")

        extraction_root = pipeline_root / "external_scaffold"
        resolved_dir: Path | None
        source_kind = "directory"
        extracted_artifact: str | None = None
        if source_path.is_file():
            if not tarfile.is_tarfile(source_path):
                raise FileNotFoundError(f"Configured scaffold source is not a tar artifact: {source_path}")
            if extraction_root.exists():
                shutil.rmtree(extraction_root)
            self.safe_extract_tar(source_path, extraction_root)
            resolved_dir = self.find_scaffold_output_dir(extraction_root)
            source_kind = "tar_artifact"
            extracted_artifact = str(source_path)
        else:
            resolved_dir = self.find_scaffold_output_dir(source_path)
            if resolved_dir is None:
                tar_candidates = sorted(
                    [path for path in source_path.rglob("*.tar.gz") if path.is_file()],
                    key=lambda path: (len(path.parts), str(path)),
                )
                if not tar_candidates:
                    raise FileNotFoundError(f"No splat.ply or .tar.gz scaffold artifact found under {source_path}")
                if extraction_root.exists():
                    shutil.rmtree(extraction_root)
                self.safe_extract_tar(tar_candidates[0], extraction_root)
                resolved_dir = self.find_scaffold_output_dir(extraction_root)
                source_kind = "directory_tar_artifact"
                extracted_artifact = str(tar_candidates[0])

        if resolved_dir is None or not (resolved_dir / "splat.ply").exists():
            raise FileNotFoundError(f"Could not resolve scaffold splat.ply from {source_path}")

        summary = {
            "stage_name": "scaffold",
            "training_mode": "global_scaffold",
            "status": "reused_external_scaffold",
            "source_dir": str(source_path),
            "source_kind": source_kind,
            "source_artifact": extracted_artifact,
            "output_dir": str(resolved_dir),
            "splat_ply": str(resolved_dir / "splat.ply"),
        }
        logger.info("🌐 Reusing external scaffold PLY from %s", resolved_dir / "splat.ply")
        return resolved_dir, summary

    def emit_probe_review_bundle(self) -> Optional[Dict[str, Any]]:
        if self.training_selection_result is None:
            return None

        review_image_names_by_bucket = self.training_selection_result.get('review_image_names_by_bucket') or {}
        if not review_image_names_by_bucket:
            return None

        images_dir = self.input_dir / "images"
        review_root = self.output_dir / "probe_review"
        reference_root = review_root / "reference"
        manifest = {
            'bucket_counts': {
                bucket_name: len(image_names)
                for bucket_name, image_names in review_image_names_by_bucket.items()
            },
            'reference_images': {},
        }
        reference_root.mkdir(parents=True, exist_ok=True)
        for bucket_name, image_names in review_image_names_by_bucket.items():
            bucket_dir = reference_root / bucket_name
            bucket_dir.mkdir(parents=True, exist_ok=True)
            copied_names: list[str] = []
            for image_name in image_names:
                source_image = images_dir / image_name
                if not source_image.exists():
                    continue
                target_image = bucket_dir / image_name
                shutil.copy2(source_image, target_image)
                copied_names.append(image_name)
            manifest['reference_images'][bucket_name] = copied_names

        manifest_path = review_root / "probe_review_manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        return manifest

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
            self.downscale_selected_training_data_if_requested()
            if not self.run_nerfstudio_training():
                raise RuntimeError(f"NerfStudio training failed for {stage_name}")
            if not self.export_trained_model():
                raise RuntimeError(f"Model export failed for {stage_name}")
            metadata = self.generate_training_metadata()
            probe_review = self.emit_probe_review_bundle()
            if probe_review is not None:
                metadata['probe_review'] = probe_review
                with open(self.output_dir / "training_metadata.json", 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
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
                'tile_manifest_resolution': self.tile_manifest_resolution,
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
                self.tile_manifest_resolution = None
                tiling_config['training_mode'] = original_training_mode
                tiling_config['tile_id'] = original_tile_id

    def resolve_training_downscale_factor(self) -> int:
        training_config = self.config.get('training', {})
        return max(1, int(training_config.get('downscale_factor', 1) or 1))

    @staticmethod
    def scale_intrinsics_for_downscale(payload: Dict[str, Any], factor: int) -> None:
        for key in ('fl_x', 'fl_y', 'cx', 'cy'):
            if key in payload:
                payload[key] = float(payload[key]) / factor
        for key in ('w', 'h'):
            if key in payload:
                payload[key] = max(1, int(round(float(payload[key]) / factor)))

    def downscale_selected_training_data_if_requested(self) -> None:
        downscale_factor = self.resolve_training_downscale_factor()
        if downscale_factor <= 1:
            return
        if Image is None:
            raise RuntimeError("Pillow is required when TRAINING_DOWNSCALE_FACTOR is enabled")

        transforms_path = self.input_dir / "transforms.json"
        if not transforms_path.exists():
            logger.warning("⚠️ Skipping proof-mode downscale because transforms.json is missing")
            return

        with open(transforms_path, 'r', encoding='utf-8') as f:
            transforms = json.load(f)
        original_transforms = json.loads(json.dumps(transforms))

        frames = transforms.get('frames', [])
        if not frames:
            logger.warning("⚠️ Skipping proof-mode downscale because no frames were selected")
            return

        images_dir = self.input_dir / "images"
        if not images_dir.exists():
            logger.warning("⚠️ Skipping proof-mode downscale because images/ is missing")
            return

        source_images_dir = images_dir.resolve()
        if images_dir.is_symlink():
            images_dir.unlink()
        images_dir.mkdir(parents=True, exist_ok=True)

        resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        logger.info(
            "🪄 Downscaling selected training images by %sx for proof-mode validation",
            downscale_factor,
        )
        self.scale_intrinsics_for_downscale(transforms, downscale_factor)
        downscaled_count = 0
        for frame in frames:
            relative_file_path = Path(str(frame.get('file_path', '')))
            if not relative_file_path.name:
                continue
            source_image = source_images_dir / relative_file_path.name
            if not source_image.exists():
                raise FileNotFoundError(f"Selected training image missing for downscale: {source_image}")
            target_image = self.input_dir / relative_file_path
            target_image.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(source_image) as image:
                new_width = max(1, image.width // downscale_factor)
                new_height = max(1, image.height // downscale_factor)
                resized = image.resize((new_width, new_height), resampling)
                resized.save(target_image)
            self.scale_intrinsics_for_downscale(frame, downscale_factor)
            downscaled_count += 1

        transforms['stage_downscale_factor'] = downscale_factor
        with open(self.input_dir / "transforms.pre_downscale.json", 'w', encoding='utf-8') as f:
            json.dump(original_transforms, f, indent=2)
        with open(transforms_path, 'w', encoding='utf-8') as f:
            json.dump(transforms, f, indent=2)

        if self.training_selection_result is not None:
            self.training_selection_result['downscale_factor'] = downscale_factor
            self.training_selection_result['downscaled_image_count'] = downscaled_count
        logger.info(
            "✅ Downscaled %s selected images and updated transforms intrinsics",
            downscaled_count,
        )

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

        if not self.validate_input_data():
            logger.error("❌ Input data validation failed")
            return False

        canonical_input_dir = self.input_dir
        tile_manifest, view_buckets = self.load_tile_selection_inputs(manifest_root=source_input_dir)
        if tile_manifest is None or view_buckets is None:
            logger.error("❌ Tiled pipeline could not resolve tile selection inputs")
            logger.error(f"   tile_manifest candidate: {tile_manifest_source}")
            logger.error(f"   view_buckets candidate: {view_bucket_source}")
            logger.error(f"   chunk_planner candidate: {source_input_dir / 'chunk_planner_manifest.json'}")
            return False
        pipeline_options = self.resolve_tiled_pipeline_options(tile_manifest)
        selected_tile_ids = pipeline_options['selected_tile_ids']
        selected_tile_manifest = subset_tile_manifest(
            tile_manifest,
            selected_tile_ids=selected_tile_ids,
        )
        if not selected_tile_ids:
            logger.error("❌ Tiled pipeline resolved zero selected tiles")
            return False
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
            'tile_manifest_resolution': self.tile_manifest_resolution,
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
            scaffold_summary: dict[str, Any] | None = None
            scaffold_output_dir, external_scaffold_summary = self.resolve_external_scaffold_output_dir(pipeline_root)
            if external_scaffold_summary is not None:
                scaffold_summary = external_scaffold_summary
                summary['stages'].append(scaffold_summary)
            elif pipeline_options['include_scaffold']:
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
                scaffold_output_dir = self.output_dir / "scaffold"

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
                    tile_id=tile_id,
                    scaffold_output_dir=scaffold_output_dir if scaffold_summary else None,
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
                        'tile_manifest_resolution': self.tile_manifest_resolution,
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
        training_config = self.config.get('training', {})
        tile_id = str(tiling_config.get('tile_id', '')).strip() or None
        max_images = int(scaffold_config.get('max_images', 0)) if training_mode == 'global_scaffold' else None
        frame_stride = int(scaffold_config.get('frame_stride', 1)) if training_mode == 'global_scaffold' else 1
        proof_max_images = int(training_config.get('max_selected_images', 0) or 0)
        proof_selection_stride = max(1, int(training_config.get('selection_stride', 1) or 1))

        selected_image_names = select_training_image_names(
            training_mode=training_mode,
            tile_manifest=tile_manifest,
            tile_id=tile_id,
            max_images=max_images,
            stride=frame_stride,
        )
        selected_image_names = limit_selected_image_names(
            selected_image_names,
            view_buckets=view_buckets,
            max_images=proof_max_images,
            selection_stride=proof_selection_stride,
        )
        if not selected_image_names:
            logger.error("❌ Manifest-driven selection resolved zero frames")
            return False

        transforms_path = self.input_dir / "transforms.json"
        with open(transforms_path, 'r', encoding='utf-8') as f:
            transforms = json.load(f)
        image_name_map_path = self.input_dir / "colmap_image_name_map.json"
        image_name_map = load_json(image_name_map_path) if image_name_map_path.exists() else None
        scaffold_init_metadata_path = self.input_dir / "scaffold_init_metadata.json"
        scaffold_init_metadata = (
            load_json(scaffold_init_metadata_path)
            if scaffold_init_metadata_path.exists()
            else None
        )
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
        review_images_by_bucket = select_review_image_names_by_bucket(
            selected_image_names,
            view_buckets,
            max_images_per_bucket=int(training_config.get('review_images_per_bucket', 4) or 4),
        )
        self.training_selection_result = {
            'training_mode': training_mode,
            'tile_id': tile_id,
            'selected_image_names': selected_image_names,
            'selected_image_count': selected_frame_count,
            'max_selected_images': proof_max_images,
            'selection_stride': proof_selection_stride,
            'view_bucket_counts': selection_counts_for_buckets(selected_image_names, bucket_payload),
            'review_image_names_by_bucket': review_images_by_bucket,
            'tile_manifest_path': str(tiling_config.get('tile_manifest_path', '')).strip() or None,
            'view_bucket_manifest_path': str(tiling_config.get('view_bucket_manifest_path', '')).strip() or None,
            'image_name_map_path': str(image_name_map_path) if image_name_map_path.exists() else None,
            'scaffold_initialization': scaffold_init_metadata,
            'tile_manifest_resolution': self.tile_manifest_resolution,
        }

        selection_path = self.output_dir / "training_selection.json"
        with open(selection_path, 'w', encoding='utf-8') as f:
            json.dump(self.training_selection_result, f, indent=2)

        logger.info("🧩 Applied manifest-driven training selection:")
        logger.info(f"   Mode: {training_mode}")
        if tile_id:
            logger.info(f"   Tile ID: {tile_id}")
        logger.info(f"   Selected images: {selected_frame_count}")
        if proof_max_images > 0:
            logger.info(f"   Proof image cap: {proof_max_images}")
        if proof_selection_stride > 1:
            logger.info(f"   Selection stride: {proof_selection_stride}")
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
        requested_bilateral_processing = model_config.get('bilateral_processing', False)
        bilateral_processing = (
            requested_bilateral_processing
            and supports_bilateral_processing(model_variant)
        )
        rasterize_mode = model_config.get('rasterize_mode', 'classic')
        use_scale_regularization = model_config.get('use_scale_regularization', True)
        cull_alpha_thresh = model_config.get('cull_alpha_thresh', 0.12)
        cull_scale_thresh = model_config.get('cull_scale_thresh', 0.35)
        stop_split_at = model_config.get('stop_split_at')
        enable_bg_model = model_config.get('enable_bg_model', True)
        enable_alpha_loss = model_config.get('enable_alpha_loss', True)
        enable_robust_mask = model_config.get('enable_robust_mask', True)
        bg_sh_degree = model_config.get('bg_sh_degree', 4)
        appearance_embed_dim = model_config.get('appearance_embed_dim', 48)
        never_mask_upper = model_config.get('never_mask_upper', 0.4)
        log_interval = training_config.get('log_interval', 100)
        cache_images = str(training_config.get('cache_images', '') or '').strip()
        cache_images_type = str(training_config.get('cache_images_type', '') or '').strip()
        dataloader_num_workers = training_config.get('dataloader_num_workers')
        steps_per_eval_image = training_config.get('steps_per_eval_image')
        steps_per_eval_all_images = training_config.get('steps_per_eval_all_images')
        steps_per_save = training_config.get('steps_per_save')
        quit_on_train_completion = bool(training_config.get('quit_on_train_completion', True))
        training_mode = self.resolve_training_mode()
        tiling_config = self.config.get('tiling', {})
        scaffold_config = tiling_config.get('global_scaffold', {})

        if training_mode == 'global_scaffold':
            max_iterations = min(max_iterations, int(scaffold_config.get('max_iterations', 4000)))
            sh_degree = min(sh_degree, int(scaffold_config.get('sh_degree', 1)))
            max_gauss_ratio = float(scaffold_config.get('max_gauss_ratio', 4.0))
        else:
            max_gauss_ratio = 10.0
        explicit_max_gauss_ratio = training_config.get('max_gauss_ratio')
        if explicit_max_gauss_ratio not in (None, ""):
            max_gauss_ratio = float(explicit_max_gauss_ratio)

        if os.environ.get('TRAINING_STEPS_PER_EVAL_IMAGE') is None and max_iterations <= 250:
            steps_per_eval_image = max_iterations + 1
        if os.environ.get('TRAINING_STEPS_PER_EVAL_ALL_IMAGES') is None and max_iterations <= 250:
            steps_per_eval_all_images = max_iterations + 1
        if os.environ.get('TRAINING_STEPS_PER_SAVE') is None and max_iterations <= 250:
            steps_per_save = max_iterations + 1
        vis_mode = str(training_config.get('vis_mode', 'tensorboard')).strip() or 'tensorboard'

        logger.info("🎯 Training Configuration:")
        logger.info(f"   Model: {model_variant}")
        logger.info(f"   Max iterations: {max_iterations}")
        logger.info(f"   SH degree: {sh_degree}")
        logger.info(f"   Rasterize mode: {rasterize_mode}")
        logger.info(f"   Scale regularization: {use_scale_regularization}")
        logger.info(f"   Cull alpha threshold: {cull_alpha_thresh}")
        logger.info(f"   Cull scale threshold: {cull_scale_thresh}")
        logger.info(
            "   Stop split at: %s",
            stop_split_at if stop_split_at not in (None, "") else "<default>",
        )
        logger.info(f"   Background model: {enable_bg_model}")
        logger.info(f"   Alpha loss: {enable_alpha_loss}")
        logger.info(f"   Robust sky masking: {enable_robust_mask}")
        logger.info(f"   Background SH degree: {bg_sh_degree}")
        logger.info(f"   Appearance embedding dim: {appearance_embed_dim}")
        logger.info(f"   Log interval: {log_interval}")
        logger.info(f"   Cache images: {cache_images or '<default>'}")
        logger.info(f"   Cache images type: {cache_images_type or '<default>'}")
        logger.info(
            "   Dataloader workers: %s",
            dataloader_num_workers if dataloader_num_workers is not None else "<default>",
        )
        logger.info(f"   Steps per eval image: {steps_per_eval_image}")
        logger.info(f"   Steps per eval all images: {steps_per_eval_all_images}")
        logger.info(f"   Steps per save: {steps_per_save}")
        logger.info(f"   Max gauss ratio: {max_gauss_ratio}")
        logger.info(f"   Visualization mode: {vis_mode}")
        logger.info(f"   Quit on train completion: {quit_on_train_completion}")
        logger.info(f"   Training mode: {training_mode}")
        logger.info(f"   Dataparser: transforms.json (via ns-process-data conversion)")
        if self.training_selection_result is not None:
            logger.info(f"   Selected images: {self.training_selection_result.get('selected_image_count')}")
            if self.training_selection_result.get('tile_id'):
                logger.info(f"   Tile ID: {self.training_selection_result['tile_id']}")
        
        base_cmd = [
            "ns-train",
            model_variant,
            "--output-dir",
            str(self.temp_dir),
            "--vis",
            vis_mode,
            "--max_num_iterations",
            str(max_iterations),
            "--pipeline.model.sh_degree",
            str(sh_degree),
            "--logging.steps_per_log",
            str(log_interval),
            "--viewer.quit_on_train_completion",
            str(quit_on_train_completion),
        ]
        if steps_per_eval_image is not None:
            base_cmd.extend(["--steps_per_eval_image", str(int(steps_per_eval_image))])
        if steps_per_eval_all_images is not None:
            base_cmd.extend(["--steps_per_eval_all_images", str(int(steps_per_eval_all_images))])
        if steps_per_save is not None:
            base_cmd.extend(["--steps_per_save", str(int(steps_per_save))])
        method_args: list[str] = []
        
        if requested_bilateral_processing and not bilateral_processing:
            logger.warning(
                "⚠️ Bilateral guided processing requested but unsupported for %s; ignoring it",
                model_variant,
            )
        elif bilateral_processing:
            method_args.extend(["--pipeline.model.use-bilateral-grid", "True"])
            logger.info("🌈 Bilateral guided processing enabled (--pipeline.model.use-bilateral-grid True)")
        else:
            logger.info("ℹ️  Bilateral guided processing disabled")

        if model_variant in {"splatfacto-w-light", "splatfacto-w"}:
            method_args.extend([
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
        if stop_split_at not in (None, ""):
            method_args.extend(["--pipeline.model.stop_split_at", str(int(stop_split_at))])
        if cache_images:
            method_args.extend(["--pipeline.datamanager.cache-images", cache_images])
        if cache_images_type:
            method_args.extend(["--pipeline.datamanager.cache-images-type", cache_images_type])
        if dataloader_num_workers is not None:
            method_args.extend([
                "--pipeline.datamanager.dataloader-num-workers",
                str(int(dataloader_num_workers)),
            ])
        
        # Memory optimization for A10G GPU (16GB vs Vincent's RTX 4090 24GB)
        # Using max-gauss-ratio instead of max_num_gaussians (suggested by NerfStudio error)
        method_args.extend([
            "--pipeline.model.max-gauss-ratio", str(max_gauss_ratio)
        ])
        logger.info(f"🖥️  A10G GPU optimization enabled (max-gauss-ratio: {max_gauss_ratio})")
        logger.info(f"🪟 Visualization backend for this run: {vis_mode}")

        def build_training_command(*, explicit_dataparser: bool) -> list[str]:
            if explicit_dataparser:
                return [
                    *base_cmd,
                    *method_args,
                    "nerfstudio-data",
                    "--data",
                    str(self.input_dir),
                ]
            return [
                "ns-train",
                model_variant,
                "--data",
                str(self.input_dir),
                *base_cmd[2:],
                *method_args,
            ]

        cmd = build_training_command(explicit_dataparser=False)
        
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
            train_log_path = self.output_dir / "ns_train.log"
            logger.info(f"📝 Streaming ns-train output to {train_log_path}")

            result = run_command_with_log_file(
                cmd,
                env=train_env,
                timeout=training_timeout_seconds,
                log_path=train_log_path,
            )

            retry_output = result.stderr or result.stdout
            if result.returncode != 0 and should_retry_with_explicit_dataparser(retry_output):
                fallback_cmd = build_training_command(explicit_dataparser=True)
                logger.warning(
                    "⚠️ ns-train rejected the initial argument ordering; retrying with explicit nerfstudio-data subcommand"
                )
                logger.info(f"   {' '.join(fallback_cmd)}")
                fallback_log_path = self.output_dir / "ns_train.retry.log"
                logger.info(f"📝 Streaming retry output to {fallback_log_path}")
                result = run_command_with_log_file(
                    fallback_cmd,
                    env=train_env,
                    timeout=training_timeout_seconds,
                    log_path=fallback_log_path,
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
            return self.persist_scaffold_training_artifacts(config_file)
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
            if training_mode == 'leaf_tile':
                export_cmd.extend(["--foreground-coordinate-frame", "original"])
        else:
            export_cmd = [
                "ns-export", "gaussian-splat",
                "--load-config", str(config_file),
                "--output-dir", str(self.output_dir)
            ]
        
        logger.info(f"🔄 Executing export command:")
        logger.info(f"   {' '.join(export_cmd)}")
        
        try:
            export_log_path = self.output_dir / "ns_export.log"
            logger.info(f"📝 Streaming export output to {export_log_path}")
            result = run_command_with_log_file(
                export_cmd,
                timeout=600,  # 10 minute timeout
                log_path=export_log_path,
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

    def persist_scaffold_training_artifacts(self, config_file: Path) -> bool:
        """Persist scaffold checkpoint plus an explicit Gaussian PLY export for leaf initialization."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            scaffold_config_path = self.output_dir / "config.yml"
            shutil.copy2(config_file, scaffold_config_path)

            checkpoint_dir = config_file.parent / "nerfstudio_models"
            if checkpoint_dir.exists():
                scaffold_checkpoint_dir = self.output_dir / "nerfstudio_models"
                if scaffold_checkpoint_dir.exists():
                    shutil.rmtree(scaffold_checkpoint_dir)
                shutil.copytree(checkpoint_dir, scaffold_checkpoint_dir)

            export_cmd = [
                "python",
                "/opt/ml/code/export_splatfacto_w_assets.py",
                "--load-config",
                str(config_file),
                "--output-dir",
                str(self.output_dir),
                "--skip-background",
            ]
            export_log_path = self.output_dir / "scaffold_export.log"
            result = run_command_with_log_file(
                export_cmd,
                timeout=600,
                log_path=export_log_path,
            )
            if result.returncode != 0:
                logger.error("❌ Scaffold Gaussian PLY export failed")
                logger.error(f"Exit code: {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return False
            scaffold_ply_path = self.output_dir / "splat.ply"
            if not scaffold_ply_path.exists():
                logger.error("❌ Scaffold export completed without splat.ply")
                return False

            export_manifest = {
                "mode": "gaussian_ply_export",
                "reason": "global_scaffold exports Gaussian PLY for geometry-first leaf initialization",
                "config": str(scaffold_config_path),
                "checkpoint_dir": str(self.output_dir / "nerfstudio_models") if checkpoint_dir.exists() else None,
                "ply": str(scaffold_ply_path),
                "inherited_attributes": ["positions", "dc_color"],
                "reinitialized_leaf_attributes": [
                    "scale",
                    "opacity",
                    "rotation",
                    "sh_rest",
                    "appearance_embeddings",
                ],
            }
            with open(self.output_dir / "export_manifest.json", "w", encoding="utf-8") as handle:
                json.dump(export_manifest, handle, indent=2)

            logger.info("✅ Scaffold artifacts persisted with Gaussian PLY export")
            logger.info(f"📄 Scaffold config: {scaffold_config_path}")
            logger.info(f"☁️ Scaffold PLY: {scaffold_ply_path}")
            if checkpoint_dir.exists():
                logger.info(f"📦 Scaffold checkpoint dir: {self.output_dir / 'nerfstudio_models'}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to persist scaffold artifacts: {e}")
            return False
    
    def generate_training_metadata(self) -> Dict[str, Any]:
        """Generate comprehensive training metadata"""
        metadata = {
            'training_methodology': 'Spaceport splatfacto-w-light skybox export',
            'framework': 'NerfStudio',
            'model_variant': self.config.get('model', {}).get('variant', 'splatfacto-w-light'),
            'training_mode': self.resolve_training_mode(),
            'bilateral_guided_processing': (
                self.config.get('model', {}).get('bilateral_processing', False)
                and supports_bilateral_processing(
                    self.config.get('model', {}).get('variant', 'splatfacto-w-light')
                )
            ),
            'bilateral_guided_processing_requested': self.config.get('model', {}).get('bilateral_processing', False),
            'sh_degree': self.config.get('model', {}).get('sh_degree', 3),
            'enable_bg_model': self.config.get('model', {}).get('enable_bg_model', True),
            'enable_alpha_loss': self.config.get('model', {}).get('enable_alpha_loss', True),
            'enable_robust_mask': self.config.get('model', {}).get('enable_robust_mask', True),
            'max_iterations': self.config.get('training', {}).get('max_iterations', 30000),
            'downscale_factor': self.resolve_training_downscale_factor(),
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
        export_manifest_path = self.output_dir / "export_manifest.json"
        if export_manifest_path.exists():
            try:
                with open(export_manifest_path, 'r', encoding='utf-8') as f:
                    metadata['export_manifest'] = json.load(f)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(f"⚠️ Could not read export manifest: {exc}")
        if self.training_selection_result is not None:
            metadata['training_selection'] = self.training_selection_result
        if self.tile_manifest_resolution is not None:
            metadata['tile_manifest_resolution'] = self.tile_manifest_resolution

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
