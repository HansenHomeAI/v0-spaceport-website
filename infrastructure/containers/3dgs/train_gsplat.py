#!/usr/bin/env python3
"""
Production 3D Gaussian Splatting Training with gsplat
Real implementation for SageMaker ml.g4dn.xlarge (T4 GPU)
"""

import os
import sys
import json
import time
import random
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
import boto3
from tqdm import tqdm

# gsplat imports
import gsplat

from utils.colmap_loader import load_colmap_data
from utils.dataset import GSplatDataset, prepare_gsplat_data


class GSplatTrainer:
    """Production gsplat trainer"""
    
    def __init__(self, config: Dict):
        """Initialize trainer with configuration"""
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        print(f"🚀 GSplat Trainer initialized")
        print(f"   Device: {self.device}")
        print(f"   CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"   GPU: {torch.cuda.get_device_name()}")
            print(f"   CUDA version: {torch.version.cuda}")
            print(f"   GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        
        # Initialize dataset
        self.dataset = None
        self.gaussians = None
        
    def load_data(self, data_path: Path):
        """Load COLMAP data"""
        print(f"📂 Loading data from: {data_path}")
        
        # Look for sparse directory
        sparse_dir = data_path / "sparse"
        if not sparse_dir.exists():
            # Try direct path
            if (data_path / "cameras.txt").exists():
                sparse_dir = data_path
            else:
                raise FileNotFoundError(f"COLMAP sparse data not found in {data_path}")
        
        # Initialize dataset
        self.dataset = GSplatDataset(sparse_dir)
        
        print(f"✅ Data loaded successfully")
        return True
    
    def initialize_gaussians(self):
        """Initialize 3D Gaussians from COLMAP points"""
        print("🎯 Initializing 3D Gaussians...")
        
        # Get initial points and colors from COLMAP
        points, colors = self.dataset.get_initial_points()
        
        # Convert to tensors
        n_points = len(points)
        print(f"   Starting with {n_points} Gaussians")
        
        # Initialize Gaussian parameters
        self.means = torch.tensor(points, dtype=torch.float32, device=self.device, requires_grad=True)
        
        # Initialize scales (small random values)
        scales = torch.log(torch.rand(n_points, 3, device=self.device) * 0.1 + 0.001)
        self.scales = torch.nn.Parameter(scales)
        
        # Initialize rotations (unit quaternions)
        rotations = torch.zeros(n_points, 4, device=self.device)
        rotations[:, 0] = 1.0  # w component
        self.rotations = torch.nn.Parameter(rotations)
        
        # Initialize colors (SH coefficients)
        # Start with RGB colors from COLMAP
        colors_normalized = torch.tensor(colors, dtype=torch.float32, device=self.device) / 255.0
        # Convert to spherical harmonics (0th order)
        sh_features = torch.zeros(n_points, 3, 16, device=self.device)  # 3 channels, 16 SH coefficients
        sh_features[:, :, 0] = colors_normalized  # 0th order SH
        self.features = torch.nn.Parameter(sh_features)
        
        # Initialize opacity (logit space)
        opacity = torch.logit(torch.ones(n_points, device=self.device) * 0.1)
        self.opacities = torch.nn.Parameter(opacity)
        
        print(f"✅ Gaussians initialized")
        print(f"   Means: {self.means.shape}")
        print(f"   Scales: {self.scales.shape}")
        print(f"   Rotations: {self.rotations.shape}")
        print(f"   Features: {self.features.shape}")
        print(f"   Opacities: {self.opacities.shape}")
    
    def get_camera_matrices(self, idx: int):
        """Get camera matrices for rendering"""
        camera_params = self.dataset.get_camera_params()
        pose = self.dataset.poses[idx]
        
        # Intrinsic matrix
        fx, fy = camera_params['fx'], camera_params['fy']
        cx, cy = camera_params['cx'], camera_params['cy']
        
        K = torch.tensor([
            [fx, 0, cx],
            [0, fy, cy],
            [0, 0, 1]
        ], dtype=torch.float32, device=self.device)
        
        # Extrinsic matrix (world to camera)
        pose_tensor = torch.tensor(pose, dtype=torch.float32, device=self.device)
        
        return K, pose_tensor
    
    def render_view(self, idx: int, height: int, width: int):
        """Render a view using gsplat"""
        K, pose = self.get_camera_matrices(idx)
        
        # Convert pose to viewmat (world to camera)
        viewmat = torch.inverse(pose)
        
        # Render with gsplat
        try:
            colors, alphas = gsplat.rasterization(
                means=self.means,
                quats=F.normalize(self.rotations, dim=-1),
                scales=torch.exp(self.scales),
                opacities=torch.sigmoid(self.opacities),
                colors=self.features[:, :, 0],  # Use 0th order SH for now
                viewmats=viewmat.unsqueeze(0),
                Ks=K.unsqueeze(0),  
                width=width,
                height=height,
            )
            
            rendered_image = colors[0]  # Remove batch dimension
            rendered_alpha = alphas[0]
            
            return rendered_image, rendered_alpha
            
        except Exception as e:
            print(f"Error in rendering: {e}")
            # Fallback to zeros
            return torch.zeros(height, width, 3, device=self.device), torch.zeros(height, width, device=self.device)
    
    def compute_loss(self, rendered_image: torch.Tensor, target_image: torch.Tensor):
        """Compute training loss"""
        # L1 loss
        l1_loss = F.l1_loss(rendered_image, target_image)
        
        # SSIM loss (simplified)
        mse_loss = F.mse_loss(rendered_image, target_image)
        
        total_loss = 0.8 * l1_loss + 0.2 * mse_loss
        
        return total_loss, l1_loss, mse_loss
    
    def train(self):
        """Main training loop"""
        print("🏋️ Starting training...")
        
        # Training configuration
        max_iterations = self.config.get('max_iterations', 30000)
        log_interval = self.config.get('log_interval', 1000)
        save_interval = self.config.get('save_interval', 5000)
        
        # Learning rates
        position_lr = self.config.get('position_lr', 0.00016)
        feature_lr = self.config.get('feature_lr', 0.0025)
        opacity_lr = self.config.get('opacity_lr', 0.05)
        scaling_lr = self.config.get('scaling_lr', 0.005)
        rotation_lr = self.config.get('rotation_lr', 0.001)
        
        # Optimizers
        params = [
            {'params': [self.means], 'lr': position_lr, 'name': 'means'},
            {'params': [self.features], 'lr': feature_lr, 'name': 'features'},
            {'params': [self.opacities], 'lr': opacity_lr, 'name': 'opacities'},
            {'params': [self.scales], 'lr': scaling_lr, 'name': 'scales'},
            {'params': [self.rotations], 'lr': rotation_lr, 'name': 'rotations'},
        ]
        
        optimizer = torch.optim.Adam(params, eps=1e-15)
        
        # Get training views
        train_indices, val_indices = self.dataset.get_training_views()
        
        # Training loop
        start_time = time.time()
        
        for iteration in range(max_iterations):
            optimizer.zero_grad()
            
            # Random training view
            idx = random.choice(train_indices)
            
            # Load target image
            target_image = self.dataset.load_image(idx)
            height, width = target_image.shape[:2]
            target_tensor = torch.tensor(target_image, dtype=torch.float32, device=self.device)
            
            # Render view
            rendered_image, rendered_alpha = self.render_view(idx, height, width)
            
            # Compute loss
            loss, l1_loss, mse_loss = self.compute_loss(rendered_image, target_tensor)
            
            # Backward pass
            loss.backward()
            optimizer.step()
            
            # Logging
            if iteration % log_interval == 0:
                elapsed = time.time() - start_time
                iter_per_sec = (iteration + 1) / elapsed if elapsed > 0 else 0
                
                # Compute metrics
                psnr = -10 * torch.log10(mse_loss).item()
                
                print(f"Iteration {iteration:5d}: Loss={loss.item():.6f}, "
                      f"L1={l1_loss.item():.6f}, PSNR={psnr:.2f}dB, "
                      f"Gaussians={len(self.means)}, {iter_per_sec:.1f} it/s")
                
                # GPU memory info
                if torch.cuda.is_available():
                    memory_used = torch.cuda.memory_allocated() / 1e9
                    memory_total = torch.cuda.get_device_properties(0).total_memory / 1e9
                    print(f"         GPU memory: {memory_used:.1f}/{memory_total:.1f} GB")
            
            # Save checkpoint
            if iteration > 0 and iteration % save_interval == 0:
                self.save_checkpoint(iteration)
        
        print(f"✅ Training completed in {time.time() - start_time:.1f} seconds")
    
    def save_checkpoint(self, iteration: int):
        """Save training checkpoint"""
        checkpoint_dir = Path("/opt/ml/checkpoints")
        checkpoint_dir.mkdir(exist_ok=True)
        
        checkpoint = {
            'iteration': iteration,
            'means': self.means.detach().cpu(),
            'scales': self.scales.detach().cpu(), 
            'rotations': self.rotations.detach().cpu(),
            'features': self.features.detach().cpu(),
            'opacities': self.opacities.detach().cpu(),
        }
        
        torch.save(checkpoint, checkpoint_dir / f"checkpoint_{iteration:06d}.pth")
        print(f"💾 Checkpoint saved at iteration {iteration}")
    
    def export_model(self, output_dir: Path):
        """Export final model"""
        print("📦 Exporting final model...")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save Gaussian parameters
        final_checkpoint = {
            'means': self.means.detach().cpu().numpy(),
            'scales': torch.exp(self.scales).detach().cpu().numpy(),
            'rotations': F.normalize(self.rotations, dim=-1).detach().cpu().numpy(),
            'features': self.features.detach().cpu().numpy(),
            'opacities': torch.sigmoid(self.opacities).detach().cpu().numpy(),
            'n_gaussians': len(self.means),
        }
        
        np.save(output_dir / "gaussians.npy", final_checkpoint)
        
        # Export PLY file for compatibility
        self.export_ply(output_dir / "point_cloud.ply")
        
        # Save training metadata
        metadata = {
            'n_gaussians': len(self.means),
            'device': str(self.device),
            'training_complete': True,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(output_dir / "training_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Model exported with {len(self.means)} Gaussians")
    
    def export_ply(self, output_path: Path):
        """Export Gaussians as PLY file"""
        means = self.means.detach().cpu().numpy()
        scales = torch.exp(self.scales).detach().cpu().numpy()
        rotations = F.normalize(self.rotations, dim=-1).detach().cpu().numpy()
        colors = self.features[:, :, 0].detach().cpu().numpy()  # RGB from SH
        opacities = torch.sigmoid(self.opacities).detach().cpu().numpy()
        
        # Clamp colors to [0, 1] and convert to [0, 255]
        colors = np.clip(colors, 0, 1) * 255
        
        # Write PLY file
        with open(output_path, 'w') as f:
            f.write("ply\n")
            f.write("format ascii 1.0\n")
            f.write(f"element vertex {len(means)}\n")
            f.write("property float x\n")
            f.write("property float y\n")
            f.write("property float z\n")
            f.write("property uchar red\n")
            f.write("property uchar green\n")
            f.write("property uchar blue\n")
            f.write("property float scale_0\n")
            f.write("property float scale_1\n")
            f.write("property float scale_2\n")
            f.write("property float rot_0\n")
            f.write("property float rot_1\n")
            f.write("property float rot_2\n")
            f.write("property float rot_3\n")
            f.write("property float opacity\n")
            f.write("end_header\n")
            
            for i in range(len(means)):
                x, y, z = means[i]
                r, g, b = colors[i].astype(int)
                sx, sy, sz = scales[i]
                qw, qx, qy, qz = rotations[i]
                opacity = opacities[i]
                
                f.write(f"{x:.6f} {y:.6f} {z:.6f} {r} {g} {b} "
                       f"{sx:.6f} {sy:.6f} {sz:.6f} "
                       f"{qw:.6f} {qx:.6f} {qy:.6f} {qz:.6f} {opacity:.6f}\n")


def download_from_s3(s3_uri: str, local_path: Path):
    """Download data from S3"""
    print(f"⬇️  Downloading from S3: {s3_uri}")
    
    # Parse S3 URI
    if not s3_uri.startswith('s3://'):
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    
    parts = s3_uri[5:].split('/', 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ""
    
    s3_client = boto3.client('s3')
    
    # Create local directory
    local_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        if s3_uri.endswith('.zip'):
            # Download and extract ZIP file
            zip_path = local_path.parent / "input.zip"
            s3_client.download_file(bucket, key, str(zip_path))
            
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(local_path)
            
            zip_path.unlink()  # Remove ZIP file
            print(f"✅ Downloaded and extracted: {s3_uri}")
        else:
            # Download directory
            # List objects with prefix
            response = s3_client.list_objects_v2(Bucket=bucket, Prefix=key)
            
            if 'Contents' not in response:
                raise FileNotFoundError(f"No objects found at {s3_uri}")
            
            for obj in response['Contents']:
                obj_key = obj['Key']
                local_file = local_path / obj_key[len(key):].lstrip('/')
                local_file.parent.mkdir(parents=True, exist_ok=True)
                s3_client.download_file(bucket, obj_key, str(local_file))
            
            print(f"✅ Downloaded directory: {s3_uri}")
    
    except Exception as e:
        print(f"❌ Error downloading from S3: {e}")
        raise


def main():
    """Main training function"""
    print("🚀 GSplat 3D Gaussian Splatting Training")
    print("=" * 50)
    
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-path', type=str, default='/opt/ml/input/data/training')
    parser.add_argument('--output-path', type=str, default='/opt/ml/model')
    parser.add_argument('--max-iterations', type=int, default=30000)
    parser.add_argument('--log-interval', type=int, default=1000)
    parser.add_argument('--save-interval', type=int, default=5000)
    args = parser.parse_args()
    
    # Get job configuration
    job_name = os.environ.get('SM_TRAINING_ENV', '{}')
    try:
        job_info = json.loads(job_name)
        job_name = job_info.get('job_name', 'gsplat-training')
    except:
        job_name = os.environ.get('JOB_NAME', 'gsplat-training')
    
    print(f"Job name: {job_name}")
    print(f"Data path: {args.data_path}")
    print(f"Output path: {args.output_path}")
    
    input_path = Path(args.data_path)
    output_path = Path(args.output_path)
    
    # Check for input data
    if not input_path.exists() or not any(input_path.iterdir()):
        print("⚠️  No input data found, cannot proceed with training")
        return 1
    
    try:
        # Training configuration
        config = {
            'max_iterations': int(os.environ.get('MAX_ITERATIONS', args.max_iterations)),
            'log_interval': int(os.environ.get('LOG_INTERVAL', args.log_interval)),
            'save_interval': int(os.environ.get('SAVE_INTERVAL', args.save_interval)),
            'position_lr': 0.00016,
            'feature_lr': 0.0025,
            'opacity_lr': 0.05,
            'scaling_lr': 0.005,
            'rotation_lr': 0.001,
        }
        
        # Initialize trainer
        trainer = GSplatTrainer(config)
        
        # Load COLMAP data
        if not trainer.load_data(input_path):
            print("❌ Failed to load COLMAP data")
            return 1
        
        # Initialize Gaussians
        trainer.initialize_gaussians()
        
        # Train model
        trainer.train()
        
        # Export final model
        trainer.export_model(output_path)
        
        print("🎉 GSplat training completed successfully!")
        return 0
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 