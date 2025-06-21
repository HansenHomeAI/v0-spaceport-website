#!/usr/bin/env python3
"""
Simplified SageMaker Test for SOGS Compression
Uses the simplified compression script to avoid compatibility issues
"""

import boto3
import json
import time
from datetime import datetime
from sagemaker.processing import ScriptProcessor
from sagemaker import get_execution_role

# Configuration
REGION = 'us-west-2'
BUCKET_NAME = 'spaceport-sagemaker-us-west-2'  # Use existing bucket
INPUT_KEY = 'test-data/sample.ply'
OUTPUT_PREFIX = f'compression-output/test-{int(time.time())}'

# SageMaker configuration
INSTANCE_TYPE = 'ml.c6i.xlarge'  # Start with smaller instance for testing
INSTANCE_COUNT = 1
VOLUME_SIZE = 30

def upload_script_to_s3():
    """Upload the compression script to S3 for SageMaker to use"""
    s3_client = boto3.client('s3', region_name=REGION)
    
    script_key = f'scripts/compress_model_simple.py'
    script_s3_uri = f's3://{BUCKET_NAME}/{script_key}'
    
    try:
        s3_client.upload_file('compress_model_simple.py', BUCKET_NAME, script_key)
        print(f"Uploaded script to {script_s3_uri}")
        return script_s3_uri
    except Exception as e:
        print(f"Failed to upload script: {e}")
        return None

def main():
    print("=== SageMaker SOGS Compression Test (Simplified) ===")
    
    # Upload script to S3 first
    script_s3_uri = upload_script_to_s3()
    if not script_s3_uri:
        print("❌ Failed to upload script")
        return False
    
    # Initialize SageMaker session
    import sagemaker
    session = sagemaker.Session()
    
    try:
        role = get_execution_role()
        print(f"Using execution role: {role}")
    except:
        # Fallback role for testing
        role = f"arn:aws:iam::339713018962:role/SageMakerExecutionRole"
        print(f"Using fallback role: {role}")
    
    # Create ScriptProcessor with simpler parameters
    processor = ScriptProcessor(
        command=['python3'],
        image_uri='python:3.9-slim',  # Use simple Python image
        role=role,
        instance_type=INSTANCE_TYPE,
        instance_count=INSTANCE_COUNT,
        volume_size_in_gb=VOLUME_SIZE,
        max_runtime_in_seconds=3600,  # 1 hour timeout
        base_job_name='sogs-compression-simple',
        sagemaker_session=session
    )
    
    # Define input/output locations
    input_s3_uri = f's3://{BUCKET_NAME}/{INPUT_KEY}'
    output_s3_uri = f's3://{BUCKET_NAME}/{OUTPUT_PREFIX}/'
    
    print(f"Input: {input_s3_uri}")
    print(f"Output: {output_s3_uri}")
    print(f"Script: {script_s3_uri}")
    
    # Environment variables for the script
    env_vars = {
        'S3_INPUT_URL': input_s3_uri,
        'S3_OUTPUT_URL': output_s3_uri,
        'AWS_DEFAULT_REGION': REGION
    }
    
    try:
        print("\nStarting SageMaker processing job...")
        
        # Run the processing job with minimal parameters
        processor.run(
            code=script_s3_uri,  # Use S3 URI directly
            inputs=[
                sagemaker.processing.ProcessingInput(
                    source=input_s3_uri,
                    destination='/opt/ml/input/data/input',
                    input_name='input-data'
                )
            ],
            outputs=[
                sagemaker.processing.ProcessingOutput(
                    source='/opt/ml/output/data',
                    destination=output_s3_uri,
                    output_name='compressed-output'
                )
            ],
            wait=True,  # Wait for completion
            logs=True,  # Show logs
            environment=env_vars
        )
        
        print("\n=== Processing Job Completed Successfully! ===")
        
        # Check outputs
        s3_client = boto3.client('s3', region_name=REGION)
        
        print(f"\nChecking outputs in {output_s3_uri}...")
        try:
            response = s3_client.list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix=OUTPUT_PREFIX
            )
            
            if 'Contents' in response:
                print(f"Found {len(response['Contents'])} output files:")
                total_size = 0
                for obj in response['Contents']:
                    size = obj['Size']
                    total_size += size
                    print(f"  - {obj['Key']} ({size} bytes)")
                
                print(f"Total output size: {total_size} bytes")
                
                # Try to read job results
                try:
                    results_key = f"{OUTPUT_PREFIX}/job_results.json"
                    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=results_key)
                    results = json.loads(response['Body'].read().decode('utf-8'))
                    
                    print(f"\nJob Results:")
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
        
    except Exception as e:
        print(f"\nProcessing job failed: {e}")
        
        # Try to get job details for debugging
        try:
            job_name = processor.latest_job.job_name if hasattr(processor, 'latest_job') and processor.latest_job else None
            if job_name:
                print(f"Job name: {job_name}")
                
                # Get job description
                sm_client = boto3.client('sagemaker', region_name=REGION)
                response = sm_client.describe_processing_job(ProcessingJobName=job_name)
                
                print(f"Job status: {response.get('ProcessingJobStatus', 'unknown')}")
                if 'FailureReason' in response:
                    print(f"Failure reason: {response['FailureReason']}")
            else:
                print("No job name available for debugging")
                
        except Exception as debug_e:
            print(f"Could not get job details: {debug_e}")
        
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")
        exit(1) 