#!/usr/bin/env python3
"""Full pipeline test with GPS flight path CSV data.
Starts at SfM (OpenSfM GPS-enhanced) and runs through 3DGS → Compression.
This validates the end-to-end pipeline with pasted CSV data supplied via the
`csvData` field of the Start-ML-Job Lambda/API.
"""

import boto3
import json
import time
import logging
from textwrap import dedent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants – update if stack changes
REGION = "us-west-2"
ACCOUNT_ID = "975050048887"
START_JOB_LAMBDA = "Spaceport-StartMLJob"  # Name set in CDK stack
STATE_MACHINE_ARN = f"arn:aws:states:{REGION}:{ACCOUNT_ID}:stateMachine:SpaceportMLPipeline"

# Test inputs
S3_URL = "s3://spaceport-uploads/1751413909023-l2zkyj-Battery-1.zip"
CSV_DATA = dedent(
    """latitude,longitude,altitude(ft),heading(deg),curvesize(ft),rotationdir,gimbalmode,gimbalpitchangle,altitudemode,speed(m/s),poi_latitude,poi_longitude,poi_altitude(ft),poi_altitudemode,photo_timeinterval,photo_distinterval
41.73272,-111.83423,130.0,249,14.48,0,2,-35,0,8.85,41.73231,-111.83423,-35,0,3.0,0
41.73256,-111.83481,141.91,189,81.87,0,2,-33,0,8.85,41.73231,-111.83423,-35,0,3.0,0
41.73201,-111.83493,156.09,351,15.54,0,2,-31,0,8.85,41.73231,-111.83423,-35,0,3.0,0
41.73268,-111.83508,173.61,51,113.2,0,2,-29,0,8.85,41.73231,-111.83423,-35,0,3.0,0
41.7332,-111.83423,194.46,250,17.13,0,2,-27,0,8.85,41.73231,-111.83423,-35,0,3.0,0
41.73286,-111.83547,230.78,190,158.77,0,2,-26,0,8.85,41.73231,-111.83423,-35,0,3.0,0
41.73166,-111.83574,253.32,351,19.45,0,2,-24,0,8.85,41.73231,-111.83423,-35,0,3.0,0
41.73312,-111.83606,294.37,51,226.98,0,2,-23,0,8.85,41.73231,-111.83423,-35,0,3.0,0
41.73423,-111.83423,333.77,249,22.86,0,2,-22,0,8.85,41.73231,-111.83423,-35,0,3.0,0
41.73346,-111.83695,386.98,189,326.56,0,2,-22,0,8.85,41.73231,-111.83423,-35,0,3.0,0
"""
).strip()
TEST_EMAIL = "gbhbyu@gmail.com"

# Polling configuration
POLL_INTERVAL = 30          # seconds between status checks
MAX_WAIT_SECONDS = 7200     # 2 hours – adjust if needed


def start_pipeline() -> str:
    """Invoke the Start-ML-Job Lambda with the test inputs and return executionArn."""

    lambda_client = boto3.client("lambda", region_name=REGION)

    payload = {
        "body": json.dumps({
            "s3Url": S3_URL,
            "email": TEST_EMAIL,
            "pipelineStep": "sfm",
            "csvData": CSV_DATA
        })
    }

    logger.info("🚀 Invoking Start-ML-Job Lambda ...")
    response = lambda_client.invoke(
        FunctionName=START_JOB_LAMBDA,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8")
    )

    resp_payload = json.loads(response["Payload"].read())
    logger.info(f"🔍 Lambda response: {json.dumps(resp_payload, indent=2)}")
    
    if response.get("FunctionError"):
        raise RuntimeError(f"Lambda error: {resp_payload}")

    body = resp_payload.get("body")
    if isinstance(body, str):
        body = json.loads(body)
    
    logger.info(f"🔍 Parsed body: {json.dumps(body, indent=2)}")

    job_id = body["jobId"]
    execution_arn = body["executionArn"]
    logger.info(f"✅ Started job {job_id}")
    logger.info(f"   Execution ARN: {execution_arn}")
    return execution_arn


def wait_for_completion(execution_arn: str) -> str:
    """Poll Step Functions until execution completes or fails. Returns final status."""
    sfn = boto3.client("stepfunctions", region_name=REGION)
    start_time = time.time()
    last_status = None

    while True:
        desc = sfn.describe_execution(executionArn=execution_arn)
        status = desc["status"]
        if status != last_status:
            logger.info(f"Status → {status}")
            last_status = status
        if status in {"SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"}:
            return status
        if time.time() - start_time > MAX_WAIT_SECONDS:
            raise TimeoutError("Pipeline timed out waiting for completion")
        time.sleep(POLL_INTERVAL)


def test_full_pipeline_with_gps():
    """Pytest entrypoint."""
    execution_arn = start_pipeline()
    final_status = wait_for_completion(execution_arn)
    assert final_status == "SUCCEEDED", f"Pipeline failed with status {final_status} – see Step Functions execution for details"


if __name__ == "__main__":
    """Run the test directly with verbose output when executed as a script."""
    logger.info("🧪 Starting GPS-Enhanced OpenSfM Pipeline Test")
    logger.info(f"📍 Test Data: {S3_URL}")
    logger.info(f"📧 Email: {TEST_EMAIL}")
    logger.info(f"🗺️ GPS Data: {len(CSV_DATA.split(chr(10)))} waypoints")
    
    try:
        execution_arn = start_pipeline()
        logger.info(f"⏳ Polling every {POLL_INTERVAL} seconds (max {MAX_WAIT_SECONDS/60:.0f} minutes)...")
        final_status = wait_for_completion(execution_arn)
        
        if final_status == "SUCCEEDED":
            logger.info("🎉 Pipeline completed successfully!")
            logger.info("✅ GPS-enhanced OpenSfM → 3DGS → Compression pipeline working!")
        else:
            logger.error(f"❌ Pipeline failed with status: {final_status}")
            logger.error("🔍 Check Step Functions execution in AWS Console for detailed logs")
            exit(1)
            
    except Exception as e:
        logger.error(f"💥 Test failed with exception: {e}")
        exit(1) 