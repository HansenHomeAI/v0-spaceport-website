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
        pipeline_step = body.get('pipelineStep', 'sfm')  # Which step to start from: 'sfm', '3dgs', or 'compression'
        csv_data = body.get('csvData')  # Optional CSV data as string for GPS-enhanced processing
        
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
        
        # Generate unique job ID early so it can be used for CSV storage
        job_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        job_name = f"ml-job-{timestamp}-{job_id[:8]}"
        
        # Verify the main object exists
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
        
        # Verify CSV file exists if provided
        csv_bucket_name = None
        csv_object_key = None
        has_gps_data = False
        
        if csv_data and pipeline_step == 'sfm':
            # Save CSV data to S3
            ml_bucket = os.environ['ML_BUCKET']
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            csv_object_key = f"csv-data/{job_id}/gps-flight-path-{timestamp}.csv"
            
            try:
                # Upload CSV data to S3
                s3.put_object(
                    Bucket=ml_bucket,
                    Key=csv_object_key,
                    Body=csv_data.encode('utf-8'),
                    ContentType='text/csv'
                )
                csv_bucket_name = ml_bucket
                has_gps_data = True
                print(f"✅ GPS flight path CSV saved: s3://{ml_bucket}/{csv_object_key}")
            except Exception as e:
                print(f"⚠️ Failed to save CSV data: {str(e)}")
                # Continue without GPS data - don't fail the entire request
        
        # Get environment variables
        state_machine_arn = os.environ['STATE_MACHINE_ARN']
        ml_bucket = os.environ['ML_BUCKET']
        
        # Get ECR repository URIs (these would be set during deployment)
        account_id = context.invoked_function_arn.split(':')[4]
        region = context.invoked_function_arn.split(':')[3]
        
        sfm_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/sfm:latest"
        gaussian_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/3dgs:latest"
        compressor_image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/compressor:latest"
        
        # Build SfM processing inputs dynamically
        sfm_processing_inputs = [{
            "InputName": "input-data",
            "AppManaged": False,
            "S3Input": {
                "S3Uri": f"s3://{bucket_name}/{object_key}",
                "LocalPath": "/opt/ml/processing/input",
                "S3DataType": "S3Prefix",
                "S3InputMode": "File"
            }
        }]
        
        # Add CSV input if GPS data is available
        if has_gps_data:
            sfm_processing_inputs.append({
                "InputName": "gps-data",
                "AppManaged": False,
                "S3Input": {
                    "S3Uri": f"s3://{csv_bucket_name}/{csv_object_key}",
                    "LocalPath": "/opt/ml/processing/input/gps",
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File"
                }
            })
        
        # Extract hyperparameters from request body (for tuning experiments)
        hyperparameters = body.get('hyperparameters', {})
        
        # Define high-quality default hyperparameters for 3DGS training
        # These are research-backed values optimized for quality and detail
        default_hyperparameters = {
            # Core Training Parameters
            "max_iterations": 30000,      # Standard for high-quality convergence
            "min_iterations": 1000,       # Minimum training before early stopping
            "target_psnr": 35.0,          # High-quality target (Peak Signal-to-Noise Ratio)
            "plateau_patience": 5000,     # Iterations to wait before early stopping
            "psnr_plateau_termination": True,  # Enable early stopping on PSNR plateau
            
            # Learning Rates (gsplat-optimized values)
            "learning_rate": 0.0025,      # Base learning rate
            "position_lr_scale": 0.00016, # Position learning rate multiplier
            "scaling_lr": 0.005,          # Gaussian scaling learning rate
            "rotation_lr": 0.001,         # Gaussian rotation learning rate
            "opacity_lr": 0.05,           # Gaussian opacity learning rate
            "feature_lr": 0.0025,         # Feature/color learning rate
            
            # Logging and Checkpointing
            "log_interval": 100,          # Log progress every N iterations
            "save_interval": 5000,        # Save checkpoint every N iterations
            
            # Densification Parameters (Critical for Quality)
            "densification_interval": 100,     # How often to run densification
            "opacity_reset_interval": 3000,    # Reset low-opacity Gaussians
            "densify_from_iter": 500,          # Start densification after N iterations
            "densify_until_iter": 15000,       # Stop densification after N iterations
            "densify_grad_threshold": 0.0002,  # Lower = more sensitive = higher detail
            "percent_dense": 0.01,             # Percentage of scene to densify
            
            # Quality Enhancement Parameters
            "lambda_dssim": 0.2,          # SSIM loss weight (preserves fine details)
            "sh_degree": 3,               # Spherical harmonics degree (3 = photorealistic)
            
            # Advanced Optimization Features
            "progressive_resolution": True,     # Start low-res, increase gradually
            "optimization_enabled": True       # Enable advanced optimization features
        }
        
        # Merge user-provided hyperparameters with defaults (user values override defaults)
        final_hyperparameters = {**default_hyperparameters, **hyperparameters}
        
        print(f"✅ Using hyperparameters: {json.dumps(final_hyperparameters, indent=2)}")
        
        # Prepare Step Functions input
        step_function_input = {
            "jobId": job_id,
            "jobName": job_name,
            "s3Url": s3_url,
            "email": email,
            "pipelineStep": pipeline_step,
            "inputS3Uri": f"s3://{bucket_name}/{object_key}",
            "colmapOutputS3Uri": f"s3://{ml_bucket}/colmap/{job_id}/",
            "gaussianOutputS3Uri": f"s3://{ml_bucket}/3dgs/{job_id}/",
            "compressedOutputS3Uri": f"s3://{ml_bucket}/compressed/{job_id}/",
            "sfmImageUri": sfm_image_uri,
            "gaussianImageUri": gaussian_image_uri,
            "compressorImageUri": compressor_image_uri,
            "sfmArgs": ["--input", "/opt/ml/processing/input", "--output", "/opt/ml/processing/output"],
            "compressionArgs": ["--input", "/opt/ml/processing/input", "--output", "/opt/ml/processing/output"],
            
            # SfM Processing Configuration
            "sfmProcessingInputs": sfm_processing_inputs,
            
            # GPS/CSV Enhancement Information
            "hasGpsData": has_gps_data,
            "csvS3Uri": f"s3://{csv_bucket_name}/{csv_object_key}" if has_gps_data else None,
            "pipelineType": "gps_enhanced" if has_gps_data else "standard",
            "sfmMethod": "opensfm_gps" if has_gps_data else "opensfm_standard",
            
            # Add all hyperparameters to the Step Functions input
            **final_hyperparameters
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