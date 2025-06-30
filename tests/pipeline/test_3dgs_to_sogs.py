#!/usr/bin/env python3
"""
🎯 3DGS → SOGS Pipeline Test
============================
Tests the 3DGS training step followed by SOGS compression.
Uses existing SfM output from successful runs as starting point.
"""

import boto3
import json
import time
import logging
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GaussianToSOGSTest:
    def __init__(self):
        self.stepfunctions = boto3.client('stepfunctions', region_name='us-west-2')
        self.s3 = boto3.client('s3', region_name='us-west-2')
        self.bucket = 'spaceport-uploads'
        
        # Use existing SfM output from successful run
        self.job_id = f"3dgs-sogs-test-{int(time.time())}"
        self.existing_sfm_job = "prod-validation-1750974917"  # From successful SfM run
        
        # Step Function ARN
        self.state_machine_arn = "arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline"
        
    def copy_sfm_output(self):
        """Copy existing SfM output to our new job directory"""
        logger.info(f"📁 Copying SfM output from {self.existing_sfm_job} to {self.job_id}")
        
        # List objects in the existing SfM job
        response = self.s3.list_objects_v2(
            Bucket=self.bucket,
            Prefix=f"jobs/{self.existing_sfm_job}/colmap/"
        )
        
        if 'Contents' not in response:
            raise Exception(f"No SfM output found for job {self.existing_sfm_job}")
            
        # Copy each file to the new job directory
        copied_files = 0
        for obj in response['Contents']:
            source_key = obj['Key']
            # Replace the job ID in the path
            dest_key = source_key.replace(f"jobs/{self.existing_sfm_job}/", f"jobs/{self.job_id}/")
            
            logger.info(f"   Copying: {source_key} → {dest_key}")
            
            self.s3.copy_object(
                CopySource={'Bucket': self.bucket, 'Key': source_key},
                Bucket=self.bucket,
                Key=dest_key
            )
            copied_files += 1
            
        logger.info(f"✅ Copied {copied_files} SfM files to new job directory")
        return copied_files
        
    def create_modified_step_function_input(self):
        """Create Step Function input that starts from 3DGS step"""
        return {
            "pipelineStep": "3dgs",  # Start from 3DGS step
            "jobName": self.job_id,
            "jobId": self.job_id,
            "inputS3Uri": f"s3://{self.bucket}/jobs/{self.job_id}/colmap/",  # Point to copied SfM output
            "colmapOutputS3Uri": f"s3://{self.bucket}/jobs/{self.job_id}/colmap/",
            "gaussianOutputS3Uri": f"s3://{self.bucket}/jobs/{self.job_id}/3dgs/",
            "compressedOutputS3Uri": f"s3://{self.bucket}/jobs/{self.job_id}/compressed/",
            "email": "test@example.com",
            "s3Url": f"s3://{self.bucket}/jobs/{self.job_id}/colmap/",
            
            # Container images
            "sfmImageUri": "975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:latest",
            "gaussianImageUri": "975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest", 
            "compressorImageUri": "975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor:latest",
            
            # Training parameters for 3DGS
            "max_iterations": "10000",
            "min_iterations": "1000", 
            "target_psnr": "25.0",
            "plateau_patience": "500",
            "psnr_plateau_termination": "true",
            "learning_rate": "0.0025",
            "log_interval": "100",
            "save_interval": "1000",
            "position_lr_scale": "1.0",
            "scaling_lr": "0.005",
            "rotation_lr": "0.001",
            "opacity_lr": "0.05",
            "feature_lr": "0.0025",
            "densification_interval": "100",
            "opacity_reset_interval": "3000",
            "densify_from_iter": "500",
            "densify_until_iter": "15000",
            "densify_grad_threshold": "0.0002",
            "percent_dense": "0.01",
            "lambda_dssim": "0.2",
            "sh_degree": "3",
            "progressive_resolution": "true",
            "optimization_enabled": "true"
        }
        
    def start_pipeline(self):
        """Start the Step Function execution"""
        input_data = self.create_modified_step_function_input()
        
        logger.info("🚀 Starting 3DGS → SOGS pipeline test")
        logger.info(f"📋 Job ID: {self.job_id}")
        logger.info(f"📋 Input data: {json.dumps(input_data, indent=2)}")
        
        response = self.stepfunctions.start_execution(
            stateMachineArn=self.state_machine_arn,
            name=self.job_id,
            input=json.dumps(input_data)
        )
        
        execution_arn = response['executionArn']
        logger.info(f"✅ Pipeline started successfully!")
        logger.info(f"📋 Execution ARN: {execution_arn}")
        
        return execution_arn
        
    def monitor_execution(self, execution_arn):
        """Monitor the Step Function execution"""
        logger.info("\n⏱️  MONITORING 3DGS → SOGS PIPELINE")
        logger.info("=" * 50)
        
        start_time = time.time()
        
        while True:
            response = self.stepfunctions.describe_execution(executionArn=execution_arn)
            status = response['status']
            
            elapsed_minutes = (time.time() - start_time) / 60
            logger.info(f"📊 [{elapsed_minutes:5.1f}m] Status: {status}")
            
            if status in ['SUCCEEDED', 'FAILED', 'ABORTED', 'TIMED_OUT']:
                logger.info(f"\n🏁 PIPELINE COMPLETED: {status}")
                logger.info(f"⏱️  Total Duration: {elapsed_minutes:.1f} minutes")
                
                # Log execution details if available
                if 'output' in response:
                    logger.info(f"📋 Output: {response['output']}")
                if 'error' in response:
                    logger.info(f"❌ Error: {response['error']}")
                if 'cause' in response:
                    logger.info(f"🔍 Cause: {response['cause']}")
                    
                return status, elapsed_minutes
                
            logger.info(f"⏳ [{elapsed_minutes:5.1f}m] Pipeline running... Status: {status}")
            time.sleep(30)  # Check every 30 seconds
            
    def validate_outputs(self):
        """Validate that both 3DGS and SOGS outputs were created"""
        logger.info("\n🔍 VALIDATING OUTPUTS")
        logger.info("=" * 30)
        
        # Check 3DGS outputs
        logger.info("📋 Checking 3DGS outputs...")
        response_3dgs = self.s3.list_objects_v2(
            Bucket=self.bucket,
            Prefix=f"jobs/{self.job_id}/3dgs/"
        )
        
        if 'Contents' in response_3dgs:
            logger.info(f"✅ 3DGS: {len(response_3dgs['Contents'])} files found")
            for obj in response_3dgs['Contents'][:5]:  # Show first 5 files
                size_mb = obj['Size'] / (1024 * 1024)
                logger.info(f"   - {obj['Key']} ({size_mb:.2f} MB)")
        else:
            logger.warning("❌ 3DGS: No output files found")
            
        # Check SOGS compression outputs
        logger.info("📋 Checking SOGS compression outputs...")
        response_sogs = self.s3.list_objects_v2(
            Bucket=self.bucket,
            Prefix=f"jobs/{self.job_id}/compressed/"
        )
        
        if 'Contents' in response_sogs:
            logger.info(f"✅ SOGS: {len(response_sogs['Contents'])} files found")
            for obj in response_sogs['Contents'][:5]:  # Show first 5 files
                size_mb = obj['Size'] / (1024 * 1024)
                logger.info(f"   - {obj['Key']} ({size_mb:.2f} MB)")
        else:
            logger.warning("❌ SOGS: No output files found")
            
        # Calculate scores
        has_3dgs = 'Contents' in response_3dgs and len(response_3dgs['Contents']) > 0
        has_sogs = 'Contents' in response_sogs and len(response_sogs['Contents']) > 0
        
        score = 0
        if has_3dgs:
            score += 50
        if has_sogs:
            score += 50
            
        logger.info(f"\n📊 OVERALL SCORE: {score}/100")
        
        return score, has_3dgs, has_sogs
        
    def run_test(self):
        """Run the complete 3DGS → SOGS test"""
        logger.info("🎯 3DGS → SOGS Pipeline Test")
        logger.info("=" * 50)
        logger.info("This test starts from 3DGS training and continues through SOGS compression")
        logger.info("Expected duration: 1.5-3 hours")
        logger.info("")
        
        try:
            # Step 1: Copy existing SfM output
            copied_files = self.copy_sfm_output()
            
            # Step 2: Start pipeline from 3DGS step
            execution_arn = self.start_pipeline()
            
            # Step 3: Monitor execution
            status, duration = self.monitor_execution(execution_arn)
            
            # Step 4: Validate outputs
            score, has_3dgs, has_sogs = self.validate_outputs()
            
            # Step 5: Final report
            logger.info("\n" + "=" * 80)
            logger.info("🎯 3DGS → SOGS TEST REPORT")
            logger.info("=" * 80)
            
            if status == 'SUCCEEDED':
                logger.info("✅ PIPELINE EXECUTION: SUCCESS")
            else:
                logger.info(f"❌ PIPELINE EXECUTION: {status}")
                
            logger.info(f"📊 OUTPUT SCORE: {score}/100")
            logger.info(f"   3DGS Outputs: {'✅' if has_3dgs else '❌'}")
            logger.info(f"   SOGS Outputs: {'✅' if has_sogs else '❌'}")
            logger.info(f"⏱️  Duration: {duration:.1f} minutes")
            logger.info(f"🔗 Execution ARN: {execution_arn}")
            
            if status == 'SUCCEEDED' and score >= 70:
                logger.info("\n🎉 SUCCESS: 3DGS → SOGS pipeline is working!")
                return True
            else:
                logger.info("\n❌ FAILURE: Pipeline needs debugging")
                logger.info("💡 Check CloudWatch logs for detailed error analysis")
                return False
                
        except Exception as e:
            logger.error(f"❌ Test failed with exception: {str(e)}")
            return False

def main():
    """Main test execution"""
    test = GaussianToSOGSTest()
    success = test.run_test()
    
    if success:
        print("\n🎉 3DGS → SOGS pipeline test PASSED!")
        exit(0)
    else:
        print("\n❌ 3DGS → SOGS pipeline test FAILED!")
        exit(1)

if __name__ == "__main__":
    main() 