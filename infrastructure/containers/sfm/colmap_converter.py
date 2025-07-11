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
        self.base_output_path = Path(output_path)
        
        # Create COLMAP sparse directory structure in temp location first
        # to avoid permission issues with SageMaker output mount
        import tempfile
        self.temp_dir = Path(tempfile.mkdtemp(prefix="colmap_"))
        self.output_path = self.temp_dir / "sparse" / "0"
        self.final_sparse_path = self.base_output_path / "sparse" / "0"
        self.reconstruction = None
        
        logger.info(f"🔄 Initializing OpenSfM to COLMAP converter")
        logger.info(f"   Input: {opensfm_path}")
        logger.info(f"   Output: {output_path}")
        logger.info(f"   Temp COLMAP dir: {self.output_path}")
        logger.info(f"   Final COLMAP dir: {self.final_sparse_path}")
    
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
            
            # CRITICAL FIX: Convert OpenSfM camera IDs to integers for COLMAP compatibility
            camera_id_mapping = {}
            numeric_camera_id = 1
            
            for camera_id, camera_data in cameras_data.items():
                # Map OpenSfM camera ID to numeric ID
                camera_id_mapping[camera_id] = numeric_camera_id
                
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
                f.write(f"{numeric_camera_id} {model} {width} {height} {params_str}\n")
                
                numeric_camera_id += 1
            
            # Store mapping for use in image conversion
            self.camera_id_mapping = camera_id_mapping
        
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
                opensfm_camera_id = shot_data.get('camera', list(self.reconstruction.get('cameras', {}).keys())[0])
                
                # CRITICAL FIX: Use numeric camera ID mapping
                numeric_camera_id = getattr(self, 'camera_id_mapping', {}).get(opensfm_camera_id, 1)
                
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
                       f"{tx:.6f} {ty:.6f} {tz:.6f} {numeric_camera_id} {shot_name}\n")
                
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
        
        # Create dense directory in temp location (avoiding permission issues)
        dense_dir = self.temp_dir / "dense"
        dense_dir.mkdir(parents=True, exist_ok=True)
        
        ply_file = dense_dir / "sparse_points.ply"
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
    
    def _copy_to_final_location(self) -> None:
        """Copy COLMAP files from temp directory to final output location"""
        import shutil
        import os
        
        try:
            # Create final sparse directory structure with proper permissions
            logger.info(f"📁 Creating final sparse directory: {self.final_sparse_path}")
            
            # Use os.makedirs with exist_ok to handle permission issues more gracefully
            os.makedirs(self.final_sparse_path, mode=0o755, exist_ok=True)
            
            # Verify directory was created and is writable
            if not os.path.exists(self.final_sparse_path):
                raise PermissionError(f"Failed to create directory: {self.final_sparse_path}")
            if not os.access(self.final_sparse_path, os.W_OK):
                raise PermissionError(f"Directory not writable: {self.final_sparse_path}")
            
            logger.info(f"✅ Final sparse directory created successfully: {self.final_sparse_path}")
            
            # Copy COLMAP files from main reconstruction (for backward compatibility)
            files_to_copy = ["cameras.txt", "images.txt", "points3D.txt"]
            for filename in files_to_copy:
                src = self.output_path / filename
                dst = self.final_sparse_path / filename
                if src.exists():
                    shutil.copy2(src, dst)
                    logger.info(f"📄 Copied {filename} to final location")
                else:
                    logger.warning(f"⚠️ Missing file: {filename}")
            
            # CRITICAL FIX: Copy train/ and test/ directories for 3DGS training
            train_src = self.temp_dir / "train"
            test_src = self.temp_dir / "test"
            train_dst = self.base_output_path / "train"
            test_dst = self.base_output_path / "test"
            
            if train_src.exists():
                if train_dst.exists():
                    shutil.rmtree(train_dst)
                shutil.copytree(train_src, train_dst)
                logger.info(f"📁 Copied train reconstruction to: {train_dst}")
            else:
                logger.warning(f"⚠️ Missing train directory: {train_src}")
            
            if test_src.exists():
                if test_dst.exists():
                    shutil.rmtree(test_dst)
                shutil.copytree(test_src, test_dst)
                logger.info(f"📁 Copied test reconstruction to: {test_dst}")
            else:
                logger.warning(f"⚠️ Missing test directory: {test_src}")
            
            # Copy dense directory (contains PLY file)
            temp_dense_dir = self.temp_dir / "dense"
            final_dense_dir = self.base_output_path / "dense"
            if temp_dense_dir.exists():
                if final_dense_dir.exists():
                    shutil.rmtree(final_dense_dir)
                shutil.copytree(temp_dense_dir, final_dense_dir)
                logger.info(f"📁 Copied dense directory to final location")
            else:
                logger.warning(f"⚠️ Missing dense directory: {temp_dense_dir}")
            
            # Clean up temp directory
            shutil.rmtree(self.temp_dir)
            logger.info(f"🧹 Cleaned up temp directory: {self.temp_dir}")
            
        except PermissionError as e:
            logger.error(f"❌ Permission denied while copying files: {e}")
            logger.error(f"🔍 Debug info:")
            logger.error(f"   Final sparse path: {self.final_sparse_path}")
            logger.error(f"   Base output path: {self.base_output_path}")
            logger.error(f"   Current user: {os.getuid() if hasattr(os, 'getuid') else 'Unknown'}")
            logger.error(f"   Output path exists: {os.path.exists(self.base_output_path)}")
            logger.error(f"   Output path writable: {os.access(self.base_output_path, os.W_OK)}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to copy files to final location: {e}")
            raise
    
    def validate_conversion(self) -> Dict:
        """Validate the COLMAP conversion"""
        validation_results = {
            'cameras_file_exists': False,
            'images_file_exists': False,
            'points_file_exists': False,
            'ply_file_exists': False,
            'train_dir_exists': False,
            'test_dir_exists': False,
            'camera_count': 0,
            'image_count': 0,
            'point_count': 0,
            'train_image_count': 0,
            'test_image_count': 0,
            'quality_check_passed': False
        }
        
        try:
            # Check file existence in final location
            cameras_file = self.final_sparse_path / "cameras.txt"
            images_file = self.final_sparse_path / "images.txt"
            points_file = self.final_sparse_path / "points3D.txt"
            ply_file = self.base_output_path / "dense" / "sparse_points.ply"
            train_dir = self.base_output_path / "train"
            test_dir = self.base_output_path / "test"
            
            validation_results['cameras_file_exists'] = cameras_file.exists()
            validation_results['images_file_exists'] = images_file.exists()
            validation_results['points_file_exists'] = points_file.exists()
            validation_results['ply_file_exists'] = ply_file.exists()
            validation_results['train_dir_exists'] = train_dir.exists()
            validation_results['test_dir_exists'] = test_dir.exists()
            
            # Count cameras
            if cameras_file.exists():
                with open(cameras_file, 'r') as f:
                    camera_count = sum(1 for line in f if line.strip() and not line.startswith('#'))
                validation_results['camera_count'] = camera_count
            
            # Count images (each image has 2 lines in COLMAP format)
            if images_file.exists():
                with open(images_file, 'r') as f:
                    image_lines = sum(1 for line in f if line.strip() and not line.startswith('#'))
                validation_results['image_count'] = image_lines // 2
            
            # Count points
            if points_file.exists():
                with open(points_file, 'r') as f:
                    point_count = sum(1 for line in f if line.strip() and not line.startswith('#'))
                validation_results['point_count'] = point_count
            
            # Count train/test images
            if train_dir.exists():
                train_images_file = train_dir / "images.txt"
                if train_images_file.exists():
                    with open(train_images_file, 'r') as f:
                        train_image_lines = sum(1 for line in f if line.strip() and not line.startswith('#'))
                    validation_results['train_image_count'] = train_image_lines // 2
            
            if test_dir.exists():
                test_images_file = test_dir / "images.txt"
                if test_images_file.exists():
                    with open(test_images_file, 'r') as f:
                        test_image_lines = sum(1 for line in f if line.strip() and not line.startswith('#'))
                    validation_results['test_image_count'] = test_image_lines // 2
            
            # Quality check (minimum requirements for 3DGS)
            min_points_required = 1000  # Same as current COLMAP pipeline
            validation_results['quality_check_passed'] = (
                validation_results['point_count'] >= min_points_required and
                validation_results['image_count'] > 0 and
                validation_results['camera_count'] > 0 and
                validation_results['train_dir_exists'] and
                validation_results['test_dir_exists'] and
                validation_results['train_image_count'] > 0 and
                validation_results['test_image_count'] > 0
            )
            
            logger.info(f"🔍 Validation Results:")
            logger.info(f"   Cameras: {validation_results['camera_count']}")
            logger.info(f"   Images: {validation_results['image_count']}")
            logger.info(f"   Points: {validation_results['point_count']}")
            logger.info(f"   Train Images: {validation_results['train_image_count']}")
            logger.info(f"   Test Images: {validation_results['test_image_count']}")
            logger.info(f"   Train/Test Split: {'✅ EXISTS' if validation_results['train_dir_exists'] and validation_results['test_dir_exists'] else '❌ MISSING'}")
            logger.info(f"   Quality Check: {'✅ PASSED' if validation_results['quality_check_passed'] else '❌ FAILED'}")
            
            if not validation_results['quality_check_passed']:
                logger.warning(f"⚠️ Quality check failed: Need at least {min_points_required} points and proper train/test split for 3DGS")
            
        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
        
        return validation_results
    
    def convert_full_reconstruction(self) -> Dict:
        """Convert complete OpenSfM reconstruction to COLMAP format with train/test split"""
        logger.info(f"🚀 Starting full OpenSfM to COLMAP conversion with train/test split")
        
        # Create temp directory structure (sparse/0 for COLMAP files)
        self.output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Created temp COLMAP sparse directory: {self.output_path}")
        
        # Load reconstruction
        self.load_opensfm_reconstruction()
        
        # CRITICAL FIX: Create train/test split for proper 3DGS training
        train_data, test_data = self.create_train_test_split()
        
        # Convert complete reconstruction (for backward compatibility)
        self.convert_cameras()
        self.convert_images()
        self.convert_points()
        
        # Create train/test split reconstructions
        self.create_split_reconstructions(train_data, test_data)
        
        self.create_reference_point_cloud()
        
        # Copy to final location
        self._copy_to_final_location()
        
        # Validate conversion
        validation_results = self.validate_conversion()
        
        logger.info(f"✅ Full OpenSfM to COLMAP conversion completed")
        return validation_results
    
    def create_train_test_split(self, train_ratio: float = 0.8) -> Tuple[Dict, Dict]:
        """Create train/test split of the reconstruction data"""
        if not self.reconstruction:
            raise ValueError("Reconstruction not loaded")
        
        shots_data = self.reconstruction.get('shots', {})
        shot_names = list(shots_data.keys())
        
        # Sort by name for consistent splitting
        shot_names.sort()
        
        # Calculate split index
        split_idx = int(len(shot_names) * train_ratio)
        
        train_shots = shot_names[:split_idx]
        test_shots = shot_names[split_idx:]
        
        logger.info(f"🔄 Creating train/test split:")
        logger.info(f"   Total images: {len(shot_names)}")
        logger.info(f"   Training images: {len(train_shots)} ({len(train_shots)/len(shot_names)*100:.1f}%)")
        logger.info(f"   Test images: {len(test_shots)} ({len(test_shots)/len(shot_names)*100:.1f}%)")
        
        # Create train data
        train_data = {
            'cameras': self.reconstruction.get('cameras', {}),
            'shots': {name: shots_data[name] for name in train_shots},
            'points': self.reconstruction.get('points', {})
        }
        
        # Create test data (shares cameras and points with training)
        test_data = {
            'cameras': self.reconstruction.get('cameras', {}),
            'shots': {name: shots_data[name] for name in test_shots},
            'points': self.reconstruction.get('points', {})
        }
        
        return train_data, test_data
    
    def create_split_reconstructions(self, train_data: Dict, test_data: Dict) -> None:
        """Create separate COLMAP reconstructions for train and test splits"""
        # Create train directory
        train_dir = self.temp_dir / "train"
        train_dir.mkdir(exist_ok=True)
        
        # Create test directory  
        test_dir = self.temp_dir / "test"
        test_dir.mkdir(exist_ok=True)
        
        logger.info(f"🔄 Creating train reconstruction in: {train_dir}")
        self._create_split_reconstruction(train_data, train_dir, "train")
        
        logger.info(f"🔄 Creating test reconstruction in: {test_dir}")
        self._create_split_reconstruction(test_data, test_dir, "test")
        
        logger.info(f"✅ Created train/test split reconstructions")
    
    def _create_split_reconstruction(self, data: Dict, output_dir: Path, split_name: str) -> None:
        """Create a COLMAP reconstruction for a specific split"""
        import shutil
        
        # Temporarily store original reconstruction
        original_reconstruction = self.reconstruction
        
        # Set reconstruction to split data
        self.reconstruction = data
        
        # Temporarily change output path
        original_output_path = self.output_path
        self.output_path = output_dir
        
        try:
            # Convert split data
            self.convert_cameras()
            self.convert_images()
            self.convert_points()
            
            # CRITICAL FIX: Copy actual image files for this split
            self._copy_images_for_split(data, output_dir, split_name)
            
            shots_count = len(data.get('shots', {}))
            points_count = len(data.get('points', {}))
            cameras_count = len(data.get('cameras', {}))
            
            logger.info(f"✅ {split_name} reconstruction: {cameras_count} cameras, {shots_count} images, {points_count} points")
            
        finally:
            # Restore original values
            self.reconstruction = original_reconstruction
            self.output_path = original_output_path

    def _copy_images_for_split(self, data: Dict, output_dir: Path, split_name: str) -> None:
        """Copy actual image files for a specific train/test split"""
        import shutil
        
        # Get the source images directory
        source_images_dir = self.base_output_path / "images"
        if not source_images_dir.exists():
            logger.warning(f"⚠️ Source images directory not found: {source_images_dir}")
            return
        
        # Get the shots (images) for this split
        shots_data = data.get('shots', {})
        if not shots_data:
            logger.warning(f"⚠️ No shots found for {split_name} split")
            return
        
        # Extract image filenames from shots
        image_filenames = []
        for shot_name, shot_data in shots_data.items():
            # The shot_name is typically the filename without extension
            # But we need to check the actual files in the images directory
            for ext in ['.JPG', '.jpg', '.PNG', '.png', '.JPEG', '.jpeg']:
                image_file = source_images_dir / f"{shot_name}{ext}"
                if image_file.exists():
                    image_filenames.append(f"{shot_name}{ext}")
                    break
        
        if not image_filenames:
            logger.warning(f"⚠️ No image files found for {split_name} split")
            return
        
        logger.info(f"📸 Copying {len(image_filenames)} images for {split_name} split:")
        
        # Copy each image file to the split directory
        copied_count = 0
        for image_filename in image_filenames:
            src_path = source_images_dir / image_filename
            dst_path = output_dir / image_filename
            
            if src_path.exists():
                try:
                    shutil.copy2(src_path, dst_path)
                    copied_count += 1
                    if copied_count <= 3:  # Log first few files
                        logger.info(f"   📄 Copied: {image_filename}")
                    elif copied_count == 4:
                        logger.info(f"   📄 ... and {len(image_filenames) - 3} more images")
                except Exception as e:
                    logger.error(f"❌ Failed to copy {image_filename}: {e}")
            else:
                logger.warning(f"⚠️ Source image not found: {src_path}")
        
        logger.info(f"✅ Copied {copied_count}/{len(image_filenames)} images for {split_name} split")

    def convert(self) -> Dict:
        """Public wrapper to preserve legacy call sites.

        Older pipeline code expects a `convert()` method on the converter.  The
        implementation was renamed to `convert_full_reconstruction()` during a
        refactor, which broke the runtime (AttributeError).  This thin wrapper
        simply forwards to the new implementation while returning its result.
        """
        return self.convert_full_reconstruction()


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