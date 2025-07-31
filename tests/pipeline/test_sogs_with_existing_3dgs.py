#!/usr/bin/env python3
"""
Simple SOGS Test with Existing 3DGS Output
==========================================

This test uses the existing 3DGS output from July 28th to test SOGS compression
without running new training. This will help us verify if SOGS compression works
with the current PLY format while we fix the gsplat rasterization issue.
"""

import json
import time
import boto3
import logging
from datetime import datetime
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleSOGSTester:
    def __init__(self, region='us-west-2'):
        self.region = region
        self.account_id = '975050048887'
        self.sagemaker = boto3.client('sagemaker', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        
        # Use existing 3DGS output from July 28th (before our SH fix)
        self.existing_3dgs_output = "s3://spaceport-ml-processing/3dgs/5740c423-e8a2-4930-a589-3e811427beef/ml-job-20250728-235313-5740c423-3dgs/output/model.tar.gz"
        
        # Configuration for SOGS compression test
        self.config = {
            'sagemaker_role': f'arn:aws:iam::{self.account_id}:role/SpaceportMLPipelineStack-SageMakerExecutionRole7843-A4BBnjJAXLs8',
            'instance_type': 'ml.g4dn.xlarge',  # GPU instance for SOGS
            'container_image': f'{self.account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/compressor:latest',
            'test_job_name': f"sogs-simple-test-{int(time.time())}"
        }

    def test_sogs_compression(self) -> Dict:
        """Test SOGS compression with existing 3DGS output"""
        logger.info("🚀 STARTING SIMPLE SOGS COMPRESSION TEST")
        logger.info("=" * 60)
        logger.info(f"Input: Existing 3DGS output (July 28th)")
        logger.info(f"Source: {self.existing_3dgs_output}")
        logger.info(f"Purpose: Test SOGS compression with current PLY format")
        logger.info("")
        logger.info("📋 This test will:")
        logger.info("   1. Use existing 3DGS output (before our SH fix)")
        logger.info("   2. Run SOGS compression to see current behavior")
        logger.info("   3. Verify if KeyError 'shN' still occurs")
        logger.info("   4. Help us understand the baseline before our fix")
        
        # Verify input exists
        if not self._verify_3dgs_output():
            raise RuntimeError("3DGS output not found or invalid")
        
        # Create SageMaker processing job for SOGS compression
        job_name = self.config['test_job_name']
        
        try:
            logger.info(f"🔧 Creating SOGS compression job: {job_name}")
            
            response = self.sagemaker.create_processing_job(
                ProcessingJobName=job_name,
                RoleArn=self.config['sagemaker_role'],
                AppSpecification={
                    'ImageUri': self.config['container_image'],
                    'ContainerEntrypoint': ['python3', '/opt/ml/code/compress.py']
                },
                ProcessingInputs=[{
                    'InputName': 'input',
                    'S3Input': {
                        'S3Uri': self.existing_3dgs_output,
                        'LocalPath': '/opt/ml/processing/input',
                        'S3DataType': 'S3Prefix',
                        'S3InputMode': 'File'
                    }
                }],
                ProcessingOutputConfig={
                    'Outputs': [{
                        'OutputName': 'compressed',
                        'S3Output': {
                            'S3Uri': f's3://spaceport-ml-processing/compressed/sogs-simple-test-{int(time.time())}/',
                            'LocalPath': '/opt/ml/processing/output',
                            'S3UploadMode': 'EndOfJob'
                        }
                    }]
                },
                ProcessingResources={
                    'ClusterConfig': {
                        'InstanceType': self.config['instance_type'],
                        'InstanceCount': 1,
                        'VolumeSizeInGB': 30
                    }
                },
                StoppingCondition={'MaxRuntimeInSeconds': 1800}  # 30 minutes max
            )
            
            logger.info(f"✅ SOGS compression job created: {response['ProcessingJobArn']}")
            
            # Monitor the job
            result = self._monitor_compression_job(job_name)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to create SOGS compression job: {e}")
            raise

    def _verify_3dgs_output(self) -> bool:
        """Verify that the 3DGS output exists and is accessible."""
        try:
            # Parse S3 URI
            if self.existing_3dgs_output.startswith('s3://'):
                bucket = self.existing_3dgs_output.split('/')[2]
                key = '/'.join(self.existing_3dgs_output.split('/')[3:])
            else:
                logger.error(f"❌ Invalid S3 URI: {self.existing_3dgs_output}")
                return False
            
            # Check if file exists
            try:
                self.s3.head_object(Bucket=bucket, Key=key)
                logger.info(f"✅ Found existing 3DGS output: s3://{bucket}/{key}")
                return True
            except:
                logger.error(f"❌ 3DGS output not found: s3://{bucket}/{key}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verifying 3DGS output: {e}")
            return False

    def _monitor_compression_job(self, job_name: str) -> Dict:
        """Monitor SOGS compression job and wait for completion."""
        logger.info("📊 MONITORING SOGS COMPRESSION JOB")
        logger.info("=" * 50)
        
        max_wait_time = 1800  # 30 minutes max
        check_interval = 30   # Check every 30 seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # Get job status
                response = self.sagemaker.describe_processing_job(ProcessingJobName=job_name)
                status = response['ProcessingJobStatus']
                
                logger.info(f"⏱️  Status: {status} ({(time.time() - start_time):.0f}s elapsed)")
                
                if status == 'Completed':
                    logger.info("✅ SOGS compression completed successfully!")
                    logger.info("📊 This means the current PLY format works with SOGS")
                    logger.info("📊 Our spherical harmonics fix may not be needed for SOGS compatibility")
                    return self._analyze_compression_results(response)
                    
                elif status == 'Failed':
                    logger.error("❌ SOGS compression failed!")
                    failure_reason = response.get('FailureReason', 'Unknown')
                    logger.error(f"Failure reason: {failure_reason}")
                    
                    # Check if it's the KeyError we were trying to fix
                    if 'KeyError' in failure_reason and 'shN' in failure_reason:
                        logger.error("❌ KeyError 'shN' confirmed - our spherical harmonics fix IS needed!")
                        logger.error("📊 This validates our approach to fix the SH structure")
                    else:
                        logger.error("❌ Different error occurred - check logs for details")
                    
                    return response
                    
                elif status == 'Stopped':
                    logger.error("❌ SOGS compression was stopped!")
                    return response
                
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error monitoring job: {e}")
                time.sleep(check_interval)
        
        logger.error("❌ SOGS compression timed out after 30 minutes")
        return {}

    def _analyze_compression_results(self, job_response: Dict) -> Dict:
        """Analyze the compression results."""
        logger.info("📊 ANALYZING COMPRESSION RESULTS")
        logger.info("=" * 40)
        
        try:
            # Get output location
            output_config = job_response.get('ProcessingOutputConfig', {})
            outputs = output_config.get('Outputs', [])
            
            if outputs:
                output_uri = outputs[0].get('S3Output', {}).get('S3Uri', '')
                logger.info(f"📁 Output location: {output_uri}")
                
                # Parse S3 URI
                if output_uri.startswith('s3://'):
                    bucket = output_uri.split('/')[2]
                    prefix = '/'.join(output_uri.split('/')[3:])
                    
                    # List output files
                    try:
                        response = self.s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
                        files = response.get('Contents', [])
                        
                        logger.info(f"📄 Generated {len(files)} output files:")
                        for file in files:
                            file_name = file['Key'].split('/')[-1]
                            file_size = file['Size']
                            logger.info(f"   - {file_name} ({file_size} bytes)")
                            
                            # Check for key files
                            if file_name.endswith('.webp'):
                                logger.info(f"     ✅ WebP texture file generated")
                            elif file_name == 'meta.json':
                                logger.info(f"     ✅ Metadata file generated")
                        
                        return {
                            'success': True,
                            'output_uri': output_uri,
                            'file_count': len(files),
                            'files': [f['Key'].split('/')[-1] for f in files]
                        }
                        
                    except Exception as e:
                        logger.error(f"❌ Error listing output files: {e}")
                        return {'success': False, 'error': str(e)}
            
            return {'success': False, 'error': 'No output files found'}
            
        except Exception as e:
            logger.error(f"❌ Error analyzing results: {e}")
            return {'success': False, 'error': str(e)}

    def run_test(self) -> bool:
        """Run the complete test."""
        logger.info("🚀 STARTING SIMPLE SOGS TEST")
        logger.info("=" * 50)
        logger.info("This test uses existing 3DGS output to verify SOGS compatibility")
        logger.info("before we fix the gsplat rasterization issue.")
        logger.info("")
        
        try:
            result = self.test_sogs_compression()
            
            if result.get('success'):
                logger.info("")
                logger.info("🎉 SIMPLE SOGS TEST PASSED!")
                logger.info("=" * 40)
                logger.info("✅ SOGS compression works with current PLY format")
                logger.info("📊 This suggests our spherical harmonics fix may not be needed")
                logger.info("📊 The issue might be with gsplat rasterization, not SOGS compatibility")
                return True
            else:
                logger.error("❌ SOGS compression failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Test execution failed: {e}")
            return False

def main():
    """Main test execution."""
    tester = SimpleSOGSTester()
    
    try:
        success = tester.run_test()
        if success:
            logger.info("✅ Simple SOGS test completed successfully!")
            exit(0)
        else:
            logger.error("❌ Simple SOGS test failed!")
            exit(1)
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        exit(1)

if __name__ == "__main__":
    main() 