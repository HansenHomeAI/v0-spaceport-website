#!/usr/bin/env python3
"""
Production SOGS Compression Test
Comprehensive testing of SOGS container in AWS SageMaker environment
"""

import os
import sys
import json
import time
import boto3
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# Add the current directory to Python path for imports
sys.path.append(str(Path(__file__).parent))

class SOGSProductionTester:
    """Production tester for SOGS compression container"""
    
    def __init__(self, region: str = "us-west-2"):
        """Initialize the tester"""
        self.region = region
        self.sagemaker = boto3.client('sagemaker', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
        # Configuration
        self.ecr_image_uri = f"{self.account_id}.dkr.ecr.{region}.amazonaws.com/spaceport-ml-sogs-compressor:latest"
        self.test_bucket = "spaceport-uploads"
        self.output_bucket = "spaceport-ml-processing"
        
        print(f"🧪 SOGS Production Tester initialized")
        print(f"   Region: {region}")
        print(f"   Account: {self.account_id}")
        print(f"   Container: {self.ecr_image_uri}")
    
    def create_test_ply_file(self) -> str:
        """Create a realistic test PLY file for compression testing"""
        print("📁 Creating test PLY file...")
        
        # Create PLY header
        ply_content = """ply
format ascii 1.0
comment Generated test model for SOGS compression testing
element vertex 5000
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
        for i in range(5000):
            # Position (spherical distribution)
            theta = random.uniform(0, 2 * math.pi)
            phi = random.uniform(0, math.pi)
            r = random.uniform(1, 10)
            
            x = r * math.sin(phi) * math.cos(theta)
            y = r * math.sin(phi) * math.sin(theta)
            z = r * math.cos(phi)
            
            # Normal (pointing outward from center)
            norm = math.sqrt(x*x + y*y + z*z)
            nx = x / norm if norm > 0 else 0
            ny = y / norm if norm > 0 else 0
            nz = z / norm if norm > 0 else 0
            
            # Color (gradient based on position)
            red = int(255 * abs(nx))
            green = int(255 * abs(ny))
            blue = int(255 * abs(nz))
            
            # Scale (varying sizes)
            s0 = random.uniform(0.05, 0.5)
            s1 = random.uniform(0.05, 0.5)
            s2 = random.uniform(0.05, 0.5)
            
            # Rotation (random quaternion)
            # Generate random unit quaternion
            u1, u2, u3 = random.random(), random.random(), random.random()
            rot0 = math.sqrt(1-u1) * math.sin(2*math.pi*u2)
            rot1 = math.sqrt(1-u1) * math.cos(2*math.pi*u2)
            rot2 = math.sqrt(u1) * math.sin(2*math.pi*u3)
            rot3 = math.sqrt(u1) * math.cos(2*math.pi*u3)
            
            # Opacity
            opacity = random.uniform(0.3, 1.0)
            
            vertices.append(f"{x:.6f} {y:.6f} {z:.6f} {nx:.6f} {ny:.6f} {nz:.6f} {red} {green} {blue} {s0:.6f} {s1:.6f} {s2:.6f} {rot0:.6f} {rot1:.6f} {rot2:.6f} {rot3:.6f} {opacity:.6f}")
        
        # Combine header and data
        full_ply = ply_content + "\n".join(vertices)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ply', delete=False) as f:
            f.write(full_ply)
            temp_file = f.name
        
        # Upload to S3
        s3_key = f"test-data/production-test-{int(time.time())}.ply"
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
                if 'SageMakerExecutionRole' in role['RoleName']:
                    role_arn = role['Arn']
                    print(f"   Found role via IAM: {role_arn}")
                    return role_arn
        except Exception as e:
            print(f"   IAM role search failed: {e}")
        
        raise ValueError("Could not find SageMaker execution role. Please deploy ML pipeline stack first.")
    
    def run_compression_job(self, input_s3_uri: str) -> Dict:
        """Run a SageMaker Processing Job to test SOGS compression"""
        print("🚀 Starting SageMaker Processing Job...")
        
        # Get SageMaker role
        role_arn = self.get_sagemaker_role()
        
        # Create unique job name
        job_name = f"sogs-production-test-{int(time.time())}"
        output_s3_uri = f"s3://{self.output_bucket}/test-outputs/{job_name}/"
        
        print(f"   Job Name: {job_name}")
        print(f"   Input: {input_s3_uri}")
        print(f"   Output: {output_s3_uri}")
        print(f"   Container: {self.ecr_image_uri}")
        
        # Create processing job
        job_config = {
            'ProcessingJobName': job_name,
            'ProcessingResources': {
                'ClusterConfig': {
                    'InstanceCount': 1,
                    'InstanceType': 'ml.c6i.4xlarge',  # Use approved instance type
                    'VolumeSizeInGB': 50
                }
            },
            'AppSpecification': {
                'ImageUri': self.ecr_image_uri,
                'ContainerEntrypoint': ['python', '/opt/ml/compress_model.py']
            },
            'ProcessingInputs': [{
                'InputName': 'input-data',
                'AppManaged': False,
                'S3Input': {
                    'S3Uri': os.path.dirname(input_s3_uri) + "/",
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
                'LOG_LEVEL': 'INFO',
                'PYTHONUNBUFFERED': '1'
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
                    time.sleep(30)  # Check every 30 seconds
                else:
                    time.sleep(10)  # Check more frequently for other statuses
                    
            except Exception as e:
                print(f"   ⚠️  Error monitoring job: {e}")
                time.sleep(10)
    
    def analyze_results(self, output_s3_uri: str) -> Dict:
        """Download and analyze compression results"""
        print("📊 Analyzing compression results...")
        
        # List output files
        bucket = self.output_bucket
        prefix = output_s3_uri.replace(f"s3://{bucket}/", "")
        
        try:
            response = self.s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            if 'Contents' not in response:
                print("   ⚠️  No output files found")
                return {'status': 'no_outputs'}
            
            files = [(obj['Key'], obj['Size']) for obj in response['Contents']]
            print(f"   Found {len(files)} output files:")
            
            total_size = 0
            for key, size in files:
                filename = os.path.basename(key)
                print(f"     - {filename}: {size / 1024:.1f} KB")
                total_size += size
            
            print(f"   Total output size: {total_size / 1024:.1f} KB")
            
            # Download and analyze reports
            results = {
                'status': 'success',
                'total_files': len(files),
                'total_size_kb': total_size / 1024,
                'files': files
            }
            
            # Try to download compression report
            report_key = None
            for key, _ in files:
                if key.endswith('compression_report.json'):
                    report_key = key
                    break
            
            if report_key:
                print("   📄 Downloading compression report...")
                temp_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False)
                self.s3.download_file(bucket, report_key, temp_file.name)
                
                try:
                    with open(temp_file.name, 'r') as f:
                        report_data = json.load(f)
                    
                    results['compression_report'] = report_data
                    
                    # Extract key metrics
                    if 'compression_metrics' in report_data:
                        metrics = report_data['compression_metrics']
                        print(f"   📈 Compression Metrics:")
                        print(f"      - Compression Ratio: {metrics.get('compression_ratio', 'N/A')}")
                        print(f"      - Original Size: {metrics.get('original_size_mb', 'N/A')} MB")
                        print(f"      - Compressed Size: {metrics.get('compressed_size_mb', 'N/A')} MB")
                        print(f"      - Space Saved: {metrics.get('space_saved_percent', 'N/A')}%")
                        
                        # Check if compression was effective
                        compression_ratio = metrics.get('compression_ratio', 0)
                        if compression_ratio >= 5.0:  # At least 5:1 ratio
                            print("   ✅ Compression ratio meets expectations (≥5:1)")
                            results['compression_effective'] = True
                        else:
                            print(f"   ⚠️  Compression ratio below expectations: {compression_ratio}:1")
                            results['compression_effective'] = False
                
                except Exception as e:
                    print(f"   ⚠️  Could not parse compression report: {e}")
                    results['report_error'] = str(e)
                
                os.unlink(temp_file.name)
            else:
                print("   ⚠️  No compression report found")
                results['no_report'] = True
            
            return results
            
        except Exception as e:
            print(f"   ❌ Error analyzing results: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def run_full_test(self) -> Dict:
        """Run the complete production test"""
        print("🎯 Starting SOGS Production Test")
        print("=" * 50)
        
        test_results = {
            'start_time': time.time(),
            'test_phases': {}
        }
        
        try:
            # Phase 1: Create test data
            print("\n📁 Phase 1: Creating test data...")
            input_s3_uri = self.create_test_ply_file()
            test_results['test_phases']['data_creation'] = {
                'status': 'success',
                'input_s3_uri': input_s3_uri
            }
            
            # Phase 2: Run compression job
            print("\n🚀 Phase 2: Running compression job...")
            job_info = self.run_compression_job(input_s3_uri)
            test_results['test_phases']['job_creation'] = {
                'status': 'success',
                'job_info': job_info
            }
            
            # Phase 3: Monitor job
            print("\n⏱️  Phase 3: Monitoring job...")
            job_result = self.monitor_job(job_info['job_name'])
            test_results['test_phases']['job_execution'] = job_result
            
            if job_result['status'] != 'success':
                print("❌ Job failed, stopping test")
                test_results['overall_status'] = 'failed'
                test_results['failure_reason'] = 'Job execution failed'
                return test_results
            
            # Phase 4: Analyze results
            print("\n📊 Phase 4: Analyzing results...")
            analysis_result = self.analyze_results(job_info['output_s3_uri'])
            test_results['test_phases']['result_analysis'] = analysis_result
            
            # Overall assessment
            if analysis_result.get('status') == 'success':
                if analysis_result.get('compression_effective', False):
                    test_results['overall_status'] = 'success'
                    print("\n🎉 SOGS Production Test PASSED!")
                else:
                    test_results['overall_status'] = 'partial'
                    print("\n⚠️  SOGS Production Test PARTIAL - compression below expectations")
            else:
                test_results['overall_status'] = 'failed'
                test_results['failure_reason'] = 'Result analysis failed'
                print("\n❌ SOGS Production Test FAILED")
            
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            test_results['overall_status'] = 'error'
            test_results['error'] = str(e)
        
        test_results['end_time'] = time.time()
        test_results['total_duration'] = int(test_results['end_time'] - test_results['start_time'])
        
        return test_results

def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description='SOGS Production Test')
    parser.add_argument('--region', default='us-west-2', help='AWS region')
    parser.add_argument('--output-file', help='Save test results to JSON file')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Run the test
    tester = SOGSProductionTester(region=args.region)
    results = tester.run_full_test()
    
    # Save results if requested
    if args.output_file:
        with open(args.output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📄 Test results saved to: {args.output_file}")
    
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
        print("\n✅ SOGS compression container is working correctly in production!")
        return 0
    else:
        print(f"\n❌ Test failed: {results.get('failure_reason', 'Unknown error')}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 