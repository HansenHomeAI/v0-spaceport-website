#!/usr/bin/env python3
"""
Final Ultra-Simple SageMaker Test for SOGS Compression
Uses only the most basic SageMaker features for maximum compatibility
"""

import boto3
import json
import time
import os
from sagemaker.processing import ScriptProcessor
from sagemaker import get_execution_role

# Configuration
REGION = 'us-west-2'
BUCKET_NAME = 'spaceport-sagemaker-us-west-2'
INPUT_KEY = 'test-data/sample.ply'
OUTPUT_PREFIX = f'compression-output/test-{int(time.time())}'

# SageMaker configuration
INSTANCE_TYPE = 'ml.t3.medium'
INSTANCE_COUNT = 1
VOLUME_SIZE = 30

def create_simple_script():
    """Create an ultra-simple compression script that doesn't rely on environment variables"""
    
    script_content = '''#!/usr/bin/env python3
import os
import sys
import json
import time
import shutil
import tempfile
from pathlib import Path

# Simple logging
def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()

def create_fake_webp(filepath, size_kb=8):
    """Create a fake WebP file for testing"""
    with open(filepath, 'wb') as f:
        # WebP header
        f.write(b'RIFF')
        f.write((size_kb * 1024).to_bytes(4, 'little'))
        f.write(b'WEBP')
        f.write(b'VP8 ')
        f.write((size_kb * 1024 - 12).to_bytes(4, 'little'))
        # Fill with random-ish data
        for i in range(size_kb * 1024 - 20):
            f.write(bytes([i % 256]))

def main():
    log("=== Simple SOGS Compression Started ===")
    
    # SageMaker processing paths
    input_dir = "/opt/ml/processing/input"
    output_dir = "/opt/ml/processing/output"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Find PLY files
    ply_files = []
    if os.path.exists(input_dir):
        for file in os.listdir(input_dir):
            if file.lower().endswith('.ply'):
                ply_path = os.path.join(input_dir, file)
                ply_files.append(ply_path)
                log(f"Found PLY file: {ply_path} ({os.path.getsize(ply_path)} bytes)")
    
    if not ply_files:
        log("ERROR: No PLY files found!")
        return 1
    
    results = []
    for ply_file in ply_files:
        log(f"Processing: {ply_file}")
        
        # Get input info
        input_size = os.path.getsize(ply_file)
        file_name = Path(ply_file).stem
        
        # Create output directory
        file_output_dir = os.path.join(output_dir, file_name)
        os.makedirs(file_output_dir, exist_ok=True)
        os.makedirs(os.path.join(file_output_dir, 'images'), exist_ok=True)
        os.makedirs(os.path.join(file_output_dir, 'metadata'), exist_ok=True)
        
        start_time = time.time()
        
        # Create simulated compressed output
        create_fake_webp(os.path.join(file_output_dir, 'images', 'positions.webp'), 8)
        create_fake_webp(os.path.join(file_output_dir, 'images', 'colors.webp'), 6)
        create_fake_webp(os.path.join(file_output_dir, 'images', 'scales.webp'), 4)
        create_fake_webp(os.path.join(file_output_dir, 'images', 'rotations.webp'), 10)
        
        # Create metadata
        metadata = {
            'format': 'sogs',
            'version': '1.0',
            'compression': 'simulated',
            'gaussian_count': 50000,
            'image_dimensions': [1024, 1024]
        }
        
        with open(os.path.join(file_output_dir, 'metadata', 'scene.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Calculate output size
        output_size = 0
        for root, dirs, files in os.walk(file_output_dir):
            for file in files:
                output_size += os.path.getsize(os.path.join(root, file))
        
        end_time = time.time()
        processing_time = end_time - start_time
        compression_ratio = input_size / output_size if output_size > 0 else 1.0
        
        result = {
            'input_file': ply_file,
            'input_size_bytes': input_size,
            'output_size_bytes': output_size,
            'compression_ratio': compression_ratio,
            'processing_time_seconds': processing_time,
            'compression_percentage': ((input_size - output_size) / input_size) * 100
        }
        results.append(result)
        
        log(f"Compressed {file_name}: {compression_ratio:.1f}x ratio in {processing_time:.1f}s")
    
    # Save results
    final_results = {
        'job_status': 'completed',
        'files_processed': len(ply_files),
        'total_processing_time': sum(r['processing_time_seconds'] for r in results),
        'average_compression_ratio': sum(r['compression_ratio'] for r in results) / len(results),
        'individual_results': results
    }
    
    with open(os.path.join(output_dir, 'job_results.json'), 'w') as f:
        json.dump(final_results, f, indent=2)
    
    log(f"=== Compression Completed Successfully ===")
    log(f"Files processed: {len(ply_files)}")
    log(f"Average compression: {final_results['average_compression_ratio']:.1f}x")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
'''
    
    with open('simple_compress.py', 'w') as f:
        f.write(script_content)
    
    return 'simple_compress.py'

def upload_script_to_s3(script_file):
    """Upload the compression script to S3"""
    s3_client = boto3.client('s3', region_name=REGION)
    
    script_key = f'scripts/{script_file}'
    script_s3_uri = f's3://{BUCKET_NAME}/{script_key}'
    
    try:
        s3_client.upload_file(script_file, BUCKET_NAME, script_key)
        print(f"Uploaded script to {script_s3_uri}")
        return script_s3_uri
    except Exception as e:
        print(f"Failed to upload script: {e}")
        return None

def main():
    print("=== Final SageMaker SOGS Compression Test ===")
    
    # Create and upload simple script
    script_file = create_simple_script()
    script_s3_uri = upload_script_to_s3(script_file)
    if not script_s3_uri:
        print("❌ Failed to upload script")
        return False
    
    # Initialize SageMaker
    import sagemaker
    session = sagemaker.Session()
    
    try:
        role = get_execution_role()
        print(f"Using execution role: {role}")
    except:
        # Try to find a suitable role
        iam = boto3.client('iam')
        try:
            roles = iam.list_roles()['Roles']
            sagemaker_roles = [r for r in roles if 'SageMaker' in r['RoleName']]
            if sagemaker_roles:
                role = sagemaker_roles[0]['Arn']
                print(f"Using found SageMaker role: {role}")
            else:
                print("❌ No SageMaker role found")
                return False
        except Exception as e:
            print(f"❌ Could not find IAM role: {e}")
            return False
    
    # Create processor with minimal parameters
    processor = ScriptProcessor(
        command=['python3'],
        image_uri='246618743249.dkr.ecr.us-west-2.amazonaws.com/sagemaker-scikit-learn:0.23-1-cpu-py3',  # Use proper SageMaker container
        role=role,
        instance_type=INSTANCE_TYPE,
        instance_count=INSTANCE_COUNT,
        volume_size_in_gb=VOLUME_SIZE,
        max_runtime_in_seconds=3600,
        base_job_name='sogs-final-test',
        sagemaker_session=session
    )
    
    # Define locations
    input_s3_uri = f's3://{BUCKET_NAME}/{INPUT_KEY}'
    output_s3_uri = f's3://{BUCKET_NAME}/{OUTPUT_PREFIX}/'
    
    print(f"Input: {input_s3_uri}")
    print(f"Output: {output_s3_uri}")
    print(f"Script: {script_s3_uri}")
    
    try:
        print("\nStarting SageMaker processing job...")
        
        # Run with absolute minimal parameters
        processor.run(
            code=script_s3_uri,
            inputs=[
                sagemaker.processing.ProcessingInput(
                    source=input_s3_uri,
                    destination='/opt/ml/processing/input'
                )
            ],
            outputs=[
                sagemaker.processing.ProcessingOutput(
                    source='/opt/ml/processing/output',
                    destination=output_s3_uri
                )
            ],
            wait=True,
            logs=True
        )
        
        print("\n=== Processing Job Completed! ===")
        
        # Check outputs
        s3_client = boto3.client('s3', region_name=REGION)
        
        try:
            response = s3_client.list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix=OUTPUT_PREFIX
            )
            
            if 'Contents' in response:
                print(f"\nFound {len(response['Contents'])} output files:")
                total_size = 0
                for obj in response['Contents']:
                    size = obj['Size']
                    total_size += size
                    print(f"  - {obj['Key']} ({size} bytes)")
                
                print(f"Total output size: {total_size} bytes")
                
                # Read results
                try:
                    results_key = f"{OUTPUT_PREFIX}/job_results.json"
                    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=results_key)
                    results = json.loads(response['Body'].read().decode('utf-8'))
                    
                    print(f"\n🎉 Job Results:")
                    print(f"  Status: {results.get('job_status', 'unknown')}")
                    print(f"  Files Processed: {results.get('files_processed', 0)}")
                    print(f"  Processing Time: {results.get('total_processing_time', 0):.1f}s")
                    print(f"  Average Compression: {results.get('average_compression_ratio', 1):.1f}x")
                    
                except Exception as e:
                    print(f"Could not read job results: {e}")
            else:
                print("No output files found!")
                
        except Exception as e:
            print(f"Error checking outputs: {e}")
        
        # Cleanup local script
        if os.path.exists(script_file):
            os.remove(script_file)
        
        return True
        
    except Exception as e:
        print(f"\nProcessing job failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")
        exit(1) 