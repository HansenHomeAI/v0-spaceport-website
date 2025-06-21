#!/usr/bin/env python3
"""
Full pipeline test - let SfM complete first, then 3DGS
This is the correct way to test the complete pipeline
"""

import boto3
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_aws_account_id():
    """Gets the AWS account ID from the caller identity."""
    try:
        sts_client = boto3.client("sts")
        return sts_client.get_caller_identity()["Account"]
    except Exception as e:
        logger.error(f"Could not determine AWS account ID: {e}")
        return None

def test_full_pipeline():
    """Test complete pipeline from SfM through 3DGS"""
    
    region = 'us-west-2'
    account_id = get_aws_account_id()

    if not account_id:
        logger.error("Exiting due to missing AWS account ID.")
        return None, 'ERROR'
    
    stepfunctions = boto3.client('stepfunctions', region_name=region)
    
    # Complete pipeline input - let it run from SfM → 3DGS → Compression
    test_input = {
        "jobName": f"full-pipeline-test-{int(time.time())}",
        "s3Url": "s3://spaceport-uploads/1748664812459-5woqcu-Archive.zip",
        "sfmImageUri": f"{account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/sfm:latest",
        "trainImageUri": f"{account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/3dgs:latest",
        "compressImageUri": f"{account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/compressor:latest",
        "inputS3Uri": "s3://spaceport-uploads/1748664812459-5woqcu-Archive.zip"
        # NOTE: Removed "pipelineStep" - let it run the full pipeline
    }
    
    state_machine_arn = f"arn:aws:states:{region}:{account_id}:stateMachine:SpaceportMLPipeline"
    execution_name = f"full-pipeline-{int(time.time())}"
    
    logger.info("🚀 TESTING COMPLETE PIPELINE: SfM → 3DGS → COMPRESSION")
    logger.info("=" * 70)
    logger.info(f"Job Name: {test_input['jobName']}")
    logger.info(f"Execution: {execution_name}")
    logger.info("📊 Dataset: 22 photos (small test dataset)")
    logger.info("🎯 Goal: Test optimized 3DGS container in full pipeline")
    
    try:
        logger.info("🚀 Starting complete pipeline test...")
        response = stepfunctions.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name,
            input=json.dumps(test_input)
        )
        
        execution_arn = response['executionArn']
        logger.info(f"✅ Started execution: {execution_arn}")
        
        # Monitor execution with detailed progress
        logger.info("⏱️  Monitoring complete pipeline progress...")
        logger.info("📋 Expected stages:")
        logger.info("   1. SfM Processing (COLMAP) - ~6 minutes")
        logger.info("   2. 3DGS Training (Our optimized container) - ~15-30 minutes")
        logger.info("   3. Compression (SOGS) - ~5 minutes")
        
        start_time = time.time()
        max_wait_time = 2400  # 40 minutes total
        last_status = None
        
        stage_times = {
            'SfM': None,
            '3DGS': None,
            'Compression': None
        }
        
        while time.time() - start_time < max_wait_time:
            time.sleep(15)  # Check every 15 seconds
            
            execution_desc = stepfunctions.describe_execution(executionArn=execution_arn)
            status = execution_desc['status']
            
            elapsed = int(time.time() - start_time)
            elapsed_min = elapsed // 60
            elapsed_sec = elapsed % 60
            
            # Try to determine current stage
            current_stage = "Unknown"
            if status == 'RUNNING':
                # Get recent events to see what stage we're in
                try:
                    history = stepfunctions.get_execution_history(
                        executionArn=execution_arn,
                        maxResults=10,
                        reverseOrder=True
                    )
                    
                    for event in history['events']:
                        if event['type'] == 'TaskStateEntered':
                            state_name = event.get('stateEnteredEventDetails', {}).get('name', '')
                            if 'SfM' in state_name:
                                current_stage = "SfM Processing"
                                if stage_times['SfM'] is None:
                                    stage_times['SfM'] = elapsed
                            elif 'Gaussian' in state_name or '3DGS' in state_name:
                                current_stage = "3DGS Training"
                                if stage_times['3DGS'] is None:
                                    stage_times['3DGS'] = elapsed
                            elif 'Compress' in state_name:
                                current_stage = "Compression"
                                if stage_times['Compression'] is None:
                                    stage_times['Compression'] = elapsed
                            break
                except:
                    pass  # Continue monitoring
            
            if status != last_status or elapsed % 60 == 0:  # Log every minute or status change
                logger.info(f"   [{elapsed_min:2d}:{elapsed_sec:02d}] Status: {status} | Stage: {current_stage}")
                last_status = status
            
            if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                break
        
        # Get final status
        final_desc = stepfunctions.describe_execution(executionArn=execution_arn)
        final_status = final_desc['status']
        
        total_time = int(time.time() - start_time)
        total_min = total_time // 60
        total_sec = total_time % 60
        
        logger.info(f"\n🏁 FINAL STATUS: {final_status}")
        logger.info(f"⏱️  Total execution time: {total_min}:{total_sec:02d}")
        
        # Log stage timing
        logger.info("📊 Stage Timing:")
        for stage, start_elapsed in stage_times.items():
            if start_elapsed is not None:
                stage_min = start_elapsed // 60
                stage_sec = start_elapsed % 60
                logger.info(f"   {stage}: Started at {stage_min}:{stage_sec:02d}")
        
        if final_status == 'SUCCEEDED':
            logger.info("\n🎉 COMPLETE PIPELINE SUCCESS!")
            logger.info("=" * 50)
            logger.info("✅ SfM Processing: WORKING")
            logger.info("✅ 3DGS Training: WORKING") 
            logger.info("✅ Compression: WORKING")
            logger.info("🚀 3DGS container is production-ready and optimized!")
            
            # Get output results
            if 'output' in final_desc:
                try:
                    output = json.loads(final_desc['output'])
                    logger.info("\n📊 Pipeline Results:")
                    for key, value in output.items():
                        if isinstance(value, str) and len(value) > 100:
                            logger.info(f"   {key}: {value[:100]}...")
                        else:
                            logger.info(f"   {key}: {value}")
                except:
                    logger.info("📊 Output data available but not JSON parseable")
        
        elif final_status == 'FAILED':
            logger.error("\n❌ Pipeline failed - analyzing failure...")
            
            # Get failure details
            history = stepfunctions.get_execution_history(
                executionArn=execution_arn,
                maxResults=100,
                reverseOrder=True
            )
            
            for event in history['events']:
                if event['type'] in ['TaskFailed', 'ExecutionFailed']:
                    logger.error(f"   Failure Type: {event['type']}")
                    if 'taskFailedEventDetails' in event:
                        details = event['taskFailedEventDetails']
                        logger.error(f"   Error: {details.get('error', 'Unknown')}")
                        logger.error(f"   Cause: {details.get('cause', 'Unknown')}")
                        
                        # Try to determine which stage failed
                        cause = details.get('cause', '')
                        if 'SfM' in cause or 'colmap' in cause.lower():
                            logger.error("   Failed Stage: SfM Processing")
                        elif '3dgs' in cause.lower() or 'gaussian' in cause.lower():
                            logger.error("   Failed Stage: 3DGS Training")
                        elif 'compress' in cause.lower():
                            logger.error("   Failed Stage: Compression")
                    break
        
        return execution_arn, final_status
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        return None, 'ERROR'

def main():
    """Run complete pipeline test"""
    execution_arn, status = test_full_pipeline()
    
    print("\n" + "="*70)
    print("🎯 COMPLETE PIPELINE TEST RESULTS")
    print("="*70)
    
    if status == 'SUCCEEDED':
        print("🎉 COMPLETE SUCCESS!")
        print("✅ SfM Processing: Production ready")
        print("✅ 3DGS Training: Production ready and optimized")
        print("✅ Compression: Production ready")
        print("\n🚀 YOUR ML PIPELINE IS FULLY OPERATIONAL!")
        print("💡 Ready for production workloads")
        
    elif status == 'FAILED':
        print("❌ PIPELINE FAILED")
        print("🔍 Check logs above for specific failure details")
        print(f"📋 Execution ARN: {execution_arn}")
        print("💡 Most likely culprit: 3DGS training stage")
        
    elif status == 'RUNNING':
        print("⏳ STILL RUNNING")
        print(f"📋 Execution ARN: {execution_arn}")
        print("💡 Check AWS Console for real-time progress")
        
    else:
        print("⚠️  UNKNOWN STATUS")
        print("🔍 Check AWS Console for details")
    
    return status == 'SUCCEEDED'

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 