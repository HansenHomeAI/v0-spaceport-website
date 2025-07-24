#!/usr/bin/env python3
"""
COLMAP Format Converter for OpenSfM Output
Converts OpenSfM reconstruction to COLMAP format for 3DGS compatibility
Generates proper dataset structure: my_dataset/images/ + sparse/0/cameras.bin etc.
"""

import os
import json
import numpy as np
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging
import tempfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OpenSfMToCOLMAPConverter:
    """Convert OpenSfM reconstruction to COLMAP format with proper 2D-3D correspondences"""
    
    def __init__(self, opensfm_path: Path, output_path: Path):
        """
        Initialize converter
        
        Args:
            opensfm_path: Path to OpenSfM reconstruction directory
            output_path: Path to output dataset directory (will create my_dataset structure)
        """
        self.opensfm_path = Path(opensfm_path)
        self.output_path = Path(output_path)
        
        # Create proper dataset structure
        self.images_dir = self.output_path / "images"
        self.sparse_dir = self.output_path / "sparse" / "0"
        
        self.reconstruction = None
        self.tracks = {}
        self.camera_id_mapping = {}
        self.image_id_mapping = {}
        self.point_id_mapping = {}
        
        logger.info(f"🔄 Initializing OpenSfM to COLMAP converter")
        logger.info(f"   Input: {opensfm_path}")
        logger.info(f"   Output: {output_path}")
        logger.info(f"   Target structure: my_dataset/images/ + sparse/0/")
    
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
    
    def extract_tracks(self) -> None:
        """Extract 2D-3D correspondence tracks from OpenSfM data"""
        logger.info(f"🔄 Extracting 2D-3D correspondence tracks")
        
        points_data = self.reconstruction.get('points', {})
        shots_data = self.reconstruction.get('shots', {})
        
        # Initialize tracking structures
        self.image_observations = {}  # image_id -> [(x, y, point3d_id), ...]
        self.point_tracks = {}        # point3d_id -> [(image_id, feature_idx), ...]
        
        for shot_name in shots_data.keys():
            self.image_observations[shot_name] = []
        
        point_id = 1
        for opensfm_point_id, point_data in points_data.items():
            self.point_id_mapping[opensfm_point_id] = point_id
            self.point_tracks[point_id] = []
            
            # Extract observations from OpenSfM point data
            observations = point_data.get('observations', {})
            
            feature_idx = 0
            for shot_name, obs_data in observations.items():
                if shot_name in shots_data:
                    # obs_data typically contains [x, y] normalized coordinates
                    if isinstance(obs_data, list) and len(obs_data) >= 2:
                        x, y = obs_data[0], obs_data[1]
                        
                        # Convert normalized coordinates to pixel coordinates
                        camera_id = shots_data[shot_name].get('camera')
                        if camera_id in self.reconstruction.get('cameras', {}):
                            camera_data = self.reconstruction['cameras'][camera_id]
                            width = camera_data.get('width', 4000)
                            height = camera_data.get('height', 2250)
                            
                            # Convert from normalized [-1,1] or [0,1] to pixel coordinates
                            if abs(x) <= 1.0 and abs(y) <= 1.0:
                                if x >= 0 and y >= 0:  # [0,1] normalized
                                    pixel_x = x * width
                                    pixel_y = y * height
                                else:  # [-1,1] normalized
                                    pixel_x = (x + 1) * width / 2
                                    pixel_y = (y + 1) * height / 2
                            else:  # Already in pixel coordinates
                                pixel_x = x
                                pixel_y = y
                            
                            # Add to image observations
                            self.image_observations[shot_name].append((pixel_x, pixel_y, point_id))
                            
                            # Add to point tracks
                            self.point_tracks[point_id].append((shot_name, feature_idx))
                            feature_idx += 1
            
            point_id += 1
        
        total_observations = sum(len(obs) for obs in self.image_observations.values())
        logger.info(f"✅ Extracted {total_observations} 2D-3D correspondences")
        logger.info(f"   Average observations per image: {total_observations / len(self.image_observations):.1f}")
    
    def convert_cameras(self) -> None:
        """Convert OpenSfM cameras to COLMAP cameras.txt format"""
        cameras_file = self.sparse_dir / "cameras.txt"
        cameras_data = self.reconstruction.get('cameras', {})
        
        logger.info(f"🔄 Converting {len(cameras_data)} cameras to COLMAP format")
        
        with open(cameras_file, 'w') as f:
            f.write("# Camera list with one line of data per camera:\n")
            f.write("#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
            f.write("# Number of cameras: {}\n".format(len(cameras_data)))
            
            numeric_camera_id = 1
            for camera_id, camera_data in cameras_data.items():
                self.camera_id_mapping[camera_id] = numeric_camera_id
                
                width = int(camera_data.get('width', 4000))
                height = int(camera_data.get('height', 2250))
                
                projection_type = camera_data.get('projection_type', 'perspective')
                
                if projection_type == 'perspective':
                    focal = camera_data.get('focal', 1.0)
                    k1 = camera_data.get('k1', 0.0)
                    k2 = camera_data.get('k2', 0.0)
                    
                    focal_pixels = focal * max(width, height)
                    
                    model = "RADIAL"
                    cx = width / 2.0
                    cy = height / 2.0
                    params = [focal_pixels, cx, cy, k1, k2]
                    
                else:
                    # Default to simple pinhole
                    model = "SIMPLE_PINHOLE"
                    focal_pixels = max(width, height) * 1.2
                    cx = width / 2.0
                    cy = height / 2.0
                    params = [focal_pixels, cx, cy]
                
                params_str = " ".join([f"{p:.6f}" for p in params])
                f.write(f"{numeric_camera_id} {model} {width} {height} {params_str}\n")
                
                numeric_camera_id += 1
        
        logger.info(f"✅ Generated cameras.txt with {len(cameras_data)} cameras")
    
    def convert_images(self) -> None:
        """Convert OpenSfM shots to COLMAP images.txt format with 2D-3D correspondences"""
        images_file = self.sparse_dir / "images.txt"
        shots_data = self.reconstruction.get('shots', {})
        
        logger.info(f"🔄 Converting {len(shots_data)} shots to COLMAP format with correspondences")
        
        with open(images_file, 'w') as f:
            f.write("# Image list with two lines of data per image:\n")
            f.write("#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
            f.write("#   POINTS2D[] as (X, Y, POINT3D_ID)\n")
            
            total_observations = sum(len(self.image_observations.get(shot_name, [])) for shot_name in shots_data.keys())
            avg_observations = total_observations / len(shots_data) if shots_data else 0
            f.write("# Number of images: {}, mean observations per image: {:.1f}\n".format(len(shots_data), avg_observations))
            
            image_id = 1
            for shot_name, shot_data in shots_data.items():
                self.image_id_mapping[shot_name] = image_id
                
                # Extract camera pose
                rotation = shot_data.get('rotation', [0.0, 0.0, 0.0])
                translation = shot_data.get('translation', [0.0, 0.0, 0.0])
                opensfm_camera_id = shot_data.get('camera', list(self.reconstruction.get('cameras', {}).keys())[0])
                
                numeric_camera_id = self.camera_id_mapping.get(opensfm_camera_id, 1)
                
                # Convert OpenSfM rotation (axis-angle) to quaternion
                quat = self._axis_angle_to_quaternion(rotation)
                qw, qx, qy, qz = quat
                
                # OpenSfM uses camera-to-world, COLMAP uses world-to-camera
                R = self._quaternion_to_rotation_matrix(quat)
                t = np.array(translation)
                
                # Invert transformation
                R_inv = R.T
                t_inv = -R_inv @ t
                
                quat_inv = self._rotation_matrix_to_quaternion(R_inv)
                qw, qx, qy, qz = quat_inv
                tx, ty, tz = t_inv
                
                # Write image line
                f.write(f"{image_id} {qw:.9f} {qx:.9f} {qy:.9f} {qz:.9f} "
                       f"{tx:.6f} {ty:.6f} {tz:.6f} {numeric_camera_id} {shot_name}\n")
                
                # Write 2D-3D correspondences
                observations = self.image_observations.get(shot_name, [])
                points2d_str = " ".join([f"{x:.6f} {y:.6f} {point3d_id}" for x, y, point3d_id in observations])
                f.write(f"{points2d_str}\n")
                
                image_id += 1
        
        logger.info(f"✅ Generated images.txt with {len(shots_data)} images and correspondences")
    
    def convert_points(self) -> None:
        """Convert OpenSfM points to COLMAP points3D.txt format with track information"""
        points_file = self.sparse_dir / "points3D.txt"
        points_data = self.reconstruction.get('points', {})
        
        logger.info(f"🔄 Converting {len(points_data)} points to COLMAP format with tracks")
        
        with open(points_file, 'w') as f:
            f.write("# 3D point list with one line of data per point:\n")
            f.write("#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
            
            avg_track_length = sum(len(track) for track in self.point_tracks.values()) / len(self.point_tracks) if self.point_tracks else 0
            f.write("# Number of points: {}, mean track length: {:.1f}\n".format(len(points_data), avg_track_length))
            
            for opensfm_point_id, point_data in points_data.items():
                point3d_id = self.point_id_mapping.get(opensfm_point_id, 1)
                
                coordinates = point_data.get('coordinates', [0.0, 0.0, 0.0])
                x, y, z = coordinates
                
                color = point_data.get('color', [255, 255, 255])
                r, g, b = [int(c) for c in color]
                
                error = 0.5  # Default error estimate
                
                # Get track information
                track_data = self.point_tracks.get(point3d_id, [])
                track_str = ""
                for shot_name, feature_idx in track_data:
                    image_id = self.image_id_mapping.get(shot_name, 1)
                    track_str += f"{image_id} {feature_idx} "
                
                f.write(f"{point3d_id} {x:.6f} {y:.6f} {z:.6f} {r} {g} {b} {error:.6f} {track_str.strip()}\n")
        
        logger.info(f"✅ Generated points3D.txt with {len(points_data)} points and tracks")
    
    def convert_to_binary(self) -> None:
        """Convert COLMAP text files to binary format using COLMAP model_converter"""
        logger.info(f"🔄 Converting COLMAP text files to binary format")
        
        try:
            cmd = [
                "colmap", "model_converter",
                "--input_path", str(self.sparse_dir),
                "--output_path", str(self.sparse_dir),
                "--output_type", "BIN"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"✅ Successfully converted to binary COLMAP format")
                
                # Verify binary files exist
                binary_files = ["cameras.bin", "images.bin", "points3D.bin"]
                for filename in binary_files:
                    filepath = self.sparse_dir / filename
                    if filepath.exists():
                        logger.info(f"   📄 Generated: {filename} ({filepath.stat().st_size} bytes)")
                    else:
                        logger.warning(f"   ⚠️ Missing: {filename}")
            else:
                logger.error(f"❌ COLMAP model_converter failed:")
                logger.error(f"   stdout: {result.stdout}")
                logger.error(f"   stderr: {result.stderr}")
                raise RuntimeError(f"COLMAP conversion failed with exit code {result.returncode}")
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ COLMAP model_converter timed out after 300 seconds")
            raise
        except FileNotFoundError:
            logger.error(f"❌ COLMAP not found in PATH. Installing COLMAP...")
            self._install_colmap()
            # Retry conversion
            self.convert_to_binary()
    
    def _install_colmap(self) -> None:
        """Install COLMAP if not available"""
        logger.info(f"📦 Installing COLMAP...")
        try:
            # For Ubuntu/Debian systems
            subprocess.run(["apt-get", "update"], check=True)
            subprocess.run(["apt-get", "install", "-y", "colmap"], check=True)
            logger.info(f"✅ COLMAP installed successfully")
        except subprocess.CalledProcessError:
            logger.error(f"❌ Failed to install COLMAP via apt-get")
            raise RuntimeError("COLMAP installation failed")
    
    def copy_images(self) -> None:
        """Copy all images to the dataset images/ directory"""
        source_images_dir = self.opensfm_path / "images"
        
        if not source_images_dir.exists():
            logger.warning(f"⚠️ Source images directory not found: {source_images_dir}")
            return
        
        logger.info(f"📸 Copying images from {source_images_dir} to {self.images_dir}")
        
        # Create images directory
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all images
        image_files = list(source_images_dir.glob("*.jpg")) + list(source_images_dir.glob("*.JPG")) + \
                     list(source_images_dir.glob("*.png")) + list(source_images_dir.glob("*.PNG")) + \
                     list(source_images_dir.glob("*.jpeg")) + list(source_images_dir.glob("*.JPEG"))
        
        copied_count = 0
        for image_file in image_files:
            dst_path = self.images_dir / image_file.name
            try:
                shutil.copy2(image_file, dst_path)
                copied_count += 1
                if copied_count <= 3:
                    logger.info(f"   📄 Copied: {image_file.name}")
                elif copied_count == 4:
                    logger.info(f"   📄 ... and {len(image_files) - 3} more images")
            except Exception as e:
                logger.error(f"❌ Failed to copy {image_file.name}: {e}")
        
        logger.info(f"✅ Copied {copied_count}/{len(image_files)} images")
    
    def validate_dataset(self) -> Dict:
        """Validate the generated dataset structure"""
        validation = {
            'structure_valid': False,
            'images_dir_exists': False,
            'sparse_dir_exists': False,
            'binary_files_exist': False,
            'image_count': 0,
            'camera_count': 0,
            'point_count': 0,
            'avg_observations': 0,
            'avg_track_length': 0
        }
        
        try:
            # Check directory structure
            validation['images_dir_exists'] = self.images_dir.exists()
            validation['sparse_dir_exists'] = self.sparse_dir.exists()
            
            # Check binary files
            binary_files = ["cameras.bin", "images.bin", "points3D.bin"]
            validation['binary_files_exist'] = all((self.sparse_dir / f).exists() for f in binary_files)
            
            # Count images
            if self.images_dir.exists():
                image_files = list(self.images_dir.glob("*.jpg")) + list(self.images_dir.glob("*.JPG")) + \
                             list(self.images_dir.glob("*.png")) + list(self.images_dir.glob("*.PNG"))
                validation['image_count'] = len(image_files)
            
            # Get statistics from text files if available
            cameras_file = self.sparse_dir / "cameras.txt"
            if cameras_file.exists():
                with open(cameras_file, 'r') as f:
                    validation['camera_count'] = sum(1 for line in f if line.strip() and not line.startswith('#'))
            
            images_file = self.sparse_dir / "images.txt"
            if images_file.exists():
                with open(images_file, 'r') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    image_count = len(lines) // 2  # Each image has 2 lines
                    
                    # Calculate average observations
                    total_obs = 0
                    for i in range(1, len(lines), 2):  # Points2D lines
                        obs_line = lines[i]
                        if obs_line:
                            obs_count = len(obs_line.split()) // 3  # Each observation is x y point3d_id
                            total_obs += obs_count
                    
                    validation['avg_observations'] = total_obs / image_count if image_count > 0 else 0
            
            points_file = self.sparse_dir / "points3D.txt"
            if points_file.exists():
                with open(points_file, 'r') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    validation['point_count'] = len(lines)
                    
                    # Calculate average track length
                    total_track_length = 0
                    for line in lines:
                        parts = line.split()
                        if len(parts) > 8:  # Has track data
                            track_data = parts[8:]  # Everything after ERROR
                            track_length = len(track_data) // 2  # Each track entry is image_id point2d_idx
                            total_track_length += track_length
                    
                    validation['avg_track_length'] = total_track_length / len(lines) if lines else 0
            
            # Overall validation
            validation['structure_valid'] = (
                validation['images_dir_exists'] and
                validation['sparse_dir_exists'] and
                validation['binary_files_exist'] and
                validation['image_count'] > 0 and
                validation['camera_count'] > 0 and
                validation['point_count'] > 0 and
                validation['avg_observations'] > 0
            )
            
            logger.info(f"🔍 Dataset Validation Results:")
            logger.info(f"   Structure: {'✅ VALID' if validation['structure_valid'] else '❌ INVALID'}")
            logger.info(f"   Images: {validation['image_count']} files")
            logger.info(f"   Cameras: {validation['camera_count']}")
            logger.info(f"   Points: {validation['point_count']}")
            logger.info(f"   Avg observations per image: {validation['avg_observations']:.1f}")
            logger.info(f"   Avg track length: {validation['avg_track_length']:.1f}")
            logger.info(f"   Binary files: {'✅ EXISTS' if validation['binary_files_exist'] else '❌ MISSING'}")
            
        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
        
        return validation
    
    def convert_full_reconstruction(self) -> Dict:
        """Convert complete OpenSfM reconstruction to proper COLMAP dataset format"""
        logger.info(f"🚀 Starting full OpenSfM to COLMAP conversion")
        
        # Create output directories
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.sparse_dir.mkdir(parents=True, exist_ok=True)
        
        # Load reconstruction data
        self.load_opensfm_reconstruction()
        
        # Extract 2D-3D correspondences
        self.extract_tracks()
        
        # Convert to COLMAP format
        self.convert_cameras()
        self.convert_images()
        self.convert_points()
        
        # Convert to binary format
        self.convert_to_binary()
        
        # Copy images
        self.copy_images()
        
        # Validate result
        validation = self.validate_dataset()
        
        logger.info(f"✅ Full OpenSfM to COLMAP conversion completed")
        logger.info(f"📁 Dataset structure: {self.output_path}")
        logger.info(f"   📸 images/ - {validation['image_count']} image files")
        logger.info(f"   📊 sparse/0/ - COLMAP reconstruction with {validation['point_count']} points")
        
        return validation
    
    def convert(self) -> Dict:
        """Legacy wrapper for backward compatibility"""
        return self.convert_full_reconstruction()
    
    def _axis_angle_to_quaternion(self, axis_angle: List[float]) -> np.ndarray:
        """Convert axis-angle rotation to quaternion"""
        axis_angle = np.array(axis_angle)
        angle = np.linalg.norm(axis_angle)
        
        if angle < 1e-8:
            return np.array([1.0, 0.0, 0.0, 0.0])
        
        axis = axis_angle / angle
        half_angle = angle / 2.0
        
        w = np.cos(half_angle)
        xyz = np.sin(half_angle) * axis
        
        return np.array([w, xyz[0], xyz[1], xyz[2]])
    
    def _quaternion_to_rotation_matrix(self, quat: np.ndarray) -> np.ndarray:
        """Convert quaternion to rotation matrix"""
        qw, qx, qy, qz = quat
        
        norm = np.sqrt(qw*qw + qx*qx + qy*qy + qz*qz)
        qw, qx, qy, qz = qw/norm, qx/norm, qy/norm, qz/norm
        
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
            s = np.sqrt(trace + 1.0) * 2
            qw = 0.25 * s
            qx = (R[2, 1] - R[1, 2]) / s
            qy = (R[0, 2] - R[2, 0]) / s
            qz = (R[1, 0] - R[0, 1]) / s
        elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
            s = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
            qw = (R[2, 1] - R[1, 2]) / s
            qx = 0.25 * s
            qy = (R[0, 1] + R[1, 0]) / s
            qz = (R[0, 2] + R[2, 0]) / s
        elif R[1, 1] > R[2, 2]:
            s = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
            qw = (R[0, 2] - R[2, 0]) / s
            qx = (R[0, 1] + R[1, 0]) / s
            qy = 0.25 * s
            qz = (R[1, 2] + R[2, 1]) / s
        else:
            s = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
            qw = (R[1, 0] - R[0, 1]) / s
            qx = (R[0, 2] + R[2, 0]) / s
            qy = (R[1, 2] + R[2, 1]) / s
            qz = 0.25 * s
        
        return np.array([qw, qx, qy, qz])


def main():
    """Test converter functionality"""
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python colmap_converter.py <opensfm_dir> <output_dir>")
        sys.exit(1)
    
    opensfm_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
    converter = OpenSfMToCOLMAPConverter(opensfm_dir, output_dir)
    validation = converter.convert_full_reconstruction()
    
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main() 