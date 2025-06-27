#!/usr/bin/env python3
"""
Create CodeBuild Project for ML Container Builds
"""

import boto3
import json

def create_codebuild_project():
    """Create CodeBuild project for ML container builds"""
    codebuild = boto3.client('codebuild')
    iam = boto3.client('iam')
    
    # Get the CodeBuild service role ARN
    try:
        role_response = iam.get_role(RoleName='CodeBuildServiceRole')
        service_role = role_response['Role']['Arn']
    except iam.exceptions.NoSuchEntityException:
        print("❌ CodeBuildServiceRole not found. Run setup_codebuild_role.py first!")
        return False
    
    project_config = {
        'name': 'spaceport-ml-containers',
        'description': 'Build ML containers for Spaceport SOGS pipeline with PyTorch + CUDA',
        'source': {
            'type': 'GITHUB',
            'location': 'https://github.com/HansenHomeAI/Spaceport-Website.git',
            'buildspec': 'buildspec.yml',
            'gitCloneDepth': 1,
            'reportBuildStatus': True
        },
        'artifacts': {
            'type': 'NO_ARTIFACTS'
        },
        'environment': {
            'type': 'LINUX_CONTAINER',
            'image': 'aws/codebuild/standard:7.0',
            'computeType': 'BUILD_GENERAL1_LARGE',  # Large instance for PyTorch builds
            'privilegedMode': True  # Required for Docker builds
        },
        'serviceRole': service_role,
        'timeoutInMinutes': 120,  # 2 hours for large container builds
        'queuedTimeoutInMinutes': 30,
        'tags': [
            {
                'key': 'Project',
                'value': 'Spaceport'
            },
            {
                'key': 'Purpose',
                'value': 'ML-Container-Build'
            }
        ]
    }
    
    try:
        response = codebuild.create_project(**project_config)
        print(f"✅ Created CodeBuild project: {response['project']['name']}")
        print(f"   ARN: {response['project']['arn']}")
        print(f"   Service Role: {service_role}")
        print(f"   Compute Type: BUILD_GENERAL1_LARGE (sufficient for PyTorch)")
        return True
        
    except codebuild.exceptions.ResourceAlreadyExistsException:
        print("✅ CodeBuild project 'spaceport-ml-containers' already exists")
        return True
    except Exception as e:
        print(f"❌ Failed to create CodeBuild project: {e}")
        return False

def main():
    """Main execution"""
    print("🔨 Creating CodeBuild Project for ML Container Builds...")
    print("   This will handle PyTorch + CUDA containers that exceed GitHub Actions limits")
    
    if create_codebuild_project():
        print("\n✅ CodeBuild project ready!")
        print("\n🎯 Next steps:")
        print("   1. GitHub Actions will trigger this CodeBuild project")
        print("   2. CodeBuild has sufficient resources for PyTorch downloads")
        print("   3. Containers will be built and pushed to ECR")
        return True
    else:
        print("\n❌ CodeBuild project creation failed!")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1) 