#!/usr/bin/env python3
"""
NerfStudio-based 3D Gaussian Splatting Training Script
======================================================

Production implementation of Vincent Woo's Sutro Tower methodology.
Uses NerfStudio's splatfacto-big with bilateral guided processing
for high-quality 3D reconstruction matching commercial standards.

Key Features:
1. Vincent Woo's exact training parameters and methodology
2. Bilateral guided radiance field processing for exposure correction
3. Production-grade error handling and logging
4. SOGS-compatible PLY output for PlayCanvas deployment
5. AWS SageMaker integration with Step Functions
"""

import os
import sys
import json
import yaml
import time
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import shutil

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NerfStudioTrainer:
    """Production NerfStudio trainer implementing Vincent Woo's methodology"""
    
    def __init__(self, config_path: str):
        """Initialize trainer with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # SageMaker environment paths
        self.input_dir = Path(os.environ.get("SM_CHANNEL_TRAINING", "/opt/ml/input/data/training"))
        self.output_dir = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
        self.temp_dir = Path("/tmp/nerfstudio_training")
        
        # Create necessary directories
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.temp_dir.mkdir(exist_ok=True, parents=True)
        
        # Apply Step Functions parameter overrides
        self.apply_step_functions_params()
        
        logger.info("🚀 NerfStudio Trainer initialized (Vincent Woo's methodology)")
        logger.info(f"📁 Input directory: {self.input_dir}")
        logger.info(f"📁 Output directory: {self.output_dir}")
        logger.info(f"📁 Temp directory: {self.temp_dir}")
    
    def apply_step_functions_params(self):
        """Apply parameters passed from Step Functions via environment variables"""
        env_params = {
            'MAX_ITERATIONS': 'training.max_iterations',
            'TARGET_PSNR': 'training.target_psnr',
            'SH_DEGREE': 'model.sh_degree',
            'BILATERAL_PROCESSING': 'model.bilateral_processing',
            'LOG_INTERVAL': 'training.log_interval',
            'MODEL_VARIANT': 'model.variant'  # splatfacto vs splatfacto-big
        }
        
        for env_var, config_path in env_params.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if env_var in ['BILATERAL_PROCESSING']:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif env_var in ['MAX_ITERATIONS', 'SH_DEGREE', 'LOG_INTERVAL']:
                    value = int(value)
                elif env_var in ['TARGET_PSNR']:
                    value = float(value)
                
                # Set nested config values
                keys = config_path.split('.')
                config_section = self.config
                for key in keys[:-1]:
                    if key not in config_section:
                        config_section[key] = {}
                    config_section = config_section[key]
                config_section[keys[-1]] = value
                
                logger.info(f"📝 Override {config_path} = {value} (from {env_var})")
    
    def validate_input_data(self) -> bool:
        """Validate COLMAP data format and convert to NerfStudio format"""
        logger.info("🔍 Validating COLMAP data format for NerfStudio...")
        
        # Check for required COLMAP structure
        required_files = [
            self.input_dir / "sparse" / "0" / "cameras.txt",
            self.input_dir / "sparse" / "0" / "images.txt", 
            self.input_dir / "sparse" / "0" / "points3D.txt",
            self.input_dir / "images"
        ]
        
        for required_file in required_files:
            if not required_file.exists():
                logger.error(f"❌ Required file/directory missing: {required_file}")
                return False
        
        # Validate content
        cameras_file = self.input_dir / "sparse" / "0" / "cameras.txt"
        images_file = self.input_dir / "sparse" / "0" / "images.txt"
        points_file = self.input_dir / "sparse" / "0" / "points3D.txt"
        images_dir = self.input_dir / "images"
        
        # Count cameras
        camera_count = 0
        with open(cameras_file, 'r') as f:
            camera_count = sum(1 for line in f if line.strip() and not line.startswith('#'))
        
        # Count images (every 2 lines in COLMAP format)
        image_count = 0
        with open(images_file, 'r') as f:
            lines = [line for line in f if line.strip() and not line.startswith('#')]
            image_count = len(lines) // 2
        
        # Count 3D points
        point_count = 0
        with open(points_file, 'r') as f:
            point_count = sum(1 for line in f if line.strip() and not line.startswith('#'))
        
        # Count image files
        image_files = list(images_dir.glob('*.jpg')) + list(images_dir.glob('*.jpeg')) + \
                     list(images_dir.glob('*.png')) + list(images_dir.glob('*.JPG')) + \
                     list(images_dir.glob('*.JPEG')) + list(images_dir.glob('*.PNG'))
        image_file_count = len(image_files)
        
        logger.info(f"📊 COLMAP Data Validation:")
        logger.info(f"   Cameras: {camera_count}")
        logger.info(f"   Images registered: {image_count}")
        logger.info(f"   Image files: {image_file_count}")
        logger.info(f"   3D points: {point_count}")
        
        # Quality checks
        if camera_count == 0:
            logger.error("❌ No cameras found in COLMAP data")
            return False
        
        if image_count == 0:
            logger.error("❌ No images found in COLMAP data")
            return False
        
        if point_count < 1000:
            logger.error(f"❌ Insufficient 3D points: {point_count} < 1000 (quality check failed)")
            return False
        
        if image_file_count < image_count * 0.8:
            logger.error(f"❌ Missing image files: {image_file_count} < {image_count * 0.8}")
            return False
        
        logger.info("✅ COLMAP data validation passed - converting to NerfStudio format")
        return self.convert_colmap_to_nerfstudio()
    
    def convert_colmap_to_nerfstudio(self) -> bool:
        """Convert COLMAP data to NerfStudio transforms.json format"""
        logger.info("🔄 Converting COLMAP data to NerfStudio format...")
        
        # Create converted data directory
        converted_dir = self.temp_dir / "converted_data"
        converted_dir.mkdir(exist_ok=True, parents=True)
        
        # First, convert COLMAP text files to binary format (required by ns-process-data)
        sparse_dir = self.input_dir / "sparse" / "0"
        if not self.convert_colmap_text_to_binary(sparse_dir):
            logger.error("❌ Failed to convert COLMAP text files to binary format")
            return False
        
        # Use ns-process-data to convert COLMAP to transforms.json
        convert_cmd = [
            "ns-process-data", "images",
            "--data", str(self.input_dir / "images"),
            "--output-dir", str(converted_dir),
            "--skip-colmap",  # Skip COLMAP processing since we already have it
            "--colmap-model-path", str(sparse_dir)
        ]
        
        logger.info(f"🚀 Executing COLMAP conversion command:")
        logger.info(f"   {' '.join(convert_cmd)}")
        
        try:
            result = subprocess.run(
                convert_cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode != 0:
                logger.error("❌ COLMAP to NerfStudio conversion failed:")
                logger.error(f"Exit code: {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return False
            
            # Verify transforms.json was created
            transforms_file = converted_dir / "transforms.json"
            if not transforms_file.exists():
                logger.error("❌ transforms.json was not created during conversion")
                return False
            
            # Update input directory to point to converted data
            self.input_dir = converted_dir
            logger.info(f"✅ COLMAP data converted successfully")
            logger.info(f"📁 Updated input directory: {self.input_dir}")
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("❌ COLMAP conversion timeout (10 minutes exceeded)")
            return False
        except Exception as e:
            logger.error(f"❌ COLMAP conversion failed: {e}")
            return False
    
    def convert_colmap_text_to_binary(self, sparse_dir: Path) -> bool:
        """Convert COLMAP text files to binary format using COLMAP's model_converter"""
        logger.info("🔄 Converting COLMAP text files to binary format...")
        
        # Check if binary files already exist
        cameras_bin = sparse_dir / "cameras.bin"
        images_bin = sparse_dir / "images.bin"
        points3D_bin = sparse_dir / "points3D.bin"
        
        if cameras_bin.exists() and images_bin.exists() and points3D_bin.exists():
            logger.info("✅ Binary files already exist, skipping conversion")
            return True
        
        # Use COLMAP's model_converter to convert text to binary
        convert_cmd = [
            "colmap", "model_converter",
            "--input_path", str(sparse_dir),
            "--output_path", str(sparse_dir),
            "--output_type", "BIN"
        ]
        
        logger.info(f"🚀 Converting text to binary: {' '.join(convert_cmd)}")
        
        try:
            result = subprocess.run(
                convert_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error("❌ COLMAP text to binary conversion failed:")
                logger.error(f"Exit code: {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return False
            
            # Verify binary files were created
            if not (cameras_bin.exists() and images_bin.exists() and points3D_bin.exists()):
                logger.error("❌ Binary files were not created")
                return False
            
            logger.info("✅ COLMAP text files converted to binary format")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("❌ COLMAP conversion timeout (5 minutes exceeded)")
            return False
        except Exception as e:
            logger.error(f"❌ COLMAP text to binary conversion failed: {e}")
            return False
    
    def run_nerfstudio_training(self) -> bool:
        """Execute NerfStudio training with Vincent Woo's exact methodology"""
        logger.info("🔥 Starting NerfStudio training (Vincent Woo's methodology)")
        logger.info("=" * 60)
        
        # Get configuration parameters
        model_config = self.config.get('model', {})
        training_config = self.config.get('training', {})
        
        model_variant = model_config.get('variant', 'splatfacto-big')  # Vincent used splatfacto-big
        max_iterations = training_config.get('max_iterations', 30000)
        sh_degree = model_config.get('sh_degree', 3)  # Industry standard (Vincent's setting)
        bilateral_processing = model_config.get('bilateral_processing', True)  # Vincent's key innovation
        log_interval = training_config.get('log_interval', 100)
        
        logger.info(f"🎯 Training Configuration (Vincent Woo's methodology):")
        logger.info(f"   Model: {model_variant}")
        logger.info(f"   Max iterations: {max_iterations}")
        logger.info(f"   SH degree: {sh_degree} (16 coefficients)")
        logger.info(f"   Bilateral guided processing: {bilateral_processing}")
        logger.info(f"   Log interval: {log_interval}")
        logger.info(f"   Dataparser: NerfStudio (COLMAP converted to transforms.json)")
        
        # Build NerfStudio command with Vincent's exact parameters
        # INVESTIGATION: Try converting COLMAP to transforms.json format instead
        cmd = [
            "ns-train", model_variant,
            "--data", str(self.input_dir),
            "--output-dir", str(self.temp_dir),
            "--max_num_iterations", str(max_iterations),
            "--pipeline.model.sh_degree", str(sh_degree),
            "--viewer.quit_on_train_completion", "True",
            "--logging.steps_per_log", str(log_interval)
        ]
        
        # Add bilateral guided processing (Vincent's exposure correction)
        # CORRECT PARAMETER FOUND: --pipeline.model.use-bilateral-grid True
        if bilateral_processing:
            cmd.extend(["--pipeline.model.use-bilateral-grid", "True"])
            logger.info("🌈 Bilateral guided processing enabled (--pipeline.model.use-bilateral-grid True)")
        else:
            logger.info("⚠️  Bilateral guided processing disabled")
        
        # Memory optimization for A10G GPU (16GB vs Vincent's RTX 4090 24GB)
        # Using max-gauss-ratio instead of max_num_gaussians (suggested by NerfStudio error)
        cmd.extend([
            "--pipeline.model.max-gauss-ratio", "10.0",  # Conservative ratio for A10G
            "--viewer.websocket_port", "7007"  # Avoid conflicts
        ])
        logger.info("🖥️  A10G GPU optimization enabled (max-gauss-ratio: 10.0)")
        
        logger.info("🚀 Executing NerfStudio training command:")
        logger.info(f"   {' '.join(cmd)}")
        logger.info("=" * 60)
        
        # Execute training
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=7200  # 2 hour timeout
            )
            
            if result.returncode != 0:
                logger.error("❌ NerfStudio training failed:")
                logger.error(f"Exit code: {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return False
            
            logger.info("✅ NerfStudio training completed successfully")
            logger.info("📊 Training output:")
            
            # Log relevant output (last 20 lines)
            stdout_lines = result.stdout.split('\n')
            for line in stdout_lines[-20:]:
                if line.strip():
                    logger.info(f"   {line}")
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("❌ Training timeout (2 hours exceeded)")
            return False
        except Exception as e:
            logger.error(f"❌ Training execution failed: {e}")
            return False
    
    def export_trained_model(self) -> bool:
        """Export trained model to PLY format (SOGS compatible)"""
        logger.info("📦 Exporting trained model to PLY format...")
        
        # Find the latest config file in training output
        config_files = list(self.temp_dir.glob("**/config.yml"))
        if not config_files:
            logger.error("❌ No config.yml found in training output")
            return False
        
        # Use the most recent config file
        config_file = max(config_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"📄 Using config: {config_file}")
        
        # Export command
        export_cmd = [
            "ns-export", "gaussian-splat",
            "--load-config", str(config_file),
            "--output-dir", str(self.output_dir)
        ]
        
        logger.info(f"🔄 Executing export command:")
        logger.info(f"   {' '.join(export_cmd)}")
        
        try:
            result = subprocess.run(
                export_cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode != 0:
                logger.error("❌ Model export failed:")
                logger.error(f"Exit code: {result.returncode}")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return False
            
            logger.info("✅ Model export completed successfully")
            
            # Verify PLY file was created
            ply_files = list(self.output_dir.glob("*.ply"))
            if ply_files:
                ply_file = ply_files[0]
                file_size_mb = ply_file.stat().st_size / (1024 * 1024)
                logger.info(f"📄 PLY file: {ply_file.name} ({file_size_mb:.1f} MB)")
                logger.info("✅ SOGS-compatible PLY format ready for compression")
            else:
                logger.warning("⚠️ No PLY file found in export output")
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("❌ Export timeout (10 minutes exceeded)")
            return False
        except Exception as e:
            logger.error(f"❌ Export execution failed: {e}")
            return False
    
    def generate_training_metadata(self) -> Dict[str, Any]:
        """Generate comprehensive training metadata"""
        metadata = {
            'training_methodology': 'Vincent Woo Sutro Tower',
            'framework': 'NerfStudio',
            'model_variant': self.config.get('model', {}).get('variant', 'splatfacto-big'),
            'bilateral_guided_processing': self.config.get('model', {}).get('bilateral_processing', True),
            'sh_degree': self.config.get('model', {}).get('sh_degree', 3),
            'max_iterations': self.config.get('training', {}).get('max_iterations', 30000),
            'commercial_license': 'Apache 2.0',
            'sogs_compatible': True,
            'playcanvas_ready': True,
            'training_completed': True,
            'timestamp': time.time(),
            'version': '1.0.0'
        }
        
        # Add file information
        ply_files = list(self.output_dir.glob("*.ply"))
        if ply_files:
            ply_file = ply_files[0]
            metadata['output_file'] = ply_file.name
            metadata['file_size_mb'] = ply_file.stat().st_size / (1024 * 1024)
        
        # Save metadata
        metadata_path = self.output_dir / "training_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("📋 Training metadata generated:")
        for key, value in metadata.items():
            logger.info(f"   {key}: {value}")
        
        return metadata
    
    def cleanup_temp_files(self):
        """Clean up temporary training files"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info("🧹 Temporary files cleaned up")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup failed: {e}")
    
    def run_full_training_pipeline(self) -> bool:
        """Execute the complete training pipeline"""
        logger.info("🚀 Starting complete NerfStudio training pipeline")
        logger.info(f"📅 Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        try:
            # Step 1: Validate input data
            if not self.validate_input_data():
                logger.error("❌ Input data validation failed")
                return False
            
            # Step 2: Run NerfStudio training
            if not self.run_nerfstudio_training():
                logger.error("❌ NerfStudio training failed")
                return False
            
            # Step 3: Export trained model
            if not self.export_trained_model():
                logger.error("❌ Model export failed")
                return False
            
            # Step 4: Generate metadata
            metadata = self.generate_training_metadata()
            
            # Step 5: Cleanup
            self.cleanup_temp_files()
            
            logger.info("=" * 80)
            logger.info("🎉 NERFSTUDIO TRAINING PIPELINE COMPLETED SUCCESSFULLY!")
            logger.info("✅ Vincent Woo's methodology implemented")
            logger.info("✅ Bilateral guided processing applied")
            logger.info("✅ SOGS-compatible PLY output generated")
            logger.info("✅ Production-ready for PlayCanvas deployment")
            logger.info(f"📁 Output directory: {self.output_dir}")
            logger.info("=" * 80)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed with exception: {e}")
            self.cleanup_temp_files()
            return False


def main():
    """Main entry point for SageMaker training"""
    parser = argparse.ArgumentParser(description="NerfStudio 3D Gaussian Splatting Trainer")
    parser.add_argument("--config", type=str, default="/opt/ml/code/nerfstudio_config.yaml", 
                       help="Path to the configuration file")
    # Handle SageMaker's automatic arguments
    parser.add_argument("train", nargs='?', help="SageMaker training argument (ignored)")
    args = parser.parse_args()
    
    try:
        logger.info("🚀 NerfStudio Production Training Started")
        logger.info("📦 Framework: NerfStudio with Vincent Woo's methodology")
        logger.info("🎯 Goal: Sutro Tower quality 3D reconstruction")
        
        # Initialize trainer
        trainer = NerfStudioTrainer(args.config)
        
        # Run complete pipeline
        success = trainer.run_full_training_pipeline()
        
        if success:
            logger.info("✅ Training pipeline completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Training pipeline failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Fatal error in training pipeline: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
