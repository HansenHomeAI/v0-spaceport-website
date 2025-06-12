#!/usr/bin/env python3
"""
COLMAP Data Loader for gsplat 3D Gaussian Splatting
Parses COLMAP sparse reconstruction output for training
"""

import os
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import struct


class COLMAPCamera:
    """COLMAP camera model"""
    def __init__(self, camera_id, model, width, height, params):
        self.camera_id = camera_id
        self.model = model
        self.width = width
        self.height = height
        self.params = params


class COLMAPImage:
    """COLMAP image with pose"""
    def __init__(self, image_id, qvec, tvec, camera_id, name, points2d):
        self.image_id = image_id
        self.qvec = qvec  # quaternion
        self.tvec = tvec  # translation
        self.camera_id = camera_id
        self.name = name
        self.points2d = points2d


class COLMAPPoint3D:
    """COLMAP 3D point"""
    def __init__(self, point3d_id, xyz, rgb, error, track):
        self.point3d_id = point3d_id
        self.xyz = xyz
        self.rgb = rgb
        self.error = error
        self.track = track


def read_cameras_text(path: Path) -> Dict[int, COLMAPCamera]:
    """Read COLMAP cameras.txt file"""
    cameras = {}
    
    if not path.exists():
        print(f"Warning: cameras.txt not found at {path}")
        return cameras
    
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or len(line) == 0:
                continue
            
            parts = line.split()
            camera_id = int(parts[0])
            model = parts[1]
            width = int(parts[2])
            height = int(parts[3])
            params = [float(p) for p in parts[4:]]
            
            cameras[camera_id] = COLMAPCamera(camera_id, model, width, height, params)
    
    return cameras


def read_images_text(path: Path) -> Dict[int, COLMAPImage]:
    """Read COLMAP images.txt file"""
    images = {}
    
    if not path.exists():
        print(f"Warning: images.txt not found at {path}")
        return images
    
    with open(path, 'r') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#') or len(line) == 0:
            i += 1
            continue
        
        # Image line
        parts = line.split()
        image_id = int(parts[0])
        qvec = np.array([float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])])
        tvec = np.array([float(parts[5]), float(parts[6]), float(parts[7])])
        camera_id = int(parts[8])
        name = parts[9] if len(parts) > 9 else f"image_{image_id}.jpg"
        
        # Points2D line (next line)
        i += 1
        points2d = []
        if i < len(lines):
            points_line = lines[i].strip()
            if points_line and not points_line.startswith('#'):
                points_parts = points_line.split()
                for j in range(0, len(points_parts), 3):
                    if j + 2 < len(points_parts):
                        x = float(points_parts[j])
                        y = float(points_parts[j + 1])
                        point3d_id = int(points_parts[j + 2]) if points_parts[j + 2] != '-1' else -1
                        points2d.append((x, y, point3d_id))
        
        images[image_id] = COLMAPImage(image_id, qvec, tvec, camera_id, name, points2d)
        i += 1
    
    return images


def read_points3d_text(path: Path) -> Dict[int, COLMAPPoint3D]:
    """Read COLMAP points3D.txt file"""
    points3d = {}
    
    if not path.exists():
        print(f"Warning: points3D.txt not found at {path}")
        return points3d
    
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or len(line) == 0:
                continue
            
            parts = line.split()
            point3d_id = int(parts[0])
            xyz = np.array([float(parts[1]), float(parts[2]), float(parts[3])])
            rgb = np.array([int(parts[4]), int(parts[5]), int(parts[6])])
            error = float(parts[7])
            
            # Track information (image_id, point2d_id pairs)
            track = []
            for i in range(8, len(parts), 2):
                if i + 1 < len(parts):
                    image_id = int(parts[i])
                    point2d_id = int(parts[i + 1])
                    track.append((image_id, point2d_id))
            
            points3d[point3d_id] = COLMAPPoint3D(point3d_id, xyz, rgb, error, track)
    
    return points3d


def qvec2rotmat(qvec: np.ndarray) -> np.ndarray:
    """Convert quaternion to rotation matrix"""
    qvec = qvec / np.linalg.norm(qvec)  # Normalize
    w, x, y, z = qvec
    
    return np.array([
        [1 - 2*y*y - 2*z*z, 2*x*y - 2*z*w, 2*x*z + 2*y*w],
        [2*x*y + 2*z*w, 1 - 2*x*x - 2*z*z, 2*y*z - 2*x*w],
        [2*x*z - 2*y*w, 2*y*z + 2*x*w, 1 - 2*x*x - 2*y*y]
    ])


def load_colmap_data(colmap_path: Path) -> Tuple[Dict, Dict, Dict]:
    """
    Load COLMAP sparse reconstruction data
    
    Args:
        colmap_path: Path to COLMAP sparse directory
        
    Returns:
        Tuple of (cameras, images, points3d) dictionaries
    """
    print(f"🔍 Loading COLMAP data from: {colmap_path}")
    
    # Check if directory exists
    if not colmap_path.exists():
        raise FileNotFoundError(f"COLMAP directory not found: {colmap_path}")
    
    # Load cameras
    cameras_file = colmap_path / "cameras.txt"
    cameras = read_cameras_text(cameras_file)
    print(f"📷 Loaded {len(cameras)} cameras")
    
    # Load images
    images_file = colmap_path / "images.txt" 
    images = read_images_text(images_file)
    print(f"🖼️  Loaded {len(images)} images")
    
    # Load 3D points
    points3d_file = colmap_path / "points3D.txt"
    points3d = read_points3d_text(points3d_file)
    print(f"📍 Loaded {len(points3d)} 3D points")
    
    return cameras, images, points3d


def colmap_to_nerf_poses(images: Dict[int, COLMAPImage]) -> np.ndarray:
    """
    Convert COLMAP poses to NeRF/gsplat format
    
    Args:
        images: Dictionary of COLMAP images
        
    Returns:
        Array of poses in NeRF format [N, 4, 4]
    """
    poses = []
    
    for image_id in sorted(images.keys()):
        image = images[image_id]
        
        # Convert quaternion to rotation matrix
        R = qvec2rotmat(image.qvec)
        
        # COLMAP uses [R|t] where X' = RX + t
        # NeRF uses camera-to-world transform
        # Need to invert: [R|t] -> [R^T | -R^T t]
        pose = np.eye(4)
        pose[:3, :3] = R.T
        pose[:3, 3] = -R.T @ image.tvec
        
        poses.append(pose)
    
    return np.array(poses)


def get_camera_intrinsics(cameras: Dict[int, COLMAPCamera], camera_id: int) -> Tuple[float, float, float, float]:
    """
    Extract camera intrinsics from COLMAP camera
    
    Args:
        cameras: Dictionary of COLMAP cameras
        camera_id: Camera ID to extract intrinsics for
        
    Returns:
        Tuple of (fx, fy, cx, cy)
    """
    if camera_id not in cameras:
        raise ValueError(f"Camera ID {camera_id} not found")
    
    camera = cameras[camera_id]
    
    if camera.model in ["PINHOLE"]:
        fx, fy, cx, cy = camera.params[:4]
    elif camera.model in ["SIMPLE_PINHOLE"]:
        f, cx, cy = camera.params[:3]
        fx = fy = f
    elif camera.model in ["RADIAL", "SIMPLE_RADIAL"]:
        f, cx, cy = camera.params[:3]
        fx = fy = f
    else:
        # Default fallback
        print(f"Warning: Unknown camera model {camera.model}, using default intrinsics")
        fx = fy = max(camera.width, camera.height) * 1.2  # Rough estimate
        cx = camera.width / 2
        cy = camera.height / 2
    
    return fx, fy, cx, cy 