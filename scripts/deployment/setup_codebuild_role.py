#!/usr/bin/env python3
"""
Setup CodeBuild IAM Role for Production SOGS Container Build
"""

import boto3
import json

def create_codebuild_role():
    """Create IAM role for CodeBuild"""
    iam = boto3.client('iam')
    
    # Trust policy for CodeBuild
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "codebuild.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Permissions policy - UPDATED with SSM Parameter Store access
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:*:*:*"
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
                "Action": [
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                    "s3:PutObject"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ssm:GetParameters",
                    "ssm:GetParameter"
                ],
                "Resource": [
                    "arn:aws:ssm:*:*:parameter/docker/password",
                    "arn:aws:ssm:*:*:parameter/docker/*"
                ]
            }
        ]
    }
    
    role_name = "CodeBuildServiceRole"
    
    try:
        # Create role
        role_response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Service role for CodeBuild to build SOGS containers with SSM access"
        )
        print(f"✅ Created IAM role: {role_name}")
        
        # Attach inline policy
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="CodeBuildPermissions",
            PolicyDocument=json.dumps(permissions_policy)
        )
        print(f"✅ Attached permissions policy to {role_name}")
        
        return role_response['Role']['Arn']
        
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"✅ IAM role already exists: {role_name}")
        
        # Update existing role policy with SSM permissions
        try:
            iam.put_role_policy(
                RoleName=role_name,
                PolicyName="CodeBuildPermissions",
                PolicyDocument=json.dumps(permissions_policy)
            )
            print(f"✅ Updated existing role with SSM permissions")
        except Exception as e:
            print(f"⚠️  Warning: Could not update role policy: {e}")
        
        role_response = iam.get_role(RoleName=role_name)
        return role_response['Role']['Arn']

def main():
    """Main execution"""
    print("🔐 Setting up CodeBuild IAM Role with SSM Parameter Store access...")
    
    try:
        role_arn = create_codebuild_role()
        print(f"\n✅ CodeBuild role ready: {role_arn}")
        print("🔑 Role now has access to SSM Parameter Store for Docker Hub credentials")
        return True
    except Exception as e:
        print(f"❌ Failed to setup role: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ IAM setup completed!")
    else:
        print("\n❌ IAM setup failed!")
        exit(1) 