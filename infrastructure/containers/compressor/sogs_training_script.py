#!/usr/bin/env python3
"""
SOGS Compression Training Script
Runs real SOGS compression using GPU training instance
"""

import os
import sys
import json
import time
import subprocess
import logging
import boto3
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def install_sogs():
    """Install SOGS and dependencies"""
    logger.info("🔧 Installing SOGS and dependencies...")
    
    try:
        # Skip apt-get, use pip-only approach
        logger.info("📦 Using pip-only installation approach...")
        
        # Install Python dependencies only
        python_deps = [
            'cupy-cuda12x',  # GPU acceleration - required for SOGS
            'trimesh', 'plyfile', 'structlog', 'orjson',
            'torchpq',  # Required for SOGS
            'git+https://github.com/playcanvas/plas.git'  # PLAS algorithm
        ]
        
        for dep in python_deps:
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', dep], check=True)
                logger.info(f"✅ Installed {dep}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"⚠️ Failed to install {dep}: {e}")
        
        # Install SOGS from GitHub
        try:
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', 
                'git+https://github.com/playcanvas/sogs.git'
            ], check=True, timeout=300)
            logger.info("✅ SOGS installed from GitHub")
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.warning(f"⚠️ SOGS installation failed: {e}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Installation failed: {e}")
        return False

def check_gpu():
    """Check GPU availability"""
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        gpu_count = torch.cuda.device_count()
        logger.info(f"🖥️ GPU available: {gpu_available}, Count: {gpu_count}")
        
        if gpu_available:
            for i in range(gpu_count):
                gpu_name = torch.cuda.get_device_name(i)
                gpu_memory = torch.cuda.get_device_properties(i).total_memory / 1e9
                logger.info(f"   GPU {i}: {gpu_name} ({gpu_memory:.1f} GB)")
        
        return gpu_available
    except Exception as e:
        logger.error(f"❌ GPU check failed: {e}")
        return False

def download_input_data():
    """Download input data from S3"""
    try:
        s3_client = boto3.client('s3')
        
        # Get values from environment variables
        bucket_name = os.environ.get('BUCKET_NAME', 'spaceport-sagemaker-us-west-2')
        input_key = os.environ.get('INPUT_KEY', 'test-data/sample.ply')
        
        # Create input directory
        input_dir = '/opt/ml/input/data/training'
        os.makedirs(input_dir, exist_ok=True)
        
        # Download PLY file
        local_file = os.path.join(input_dir, 'sample.ply')
        s3_client.download_file(bucket_name, input_key, local_file)
        
        logger.info(f"✅ Downloaded input: {local_file} ({os.path.getsize(local_file)} bytes)")
        return local_file
        
    except Exception as e:
        logger.error(f"❌ Download failed: {e}")
        return None

def upload_output_data(local_dir):
    """Upload output data to S3"""
    try:
        s3_client = boto3.client('s3')
        
        # Get values from environment variables
        bucket_name = os.environ.get('BUCKET_NAME', 'spaceport-sagemaker-us-west-2')
        output_prefix = os.environ.get('OUTPUT_PREFIX', 'production-gpu-training/test')
        
        upload_count = 0
        
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_path, local_dir)
                s3_key = f"{output_prefix}/{relative_path}"
                
                s3_client.upload_file(local_path, bucket_name, s3_key)
                logger.info(f"✅ Uploaded: s3://{bucket_name}/{s3_key}")
                upload_count += 1
        
        return upload_count
        
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        return 0

def run_real_sogs_compression(input_file, output_dir, gpu_available=True):
    """Run real SOGS compression"""
    try:
        logger.info("🚀 Running REAL SOGS compression with GPU!")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Try SOGS CLI
        cmd = ['sogs-compress', '--ply', input_file, '--output-dir', output_dir]
        if gpu_available:
            cmd.extend(['--gpu'])
        
        logger.info(f"🎯 Command: {' '.join(cmd)}")
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        end_time = time.time()
        
        if result.returncode == 0:
            logger.info("🎉 REAL SOGS compression SUCCESS!")
            logger.info(f"⏱️ Processing time: {end_time - start_time:.1f}s")
            logger.info(f"📤 STDOUT: {result.stdout}")
            
            # Calculate compression metrics
            input_size = os.path.getsize(input_file)
            output_size = sum(
                os.path.getsize(os.path.join(root, file))
                for root, dirs, files in os.walk(output_dir)
                for file in files
            )
            compression_ratio = input_size / output_size if output_size > 0 else 1.0
            
            return {
                'method': 'real_sogs_gpu',
                'success': True,
                'gpu_used': gpu_available,
                'processing_time': end_time - start_time,
                'input_size': input_size,
                'output_size': output_size,
                'compression_ratio': compression_ratio,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        else:
            logger.error(f"❌ SOGS failed: {result.stderr}")
            return None
            
    except Exception as e:
        logger.error(f"❌ SOGS compression error: {e}")
        return None

def main():
    """Main training function"""
    logger.info("🚀 Production SOGS GPU Training Started")
    logger.info("=" * 50)
    
    try:
        # Step 1: Install SOGS
        sogs_installed = install_sogs()
        if not sogs_installed:
            raise Exception("SOGS installation failed")
        
        # Step 2: Check GPU
        gpu_available = check_gpu()
        logger.info(f"🖥️ GPU Available: {gpu_available}")
        
        # Step 3: Download input
        input_file = download_input_data()
        if not input_file:
            raise Exception("Failed to download input data")
        
        # Step 4: Run SOGS compression
        output_dir = '/opt/ml/model'
        os.makedirs(output_dir, exist_ok=True)
        
        result = run_real_sogs_compression(input_file, output_dir, gpu_available)
        
        if result:
            logger.info("🎉 REAL SOGS COMPRESSION SUCCESSFUL!")
            logger.info(f"📊 Compression ratio: {result['compression_ratio']:.1f}x")
            logger.info(f"⏱️ Processing time: {result['processing_time']:.1f}s")
            logger.info(f"🖥️ GPU used: {result['gpu_used']}")
        else:
            raise Exception("SOGS compression failed")
        
        # Step 5: Save results
        results = {
            'job_status': 'completed',
            'sogs_method': 'real_gpu',
            'gpu_available': gpu_available,
            'compression_result': result
        }
        
        with open(os.path.join(output_dir, 'training_results.json'), 'w') as f:
            json.dump(results, f, indent=2)
        
        # Step 6: Upload to S3
        upload_count = upload_output_data(output_dir)
        logger.info(f"📤 Uploaded {upload_count} files to S3")
        
        logger.info("🎉 Production SOGS GPU Training COMPLETED!")
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        
        # Save error results
        error_results = {
            'job_status': 'failed',
            'error_message': str(e),
            'error_type': type(e).__name__
        }
        
        os.makedirs('/opt/ml/model', exist_ok=True)
        with open('/opt/ml/model/training_results.json', 'w') as f:
            json.dump(error_results, f, indent=2)
        
        raise

if __name__ == "__main__":
    main()
