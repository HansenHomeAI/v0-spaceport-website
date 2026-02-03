#!/usr/bin/env python3
"""Full pipeline test using EXIF-only GPS priors.
Starts at SfM (OpenSfM EXIF-enhanced) and runs through 3DGS → Compression.
This validates the end-to-end pipeline without any CSV priors.
"""

import boto3
import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants – update if stack changes
REGION = "us-west-2"
ACCOUNT_ID = "975050048887"
START_JOB_LAMBDA = "Spaceport-StartMLJob-staging"  # Staging environment
STATE_MACHINE_ARN = f"arn:aws:states:{REGION}:{ACCOUNT_ID}:stateMachine:SpaceportMLPipeline-staging"

# Test inputs
S3_URL = "s3://spaceport-ml-processing/test-data/1751413909023-l2zkyj-Battery-1.zip"
TEST_EMAIL = "gbhbyu@gmail.com"

# Hyperparameter tuning configuration
# These values override the defaults in the Lambda for experimentation
EXPERIMENTAL_HYPERPARAMETERS = {
    # Example: High-detail configuration
    "sh_degree": 3,                    # Maximum spherical harmonics for photorealistic results
    "densify_grad_threshold": 0.0001,  # More sensitive densification = higher detail
    "max_iterations": 25000,           # Slightly reduced for faster testing
    "lambda_dssim": 0.3,              # Higher SSIM weight for better texture preservation
    "target_psnr": 32.0,              # Reasonable quality target for testing
    
    # Example: Fast testing configuration (uncomment to use)
    # "max_iterations": 5000,
    # "densify_grad_threshold": 0.0005,
    # "sh_degree": 1,
    # "target_psnr": 28.0,
}

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
            "hyperparameters": EXPERIMENTAL_HYPERPARAMETERS
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
    cycle = 0

    while True:
        desc = sfn.describe_execution(executionArn=execution_arn)
        status = desc["status"]
        cycle += 1

        # Always log the poll cycle and status
        elapsed = time.time() - start_time
        logger.info(f"⏲️  Poll #{cycle} – {elapsed/60:.1f} min elapsed – Status: {status}")

        # Log only when status changes for detailed updates
        if status != last_status:
            logger.info(f"Status changed → {status}")
            last_status = status

        if status in {"SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"}:
            return status
        if elapsed > MAX_WAIT_SECONDS:
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
    logger.info(f"🎛️ Hyperparameters: {json.dumps(EXPERIMENTAL_HYPERPARAMETERS, indent=2)}")
    
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
