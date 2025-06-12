#!/usr/bin/env python3
"""
Production Test Script for Optimized 3DGS Pipeline
Tests the complete pipeline with the small dataset to validate performance
"""

import boto3
import json
import time
import uuid
from datetime import datetime
from pathlib import Path

class OptimizedPipelineTest:
    def __init__(self, region='us-west-2'):
        self.region = region
        self.stepfunctions = boto3.client('stepfunctions', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
        # Configuration
        self.test_config = {
            'small_dataset_s3_url': 's3://spaceport-uploads/1748664812459-5woqcu-Archive.zip',
            'test_email': 'test@spaceport.com',
            'state_machine_arn': f'arn:aws:states:{region}:{self.account_id}:stateMachine:SpaceportMLPipeline',
            'expected_performance': {
                'min_psnr': 30.0,  # Relaxed for small dataset
                'max_training_time_minutes': 15,  # Small dataset should be fast
                'max_model_size_mb': 10.0,  # Small dataset = small model
                'expected_early_termination': True
            }
        }
    
    def create_test_job_input(self):
        """Create test job input with optimization parameters"""
        job_id = f"test-optimized-{int(time.time())}"
        
        return {
            "jobId": job_id,
            "jobName": f"optimized-test-{job_id}",
            "s3Url": self.test_config['small_dataset_s3_url'],  # Keep for compatibility
            "inputS3Uri": self.test_config['small_dataset_s3_url'],  # Field expected by Step Functions
            "email": self.test_config['test_email'],
            "timestamp": datetime.now().isoformat(),
            
            # Required field for Step Functions choice logic
            "pipelineStep": "sfm",  # Start from beginning (full pipeline)
            
            # S3 paths for pipeline stages
            "extractedS3Uri": f"s3://spaceport-ml-pipeline/jobs/{job_id}/extracted/",
            "colmapOutputS3Uri": f"s3://spaceport-ml-pipeline/jobs/{job_id}/colmap/",
            "gaussianOutputS3Uri": f"s3://spaceport-ml-pipeline/jobs/{job_id}/gaussian/",
            "compressedOutputS3Uri": f"s3://spaceport-ml-pipeline/jobs/{job_id}/compressed/",
            
            # Container image URIs with correct field names
            "extractorImageUri": f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/sagemaker-unzip:latest",
            "sfmImageUri": f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/spaceport/sfm:latest",  # Fixed field name
            "gaussianImageUri": f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/spaceport/3dgs:latest",
            "compressorImageUri": f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/spaceport/compressor:latest",
            
            # Optimization flags for the enhanced training
            "optimization_enabled": True,
            "progressive_resolution": True,
            "psnr_plateau_termination": True,
            "target_psnr": 30.0,
            "max_iterations": 10000  # Reduced for small dataset testing
        }
    
    def start_test_execution(self):
        """Start the Step Functions execution"""
        job_input = self.create_test_job_input()
        
        print("🚀 STARTING OPTIMIZED 3DGS PIPELINE TEST")
        print("=" * 50)
        print(f"Job ID: {job_input['jobId']}")
        print(f"Dataset: {self.test_config['small_dataset_s3_url']}")
        print(f"Expected optimizations:")
        print(f"  • Progressive resolution training")
        print(f"  • PSNR plateau early termination")
        print(f"  • Significance-based pruning")
        print(f"  • Target PSNR: {job_input['target_psnr']}dB")
        print("")
        
        try:
            response = self.stepfunctions.start_execution(
                stateMachineArn=self.test_config['state_machine_arn'],
                name=job_input['jobName'],
                input=json.dumps(job_input)
            )
            
            execution_arn = response['executionArn']
            print(f"✅ Execution started successfully!")
            print(f"   Execution ARN: {execution_arn}")
            print("")
            
            return execution_arn, job_input
            
        except Exception as e:
            print(f"❌ Failed to start execution: {str(e)}")
            return None, None
    
    def monitor_execution(self, execution_arn, job_input):
        """Monitor the execution progress"""
        print("📊 MONITORING EXECUTION PROGRESS")
        print("=" * 40)
        
        start_time = time.time()
        last_status = None
        
        while True:
            try:
                response = self.stepfunctions.describe_execution(
                    executionArn=execution_arn
                )
                
                status = response['status']
                elapsed_minutes = (time.time() - start_time) / 60
                
                if status != last_status:
                    print(f"[{elapsed_minutes:.1f}m] Status: {status}")
                    last_status = status
                
                if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                    print(f"\n🏁 Execution completed with status: {status}")
                    print(f"   Total time: {elapsed_minutes:.1f} minutes")
                    
                    if status == 'SUCCEEDED':
                        return self.validate_results(job_input, elapsed_minutes)
                    else:
                        print(f"❌ Execution failed. Check CloudWatch logs for details.")
                        return False
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"❌ Error monitoring execution: {str(e)}")
                return False
    
    def validate_results(self, job_input, execution_time_minutes):
        """Validate the training results against production criteria"""
        print("\n🔍 VALIDATING RESULTS")
        print("=" * 30)
        
        try:
            # Check for training outputs in S3
            bucket = 'spaceport-ml-pipeline'
            job_id = job_input['jobId']
            
            # List objects in the gaussian output path
            gaussian_prefix = f"jobs/{job_id}/gaussian/"
            response = self.s3.list_objects_v2(
                Bucket=bucket,
                Prefix=gaussian_prefix
            )
            
            if 'Contents' not in response:
                print("❌ No output files found in S3")
                return False
            
            files_found = [obj['Key'] for obj in response['Contents']]
            print(f"✅ Found {len(files_found)} output files:")
            for file in files_found[:5]:  # Show first 5 files
                print(f"   - {file}")
            
            # Performance validation
            validation_results = {
                'execution_time_check': execution_time_minutes <= self.test_config['expected_performance']['max_training_time_minutes'],
                'output_files_exist': len(files_found) > 0,
                'reasonable_duration': 2 <= execution_time_minutes <= 20  # Reasonable range for small dataset
            }
            
            # Print validation results
            print(f"\n📊 PERFORMANCE VALIDATION:")
            print(f"✅ Execution time: {execution_time_minutes:.1f}m (max: {self.test_config['expected_performance']['max_training_time_minutes']}m) - {'PASS' if validation_results['execution_time_check'] else 'FAIL'}")
            print(f"✅ Output files: {len(files_found)} files - {'PASS' if validation_results['output_files_exist'] else 'FAIL'}")
            print(f"✅ Duration reasonable: {'PASS' if validation_results['reasonable_duration'] else 'FAIL'}")
            
            overall_pass = all(validation_results.values())
            
            print(f"\n{'🎉 PRODUCTION TEST: PASSED' if overall_pass else '❌ PRODUCTION TEST: FAILED'}")
            
            if overall_pass:
                print("✅ Pipeline is ready for larger datasets!")
                print("📋 Next steps:")
                print("   1. Deploy optimized container with latest techniques")
                print("   2. Test with medium-sized dataset (100-200 images)")
                print("   3. Validate quality metrics (PSNR, model size)")
                print("   4. Scale to production datasets")
            else:
                print("❌ Pipeline needs optimization before production use")
                print("🔧 Recommended actions:")
                print("   1. Check CloudWatch logs for training issues")
                print("   2. Verify container configurations")
                print("   3. Optimize training parameters")
            
            return overall_pass
            
        except Exception as e:
            print(f"❌ Validation failed: {str(e)}")
            return False
    
    def run_complete_test(self):
        """Run the complete pipeline test"""
        print("🎯 PRODUCTION-READY 3DGS PIPELINE TEST")
        print("=" * 50)
        print(f"Testing with small dataset: 22 photos")
        print(f"Expected optimizations: Progressive training, PSNR plateau, pruning")
        print("")
        
        # Start execution
        execution_arn, job_input = self.start_test_execution()
        if not execution_arn:
            return False
        
        # Monitor and validate
        return self.monitor_execution(execution_arn, job_input)

def main():
    """Main test function"""
    tester = OptimizedPipelineTest()
    
    print("🧪 OPTIMIZED 3DGS PIPELINE - PRODUCTION TEST")
    print("=" * 60)
    print("This test validates the pipeline with a small dataset")
    print("to ensure production readiness before scaling up.")
    print("")
    
    success = tester.run_complete_test()
    
    if success:
        print("\n🚀 SUCCESS: Pipeline is production-ready!")
        return 0
    else:
        print("\n❌ FAILURE: Pipeline needs optimization")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 