import json
import boto3
import os
import re
import uuid
from datetime import datetime
from urllib.parse import urlparse

# Initialize AWS clients
stepfunctions = boto3.client('stepfunctions')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    Lambda function to start ML processing pipeline
    Expects: { "s3Url": "https://spaceport-uploads.s3.amazonaws.com/..." }
    Returns: { "jobId": "...", "executionArn": "..." }
    """
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
            
        s3_url = body.get('s3Url')
        email = body.get('email', 'noreply@hansenhome.ai')  # Optional email for notifications
        
        if not s3_url:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Missing required field: s3Url'
                })
            }
        
        # Validate S3 URL format
        if not validate_s3_url(s3_url):
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Invalid S3 URL format'
                })
            }
        
        # Parse S3 URL to get bucket and key
        bucket_name, object_key = parse_s3_url(s3_url)
        
        # Verify the object exists
        try:
            s3.head_object(Bucket=bucket_name, Key=object_key)
        except s3.exceptions.NoSuchKey:
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'S3 object not found'
                })
            }
        except Exception as e:
            return {
                'statusCode': 403,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'error': f'Cannot access S3 object: {str(e)}'
                })
            }
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        job_name = f"ml-job-{timestamp}-{job_id[:8]}"
        
        # Get environment variables
        state_machine_arn = os.environ['STATE_MACHINE_ARN']
        ml_bucket = os.environ['ML_BUCKET']
        
        # Get ECR repository URIs (these would be set during deployment)
        account_id = context.invoked_function_arn.split(':')[4]
        region = context.invoked_function_arn.split(':')[3]
        
        sfm_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/sfm:cuda-disabled"
        gaussian_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/3dgs:latest"
        compressor_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/compressor:latest"
        
        # Prepare Step Functions input
        step_function_input = {
            "jobId": job_id,
            "jobName": job_name,
            "s3Url": s3_url,
            "email": email,
            "inputS3Uri": f"s3://{bucket_name}/{object_key}",
            "colmapOutputS3Uri": f"s3://{ml_bucket}/colmap/{job_id}/",
            "gaussianOutputS3Uri": f"s3://{ml_bucket}/3dgs/{job_id}/",
            "compressedOutputS3Uri": f"s3://{ml_bucket}/compressed/{job_id}/",
            "sfmImageUri": sfm_image_uri,
            "gaussianImageUri": gaussian_image_uri,
            "compressorImageUri": compressor_image_uri,
            "sfmArgs": ["--input", "/opt/ml/processing/input", "--output", "/opt/ml/processing/output"],
            "compressionArgs": ["--input", "/opt/ml/processing/input", "--output", "/opt/ml/processing/output"]
        }
        
        # Start Step Functions execution
        response = stepfunctions.start_execution(
            stateMachineArn=state_machine_arn,
            name=f"execution-{job_id}",
            input=json.dumps(step_function_input)
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'jobId': job_id,
                'executionArn': response['executionArn'],
                'message': 'ML processing job started successfully'
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }


def validate_s3_url(url):
    """
    Validate S3 URL format
    Accepts: 
    - s3://bucket-name/key
    - https://bucket-name.s3.amazonaws.com/key 
    - https://s3.amazonaws.com/bucket-name/key
    """
    # S3 protocol format
    s3_protocol_pattern = r'^s3://([a-z0-9.-]+)/(.+)$'
    # HTTPS format
    https_pattern = r'^https://(?:([a-z0-9.-]+)\.s3\.amazonaws\.com/(.+)|s3\.amazonaws\.com/([a-z0-9.-]+)/(.+))$'
    
    return re.match(s3_protocol_pattern, url) is not None or re.match(https_pattern, url) is not None


def parse_s3_url(url):
    """
    Parse S3 URL to extract bucket name and object key
    Handles both s3:// and https:// formats
    """
    # Check for s3:// protocol format first
    s3_protocol_match = re.match(r'^s3://([a-z0-9.-]+)/(.+)$', url)
    if s3_protocol_match:
        bucket_name = s3_protocol_match.group(1)
        object_key = s3_protocol_match.group(2)
        return bucket_name, object_key
    
    # Fall back to HTTPS format parsing
    parsed = urlparse(url)
    
    if parsed.netloc.endswith('.s3.amazonaws.com'):
        # Format: https://bucket-name.s3.amazonaws.com/key
        bucket_name = parsed.netloc.replace('.s3.amazonaws.com', '')
        object_key = parsed.path.lstrip('/')
    elif parsed.netloc == 's3.amazonaws.com':
        # Format: https://s3.amazonaws.com/bucket-name/key
        path_parts = parsed.path.lstrip('/').split('/', 1)
        bucket_name = path_parts[0]
        object_key = path_parts[1] if len(path_parts) > 1 else ''
    else:
        raise ValueError("Invalid S3 URL format")
    
    return bucket_name, object_key 