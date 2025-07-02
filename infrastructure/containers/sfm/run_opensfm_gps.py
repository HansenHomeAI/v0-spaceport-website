#!/usr/bin/env python3
"""
Production OpenSfM GPS-Constrained Reconstruction
Main processing script for drone imagery with flight path data
"""

import os
import sys
import json
import shutil
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
import yaml

# Import our custom modules
from gps_processor import DroneFlightPathProcessor
from colmap_converter import OpenSfMToCOLMAPConverter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/opensfm_processing.log')
    ]
)
logger = logging.getLogger(__name__)


class SpaceportOpenSfMProcessor:
    """Main processor for GPS-constrained OpenSfM reconstruction"""
    
    def __init__(self, input_dir: Path, output_dir: Path):
        """
        Initialize the processor
        
        Args:
            input_dir: SageMaker input directory (/opt/ml/processing/input)
            output_dir: SageMaker output directory (/opt/ml/processing/output)
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.work_dir = Path("/tmp/opensfm_work")
        
        # Processing paths
        self.images_dir = self.work_dir / "images"
        self.opensfm_dir = self.work_dir / "opensfm"
        self.colmap_output_dir = self.output_dir / "sparse" / "0"
        
        # Processing statistics
        self.stats = {
            'start_time': datetime.utcnow().isoformat(),
            'pipeline_version': 'opensfm_gps_v1.0',
            'processing_steps': [],
            'errors': [],
            'warnings': []
        }
        
        logger.info(f"🚀 Initializing Spaceport OpenSfM GPS Processor")
        logger.info(f"   Input: {input_dir}")
        logger.info(f"   Output: {output_dir}")
        logger.info(f"   Work: {self.work_dir}")
    
    def setup_directories(self) -> None:
        """Create necessary working directories"""
        try:
            # Create work directories
            self.work_dir.mkdir(parents=True, exist_ok=True)
            self.images_dir.mkdir(parents=True, exist_ok=True)
            self.opensfm_dir.mkdir(parents=True, exist_ok=True)
            
            # Create output directories
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.colmap_output_dir.mkdir(parents=True, exist_ok=True)
            (self.output_dir / "dense").mkdir(parents=True, exist_ok=True)
            (self.output_dir / "images").mkdir(parents=True, exist_ok=True)
            
            logger.info("✅ Created working directories")
            
        except Exception as e:
            logger.error(f"❌ Failed to create directories: {e}")
            raise
    
    def extract_input_data(self) -> Tuple[Path, Optional[Path]]:
        """Extract images and find CSV file from input"""
        logger.info("📁 Extracting input data...")
        
        try:
            # List input contents
            input_files = list(self.input_dir.rglob('*'))
            logger.info(f"🔍 Found {len(input_files)} input files")
            
            # Find image archive (ZIP)
            image_archive = None
            for file_path in input_files:
                if file_path.suffix.lower() == '.zip':
                    image_archive = file_path
                    break
            
            if not image_archive:
                raise FileNotFoundError("No ZIP archive found in input directory")
            
            # Find CSV file
            csv_file = None
            for file_path in input_files:
                if file_path.suffix.lower() == '.csv':
                    csv_file = file_path
                    break
            
            # Extract image archive
            logger.info(f"📦 Extracting images from: {image_archive}")
            subprocess.run(['unzip', '-q', str(image_archive), '-d', str(self.images_dir)], 
                         check=True)
            
            # Count extracted images
            image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
            images = [f for f in self.images_dir.rglob('*') if f.suffix in image_extensions]
            logger.info(f"📸 Extracted {len(images)} images")
            
            if len(images) == 0:
                raise ValueError("No images found in archive")
            
            # Log CSV status
            if csv_file:
                logger.info(f"🛰️ Found GPS flight path: {csv_file}")
            else:
                logger.warning("⚠️ No CSV flight path found - will proceed without GPS constraints")
            
            self.stats['processing_steps'].append({
                'step': 'extract_input',
                'status': 'completed',
                'images_count': len(images),
                'has_gps_data': csv_file is not None,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return image_archive, csv_file
            
        except Exception as e:
            logger.error(f"❌ Failed to extract input data: {e}")
            self.stats['errors'].append(f"extract_input: {str(e)}")
            raise
    
    def process_gps_data(self, csv_file: Path) -> Optional[DroneFlightPathProcessor]:
        """Process GPS flight path data"""
        if not csv_file:
            logger.info("⚠️ No GPS data available - using traditional SfM")
            return None
        
        logger.info("🛰️ Processing GPS flight path data...")
        
        try:
            # Initialize GPS processor
            gps_processor = DroneFlightPathProcessor(csv_file, self.images_dir)
            
            # Parse flight data
            flight_data = gps_processor.parse_flight_csv()
            logger.info(f"✅ Parsed {len(flight_data)} GPS waypoints")
            
            # Get photo list
            photos = gps_processor.get_photo_list()
            logger.info(f"📸 Found {len(photos)} photos to process")
            
            # Map photos to GPS coordinates
            mapping = gps_processor.map_photos_to_gps_sequential(photos)
            logger.info(f"🗺️ Mapped {len(mapping)} photos to GPS coordinates")
            
            # Setup local coordinate system
            gps_processor.setup_local_coordinate_system()
            
            # Generate OpenSfM GPS files
            gps_processor.generate_opensfm_gps_file(self.opensfm_dir / "gps_list.txt")
            gps_processor.create_reference_lla_file(self.opensfm_dir / "reference.lla")
            
            # Get processing statistics
            gps_stats = gps_processor.get_processing_stats()
            
            self.stats['processing_steps'].append({
                'step': 'process_gps',
                'status': 'completed',
                'gps_stats': gps_stats,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.info("✅ GPS data processing completed")
            return gps_processor
            
        except Exception as e:
            logger.error(f"❌ GPS processing failed: {e}")
            self.stats['errors'].append(f"process_gps: {str(e)}")
            self.stats['warnings'].append("Falling back to traditional SfM without GPS")
            return None
    
    def create_opensfm_config(self, has_gps: bool, gps_processor: Optional[DroneFlightPathProcessor] = None) -> Path:
        """Create OpenSfM configuration file"""
        logger.info("⚙️ Creating OpenSfM configuration...")
        
        try:
            # Load base configuration template
            config_template_path = Path("/opt/ml/code/config_template.yaml")
            with open(config_template_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Modify configuration based on GPS availability
            if has_gps and gps_processor:
                # GPS-enhanced configuration
                config['use_gps'] = True
                config['reconstruct_with_gps'] = True
                config['bundle_use_gps'] = True
                
                # Set reference location if available
                if gps_processor.local_origin:
                    lat, lon = gps_processor.local_origin
                    config['reference_lla'] = [lat, lon, 0.0]
                
                logger.info("✅ Configured for GPS-constrained reconstruction")
            else:
                # Traditional SfM configuration
                config['use_gps'] = False
                config['reconstruct_with_gps'] = False
                config['bundle_use_gps'] = False
                
                logger.info("✅ Configured for traditional SfM reconstruction")
            
            # Save configuration
            config_path = self.opensfm_dir / "config.yaml"
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            logger.info(f"✅ Created OpenSfM config: {config_path}")
            return config_path
            
        except Exception as e:
            logger.error(f"❌ Failed to create OpenSfM config: {e}")
            raise
    
    def copy_images_to_opensfm(self) -> None:
        """Copy images to OpenSfM directory"""
        logger.info("📷 Copying images to OpenSfM directory...")
        
        try:
            opensfm_images_dir = self.opensfm_dir / "images"
            opensfm_images_dir.mkdir(exist_ok=True)
            
            # Copy all images
            image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
            images = [f for f in self.images_dir.rglob('*') if f.suffix in image_extensions]
            
            copied_count = 0
            for image_path in images:
                dest_path = opensfm_images_dir / image_path.name
                shutil.copy2(image_path, dest_path)
                copied_count += 1
            
            logger.info(f"✅ Copied {copied_count} images to OpenSfM")
            
        except Exception as e:
            logger.error(f"❌ Failed to copy images: {e}")
            raise
    
    def run_opensfm_reconstruction(self) -> bool:
        """Run OpenSfM reconstruction pipeline"""
        logger.info("🔄 Running OpenSfM reconstruction...")
        
        try:
            # Change to OpenSfM directory
            os.chdir(self.opensfm_dir)
            
            # OpenSfM pipeline steps
            steps = [
                ("extract_metadata", "Extract image metadata"),
                ("detect_features", "Detect features"),
                ("match_features", "Match features"),
                ("create_tracks", "Create tracks"),
                ("reconstruct", "Reconstruct")
            ]
            
            for step_name, step_description in steps:
                logger.info(f"🔧 {step_description}...")
                
                try:
                    # Run OpenSfM command
                    cmd = ["opensfm", step_name, str(self.opensfm_dir)]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
                    
                    if result.returncode != 0:
                        logger.error(f"❌ OpenSfM {step_name} failed:")
                        logger.error(f"   stdout: {result.stdout}")
                        logger.error(f"   stderr: {result.stderr}")
                        return False
                    
                    logger.info(f"✅ {step_description} completed")
                    
                except subprocess.TimeoutExpired:
                    logger.error(f"❌ OpenSfM {step_name} timed out")
                    return False
                except Exception as e:
                    logger.error(f"❌ OpenSfM {step_name} error: {e}")
                    return False
            
            # Check if reconstruction was successful
            reconstruction_file = self.opensfm_dir / "reconstruction.json"
            if not reconstruction_file.exists():
                logger.error("❌ No reconstruction.json file generated")
                return False
            
            # Validate reconstruction
            with open(reconstruction_file, 'r') as f:
                reconstructions = json.load(f)
            
            if not reconstructions:
                logger.error("❌ Empty reconstruction file")
                return False
            
            reconstruction = reconstructions[0]
            point_count = len(reconstruction.get('points', {}))
            shot_count = len(reconstruction.get('shots', {}))
            camera_count = len(reconstruction.get('cameras', {}))
            
            logger.info(f"✅ OpenSfM reconstruction completed:")
            logger.info(f"   Cameras: {camera_count}")
            logger.info(f"   Shots: {shot_count}")
            logger.info(f"   Points: {point_count}")
            
            # Quality check (same as COLMAP pipeline)
            min_points_required = 1000
            if point_count < min_points_required:
                logger.error(f"❌ Insufficient 3D points: {point_count} < {min_points_required}")
                logger.error("❌ Reconstruction quality too low for 3DGS training")
                return False
            
            self.stats['processing_steps'].append({
                'step': 'opensfm_reconstruction',
                'status': 'completed',
                'cameras': camera_count,
                'shots': shot_count,
                'points': point_count,
                'quality_check': 'passed',
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ OpenSfM reconstruction failed: {e}")
            logger.error(traceback.format_exc())
            self.stats['errors'].append(f"opensfm_reconstruction: {str(e)}")
            return False
    
    def convert_to_colmap_format(self) -> bool:
        """Convert OpenSfM output to COLMAP format"""
        logger.info("🔄 Converting to COLMAP format...")
        
        try:
            # Initialize converter
            converter = OpenSfMToCOLMAPConverter(self.opensfm_dir, self.colmap_output_dir)
            
            # Run conversion
            validation = converter.convert_full_reconstruction()
            
            if not validation['quality_check_passed']:
                logger.error("❌ COLMAP conversion failed quality check")
                return False
            
            logger.info("✅ COLMAP format conversion completed")
            
            self.stats['processing_steps'].append({
                'step': 'colmap_conversion',
                'status': 'completed',
                'validation': validation,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ COLMAP conversion failed: {e}")
            self.stats['errors'].append(f"colmap_conversion: {str(e)}")
            return False
    
    def copy_output_files(self) -> None:
        """Copy all necessary output files"""
        logger.info("📋 Copying output files...")
        
        try:
            # Copy original images for 3DGS training
            output_images_dir = self.output_dir / "images"
            output_images_dir.mkdir(exist_ok=True)
            
            image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
            images = [f for f in self.images_dir.rglob('*') if f.suffix in image_extensions]
            
            for image_path in images:
                dest_path = output_images_dir / image_path.name
                shutil.copy2(image_path, dest_path)
            
            # Copy reference point cloud to dense directory
            dense_dir = self.output_dir / "dense"
            dense_dir.mkdir(exist_ok=True)
            
            sparse_ply = self.colmap_output_dir / "sparse_points.ply"
            if sparse_ply.exists():
                shutil.copy2(sparse_ply, dense_dir / "sparse_points.ply")
            
            # Create database.db placeholder (for compatibility)
            db_path = self.output_dir / "database.db"
            with open(db_path, 'wb') as f:
                f.write(b'')  # Empty file
            
            logger.info("✅ Output files copied successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to copy output files: {e}")
            raise
    
    def generate_metadata(self) -> None:
        """Generate processing metadata"""
        logger.info("📊 Generating processing metadata...")
        
        try:
            # Update final statistics
            self.stats['end_time'] = datetime.utcnow().isoformat()
            
            # Calculate processing time
            start_time = datetime.fromisoformat(self.stats['start_time'])
            end_time = datetime.fromisoformat(self.stats['end_time'])
            processing_time = (end_time - start_time).total_seconds()
            
            # Count final outputs
            cameras_file = self.colmap_output_dir / "cameras.txt"
            images_file = self.colmap_output_dir / "images.txt"
            points_file = self.colmap_output_dir / "points3D.txt"
            
            camera_count = 0
            image_count = 0
            point_count = 0
            
            if cameras_file.exists():
                with open(cameras_file, 'r') as f:
                    camera_count = sum(1 for line in f if line.strip() and not line.startswith('#'))
            
            if images_file.exists():
                with open(images_file, 'r') as f:
                    lines = [line for line in f if line.strip() and not line.startswith('#')]
                    image_count = len(lines) // 2
            
            if points_file.exists():
                with open(points_file, 'r') as f:
                    point_count = sum(1 for line in f if line.strip() and not line.startswith('#'))
            
            # Create metadata
            metadata = {
                "pipeline": "opensfm_gps_constrained",
                "version": "1.0",
                "timestamp": self.stats['end_time'],
                "processing_time_seconds": round(processing_time, 1),
                "optimization": "gps_constrained_reconstruction",
                "advantages": [
                    "GPS-enhanced pose estimation",
                    "Better handling of low-feature areas",
                    "Improved accuracy in challenging scenarios"
                ],
                "statistics": {
                    "cameras_registered": camera_count,
                    "images_registered": image_count,
                    "sparse_points": point_count,
                    "processing_steps": len(self.stats['processing_steps']),
                    "errors": len(self.stats['errors']),
                    "warnings": len(self.stats['warnings'])
                },
                "processing_steps": [
                    "gps_data_processing",
                    "feature_extraction",
                    "gps_constrained_matching",
                    "gps_constrained_reconstruction",
                    "colmap_format_conversion"
                ],
                "output_format": "colmap_text",
                "image_format": "original_with_gps_constraints",
                "ready_for_3dgs": True,
                "detailed_stats": self.stats
            }
            
            # Save metadata
            metadata_file = self.output_dir / "sfm_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info("✅ Generated processing metadata")
            logger.info(f"📊 Processing completed in {processing_time:.1f} seconds")
            logger.info(f"📷 Cameras: {camera_count}, Images: {image_count}, Points: {point_count}")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate metadata: {e}")
    
    def cleanup(self) -> None:
        """Clean up temporary files"""
        logger.info("🧹 Cleaning up temporary files...")
        
        try:
            if self.work_dir.exists():
                shutil.rmtree(self.work_dir)
            logger.info("✅ Cleanup completed")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")
    
    def run_full_pipeline(self) -> bool:
        """Run the complete GPS-constrained OpenSfM pipeline"""
        logger.info("🚀 Starting GPS-constrained OpenSfM pipeline")
        
        try:
            # Setup
            self.setup_directories()
            
            # Extract input data
            image_archive, csv_file = self.extract_input_data()
            
            # Process GPS data (if available)
            gps_processor = self.process_gps_data(csv_file)
            has_gps = gps_processor is not None
            
            # Create OpenSfM configuration
            self.create_opensfm_config(has_gps, gps_processor)
            
            # Copy images to OpenSfM directory
            self.copy_images_to_opensfm()
            
            # Run OpenSfM reconstruction
            if not self.run_opensfm_reconstruction():
                logger.error("❌ OpenSfM reconstruction failed")
                return False
            
            # Convert to COLMAP format
            if not self.convert_to_colmap_format():
                logger.error("❌ COLMAP conversion failed")
                return False
            
            # Copy output files
            self.copy_output_files()
            
            # Generate metadata
            self.generate_metadata()
            
            logger.info("🎉 GPS-constrained OpenSfM pipeline completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {e}")
            logger.error(traceback.format_exc())
            self.stats['errors'].append(f"pipeline: {str(e)}")
            return False
        
        finally:
            # Always clean up
            self.cleanup()


def main():
    """Main entry point"""
    # SageMaker paths
    input_dir = Path("/opt/ml/processing/input")
    output_dir = Path("/opt/ml/processing/output")
    
    # Initialize processor
    processor = SpaceportOpenSfMProcessor(input_dir, output_dir)
    
    # Run pipeline
    success = processor.run_full_pipeline()
    
    # Exit with appropriate code
    exit_code = 0 if success else 1
    logger.info(f"🏁 Pipeline finished with exit code: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main() 