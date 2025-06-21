#!/usr/bin/env python3
"""
Build Production SOGS Container on AWS CodeBuild
Uses CUDA runtime and real SOGS compression
"""

import boto3
import json
import time
import os
from datetime import datetime

# Configuration
REGION = 'us-west-2'
PROJECT_NAME = 'sogs-production-build'
ECR_REPO_NAME = 'sogs-production'
SOURCE_LOCATION = 'https://github.com/gabrielhansen/Spaceport-Website.git'  # Update with your repo
DOCKERFILE_PATH = 'infrastructure/containers/compressor/Dockerfile.production'

def create_ecr_repository():
    """Create ECR repository for the production container"""
    ecr_client = boto3.client('ecr', region_name=REGION)
    
    try:
        response = ecr_client.create_repository(
            repositoryName=ECR_REPO_NAME,
            imageScanningConfiguration={'scanOnPush': True},
            encryptionConfiguration={'encryptionType': 'AES256'}
        )
        print(f"✅ Created ECR repository: {response['repository']['repositoryUri']}")
        return response['repository']['repositoryUri']
    except ecr_client.exceptions.RepositoryAlreadyExistsException:
        print(f"✅ ECR repository already exists: {ECR_REPO_NAME}")
        response = ecr_client.describe_repositories(repositoryNames=[ECR_REPO_NAME])
        return response['repositories'][0]['repositoryUri']

def get_account_id():
    """Get AWS account ID"""
    sts = boto3.client('sts')
    return sts.get_caller_identity()['Account']

def create_codebuild_project():
    """Create CodeBuild project for building the production container"""
    codebuild = boto3.client('codebuild', region_name=REGION)
    
    account_id = get_account_id()
    ecr_uri = f'{account_id}.dkr.ecr.{REGION}.amazonaws.com/{ECR_REPO_NAME}'
    
    # Create buildspec for production SOGS
    buildspec = {
        'version': '0.2',
        'phases': {
            'pre_build': {
                'commands': [
                    'echo Logging in to Amazon ECR...',
                    f'aws ecr get-login-password --region {REGION} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{REGION}.amazonaws.com',
                    'echo Build started on `date`',
                    'echo Building the Docker image...'
                ]
            },
            'build': {
                'commands': [
                    f'cd infrastructure/containers/compressor',
                    f'docker build -f Dockerfile.production -t {ECR_REPO_NAME}:latest .',
                    f'docker tag {ECR_REPO_NAME}:latest {ecr_uri}:latest',
                    f'docker tag {ECR_REPO_NAME}:latest {ecr_uri}:production-{int(time.time())}'
                ]
            },
            'post_build': {
                'commands': [
                    'echo Build completed on `date`',
                    'echo Pushing the Docker images...',
                    f'docker push {ecr_uri}:latest',
                    f'docker push {ecr_uri}:production-{int(time.time())}',
                    'echo Push completed'
                ]
            }
        },
        'artifacts': {
            'files': [
                '**/*'
            ]
        }
    }
    
    # Save buildspec
    with open('buildspec_production.yml', 'w') as f:
        # Write YAML manually instead of using PyYAML
        f.write("version: 0.2\n")
        f.write("phases:\n")
        f.write("  pre_build:\n")
        f.write("    commands:\n")
        f.write("      - echo Logging in to Amazon ECR...\n")
        f.write(f"      - aws ecr get-login-password --region {REGION} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{REGION}.amazonaws.com\n")
        f.write("      - echo Build started on `date`\n")
        f.write("      - echo Building the Docker image...\n")
        f.write("  build:\n")
        f.write("    commands:\n")
        f.write("      - cd infrastructure/containers/compressor\n")
        f.write(f"      - docker build -f Dockerfile.production -t {ECR_REPO_NAME}:latest .\n")
        f.write(f"      - docker tag {ECR_REPO_NAME}:latest {ecr_uri}:latest\n")
        f.write(f"      - docker tag {ECR_REPO_NAME}:latest {ecr_uri}:production-$(date +%s)\n")
        f.write("  post_build:\n")
        f.write("    commands:\n")
        f.write("      - echo Build completed on `date`\n")
        f.write("      - echo Pushing the Docker images...\n")
        f.write(f"      - docker push {ecr_uri}:latest\n")
        f.write(f"      - docker push {ecr_uri}:production-$(date +%s)\n")
        f.write("      - echo Push completed\n")
        f.write("artifacts:\n")
        f.write("  files:\n")
        f.write("    - '**/*'\n")
    
    try:
        response = codebuild.create_project(
            name=PROJECT_NAME,
            description='Build production SOGS compression container with CUDA support',
            source={
                'type': 'GITHUB',
                'location': SOURCE_LOCATION,
                'buildspec': json.dumps(buildspec)
            },
            artifacts={
                'type': 'NO_ARTIFACTS'
            },
            environment={
                'type': 'LINUX_CONTAINER',
                'image': 'aws/codebuild/standard:7.0',  # Latest with Docker support
                'computeType': 'BUILD_GENERAL1_LARGE',  # Large for CUDA builds
                'privilegedMode': True  # Required for Docker builds
            },
            serviceRole=f'arn:aws:iam::{account_id}:role/CodeBuildServiceRole',
            timeoutInMinutes=120,  # 2 hours for CUDA build
            tags=[
                {
                    'key': 'Project',
                    'value': 'Spaceport-SOGS'
                },
                {
                    'key': 'Environment',
                    'value': 'Production'
                }
            ]
        )
        print(f"✅ Created CodeBuild project: {PROJECT_NAME}")
        return response['project']['arn']
    except codebuild.exceptions.ResourceAlreadyExistsException:
        print(f"✅ CodeBuild project already exists: {PROJECT_NAME}")
        response = codebuild.describe_projects(names=[PROJECT_NAME])
        return response['projects'][0]['arn']

def start_build():
    """Start the CodeBuild build"""
    codebuild = boto3.client('codebuild', region_name=REGION)
    
    try:
        response = codebuild.start_build(
            projectName=PROJECT_NAME,
            sourceVersion='main'  # Use main branch
        )
        
        build_id = response['build']['id']
        print(f"✅ Started build: {build_id}")
        
        return build_id
    except Exception as e:
        print(f"❌ Failed to start build: {e}")
        return None

def monitor_build(build_id):
    """Monitor the build progress"""
    codebuild = boto3.client('codebuild', region_name=REGION)
    
    print(f"\n🔄 Monitoring build: {build_id}")
    print("This may take 30-60 minutes for CUDA container build...")
    
    while True:
        try:
            response = codebuild.batch_get_builds(ids=[build_id])
            build = response['builds'][0]
            
            status = build['buildStatus']
            phase = build.get('currentPhase', 'UNKNOWN')
            
            print(f"Status: {status}, Phase: {phase}")
            
            if status in ['SUCCEEDED', 'FAILED', 'STOPPED', 'TIMED_OUT']:
                break
            
            time.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            print(f"Error monitoring build: {e}")
            break
    
    # Get final build details
    try:
        response = codebuild.batch_get_builds(ids=[build_id])
        build = response['builds'][0]
        
        print(f"\n🏁 Build completed!")
        print(f"Status: {build['buildStatus']}")
        print(f"Duration: {build.get('timeoutInMinutes', 'unknown')} minutes")
        
        if 'logs' in build:
            print(f"Logs: {build['logs'].get('cloudWatchLogs', {}).get('groupName', 'N/A')}")
        
        return build['buildStatus'] == 'SUCCEEDED'
        
    except Exception as e:
        print(f"Error getting final build status: {e}")
        return False

def test_container():
    """Test the built container"""
    print("\n🧪 Testing production container...")
    
    account_id = get_account_id()
    container_uri = f'{account_id}.dkr.ecr.{REGION}.amazonaws.com/{ECR_REPO_NAME}:latest'
    
    # Create test script
    test_script = f"""
import boto3
from sagemaker.processing import Processor
from sagemaker import get_execution_role

# Test configuration
REGION = '{REGION}'
BUCKET_NAME = 'spaceport-sagemaker-us-west-2'
INPUT_KEY = 'test-data/sample.ply'
OUTPUT_PREFIX = 'production-test/test-{{int(time.time())}}'

def test_production_container():
    import sagemaker
    session = sagemaker.Session()
    
    try:
        role = get_execution_role()
    except:
        # Find SageMaker role
        iam = boto3.client('iam')
        roles = iam.list_roles()['Roles']
        sagemaker_roles = [r for r in roles if 'SageMaker' in r['RoleName']]
        role = sagemaker_roles[0]['Arn']
    
    # Create processor with production container
    processor = Processor(
        image_uri='{container_uri}',
        role=role,
        instance_type='ml.g4dn.xlarge',  # GPU instance
        instance_count=1,
        volume_size_in_gb=50,
        max_runtime_in_seconds=3600,
        base_job_name='sogs-production-test',
        sagemaker_session=session
    )
    
    # Define locations
    input_s3_uri = f's3://{{BUCKET_NAME}}/{{INPUT_KEY}}'
    output_s3_uri = f's3://{{BUCKET_NAME}}/{{OUTPUT_PREFIX}}/'
    
    print(f"Testing with:")
    print(f"  Container: {container_uri}")
    print(f"  Input: {{input_s3_uri}}")
    print(f"  Output: {{output_s3_uri}}")
    
    try:
        processor.run(
            inputs=[
                sagemaker.processing.ProcessingInput(
                    source=input_s3_uri,
                    destination='/opt/ml/processing/input'
                )
            ],
            outputs=[
                sagemaker.processing.ProcessingOutput(
                    source='/opt/ml/processing/output',
                    destination=output_s3_uri
                )
            ],
            wait=True,
            logs=True
        )
        
        print("\\n✅ Production container test PASSED!")
        return True
        
    except Exception as e:
        print(f"\\n❌ Production container test FAILED: {{e}}")
        return False

if __name__ == "__main__":
    import time
    success = test_production_container()
    exit(0 if success else 1)
"""
    
    with open('test_production_container.py', 'w') as f:
        f.write(test_script)
    
    print(f"✅ Created test script: test_production_container.py")
    print(f"📋 Container URI: {container_uri}")
    
    return container_uri

def main():
    """Main execution"""
    print("🚀 Building Production SOGS Container with Real Compression")
    print("=" * 60)
    
    try:
        # Step 1: Create ECR repository
        print("\n1️⃣ Creating ECR repository...")
        ecr_uri = create_ecr_repository()
        
        # Step 2: Create CodeBuild project
        print("\n2️⃣ Creating CodeBuild project...")
        project_arn = create_codebuild_project()
        
        # Step 3: Start build
        print("\n3️⃣ Starting container build...")
        build_id = start_build()
        
        if not build_id:
            print("❌ Failed to start build")
            return False
        
        # Step 4: Monitor build
        print("\n4️⃣ Monitoring build progress...")
        success = monitor_build(build_id)
        
        if not success:
            print("❌ Build failed")
            return False
        
        # Step 5: Create test script
        print("\n5️⃣ Creating test infrastructure...")
        container_uri = test_container()
        
        print("\n" + "=" * 60)
        print("🎉 Production SOGS Container Build COMPLETED!")
        print(f"📦 Container URI: {container_uri}")
        print(f"🧪 Test script: test_production_container.py")
        print("\nNext steps:")
        print("1. Run: python test_production_container.py")
        print("2. Verify real SOGS compression in SageMaker logs")
        print("3. Check GPU acceleration usage")
        print("4. Validate compression ratios (should be 15-20x)")
        
        return True
        
    except Exception as e:
        print(f"❌ Build process failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Production build process completed successfully!")
    else:
        print("\n❌ Production build process failed!")
        exit(1) 