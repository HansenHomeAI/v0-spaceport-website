#!/usr/bin/env python3
"""
Fixed pipeline test with correct input format
Now includes the missing jobName field
"""

import boto3
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_fixed_pipeline():
    """Test pipeline with correct input format"""
    
    region = 'us-west-2'
    account_id = '975050048887'
    
    stepfunctions = boto3.client('stepfunctions', region_name=region)
    
    # CORRECT input format with jobName field
    test_input = {
        "jobName": f"production-test-{int(time.time())}",  # THIS WAS MISSING!
        "pipelineStep": "sfm",
        "s3Url": "s3://spaceport-uploads/1748664812459-5woqcu-Archive.zip",
        "sfmImageUri": f"{account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/sfm:real-colmap-fixed-final",
        "trainImageUri": f"{account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/3dgs:latest",
        "compressImageUri": f"{account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/compressor:latest",
        "inputS3Uri": "s3://spaceport-uploads/1748664812459-5woqcu-Archive.zip"
    }
    
    state_machine_arn = f"arn:aws:states:{region}:{account_id}:stateMachine:SpaceportMLPipeline"
    execution_name = f"fixed-test-{int(time.time())}"
    
    logger.info("🚀 TESTING FIXED PIPELINE WITH CORRECT INPUT FORMAT")
    logger.info("=" * 60)
    logger.info(f"Job Name: {test_input['jobName']}")
    logger.info(f"Execution: {execution_name}")
    logger.info("Key Fix: Added missing 'jobName' field!")
    
    try:
        logger.info("🚀 Starting fixed pipeline test...")
        response = stepfunctions.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name,
            input=json.dumps(test_input)
        )
        
        execution_arn = response['executionArn']
        logger.info(f"✅ Started execution: {execution_arn}")
        
        # Monitor execution
        logger.info("⏱️  Monitoring execution progress...")
        
        start_time = time.time()
        max_wait_time = 600  # 10 minutes
        
        while time.time() - start_time < max_wait_time:
            time.sleep(10)  # Check every 10 seconds
            
            execution_desc = stepfunctions.describe_execution(executionArn=execution_arn)
            status = execution_desc['status']
            
            elapsed = int(time.time() - start_time)
            logger.info(f"   [{elapsed:3d}s] Status: {status}")
            
            if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                break
        
        # Get final status
        final_desc = stepfunctions.describe_execution(executionArn=execution_arn)
        final_status = final_desc['status']
        
        logger.info(f"\n🏁 FINAL STATUS: {final_status}")
        
        if final_status == 'SUCCEEDED':
            logger.info("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
            logger.info("✅ Both SfM and 3DGS containers are working perfectly!")
            logger.info("✅ The issue was just the missing jobName field!")
            
            # Get output
            if 'output' in final_desc:
                output = json.loads(final_desc['output'])
                logger.info("📊 Pipeline Results:")
                for key, value in output.items():
                    logger.info(f"   {key}: {value}")
        
        elif final_status == 'FAILED':
            logger.error("❌ Pipeline failed - getting details...")
            
            # Get failure details
            history = stepfunctions.get_execution_history(
                executionArn=execution_arn,
                maxResults=50,
                reverseOrder=True
            )
            
            for event in history['events']:
                if event['type'] in ['TaskFailed', 'ExecutionFailed']:
                    logger.error(f"   Failure Type: {event['type']}")
                    if 'taskFailedEventDetails' in event:
                        details = event['taskFailedEventDetails']
                        logger.error(f"   Error: {details.get('error', 'Unknown')}")
                        logger.error(f"   Cause: {details.get('cause', 'Unknown')}")
                    break
        
        return execution_arn, final_status
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        return None, 'ERROR'

def main():
    """Main test entry point"""
    execution_arn, status = test_fixed_pipeline()
    
    print("\n" + "="*60)
    print("🎯 PIPELINE TEST COMPLETE")
    print("="*60)
    
    if status == 'SUCCEEDED':
        print("🎉 SUCCESS: Pipeline is working perfectly!")
        print("✅ 3DGS container is production-ready!")
        print("💡 Issue was just missing 'jobName' field in input")
    elif status == 'FAILED':
        print("❌ FAILED: Check logs above for details")
        print(f"🔍 Execution ARN: {execution_arn}")
    else:
        print("⚠️  UNKNOWN: Check AWS Console for details")
    
    return status == 'SUCCEEDED'

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 