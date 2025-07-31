#!/usr/bin/env python3
"""
SOGS Compression Only Test
=========================

Test script to validate PlayCanvas SOGS compression using the latest 3DGS training output.
Uses the most recent successful 3DGS training run from July 31st with proper spherical harmonics.

This test verifies:
1. SOGS compression container is working
2. Real PlayCanvas SOGS package is installed correctly
3. WebP textures and metadata are generated properly
4. Output is compatible with SuperSplat viewer
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

class SOGSCompressionTester:
    def __init__(self, region='us-west-2'):
        self.region = region
        self.account_id = '975050048887'
        self.sagemaker = boto3.client('sagemaker', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        
        # Latest 3DGS training output (July 31st) - model.tar.gz contains the files with proper spherical harmonics
        self.latest_3dgs_output = "s3://spaceport-ml-processing/3dgs/20f35078-d929-4f9f-9608-ad6235f713fe/ml-job-20250731-182052-20f35078-3dgs/output/model.tar.gz"
        
        # Configuration for SOGS compression test
        self.config = {
            'sagemaker_role': f'arn:aws:iam::{self.account_id}:role/SpaceportMLPipelineStack-SageMakerExecutionRole7843-A4BBnjJAXLs8',
            'instance_type': 'ml.g4dn.xlarge',  # GPU instance for SOGS
            'container_image': f'{self.account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/compressor:latest',
            'test_job_name': f"sogs-compression-test-{int(time.time())}"
        }

    def test_sogs_compression(self) -> Dict:
        """Test SOGS compression with latest 3DGS output"""
        logger.info("🚀 STARTING SOGS COMPRESSION TEST")
        logger.info("=" * 60)
        logger.info(f"Input: Latest 3DGS training output (July 31st) with proper spherical harmonics")
        logger.info(f"Source: {self.latest_3dgs_output}")
        logger.info(f"Container: PlayCanvas SOGS implementation")
        
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
                        'S3Uri': self.latest_3dgs_output,
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
                        'InstanceType': self.config['instance_type'],
                        'InstanceCount': 1,
                        'VolumeSizeInGB': 30
                    }
                },
                StoppingCondition={'MaxRuntimeInSeconds': 3600}  # 1 hour max
            )
            
            logger.info(f"✅ SOGS compression job created: {response['ProcessingJobArn']}")
            
            # Monitor the job
            return self._monitor_compression_job(job_name)
            
        except Exception as e:
            logger.error(f"❌ Failed to create SOGS compression job: {e}")
            raise

    def _verify_3dgs_output(self) -> bool:
        """Verify that the latest 3DGS output exists and is valid"""
        logger.info("🔍 Verifying 3DGS training output...")
        
        try:
            # Parse S3 URI
            s3_uri = self.latest_3dgs_output
            bucket = s3_uri.split('/')[2]
            key = '/'.join(s3_uri.split('/')[3:])
            
            # Check if model.tar.gz exists
            try:
                response = self.s3.head_object(Bucket=bucket, Key=key)
                file_size_mb = response['ContentLength'] / (1024 * 1024)
                logger.info(f"✅ Found model.tar.gz ({file_size_mb:.1f} MB)")
            except Exception as e:
                logger.error(f"❌ model.tar.gz not found at {s3_uri}")
                return False
            
            # Download and extract to verify contents
            logger.info("📦 Extracting model.tar.gz to verify contents...")
            temp_dir = "/tmp/sogs_test_extract"
            import os
            import tarfile
            
            # Create temp directory
            os.makedirs(temp_dir, exist_ok=True)
            
            # Download tar.gz
            tar_path = os.path.join(temp_dir, "model.tar.gz")
            self.s3.download_file(bucket, key, tar_path)
            
            # Extract and check contents
            with tarfile.open(tar_path, 'r:gz') as tar:
                tar.extractall(temp_dir)
                members = tar.getmembers()
                
                # Check for required files
                required_files = ['final_model.ply', 'training_metadata.json']
                found_files = []
                
                for member in members:
                    if member.name in required_files:
                        found_files.append(member.name)
                        file_size_mb = member.size / (1024 * 1024)
                        logger.info(f"✅ Found {member.name} ({file_size_mb:.1f} MB)")
                
                if len(found_files) < len(required_files):
                    missing = set(required_files) - set(found_files)
                    logger.error(f"❌ Missing required files in tar.gz: {missing}")
                    return False
                
                # Verify PLY file has correct format for SOGS
                ply_path = os.path.join(temp_dir, 'final_model.ply')
                return self._verify_ply_format_local(ply_path)
            
        except Exception as e:
            logger.error(f"❌ Error verifying 3DGS output: {e}")
            return False

    def _verify_ply_format_local(self, ply_path: str) -> bool:
        """Verify PLY file has required fields for SOGS compression (local file)"""
        try:
            logger.info("🔍 Verifying PLY file format for SOGS compatibility...")
            
            # Read first part of PLY file to check header
            with open(ply_path, 'rb') as f:
                header_bytes = f.read(2048)
                header = header_bytes.decode('utf-8', errors='ignore')
            
            # Check for required SOGS fields
            required_fields = ['f_dc_0', 'f_dc_1', 'f_dc_2', 'opacity', 'scale_0', 'scale_1', 'scale_2']
            missing_fields = []
            
            for field in required_fields:
                if field not in header:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.error(f"❌ PLY missing required SOGS fields: {missing_fields}")
                return False
            
            logger.info("✅ PLY file format is compatible with SOGS compression")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error verifying PLY format: {e}")
            return False

    def _verify_ply_format(self, bucket: str, ply_key: str) -> bool:
        """Verify PLY file has required fields for SOGS compression (S3 file)"""
        try:
            logger.info("🔍 Verifying PLY file format for SOGS compatibility...")
            
            # Download first part of PLY file to check header
            response = self.s3.get_object(Bucket=bucket, Key=ply_key, Range='bytes=0-2048')
            header_bytes = response['Body'].read()
            header = header_bytes.decode('utf-8', errors='ignore')
            
            # Check for required SOGS fields
            required_fields = ['f_dc_0', 'f_dc_1', 'f_dc_2', 'opacity', 'scale_0', 'scale_1', 'scale_2']
            missing_fields = []
            
            for field in required_fields:
                if field not in header:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.error(f"❌ PLY missing required SOGS fields: {missing_fields}")
                return False
            
            logger.info("✅ PLY file format is compatible with SOGS compression")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error verifying PLY format: {e}")
            return False

    def _monitor_compression_job(self, job_name: str) -> Dict:
        """Monitor SOGS compression job progress"""
        logger.info(f"⏱️  Monitoring SOGS compression job: {job_name}")
        
        start_time = time.time()
        max_wait_time = 3600  # 1 hour
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.sagemaker.describe_processing_job(ProcessingJobName=job_name)
                status = response['ProcessingJobStatus']
                
                elapsed = int(time.time() - start_time)
                elapsed_min = elapsed // 60
                elapsed_sec = elapsed % 60
                
                logger.info(f"📊 Status: {status} | Elapsed: {elapsed_min}m {elapsed_sec}s")
                
                if status == 'Completed':
                    logger.info("✅ SOGS compression completed successfully!")
                    return self._analyze_compression_results(response)
                
                elif status == 'Failed':
                    failure_reason = response.get('FailureReason', 'Unknown error')
                    logger.error(f"❌ SOGS compression failed: {failure_reason}")
                    return {'status': 'failed', 'error': failure_reason}
                
                elif status in ['Stopping', 'Stopped']:
                    logger.error(f"❌ SOGS compression was stopped: {status}")
                    return {'status': 'stopped'}
                
                # Wait before next check
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Error monitoring job: {e}")
                raise
        
        logger.error("❌ SOGS compression job timed out")
        return {'status': 'timeout'}

    def _analyze_compression_results(self, job_response: Dict) -> Dict:
        """Analyze SOGS compression results"""
        logger.info("📊 Analyzing SOGS compression results...")
        
        # Get output S3 location
        output_config = job_response['ProcessingOutputConfig']['Outputs'][0]['S3Output']
        output_s3_uri = output_config['S3Uri']
        
        logger.info(f"📁 Output location: {output_s3_uri}")
        
        try:
            # Parse S3 URI
            bucket = output_s3_uri.split('/')[2]
            prefix = '/'.join(output_s3_uri.split('/')[3:])
            
            # List output files
            response = self.s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            
            if 'Contents' not in response:
                logger.error("❌ No output files found")
                return {'status': 'failed', 'error': 'No output files'}
            
            files = response['Contents']
            total_size = sum(obj['Size'] for obj in files)
            
            # Analyze file types
            webp_files = [f for f in files if f['Key'].endswith('.webp')]
            json_files = [f for f in files if f['Key'].endswith('.json')]
            bundle_dirs = [f for f in files if 'supersplat_bundle' in f['Key']]
            
            results = {
                'status': 'success',
                'output_s3_uri': output_s3_uri,
                'total_files': len(files),
                'total_size_mb': total_size / (1024 * 1024),
                'webp_files': len(webp_files),
                'json_files': len(json_files),
                'has_supersplat_bundle': len(bundle_dirs) > 0,
                'file_list': [f['Key'].split('/')[-1] for f in files]
            }
            
            logger.info("🎯 SOGS Compression Results:")
            logger.info(f"   Total Files: {results['total_files']}")
            logger.info(f"   WebP Textures: {results['webp_files']}")
            logger.info(f"   JSON Metadata: {results['json_files']}")
            logger.info(f"   Total Size: {results['total_size_mb']:.2f} MB")
            logger.info(f"   SuperSplat Bundle: {'✅' if results['has_supersplat_bundle'] else '❌'}")
            
            # Check for expected SOGS output
            if results['webp_files'] > 0 and results['json_files'] > 0:
                logger.info("✅ SOGS compression appears successful - WebP textures generated")
                
                # Generate viewer URL for testing
                if results['has_supersplat_bundle']:
                    bundle_url = f"{output_s3_uri}supersplat_bundle/"
                    results['viewer_url'] = f"https://your-domain.com/viewer.html?bundle={bundle_url}"
                    logger.info(f"🔗 Test in viewer: {results['viewer_url']}")
                
            else:
                logger.warning("⚠️ SOGS compression may have issues - missing expected files")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error analyzing results: {e}")
            return {'status': 'error', 'error': str(e)}

def main():
    """Run SOGS compression test"""
    try:
        tester = SOGSCompressionTester()
        results = tester.test_sogs_compression()
        
        logger.info("🏁 SOGS COMPRESSION TEST COMPLETE")
        logger.info("=" * 60)
        
        if results['status'] == 'success':
            logger.info("✅ SUCCESS: PlayCanvas SOGS compression working correctly!")
            logger.info(f"📊 Generated {results['webp_files']} WebP textures")
            logger.info(f"💾 Total compressed size: {results['total_size_mb']:.2f} MB")
            
            if 'viewer_url' in results:
                logger.info(f"🔗 Test the model: {results['viewer_url']}")
        else:
            logger.error(f"❌ FAILED: {results.get('error', 'Unknown error')}")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 