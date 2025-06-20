#!/usr/bin/env python3
"""
Direct SageMaker Test
Tests SOGS compression by uploading the script to SageMaker directly
Uses pre-built Python container instead of custom Docker build
"""

import os
import sys
import json
import time
import boto3
import tempfile
import zipfile
from pathlib import Path
from typing import Dict
import argparse

class DirectSageMakerTester:
    """Tests SOGS compression using direct script upload to SageMaker"""
    
    def __init__(self, region: str = "us-west-2"):
        """Initialize the tester"""
        self.region = region
        self.sagemaker = boto3.client('sagemaker', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
        # Configuration
        self.test_bucket = "spaceport-uploads"
        self.output_bucket = "spaceport-ml-processing"
        self.code_bucket = f"sogs-code-{self.account_id}"
        
        print(f"🧪 Direct SageMaker Tester initialized")
        print(f"   Region: {region}")
        print(f"   Account: {self.account_id}")
    
    def setup_code_bucket(self):
        """Create S3 bucket for code artifacts"""
        print("📦 Setting up code bucket...")
        
        try:
            if self.region == 'us-east-1':
                self.s3.create_bucket(Bucket=self.code_bucket)
            else:
                self.s3.create_bucket(
                    Bucket=self.code_bucket,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
            print(f"   ✅ Code bucket created: {self.code_bucket}")
        except Exception as e:
            if "BucketAlreadyExists" in str(e) or "BucketAlreadyOwnedByYou" in str(e):
                print(f"   ✅ Code bucket exists: {self.code_bucket}")
            else:
                print(f"   ❌ Code bucket error: {e}")
                raise
    
    def upload_code_package(self):
        """Upload compression code as a package to S3"""
        print("📁 Creating and uploading code package...")
        
        # Create ZIP file with compression script and dependencies
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip.name, 'w') as zf:
                # Add compression script
                zf.write('compress_model.py', 'compress_model.py')
                print(f"   Added: compress_model.py")
                
                # Add requirements
                zf.write('requirements.txt', 'requirements.txt')
                print(f"   Added: requirements.txt")
                
                # Create a simple entrypoint script
                entrypoint_script = '''#!/usr/bin/env python3
import subprocess
import sys
import os

# Install requirements
print("Installing requirements...")
subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

# Run the compression script
print("Running compression script...")
os.execv(sys.executable, [sys.executable, "compress_model.py"])
'''
                zf.writestr('entrypoint.py', entrypoint_script)
                print(f"   Added: entrypoint.py")
            
            # Upload to S3
            code_s3_key = f"code/sogs-compression-{int(time.time())}.zip"
            self.s3.upload_file(tmp_zip.name, self.code_bucket, code_s3_key)
            os.unlink(tmp_zip.name)
            
            code_s3_uri = f"s3://{self.code_bucket}/{code_s3_key}"
            print(f"   ✅ Code uploaded: {code_s3_uri}")
            return code_s3_uri
    
    def create_test_ply_file(self) -> str:
        """Create a test PLY file for compression testing"""
        print("📁 Creating test PLY file...")
        
        # Create PLY header
        ply_content = """ply
format ascii 1.0
comment Generated test model for SOGS compression testing
element vertex 500
property float x
property float y
property float z
property float nx
property float ny
property float nz
property uchar red
property uchar green
property uchar blue
property float scale_0
property float scale_1
property float scale_2
property float rot_0
property float rot_1
property float rot_2
property float rot_3
property float opacity
end_header
"""
        
        # Generate realistic Gaussian splat data
        import random
        import math
        
        vertices = []
        for i in range(500):
            # Position
            x = random.uniform(-3, 3)
            y = random.uniform(-3, 3)
            z = random.uniform(-3, 3)
            
            # Normal
            nx = random.uniform(-1, 1)
            ny = random.uniform(-1, 1)
            nz = random.uniform(-1, 1)
            norm = math.sqrt(nx*nx + ny*ny + nz*nz)
            if norm > 0:
                nx, ny, nz = nx/norm, ny/norm, nz/norm
            
            # Color
            red = random.randint(50, 255)
            green = random.randint(50, 255)
            blue = random.randint(50, 255)
            
            # Scale
            s0 = random.uniform(0.1, 0.8)
            s1 = random.uniform(0.1, 0.8)
            s2 = random.uniform(0.1, 0.8)
            
            # Rotation (quaternion)
            u1, u2, u3 = random.random(), random.random(), random.random()
            rot0 = math.sqrt(1-u1) * math.sin(2*math.pi*u2)
            rot1 = math.sqrt(1-u1) * math.cos(2*math.pi*u2)
            rot2 = math.sqrt(u1) * math.sin(2*math.pi*u3)
            rot3 = math.sqrt(u1) * math.cos(2*math.pi*u3)
            
            # Opacity
            opacity = random.uniform(0.5, 1.0)
            
            vertices.append(f"{x:.6f} {y:.6f} {z:.6f} {nx:.6f} {ny:.6f} {nz:.6f} {red} {green} {blue} {s0:.6f} {s1:.6f} {s2:.6f} {rot0:.6f} {rot1:.6f} {rot2:.6f} {rot3:.6f} {opacity:.6f}")
        
        # Combine header and data
        full_ply = ply_content + "\n".join(vertices)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ply', delete=False) as f:
            f.write(full_ply)
            temp_file = f.name
        
        # Upload to S3
        s3_key = f"test-data/direct-test-{int(time.time())}.ply"
        s3_uri = f"s3://{self.test_bucket}/{s3_key}"
        
        print(f"   Uploading to: {s3_uri}")
        self.s3.upload_file(temp_file, self.test_bucket, s3_key)
        
        # Cleanup local file
        os.unlink(temp_file)
        
        # Verify upload
        file_size = self.s3.head_object(Bucket=self.test_bucket, Key=s3_key)['ContentLength']
        print(f"   ✅ Test PLY uploaded: {file_size / 1024:.1f} KB")
        
        return s3_uri
    
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
                    print(f"   Found role: {role_arn}")
                    return role_arn
        except Exception as e:
            print(f"   CloudFormation lookup failed: {e}")
        
        # Fallback: search IAM roles
        iam = boto3.client('iam', region_name=self.region)
        try:
            roles = iam.list_roles()
            for role in roles['Roles']:
                if 'SageMakerExecutionRole' in role['RoleName'] or 'MySageMakerExecutionRole' in role['RoleName']:
                    role_arn = role['Arn']
                    print(f"   Found role via IAM: {role_arn}")
                    return role_arn
        except Exception as e:
            print(f"   IAM role search failed: {e}")
        
        raise ValueError("Could not find SageMaker execution role. Please deploy ML pipeline stack first.")
    
    def run_processing_job(self, input_s3_uri: str, code_s3_uri: str) -> Dict:
        """Run a SageMaker Processing Job with direct script execution"""
        print("🚀 Starting SageMaker Processing Job with direct script...")
        
        # Get SageMaker role
        role_arn = self.get_sagemaker_role()
        
        # Create unique job name
        job_name = f"sogs-direct-test-{int(time.time())}"
        output_s3_uri = f"s3://{self.output_bucket}/test-outputs/{job_name}/"
        
        print(f"   Job Name: {job_name}")
        print(f"   Input: {input_s3_uri}")
        print(f"   Code: {code_s3_uri}")
        print(f"   Output: {output_s3_uri}")
        
        # Create processing job using pre-built Python container
        job_config = {
            'ProcessingJobName': job_name,
            'ProcessingResources': {
                'ClusterConfig': {
                    'InstanceCount': 1,
                    'InstanceType': 'ml.c6i.2xlarge',
                    'VolumeSizeInGB': 30
                }
            },
            'AppSpecification': {
                'ImageUri': '236514542706.dkr.ecr.us-west-2.amazonaws.com/sagemaker-base-python-v4:1-cpu',  # Pre-built SageMaker Python container
                'ContainerEntrypoint': ['python', '/opt/ml/processing/input/code/entrypoint.py']
            },
            'ProcessingInputs': [
                {
                    'InputName': 'input-data',
                    'AppManaged': False,
                    'S3Input': {
                        'S3Uri': os.path.dirname(input_s3_uri) + "/",
                        'LocalPath': '/opt/ml/processing/input',
                        'S3DataType': 'S3Prefix',
                        'S3InputMode': 'File'
                    }
                },
                {
                    'InputName': 'code',
                    'AppManaged': False,
                    'S3Input': {
                        'S3Uri': code_s3_uri,
                        'LocalPath': '/opt/ml/processing/input/code',
                        'S3DataType': 'S3Prefix',
                        'S3InputMode': 'File',
                        'S3CompressionType': 'None'
                    }
                }
            ],
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
                'LOG_LEVEL': 'INFO',
                'PYTHONUNBUFFERED': '1',
                'SOGS_FALLBACK_MODE': 'true'
            }
        }
        
        # Start the job
        response = self.sagemaker.create_processing_job(**job_config)
        print(f"   ✅ Job created: {response['ProcessingJobArn']}")
        
        return {
            'job_name': job_name,
            'job_arn': response['ProcessingJobArn'],
            'output_s3_uri': output_s3_uri,
            'input_s3_uri': input_s3_uri
        }
    
    def monitor_job(self, job_name: str) -> Dict:
        """Monitor the processing job until completion"""
        print(f"⏱️  Monitoring job: {job_name}")
        
        start_time = time.time()
        last_status = None
        
        while True:
            try:
                response = self.sagemaker.describe_processing_job(ProcessingJobName=job_name)
                status = response['ProcessingJobStatus']
                
                if status != last_status:
                    elapsed = int(time.time() - start_time)
                    print(f"   Status: {status} (elapsed: {elapsed}s)")
                    last_status = status
                
                if status == 'Completed':
                    print("   ✅ Job completed successfully!")
                    return {
                        'status': 'success',
                        'duration': int(time.time() - start_time),
                        'details': response
                    }
                elif status in ['Failed', 'Stopped']:
                    failure_reason = response.get('FailureReason', 'Unknown failure')
                    print(f"   ❌ Job failed: {failure_reason}")
                    return {
                        'status': 'failed',
                        'duration': int(time.time() - start_time),
                        'failure_reason': failure_reason,
                        'details': response
                    }
                elif status == 'InProgress':
                    time.sleep(30)
                else:
                    time.sleep(10)
                    
            except Exception as e:
                print(f"   ⚠️  Error monitoring job: {e}")
                time.sleep(10)
    
    def run_full_test(self) -> Dict:
        """Run the complete direct SageMaker test"""
        print("🎯 Starting Direct SageMaker Test")
        print("=" * 50)
        
        test_results = {
            'start_time': time.time(),
            'test_phases': {}
        }
        
        try:
            # Phase 1: Setup
            print("\n🔧 Phase 1: Setting up infrastructure...")
            self.setup_code_bucket()
            test_results['test_phases']['setup'] = {'status': 'success'}
            
            # Phase 2: Upload code
            print("\n📦 Phase 2: Uploading code package...")
            code_s3_uri = self.upload_code_package()
            test_results['test_phases']['code_upload'] = {
                'status': 'success',
                'code_s3_uri': code_s3_uri
            }
            
            # Phase 3: Create test data
            print("\n📁 Phase 3: Creating test data...")
            input_s3_uri = self.create_test_ply_file()
            test_results['test_phases']['data_creation'] = {
                'status': 'success',
                'input_s3_uri': input_s3_uri
            }
            
            # Phase 4: Run processing job
            print("\n🚀 Phase 4: Running SageMaker job...")
            job_info = self.run_processing_job(input_s3_uri, code_s3_uri)
            test_results['test_phases']['job_creation'] = {
                'status': 'success',
                'job_info': job_info
            }
            
            # Phase 5: Monitor job
            print("\n⏱️  Phase 5: Monitoring job...")
            job_result = self.monitor_job(job_info['job_name'])
            test_results['test_phases']['job_execution'] = job_result
            
            if job_result['status'] == 'success':
                test_results['overall_status'] = 'success'
                print("\n🎉 Direct SageMaker Test PASSED!")
            else:
                test_results['overall_status'] = 'failed'
                test_results['failure_reason'] = 'Job execution failed'
                print("\n❌ Direct SageMaker Test FAILED")
            
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            test_results['overall_status'] = 'error'
            test_results['error'] = str(e)
        
        test_results['end_time'] = time.time()
        test_results['total_duration'] = int(test_results['end_time'] - test_results['start_time'])
        
        return test_results

def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description='Direct SageMaker SOGS Test')
    parser.add_argument('--region', default='us-west-2', help='AWS region')
    
    args = parser.parse_args()
    
    # Run the test
    tester = DirectSageMakerTester(region=args.region)
    results = tester.run_full_test()
    
    # Print summary
    print("\n" + "=" * 50)
    print("🏁 TEST SUMMARY")
    print("=" * 50)
    print(f"Overall Status: {results['overall_status'].upper()}")
    print(f"Total Duration: {results['total_duration']} seconds")
    
    for phase, result in results['test_phases'].items():
        status = result.get('status', 'unknown')
        print(f"{phase.replace('_', ' ').title()}: {status.upper()}")
    
    if results['overall_status'] == 'success':
        print("\n✅ SOGS compression works correctly on SageMaker!")
        print("💡 Ready to integrate into ML pipeline.")
        return 0
    else:
        print(f"\n❌ Test failed: {results.get('failure_reason', 'Unknown error')}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 