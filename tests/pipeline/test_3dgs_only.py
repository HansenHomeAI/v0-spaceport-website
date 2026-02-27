#!/usr/bin/env python3
"""
Test 3DGS Training Step Only
Using existing SfM output from successful GPS-enhanced pipeline run
"""

import boto3
import json
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_3dgs_only():
    """Test only the 3DGS training step using existing SfM output"""
    
    # Use existing SfM output from successful run
    existing_colmap_s3_uri = "s3://spaceport-ml-processing/colmap/ff77d14d-92f2-4cc1-8288-ef705f04a6cf/"
    
    # Generate new job ID for this 3DGS test
    job_id = f"3dgs-test-{int(time.time())}"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    job_name = f"ml-job-{timestamp}-{job_id[:8]}"
    
    logger.info("🧪 Starting 3DGS-Only Test")
    logger.info(f"📍 Using existing SfM output: {existing_colmap_s3_uri}")
    logger.info(f"🆔 New job ID: {job_id}")
    
    # Create SageMaker client
    sagemaker = boto3.client('sagemaker', region_name='us-west-2')
    
    # Define training job parameters
    training_job_name = f"{job_name}-3dgs"
    
    training_params = {
        'TrainingJobName': training_job_name,
        'AlgorithmSpecification': {
            'TrainingImage': '975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest',
            'TrainingInputMode': 'File'
        },
        'RoleArn': 'arn:aws:iam::975050048887:role/Spaceport-SageMaker-Role-staging',
        'InputDataConfig': [
            {
                'ChannelName': 'training',
                'DataSource': {
                    'S3DataSource': {
                        'S3DataType': 'S3Prefix',
                        'S3Uri': existing_colmap_s3_uri,
                        'S3DataDistributionType': 'FullyReplicated'
                    }
                },
                'CompressionType': 'None',
                'RecordWrapperType': 'None'
            }
        ],
        'OutputDataConfig': {
            'S3OutputPath': f's3://spaceport-ml-processing/3dgs/{job_id}/'
        },
        'ResourceConfig': {
            'InstanceType': 'ml.g5.2xlarge',  # Upgraded to handle Vincent Woo's full methodology
            'InstanceCount': 1,
            'VolumeSizeInGB': 100
        },
        'StoppingCondition': {
            'MaxRuntimeInSeconds': 7200  # 2 hours
        },
        'Environment': {
            'AWS_DEFAULT_REGION': 'us-west-2',
            'PYTHONUNBUFFERED': '1',
            'SAGEMAKER_PROGRAM': 'train.py',
            'TORCH_CUDA_ARCH_LIST': '8.0 8.6',
            'CUDA_HOME': '/usr/local/cuda',
            'LD_LIBRARY_PATH': '/usr/local/cuda/lib64:/usr/local/cuda/lib',
            'LIBRARY_PATH': '/usr/local/cuda/lib64:/usr/local/cuda/lib',
            
            # Vincent Woo's methodology parameters
            'MAX_ITERATIONS': '30000',
            'TARGET_PSNR': '35.0',
            'MODEL_VARIANT': 'splatfacto-big',
            'SH_DEGREE': '3',
            'BILATERAL_PROCESSING': 'true',
            'LOG_INTERVAL': '100',
            'FRAMEWORK': 'nerfstudio',
            'METHODOLOGY': 'vincent_woo_sutro_tower',
            'LICENSE': 'apache_2_0',
            'COMMERCIAL_LICENSE': 'true',
            'OUTPUT_FORMAT': 'ply',
            'SOGS_COMPATIBLE': 'true',
            'MAX_NUM_GAUSSIANS': '1500000',
            'MEMORY_OPTIMIZATION': 'true'
        }
    }
    
    logger.info("🚀 Starting 3DGS training job...")
    logger.info(f"   Job name: {training_job_name}")
    logger.info(f"   Input: {existing_colmap_s3_uri}")
    logger.info(f"   Output: s3://spaceport-ml-processing/3dgs/{job_id}/")
    logger.info(f"   Instance: ml.g5.2xlarge (A10G GPU with 32GB RAM)")
    
    # Start the training job
    response = sagemaker.create_training_job(**training_params)
    
    logger.info(f"✅ Training job started successfully!")
    logger.info(f"   Training job ARN: {response['TrainingJobArn']}")
    
    # Monitor the job
    logger.info("⏳ Monitoring training job progress...")
    
    while True:
        time.sleep(30)  # Check every 30 seconds
        
        status = sagemaker.describe_training_job(TrainingJobName=training_job_name)
        current_status = status['TrainingJobStatus']
        
        if current_status == 'InProgress':
            secondary_status = status.get('SecondaryStatus', 'Unknown')
            logger.info(f"⏲️  Status: {current_status} - {secondary_status}")
            
        elif current_status == 'Completed':
            logger.info("🎉 3DGS training completed successfully!")
            logger.info(f"   Training time: {status.get('TrainingTimeInSeconds', 0)} seconds")
            logger.info(f"   Billable time: {status.get('BillableTimeInSeconds', 0)} seconds")
            logger.info(f"   Model artifacts: {status['ModelArtifacts']['S3ModelArtifacts']}")
            break
            
        elif current_status == 'Failed':
            logger.error("❌ 3DGS training failed!")
            logger.error(f"   Failure reason: {status.get('FailureReason', 'Unknown')}")
            break
            
        elif current_status == 'Stopped':
            logger.warning("⏹️ 3DGS training was stopped")
            break
    
    return current_status == 'Completed'

if __name__ == "__main__":
    success = test_3dgs_only()
    if success:
        print("✅ 3DGS test completed successfully!")
    else:
        print("❌ 3DGS test failed")
        exit(1)
