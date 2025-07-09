#!/usr/bin/env python3
"""
OpenSfM GPS-Enhanced SfM Processing Pipeline
Runs Structure-from-Motion with GPS priors from drone flight path data
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple
import logging
import zipfile
import yaml
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our GPS processors
from gps_processor import DroneFlightPathProcessor
from gps_processor_3d import Advanced3DPathProcessor
from colmap_converter import OpenSfMToCOLMAPConverter


class OpenSfMGPSPipeline:
    """Main pipeline for GPS-enhanced OpenSfM processing"""
    
    def __init__(self, input_dir: Path, output_dir: Path, gps_csv_path: Path = None):
        """
        Initialize OpenSfM GPS pipeline
        
        Args:
            input_dir: Directory containing input ZIP or images
            output_dir: Directory for output files
            gps_csv_path: Optional path to GPS CSV file
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.gps_csv_path = Path(gps_csv_path) if gps_csv_path else None
        self.work_dir = None
        self.images_dir = None
        self.opensfm_dir = None
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def setup_workspace(self) -> Path:
        """Set up temporary workspace for processing"""
        self.work_dir = Path(tempfile.mkdtemp(prefix="opensfm_"))
        self.images_dir = self.work_dir / "images"
        self.opensfm_dir = self.work_dir / "opensfm"
        
        # Create directories
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.opensfm_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🏗️ Created workspace: {self.work_dir}")
        return self.work_dir
    
    def extract_images(self) -> int:
        """Extract images from input directory or ZIP file"""
        image_count = 0
        
        # Check if input is a ZIP file
        zip_files = list(self.input_dir.glob("*.zip"))
        if zip_files:
            # Extract first ZIP file found
            zip_path = zip_files[0]
            logger.info(f"📦 Extracting ZIP: {zip_path}")
            
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for member in zf.namelist():
                    if member.lower().endswith(('.jpg', '.jpeg', '.png')):
                        # Extract to images directory
                        target_path = self.images_dir / Path(member).name
                        with zf.open(member) as source, open(target_path, 'wb') as target:
                            target.write(source.read())
                        image_count += 1
        else:
            # Copy images from input directory
            for img_path in self.input_dir.rglob('*'):
                if img_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                    shutil.copy2(img_path, self.images_dir / img_path.name)
                    image_count += 1
        
        logger.info(f"📷 Extracted {image_count} images")
        return image_count
    
    def process_gps_data(self) -> bool:
        """Process GPS data if available"""
        if not self.gps_csv_path or not self.gps_csv_path.exists():
            # Check for GPS CSV in input directory
            csv_files = list(self.input_dir.glob("gps/*.csv"))
            if not csv_files:
                logger.warning("⚠️ No GPS CSV file found, proceeding without GPS priors")
                return False
            self.gps_csv_path = csv_files[0]
        
        logger.info(f"🛰️ Processing GPS data from: {self.gps_csv_path}")
        
        try:
            # Use the new Advanced 3D Path Processor
            processor = Advanced3DPathProcessor(self.gps_csv_path, self.images_dir)
            
            # Process flight data
            processor.parse_flight_csv()
            processor.setup_local_coordinate_system()
            processor.build_3d_flight_path()
            
            # Process photos with intelligent ordering
            photos = processor.get_photo_list_with_validation()
            if not photos:
                logger.error("❌ No photos found to process")
                return False
            
            # Map photos to 3D positions
            processor.map_photos_to_3d_positions(photos)
            
            # Generate OpenSfM files
            processor.generate_opensfm_files(self.opensfm_dir)
            
            # Get processing summary
            summary = processor.get_processing_summary()
            logger.info(f"📊 GPS Processing Summary:")
            logger.info(f"   Photos: {summary['photos_processed']}")
            logger.info(f"   Path length: {summary['path_length_m']}m")
            logger.info(f"   Photo spacing: {summary['photo_spacing_m']}m")
            logger.info(f"   Confidence: {summary['confidence_stats']['mean']:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ GPS processing failed: {e}")
            logger.warning("⚠️ Continuing without GPS priors")
            return False
    
    def create_opensfm_config(self) -> None:
        """Create OpenSfM configuration file"""
        config = {
            # Feature extraction
            'feature_type': 'SIFT',
            'feature_process_size': 2048,          # High-res processing for drone images
            'feature_max_num_features': 20000,     # Allow dense feature extraction
            'feature_min_frames': 4000,            # Lower floor so images with fewer features are still accepted
            'sift_peak_threshold': 0.006,          # Lower threshold → more features in low-texture areas
            
            # Matching
            'matching_gps_neighbors': 30,          # More temporal neighbors
            'matching_gps_distance': 300,          # Allow matches up to 300 m apart
            'matching_graph_rounds': 80,           # More graph refinement rounds
            'robust_matching_min_match': 8,        # Relax minimum matches to keep difficult pairs
            
            # Reconstruction
            'min_ray_angle_degrees': 1.0,          # Allow shallower angles → more points
            'reconstruction_min_ratio': 0.6,       # Allow more images even with fewer inliers
            'triangulation_min_ray_angle_degrees': 1.0,
            
            # GPS integration
            'use_altitude_tag': True,
            'gps_accuracy': 5.0,
            
            # Bundle adjustment
            'bundle_use_gps': True,
            'bundle_use_gcp': False,
            
            # Optimization
            'optimize_camera_parameters': True,
            'bundle_max_iterations': 100,
            
            # Output
            'processes': 4,  # Parallelise where possible
            
            # CRITICAL FIX: Enable train/test split for proper 3DGS training
            'reconstruction_split_ratio': 0.8,     # 80% training, 20% validation
            'reconstruction_split_method': 'sequential',  # Sequential split for temporal consistency
            'save_partial_reconstructions': True,   # Save both train and test sets
        }
        
        config_path = self.opensfm_dir / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        logger.info(f"✅ Created OpenSfM config: {config_path}")
    
    def copy_images_to_opensfm(self) -> None:
        """Copy images to OpenSfM directory structure"""
        opensfm_images = self.opensfm_dir / "images"
        if opensfm_images.exists():
            shutil.rmtree(opensfm_images)
        shutil.copytree(self.images_dir, opensfm_images)
        logger.info(f"✅ Copied {len(list(opensfm_images.iterdir()))} images to OpenSfM")
    
    def run_opensfm_commands(self) -> bool:
        """Run OpenSfM reconstruction pipeline"""
        commands = [
            ("extract_metadata", "Extract image metadata"),
            ("detect_features", "Detect features"),
            ("match_features", "Match features"),
            ("create_tracks", "Create tracks"),
            ("reconstruct", "Reconstruct 3D structure"),
        ]
        
        for cmd, description in commands:
            logger.info(f"🔧 {description}...")
            
            try:
                result = subprocess.run(
                    ["opensfm", cmd, str(self.opensfm_dir)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.info(f"✅ {description} completed")
                
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ OpenSfM {cmd} failed:")
                logger.error(f"   stdout: {e.stdout}")
                logger.error(f"   stderr: {e.stderr}")
                return False
        
        return True
    
    def validate_reconstruction(self) -> bool:
        """Validate OpenSfM reconstruction quality"""
        reconstruction_file = self.opensfm_dir / "reconstruction.json"
        
        if not reconstruction_file.exists():
            logger.error("❌ No reconstruction file found")
            return False
        
        with open(reconstruction_file, 'r') as f:
            reconstructions = json.load(f)
        
        if not reconstructions:
            logger.error("❌ Empty reconstruction")
            return False
        
        # Get the largest reconstruction
        recon = max(reconstructions, key=lambda r: len(r.get('points', {})))
        
        shots_dict = recon.get('shots', {})
        num_cameras = len(shots_dict)
        num_points = len(recon.get('points', {}))
        
        logger.info(f"📊 Reconstruction statistics:")
        logger.info(f"   Cameras: {num_cameras}")
        logger.info(f"   3D points: {num_points}")
        
        # Log which images were registered (first 20 for brevity)
        registered_images = list(shots_dict.keys())
        logger.info(f"   Registered images (showing up to 20): {registered_images[:20]}")
        
        # Determine unregistered images for debugging
        all_images = [p.name for p in (self.images_dir).iterdir() if p.suffix.lower() in {'.jpg', '.jpeg', '.png'}]
        unregistered = sorted(set(all_images) - set(registered_images))
        if unregistered:
            logger.warning(f"⚠️ Unregistered images (showing up to 20): {unregistered[:20]}")
        
        # Validate minimum quality
        if num_cameras < 5:
            logger.error("❌ Too few cameras reconstructed")
            return False
        
        if num_points < 1000:
            logger.error("❌ Too few 3D points reconstructed")
            return False
        
        logger.info("✅ Reconstruction validated")
        return True
    
    def convert_to_colmap(self) -> bool:
        """Convert OpenSfM output to COLMAP format"""
        try:
            converter = OpenSfMToCOLMAPConverter(self.opensfm_dir, self.output_dir)
            validation_results = converter.convert_full_reconstruction()
            
            # Log conversion results
            logger.info(f"📊 COLMAP Conversion Results:")
            logger.info(f"   Cameras: {validation_results.get('camera_count', 0)}")
            logger.info(f"   Images: {validation_results.get('image_count', 0)}")
            logger.info(f"   Points: {validation_results.get('point_count', 0)}")
            logger.info(f"   Quality Check: {'✅ PASSED' if validation_results.get('quality_check_passed', False) else '❌ FAILED'}")
            
            return validation_results.get('quality_check_passed', False)
        except Exception as e:
            logger.error(f"❌ COLMAP conversion failed: {e}")
            return False
    
    def copy_images_for_3dgs(self) -> None:
        """Copy images to output directory for 3DGS training"""
        output_images_dir = self.output_dir / "images"
        
        if output_images_dir.exists():
            shutil.rmtree(output_images_dir)
        
        # Copy images from extracted directory
        shutil.copytree(self.images_dir, output_images_dir)
        
        image_count = len(list(output_images_dir.iterdir()))
        logger.info(f"✅ Copied {image_count} images to output directory for 3DGS training")
    
    def generate_metadata_json(self) -> None:
        """Generate metadata JSON file with processing statistics"""
        # Get reconstruction statistics
        reconstruction_file = self.opensfm_dir / "reconstruction.json"
        
        if not reconstruction_file.exists():
            logger.warning("⚠️ No reconstruction file found for metadata generation")
            return
        
        with open(reconstruction_file, 'r') as f:
            reconstructions = json.load(f)
        
        if not reconstructions:
            logger.warning("⚠️ Empty reconstruction for metadata generation")
            return
        
        # Get the largest reconstruction
        recon = max(reconstructions, key=lambda r: len(r.get('points', {})))
        
        shots_dict = recon.get('shots', {})
        num_cameras = len(shots_dict)
        num_points = len(recon.get('points', {}))
        
        # Calculate processing time (approximate)
        processing_time = time.time() - getattr(self, '_start_time', time.time())
        
        # Generate metadata
        metadata = {
            'pipeline': 'OpenSfM GPS-Enhanced Structure-from-Motion',
            'processing_time_seconds': round(processing_time, 2),
            'cameras_registered': num_cameras,
            'images_registered': num_cameras,  # Assuming 1:1 mapping
            'points_3d': num_points,
            'gps_enhanced': hasattr(self, 'gps_csv_path') and self.gps_csv_path is not None,
            'quality_check_passed': num_points >= 1000,
            'colmap_format': True,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
        }
        
        metadata_file = self.output_dir / "sfm_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Generated metadata JSON: {metadata_file}")
    
    def create_stub_database(self) -> None:
        """Create a stub COLMAP database.db file for compatibility"""
        import sqlite3
        
        database_file = self.output_dir / "database.db"
        
        # Create minimal COLMAP database schema
        conn = sqlite3.connect(str(database_file))
        cursor = conn.cursor()
        
        # Create basic COLMAP database tables (minimal schema)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cameras (
                camera_id INTEGER PRIMARY KEY,
                model INTEGER NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                params BLOB,
                prior_focal_length INTEGER NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                image_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                camera_id INTEGER NOT NULL,
                prior_qw REAL,
                prior_qx REAL,
                prior_qy REAL,
                prior_qz REAL,
                prior_tx REAL,
                prior_ty REAL,
                prior_tz REAL,
                CONSTRAINT fk_images_camera_id FOREIGN KEY(camera_id) REFERENCES cameras(camera_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS keypoints (
                image_id INTEGER NOT NULL,
                rows INTEGER NOT NULL,
                cols INTEGER NOT NULL,
                data BLOB,
                CONSTRAINT fk_keypoints_image_id FOREIGN KEY(image_id) REFERENCES images(image_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                pair_id INTEGER PRIMARY KEY,
                rows INTEGER NOT NULL,
                cols INTEGER NOT NULL,
                data BLOB
            )
        ''')
        
        # Insert minimal data based on COLMAP conversion
        sparse_dir = self.output_dir / "sparse" / "0"
        cameras_file = sparse_dir / "cameras.txt"
        images_file = sparse_dir / "images.txt"
        
        if cameras_file.exists():
            with open(cameras_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split()
                    if len(parts) >= 5:
                        try:
                            camera_id = int(parts[0])
                            model = 1  # PINHOLE model
                            width = int(parts[2])
                            height = int(parts[3])
                            cursor.execute(
                                'INSERT OR REPLACE INTO cameras (camera_id, model, width, height, params, prior_focal_length) VALUES (?, ?, ?, ?, ?, ?)',
                                (camera_id, model, width, height, b'', 0)
                            )
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Skipping malformed camera line: {line} - {e}")
                            continue
        
        if images_file.exists():
            with open(images_file, 'r') as f:
                lines = f.readlines()
                i = 0
                image_id = 1
                while i < len(lines):
                    line = lines[i].strip()
                    if not line or line.startswith('#'):
                        i += 1
                        continue
                    parts = line.split()
                    if len(parts) >= 10:
                        try:
                            camera_id = int(parts[8])
                            name = parts[9]
                            cursor.execute(
                                'INSERT OR REPLACE INTO images (image_id, name, camera_id) VALUES (?, ?, ?)',
                                (image_id, name, camera_id)
                            )
                            image_id += 1
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Skipping malformed image line: {line} - {e}")
                    i += 2  # Skip points2D line
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Created stub COLMAP database: {database_file}")
    
    def cleanup(self) -> None:
        """Clean up temporary files"""
        if self.work_dir and self.work_dir.exists():
            shutil.rmtree(self.work_dir)
            logger.info("🧹 Cleanup completed")
    
    def run(self) -> int:
        """Run the complete pipeline"""
        try:
            # Record start time for metadata
            self._start_time = time.time()
            
            # Set up workspace
            self.setup_workspace()
            
            # Extract images
            image_count = self.extract_images()
            if image_count == 0:
                logger.error("❌ No images found to process")
                return 1
            
            # Process GPS data (if available)
            has_gps = self.process_gps_data()
            
            # Create OpenSfM config
            self.create_opensfm_config()
            
            # Copy images
            self.copy_images_to_opensfm()
            
            # Run OpenSfM
            logger.info("🔄 Running OpenSfM reconstruction...")
            if not self.run_opensfm_commands():
                logger.error("❌ OpenSfM reconstruction failed")
                return 1
            
            # Validate reconstruction
            if not self.validate_reconstruction():
                return 1
            
            # Convert to COLMAP format
            logger.info("🔄 Converting to COLMAP format...")
            if not self.convert_to_colmap():
                return 1
            
            # Generate additional artifacts for 3DGS compatibility
            logger.info("🔄 Generating additional artifacts for 3DGS compatibility...")
            self.copy_images_for_3dgs()
            self.generate_metadata_json()
            self.create_stub_database()
            
            logger.info("✅ OpenSfM GPS pipeline completed successfully")
            return 0
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed with error: {e}")
            import traceback
            traceback.print_exc()
            return 1
        
        finally:
            # Always cleanup
            self.cleanup()


def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: python run_opensfm_gps.py <input_dir> <output_dir> [gps_csv]")
        sys.exit(1)
    
    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    gps_csv = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    
    # Run pipeline
    pipeline = OpenSfMGPSPipeline(input_dir, output_dir, gps_csv)
    exit_code = pipeline.run()
    
    logger.info(f"🏁 Pipeline finished with exit code: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main() 