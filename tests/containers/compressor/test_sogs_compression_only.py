#!/usr/bin/env python3
"""
Test Real PlayCanvas SOGS Compression Container
Tests ONLY the compression step with existing 3DGS output
"""

import boto3
import logging
import time
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sogs_compression():
    """Test the real PlayCanvas SOGS compression container"""
    
    print("🎯 Testing Real PlayCanvas SOGS Compression Container")
    print("=" * 60)
    
    # Initialize SageMaker client
    sagemaker = boto3.client('sagemaker')
    
    # Test configuration
    job_name = f"test-sogs-compression-{int(time.time())}"
    
    # Use existing 3DGS output as input for compression test
    input_s3_path = "s3://spaceport-ml-data/jobs/prod-validation-1750974917/3dgs/"
    output_s3_path = f"s3://spaceport-ml-data/test-compression/{job_name}/"
    
    print(f"📋 Test Configuration:")
    print(f"   Job Name: {job_name}")
    print(f"   Input: {input_s3_path}")
    print(f"   Output: {output_s3_path}")
    print(f"   Container: spaceport/compressor:latest")
    print()
    
    # Processing job configuration
    processing_job_config = {
        'ProcessingJobName': job_name,
        'ProcessingResources': {
            'ClusterConfig': {
                'InstanceType': 'ml.g4dn.xlarge',  # GPU instance for SOGS
                'InstanceCount': 1,
                'VolumeSizeInGB': 30
            }
        },
        'AppSpecification': {
            'ImageUri': '975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor:latest',
            'ContainerEntrypoint': ['python3', '/opt/ml/code/compress.py']
        },
        'ProcessingInputs': [
            {
                'InputName': 'input',
                'S3Input': {
                    'S3Uri': input_s3_path,
                    'LocalPath': '/opt/ml/processing/input',
                    'S3DataType': 'S3Prefix',
                    'S3InputMode': 'File'
                }
            }
        ],
        'ProcessingOutputConfig': {
            'Outputs': [
                {
                    'OutputName': 'output',
                    'S3Output': {
                        'S3Uri': output_s3_path,
                        'LocalPath': '/opt/ml/processing/output',
                        'S3UploadMode': 'EndOfJob'
                    }
                }
            ]
        },
        'RoleArn': 'arn:aws:iam::975050048887:role/SageMakerExecutionRole'
    }
    
    try:
        # Start the compression job
        logger.info("🚀 Starting PlayCanvas SOGS compression test...")
        response = sagemaker.create_processing_job(**processing_job_config)
        
        print(f"✅ Compression job started successfully!")
        print(f"📋 Job ARN: {response['ProcessingJobArn']}")
        print()
        
        # Monitor the job
        print("⏱️  Monitoring SOGS Compression Job")
        print("=" * 40)
        
        start_time = time.time()
        
        while True:
            # Get job status
            job_desc = sagemaker.describe_processing_job(ProcessingJobName=job_name)
            status = job_desc['ProcessingJobStatus']
            
            elapsed_minutes = (time.time() - start_time) / 60
            print(f"📊 [{elapsed_minutes:5.1f}m] Status: {status}")
            
            if status in ['Completed', 'Failed', 'Stopped']:
                break
            
            time.sleep(30)
        
        # Final status
        final_elapsed = (time.time() - start_time) / 60
        print(f"\n🏁 COMPRESSION JOB COMPLETED: {status}")
        print(f"⏱️  Total Duration: {final_elapsed:.1f} minutes")
        print()
        
        if status == 'Completed':
            # Validate SOGS output
            print("🔍 Validating PlayCanvas SOGS Output")
            print("=" * 40)
            
            s3_client = boto3.client('s3')
            bucket = 'spaceport-ml-data'
            prefix = f"test-compression/{job_name}/"
            
            # List output files
            response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            
            if 'Contents' in response:
                output_files = []
                total_size = 0
                webp_files = 0
                metadata_files = 0
                
                for obj in response['Contents']:
                    file_name = obj['Key'].replace(prefix, '')
                    file_size = obj['Size']
                    output_files.append((file_name, file_size))
                    total_size += file_size
                    
                    if file_name.endswith('.webp'):
                        webp_files += 1
                    elif file_name.endswith('.json'):
                        metadata_files += 1
                
                print(f"📁 Found {len(output_files)} output files:")
                for file_name, file_size in output_files[:10]:  # Show first 10
                    size_mb = file_size / (1024 * 1024)
                    print(f"   - {file_name} ({size_mb:.2f} MB)")
                
                if len(output_files) > 10:
                    print(f"   ... and {len(output_files) - 10} more files")
                
                print()
                print(f"📊 SOGS Output Analysis:")
                print(f"   Total Files: {len(output_files)}")
                print(f"   WebP Images: {webp_files}")
                print(f"   Metadata Files: {metadata_files}")
                print(f"   Total Size: {total_size / (1024 * 1024):.2f} MB")
                print()
                
                # Validate SOGS format
                sogs_valid = True
                validation_issues = []
                
                if webp_files == 0:
                    sogs_valid = False
                    validation_issues.append("No WebP images found (required for SOGS)")
                
                if metadata_files == 0:
                    sogs_valid = False
                    validation_issues.append("No metadata.json files found (required for SOGS)")
                
                # Check for compression summary
                compression_summary_found = any('compression_summary.json' in f[0] for f in output_files)
                if not compression_summary_found:
                    validation_issues.append("No compression_summary.json found")
                
                if sogs_valid:
                    print("✅ SOGS FORMAT VALIDATION: PASSED")
                    print("   - WebP images present ✓")
                    print("   - Metadata files present ✓")
                    print("   - Real PlayCanvas SOGS format confirmed ✓")
                else:
                    print("❌ SOGS FORMAT VALIDATION: FAILED")
                    for issue in validation_issues:
                        print(f"   - {issue}")
                
                print()
                
                # Overall assessment
                print("=" * 60)
                print("🎯 PLAYCANVAS SOGS COMPRESSION TEST REPORT")
                print("=" * 60)
                
                if status == 'Completed' and sogs_valid:
                    print("✅ SUCCESS: Real PlayCanvas SOGS compression working!")
                    print(f"📊 Performance: {final_elapsed:.1f} minutes")
                    print(f"📁 Output: {len(output_files)} files, {webp_files} WebP images")
                    print("🎯 Ready for production use")
                else:
                    print("❌ ISSUES IDENTIFIED:")
                    if status != 'Completed':
                        print(f"   - Job failed with status: {status}")
                    for issue in validation_issues:
                        print(f"   - {issue}")
                
                return status == 'Completed' and sogs_valid
                
            else:
                print("❌ No output files found")
                return False
        
        else:
            print(f"❌ Job failed with status: {status}")
            
            # Get failure reason if available
            if 'FailureReason' in job_desc:
                print(f"💥 Failure Reason: {job_desc['FailureReason']}")
            
            return False
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_sogs_compression()
    exit(0 if success else 1) 