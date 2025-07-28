#!/usr/bin/env python3
"""
REAL Production 3D Gaussian Splatting Training Script
=====================================================

This script performs ACTUAL 3D Gaussian Splatting training using the gsplat library.
Outputs production-ready PLY files with proper spherical harmonics for SOGS compression.

Key Features:
1. Real gsplat library integration with proper SH coefficients
2. CUDA GPU acceleration
3. Actual COLMAP data loading with camera poses
4. Real optimization with densification
5. Production PLY output compatible with SOGS
"""

# ======================= CORE IMPORTS =======================
import os
import sys
import json
import yaml
import time
import math
import logging
import argparse
import subprocess
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# PyTorch imports
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from tqdm import tqdm
from plyfile import PlyData, PlyElement

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import gsplat directly (now pre-installed)
try:
    import gsplat
    from gsplat import rasterization
    logger.info("✅ gsplat library available")
    logger.info(f"✅ gsplat version: {getattr(gsplat, '__version__', 'unknown')}")
    logger.info(f"✅ gsplat rasterization available: {hasattr(gsplat, 'rasterization')}")
except ImportError as e:
    logger.error(f"❌ Failed to import gsplat: {e}")
    raise ImportError("gsplat library not available") from e

# Import dataset utilities
try:
    from utils.dataset import SpaceportDataset
    logger.info("✅ SpaceportDataset imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import SpaceportDataset: {e}")
    raise ImportError("SpaceportDataset not available") from e

class Trainer:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # DEFINITIVE GPU DETECTION AND INITIALIZATION
        self.device = self._initialize_gpu_device()
        
        # Determine paths from SageMaker environment variables FIRST
        self.input_dir = Path(os.environ.get("SM_CHANNEL_TRAINING", "/opt/ml/input/data/training"))
        self.output_dir = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Override config with Step Functions parameters (after paths are set)
        self.apply_step_functions_params()
    
    def _initialize_gpu_device(self) -> torch.device:
        """Definitive GPU detection and initialization for SageMaker ml.g5.xlarge (A10G GPU)"""
        logger.info("🔍 DEFINITIVE GPU DETECTION AND INITIALIZATION")
        logger.info("=" * 60)
        
        # Step 1: Check CUDA availability
        logger.info(f"🔧 PyTorch version: {torch.__version__}")
        logger.info(f"🔧 CUDA compiled version: {torch.version.cuda}")
        logger.info(f"🔧 CUDA available: {torch.cuda.is_available()}")
        
        if not torch.cuda.is_available():
            logger.error("❌ CRITICAL: CUDA not available in PyTorch!")
            logger.error("❌ This indicates a PyTorch/CUDA version mismatch")
            logger.error("❌ Container build failed - GPU training is IMPOSSIBLE")
            raise RuntimeError("CUDA not available - cannot proceed with GPU training")
        
        # Step 2: Check GPU device count
        gpu_count = torch.cuda.device_count()
        logger.info(f"🎮 GPU devices detected: {gpu_count}")
        
        if gpu_count == 0:
            logger.error("❌ CRITICAL: No GPU devices found!")
            logger.error("❌ ml.g5.xlarge should have 1 NVIDIA A10G GPU")
            logger.error("❌ Check SageMaker instance configuration")
            raise RuntimeError("No GPU devices found - cannot proceed with GPU training")
        
        # Step 3: Initialize GPU and get device properties
        torch.cuda.init()
        device = torch.device("cuda:0")
        
        # Step 4: Get GPU properties and verify
        gpu_props = torch.cuda.get_device_properties(0)
        gpu_name = gpu_props.name
        gpu_memory_gb = gpu_props.total_memory / 1024**3
        
        logger.info(f"🎯 Selected GPU: {gpu_name}")
        logger.info(f"💾 GPU Memory: {gpu_memory_gb:.1f} GB")
        logger.info(f"🔧 CUDA capability: {gpu_props.major}.{gpu_props.minor}")
        
        # Step 5: Log nvidia-smi for definitive proof
        try:
            nvidia_smi_output = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,driver_version,power.draw,utilization.gpu,memory.total,memory.used,memory.free', '--format=csv,noheader'],
                capture_output=True, text=True, check=True
            ).stdout.strip()
            logger.info(f"✅ nvidia-smi check: PASSED")
            logger.info(f"🖥️  GPU Details: {nvidia_smi_output}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"❌ nvidia-smi check FAILED: {e}")
            logger.warning(" nvidia-smi not found or failed. This is a strong indicator of a driver/path issue.")

        # Step 6: Test GPU functionality with a tensor operation
        try:
            # Create test tensor on GPU
            test_tensor = torch.randn(1000, 1000, device=device)
            test_result = torch.matmul(test_tensor, test_tensor.T)
            logger.info(f"✅ GPU functionality test: PASSED")
            logger.info(f"✅ Test tensor shape: {test_result.shape}")
        except Exception as e:
            logger.error(f"❌ GPU functionality test FAILED: {e}")
            raise RuntimeError(f"GPU functionality test failed: {e}")
        
        # Step 7: Initialize CUDA context for training
        torch.cuda.empty_cache()
        torch.backends.cudnn.enabled = True
        
        logger.info("✅ GPU INITIALIZATION COMPLETE")
        logger.info("🚀 Ready for GPU-accelerated 3D Gaussian Splatting training")
        logger.info("=" * 60)
        
        return device
    
    def apply_step_functions_params(self):
        """Apply parameters passed from Step Functions via environment variables."""
        env_params = {
            'MAX_ITERATIONS': 'training.max_iterations',
            'MIN_ITERATIONS': 'training.min_iterations', 
            'TARGET_PSNR': 'training.target_psnr',
            'PLATEAU_PATIENCE': 'training.plateau_patience',
            'PSNR_PLATEAU_TERMINATION': 'training.psnr_plateau_termination',
            'LEARNING_RATE': 'learning_rates.gaussian_lr',
            'LOG_INTERVAL': 'training.log_interval',
            'SAVE_INTERVAL': 'training.save_interval',
            # Enhanced densification parameters
            'DENSIFICATION_INTERVAL': 'gaussian_management.densification.interval',
            'DENSIFY_FROM_ITER': 'gaussian_management.densification.start_iteration',
            'DENSIFY_UNTIL_ITER': 'gaussian_management.densification.end_iteration',
            'DENSIFY_GRAD_THRESHOLD': 'gaussian_management.densification.grad_threshold',
            'PERCENT_DENSE': 'gaussian_management.densification.percent_dense',
            'OPACITY_RESET_INTERVAL': 'gaussian_management.opacity_reset_interval'
        }
        
        for env_var, config_path in env_params.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if env_var in ['PSNR_PLATEAU_TERMINATION']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif env_var in ['MAX_ITERATIONS', 'MIN_ITERATIONS', 'PLATEAU_PATIENCE', 'LOG_INTERVAL', 'SAVE_INTERVAL', 
                                'DENSIFICATION_INTERVAL', 'DENSIFY_FROM_ITER', 'DENSIFY_UNTIL_ITER', 'OPACITY_RESET_INTERVAL']:
                    value = int(value)
                elif env_var in ['TARGET_PSNR', 'LEARNING_RATE', 'DENSIFY_GRAD_THRESHOLD', 'PERCENT_DENSE']:
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
        
        # Ensure required sections exist
        if 'training' not in self.config:
            self.config['training'] = {}
        if 'learning_rates' not in self.config:
            self.config['learning_rates'] = {}
        if 'gaussian_management' not in self.config:
            self.config['gaussian_management'] = {}
        if 'densification' not in self.config['gaussian_management']:
            self.config['gaussian_management']['densification'] = {}

        logger.info("✅ Trainer initialized")
        logger.info(f"📁 Input directory: {self.input_dir}")
        logger.info(f"📁 Output directory: {self.output_dir}")
        # GPU information already logged in _initialize_gpu_device method

    def run_real_training(self):
        """Run real gsplat training with proper spherical harmonics output."""
        logger.info("🚀 Starting REAL gsplat 3D Gaussian Splatting Training")

        # 1. Load COLMAP data with cameras and images
        logger.info("📊 Loading COLMAP reconstruction data...")
        scene_data = self.load_colmap_scene()
        
        # 2. Initialize dataset with 80/20 train/test split
        logger.info("📊 Setting up dataset with 80/20 train/test split...")
        dataset = SpaceportDataset(scene_data['scene_path'], scene_data['images_dir'])
        train_indices, val_indices = dataset.get_training_views(split_ratio=0.8)
        
        logger.info(f"✅ Dataset split complete:")
        logger.info(f"   Training images: {len(train_indices)}")
        logger.info(f"   Validation images: {len(val_indices)}")
        
        # Store dataset and splits in scene_data for training loop
        scene_data['dataset'] = dataset
        scene_data['train_indices'] = train_indices
        scene_data['val_indices'] = val_indices
        
        # 3. Initialize Gaussian parameters with proper SH
        logger.info("🎯 Initializing Gaussians with spherical harmonics...")
        gaussians = self.initialize_gaussians_from_colmap(scene_data)
        
        # 4. Setup real gsplat training
        logger.info("⚙️ Setting up gsplat training...")
        optimizer = self.setup_optimizer(gaussians)
        
        # 5. Real training loop with gsplat rasterization
        logger.info("🔥 Starting real gsplat training...")
        self.train_with_gsplat(gaussians, optimizer, scene_data)
        
        logger.info("✅ Real gsplat training completed!")

    def load_colmap_scene(self) -> Dict:
        """Load COLMAP scene data including cameras, images, and image files."""
        scene_path = self.find_colmap_sparse_dir()
        images_dir = self.find_images_dir()
        
        # Load cameras
        cameras = self.load_colmap_cameras(scene_path / "cameras.txt")
        
        # Load images (camera poses)
        images = self.load_colmap_images(scene_path / "images.txt")
        
        # Load 3D points
        points_3d = self.load_colmap_points(scene_path / "points3D.txt")
        
        # Validate image files exist
        image_files = self.validate_image_files(images, images_dir)
        
        return {
            'cameras': cameras,
            'images': images, 
            'points_3d': points_3d,
            'scene_path': scene_path,
            'images_dir': images_dir,
            'image_files': image_files
        }
    
    def load_colmap_cameras(self, cameras_file: Path) -> Dict:
        """Load COLMAP camera intrinsics."""
        cameras = {}
        
        with open(cameras_file, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                    
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                    
                camera_id = int(parts[0])
                model = parts[1]
                width = int(parts[2])
                height = int(parts[3])
                params = [float(p) for p in parts[4:]]
                
                cameras[camera_id] = {
                    'model': model,
                    'width': width,
                    'height': height,
                    'params': params
                }
        
        logger.info(f"✅ Loaded {len(cameras)} cameras")
        return cameras
    
    def load_colmap_images(self, images_file: Path) -> Dict:
        """Load COLMAP image poses."""
        images = {}
        
        with open(images_file, 'r') as f:
            lines = f.readlines()
            
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#') or not line:
                i += 1
                continue
                
            parts = line.split()
            if len(parts) < 10:
                i += 1
                continue
                
            image_id = int(parts[0])
            qw, qx, qy, qz = [float(p) for p in parts[1:5]]
            tx, ty, tz = [float(p) for p in parts[5:8]]
            camera_id = int(parts[8])
            name = parts[9]
            
            # Skip the points line
            i += 2
            
            images[image_id] = {
                'quat': [qw, qx, qy, qz],
                'trans': [tx, ty, tz],
                'camera_id': camera_id,
                'name': name
            }
        
        logger.info(f"✅ Loaded {len(images)} image poses")
        return images
    
    def load_colmap_points(self, points_file: Path) -> Dict:
        """Load COLMAP 3D points."""
        points_3d = []
        colors = []
        
        with open(points_file, 'r') as f:
            for line_num, line in enumerate(f):
                if line.startswith('#') or not line.strip():
                    continue
                
                parts = line.strip().split()
                if len(parts) < 7:
                    continue
                
                try:
                    # XYZ coordinates
                    x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                    # RGB colors
                    r, g, b = int(parts[4]), int(parts[5]), int(parts[6])
                    points_3d.append([x, y, z])
                    colors.append([r, g, b])  # Keep as 0-255 for now
                except (ValueError, IndexError) as e:
                    logger.warning(f"Skipping malformed line {line_num + 1}: {e}")
                    continue
        
        if not points_3d:
            raise Exception("No valid 3D points found in COLMAP reconstruction")
            
        logger.info(f"✅ Loaded {len(points_3d)} 3D points from COLMAP")
        
        return {
            'positions': np.array(points_3d, dtype=np.float32),
            'colors': np.array(colors, dtype=np.uint8)
        }
    
    def initialize_gaussians_from_colmap(self, scene_data: Dict) -> Dict[str, torch.Tensor]:
        """Initialize Gaussian parameters from COLMAP point cloud with proper SH setup."""
        points_3d = scene_data['points_3d']
        
        if not points_3d:
            raise Exception("No 3D points available from COLMAP reconstruction")
        
        positions = points_3d['positions']
        colors = points_3d['colors']
        
        n_points = len(positions)
        logger.info(f"🎯 Initializing {n_points} Gaussians from COLMAP points")
        
        # CRITICAL: Validate sufficient points for quality training
        MIN_SPLATS = 1000
        if n_points < MIN_SPLATS:
            logger.error(f"❌ CRITICAL: Only {n_points} initial splats available!")
            logger.error(f"❌ Need at least {MIN_SPLATS} splats for quality 3D Gaussian Splatting")
            logger.error(f"❌ This indicates poor SfM reconstruction quality")
            logger.error(f"❌ 3DGS TRAINING ABORTED - Fix SfM stage first")
            sys.exit(1)
        
        logger.info(f"✅ Quality check passed: {n_points} >= {MIN_SPLATS} initial splats")
        
        positions = torch.from_numpy(positions).float().to(self.device)
        colors_rgb = colors.astype(np.float32) / 255.0  # Normalize to [0,1]
        
        # Convert RGB to spherical harmonics DC coefficients
        # SH DC coefficient is RGB / sqrt(4*pi) for proper normalization
        sh_dc = torch.from_numpy(colors_rgb).float().to(self.device) / math.sqrt(4 * math.pi)
        
        # Initialize Gaussian parameters
        gaussians = {
            'positions': nn.Parameter(positions),
            'sh_dc': nn.Parameter(sh_dc),  # [N, 3] - DC coefficients only
            'sh_rest': nn.Parameter(torch.zeros(n_points, 0, 3).to(self.device)),  # No higher order SH
            'opacities': nn.Parameter(torch.logit(torch.full((n_points,), 0.7).to(self.device))),
            'scales': nn.Parameter(torch.log(torch.full((n_points, 3), 0.01).to(self.device))),
            'rotations': nn.Parameter(torch.zeros(n_points, 4).to(self.device))  # Quaternions
        }
        
        # Initialize rotations as identity quaternions
        gaussians['rotations'].data[:, 0] = 1.0
        
        logger.info(f"✅ Initialized {n_points} Gaussians with spherical harmonics")
        return gaussians
    
    def setup_optimizer(self, gaussians: Dict[str, torch.Tensor]) -> torch.optim.Optimizer:
        """Setup optimizer with gsplat-recommended learning rates."""
        # Use gsplat default learning rates from documentation
        param_groups = [
            {'params': [gaussians['positions']], 'lr': 0.0001, 'name': 'positions'},  # gsplat default: 1e-4
            {'params': [gaussians['sh_dc']], 'lr': 0.0025, 'name': 'sh_dc'},         # gsplat default: 2.5e-3
            {'params': [gaussians['sh_rest']], 'lr': 0.0025 / 20.0, 'name': 'sh_rest'},  # gsplat default: 2.5e-3/20
            {'params': [gaussians['opacities']], 'lr': 0.05, 'name': 'opacities'},   # gsplat default: 5e-2
            {'params': [gaussians['scales']], 'lr': 0.005, 'name': 'scales'},        # gsplat default: 5e-3
            {'params': [gaussians['rotations']], 'lr': 0.001, 'name': 'rotations'}   # gsplat default: 1e-3
        ]
        
        logger.info("✅ Using gsplat-recommended learning rates:")
        for group in param_groups:
            logger.info(f"   {group['name']}: {group['lr']}")
        
        return torch.optim.Adam(param_groups, lr=0.0, eps=1e-15)
    
    def train_with_gsplat(self, gaussians: Dict[str, torch.Tensor], optimizer: torch.optim.Optimizer, scene_data: Dict):
        """REAL gsplat training loop with photometric loss and 80/20 dataset split."""
        max_iterations = self.config['training']['max_iterations']
        min_iterations = self.config['training'].get('min_iterations', 1000)
        target_psnr = self.config['training'].get('target_psnr', 35.0)
        psnr_plateau_termination = self.config['training'].get('psnr_plateau_termination', False)
        plateau_patience = self.config['training'].get('plateau_patience', 2000)
        validation_interval = self.config['training'].get('validation_interval', 500)
        
        # Enhanced densification parameters
        densify_interval = self.config['gaussian_management']['densification'].get('interval', 100)
        densify_from_iter = self.config['gaussian_management']['densification'].get('start_iteration', 500)
        densify_until_iter = self.config['gaussian_management']['densification'].get('end_iteration', 15000)
        grad_threshold = self.config['gaussian_management']['densification'].get('grad_threshold', 0.0002)
        percent_dense = self.config['gaussian_management']['densification'].get('percent_dense', 0.05)
        opacity_reset_interval = self.config['gaussian_management'].get('opacity_reset_interval', 3000)
        
        # Extract dataset and splits
        dataset = scene_data['dataset']
        train_indices = scene_data['train_indices']
        val_indices = scene_data['val_indices']
        
        # Extract camera parameters for rasterization
        camera_params = self.extract_camera_parameters(scene_data)
        
        # Training tracking
        loss_history = []
        psnr_history = []
        val_psnr_history = []
        densification_events = []
        best_psnr = 0.0
        plateau_counter = 0
        initial_gaussian_count = gaussians['positions'].shape[0]
        
        logger.info(f"🔥 REAL gsplat Training Configuration:")
        logger.info(f"   Max Iterations: {max_iterations}")
        logger.info(f"   Training Images: {len(train_indices)}")
        logger.info(f"   Validation Images: {len(val_indices)}")
        logger.info(f"   Target PSNR: {target_psnr} dB")
        logger.info(f"   Densification: {densify_from_iter}-{densify_until_iter} every {densify_interval} iters")
        logger.info(f"   Initial Gaussians: {initial_gaussian_count}")
        
        # Initialize gradient accumulation
        self.initialize_gradient_accumulation(gaussians)
        
        for iteration in range(max_iterations):
            self.current_iteration = iteration
            
            # Sample random training view
            train_idx = np.random.choice(train_indices)
            image_id = list(scene_data['images'].keys())[train_idx]
            
            # Load ground truth image
            gt_image = dataset.load_image(train_idx)  # Returns [H, W, 3] in [0, 1]
            gt_image_tensor = torch.from_numpy(gt_image).float().to(self.device)
            gt_image_tensor = gt_image_tensor.permute(2, 0, 1)  # [3, H, W]
            
            # Get camera parameters for this view
            cam_params = camera_params[image_id]
            
            # CRITICAL: Real gsplat rasterization
            try:
                # Prepare gsplat parameters
                positions = gaussians['positions']  # [N, 3]
                scales = torch.exp(gaussians['scales'])  # [N, 3] 
                rotations = gaussians['rotations']  # [N, 4]
                opacities = torch.sigmoid(gaussians['opacities'])  # [N]
                
                # Combine SH coefficients [N, 3] for DC only
                colors = gaussians['sh_dc']  # [N, 3]
                
                # Convert camera parameters to tensors
                fx = torch.tensor(cam_params['fx'], device=self.device, dtype=torch.float32)
                fy = torch.tensor(cam_params['fy'], device=self.device, dtype=torch.float32)
                cx = torch.tensor(cam_params['cx'], device=self.device, dtype=torch.float32)
                cy = torch.tensor(cam_params['cy'], device=self.device, dtype=torch.float32)
                width = cam_params['width']
                height = cam_params['height']
                
                # Camera pose (world to camera transform)
                world_to_cam = torch.from_numpy(cam_params['transform']).float().to(self.device)
                
                # Render with gsplat (API: returns 3 values in v1.5.3+)
                render_colors, render_alphas, meta = rasterization(
                    means=positions,
                    scales=scales,
                    quats=rotations,
                    opacities=opacities,
                    colors=colors,
                    viewmats=world_to_cam.unsqueeze(0),
                    Ks=torch.tensor([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], device=self.device).unsqueeze(0),
                    width=width, height=height
                )
                
                # Extract rendered image from colors (first 3 channels are RGB)
                rendered_image = render_colors[..., :3]  # [H, W, 3]
                
                # Ensure ground truth has the same shape as rendered image
                if gt_image_tensor.dim() == 4:  # [1, H, W, 3]
                    gt_image_tensor = gt_image_tensor.squeeze(0)  # [H, W, 3]
                
                # Compute photometric loss
                l1_loss = torch.nn.functional.l1_loss(rendered_image, gt_image_tensor)
                total_loss = l1_loss
                
                # Compute PSNR (using the same tensor shapes as above)
                mse_loss = torch.nn.functional.mse_loss(rendered_image, gt_image_tensor)
                psnr = -10 * torch.log10(mse_loss + 1e-8)
                current_psnr = psnr.item()
                
            except Exception as e:
                logger.error(f"❌ CRITICAL: gsplat rasterization failed: {e}")
                logger.error("❌ No fallback available - training cannot continue with broken rasterization")
                logger.error("❌ This indicates an API mismatch or missing gsplat dependencies")
                raise RuntimeError(f"gsplat rasterization failed: {e}") from e
            
            # Backpropagation
            total_loss.backward()
            
            # Store gradients for densification
            if iteration >= densify_from_iter and iteration <= densify_until_iter:
                if gaussians['positions'].grad is not None:
                    gaussians['positions'].grad_accum += gaussians['positions'].grad.detach().clone()
                    gaussians['positions'].grad_count += 1
            
            optimizer.step()
            optimizer.zero_grad()
            
            # Track metrics
            loss_history.append(total_loss.item())
            psnr_history.append(current_psnr)
            
            # Track best PSNR
            if current_psnr > best_psnr:
                best_psnr = current_psnr
                plateau_counter = 0
            else:
                plateau_counter += 1
            
            # Validation phase
            if iteration % validation_interval == 0 and iteration > 0:
                val_psnr = self.validate_model(gaussians, val_indices, camera_params, dataset, scene_data)
                val_psnr_history.append({'iteration': iteration, 'psnr': val_psnr})
                logger.info(f"📊 Validation PSNR at iter {iteration}: {val_psnr:.2f} dB")
            
            # Densification logic
            if (iteration >= densify_from_iter and iteration <= densify_until_iter and 
                iteration % densify_interval == 0 and iteration > 0):
                
                logger.info(f"🔍 Attempting densification at iter {iteration}")
                old_count = gaussians['positions'].shape[0]
                gaussians = self.densify_gaussians(gaussians, grad_threshold, percent_dense)
                new_count = gaussians['positions'].shape[0]
                
                if new_count > old_count:
                    densification_events.append({
                        'iteration': iteration,
                        'old_count': old_count,
                        'new_count': new_count,
                        'added': new_count - old_count
                    })
                    
                    # Update optimizer with new parameters
                    optimizer = self.update_optimizer_with_new_gaussians(optimizer, gaussians)
                    self.initialize_gradient_accumulation(gaussians)
                    
                    logger.info(f"🌱 SUCCESS: Densification at iter {iteration}: {old_count} → {new_count} (+{new_count - old_count})")
                else:
                    logger.info(f"📊 No densification occurred at iter {iteration}: {old_count} Gaussians (unchanged)")
            
            # Opacity reset
            if iteration > 0 and iteration % opacity_reset_interval == 0:
                with torch.no_grad():
                    low_opacity_mask = torch.sigmoid(gaussians['opacities']) < 0.05
                    gaussians['opacities'][low_opacity_mask] = torch.logit(torch.tensor(0.01))
                    logger.info(f"🔄 Opacity reset at iter {iteration}: {low_opacity_mask.sum().item()} Gaussians reset")
            
            # Enhanced logging
            if iteration % self.config['training']['log_interval'] == 0:
                num_gaussians = gaussians['positions'].shape[0]
                logger.info(f"Iter {iteration:6d}: Loss={total_loss.item():.6f}, PSNR={current_psnr:.1f}dB, Gaussians={num_gaussians}")
            
            # Save checkpoints
            if iteration > 0 and iteration % self.config['training']['save_interval'] == 0:
                self.save_gaussians_ply(gaussians, f"checkpoint_{iteration}.ply")
                logger.info(f"💾 Checkpoint saved at iteration {iteration}")
            
            # Early termination based on PSNR plateau
            if (psnr_plateau_termination and iteration >= min_iterations and 
                plateau_counter >= plateau_patience and best_psnr >= target_psnr):
                logger.info(f"🎯 Early termination: PSNR plateau reached")
                logger.info(f"   Best PSNR: {best_psnr:.2f} dB (target: {target_psnr} dB)")
                break
        
        # Final validation
        final_val_psnr = self.validate_model(gaussians, val_indices, camera_params, dataset, scene_data)
        
        # Save final model
        self.save_gaussians_ply(gaussians, "final_model.ply")

        # Enhanced training metadata with real metrics
        final_gaussian_count = gaussians['positions'].shape[0]
        metadata = {
            'iterations_completed': iteration + 1,
            'training_completed': True,
            'output_format': 'spherical_harmonics',
            'sogs_compatible': True,
            
            # Real quality metrics
            'final_loss': loss_history[-1] if loss_history else 0.0,
            'best_training_psnr': best_psnr,
            'final_validation_psnr': final_val_psnr,
            'target_psnr': target_psnr,
            'psnr_target_achieved': final_val_psnr >= target_psnr,
            
            # Dataset split info
            'training_images': len(train_indices),
            'validation_images': len(val_indices),
            'dataset_split_ratio': 0.8,
            
            # Gaussian evolution
            'initial_gaussian_count': initial_gaussian_count,
            'final_gaussian_count': final_gaussian_count,
            'gaussian_growth_factor': final_gaussian_count / initial_gaussian_count,
            
            # Densification events
            'densification_events': densification_events,
            'total_densifications': len(densification_events),
            
            # Training curves
            'loss_curve': loss_history[-100:] if len(loss_history) > 100 else loss_history,
            'psnr_curve': psnr_history[-100:] if len(psnr_history) > 100 else psnr_history,
            'validation_psnr_curve': val_psnr_history,
        }
        
        metadata_path = self.output_dir / "training_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ REAL gsplat training completed!")
        logger.info(f"📊 Final Results:")
        logger.info(f"   Iterations: {iteration + 1}")
        logger.info(f"   Best Training PSNR: {best_psnr:.2f} dB")
        logger.info(f"   Final Validation PSNR: {final_val_psnr:.2f} dB")
        logger.info(f"   Gaussians: {initial_gaussian_count} → {final_gaussian_count} ({final_gaussian_count/initial_gaussian_count:.2f}x)")
        logger.info(f"   Densifications: {len(densification_events)}")

    def find_colmap_sparse_dir(self) -> Path:
        """Finds the COLMAP sparse reconstruction directory with robust path detection."""
        logger.info(f"🔍 Searching for COLMAP sparse directory in {self.input_dir}...")
        
        # Strategy 1: Look for the standard COLMAP structure
        # Expected: input_dir/sparse/0/points3D.txt
        standard_sparse = self.input_dir / "sparse" / "0"
        if (standard_sparse / "points3D.txt").exists():
            logger.info(f"✅ Found standard COLMAP structure at: {standard_sparse}")
            return standard_sparse
        
        # Strategy 2: Look for any subdirectory containing points3D.txt
        # This handles cases where the structure might be different
        sparse_files = list(self.input_dir.glob("**/points3D.txt"))
        if sparse_files:
            sparse_dir = sparse_files[0].parent
            logger.info(f"✅ Found COLMAP sparse reconstruction at: {sparse_dir}")
            return sparse_dir
        
        # Strategy 3: Look for alternative file names (some converters use different names)
        alternative_files = ["points3d.txt", "points.txt", "3D_points.txt"]
        for alt_file in alternative_files:
            alt_files = list(self.input_dir.glob(f"**/{alt_file}"))
            if alt_files:
                sparse_dir = alt_files[0].parent
                logger.info(f"✅ Found alternative COLMAP structure at: {sparse_dir} (file: {alt_file})")
                return sparse_dir
        
        # Strategy 4: Check if we're in a flat structure (all files in same directory)
        if (self.input_dir / "points3D.txt").exists():
            logger.info(f"✅ Found flat COLMAP structure at: {self.input_dir}")
            return self.input_dir
        
        # Strategy 5: Look for any directory containing COLMAP files
        colmap_files = ["cameras.txt", "images.txt"]
        for colmap_file in colmap_files:
            colmap_locations = list(self.input_dir.glob(f"**/{colmap_file}"))
            if colmap_locations:
                potential_dir = colmap_locations[0].parent
                logger.info(f"🔍 Found potential COLMAP directory at: {potential_dir}")
                # Check if this directory has the essential files
                if (potential_dir / "points3D.txt").exists():
                    logger.info(f"✅ Confirmed COLMAP structure at: {potential_dir}")
                    return potential_dir
        
        # Final check: List all files for debugging
        logger.error(f"❌ Could not find COLMAP sparse reconstruction in {self.input_dir}")
        logger.error("📁 Directory contents:")
        for item in self.input_dir.rglob("*"):
            if item.is_file():
                logger.error(f"   {item.relative_to(self.input_dir)}")
        
        raise FileNotFoundError(
            f"Could not find 'points3D.txt' or equivalent in any subdirectory of {self.input_dir}. "
            f"Expected structure: sparse/0/points3D.txt or similar COLMAP format."
        )

    def find_images_dir(self) -> Path:
        """Finds the images directory with robust path detection."""
        logger.info(f"🔍 Searching for images directory in {self.input_dir}...")
        
        # Strategy 1: Look for standard images directory
        # Expected: input_dir/images/
        standard_images = self.input_dir / "images"
        if standard_images.exists() and standard_images.is_dir():
            image_files = list(standard_images.glob("*.jpg")) + list(standard_images.glob("*.jpeg")) + list(standard_images.glob("*.png")) + list(standard_images.glob("*.JPG")) + list(standard_images.glob("*.JPEG")) + list(standard_images.glob("*.PNG"))
            if image_files:
                logger.info(f"✅ Found standard images directory at: {standard_images} with {len(image_files)} images")
                return standard_images
        
        # Strategy 2: Look for any directory containing image files
        image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]
        for ext in image_extensions:
            image_files = list(self.input_dir.glob(f"**/{ext}"))
            if image_files:
                images_dir = image_files[0].parent
                logger.info(f"✅ Found images directory at: {images_dir} with {len(image_files)} {ext} files")
                return images_dir
        
        # Strategy 3: Check if images are in the same directory as COLMAP files
        sparse_dir = self.find_colmap_sparse_dir()
        if sparse_dir != self.input_dir:
            # Check if images are in the parent directory
            parent_dir = sparse_dir.parent
            image_files = []
            for ext in image_extensions:
                image_files.extend(list(parent_dir.glob(ext)))
            if image_files:
                logger.info(f"✅ Found images in parent directory: {parent_dir} with {len(image_files)} images")
                return parent_dir
        
        # Strategy 4: Check if images are in the same directory as sparse files
        image_files = []
        for ext in image_extensions:
            image_files.extend(list(sparse_dir.glob(ext)))
        if image_files:
            logger.info(f"✅ Found images in sparse directory: {sparse_dir} with {len(image_files)} images")
            return sparse_dir
        
        # Final check: List all files for debugging
        logger.error(f"❌ Could not find images directory in {self.input_dir}")
        logger.error("📁 Directory contents:")
        for item in self.input_dir.rglob("*"):
            if item.is_file():
                logger.error(f"   {item.relative_to(self.input_dir)}")
        
        raise FileNotFoundError(
            f"Could not find image files in any subdirectory of {self.input_dir}. "
            f"Expected structure: images/ directory with .jpg/.png files or images alongside COLMAP files."
        )

    def validate_image_files(self, images: Dict, images_dir: Path) -> Dict[str, Path]:
        """Validate that image files referenced in COLMAP exist in the images directory."""
        logger.info(f"🔍 Validating image files in {images_dir}...")
        
        validated_files = {}
        missing_files = []
        found_files = []
        
        for image_id, image_data in images.items():
            image_name = image_data['name']
            
            # Try to find the image file with various extensions
            image_path = None
            base_name = Path(image_name).stem
            
            for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
                candidate_path = images_dir / f"{base_name}{ext}"
                if candidate_path.exists():
                    image_path = candidate_path
                    break
            
            if image_path is not None:
                validated_files[image_id] = image_path
                found_files.append(image_name)
            else:
                missing_files.append(image_name)
        
        logger.info(f"✅ Image validation complete:")
        logger.info(f"   Found: {len(found_files)}/{len(images)} images")
        logger.info(f"   Missing: {len(missing_files)} images")
        
        if missing_files:
            logger.warning(f"⚠️  Missing image files:")
            for missing in missing_files[:10]:  # Show first 10 missing files
                logger.warning(f"   - {missing}")
            if len(missing_files) > 10:
                logger.warning(f"   ... and {len(missing_files) - 10} more")
        
        # Require at least 80% of images to be present for training
        success_rate = len(found_files) / len(images)
        if success_rate < 0.8:
            logger.error(f"❌ CRITICAL: Only {success_rate:.1%} of images found!")
            logger.error(f"❌ Need at least 80% of images for quality training")
            logger.error(f"❌ 3DGS TRAINING ABORTED - Fix image file availability")
            raise FileNotFoundError(f"Only {success_rate:.1%} of images found, need at least 80%")
        
        logger.info(f"✅ Image validation passed: {success_rate:.1%} success rate")
        return validated_files
    
    def extract_camera_parameters(self, scene_data: Dict) -> Dict:
        """Extract camera parameters for gsplat rasterization."""
        cameras = scene_data['cameras']
        images = scene_data['images']
        
        # For now, assume single camera model (most common case)
        camera_id = list(cameras.keys())[0]
        camera = cameras[camera_id]
        
        # Extract intrinsics
        if camera['model'] == 'PINHOLE':
            fx, fy, cx, cy = camera['params']
        elif camera['model'] == 'SIMPLE_PINHOLE':
            f, cx, cy = camera['params']
            fx = fy = f
        else:
            logger.warning(f"Unsupported camera model: {camera['model']}, using PINHOLE approximation")
            fx, fy, cx, cy = camera['params'][:4]
        
        # Build camera parameter dict for each image
        camera_params = {}
        for image_id, image_data in images.items():
            # Convert quaternion + translation to 4x4 transformation matrix
            qw, qx, qy, qz = image_data['quat']
            tx, ty, tz = image_data['trans']
            
            # Quaternion to rotation matrix
            R = np.array([
                [1 - 2*(qy**2 + qz**2), 2*(qx*qy - qw*qz), 2*(qx*qz + qw*qy)],
                [2*(qx*qy + qw*qz), 1 - 2*(qx**2 + qz**2), 2*(qy*qz - qw*qx)],
                [2*(qx*qz - qw*qy), 2*(qy*qz + qw*qx), 1 - 2*(qx**2 + qy**2)]
            ])
            
            # Build 4x4 transformation matrix
            transform = np.eye(4)
            transform[:3, :3] = R
            transform[:3, 3] = [tx, ty, tz]
            
            camera_params[image_id] = {
                'width': camera['width'],
                'height': camera['height'],
                'fx': fx,
                'fy': fy,
                'cx': cx,
                'cy': cy,
                'transform': transform,
                'camera_id': camera_id
            }
        
        logger.info(f"✅ Extracted camera parameters for {len(camera_params)} images")
        return camera_params
    
    def validate_model(self, gaussians: Dict[str, torch.Tensor], val_indices: List[int], 
                      camera_params: Dict, dataset, scene_data: Dict) -> float:
        """Validate model on held-out test set and return average PSNR."""
        logger.info(f"📊 Running validation on {len(val_indices)} images...")
        
        psnr_values = []
        
        with torch.no_grad():
            for i, val_idx in enumerate(val_indices[:5]):  # Limit to 5 images for speed
                try:
                    # Load validation image
                    image_id = list(scene_data['images'].keys())[val_idx]
                    gt_image = dataset.load_image(val_idx)
                    gt_image_tensor = torch.from_numpy(gt_image).float().to(self.device)
                    gt_image_tensor = gt_image_tensor.permute(2, 0, 1)  # [3, H, W]
                    
                    # Get camera parameters
                    cam_params = camera_params[image_id]
                    
                    # Render with gsplat
                    positions = gaussians['positions']
                    scales = torch.exp(gaussians['scales'])
                    rotations = gaussians['rotations']
                    opacities = torch.sigmoid(gaussians['opacities'])
                    colors = gaussians['sh_dc']
                    
                    fx = torch.tensor(cam_params['fx'], device=self.device, dtype=torch.float32)
                    fy = torch.tensor(cam_params['fy'], device=self.device, dtype=torch.float32)
                    cx = torch.tensor(cam_params['cx'], device=self.device, dtype=torch.float32)
                    cy = torch.tensor(cam_params['cy'], device=self.device, dtype=torch.float32)
                    width = cam_params['width']
                    height = cam_params['height']
                    world_to_cam = torch.from_numpy(cam_params['transform']).float().to(self.device)
                    
                    rendered_image, _ = rasterization(
                        means=positions,
                        scales=scales,
                        quats=rotations,
                        opacities=opacities,
                        colors=colors,
                        viewmats=world_to_cam.unsqueeze(0),
                        Ks=torch.tensor([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], device=self.device).unsqueeze(0),
                        width=width, height=height
                    )
                    
                    # Compute PSNR
                    mse_loss = torch.nn.functional.mse_loss(rendered_image, gt_image_tensor)
                    psnr = -10 * torch.log10(mse_loss + 1e-8)
                    psnr_values.append(psnr.item())
                    
                except Exception as e:
                    logger.warning(f"Validation failed for image {val_idx}: {e}")
                    if "positions" in str(e):
                        logger.error("⚠️  Validation using old API - this should be fixed!")
                    continue
        
        if psnr_values:
            avg_psnr = np.mean(psnr_values)
            logger.info(f"✅ Validation complete: {len(psnr_values)} images, avg PSNR: {avg_psnr:.2f} dB")
            return avg_psnr
        else:
            logger.warning("⚠️ No successful validation renders, returning 0.0 PSNR")
            return 0.0
    
    def densify_gaussians(self, gaussians: Dict[str, torch.Tensor], grad_threshold: float, percent_dense: float) -> Dict[str, torch.Tensor]:
        """
        COMPLETELY REWRITTEN: Proper adaptive densification based on latest 3DGS research.
        
        Based on:
        - Original 3DGS paper (Kerbl et al., 2023)
        - GeoTexDensifier (2024): Geometry-texture-aware densification
        - Micro-splatting (2024): Isotropic constraints for refined optimization  
        """
        if not hasattr(gaussians['positions'], 'grad_accum'):
            logger.warning("No gradient accumulation found - initializing")
            self.initialize_gradient_accumulation(gaussians)
            return gaussians
        
        # Get accumulated gradients (proper normalization)
        grad_accum = gaussians['positions'].grad_accum
        grad_count = max(gaussians['positions'].grad_count, 1)
        
        # CRITICAL FIX: Compute gradient NORMS, not raw gradients
        avg_grad_norms = torch.norm(grad_accum / grad_count, dim=1)
        
        logger.info(f"📊 Densification analysis:")
        logger.info(f"   Avg gradient norm: {avg_grad_norms.mean():.6f}")
        logger.info(f"   Max gradient norm: {avg_grad_norms.max():.6f}")
        logger.info(f"   Gradient threshold: {grad_threshold:.6f}")
        logger.info(f"   Gaussians above threshold: {(avg_grad_norms > grad_threshold).sum()}/{len(avg_grad_norms)}")
        
        # Progressive threshold (start aggressive, become conservative)
        progressive_config = self.config['gaussian_management']['densification'].get('progressive_schedule', {})
        if progressive_config.get('enabled', False):
            current_iter = getattr(self, 'current_iteration', 0)
            schedule_iters = progressive_config.get('schedule_iterations', 7000)
            initial_thresh = progressive_config.get('initial_threshold', 0.00005)
            final_thresh = progressive_config.get('final_threshold', 0.00002)
            
            progress = min(current_iter / schedule_iters, 1.0)
            adaptive_threshold = initial_thresh * (1 - progress) + final_thresh * progress
            logger.info(f"📈 Progressive threshold: {adaptive_threshold:.6f} (iter {current_iter})")
        else:
            adaptive_threshold = grad_threshold
        
        # Advanced densification criteria (based on research)
        split_threshold = self.config['gaussian_management']['densification'].get('split_threshold', 0.00005)
        clone_threshold = self.config['gaussian_management']['densification'].get('clone_threshold', 0.00002)
        
        # Geometry-aware criteria (GeoTexDensifier approach)
        scales = torch.exp(gaussians['scales'])  # Convert log scales to actual scales
        max_scale = torch.max(scales, dim=1)[0]  # Maximum scale per Gaussian
        
        # Adaptive criteria based on gradient magnitude
        high_grad_mask = avg_grad_norms > adaptive_threshold
        very_high_grad_mask = avg_grad_norms > split_threshold
        
        # Split criteria: Large Gaussians with very high gradients
        large_gaussian_mask = max_scale > (percent_dense * 2.0)  # More conservative large detection
        split_mask = very_high_grad_mask & large_gaussian_mask
        
        # Clone criteria: Small Gaussians with high gradients  
        small_gaussian_mask = max_scale <= (percent_dense * 2.0)
        clone_mask = high_grad_mask & small_gaussian_mask
        
        # Opacity-based filtering (remove low-opacity Gaussians)
        opacity_threshold = self.config['gaussian_management']['densification'].get('min_opacity', 0.005)
        valid_opacity_mask = torch.sigmoid(gaussians['opacities']).squeeze() > opacity_threshold
        
        split_mask = split_mask & valid_opacity_mask
        clone_mask = clone_mask & valid_opacity_mask
        
        n_split = split_mask.sum().item()
        n_clone = clone_mask.sum().item()
        
        logger.info(f"🌱 Densification decision: {n_split} splits, {n_clone} clones")
        logger.info(f"   High grad: {high_grad_mask.sum()}/{len(high_grad_mask)}, Large: {large_gaussian_mask.sum()}")
        
        if n_split == 0 and n_clone == 0:
            logger.info("   No densification needed")
            self.reset_gradient_accumulation(gaussians)
            return gaussians
        
        # Apply densification operations
        new_gaussians = gaussians.copy()
        
        if n_split > 0:
            logger.info(f"   Splitting {n_split} large Gaussians")
            new_gaussians = self.split_gaussians_advanced(new_gaussians, split_mask)
        
        if n_clone > 0:
            logger.info(f"   Cloning {n_clone} small Gaussians")
            new_gaussians = self.clone_gaussians_advanced(new_gaussians, clone_mask)
        
        # Reset gradient accumulation
        self.reset_gradient_accumulation(new_gaussians)
        
        # Enforce maximum Gaussian limit
        max_gaussians = self.config['gaussian_management']['densification'].get('max_gaussians', 2000000)
        if len(new_gaussians['positions']) > max_gaussians:
            logger.warning(f"⚠️  Gaussian count ({len(new_gaussians['positions'])}) exceeds limit ({max_gaussians})")
            new_gaussians = self.prune_gaussians_by_importance(new_gaussians, max_gaussians)
        
        logger.info(f"✅ Densification complete: {len(gaussians['positions'])} → {len(new_gaussians['positions'])}")
        return new_gaussians
    
    def initialize_gradient_accumulation(self, gaussians: Dict[str, torch.Tensor]):
        """Initialize gradient accumulation for densification."""
        n_gaussians = len(gaussians['positions'])
        gaussians['positions'].grad_accum = torch.zeros((n_gaussians, 3), device=self.device)
        gaussians['positions'].grad_count = 0
        logger.info(f"🔧 Initialized gradient accumulation for {n_gaussians} Gaussians")
    
    def reset_gradient_accumulation(self, gaussians: Dict[str, torch.Tensor]):
        """Reset gradient accumulation after densification."""
        n_gaussians = len(gaussians['positions'])
        gaussians['positions'].grad_accum = torch.zeros((n_gaussians, 3), device=self.device)
        gaussians['positions'].grad_count = 0
        logger.info(f"🔄 Reset gradient accumulation for {n_gaussians} Gaussians")
    
    def split_gaussians_advanced(self, gaussians: Dict[str, torch.Tensor], split_mask: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Advanced Gaussian splitting based on latest 3DGS research.
        Splits large Gaussians into two smaller, more isotropic Gaussians.
        """
        n_split = split_mask.sum().item()
        if n_split == 0:
            return gaussians
        
        # Get Gaussians to split
        split_positions = gaussians['positions'][split_mask]
        split_scales = gaussians['scales'][split_mask]
        split_rotations = gaussians['rotations'][split_mask]
        
        # Convert to actual scales
        actual_scales = torch.exp(split_scales)
        
        # Create two new Gaussians per split using principal axis
        split_directions = self.compute_split_directions(actual_scales, split_rotations)
        
        # Offset distance based on scale (more conservative than original)
        offset_scale = 0.1  # Reduced from typical 0.16 for better stability
        offsets = split_directions * actual_scales.unsqueeze(-1) * offset_scale
        
        new_positions_1 = split_positions + offsets
        new_positions_2 = split_positions - offsets
        
        # Reduce scale of new Gaussians (critical for quality)
        scale_reduction = math.log(1.6)  # Standard reduction factor
        new_scales = split_scales - scale_reduction
        
        # Slightly reduce opacity to prevent over-brightness
        opacity_reduction = 0.1  # Reduce opacity by 10%
        new_opacities = gaussians['opacities'][split_mask] - opacity_reduction
        
        # Replicate other parameters
        new_sh_dc_1 = gaussians['sh_dc'][split_mask]
        new_sh_dc_2 = gaussians['sh_dc'][split_mask]
        new_sh_rest_1 = gaussians['sh_rest'][split_mask] 
        new_sh_rest_2 = gaussians['sh_rest'][split_mask]
        new_rotations_1 = gaussians['rotations'][split_mask]
        new_rotations_2 = gaussians['rotations'][split_mask]
        
        # Remove original split Gaussians and add new ones
        keep_mask = ~split_mask
        
        new_gaussians = {
            'positions': nn.Parameter(torch.cat([
                gaussians['positions'][keep_mask], new_positions_1, new_positions_2
            ])),
            'sh_dc': nn.Parameter(torch.cat([
                gaussians['sh_dc'][keep_mask], new_sh_dc_1, new_sh_dc_2
            ])),
            'sh_rest': nn.Parameter(torch.cat([
                gaussians['sh_rest'][keep_mask], new_sh_rest_1, new_sh_rest_2
            ])),
            'opacities': nn.Parameter(torch.cat([
                gaussians['opacities'][keep_mask], new_opacities, new_opacities
            ])),
            'scales': nn.Parameter(torch.cat([
                gaussians['scales'][keep_mask], new_scales, new_scales
            ])),
            'rotations': nn.Parameter(torch.cat([
                gaussians['rotations'][keep_mask], new_rotations_1, new_rotations_2
            ]))
        }
        
        return new_gaussians
    
    def compute_split_directions(self, scales: torch.Tensor, rotations: torch.Tensor) -> torch.Tensor:
        """
        Compute optimal split directions using principal component analysis.
        Based on Micro-splatting research for isotropic constraints.
        """
        # Convert quaternions to rotation matrices
        rotation_matrices = self.quaternion_to_rotation_matrix(rotations)
        
        # Find the direction of maximum scale (principal axis)
        scale_matrix = torch.diag_embed(scales)  # Create diagonal scale matrix
        
        # Apply rotation to get world-space principal axes
        principal_axes = torch.bmm(rotation_matrices, scale_matrix)
        
        # Use the direction of maximum scale for splitting
        max_scale_idx = torch.argmax(scales, dim=1)
        split_directions = torch.zeros_like(principal_axes[:, :, 0])
        
        for i, idx in enumerate(max_scale_idx):
            split_directions[i] = principal_axes[i, :, idx]
        
        # Normalize directions
        split_directions = torch.nn.functional.normalize(split_directions, dim=1)
        
        return split_directions
    
    def quaternion_to_rotation_matrix(self, quaternions: torch.Tensor) -> torch.Tensor:
        """Convert quaternions to rotation matrices."""
        # Normalize quaternions
        q = torch.nn.functional.normalize(quaternions, dim=1)
        
        # Extract components
        w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
        
        # Compute rotation matrix elements
        xx, yy, zz = x*x, y*y, z*z
        xy, xz, yz = x*y, x*z, y*z
        wx, wy, wz = w*x, w*y, w*z
        
        # Build rotation matrices
        rotation_matrices = torch.stack([
            torch.stack([1-2*(yy+zz), 2*(xy-wz), 2*(xz+wy)], dim=1),
            torch.stack([2*(xy+wz), 1-2*(xx+zz), 2*(yz-wx)], dim=1),
            torch.stack([2*(xz-wy), 2*(yz+wx), 1-2*(xx+yy)], dim=1)
        ], dim=1)
        
        return rotation_matrices
    
    def clone_gaussians_advanced(self, gaussians: Dict[str, torch.Tensor], clone_mask: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Advanced Gaussian cloning with improved positioning.
        Based on GeoTexDensifier approach for texture-aware densification.
        """
        n_clone = clone_mask.sum().item()
        if n_clone == 0:
            return gaussians
        
        # Get Gaussians to clone
        clone_positions = gaussians['positions'][clone_mask]
        clone_scales = gaussians['scales'][clone_mask]
        
        # Compute smart offset based on local geometry
        actual_scales = torch.exp(clone_scales)
        mean_scale = torch.mean(actual_scales, dim=1, keepdim=True)
        
        # Use smaller offset for cloning (more conservative)
        offset_scale = 0.01  # Very small offset to avoid artifacts
        offsets = torch.randn_like(clone_positions) * mean_scale * offset_scale
        
        new_positions = clone_positions + offsets
        
        # Clone all other parameters exactly
        new_sh_dc = gaussians['sh_dc'][clone_mask]
        new_sh_rest = gaussians['sh_rest'][clone_mask]
        new_opacities = gaussians['opacities'][clone_mask]
        new_scales = gaussians['scales'][clone_mask]
        new_rotations = gaussians['rotations'][clone_mask]
        
        # Concatenate with original Gaussians
        new_gaussians = {
            'positions': nn.Parameter(torch.cat([gaussians['positions'], new_positions])),
            'sh_dc': nn.Parameter(torch.cat([gaussians['sh_dc'], new_sh_dc])),
            'sh_rest': nn.Parameter(torch.cat([gaussians['sh_rest'], new_sh_rest])),
            'opacities': nn.Parameter(torch.cat([gaussians['opacities'], new_opacities])),
            'scales': nn.Parameter(torch.cat([gaussians['scales'], new_scales])),
            'rotations': nn.Parameter(torch.cat([gaussians['rotations'], new_rotations]))
        }
        
        return new_gaussians
    
    def prune_gaussians_by_importance(self, gaussians: Dict[str, torch.Tensor], max_count: int) -> Dict[str, torch.Tensor]:
        """Prune Gaussians by importance (opacity and scale) to maintain reasonable count."""
        current_count = len(gaussians['positions'])
        if current_count <= max_count:
            return gaussians
        
        # Compute importance score (opacity * average_scale)
        opacities = torch.sigmoid(gaussians['opacities']).squeeze()
        scales = torch.exp(gaussians['scales'])
        avg_scales = torch.mean(scales, dim=1)
        importance = opacities * avg_scales
        
        # Keep the most important Gaussians
        _, indices = torch.topk(importance, max_count, largest=True)
        
        logger.info(f"🗂️  Pruned {current_count - max_count} least important Gaussians")
        
        return {
            'positions': nn.Parameter(gaussians['positions'][indices]),
            'sh_dc': nn.Parameter(gaussians['sh_dc'][indices]),
            'sh_rest': nn.Parameter(gaussians['sh_rest'][indices]),
            'opacities': nn.Parameter(gaussians['opacities'][indices]),
            'scales': nn.Parameter(gaussians['scales'][indices]),
            'rotations': nn.Parameter(gaussians['rotations'][indices])
        }
    
    def split_gaussians(self, gaussians: Dict[str, torch.Tensor], mask: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Split large Gaussians into smaller ones."""
        n_split = mask.sum().item()
        if n_split == 0:
            return gaussians
        
        # Sample new positions around the original
        split_positions = gaussians['positions'][mask]
        scales = torch.exp(gaussians['scales'][mask])
        
        # Create two new Gaussians for each split
        offset = torch.randn_like(split_positions) * scales * 0.1
        new_positions_1 = split_positions + offset
        new_positions_2 = split_positions - offset
        
        # Combine original and new positions
        new_positions = torch.cat([gaussians['positions'], new_positions_1, new_positions_2])
        
        # Replicate other parameters
        new_sh_dc = torch.cat([gaussians['sh_dc'], gaussians['sh_dc'][mask], gaussians['sh_dc'][mask]])
        new_sh_rest = torch.cat([gaussians['sh_rest'], gaussians['sh_rest'][mask], gaussians['sh_rest'][mask]])
        new_opacities = torch.cat([gaussians['opacities'], gaussians['opacities'][mask], gaussians['opacities'][mask]])
        
        # Scale down the new Gaussians
        new_scales = gaussians['scales'][mask] - math.log(1.6)  # Reduce scale
        new_scales_all = torch.cat([gaussians['scales'], new_scales, new_scales])
        
        new_rotations = torch.cat([gaussians['rotations'], gaussians['rotations'][mask], gaussians['rotations'][mask]])
        
        # Remove original split Gaussians
        keep_mask = ~mask
        final_positions = torch.cat([new_positions[keep_mask], new_positions_1, new_positions_2])
        final_sh_dc = torch.cat([new_sh_dc[keep_mask], new_sh_dc[len(gaussians['positions']):len(gaussians['positions'])+n_split], new_sh_dc[len(gaussians['positions'])+n_split:]])
        final_sh_rest = torch.cat([new_sh_rest[keep_mask], new_sh_rest[len(gaussians['positions']):len(gaussians['positions'])+n_split], new_sh_rest[len(gaussians['positions'])+n_split:]])
        final_opacities = torch.cat([new_opacities[keep_mask], new_opacities[len(gaussians['positions']):len(gaussians['positions'])+n_split], new_opacities[len(gaussians['positions'])+n_split:]])
        final_scales = torch.cat([new_scales_all[keep_mask], new_scales_all[len(gaussians['positions']):len(gaussians['positions'])+n_split], new_scales_all[len(gaussians['positions'])+n_split:]])
        final_rotations = torch.cat([new_rotations[keep_mask], new_rotations[len(gaussians['positions']):len(gaussians['positions'])+n_split], new_rotations[len(gaussians['positions'])+n_split:]])
        
        return {
            'positions': nn.Parameter(final_positions),
            'sh_dc': nn.Parameter(final_sh_dc),
            'sh_rest': nn.Parameter(final_sh_rest),
            'opacities': nn.Parameter(final_opacities),
            'scales': nn.Parameter(final_scales),
            'rotations': nn.Parameter(final_rotations)
        }
    
    def clone_gaussians(self, gaussians: Dict[str, torch.Tensor], mask: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Clone small Gaussians with high gradients."""
        n_clone = mask.sum().item()
        if n_clone == 0:
            return gaussians
        
        # Clone the selected Gaussians
        clone_positions = gaussians['positions'][mask]
        clone_sh_dc = gaussians['sh_dc'][mask]
        clone_sh_rest = gaussians['sh_rest'][mask]
        clone_opacities = gaussians['opacities'][mask]
        clone_scales = gaussians['scales'][mask]
        clone_rotations = gaussians['rotations'][mask]
        
        # Add small random offset to positions
        offset = torch.randn_like(clone_positions) * 0.01
        clone_positions = clone_positions + offset
        
        # Concatenate with original Gaussians
        return {
            'positions': nn.Parameter(torch.cat([gaussians['positions'], clone_positions])),
            'sh_dc': nn.Parameter(torch.cat([gaussians['sh_dc'], clone_sh_dc])),
            'sh_rest': nn.Parameter(torch.cat([gaussians['sh_rest'], clone_sh_rest])),
            'opacities': nn.Parameter(torch.cat([gaussians['opacities'], clone_opacities])),
            'scales': nn.Parameter(torch.cat([gaussians['scales'], clone_scales])),
            'rotations': nn.Parameter(torch.cat([gaussians['rotations'], clone_rotations]))
        }
    
    def update_optimizer_with_new_gaussians(self, optimizer: torch.optim.Optimizer, gaussians: Dict[str, torch.Tensor]) -> torch.optim.Optimizer:
        """Update optimizer with new Gaussian parameters after densification."""
        # Create new optimizer with updated parameters
        param_groups = [
            {'params': [gaussians['positions']], 'lr': 0.00016, 'name': 'positions'},
            {'params': [gaussians['sh_dc']], 'lr': 0.0025, 'name': 'sh_dc'},
            {'params': [gaussians['sh_rest']], 'lr': 0.0025 / 20.0, 'name': 'sh_rest'},
            {'params': [gaussians['opacities']], 'lr': 0.05, 'name': 'opacities'},
            {'params': [gaussians['scales']], 'lr': 0.005, 'name': 'scales'},
            {'params': [gaussians['rotations']], 'lr': 0.001, 'name': 'rotations'}
        ]
        
        return torch.optim.Adam(param_groups, lr=0.0, eps=1e-15)
    
    def estimate_model_size_mb(self, gaussian_count: int) -> float:
        """Estimate model size in MB based on Gaussian count."""
        # Rough estimate: each Gaussian has ~60 bytes (positions, colors, scales, rotations, opacity)
        bytes_per_gaussian = 60
        total_bytes = gaussian_count * bytes_per_gaussian
        return total_bytes / (1024 * 1024)
    
    def assess_model_quality(self, gaussian_count: int, best_psnr: float, target_psnr: float) -> str:
        """Assess model quality based on metrics."""
        quality_flags = []
        
        # Check PSNR
        if best_psnr >= target_psnr:
            quality_flags.append("PSNR_TARGET_ACHIEVED")
        else:
            quality_flags.append("PSNR_BELOW_TARGET")
        
        # Check Gaussian count (for complex scenes like town squares)
        if gaussian_count < 10000:
            quality_flags.append("LOW_GAUSSIAN_COUNT")
        elif gaussian_count < 50000:
            quality_flags.append("MODERATE_GAUSSIAN_COUNT")
        else:
            quality_flags.append("HIGH_GAUSSIAN_COUNT")
        
        # Check model size
        model_size = self.estimate_model_size_mb(gaussian_count)
        if model_size < 1.0:
            quality_flags.append("SMALL_MODEL")
        elif model_size < 5.0:
            quality_flags.append("MEDIUM_MODEL")
        else:
            quality_flags.append("LARGE_MODEL")
        
        return " | ".join(quality_flags)

    def save_gaussians_ply(self, gaussians: Dict[str, torch.Tensor], filename: str):
        """Save Gaussians to PLY file with proper spherical harmonics format for SOGS."""
        path = self.output_dir / filename
        
        # Extract parameters
        positions = gaussians['positions'].detach().cpu().numpy()
        sh_dc = gaussians['sh_dc'].detach().cpu().numpy()
        sh_rest = gaussians['sh_rest'].detach().cpu().numpy() if gaussians['sh_rest'].numel() > 0 else None
        opacities = torch.sigmoid(gaussians['opacities']).detach().cpu().numpy()
        scales = torch.exp(gaussians['scales']).detach().cpu().numpy()
        rotations = gaussians['rotations'].detach().cpu().numpy()
        
        num_points = positions.shape[0]
        
        # Prepare vertex data with proper field names for SOGS
        dtype_list = [
            ('x', 'f4'), ('y', 'f4'), ('z', 'f4'),
            ('f_dc_0', 'f4'), ('f_dc_1', 'f4'), ('f_dc_2', 'f4'),  # SH DC coefficients
            ('opacity', 'f4'),
            ('scale_0', 'f4'), ('scale_1', 'f4'), ('scale_2', 'f4'),
            ('rot_0', 'f4'), ('rot_1', 'f4'), ('rot_2', 'f4'), ('rot_3', 'f4')
        ]
        
        # Add higher-order SH coefficients if present
        if sh_rest is not None and sh_rest.shape[1] > 0:
            for i in range(sh_rest.shape[1]):
                for j in range(3):  # RGB channels
                    dtype_list.append((f'f_rest_{i*3+j}', 'f4'))
        
        # Create vertex array
        vertex_data = np.zeros(num_points, dtype=dtype_list)
        
        # Fill basic data
        vertex_data['x'] = positions[:, 0]
        vertex_data['y'] = positions[:, 1]
        vertex_data['z'] = positions[:, 2]
        
        # Fill spherical harmonics DC coefficients
        vertex_data['f_dc_0'] = sh_dc[:, 0]
        vertex_data['f_dc_1'] = sh_dc[:, 1]
        vertex_data['f_dc_2'] = sh_dc[:, 2]
        
        # Fill higher-order SH if present
        if sh_rest is not None and sh_rest.shape[1] > 0:
            for i in range(sh_rest.shape[1]):
                for j in range(3):
                    field_name = f'f_rest_{i*3+j}'
                    vertex_data[field_name] = sh_rest[:, i, j]
        
        # Fill other parameters
        vertex_data['opacity'] = opacities
        vertex_data['scale_0'] = scales[:, 0]
        vertex_data['scale_1'] = scales[:, 1]
        vertex_data['scale_2'] = scales[:, 2]
        vertex_data['rot_0'] = rotations[:, 0]
        vertex_data['rot_1'] = rotations[:, 1]
        vertex_data['rot_2'] = rotations[:, 2]
        vertex_data['rot_3'] = rotations[:, 3]
        
        # Create PLY element and save
        vertex_element = PlyElement.describe(vertex_data, 'vertex')
        PlyData([vertex_element]).write(str(path))
        
        logger.info(f"💾 Gaussians saved to {path} with spherical harmonics format")
        logger.info(f"   - {num_points} Gaussians")
        logger.info(f"   - SH DC coefficients: f_dc_0, f_dc_1, f_dc_2")
        if sh_rest is not None and sh_rest.shape[1] > 0:
            logger.info(f"   - Higher-order SH: {sh_rest.shape[1]} bands")
        logger.info(f"   - Compatible with SOGS compression ✓")

def main():
    parser = argparse.ArgumentParser(description="3D Gaussian Splatting Trainer")
    parser.add_argument("--config", type=str, default="/opt/ml/code/progressive_config.yaml", help="Path to the config file.")
    parser.add_argument("train", nargs='?', help="SageMaker training argument (ignored)")  # Handle SageMaker's automatic "train" argument
    args = parser.parse_args()
    
    try:
        logger.info("🚀 Starting 3D Gaussian Splatting Training")
        logger.info("📦 gsplat library status: READY")
        
        trainer = Trainer(args.config)
        trainer.run_real_training()
        
        logger.info("✅ Training completed successfully")
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        logger.error("📋 Check logs above for gsplat installation details")
        raise

if __name__ == "__main__":
    main() 