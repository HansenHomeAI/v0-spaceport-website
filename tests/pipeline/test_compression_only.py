#!/usr/bin/env python3
"""
Compression-Only Pipeline Test
==============================
Test ONLY the compression stage using pre-existing 3DGS model data.
This allows rapid iteration on compression parameters without waiting for SfM/3DGS.
"""

import boto3
import json
import time
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CompressionOnlyTester:
    def __init__(self, region='us-west-2'):
        self.region = region
        self.account_id = '975050048887'
        self.stepfunctions = boto3.client('stepfunctions', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        
        # Step Functions ARN
        self.state_machine_arn = f"arn:aws:states:{region}:{self.account_id}:stateMachine:SpaceportMLPipeline"
        
        # Use successful 3DGS output from our previous test
        self.source_job_id = "3dgs-only-1750999715"  # Our successful 3DGS run
        
    def start_compression_only_test(self) -> Tuple[str, str]:
        """Start a compression-only test using existing 3DGS model data."""
        
        # Generate unique job ID
        job_id = f"compression-only-{int(time.time())}"
        
        logger.info("🗜️ COMPRESSION-ONLY PIPELINE TEST")
        logger.info("=" * 50)
        logger.info(f"Source 3DGS Job: {self.source_job_id}")
        logger.info(f"Compression Job ID: {job_id}")
        logger.info("")
        
        # Verify source 3DGS model exists
        source_key = f"jobs/{self.source_job_id}/gaussian/3dgs-only-3dgs-only-1750999715-3dgs/output/model.tar.gz"
        try:
            response = self.s3.head_object(Bucket='spaceport-ml-pipeline', Key=source_key)
            model_size = response['ContentLength']
            logger.info(f"✅ Source 3DGS model found: {model_size} bytes")
        except Exception as e:
            logger.error(f"❌ Source 3DGS model not found: {e}")
            return None, None
        
        # Step Functions input for compression-only pipeline
        input_data = {
            "jobId": job_id,
            "jobName": f"compression-only-{job_id}",  # Step Functions expects jobName
            "pipelineStep": "compression",  # Start directly from compression
            
            # Point to existing 3DGS model
            "gaussianModelUri": f"s3://spaceport-ml-pipeline/{source_key}",
            "gaussianOutputS3Uri": f"s3://spaceport-ml-pipeline/{source_key}",  # Expected by compression stage
            "compressedOutputS3Uri": f"s3://spaceport-ml-pipeline/jobs/{job_id}/compression/",
            
            # Compression parameters
            "compressionLevel": 0.8,  # High compression
            "qualityTarget": 0.9,    # Maintain 90% quality
            "maxFileSize": 50,       # Max 50MB output
            "optimizeForWeb": True,  # Web delivery optimization
            
            # Debugging parameters
            "debugMode": True,
            "verboseLogging": True
        }
        
        try:
            # Start Step Functions execution
            response = self.stepfunctions.start_execution(
                stateMachineArn=self.state_machine_arn,
                name=job_id,
                input=json.dumps(input_data)
            )
            
            execution_arn = response['executionArn']
            logger.info(f"✅ Compression test started successfully!")
            logger.info(f"📋 Execution ARN: {execution_arn}")
            logger.info("")
            
            return job_id, execution_arn
            
        except Exception as e:
            logger.error(f"❌ Failed to start compression test: {e}")
            return None, None
    
    def monitor_execution(self, execution_arn: str, job_id: str) -> str:
        """Monitor the compression execution until completion."""
        
        logger.info("⏱️  MONITORING COMPRESSION EXECUTION")
        logger.info("=" * 40)
        
        start_time = time.time()
        
        while True:
            try:
                response = self.stepfunctions.describe_execution(
                    executionArn=execution_arn
                )
                
                status = response['status']
                elapsed = (time.time() - start_time) / 60  # minutes
                
                logger.info(f"📊 [{elapsed:5.1f}m] Status: {status}")
                
                if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                    logger.info("")
                    logger.info(f"🏁 COMPRESSION COMPLETED: {status}")
                    logger.info(f"⏱️  Total Duration: {elapsed:.1f} minutes")
                    logger.info("")
                    return status
                
                logger.info(f"⏳ [{elapsed:5.1f}m] Compression running... Status: {status}")
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Error monitoring execution: {e}")
                break
        
        return "ERROR"
    
    def analyze_compression_output(self, job_id: str) -> Dict:
        """Analyze compression output and quality."""
        
        logger.info("🔍 ANALYZING COMPRESSION OUTPUT")
        logger.info("=" * 35)
        
        try:
            # List compression output files
            prefix = f"jobs/{job_id}/compression/"
            response = self.s3.list_objects_v2(
                Bucket='spaceport-ml-pipeline',
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                logger.warning("❌ No compression output files found")
                return {"success": False, "files": 0, "total_size": 0}
            
            files = response['Contents']
            total_size = sum(f['Size'] for f in files)
            
            logger.info(f"✅ Compression output: {len(files)} files, {total_size/1024/1024:.2f} MB")
            
            # Show key files
            for file in files[:5]:  # Show first 5 files
                size_mb = file['Size'] / 1024 / 1024
                logger.info(f"   - {file['Key'].split('/')[-1]} ({size_mb:.2f} MB)")
            
            if len(files) > 5:
                logger.info(f"   ... and {len(files) - 5} more files")
            
            return {
                "success": True,
                "files": len(files),
                "total_size": total_size,
                "files_list": [f['Key'] for f in files]
            }
            
        except Exception as e:
            logger.error(f"❌ Error analyzing compression output: {e}")
            return {"success": False, "error": str(e)}
    
    def get_compression_logs(self, job_id: str) -> None:
        """Get CloudWatch logs for compression job debugging."""
        
        logger.info("📋 COMPRESSION LOGS ANALYSIS")
        logger.info("=" * 30)
        
        try:
            # Get SageMaker processing job logs
            logs_client = boto3.client('logs', region_name=self.region)
            
            # Find log group for this job
            log_group = "/aws/sagemaker/ProcessingJobs"
            
            # List log streams for this job
            response = logs_client.describe_log_streams(
                logGroupName=log_group,
                logStreamNamePrefix=f"compression-only-{job_id}",
                orderBy='LastEventTime',
                descending=True,
                limit=5
            )
            
            if not response['logStreams']:
                logger.warning("❌ No compression log streams found")
                return
            
            # Get logs from the most recent stream
            log_stream = response['logStreams'][0]['logStreamName']
            logger.info(f"📋 Log stream: {log_stream}")
            
            log_response = logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=log_stream,
                limit=50,
                startFromHead=False  # Get latest logs
            )
            
            logger.info("🔍 Recent compression logs:")
            for event in log_response['events'][-20:]:  # Last 20 log entries
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].strip()
                logger.info(f"   {timestamp.strftime('%H:%M:%S')} | {message}")
                
        except Exception as e:
            logger.error(f"❌ Error getting compression logs: {e}")

def main():
    """Run compression-only test."""
    
    tester = CompressionOnlyTester()
    
    # Start compression test
    job_id, execution_arn = tester.start_compression_only_test()
    
    if not job_id:
        logger.error("❌ Failed to start compression test")
        return
    
    # Monitor execution
    final_status = tester.monitor_execution(execution_arn, job_id)
    
    # Analyze results
    output_analysis = tester.analyze_compression_output(job_id)
    
    # Get logs for debugging
    tester.get_compression_logs(job_id)
    
    # Final summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("🎯 COMPRESSION TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Job ID: {job_id}")
    logger.info(f"Status: {final_status}")
    logger.info(f"Output Files: {output_analysis.get('files', 0)}")
    logger.info(f"Total Size: {output_analysis.get('total_size', 0)/1024/1024:.2f} MB")
    
    if final_status == 'SUCCEEDED' and output_analysis.get('success'):
        logger.info("✅ COMPRESSION TEST PASSED")
    else:
        logger.info("❌ COMPRESSION TEST FAILED - Check logs above for details")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    main() 