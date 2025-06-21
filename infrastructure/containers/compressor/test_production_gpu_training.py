#!/usr/bin/env python3
"""
Production SOGS Test using SageMaker Training Job with GPU
Uses the approved ml.g4dn.xlarge quota for training jobs
"""

import boto3
import json
import time
import os
from sagemaker.pytorch import PyTorch
from sagemaker import get_execution_role

# Configuration
REGION = 'us-west-2'
BUCKET_NAME = 'spaceport-sagemaker-us-west-2'
INPUT_KEY = 'test-data/3dgs_sample.ply'  # Use proper 3DGS PLY file
OUTPUT_PREFIX = f'production-gpu-training/test-{int(time.time())}'

# Use PyTorch container with CUDA support and complete runtime
PYTORCH_VERSION = '2.0.1'
PYTHON_VERSION = 'py310'
# Use GPU container with complete CUDA runtime
CONTAINER_URI = f'763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-training:{PYTORCH_VERSION}-gpu-{PYTHON_VERSION}-cu118-ubuntu20.04-sagemaker'
INSTANCE_TYPE = 'ml.g4dn.xlarge'  # Approved GPU quota for training jobs

def create_training_script():
    """Create training script that does SOGS compression"""
    
    script_content = '''#!/usr/bin/env python3
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
            'git+https://github.com/fraunhoferhhi/PLAS.git'  # PLAS algorithm - CORRECT REPO!
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
        
        # Run SOGS compression (GPU will be used automatically if available)
        cmd = [
            "sogs-compress", 
            "--ply", input_file,
            "--output-dir", output_dir
        ]
        
        logger.info(f"🎯 Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ SOGS compression completed successfully!")
            logger.info(f"📊 STDOUT: {result.stdout}")
        else:
            logger.error(f"❌ SOGS failed: {result.stderr}")
            raise Exception("SOGS compression failed")
            
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
'''
    
    with open('sogs_training_script.py', 'w') as f:
        f.write(script_content)
    
    return 'sogs_training_script.py'

def main():
    """Main test execution"""
    print("🚀 Production SOGS GPU Training Test")
    print("=" * 50)
    
    # Create training script
    script_file = create_training_script()
    print(f"✅ Created training script: {script_file}")
    
    # Initialize SageMaker
    import sagemaker
    session = sagemaker.Session()
    
    try:
        role = get_execution_role()
        print(f"✅ Using execution role: {role}")
    except:
        # Find SageMaker role
        iam = boto3.client('iam')
        roles = iam.list_roles()['Roles']
        sagemaker_roles = [r for r in roles if 'SageMaker' in r['RoleName']]
        if sagemaker_roles:
            role = sagemaker_roles[0]['Arn']
            print(f"✅ Using found role: {role}")
        else:
            print("❌ No SageMaker role found")
            return False
    
    # Create PyTorch estimator with GPU
    estimator = PyTorch(
        entry_point=script_file,
        framework_version=PYTORCH_VERSION,
        py_version=PYTHON_VERSION,
        role=role,
        instance_type=INSTANCE_TYPE,  # GPU instance with approved quota
        instance_count=1,
        volume_size=50,
        max_run=3600,  # 1 hour max
        base_job_name='sogs-production-gpu',
        sagemaker_session=session,
        environment={
            'BUCKET_NAME': BUCKET_NAME,
            'INPUT_KEY': INPUT_KEY,
            'OUTPUT_PREFIX': OUTPUT_PREFIX
        },
        image_uri=CONTAINER_URI
    )
    
    print(f"🖥️ Instance: {INSTANCE_TYPE} (GPU with approved quota)")
    print(f"🐍 PyTorch: {PYTORCH_VERSION}")
    print(f"📥 Input: s3://{BUCKET_NAME}/{INPUT_KEY}")
    print(f"📤 Output: s3://{BUCKET_NAME}/{OUTPUT_PREFIX}/")
    
    try:
        print("\n🚀 Starting GPU training job...")
        
        # Start training job (no inputs needed - script downloads from S3)
        estimator.fit(wait=True, logs=True)
        
        print("\n🎉 GPU training completed!")
        
        # Check results in S3
        s3_client = boto3.client('s3', region_name=REGION)
        
        try:
            response = s3_client.list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix=OUTPUT_PREFIX
            )
            
            if 'Contents' in response:
                print(f"\n📁 Output files ({len(response['Contents'])}):")
                total_size = 0
                for obj in response['Contents']:
                    size = obj['Size']
                    total_size += size
                    print(f"   {obj['Key']} ({size} bytes)")
                
                print(f"📊 Total output: {total_size} bytes")
                
                # Read results
                try:
                    results_key = f"{OUTPUT_PREFIX}/training_results.json"
                    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=results_key)
                    results = json.loads(response['Body'].read().decode('utf-8'))
                    
                    print(f"\n🎯 GPU Training Results:")
                    print(f"   Status: {results.get('job_status', 'unknown')}")
                    print(f"   SOGS Method: {results.get('sogs_method', 'unknown')}")
                    print(f"   GPU Available: {results.get('gpu_available', False)}")
                    
                    if 'compression_result' in results:
                        comp = results['compression_result']
                        print(f"   Compression Ratio: {comp.get('compression_ratio', 'unknown'):.1f}x")
                        print(f"   Processing Time: {comp.get('processing_time', 'unknown'):.1f}s")
                        print(f"   GPU Used: {comp.get('gpu_used', False)}")
                        print(f"   Method: {comp.get('method', 'unknown')}")
                    
                except Exception as e:
                    print(f"Could not read results: {e}")
            
            else:
                print("❌ No output files found")
        
        except Exception as e:
            print(f"Error checking outputs: {e}")
        
        # Cleanup
        if os.path.exists(script_file):
            os.remove(script_file)
        
        return True
        
    except Exception as e:
        print(f"\n❌ GPU training failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Production GPU training completed successfully!")
        print("🎉 REAL SOGS compression with GPU achieved!")
    else:
        print("\n❌ Production GPU training failed!")
        exit(1) 