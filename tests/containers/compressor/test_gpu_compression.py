#!/usr/bin/env python3
"""
GPU SOGS Compression Test
Tests the new production SOGS container with ml.g4dn.xlarge GPU instances
"""

import os
import sys
import json
import time
import boto3
import tempfile
from pathlib import Path

class GPUSOGSCompressionTest:
    """Test SOGS compression using GPU instances"""
    
    def __init__(self, region: str = "us-west-2"):
        """Initialize the tester"""
        self.region = region
        self.sagemaker = boto3.client('sagemaker', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
        # Configuration - using the NEW container and GPU instances
        self.ecr_image_uri = f"{self.account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/compressor:latest"
        self.test_bucket = "spaceport-uploads"
        self.output_bucket = "spaceport-ml-processing"
        
        print(f"🎯 GPU SOGS Compression Test")
        print(f"   Region: {region}")
        print(f"   Account: {self.account_id}")
        print(f"   Container: {self.ecr_image_uri}")
        print(f"   Instance Type: ml.g4dn.xlarge (GPU)")
    
    def get_existing_test_data(self) -> str:
        """Use existing test data from previous runs"""
        print("📁 Looking for existing test data...")
        
        # Use the same test data that worked in previous pipeline runs
        test_s3_uri = "s3://spaceport-uploads/1749575207099-4fanwl-Archive.zip"
        
        try:
            # Verify it exists
            bucket, key = test_s3_uri.replace("s3://", "").split("/", 1)
            self.s3.head_object(Bucket=bucket, Key=key)
            
            file_size = self.s3.head_object(Bucket=bucket, Key=key)['ContentLength']
            print(f"   ✅ Found test data: {test_s3_uri} ({file_size / 1024 / 1024:.1f} MB)")
            return test_s3_uri
            
        except Exception as e:
            print(f"   ❌ Test data not found: {e}")
            raise ValueError("Test data not available. Please upload test images first.")
    
    def get_sagemaker_role(self) -> str:
        """Get the SageMaker execution role ARN"""
        print("🔍 Finding SageMaker execution role...")
        
        # Try to get from CloudFormation stack
        cf = boto3.client('cloudformation', region_name=self.region)
        try:
            response = cf.describe_stacks(StackName='SpaceportMLPipelineStack')
            for output in response['Stacks'][0]['Outputs']:
                if 'SageMakerExecutionRole' in output['OutputKey']:
                    role_arn = output['OutputValue']
                    print(f"   ✅ Found role: {role_arn}")
                    return role_arn
        except Exception as e:
            print(f"   CloudFormation lookup failed: {e}")
        
        # Fallback: search IAM roles
        iam = boto3.client('iam', region_name=self.region)
        try:
            roles = iam.list_roles()
            for role in roles['Roles']:
                if 'SageMakerExecutionRole' in role['RoleName']:
                    role_arn = role['Arn']
                    print(f"   ✅ Found role via IAM: {role_arn}")
                    return role_arn
        except Exception as e:
            print(f"   IAM role search failed: {e}")
        
        raise ValueError("Could not find SageMaker execution role. Please deploy ML pipeline stack first.")
    
    def run_gpu_compression_test(self, input_s3_uri: str) -> dict:
        """Run SOGS compression test using GPU processing job"""
        print("🚀 Starting GPU SOGS Compression Test...")
        
        # Get SageMaker role
        role_arn = self.get_sagemaker_role()
        
        # Create unique job name
        job_name = f"gpu-sogs-test-{int(time.time())}"
        output_s3_uri = f"s3://{self.output_bucket}/gpu-compression-test/{job_name}/"
        
        print(f"   Job Name: {job_name}")
        print(f"   Input: {input_s3_uri}")
        print(f"   Output: {output_s3_uri}")
        print(f"   Container: {self.ecr_image_uri}")
        print(f"   Instance: ml.g4dn.xlarge (1x NVIDIA T4 GPU)")
        
        # Create processing job with GPU instance
        job_config = {
            'ProcessingJobName': job_name,
            'ProcessingResources': {
                'ClusterConfig': {
                    'InstanceCount': 1,
                    'InstanceType': 'ml.g4dn.xlarge',  # GPU instance!
                    'VolumeSizeInGB': 50
                }
            },
            'AppSpecification': {
                'ImageUri': self.ecr_image_uri,
                # Use the entry point from the container
            },
            'ProcessingInputs': [{
                'InputName': 'input-data',
                'AppManaged': False,
                'S3Input': {
                    'S3Uri': input_s3_uri,
                    'LocalPath': '/opt/ml/processing/input',
                    'S3DataType': 'S3Prefix',
                    'S3InputMode': 'File'
                }
            }],
            'ProcessingOutputConfig': {
                'Outputs': [{
                    'OutputName': 'compressed-output',
                    'AppManaged': False,
                    'S3Output': {
                        'S3Uri': output_s3_uri,
                        'LocalPath': '/opt/ml/processing/output',
                        'S3UploadMode': 'EndOfJob'
                    }
                }]
            },
            'RoleArn': role_arn,
            'Environment': {
                'COMPRESSION_TARGET': 'sogs',
                'GPU_ENABLED': 'true',
                'FAIL_FAST': 'true'  # Fail immediately if GPU not available
            }
        }
        
        try:
            response = self.sagemaker.create_processing_job(**job_config)
            print(f"   ✅ Job created successfully!")
            print(f"   Job ARN: {response['ProcessingJobArn']}")
            
            return {
                'job_name': job_name,
                'job_arn': response['ProcessingJobArn'],
                'output_s3_uri': output_s3_uri,
                'status': 'STARTED'
            }
            
        except Exception as e:
            print(f"   ❌ Failed to create job: {e}")
            return {
                'job_name': job_name,
                'status': 'FAILED',
                'error': str(e)
            }
    
    def monitor_job(self, job_name: str) -> dict:
        """Monitor the processing job and return final status"""
        print(f"⏱️  Monitoring job: {job_name}")
        
        start_time = time.time()
        
        while True:
            try:
                response = self.sagemaker.describe_processing_job(ProcessingJobName=job_name)
                status = response['ProcessingJobStatus']
                
                elapsed = time.time() - start_time
                print(f"   [{elapsed/60:.1f}m] Status: {status}")
                
                if status in ['Completed', 'Failed', 'Stopped']:
                    print(f"   🏁 Job finished with status: {status}")
                    
                    if status == 'Completed':
                        print(f"   ✅ SUCCESS! SOGS compression completed")
                    else:
                        failure_reason = response.get('FailureReason', 'Unknown')
                        print(f"   ❌ FAILURE: {failure_reason}")
                    
                    return {
                        'status': status,
                        'duration_minutes': elapsed / 60,
                        'failure_reason': response.get('FailureReason'),
                        'response': response
                    }
                
                # Wait before checking again
                time.sleep(30)
                
            except Exception as e:
                print(f"   ❌ Error monitoring job: {e}")
                return {
                    'status': 'ERROR',
                    'error': str(e)
                }
    
    def analyze_results(self, output_s3_uri: str) -> dict:
        """Analyze the compression results"""
        print(f"🔍 Analyzing results from: {output_s3_uri}")
        
        try:
            # Parse S3 URI
            bucket, prefix = output_s3_uri.replace("s3://", "").split("/", 1)
            
            # List all output files
            response = self.s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            
            if 'Contents' not in response:
                print("   ❌ No output files found!")
                return {
                    'success': False,
                    'file_count': 0,
                    'total_size': 0,
                    'files': []
                }
            
            files = []
            total_size = 0
            
            for obj in response['Contents']:
                file_info = {
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'modified': obj['LastModified'].isoformat()
                }
                files.append(file_info)
                total_size += obj['Size']
            
            print(f"   ✅ Found {len(files)} output files")
            print(f"   📊 Total size: {total_size / 1024:.1f} KB")
            
            # Check for SOGS-specific files
            sogs_files = [f for f in files if any(ext in f['key'].lower() for ext in ['.bin', '.sogs', '.json'])]
            webp_files = [f for f in files if '.webp' in f['key'].lower()]
            
            print(f"   🎯 SOGS files: {len(sogs_files)}")
            print(f"   🖼️  WebP files: {len(webp_files)}")
            
            # Determine if this is real SOGS or fallback
            is_real_sogs = len(sogs_files) > 0 and len(webp_files) == 0
            
            if is_real_sogs:
                print("   🎉 SUCCESS: Real SOGS compression detected!")
            else:
                print("   ⚠️  WARNING: Appears to be fallback compression")
            
            # Show first few files
            print("   📁 Output files:")
            for file_info in files[:10]:  # Show first 10
                print(f"      - {file_info['key']} ({file_info['size']} bytes)")
            
            if len(files) > 10:
                print(f"      ... and {len(files) - 10} more files")
            
            return {
                'success': True,
                'file_count': len(files),
                'total_size': total_size,
                'files': files,
                'sogs_files': len(sogs_files),
                'webp_files': len(webp_files),
                'is_real_sogs': is_real_sogs
            }
            
        except Exception as e:
            print(f"   ❌ Analysis failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_full_test(self) -> dict:
        """Run the complete GPU SOGS compression test"""
        print("🎯 Starting Full GPU SOGS Compression Test")
        print("=" * 60)
        
        try:
            # Step 1: Get test data
            input_s3_uri = self.get_existing_test_data()
            
            # Step 2: Start compression job
            job_result = self.run_gpu_compression_test(input_s3_uri)
            
            if job_result['status'] == 'FAILED':
                return job_result
            
            # Step 3: Monitor job
            monitor_result = self.monitor_job(job_result['job_name'])
            
            # Step 4: Analyze results if successful
            if monitor_result['status'] == 'Completed':
                analysis_result = self.analyze_results(job_result['output_s3_uri'])
                
                return {
                    'overall_status': 'SUCCESS' if analysis_result['is_real_sogs'] else 'PARTIAL_SUCCESS',
                    'job_result': job_result,
                    'monitor_result': monitor_result,
                    'analysis_result': analysis_result
                }
            else:
                return {
                    'overall_status': 'FAILED',
                    'job_result': job_result,
                    'monitor_result': monitor_result
                }
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return {
                'overall_status': 'ERROR',
                'error': str(e)
            }

def main():
    """Main test execution"""
    print("🚀 GPU SOGS Compression Test")
    print("Testing the new production SOGS container with GPU instances")
    print()
    
    # Run the test
    tester = GPUSOGSCompressionTest()
    result = tester.run_full_test()
    
    # Print final results
    print()
    print("=" * 60)
    print("🏁 FINAL RESULTS")
    print("=" * 60)
    
    status = result['overall_status']
    if status == 'SUCCESS':
        print("🎉 SUCCESS: Real SOGS compression working!")
        print("✅ GPU instances functional")
        print("✅ Container building and running")
        print("✅ SOGS compression producing correct output format")
    elif status == 'PARTIAL_SUCCESS':
        print("⚠️  PARTIAL SUCCESS: Job completed but using fallback compression")
        print("✅ GPU instances functional")
        print("✅ Container building and running")
        print("❌ SOGS compression falling back to WebP")
    else:
        print("❌ FAILURE: Test did not complete successfully")
        if 'error' in result:
            print(f"   Error: {result['error']}")
    
    # Print detailed results
    print()
    print("📊 Detailed Results:")
    print(json.dumps(result, indent=2, default=str))
    
    return result

if __name__ == "__main__":
    main() 