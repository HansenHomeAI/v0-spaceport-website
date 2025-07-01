#!/usr/bin/env python3
"""
Simple SfM Debug Test
Runs just the SfM step to debug container issues
"""

import boto3
import time
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sfm_only():
    """Test just the SfM container to debug the issue"""
    
    logger.info("🔧 SfM Container Debug Test")
    logger.info("="*50)
    
    # Initialize SageMaker client
    sagemaker = boto3.client('sagemaker', region_name='us-west-2')
    
    # Test with a small, known-good dataset
    test_input = "s3://spaceport-uploads/1749575207099-4fanwl-Archive.zip"
    test_output = "s3://spaceport-ml-pipeline/debug-tests/sfm-debug/"
    
    job_name = f"sfm-debug-{int(time.time())}"
    
    logger.info(f"Job Name: {job_name}")
    logger.info(f"Input: {test_input}")
    logger.info(f"Output: {test_output}")
    
    # SfM processing job configuration
    processing_job_config = {
        'ProcessingJobName': job_name,
        'ProcessingInputs': [
            {
                'InputName': 'input-data',
                'AppManaged': False,
                'S3Input': {
                    'S3Uri': test_input,
                    'LocalPath': '/opt/ml/processing/input',
                    'S3DataType': 'S3Prefix',
                    'S3InputMode': 'File',
                    'S3DataDistributionType': 'FullyReplicated'
                }
            }
        ],
        'ProcessingOutputConfig': {
            'Outputs': [
                {
                    'OutputName': 'colmap-output',
                    'AppManaged': False,
                    'S3Output': {
                        'S3Uri': test_output,
                        'LocalPath': '/opt/ml/processing/output',
                        'S3UploadMode': 'EndOfJob'
                    }
                }
            ]
        },
        'ProcessingResources': {
            'ClusterConfig': {
                'InstanceCount': 1,
                'InstanceType': 'ml.c6i.2xlarge',  # Smaller instance for debugging
                'VolumeSizeInGB': 50
            }
        },
        'StoppingCondition': {
            'MaxRuntimeInSeconds': 3600  # 1 hour max
        },
        'AppSpecification': {
            'ImageUri': '975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:latest',
            'ContainerEntrypoint': ['/opt/ml/code/run_sfm.sh']
        },
        'RoleArn': 'arn:aws:iam::975050048887:role/SpaceportMLPipelineStack-SageMakerExecutionRole7843-A4BBnjJAXLs8'
    }
    
    try:
        # Start the job
        logger.info("🚀 Starting SfM debug job...")
        response = sagemaker.create_processing_job(**processing_job_config)
        logger.info(f"✅ Job started: {response['ProcessingJobArn']}")
        
        # Monitor the job
        while True:
            time.sleep(30)
            
            status_response = sagemaker.describe_processing_job(ProcessingJobName=job_name)
            status = status_response['ProcessingJobStatus']
            
            logger.info(f"Status: {status}")
            
            if status in ['Completed', 'Failed', 'Stopped']:
                break
        
        # Final status
        final_response = sagemaker.describe_processing_job(ProcessingJobName=job_name)
        logger.info(f"Final Status: {final_response['ProcessingJobStatus']}")
        
        if final_response['ProcessingJobStatus'] == 'Failed':
            logger.error(f"Failure Reason: {final_response.get('FailureReason', 'Unknown')}")
            return False
        else:
            logger.info("✅ SfM debug test completed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Debug test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_sfm_only()
    if success:
        print("🎉 SfM container is working correctly!")
    else:
        print("❌ SfM container has issues that need fixing.") 