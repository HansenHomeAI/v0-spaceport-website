#!/usr/bin/env python3
"""
Test script to diagnose current ML pipeline issues
Focus on understanding what's failing in the 3DGS stage
"""

import boto3
import json
import time
import logging
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PipelineDiagnostics:
    """Diagnose ML pipeline issues"""
    
    def __init__(self):
        self.region = 'us-west-2'
        self.account_id = '975050048887'
        self.stepfunctions = boto3.client('stepfunctions', region_name=self.region)
        self.sagemaker = boto3.client('sagemaker', region_name=self.region)
        self.ecr = boto3.client('ecr', region_name=self.region)
        
    def check_recent_executions(self):
        """Check recent Step Functions executions"""
        logger.info("🔍 Checking recent Step Functions executions...")
        
        state_machine_arn = f"arn:aws:states:{self.region}:{self.account_id}:stateMachine:SpaceportMLPipeline"
        
        try:
            response = self.stepfunctions.list_executions(
                stateMachineArn=state_machine_arn,
                statusFilter='FAILED',
                maxResults=5
            )
            
            executions = response.get('executions', [])
            logger.info(f"📊 Found {len(executions)} recent failed executions")
            
            if executions:
                latest_execution = executions[0]
                execution_arn = latest_execution['executionArn']
                logger.info(f"🔍 Analyzing latest failed execution: {latest_execution['name']}")
                
                # Get execution history
                history = self.stepfunctions.get_execution_history(
                    executionArn=execution_arn,
                    maxResults=50,
                    reverseOrder=True
                )
                
                # Find failure details
                for event in history['events']:
                    if event['type'] in ['TaskFailed', 'ExecutionFailed']:
                        logger.error(f"❌ Failure Type: {event['type']}")
                        if 'taskFailedEventDetails' in event:
                            details = event['taskFailedEventDetails']
                            logger.error(f"   Error: {details.get('error', 'Unknown')}")
                            logger.error(f"   Cause: {details.get('cause', 'Unknown')}")
                        break
                
                return execution_arn
            else:
                logger.info("✅ No recent failed executions found")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error checking executions: {str(e)}")
            return None
    
    def check_training_jobs(self):
        """Check recent SageMaker training jobs"""
        logger.info("🔍 Checking recent SageMaker training jobs...")
        
        try:
            response = self.sagemaker.list_training_jobs(
                SortBy='CreationTime',
                SortOrder='Descending',
                MaxResults=10
            )
            
            jobs = response.get('TrainingJobSummaries', [])
            logger.info(f"📊 Found {len(jobs)} recent training jobs")
            
            for job in jobs:
                job_name = job['TrainingJobName']
                status = job['TrainingJobStatus']
                creation_time = job['CreationTime']
                
                logger.info(f"   📋 {job_name}: {status} ({creation_time})")
                
                if status == 'Failed':
                    # Get detailed failure information
                    details = self.sagemaker.describe_training_job(TrainingJobName=job_name)
                    failure_reason = details.get('FailureReason', 'Unknown')
                    logger.error(f"      ❌ Failure: {failure_reason}")
                    
                    return job_name
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error checking training jobs: {str(e)}")
            return None
    
    def check_container_images(self):
        """Check available container images"""
        logger.info("🔍 Checking ECR container images...")
        
        repositories = ['spaceport/sfm', 'spaceport/3dgs', 'spaceport/compressor']
        
        for repo in repositories:
            try:
                response = self.ecr.list_images(repositoryName=repo)
                images = response.get('imageIds', [])
                
                tagged_images = [img for img in images if 'imageTag' in img]
                logger.info(f"📦 {repo}: {len(tagged_images)} tagged images")
                
                if tagged_images:
                    for img in tagged_images[:3]:  # Show first 3
                        tag = img.get('imageTag', 'untagged')
                        logger.info(f"      - {tag}")
                else:
                    logger.warning(f"⚠️  {repo}: No tagged images found")
                    
            except Exception as e:
                logger.error(f"❌ Error checking {repo}: {str(e)}")
    
    def test_simple_pipeline(self):
        """Test a simple pipeline execution"""
        logger.info("🧪 Testing a simple pipeline execution...")
        
        test_input = {
            "pipelineStep": "sfm",
            "s3Url": "s3://spaceport-uploads/1748664812459-5woqcu-Archive.zip",
            "sfmImageUri": f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/spaceport/sfm:real-colmap-fixed-final",
            "trainImageUri": f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/spaceport/3dgs:latest",
            "compressImageUri": f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/spaceport/compressor:latest",
            "inputS3Uri": "s3://spaceport-uploads/1748664812459-5woqcu-Archive.zip"
        }
        
        state_machine_arn = f"arn:aws:states:{self.region}:{self.account_id}:stateMachine:SpaceportMLPipeline"
        execution_name = f"diagnostic-test-{int(time.time())}"
        
        try:
            logger.info(f"🚀 Starting test execution: {execution_name}")
            response = self.stepfunctions.start_execution(
                stateMachineArn=state_machine_arn,
                name=execution_name,
                input=json.dumps(test_input)
            )
            
            execution_arn = response['executionArn']
            logger.info(f"✅ Started execution: {execution_arn}")
            
            # Monitor for a short time
            logger.info("⏱️  Monitoring execution for 30 seconds...")
            for i in range(6):  # 30 seconds total
                time.sleep(5)
                
                execution_desc = self.stepfunctions.describe_execution(executionArn=execution_arn)
                status = execution_desc['status']
                
                logger.info(f"   Status: {status}")
                
                if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                    break
            
            # Get final status
            final_desc = self.stepfunctions.describe_execution(executionArn=execution_arn)
            final_status = final_desc['status']
            
            logger.info(f"🏁 Final status: {final_status}")
            
            if final_status == 'FAILED':
                # Get failure details
                history = self.stepfunctions.get_execution_history(
                    executionArn=execution_arn,
                    maxResults=20,
                    reverseOrder=True
                )
                
                for event in history['events']:
                    if event['type'] in ['TaskFailed', 'ExecutionFailed']:
                        logger.error(f"❌ Test Failure: {event['type']}")
                        if 'taskFailedEventDetails' in event:
                            details = event['taskFailedEventDetails']
                            logger.error(f"   Error: {details.get('error', 'Unknown')}")
                            logger.error(f"   Cause: {details.get('cause', 'Unknown')}")
                        break
            
            return execution_arn
            
        except Exception as e:
            logger.error(f"❌ Test execution failed: {str(e)}")
            return None
    
    def run_diagnostics(self):
        """Run full diagnostics"""
        logger.info("🔧 SPACEPORT ML PIPELINE DIAGNOSTICS")
        logger.info("=" * 50)
        
        # Check recent failures
        self.check_recent_executions()
        print()
        
        # Check training jobs
        self.check_training_jobs()
        print()
        
        # Check containers
        self.check_container_images()
        print()
        
        # Test simple execution
        execution_arn = self.test_simple_pipeline()
        
        logger.info("\n🎯 DIAGNOSTICS COMPLETE")
        logger.info("=" * 30)
        
        if execution_arn:
            logger.info(f"💡 Test execution created: {execution_arn}")
            logger.info("   Check AWS Console for detailed logs")
        
        return execution_arn

def main():
    """Main diagnostics entry point"""
    diagnostics = PipelineDiagnostics()
    return diagnostics.run_diagnostics()

if __name__ == "__main__":
    main() 