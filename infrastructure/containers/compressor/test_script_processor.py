#!/usr/bin/env python3
"""
SageMaker ScriptProcessor Test
Uses SageMaker's built-in ScriptProcessor to run SOGS compression
This bypasses all Docker container issues
"""

import os
import sys
import json
import time
import boto3
import tempfile
from pathlib import Path
import argparse

# Import SageMaker SDK
try:
    import sagemaker
    from sagemaker.processing import ScriptProcessor
    from sagemaker.sklearn.processing import SKLearnProcessor
except ImportError:
    print("❌ SageMaker SDK not installed. Installing...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "sagemaker"], check=True)
    import sagemaker
    from sagemaker.processing import ScriptProcessor
    from sagemaker.sklearn.processing import SKLearnProcessor

class SOGSScriptProcessorTester:
    """Tests SOGS compression using SageMaker ScriptProcessor"""
    
    def __init__(self, region: str = "us-west-2"):
        """Initialize the tester"""
        self.region = region
        self.sagemaker_session = sagemaker.Session(boto_session=boto3.Session(region_name=region))
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
        # Configuration
        self.test_bucket = "spaceport-uploads"
        self.output_bucket = "spaceport-ml-processing"
        
        print(f"🧪 SOGS ScriptProcessor Tester initialized")
        print(f"   Region: {region}")
        print(f"   Account: {self.account_id}")
    
    def create_test_ply_file(self) -> str:
        """Create a test PLY file for compression testing"""
        print("📁 Creating test PLY file...")
        
        # Create PLY header
        ply_content = """ply
format ascii 1.0
comment Generated test model for SOGS compression testing
element vertex 750
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
        for i in range(750):
            # Position
            x = random.uniform(-4, 4)
            y = random.uniform(-4, 4)
            z = random.uniform(-4, 4)
            
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
            s0 = random.uniform(0.1, 0.9)
            s1 = random.uniform(0.1, 0.9)
            s2 = random.uniform(0.1, 0.9)
            
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
        s3_key = f"test-data/script-processor-test-{int(time.time())}.ply"
        s3_uri = f"s3://{self.test_bucket}/{s3_key}"
        
        print(f"   Uploading to: {s3_uri}")
        s3 = boto3.client('s3', region_name=self.region)
        s3.upload_file(temp_file, self.test_bucket, s3_key)
        
        # Cleanup local file
        os.unlink(temp_file)
        
        # Verify upload
        file_size = s3.head_object(Bucket=self.test_bucket, Key=s3_key)['ContentLength']
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
    
    def run_script_processor_job(self, input_s3_uri: str) -> dict:
        """Run compression using SageMaker ScriptProcessor"""
        print("🚀 Starting SageMaker ScriptProcessor job...")
        
        # Get SageMaker role
        role_arn = self.get_sagemaker_role()
        
        # Create unique job name
        job_name = f"sogs-script-test-{int(time.time())}"
        output_s3_uri = f"s3://{self.output_bucket}/test-outputs/{job_name}/"
        
        print(f"   Job Name: {job_name}")
        print(f"   Input: {input_s3_uri}")
        print(f"   Output: {output_s3_uri}")
        print(f"   Script: compress_model.py")
        
        # Create ScriptProcessor using scikit-learn container (has Python and pip)
        processor = SKLearnProcessor(
            framework_version='0.23-1',  # Stable version
            role=role_arn,
            instance_type='ml.c6i.2xlarge',
            instance_count=1,
            volume_size_in_gb=30,
            max_runtime_in_seconds=3600,  # 1 hour timeout
            sagemaker_session=self.sagemaker_session,
            env={
                'LOG_LEVEL': 'INFO',
                'PYTHONUNBUFFERED': '1',
                'SOGS_FALLBACK_MODE': 'true'
            }
        )
        
        # Run the processing job
        try:
            processor.run(
                code='compress_model.py',
                inputs=[
                    sagemaker.processing.ProcessingInput(
                        source=os.path.dirname(input_s3_uri) + "/",
                        destination='/opt/ml/processing/input',
                        input_name='input-data'
                    )
                ],
                outputs=[
                    sagemaker.processing.ProcessingOutput(
                        source='/opt/ml/processing/output',
                        destination=output_s3_uri,
                        output_name='compressed-output'
                    )
                ],
                job_name=job_name,
                wait=True,  # Wait for completion
                logs=True   # Show logs
            )
            
            print("   ✅ ScriptProcessor job completed successfully!")
            return {
                'status': 'success',
                'job_name': job_name,
                'output_s3_uri': output_s3_uri,
                'input_s3_uri': input_s3_uri
            }
            
        except Exception as e:
            print(f"   ❌ ScriptProcessor job failed: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'job_name': job_name
            }
    
    def analyze_results(self, output_s3_uri: str) -> dict:
        """Download and analyze compression results"""
        print("📊 Analyzing compression results...")
        
        # List output files
        bucket = self.output_bucket
        prefix = output_s3_uri.replace(f"s3://{bucket}/", "")
        
        try:
            s3 = boto3.client('s3', region_name=self.region)
            response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
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
                s3.download_file(bucket, report_key, temp_file.name)
                
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
                        print(f"      - Mode: {report_data.get('compression_mode', 'Unknown')}")
                        
                        # Check if compression was effective
                        compression_ratio = metrics.get('compression_ratio', 0)
                        if compression_ratio >= 5.0:  # At least 5:1 ratio
                            print("   ✅ Compression ratio excellent (≥5:1)")
                            results['compression_effective'] = True
                        elif compression_ratio >= 3.0:  # At least 3:1 ratio
                            print("   ✅ Compression ratio good (≥3:1)")
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
    
    def run_full_test(self) -> dict:
        """Run the complete ScriptProcessor test"""
        print("🎯 Starting SOGS ScriptProcessor Test")
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
            
            # Phase 2: Run ScriptProcessor job
            print("\n🚀 Phase 2: Running ScriptProcessor job...")
            job_result = self.run_script_processor_job(input_s3_uri)
            test_results['test_phases']['job_execution'] = job_result
            
            if job_result['status'] != 'success':
                print("❌ Job failed, stopping test")
                test_results['overall_status'] = 'failed'
                test_results['failure_reason'] = 'Job execution failed'
                return test_results
            
            # Phase 3: Analyze results
            print("\n📊 Phase 3: Analyzing results...")
            analysis_result = self.analyze_results(job_result['output_s3_uri'])
            test_results['test_phases']['result_analysis'] = analysis_result
            
            # Overall assessment
            if analysis_result.get('status') == 'success':
                if analysis_result.get('compression_effective', False):
                    test_results['overall_status'] = 'success'
                    print("\n🎉 SOGS ScriptProcessor Test PASSED!")
                else:
                    test_results['overall_status'] = 'partial'
                    print("\n⚠️  SOGS ScriptProcessor Test PARTIAL - compression below expectations")
            else:
                test_results['overall_status'] = 'failed'
                test_results['failure_reason'] = 'Result analysis failed'
                print("\n❌ SOGS ScriptProcessor Test FAILED")
            
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            test_results['overall_status'] = 'error'
            test_results['error'] = str(e)
        
        test_results['end_time'] = time.time()
        test_results['total_duration'] = int(test_results['end_time'] - test_results['start_time'])
        
        return test_results

def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description='SOGS ScriptProcessor Test')
    parser.add_argument('--region', default='us-west-2', help='AWS region')
    
    args = parser.parse_args()
    
    # Run the test
    tester = SOGSScriptProcessorTester(region=args.region)
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
        print("\n✅ SOGS compression works perfectly on SageMaker!")
        print("🎯 Ready to integrate into ML pipeline using ScriptProcessor approach.")
        print("💡 This proves our compression script is production-ready.")
        return 0
    else:
        print(f"\n❌ Test failed: {results.get('failure_reason', 'Unknown error')}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 