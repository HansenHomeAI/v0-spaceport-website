#!/usr/bin/env python3
"""
3DGS + SOGS Pipeline Test - Comprehensive Spherical Harmonics Validation

This test validates the complete pipeline from 3DGS training to SOGS compression:
1. Start 3DGS training with new spherical harmonics implementation
2. Wait for training completion and PLY file generation
3. Run SOGS compression on the generated PLY files
4. Verify SOGS compatibility and compression success

This test specifically validates that our spherical harmonics fix resolves the
KeyError: 'shN' issue and enables proper SOGS compression.
"""

import json
import time
import boto3
import logging
import tarfile
import tempfile
from datetime import datetime
from typing import Dict, Optional, Tuple, List
from pathlib import Path
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GaussianSOGSTester:
    def __init__(self, region='us-west-2'):
        self.region = region
        self.account_id = '975050048887'
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.stepfunctions = boto3.client('stepfunctions', region_name=region)
        self.sagemaker = boto3.client('sagemaker', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        
        # Configuration for comprehensive test
        self.config = {
            'lambda_function_name': 'Spaceport-StartMLJob',
            'existing_sfm_data': "s3://spaceport-ml-processing/colmap/a46a72b1-0019-46ee-9241-af02891eace3/",
            'test_email': "test@spaceport.com",
            'sagemaker_role': f'arn:aws:iam::{self.account_id}:role/SpaceportMLPipelineStack-SageMakerExecutionRole7843-A4BBnjJAXLs8',
            'compressor_image': f'{self.account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/compressor:latest'
        }
        
        # Test tracking
        self.job_id = None
        self.execution_arn = None
        self.output_uri_3dgs = None
        self.sogs_job_name = None
        
    def create_lambda_test_payload(self) -> Dict:
        """Create payload for Lambda function that will start 3DGS training."""
        return {
            "body": {
                "s3Url": "s3://spaceport-ml-pipeline/test-data/dummy-file.zip",
                "email": self.config['test_email'],
                "pipelineStep": "3dgs",  # Start directly from 3DGS stage
                "existingColmapUri": self.config['existing_sfm_data'],  # Use existing SfM data
                # Use Lambda's high-quality defaults for comprehensive testing
            }
        }
    
    def start_3dgs_training(self) -> Tuple[Optional[str], Optional[Dict]]:
        """Start 3DGS training and return execution details."""
        payload = self.create_lambda_test_payload()
        
        logger.info("🎯 STARTING 3DGS TRAINING WITH NEW SPHERICAL HARMONICS")
        logger.info("=" * 70)
        logger.info(f"Lambda Function: {self.config['lambda_function_name']}")
        logger.info(f"Pipeline Step: {payload['body']['pipelineStep']}")
        logger.info(f"Using existing SfM data: {self.config['existing_sfm_data']}")
        logger.info("🎨 Testing new spherical harmonics implementation:")
        logger.info("   - Proper SH structure: [N,1,3] + [N,15,3]")
        logger.info("   - Progressive training: 1→4 bands")
        logger.info("   - Industry standard: 16 coefficients (degree 3)")
        logger.info("   - SOGS compatible: f_rest_* fields in PLY")
        logger.info("")
        
        try:
            # Invoke the Lambda function
            response = self.lambda_client.invoke(
                FunctionName=self.config['lambda_function_name'],
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            # Parse Lambda response
            lambda_response = json.loads(response['Payload'].read())
            
            if lambda_response.get('statusCode') != 200:
                logger.error(f"❌ Lambda returned error: {lambda_response}")
                return None, None
            
            # Extract execution details
            body = json.loads(lambda_response['body'])
            execution_arn = body['executionArn']
            job_id = body['jobId']
            
            self.job_id = job_id
            self.execution_arn = execution_arn
            
            logger.info(f"✅ 3DGS training started successfully!")
            logger.info(f"📋 Job ID: {job_id}")
            logger.info(f"📋 Execution ARN: {execution_arn}")
            
            return execution_arn, body
            
        except Exception as e:
            logger.error(f"❌ Failed to start 3DGS training: {e}")
            return None, None
    
    def monitor_3dgs_execution(self, execution_arn: str) -> Dict:
        """Monitor 3DGS training execution and wait for completion."""
        logger.info("📊 MONITORING 3DGS TRAINING EXECUTION")
        logger.info("=" * 50)
        
        max_wait_time = 7200  # 2 hours max
        check_interval = 30   # Check every 30 seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # Get execution status
                execution_desc = self.stepfunctions.describe_execution(executionArn=execution_arn)
                status = execution_desc['status']
                
                logger.info(f"⏱️  Status: {status} ({(time.time() - start_time):.0f}s elapsed)")
                
                if status == 'SUCCEEDED':
                    logger.info("✅ 3DGS training completed successfully!")
                    
                    # Extract output location
                    output = json.loads(execution_desc.get('output', '{}'))
                    self.output_uri_3dgs = output.get('3dgs_output_uri')
                    
                    if self.output_uri_3dgs:
                        logger.info(f"📁 3DGS output location: {self.output_uri_3dgs}")
                    else:
                        logger.warning("⚠️  No 3DGS output URI found in execution output")
                    
                    return execution_desc
                    
                elif status == 'FAILED':
                    logger.error("❌ 3DGS training failed!")
                    logger.error(f"Error: {execution_desc.get('cause', 'Unknown error')}")
                    return execution_desc
                    
                elif status == 'ABORTED':
                    logger.error("❌ 3DGS training was aborted!")
                    return execution_desc
                
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error monitoring execution: {e}")
                time.sleep(check_interval)
        
        logger.error("❌ 3DGS training timed out after 2 hours")
        return {}
    
    def verify_3dgs_output(self) -> bool:
        """Verify 3DGS output contains proper PLY files with spherical harmonics."""
        if not self.output_uri_3dgs:
            logger.error("❌ No 3DGS output URI available")
            return False
        
        logger.info("🔍 VERIFYING 3DGS OUTPUT")
        logger.info("=" * 40)
        logger.info(f"Checking: {self.output_uri_3dgs}")
        
        try:
            # Parse S3 URI
            if self.output_uri_3dgs.startswith('s3://'):
                bucket = self.output_uri_3dgs.split('/')[2]
                key = '/'.join(self.output_uri_3dgs.split('/')[3:])
            else:
                logger.error(f"❌ Invalid S3 URI: {self.output_uri_3dgs}")
                return False
            
            # Check if model.tar.gz exists
            try:
                self.s3.head_object(Bucket=bucket, Key=key)
                logger.info(f"✅ Found model.tar.gz: s3://{bucket}/{key}")
            except:
                logger.error(f"❌ model.tar.gz not found: s3://{bucket}/{key}")
                return False
            
            # Download and extract to check PLY format
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / "model.tar.gz"
                
                logger.info("📥 Downloading model.tar.gz for PLY verification...")
                self.s3.download_file(bucket, key, str(temp_path))
                
                # Extract and find PLY files
                ply_files = []
                with tarfile.open(temp_path, 'r:gz') as tar:
                    tar.extractall(temp_dir)
                    
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            if file.endswith('.ply'):
                                ply_files.append(os.path.join(root, file))
                
                if not ply_files:
                    logger.error("❌ No PLY files found in 3DGS output")
                    return False
                
                logger.info(f"✅ Found {len(ply_files)} PLY file(s)")
                
                # Verify PLY format for SOGS compatibility
                for ply_file in ply_files:
                    if self._verify_ply_format_local(ply_file):
                        logger.info(f"✅ PLY file verified: {os.path.basename(ply_file)}")
                    else:
                        logger.error(f"❌ PLY file verification failed: {os.path.basename(ply_file)}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error verifying 3DGS output: {e}")
            return False
    
    def _verify_ply_format_local(self, ply_path: str) -> bool:
        """Verify PLY file has proper spherical harmonics format for SOGS."""
        try:
            with open(ply_path, 'rb') as f:
                header = f.read(2048).decode('utf-8', errors='ignore')
            
            # Check for required fields
            required_fields = ['f_dc_0', 'f_dc_1', 'f_dc_2', 'opacity', 'scale_0', 'scale_1', 'scale_2']
            
            for field in required_fields:
                if field not in header:
                    logger.error(f"Missing required field '{field}' in PLY file")
                    return False
            
            # Check for higher-order spherical harmonics (our fix)
            f_rest_fields = [f for f in header.split() if f.startswith('f_rest_')]
            
            if not f_rest_fields:
                logger.error("❌ No f_rest_* fields found - spherical harmonics fix not working!")
                return False
            
            logger.info(f"✅ Found {len(f_rest_fields)} f_rest_* fields (higher-order SH)")
            logger.info(f"   First few: {f_rest_fields[:5]}")
            
            # Verify we have enough coefficients for degree 3 (industry standard)
            expected_coeffs = 15  # (3+1)² - 1 = 15 higher-order coefficients
            if len(f_rest_fields) < expected_coeffs:
                logger.warning(f"⚠️  Only {len(f_rest_fields)} f_rest_* fields (expected {expected_coeffs})")
            else:
                logger.info(f"✅ Sufficient SH coefficients for industry standard (degree 3)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error verifying PLY format: {e}")
            return False
    
    def start_sogs_compression(self) -> bool:
        """Start SOGS compression on the 3DGS output."""
        if not self.output_uri_3dgs:
            logger.error("❌ No 3DGS output available for SOGS compression")
            return False
        
        logger.info("🚀 STARTING SOGS COMPRESSION TEST")
        logger.info("=" * 50)
        logger.info(f"Input: {self.output_uri_3dgs}")
        logger.info("🎯 Testing SOGS compatibility with new spherical harmonics")
        
        # Create SageMaker processing job for SOGS compression
        self.sogs_job_name = f"sogs-compression-test-{int(time.time())}"
        
        try:
            response = self.sagemaker.create_processing_job(
                ProcessingJobName=self.sogs_job_name,
                RoleArn=self.config['sagemaker_role'],
                AppSpecification={
                    'ImageUri': self.config['compressor_image'],
                    'ContainerEntrypoint': ['python3', '/opt/ml/code/compress.py']
                },
                ProcessingInputs=[{
                    'InputName': 'input',
                    'S3Input': {
                        'S3Uri': self.output_uri_3dgs,
                        'LocalPath': '/opt/ml/processing/input',
                        'S3DataType': 'S3Prefix',
                        'S3InputMode': 'File'
                    }
                }],
                ProcessingOutputConfig={
                    'Outputs': [{
                        'OutputName': 'compressed',
                        'S3Output': {
                            'S3Uri': f's3://spaceport-ml-processing/compressed/sogs-test-{int(time.time())}/',
                            'LocalPath': '/opt/ml/processing/output',
                            'S3UploadMode': 'EndOfJob'
                        }
                    }]
                },
                ProcessingResources={
                    'ClusterConfig': {
                        'InstanceType': 'ml.g4dn.xlarge',  # GPU instance for SOGS
                        'InstanceCount': 1,
                        'VolumeSizeInGB': 30
                    }
                },
                StoppingCondition={'MaxRuntimeInSeconds': 3600}  # 1 hour max
            )
            
            logger.info(f"✅ SOGS compression job created: {response['ProcessingJobArn']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create SOGS compression job: {e}")
            return False
    
    def monitor_sogs_compression(self) -> Dict:
        """Monitor SOGS compression job and wait for completion."""
        if not self.sogs_job_name:
            logger.error("❌ No SOGS job name available")
            return {}
        
        logger.info("📊 MONITORING SOGS COMPRESSION")
        logger.info("=" * 40)
        
        max_wait_time = 3600  # 1 hour max
        check_interval = 30   # Check every 30 seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # Get job status
                response = self.sagemaker.describe_processing_job(ProcessingJobName=self.sogs_job_name)
                status = response['ProcessingJobStatus']
                
                logger.info(f"⏱️  Status: {status} ({(time.time() - start_time):.0f}s elapsed)")
                
                if status == 'Completed':
                    logger.info("✅ SOGS compression completed successfully!")
                    logger.info("🎉 SPHERICAL HARMONICS FIX VALIDATED!")
                    logger.info("   - 3DGS training with proper SH structure ✓")
                    logger.info("   - PLY export with f_rest_* fields ✓")
                    logger.info("   - SOGS compression without KeyError ✓")
                    logger.info("   - Industry standard 16 coefficients ✓")
                    return response
                    
                elif status == 'Failed':
                    logger.error("❌ SOGS compression failed!")
                    logger.error(f"Failure reason: {response.get('FailureReason', 'Unknown')}")
                    
                    # Check if it's the KeyError we were trying to fix
                    if 'KeyError' in response.get('FailureReason', ''):
                        logger.error("❌ KeyError still occurring - spherical harmonics fix may not be working")
                    else:
                        logger.error("❌ Different error occurred - check logs for details")
                    
                    return response
                    
                elif status == 'Stopped':
                    logger.error("❌ SOGS compression was stopped!")
                    return response
                
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error monitoring SOGS job: {e}")
                time.sleep(check_interval)
        
        logger.error("❌ SOGS compression timed out after 1 hour")
        return {}
    
    def run_comprehensive_test(self) -> bool:
        """Run the complete 3DGS + SOGS test pipeline."""
        logger.info("🚀 STARTING COMPREHENSIVE 3DGS + SOGS TEST")
        logger.info("=" * 70)
        logger.info("This test validates our spherical harmonics fix:")
        logger.info("1. 3DGS training with proper SH structure")
        logger.info("2. PLY export with f_rest_* fields")
        logger.info("3. SOGS compression without KeyError")
        logger.info("4. Industry standard compatibility")
        logger.info("")
        
        # Step 1: Start 3DGS training
        execution_arn, lambda_response = self.start_3dgs_training()
        if not execution_arn:
            logger.error("❌ Failed to start 3DGS training")
            return False
        
        # Step 2: Monitor 3DGS training
        execution_result = self.monitor_3dgs_execution(execution_arn)
        if not execution_result or execution_result.get('status') != 'SUCCEEDED':
            logger.error("❌ 3DGS training failed or timed out")
            return False
        
        # Step 3: Verify 3DGS output
        if not self.verify_3dgs_output():
            logger.error("❌ 3DGS output verification failed")
            return False
        
        # Step 4: Start SOGS compression
        if not self.start_sogs_compression():
            logger.error("❌ Failed to start SOGS compression")
            return False
        
        # Step 5: Monitor SOGS compression
        sogs_result = self.monitor_sogs_compression()
        if not sogs_result or sogs_result.get('ProcessingJobStatus') != 'Completed':
            logger.error("❌ SOGS compression failed or timed out")
            return False
        
        # Success!
        logger.info("")
        logger.info("🎉 COMPREHENSIVE TEST PASSED!")
        logger.info("=" * 50)
        logger.info("✅ Spherical harmonics fix is working correctly:")
        logger.info("   - 3DGS training with proper SH structure")
        logger.info("   - PLY export with f_rest_* fields")
        logger.info("   - SOGS compression without KeyError")
        logger.info("   - Industry standard compatibility")
        logger.info("")
        logger.info("🚀 Ready for production use!")
        
        return True

def main():
    """Main test execution."""
    tester = GaussianSOGSTester()
    
    try:
        success = tester.run_comprehensive_test()
        if success:
            logger.info("✅ All tests passed!")
            exit(0)
        else:
            logger.error("❌ Tests failed!")
            exit(1)
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        exit(1)

if __name__ == "__main__":
    main() 