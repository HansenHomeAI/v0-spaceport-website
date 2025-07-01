#!/usr/bin/env python3
"""
COLMAP Format Converter for OpenSfM Output
Converts OpenSfM reconstruction to COLMAP text format for 3DGS compatibility
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OpenSfMToCOLMAPConverter:
    """Convert OpenSfM reconstruction to COLMAP format"""
    
    def __init__(self, opensfm_path: Path, output_path: Path):
        """
        Initialize converter
        
        Args:
            opensfm_path: Path to OpenSfM reconstruction directory
            output_path: Path to output COLMAP format files
        """
        self.opensfm_path = Path(opensfm_path)
        self.output_path = Path(output_path)
        self.reconstruction = None
        
        logger.info(f"🔄 Initializing OpenSfM to COLMAP converter")
        logger.info(f"   Input: {opensfm_path}")
        logger.info(f"   Output: {output_path}")
    
    def load_opensfm_reconstruction(self) -> Dict:
        """Load OpenSfM reconstruction data"""
        reconstruction_file = self.opensfm_path / "reconstruction.json"
        
        if not reconstruction_file.exists():
            raise FileNotFoundError(f"OpenSfM reconstruction not found: {reconstruction_file}")
        
        try:
            with open(reconstruction_file, 'r') as f:
                reconstructions = json.load(f)
            
            if not reconstructions:
                raise ValueError("No reconstructions found in OpenSfM output")
            
            # Use the first (largest) reconstruction
            self.reconstruction = reconstructions[0]
            
            logger.info(f"✅ Loaded OpenSfM reconstruction:")
            logger.info(f"   Cameras: {len(self.reconstruction.get('cameras', {}))}")
            logger.info(f"   Shots: {len(self.reconstruction.get('shots', {}))}")
            logger.info(f"   Points: {len(self.reconstruction.get('points', {}))}")
            
            return self.reconstruction
            
        except Exception as e:
            logger.error(f"❌ Failed to load OpenSfM reconstruction: {e}")
            raise
    
    def convert_cameras(self) -> None:
        """Convert OpenSfM cameras to COLMAP cameras.txt format"""
        if not self.reconstruction:
            raise ValueError("Reconstruction not loaded")
        
        cameras_file = self.output_path / "cameras.txt"
        cameras_data = self.reconstruction.get('cameras', {})
        
        logger.info(f"🔄 Converting {len(cameras_data)} cameras to COLMAP format")
        
        with open(cameras_file, 'w') as f:
            f.write("# Camera list with one line of data per camera:\n")
            f.write("#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
            f.write("# Number of cameras: {}\n".format(len(cameras_data)))
            
            for camera_id, camera_data in cameras_data.items():
                # Extract camera parameters
                width = int(camera_data.get('width', 1920))
                height = int(camera_data.get('height', 1080))
                
                # Convert OpenSfM camera model to COLMAP
                projection_type = camera_data.get('projection_type', 'perspective')
                
                if projection_type == 'perspective':
                    # OpenSfM perspective camera
                    focal = camera_data.get('focal', 1.0)
                    k1 = camera_data.get('k1', 0.0)
                    k2 = camera_data.get('k2', 0.0)
                    
                    # Convert normalized focal to pixel focal length
                    focal_pixels = focal * max(width, height)
                    
                    # COLMAP RADIAL model: f, cx, cy, k1, k2
                    model = "RADIAL"
                    cx = width / 2.0
                    cy = height / 2.0
                    params = [focal_pixels, cx, cy, k1, k2]
                    
                elif projection_type == 'fisheye':
                    # OpenSfM fisheye camera
                    focal = camera_data.get('focal', 1.0)
                    k1 = camera_data.get('k1', 0.0)
                    k2 = camera_data.get('k2', 0.0)
                    
                    focal_pixels = focal * max(width, height)
                    
                    # COLMAP OPENCV_FISHEYE model
                    model = "OPENCV_FISHEYE"
                    cx = width / 2.0
                    cy = height / 2.0
                    params = [focal_pixels, focal_pixels, cx, cy, k1, k2, 0.0, 0.0]
                    
                else:
                    # Default to simple pinhole
                    model = "SIMPLE_PINHOLE"
                    focal_pixels = max(width, height) * 1.2  # Reasonable default
                    cx = width / 2.0
                    cy = height / 2.0
                    params = [focal_pixels, cx, cy]
                
                # Format: CAMERA_ID MODEL WIDTH HEIGHT PARAMS[]
                params_str = " ".join([f"{p:.6f}" for p in params])
                f.write(f"{camera_id} {model} {width} {height} {params_str}\n")
        
        logger.info(f"✅ Generated cameras.txt with {len(cameras_data)} cameras")
    
    def convert_images(self) -> None:
        """Convert OpenSfM shots to COLMAP images.txt format"""
        if not self.reconstruction:
            raise ValueError("Reconstruction not loaded")
        
        images_file = self.output_path / "images.txt"
        shots_data = self.reconstruction.get('shots', {})
        
        logger.info(f"🔄 Converting {len(shots_data)} shots to COLMAP format")
        
        with open(images_file, 'w') as f:
            f.write("# Image list with two lines of data per image:\n")
            f.write("#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
            f.write("#   POINTS2D[] as (X, Y, POINT3D_ID)\n")
            f.write("# Number of images: {}, mean observations per image: 0\n".format(len(shots_data)))
            
            image_id = 1
            for shot_name, shot_data in shots_data.items():
                # Extract camera pose
                rotation = shot_data.get('rotation', [0.0, 0.0, 0.0])
                translation = shot_data.get('translation', [0.0, 0.0, 0.0])
                camera_id = shot_data.get('camera', list(self.reconstruction.get('cameras', {}).keys())[0])
                
                # Convert OpenSfM rotation (axis-angle) to quaternion
                quat = self._axis_angle_to_quaternion(rotation)
                qw, qx, qy, qz = quat
                
                # OpenSfM uses camera-to-world, COLMAP uses world-to-camera
                # Need to invert the transformation
                R = self._quaternion_to_rotation_matrix(quat)
                t = np.array(translation)
                
                # Invert: [R|t] -> [R^T | -R^T * t]
                R_inv = R.T
                t_inv = -R_inv @ t
                
                # Convert back to quaternion
                quat_inv = self._rotation_matrix_to_quaternion(R_inv)
                qw, qx, qy, qz = quat_inv
                tx, ty, tz = t_inv
                
                # Write image line
                f.write(f"{image_id} {qw:.9f} {qx:.9f} {qy:.9f} {qz:.9f} "
                       f"{tx:.6f} {ty:.6f} {tz:.6f} {camera_id} {shot_name}\n")
                
                # Write empty points2D line (we'll populate this from tracks if available)
                f.write("\n")
                
                image_id += 1
        
        logger.info(f"✅ Generated images.txt with {len(shots_data)} images")
    
    def convert_points(self) -> None:
        """Convert OpenSfM points to COLMAP points3D.txt format"""
        if not self.reconstruction:
            raise ValueError("Reconstruction not loaded")
        
        points_file = self.output_path / "points3D.txt"
        points_data = self.reconstruction.get('points', {})
        
        logger.info(f"🔄 Converting {len(points_data)} points to COLMAP format")
        
        with open(points_file, 'w') as f:
            f.write("# 3D point list with one line of data per point:\n")
            f.write("#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
            f.write("# Number of points: {}, mean track length: 0\n".format(len(points_data)))
            
            point_id = 1
            for point_key, point_data in points_data.items():
                # Extract 3D coordinates
                coordinates = point_data.get('coordinates', [0.0, 0.0, 0.0])
                x, y, z = coordinates
                
                # Extract color (default to white if not available)
                color = point_data.get('color', [255, 255, 255])
                r, g, b = [int(c) for c in color]
                
                # Error estimate (default to small value)
                error = 0.5
                
                # Track information (which images see this point)
                track = []
                # Note: OpenSfM tracks are more complex, simplified here
                
                # Format: POINT3D_ID X Y Z R G B ERROR TRACK[]
                track_str = " ".join([f"{img_id} {pt_idx}" for img_id, pt_idx in track])
                f.write(f"{point_id} {x:.6f} {y:.6f} {z:.6f} {r} {g} {b} {error:.6f} {track_str}\n")
                
                point_id += 1
        
        logger.info(f"✅ Generated points3D.txt with {len(points_data)} points")
    
    def _axis_angle_to_quaternion(self, axis_angle: List[float]) -> np.ndarray:
        """Convert axis-angle rotation to quaternion"""
        axis_angle = np.array(axis_angle)
        angle = np.linalg.norm(axis_angle)
        
        if angle < 1e-8:
            return np.array([1.0, 0.0, 0.0, 0.0])  # Identity quaternion
        
        axis = axis_angle / angle
        half_angle = angle / 2.0
        
        w = np.cos(half_angle)
        xyz = np.sin(half_angle) * axis
        
        return np.array([w, xyz[0], xyz[1], xyz[2]])
    
    def _quaternion_to_rotation_matrix(self, quat: np.ndarray) -> np.ndarray:
        """Convert quaternion to rotation matrix"""
        qw, qx, qy, qz = quat
        
        # Normalize quaternion
        norm = np.sqrt(qw*qw + qx*qx + qy*qy + qz*qz)
        qw, qx, qy, qz = qw/norm, qx/norm, qy/norm, qz/norm
        
        # Convert to rotation matrix
        R = np.array([
            [1 - 2*(qy*qy + qz*qz), 2*(qx*qy - qw*qz), 2*(qx*qz + qw*qy)],
            [2*(qx*qy + qw*qz), 1 - 2*(qx*qx + qz*qz), 2*(qy*qz - qw*qx)],
            [2*(qx*qz - qw*qy), 2*(qy*qz + qw*qx), 1 - 2*(qx*qx + qy*qy)]
        ])
        
        return R
    
    def _rotation_matrix_to_quaternion(self, R: np.ndarray) -> np.ndarray:
        """Convert rotation matrix to quaternion"""
        trace = np.trace(R)
        
        if trace > 0:
            s = np.sqrt(trace + 1.0) * 2  # s = 4 * qw
            qw = 0.25 * s
            qx = (R[2, 1] - R[1, 2]) / s
            qy = (R[0, 2] - R[2, 0]) / s
            qz = (R[1, 0] - R[0, 1]) / s
        elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
            s = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2  # s = 4 * qx
            qw = (R[2, 1] - R[1, 2]) / s
            qx = 0.25 * s
            qy = (R[0, 1] + R[1, 0]) / s
            qz = (R[0, 2] + R[2, 0]) / s
        elif R[1, 1] > R[2, 2]:
            s = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2  # s = 4 * qy
            qw = (R[0, 2] - R[2, 0]) / s
            qx = (R[0, 1] + R[1, 0]) / s
            qy = 0.25 * s
            qz = (R[1, 2] + R[2, 1]) / s
        else:
            s = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2  # s = 4 * qz
            qw = (R[1, 0] - R[0, 1]) / s
            qx = (R[0, 2] + R[2, 0]) / s
            qy = (R[1, 2] + R[2, 1]) / s
            qz = 0.25 * s
        
        return np.array([qw, qx, qy, qz])
    
    def create_reference_point_cloud(self) -> None:
        """Create reference point cloud PLY file"""
        if not self.reconstruction:
            raise ValueError("Reconstruction not loaded")
        
        ply_file = self.output_path / "sparse_points.ply"
        points_data = self.reconstruction.get('points', {})
        
        logger.info(f"☁️ Creating reference point cloud with {len(points_data)} points")
        
        with open(ply_file, 'w') as f:
            f.write("ply\n")
            f.write("format ascii 1.0\n")
            f.write(f"element vertex {len(points_data)}\n")
            f.write("property float x\n")
            f.write("property float y\n")
            f.write("property float z\n")
            f.write("property uchar red\n")
            f.write("property uchar green\n")
            f.write("property uchar blue\n")
            f.write("end_header\n")
            
            for point_data in points_data.values():
                coordinates = point_data.get('coordinates', [0.0, 0.0, 0.0])
                color = point_data.get('color', [255, 255, 255])
                
                x, y, z = coordinates
                r, g, b = [int(c) for c in color]
                
                f.write(f"{x:.6f} {y:.6f} {z:.6f} {r} {g} {b}\n")
        
        logger.info(f"✅ Generated reference point cloud: {ply_file}")
    
    def validate_conversion(self) -> Dict:
        """Validate the COLMAP conversion"""
        validation_results = {
            'cameras_file_exists': False,
            'images_file_exists': False,
            'points_file_exists': False,
            'ply_file_exists': False,
            'camera_count': 0,
            'image_count': 0,
            'point_count': 0,
            'quality_check_passed': False
        }
        
        try:
            # Check file existence
            cameras_file = self.output_path / "cameras.txt"
            images_file = self.output_path / "images.txt"
            points_file = self.output_path / "points3D.txt"
            ply_file = self.output_path / "sparse_points.ply"
            
            validation_results['cameras_file_exists'] = cameras_file.exists()
            validation_results['images_file_exists'] = images_file.exists()
            validation_results['points_file_exists'] = points_file.exists()
            validation_results['ply_file_exists'] = ply_file.exists()
            
            # Count entries
            if cameras_file.exists():
                with open(cameras_file, 'r') as f:
                    camera_count = sum(1 for line in f if line.strip() and not line.startswith('#'))
                validation_results['camera_count'] = camera_count
            
            if images_file.exists():
                with open(images_file, 'r') as f:
                    lines = [line for line in f if line.strip() and not line.startswith('#')]
                    image_count = len(lines) // 2  # Two lines per image
                validation_results['image_count'] = image_count
            
            if points_file.exists():
                with open(points_file, 'r') as f:
                    point_count = sum(1 for line in f if line.strip() and not line.startswith('#'))
                validation_results['point_count'] = point_count
            
            # Quality check (minimum requirements for 3DGS)
            min_points_required = 1000  # Same as current COLMAP pipeline
            validation_results['quality_check_passed'] = (
                validation_results['point_count'] >= min_points_required and
                validation_results['image_count'] > 0 and
                validation_results['camera_count'] > 0
            )
            
            logger.info(f"🔍 Validation Results:")
            logger.info(f"   Cameras: {validation_results['camera_count']}")
            logger.info(f"   Images: {validation_results['image_count']}")
            logger.info(f"   Points: {validation_results['point_count']}")
            logger.info(f"   Quality Check: {'✅ PASSED' if validation_results['quality_check_passed'] else '❌ FAILED'}")
            
            if not validation_results['quality_check_passed']:
                logger.warning(f"⚠️ Quality check failed: Need at least {min_points_required} points for 3DGS")
            
        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
        
        return validation_results
    
    def convert_full_reconstruction(self) -> Dict:
        """Convert complete OpenSfM reconstruction to COLMAP format"""
        logger.info(f"🚀 Starting full OpenSfM to COLMAP conversion")
        
        # Create output directory
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Load reconstruction
        self.load_opensfm_reconstruction()
        
        # Convert all components
        self.convert_cameras()
        self.convert_images()
        self.convert_points()
        self.create_reference_point_cloud()
        
        # Validate conversion
        validation = self.validate_conversion()
        
        logger.info(f"✅ Full conversion completed")
        return validation


def main():
    """Test converter functionality"""
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python colmap_converter.py <opensfm_dir> <output_dir>")
        sys.exit(1)
    
    opensfm_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
    # Initialize converter
    converter = OpenSfMToCOLMAPConverter(opensfm_dir, output_dir)
    
    # Run conversion
    validation = converter.convert_full_reconstruction()
    
    # Print results
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main() 