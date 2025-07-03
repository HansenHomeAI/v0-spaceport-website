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
            'feature_process_size': 2048,
            'feature_min_frames': 8000,
            'sift_peak_threshold': 0.01,
            
            # Matching
            'matching_gps_neighbors': 20,
            'matching_gps_distance': 100,  # meters
            'matching_graph_rounds': 50,
            'robust_matching_min_match': 20,
            
            # Reconstruction
            'min_ray_angle_degrees': 2.0,
            'reconstruction_min_ratio': 0.8,
            'triangulation_min_ray_angle_degrees': 2.0,
            
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
            'processes': 1,  # Use single process for stability
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
        
        num_cameras = len(recon.get('shots', {}))
        num_points = len(recon.get('points', {}))
        
        logger.info(f"📊 Reconstruction statistics:")
        logger.info(f"   Cameras: {num_cameras}")
        logger.info(f"   3D points: {num_points}")
        
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
            converter.convert()
            return True
        except Exception as e:
            logger.error(f"❌ COLMAP conversion failed: {e}")
            return False
    
    def cleanup(self) -> None:
        """Clean up temporary files"""
        if self.work_dir and self.work_dir.exists():
            shutil.rmtree(self.work_dir)
            logger.info("🧹 Cleanup completed")
    
    def run(self) -> int:
        """Run the complete pipeline"""
        try:
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