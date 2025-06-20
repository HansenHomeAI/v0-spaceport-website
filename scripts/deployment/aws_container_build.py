#!/usr/bin/env python3
"""
AWS Container Build Script
Builds SOGS compression container entirely on AWS infrastructure
Bypasses all local Docker issues
"""

import boto3
import json
import time
import zipfile
import tempfile
import os
from pathlib import Path

def main():
    """Main function to build SOGS containers on AWS"""
    print("🚀 AWS Container Builder")
    print("Building SOGS containers entirely on AWS infrastructure")
    print("=" * 60)
    
    # Configuration
    region = "us-west-2"
    account_id = boto3.client('sts').get_caller_identity()['Account']
    bucket_name = f"sogs-build-{account_id}"
    repo_name = "spaceport-ml-sogs-compressor"
    project_name = "sogs-aws-builder"
    
    print(f"🏗️ AWS Container Builder initialized")
    print(f"   Account: {account_id}")
    print(f"   Region: {region}")
    print(f"   ECR Repo: {repo_name}")
    
    # Initialize clients
    codebuild = boto3.client('codebuild', region_name=region)
    s3 = boto3.client('s3', region_name=region)
    iam = boto3.client('iam', region_name=region)
    ecr = boto3.client('ecr', region_name=region)
    
    # Step 1: Setup infrastructure
    print("🔧 Setting up AWS infrastructure...")
    
    # Create S3 bucket
    try:
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        print(f"   ✅ S3 bucket created: {bucket_name}")
    except Exception as e:
        if "BucketAlreadyExists" in str(e) or "BucketAlreadyOwnedByYou" in str(e):
            print(f"   ✅ S3 bucket exists: {bucket_name}")
        else:
            print(f"   ❌ S3 bucket error: {e}")
    
    # Create ECR repository
    try:
        ecr.create_repository(repositoryName=repo_name)
        print(f"   ✅ ECR repository created: {repo_name}")
    except Exception as e:
        if "RepositoryAlreadyExistsException" in str(e):
            print(f"   ✅ ECR repository exists: {repo_name}")
        else:
            print(f"   ❌ ECR repository error: {e}")
    
    # Create IAM role for CodeBuild
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "codebuild.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    role_name = "SOGSCodeBuildRole"
    try:
        iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        print(f"   ✅ IAM role created: {role_name}")
    except Exception as e:
        if "EntityAlreadyExists" in str(e):
            print(f"   ✅ IAM role exists: {role_name}")
        else:
            print(f"   ❌ IAM role error: {e}")
    
    # Attach policies to role
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream", 
                    "logs:PutLogEvents"
                ],
                "Resource": f"arn:aws:logs:{region}:{account_id}:log-group:/aws/codebuild/*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:GetAuthorizationToken",
                    "ecr:PutImage",
                    "ecr:InitiateLayerUpload",
                    "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject"],
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }
        ]
    }
    
    try:
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="SOGSBuildPolicy",
            PolicyDocument=json.dumps(policy)
        )
        print(f"   ✅ IAM policy attached")
    except Exception as e:
        print(f"   ⚠️  IAM policy warning: {e}")
    
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    
    # Step 2: Upload source code
    print("📦 Uploading source code to S3...")
    
    # Create ZIP file with source code
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
        with zipfile.ZipFile(tmp_zip.name, 'w') as zf:
            # Add all files from compressor directory
            compressor_dir = Path(".")  # Current directory is compressor
            
            for file_path in compressor_dir.rglob("*"):
                if file_path.is_file() and not any(skip in str(file_path) for skip in ['.pyc', '__pycache__', 'test_output']):
                    arc_name = file_path.relative_to(compressor_dir)
                    zf.write(file_path, arc_name)
                    print(f"   Added: {arc_name}")
        
        # Upload to S3
        s3_key = f"source/sogs-source-{int(time.time())}.zip"
        s3.upload_file(tmp_zip.name, bucket_name, s3_key)
        os.unlink(tmp_zip.name)
        
        print(f"   ✅ Source uploaded: s3://{bucket_name}/{s3_key}")
        source_location = f"{bucket_name}/{s3_key}"
    
    # Step 3: Create buildspec
    buildspec = {
        "version": 0.2,
        "phases": {
            "pre_build": {
                "commands": [
                    "echo '🚀 Starting SOGS Container Build on AWS'",
                    "echo 'Build started on $(date)'",
                    "echo 'Logging in to Amazon ECR...'",
                    "aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com",
                    f"REPOSITORY_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/{repo_name}",
                    "IMAGE_TAG=latest",
                    "echo Repository URI = $REPOSITORY_URI",
                    "echo Current directory contents:",
                    "ls -la"
                ]
            },
            "build": {
                "commands": [
                    "echo '🏗️ Building SOGS container...'",
                    "echo 'Building simple CPU-only version first...'",
                    f"docker build -f Dockerfile.simple -t {repo_name}:simple .",
                    f"docker tag {repo_name}:simple $REPOSITORY_URI:simple",
                    "echo 'Building full CUDA version...'",
                    f"docker build -f Dockerfile.aws-build -t {repo_name}:latest .",
                    f"docker tag {repo_name}:latest $REPOSITORY_URI:latest",
                    "echo 'Build completed on $(date)'"
                ]
            },
            "post_build": {
                "commands": [
                    "echo '📤 Pushing Docker images to ECR...'",
                    "docker push $REPOSITORY_URI:simple",
                    "docker push $REPOSITORY_URI:latest",
                    "echo '✅ Images pushed successfully!'",
                    "echo Simple image: $REPOSITORY_URI:simple",
                    "echo Full image: $REPOSITORY_URI:latest"
                ]
            }
        }
    }
    
    # Step 4: Create CodeBuild project
    print("🏗️ Creating CodeBuild project...")
    
    # Delete existing project if it exists
    try:
        codebuild.delete_project(name=project_name)
        time.sleep(5)  # Wait for deletion
    except:
        pass
    
    project_config = {
        "name": project_name,
        "description": "AWS-based SOGS container builder",
        "source": {
            "type": "S3",
            "location": source_location,
            "buildspec": json.dumps(buildspec, indent=2)
        },
        "artifacts": {"type": "NO_ARTIFACTS"},
        "environment": {
            "type": "LINUX_CONTAINER",
            "image": "aws/codebuild/standard:7.0",
            "computeType": "BUILD_GENERAL1_LARGE",
            "privilegedMode": True,
            "environmentVariables": [
                {"name": "AWS_DEFAULT_REGION", "value": region},
                {"name": "AWS_ACCOUNT_ID", "value": account_id},
                {"name": "IMAGE_REPO_NAME", "value": repo_name}
            ]
        },
        "serviceRole": role_arn,
        "timeoutInMinutes": 120
    }
    
    codebuild.create_project(**project_config)
    print(f"   ✅ CodeBuild project created: {project_name}")
    
    # Step 5: Start build and monitor
    print("🚀 Starting container build...")
    
    # Start build
    response = codebuild.start_build(projectName=project_name)
    build_id = response['build']['id']
    
    print(f"   Build ID: {build_id}")
    print("   Monitoring build progress...")
    
    # Monitor build
    start_time = time.time()
    last_status = None
    
    while True:
        try:
            response = codebuild.batch_get_builds(ids=[build_id])
            build = response['builds'][0]
            status = build['buildStatus']
            
            if status != last_status:
                elapsed = int(time.time() - start_time)
                print(f"   Status: {status} (elapsed: {elapsed}s)")
                last_status = status
            
            if status == 'SUCCEEDED':
                print("   ✅ Build completed successfully!")
                duration = int(time.time() - start_time)
                print(f"\n🎉 Container build completed successfully!")
                print(f"   Duration: {duration} seconds")
                print(f"   Simple image: {account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}:simple")
                print(f"   Full image: {account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}:latest")
                
                print("\n🎯 Next steps:")
                print("1. Test the simple container:")
                print("   python3 test_sogs_fallback.py")
                print("2. Test the full container:")
                print("   python3 test_sogs_production.py")
                print("3. Update your ML pipeline to use the new containers")
                return 0
                
            elif status in ['FAILED', 'FAULT', 'STOPPED', 'TIMED_OUT']:
                print(f"   ❌ Build failed with status: {status}")
                
                # Get build logs
                if 'logs' in build and 'cloudWatchLogs' in build['logs']:
                    log_group = build['logs']['cloudWatchLogs'].get('groupName')
                    log_stream = build['logs']['cloudWatchLogs'].get('streamName')
                    
                    if log_group and log_stream:
                        print("   📋 Build logs:")
                        try:
                            logs = boto3.client('logs', region_name=region)
                            logs_response = logs.get_log_events(
                                logGroupName=log_group,
                                logStreamName=log_stream
                            )
                            for event in logs_response['events'][-20:]:  # Last 20 log entries
                                print(f"      {event['message']}")
                        except Exception as e:
                            print(f"      Could not fetch logs: {e}")
                
                return 1
                
            elif status == 'IN_PROGRESS':
                time.sleep(30)  # Check every 30 seconds
            else:
                time.sleep(10)  # Check more frequently for other statuses
                
        except Exception as e:
            print(f"   ⚠️  Error monitoring build: {e}")
            time.sleep(10)

if __name__ == "__main__":
    import sys
    sys.exit(main()) 