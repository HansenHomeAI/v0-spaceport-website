#!/usr/bin/env python3
"""
Simple test script for gsplat container
Tests the existing container with your dataset
"""

import boto3
import time
from datetime import datetime

def test_gsplat_container():
    """Test the gsplat container with real dataset"""
    print("🎯 Testing gsplat container with real dataset")
    print("=" * 60)
    
    sagemaker = boto3.client('sagemaker', region_name='us-west-2')
    
    job_name = f"gsplat-test-{int(time.time())}"
    
    # Use the correct SageMaker execution role
    role_arn = 'arn:aws:iam::975050048887:role/SpaceportMLPipelineStack-SageMakerExecutionRole7843-A4BBnjJAXLs8'
    
    print(f"🎮 Creating test job: {job_name}")
    print(f"📦 Container: 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest")
    print(f"📂 Dataset: s3://spaceport-uploads/1748664812459-5woqcu-Archive.zip")
    print(f"💪 Instance: ml.g4dn.xlarge (NVIDIA T4 GPU)")
    
    training_job_config = {
        'TrainingJobName': job_name,
        'RoleArn': role_arn,
        'AlgorithmSpecification': {
            'TrainingImage': '975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest',
            'TrainingInputMode': 'File'
        },
        'InputDataConfig': [{
            'ChannelName': 'training',
            'DataSource': {
                'S3DataSource': {
                    'S3DataType': 'S3Prefix',
                    'S3Uri': 's3://spaceport-uploads/1748664812459-5woqcu-Archive.zip',
                    'S3DataDistributionType': 'FullyReplicated'
                }
            }
        }],
        'OutputDataConfig': {
            'S3OutputPath': 's3://spaceport-sagemaker-us-west-2/gsplat-test-output/'
        },
        'ResourceConfig': {
            'InstanceType': 'ml.g4dn.xlarge',  # GPU instance for real test
            'InstanceCount': 1,
            'VolumeSizeInGB': 50
        },
        'StoppingCondition': {
            'MaxRuntimeInSeconds': 1800  # 30 minutes max
        },
        'Environment': {
            'GSPLAT_TEST': 'true',
            'DATASET_PATH': '/opt/ml/input/data/training'
        }
    }
    
    try:
        print("🚀 Starting test job...")
        response = sagemaker.create_training_job(**training_job_config)
        print(f"✅ Test job created successfully!")
        print(f"📋 Job ARN: {response['TrainingJobArn']}")
        
        print("\n⏳ Monitoring job progress...")
        
        # Monitor job status
        for i in range(20):  # Check for up to 20 minutes
            try:
                job_description = sagemaker.describe_training_job(TrainingJobName=job_name)
                status = job_description['TrainingJobStatus']
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"   [{timestamp}] Status: {status}")
                
                if status == 'Completed':
                    print("\n🎉 SUCCESS! gsplat container test PASSED!")
                    print("✅ The container successfully:")
                    print("   - Started on GPU instance")
                    print("   - Loaded the dataset")
                    print("   - Ran gsplat code")
                    print("   - Completed without errors")
                    print("\n🎯 Container URI: 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest")
                    print("🏆 GOAL ACHIEVED: Production gsplat container is working!")
                    return True
                    
                elif status == 'Failed':
                    print(f"\n❌ Test FAILED!")
                    if 'FailureReason' in job_description:
                        print(f"   Reason: {job_description['FailureReason']}")
                    print("   This means we need to fix the container")
                    return False
                    
                elif status == 'Stopped':
                    print(f"\n⏹️  Test was stopped")
                    return False
                    
                elif status in ['InProgress', 'Starting']:
                    # Still running, wait more
                    time.sleep(60)  # Wait 1 minute between checks
                    continue
                else:
                    print(f"   Unknown status: {status}")
                    time.sleep(30)
                    
            except Exception as e:
                print(f"   Error checking status: {e}")
                time.sleep(30)
        
        print("\n⏰ Test monitoring timeout reached")
        print("   The test may still be running. Check manually:")
        print(f"   aws sagemaker describe-training-job --training-job-name {job_name}")
        return False
        
    except Exception as e:
        print(f"❌ Error creating test job: {e}")
        return False

if __name__ == "__main__":
    success = test_gsplat_container()
    
    if success:
        print("\n🚀 MISSION ACCOMPLISHED!")
        print("✅ We have a production-ready gsplat container working in AWS!")
    else:
        print("\n⚠️  Test failed - need to debug and fix the container")
        print("💡 Next steps:")
        print("   1. Check CloudWatch logs for the training job")
        print("   2. Debug container issues")
        print("   3. Rebuild container if needed") 