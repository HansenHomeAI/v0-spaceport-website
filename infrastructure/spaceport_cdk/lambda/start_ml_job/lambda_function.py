import json
import boto3
import os
import re
import uuid
from datetime import datetime
from urllib.parse import urlparse

# Initialize AWS clients (ECR client will be initialized per-region in resolve_ecr_uri)
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
        email = body.get('email', 'hello@spcprt.com')  # Optional email for notifications
        pipeline_step = body.get('pipelineStep', 'sfm')  # Which step to start from: 'sfm', '3dgs', or 'compression'
        csv_data = body.get('csvData')  # Optional CSV data as string for GPS-enhanced processing
        existing_colmap_uri = body.get('existingColmapUri')  # Optional: use existing SfM data
        
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
        
        # Verify the main object exists (skip for test data that may not exist)
        if not s3_url.startswith("s3://spaceport-ml-pipeline/test-data/"):
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
        
        # Generate unique job ID early so it can be used for CSV storage
        job_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        job_name = f"ml-job-{timestamp}-{job_id[:8]}"
        
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
        
        # Get ECR repository names from environment variables (set by CDK)
        # Format: "spaceport/sfm" or "spaceport/sfm-{suffix}" for branch-specific
        # CDK will set both branch-specific and fallback names
        sfm_repo = os.environ.get('SFM_ECR_REPO', 'spaceport/sfm')
        gaussian_repo = os.environ.get('GAUSSIAN_ECR_REPO', 'spaceport/3dgs')
        compressor_repo = os.environ.get('COMPRESSOR_ECR_REPO', 'spaceport/compressor')
        
        # Fallback repo names (shared repos without suffix)
        sfm_repo_fallback = os.environ.get('SFM_ECR_REPO_FALLBACK', 'spaceport/sfm')
        gaussian_repo_fallback = os.environ.get('GAUSSIAN_ECR_REPO_FALLBACK', 'spaceport/3dgs')
        compressor_repo_fallback = os.environ.get('COMPRESSOR_ECR_REPO_FALLBACK', 'spaceport/compressor')
        
        account_id = context.invoked_function_arn.split(':')[4]
        region = context.invoked_function_arn.split(':')[3]
        
        image_tag = os.environ.get('ECR_IMAGE_TAG', 'latest').strip() or 'latest'
        require_branch_image_tag = os.environ.get('REQUIRE_BRANCH_ECR_TAG', 'false').lower() in ('1', 'true', 'yes', 'on')

        # Resolve ECR image URIs with fallback logic.
        # Branch previews must validate the branch tag/digest, not silently run :latest.
        def resolve_ecr_uri(repo_name, fallback_repo_name, image_tag=image_tag):
            """Resolve ECR URI, trying branch-specific repo/tag first, then fallback."""
            ecr_client = boto3.client('ecr', region_name=region)

            def image_exists(repository_name, tag):
                try:
                    ecr_client.describe_images(repositoryName=repository_name, imageIds=[{'imageTag': tag}])
                    return True
                except Exception as image_error:
                    code = image_error.response.get('Error', {}).get('Code', '') if hasattr(image_error, 'response') else ''
                    if code in ('ImageNotFoundException', 'RepositoryNotFoundException'):
                        return False
                    raise

            def image_uri(repository_name, tag):
                return f"{account_id}.dkr.ecr.{region}.amazonaws.com/{repository_name}:{tag}"

            # Try branch-specific repo first
            try:
                ecr_client.describe_repositories(repositoryNames=[repo_name])
                if image_exists(repo_name, image_tag):
                    print(f"Using branch-specific ECR image: {repo_name}:{image_tag}")
                    return image_uri(repo_name, image_tag)
                if require_branch_image_tag:
                    raise RuntimeError(f"Required branch ECR image tag missing: {repo_name}:{image_tag}")
                print(f"Branch-specific repo {repo_name} lacks tag {image_tag}, falling back to latest")
                return image_uri(repo_name, 'latest')
            except Exception as e:
                # Check if it's a repository not found error
                error_code = e.response.get('Error', {}).get('Code', '') if hasattr(e, 'response') else ''
                if require_branch_image_tag and error_code != 'RepositoryNotFoundException':
                    raise
                if error_code == 'RepositoryNotFoundException':
                    # Fallback to shared repo
                    try:
                        ecr_client.describe_repositories(repositoryNames=[fallback_repo_name])
                        if image_exists(fallback_repo_name, image_tag):
                            print(f"Using fallback repo with branch tag: {fallback_repo_name}:{image_tag}")
                            return image_uri(fallback_repo_name, image_tag)
                        if require_branch_image_tag:
                            raise RuntimeError(
                                f"Required branch ECR image tag missing in fallback repo: {fallback_repo_name}:{image_tag}"
                            )
                        print(f"Branch-specific repo {repo_name} not found, using fallback latest: {fallback_repo_name}")
                        return image_uri(fallback_repo_name, 'latest')
                    except Exception as e2:
                        # If fallback also doesn't exist, use it anyway (will fail at runtime with clear error)
                        if require_branch_image_tag:
                            raise
                        print(f"Warning: Neither {repo_name} nor {fallback_repo_name} found, using fallback")
                        return image_uri(fallback_repo_name, 'latest')
                else:
                    # On any other error, use fallback
                    if require_branch_image_tag:
                        raise
                    print(f"Error checking repo {repo_name}: {str(e)}, using fallback: {fallback_repo_name}")
                    return image_uri(fallback_repo_name, 'latest')
        
        sfm_image_uri = resolve_ecr_uri(sfm_repo, sfm_repo_fallback)
        gaussian_image_uri = resolve_ecr_uri(gaussian_repo, gaussian_repo_fallback)
        compressor_image_uri = resolve_ecr_uri(compressor_repo, compressor_repo_fallback)
        
        print(f"Using ECR repos - SfM: {sfm_image_uri}, 3DGS: {gaussian_image_uri}, Compressor: {compressor_image_uri}")
        
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
        
        # Special handling for 3DGS-only tests with existing SfM data
        existing_colmap_uri = body.get('existingColmapUri')  # Optional: use existing SfM data
        
        # Default to splatfacto-w-light with the background model enabled so the
        # pipeline produces a foreground PLY for SOGS plus a lightweight skybox.
        default_hyperparameters = {
            "MAX_ITERATIONS": "30000",
            "TARGET_PSNR": "35.0",
            "MODEL_VARIANT": "splatfacto-w-light",
            "SH_DEGREE": "3",
            "BILATERAL_PROCESSING": "false",
            "LOG_INTERVAL": "100",
            "RASTERIZE_MODE": "classic",
            "USE_SCALE_REGULARIZATION": "true",
            "CULL_ALPHA_THRESH": "0.12",
            "CULL_SCALE_THRESH": "0.35",
            "ENABLE_BG_MODEL": "true",
            "ENABLE_ALPHA_LOSS": "true",
            "ENABLE_ROBUST_MASK": "true",
            "BG_SH_DEGREE": "8",
            "APPEARANCE_EMBED_DIM": "64",
            "NEVER_MASK_UPPER": "0.4",
            "BACKGROUND_APPEARANCE_MODE": "auto_camera",
            "BACKGROUND_SKYBOX_WIDTH": "2048",
            "BACKGROUND_SKYBOX_HEIGHT": "1024",
            "BACKGROUND_SKYBOX_QUALITY": "95",
            "BACKGROUND_SELECTION_STRIDE": "5",
            "BACKGROUND_SELECTION_MAX_FRAMES": "32",
            "FLOATER_PRUNING_ENABLED": "true",
            "FLOATER_PRUNING_MIN_VIEWS": "6",
            "FLOATER_PRUNING_TOP_REGION_RATIO": "0.35",
            "FLOATER_PRUNING_TOP_VIEW_FRACTION": "0.9",
            "FLOATER_PRUNING_MIN_SKY_VIEWS": "2",
            "FLOATER_PRUNING_SKY_MIN_LUMINANCE": "0.3",
            "FLOATER_PRUNING_SKY_MIN_SATURATION": "0.08",
            "FLOATER_PRUNING_SKY_BLUE_DOMINANCE_MARGIN": "0.02",
            "FLOATER_PRUNING_MAX_OPACITY": "0.75",
            "FLOATER_PRUNING_MAX_COLOR_DISTANCE": "0.18",
            "FLOATER_PRUNING_MIN_EDGE_SUPPORT": "1",
            "TRAINING_TIMEOUT_SECONDS": "14400",
            
            # NerfStudio Framework Configuration
            "FRAMEWORK": "nerfstudio",
            "METHODOLOGY": "spaceport_splatfacto_w_light_skybox",
            "LICENSE": "apache_2_0",
            "COMMERCIAL_LICENSE": "true",
            
            # Quality and Output Settings
            "OUTPUT_FORMAT": "ply",             # SOGS-compatible format
            "SOGS_COMPATIBLE": "true",          # Enable SOGS export
            
            # GPU Optimization for A10G (24GB on G5)
            "MAX_NUM_GAUSSIANS": "1500000",     # Conservative limit for A10G
            "MEMORY_OPTIMIZATION": "true",      # Enable memory optimization
            "TORCH_CUDA_ARCH_LIST": "7.0;8.0;8.6+PTX",  # Match 3DGS Dockerfile CUDA targets
            
            # Legacy G-Splat parameters for backward compatibility (will be ignored by NerfStudio)
            "max_iterations": 30000,
            "target_psnr": 35.0,
            "sh_degree": 3,
            "log_interval": 100
        }
        
        # Merge user-provided hyperparameters with defaults (user values override defaults)
        final_hyperparameters = {**default_hyperparameters, **hyperparameters}
        
        print(f"✅ Using hyperparameters: {json.dumps(final_hyperparameters, indent=2)}")
        
        # Determine COLMAP output URI - use existing data if provided, otherwise generate new path
        if existing_colmap_uri:
            colmap_output_uri = existing_colmap_uri
            print(f"✅ Using existing COLMAP data: {colmap_output_uri}")
        else:
            colmap_output_uri = f"s3://{ml_bucket}/colmap/{job_id}/"
            print(f"✅ Will generate new COLMAP data: {colmap_output_uri}")
        
        # Prepare Step Functions input
        step_function_input = {
            "jobId": job_id,
            "jobName": job_name,
            "s3Url": s3_url,
            "email": email,
            "pipelineStep": pipeline_step,
            "inputS3Uri": f"s3://{bucket_name}/{object_key}",
            "colmapOutputS3Uri": colmap_output_uri,
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
