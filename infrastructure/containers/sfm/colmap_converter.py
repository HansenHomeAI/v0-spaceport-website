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
import shutil
from collections import defaultdict

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
            output_path: Path to output dataset directory
        """
        self.opensfm_path = Path(opensfm_path)
        self.output_path = Path(output_path)
        
        # Create proper dataset structure
        self.images_dir = self.output_path / "images"
        self.sparse_dir = self.output_path / "sparse" / "0"
        
        self.reconstruction = None
        self.tracks = None
        self.camera_id_mapping = {}
        self.image_id_mapping = {}
        self.point_id_mapping = {}
        
        logger.info(f"🔄 Initializing OpenSfM to COLMAP converter")
        logger.info(f"   Input: {opensfm_path}")
        logger.info(f"   Output: {output_path}")
        logger.info(f"   Images: {self.images_dir}")
        logger.info(f"   Sparse: {self.sparse_dir}")
    
    def load_opensfm_data(self) -> bool:
        """Load OpenSfM reconstruction and track data"""
        reconstruction_file = self.opensfm_path / "reconstruction.json"
        
        if not reconstruction_file.exists():
            logger.error(f"❌ OpenSfM reconstruction not found: {reconstruction_file}")
            return False
        
        try:
            # Load reconstruction
            with open(reconstruction_file, 'r') as f:
                reconstructions = json.load(f)
            
            if not reconstructions:
                logger.error("❌ No reconstructions found in OpenSfM output")
                return False
            
            # Use the first (largest) reconstruction
            self.reconstruction = reconstructions[0]
            
            logger.info(f"✅ Loaded OpenSfM reconstruction:")
            logger.info(f"   Cameras: {len(self.reconstruction.get('cameras', {}))}")
            logger.info(f"   Shots: {len(self.reconstruction.get('shots', {}))}")
            logger.info(f"   Points: {len(self.reconstruction.get('points', {}))}")
            
            # Load tracks for 2D-3D correspondence
            self._load_tracks()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load OpenSfM data: {e}")
            return False
    
    def _load_tracks(self) -> None:
        """Load OpenSfM tracks for 2D-3D correspondence"""
        # Try multiple track file locations
        track_files = [
            self.opensfm_path / "tracks.json",
            self.opensfm_path / "features.json"
        ]
        
        tracks_loaded = False
        
        for track_file in track_files:
            if track_file.exists():
                try:
                    with open(track_file, 'r') as f:
                        self.tracks = json.load(f)
                    logger.info(f"✅ Loaded tracks from: {track_file}")
                    tracks_loaded = True
                    break
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load tracks from {track_file}: {e}")
        
        # If no tracks file, extract from reconstruction points
        if not tracks_loaded:
            logger.info("🔄 Extracting tracks from reconstruction points...")
            self._extract_tracks_from_points()
    
    def _extract_tracks_from_points(self) -> None:
        """Extract tracks from OpenSfM point observations"""
        self.tracks = {}
        points_data = self.reconstruction.get('points', {})
        
        for point_id, point_data in points_data.items():
            observations = point_data.get('observations', {})
            if observations:
                track = []
                for shot_id, obs_data in observations.items():
                    # obs_data typically contains [x, y] coordinates
                    if isinstance(obs_data, list) and len(obs_data) >= 2:
                        x, y = obs_data[0], obs_data[1]
                        track.append({
                            'shot_id': shot_id,
                            'feature': [x, y]
                        })
                
                if track:
                    self.tracks[point_id] = track
        
        logger.info(f"✅ Extracted {len(self.tracks)} tracks from point observations")
    
    def create_dataset_structure(self) -> None:
        """Create the proper dataset directory structure"""
        # Create directories
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.sparse_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 Created dataset structure:")
        logger.info(f"   Images: {self.images_dir}")
        logger.info(f"   Sparse: {self.sparse_dir}")
    
    def copy_images(self) -> None:
        """Copy all images to the images/ directory"""
        source_images_dir = self.opensfm_path / "images"
        
        if not source_images_dir.exists():
            logger.warning(f"⚠️ Source images directory not found: {source_images_dir}")
            return
        
        shots_data = self.reconstruction.get('shots', {})
        copied_count = 0
        
        logger.info(f"📸 Copying {len(shots_data)} images...")
        
        for shot_name in shots_data.keys():
            # Try different extensions
            source_file = None
            for ext in ['.JPG', '.jpg', '.PNG', '.png', '.JPEG', '.jpeg']:
                candidate = source_images_dir / f"{shot_name}{ext}"
                if candidate.exists():
                    source_file = candidate
                    break
                # Also try if shot_name already has extension
                candidate = source_images_dir / shot_name
                if candidate.exists():
                    source_file = candidate
                    break
            
            if source_file:
                dest_file = self.images_dir / source_file.name
                try:
                    shutil.copy2(source_file, dest_file)
                    copied_count += 1
                    if copied_count <= 3:
                        logger.info(f"   📄 Copied: {source_file.name}")
                    elif copied_count == 4:
                        logger.info(f"   📄 ... and {len(shots_data) - 3} more images")
                except Exception as e:
                    logger.error(f"❌ Failed to copy {source_file.name}: {e}")
            else:
                logger.warning(f"⚠️ Image not found: {shot_name}")
        
        logger.info(f"✅ Copied {copied_count}/{len(shots_data)} images")
    
    def convert_cameras(self) -> None:
        """Convert OpenSfM cameras to COLMAP cameras.txt"""
        cameras_file = self.sparse_dir / "cameras.txt"
        cameras_data = self.reconstruction.get('cameras', {})
        
        logger.info(f"🔄 Converting {len(cameras_data)} cameras to COLMAP format")
        
        with open(cameras_file, 'w') as f:
            f.write("# Camera list with one line of data per camera:\n")
            f.write("#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
            f.write(f"# Number of cameras: {len(cameras_data)}\n")
            
            camera_id = 1
            for camera_key, camera_data in cameras_data.items():
                # Store mapping for later use
                self.camera_id_mapping[camera_key] = camera_id
                
                # Extract camera parameters
                width = int(camera_data.get('width', 1920))
                height = int(camera_data.get('height', 1080))
                
                # Convert OpenSfM camera model to COLMAP
                projection_type = camera_data.get('projection_type', 'perspective')
                
                if projection_type == 'perspective':
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
                    focal = camera_data.get('focal', 1.0)
                    k1 = camera_data.get('k1', 0.0)
                    k2 = camera_data.get('k2', 0.0)
                    
                    focal_pixels = focal * max(width, height)
                    
                    model = "OPENCV_FISHEYE"
                    cx = width / 2.0
                    cy = height / 2.0
                    params = [focal_pixels, focal_pixels, cx, cy, k1, k2, 0.0, 0.0]
                    
                else:
                    # Default to simple pinhole
                    model = "SIMPLE_PINHOLE"
                    focal_pixels = max(width, height) * 1.2
                    cx = width / 2.0
                    cy = height / 2.0
                    params = [focal_pixels, cx, cy]
                
                # Write camera line
                params_str = " ".join([f"{p:.6f}" for p in params])
                f.write(f"{camera_id} {model} {width} {height} {params_str}\n")
                
                camera_id += 1
        
        logger.info(f"✅ Generated cameras.txt with {len(cameras_data)} cameras")
    
    def convert_images(self) -> None:
        """Convert OpenSfM shots to COLMAP images.txt with 2D-3D correspondences"""
        images_file = self.sparse_dir / "images.txt"
        shots_data = self.reconstruction.get('shots', {})
        
        logger.info(f"🔄 Converting {len(shots_data)} images with 2D-3D correspondences")
        
        # Build correspondence data
        image_correspondences = self._build_image_correspondences()
        
        with open(images_file, 'w') as f:
            f.write("# Image list with two lines of data per image:\n")
            f.write("#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
            f.write("#   POINTS2D[] as (X, Y, POINT3D_ID)\n")
            
            # Calculate mean observations
            total_observations = sum(len(obs) for obs in image_correspondences.values())
            mean_obs = total_observations / len(shots_data) if shots_data else 0
            f.write(f"# Number of images: {len(shots_data)}, mean observations per image: {mean_obs:.1f}\n")
            
            image_id = 1
            for shot_name, shot_data in shots_data.items():
                # Store mapping
                self.image_id_mapping[shot_name] = image_id
                
                # Extract camera pose
                rotation = shot_data.get('rotation', [0.0, 0.0, 0.0])
                translation = shot_data.get('translation', [0.0, 0.0, 0.0])
                camera_key = shot_data.get('camera', list(self.reconstruction.get('cameras', {}).keys())[0])
                camera_id = self.camera_id_mapping.get(camera_key, 1)
                
                # Convert OpenSfM rotation (axis-angle) to quaternion
                quat = self._axis_angle_to_quaternion(rotation)
                qw, qx, qy, qz = quat
                
                # OpenSfM uses camera-to-world, COLMAP uses world-to-camera
                R = self._quaternion_to_rotation_matrix(quat)
                t = np.array(translation)
                
                # Invert transformation
                R_inv = R.T
                t_inv = -R_inv @ t
                
                # Convert back to quaternion
                quat_inv = self._rotation_matrix_to_quaternion(R_inv)
                qw, qx, qy, qz = quat_inv
                tx, ty, tz = t_inv
                
                # Write image line
                f.write(f"{image_id} {qw:.9f} {qx:.9f} {qy:.9f} {qz:.9f} "
                       f"{tx:.6f} {ty:.6f} {tz:.6f} {camera_id} {shot_name}\n")
                
                # Write 2D-3D correspondences
                correspondences = image_correspondences.get(shot_name, [])
                if correspondences:
                    points_str = " ".join([f"{x:.6f} {y:.6f} {point_id}" 
                                         for x, y, point_id in correspondences])
                    f.write(f"{points_str}\n")
                else:
                    f.write("\n")
                
                image_id += 1
        
        logger.info(f"✅ Generated images.txt with {len(shots_data)} images and {total_observations} total correspondences")
    
    def _build_image_correspondences(self) -> Dict[str, List[Tuple[float, float, int]]]:
        """Build 2D-3D correspondence data for each image"""
        correspondences = defaultdict(list)
        
        if not self.tracks:
            logger.warning("⚠️ No tracks available for correspondence generation")
            return correspondences
        
        point_id = 1
        for track_key, track_data in self.tracks.items():
            # Store point ID mapping
            self.point_id_mapping[track_key] = point_id
            
            if isinstance(track_data, list):
                # Track data is a list of observations
                for obs in track_data:
                    if isinstance(obs, dict):
                        shot_id = obs.get('shot_id')
                        feature = obs.get('feature', [])
                        if shot_id and len(feature) >= 2:
                            x, y = feature[0], feature[1]
                            correspondences[shot_id].append((x, y, point_id))
            
            point_id += 1
        
        total_correspondences = sum(len(obs) for obs in correspondences.values())
        logger.info(f"📍 Built correspondences for {len(correspondences)} images, {total_correspondences} total points")
        
        return correspondences
    
    def convert_points(self) -> None:
        """Convert OpenSfM points to COLMAP points3D.txt with track information"""
        points_file = self.sparse_dir / "points3D.txt"
        points_data = self.reconstruction.get('points', {})
        
        logger.info(f"🔄 Converting {len(points_data)} points with track information")
        
        with open(points_file, 'w') as f:
            f.write("# 3D point list with one line of data per point:\n")
            f.write("#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
            
            # Calculate mean track length
            total_track_length = 0
            valid_points = 0
            
            for point_key in points_data.keys():
                if point_key in self.tracks:
                    total_track_length += len(self.tracks[point_key])
                    valid_points += 1
            
            mean_track_length = total_track_length / valid_points if valid_points > 0 else 0
            f.write(f"# Number of points: {len(points_data)}, mean track length: {mean_track_length:.1f}\n")
            
            for point_key, point_data in points_data.items():
                point_id = self.point_id_mapping.get(point_key, 1)
                
                # Extract 3D coordinates
                coordinates = point_data.get('coordinates', [0.0, 0.0, 0.0])
                x, y, z = coordinates
                
                # Extract color
                color = point_data.get('color', [255, 255, 255])
                r, g, b = [int(c) for c in color]
                
                # Error estimate
                error = 0.5
                
                # Build track information
                track_str = ""
                if point_key in self.tracks:
                    track_entries = []
                    point2d_idx = 0  # Simple indexing for 2D points
                    
                    for obs in self.tracks[point_key]:
                        if isinstance(obs, dict):
                            shot_id = obs.get('shot_id')
                            if shot_id and shot_id in self.image_id_mapping:
                                image_id = self.image_id_mapping[shot_id]
                                track_entries.append(f"{image_id} {point2d_idx}")
                                point2d_idx += 1
                    
                    track_str = " ".join(track_entries)
                
                # Write point line
                f.write(f"{point_id} {x:.6f} {y:.6f} {z:.6f} {r} {g} {b} {error:.6f} {track_str}\n")
        
        logger.info(f"✅ Generated points3D.txt with {len(points_data)} points")
    
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
    
    def validate_conversion(self) -> Dict:
        """Validate the COLMAP conversion"""
        validation_results = {
            'images_dir_exists': False,
            'sparse_dir_exists': False,
            'cameras_file_exists': False,
            'images_file_exists': False,
            'points_file_exists': False,
            'camera_count': 0,
            'image_count': 0,
            'point_count': 0,
            'total_correspondences': 0,
            'mean_correspondences_per_image': 0.0,
            'quality_check_passed': False
        }
        
        try:
            # Check directory structure
            validation_results['images_dir_exists'] = self.images_dir.exists()
            validation_results['sparse_dir_exists'] = self.sparse_dir.exists()
            
            # Check COLMAP files
            cameras_file = self.sparse_dir / "cameras.txt"
            images_file = self.sparse_dir / "images.txt"
            points_file = self.sparse_dir / "points3D.txt"
            
            validation_results['cameras_file_exists'] = cameras_file.exists()
            validation_results['images_file_exists'] = images_file.exists()
            validation_results['points_file_exists'] = points_file.exists()
            
            # Count cameras
            if cameras_file.exists():
                with open(cameras_file, 'r') as f:
                    validation_results['camera_count'] = sum(1 for line in f if line.strip() and not line.startswith('#'))
            
            # Count images and correspondences
            if images_file.exists():
                with open(images_file, 'r') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    validation_results['image_count'] = len(lines) // 2
                    
                    # Count correspondences (every other line starting from line 1)
                    total_correspondences = 0
                    for i in range(1, len(lines), 2):
                        if lines[i]:  # Non-empty correspondence line
                            # Count triplets (x, y, point_id)
                            parts = lines[i].split()
                            total_correspondences += len(parts) // 3
                    
                    validation_results['total_correspondences'] = total_correspondences
                    if validation_results['image_count'] > 0:
                        validation_results['mean_correspondences_per_image'] = total_correspondences / validation_results['image_count']
            
            # Count points
            if points_file.exists():
                with open(points_file, 'r') as f:
                    validation_results['point_count'] = sum(1 for line in f if line.strip() and not line.startswith('#'))
            
            # Count copied images
            if self.images_dir.exists():
                image_files = list(self.images_dir.glob('*'))
                validation_results['copied_image_count'] = len([f for f in image_files if f.is_file()])
            
            # Quality check
            validation_results['quality_check_passed'] = (
                validation_results['images_dir_exists'] and
                validation_results['sparse_dir_exists'] and
                validation_results['cameras_file_exists'] and
                validation_results['images_file_exists'] and
                validation_results['points_file_exists'] and
                validation_results['camera_count'] > 0 and
                validation_results['image_count'] > 0 and
                validation_results['point_count'] > 0 and
                validation_results['total_correspondences'] > 0
            )
            
            logger.info(f"🔍 Validation Results:")
            logger.info(f"   Dataset Structure: {'✅ CORRECT' if validation_results['images_dir_exists'] and validation_results['sparse_dir_exists'] else '❌ WRONG'}")
            logger.info(f"   Cameras: {validation_results['camera_count']}")
            logger.info(f"   Images: {validation_results['image_count']}")
            logger.info(f"   Points: {validation_results['point_count']}")
            logger.info(f"   Total 2D-3D Correspondences: {validation_results['total_correspondences']}")
            logger.info(f"   Mean Correspondences/Image: {validation_results['mean_correspondences_per_image']:.1f}")
            logger.info(f"   Quality Check: {'✅ PASSED' if validation_results['quality_check_passed'] else '❌ FAILED'}")
            
        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
        
        return validation_results
    
    def convert(self) -> Dict:
        """Main conversion method - creates proper dataset structure for 3DGS"""
        logger.info(f"🚀 Starting OpenSfM to COLMAP conversion (3DGS dataset format)")
        
        # Load OpenSfM data
        if not self.load_opensfm_data():
            return {'quality_check_passed': False, 'error': 'Failed to load OpenSfM data'}
        
        # Create proper dataset structure
        self.create_dataset_structure()
        
        # Copy all images to images/ directory
        self.copy_images()
        
        # Convert to COLMAP format with proper correspondences
        self.convert_cameras()
        self.convert_images()
        self.convert_points()
        
        # Validate the conversion
        validation_results = self.validate_conversion()
        
        if validation_results['quality_check_passed']:
            logger.info(f"✅ OpenSfM to COLMAP conversion completed successfully")
            logger.info(f"📁 Dataset ready for 3DGS training at: {self.output_path}")
        else:
            logger.error(f"❌ Conversion failed quality check")
        
        return validation_results


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
    validation = converter.convert()
    
    # Print results
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main() 