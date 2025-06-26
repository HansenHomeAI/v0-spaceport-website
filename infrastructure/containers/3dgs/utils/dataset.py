#!/usr/bin/env python3
"""
Dataset utilities for gsplat 3D Gaussian Splatting training
Prepares COLMAP data for training with gsplat
"""

import os
import numpy as np
import torch
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image

from .colmap_loader import load_colmap_data, colmap_to_nerf_poses, get_camera_intrinsics


class SpaceportDataset:
    """Dataset class for gsplat training"""
    
    def __init__(self, data_dir: Path, images_dir: Optional[Path] = None):
        """
        Initialize dataset
        
        Args:
            data_dir: Path to COLMAP sparse reconstruction
            images_dir: Path to images directory (if different from data_dir/images)
        """
        self.data_dir = Path(data_dir)
        self.images_dir = images_dir if images_dir else self.data_dir / "images"
        
        # Load COLMAP data
        self.cameras, self.images, self.points3d = load_colmap_data(self.data_dir)
        
        # Convert to training format
        self.poses = colmap_to_nerf_poses(self.images)
        self.image_paths = self._get_image_paths()
        
        print(f"📊 Dataset initialized:")
        print(f"   Images: {len(self.images)}")
        print(f"   Cameras: {len(self.cameras)}")
        print(f"   3D Points: {len(self.points3d)}")
    
    def _get_image_paths(self) -> List[Path]:
        """Get sorted list of image paths"""
        image_paths = []
        
        for image_id in sorted(self.images.keys()):
            image = self.images[image_id]
            image_path = self.images_dir / image.name
            
            if not image_path.exists():
                # Try common extensions
                base_name = image_path.stem
                for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
                    candidate = self.images_dir / f"{base_name}{ext}"
                    if candidate.exists():
                        image_path = candidate
                        break
            
            if image_path.exists():
                image_paths.append(image_path)
            else:
                print(f"Warning: Image not found: {image.name}")
        
        return image_paths
    
    def get_camera_params(self) -> Dict:
        """Get camera parameters for training"""
        # Assume single camera for now (most common case)
        camera_id = list(self.cameras.keys())[0]
        camera = self.cameras[camera_id]
        
        fx, fy, cx, cy = get_camera_intrinsics(self.cameras, camera_id)
        
        return {
            'width': camera.width,
            'height': camera.height,
            'fx': fx,
            'fy': fy,
            'cx': cx,
            'cy': cy,
            'camera_model': camera.model
        }
    
    def get_initial_points(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get initial 3D points and colors from COLMAP
        
        Returns:
            Tuple of (points, colors) as numpy arrays
        """
        if len(self.points3d) == 0:
            print("Warning: No 3D points found, creating dummy points")
            # Create some dummy points for initialization
            points = np.random.randn(1000, 3) * 2.0
            colors = np.random.randint(0, 255, (1000, 3)).astype(np.uint8)
            return points, colors
        
        points = []
        colors = []
        
        for point3d in self.points3d.values():
            points.append(point3d.xyz)
            colors.append(point3d.rgb)
        
        points = np.array(points)
        colors = np.array(colors)
        
        print(f"📍 Initial points: {len(points)}")
        print(f"   Point cloud bounds: {points.min(axis=0)} to {points.max(axis=0)}")
        
        return points, colors
    
    def load_image(self, idx: int, downscale: int = 1) -> np.ndarray:
        """
        Load and preprocess image
        
        Args:
            idx: Image index
            downscale: Downscaling factor
            
        Returns:
            Image as numpy array [H, W, 3] in range [0, 1]
        """
        if idx >= len(self.image_paths):
            raise IndexError(f"Image index {idx} out of range")
        
        image_path = self.image_paths[idx]
        image = Image.open(image_path).convert('RGB')
        
        if downscale > 1:
            width, height = image.size
            new_width = width // downscale
            new_height = height // downscale
            image = image.resize((new_width, new_height), Image.LANCZOS)
        
        # Convert to numpy array and normalize to [0, 1]
        image_np = np.array(image).astype(np.float32) / 255.0
        
        return image_np
    
    def get_training_views(self, split_ratio: float = 0.9) -> Tuple[List[int], List[int]]:
        """
        Split dataset into training and validation views
        
        Args:
            split_ratio: Ratio of training views
            
        Returns:
            Tuple of (train_indices, val_indices)
        """
        n_images = len(self.image_paths)
        n_train = int(n_images * split_ratio)
        
        indices = list(range(n_images))
        np.random.shuffle(indices)
        
        train_indices = indices[:n_train]
        val_indices = indices[n_train:]
        
        print(f"📊 Dataset split:")
        print(f"   Training views: {len(train_indices)}")
        print(f"   Validation views: {len(val_indices)}")
        
        return train_indices, val_indices
    
    def compute_scene_bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute scene bounding box from camera positions and 3D points
        
        Returns:
            Tuple of (min_bounds, max_bounds)
        """
        # Get camera positions
        camera_positions = self.poses[:, :3, 3]
        
        # Get 3D point positions
        if len(self.points3d) > 0:
            point_positions = np.array([p.xyz for p in self.points3d.values()])
            all_positions = np.vstack([camera_positions, point_positions])
        else:
            all_positions = camera_positions
        
        min_bounds = all_positions.min(axis=0)
        max_bounds = all_positions.max(axis=0)
        
        # Add some padding
        padding = (max_bounds - min_bounds) * 0.1
        min_bounds -= padding
        max_bounds += padding
        
        print(f"🗺️  Scene bounds: {min_bounds} to {max_bounds}")
        
        return min_bounds, max_bounds


def prepare_gsplat_data(data_dir: Path, output_dir: Path, downscale: int = 1):
    """
    Prepare COLMAP data for gsplat training
    
    Args:
        data_dir: Path to COLMAP sparse reconstruction
        output_dir: Path to save prepared data
        downscale: Image downscaling factor
    """
    print(f"🔄 Preparing gsplat data...")
    print(f"   Input: {data_dir}")
    print(f"   Output: {output_dir}")
    print(f"   Downscale: {downscale}x")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load dataset
    dataset = GSplatDataset(data_dir)
    
    # Get camera parameters
    camera_params = dataset.get_camera_params()
    
    # Adjust for downscaling
    if downscale > 1:
        camera_params['width'] //= downscale
        camera_params['height'] //= downscale
        camera_params['fx'] /= downscale
        camera_params['fy'] /= downscale
        camera_params['cx'] /= downscale
        camera_params['cy'] /= downscale
    
    # Save camera parameters
    np.save(output_dir / "camera_params.npy", camera_params)
    
    # Save poses
    np.save(output_dir / "poses.npy", dataset.poses)
    
    # Get initial points
    points, colors = dataset.get_initial_points()
    np.save(output_dir / "initial_points.npy", points)
    np.save(output_dir / "initial_colors.npy", colors)
    
    # Compute scene bounds
    min_bounds, max_bounds = dataset.compute_scene_bounds()
    np.save(output_dir / "scene_bounds.npy", {'min': min_bounds, 'max': max_bounds})
    
    # Process and save images
    images_output_dir = output_dir / "images"
    images_output_dir.mkdir(exist_ok=True)
    
    for i, image_path in enumerate(dataset.image_paths):
        image = dataset.load_image(i, downscale)
        output_path = images_output_dir / f"{i:04d}.png"
        
        # Convert back to PIL and save
        image_pil = Image.fromarray((image * 255).astype(np.uint8))
        image_pil.save(output_path)
    
    print(f"✅ Data preparation complete!")
    print(f"   Saved {len(dataset.image_paths)} images")
    print(f"   Saved camera parameters and poses")
    print(f"   Saved {len(points)} initial 3D points") 