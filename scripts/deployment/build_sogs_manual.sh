#!/bin/bash
set -e

# Manual SOGS Container Build Script
# Creates CodeBuild project and builds SOGS container on AWS

echo "🚀 Manual SOGS Container Build on AWS"
echo "====================================="

# Configuration
AWS_REGION=${AWS_REGION:-"us-west-2"}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PROJECT_NAME="sogs-manual-build"
ECR_REPO_NAME="spaceport-ml-sogs-compressor"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "AWS Account: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"
echo "ECR Repository: $ECR_URI"
echo ""

# Step 1: Create S3 bucket for build artifacts
BUCKET_NAME="sogs-build-artifacts-$AWS_ACCOUNT_ID"
echo "📦 Creating S3 bucket for build artifacts..."
aws s3api create-bucket \
    --bucket "$BUCKET_NAME" \
    --region "$AWS_REGION" \
    --create-bucket-configuration LocationConstraint="$AWS_REGION" \
    2>/dev/null || echo "Bucket already exists"

# Step 2: Create CodeBuild service role
ROLE_NAME="SOGSCodeBuildRole"
echo "🔐 Creating CodeBuild service role..."

# Create trust policy
cat > /tmp/trust-policy.json << EOF
{
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
EOF

# Create role
aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document file:///tmp/trust-policy.json \
    2>/dev/null || echo "Role already exists"

# Create policy
cat > /tmp/codebuild-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:/aws/codebuild/*"
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
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*"
    }
  ]
}
EOF

# Attach policy
aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "SOGSBuildPolicy" \
    --policy-document file:///tmp/codebuild-policy.json

# Get role ARN
ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
echo "Role ARN: $ROLE_ARN"

# Step 3: Create buildspec for SOGS container
cat > /tmp/buildspec.yml << EOF
version: 0.2

phases:
  pre_build:
    commands:
      - echo "🚀 Starting SOGS Container Build"
      - echo "Build started on \$(date)"
      - echo "Logging in to Amazon ECR..."
      - aws ecr get-login-password --region \$AWS_DEFAULT_REGION | docker login --username AWS --password-stdin \$AWS_ACCOUNT_ID.dkr.ecr.\$AWS_DEFAULT_REGION.amazonaws.com
      - REPOSITORY_URI=\$AWS_ACCOUNT_ID.dkr.ecr.\$AWS_DEFAULT_REGION.amazonaws.com/\$IMAGE_REPO_NAME
      - IMAGE_TAG=latest
      - echo "Repository URI = \$REPOSITORY_URI"
      
  build:
    commands:
      - echo "🏗️ Building SOGS container with CUDA support..."
      - docker build -f Dockerfile.aws-build -t \$IMAGE_REPO_NAME:latest .
      - docker tag \$IMAGE_REPO_NAME:latest \$REPOSITORY_URI:latest
      - echo "Build completed on \$(date)"
      
  post_build:
    commands:
      - echo "📤 Pushing Docker image to ECR..."
      - docker push \$REPOSITORY_URI:latest
      - echo "✅ Image pushed successfully: \$REPOSITORY_URI:latest"
EOF

# Step 4: Upload source code to S3
echo "📁 Uploading source code to S3..."
# We're already in the compressor directory when this script is called
zip -r /tmp/sogs-source.zip . -x "*.pyc" "__pycache__/*" "test_output/*"
aws s3 cp /tmp/sogs-source.zip "s3://$BUCKET_NAME/source/sogs-source.zip"

# Step 5: Create CodeBuild project
echo "🏗️ Creating CodeBuild project..."
cat > /tmp/codebuild-project.json << EOF
{
  "name": "$PROJECT_NAME",
  "description": "Manual build project for SOGS compression container",
  "source": {
    "type": "S3",
    "location": "$BUCKET_NAME/source/sogs-source.zip",
    "buildspec": "$(cat /tmp/buildspec.yml | sed 's/"/\\"/g' | tr '\n' ' ')"
  },
  "artifacts": {
    "type": "NO_ARTIFACTS"
  },
  "environment": {
    "type": "LINUX_CONTAINER",
    "image": "aws/codebuild/standard:7.0",
    "computeType": "BUILD_GENERAL1_LARGE",
    "privilegedMode": true,
    "environmentVariables": [
      {
        "name": "AWS_DEFAULT_REGION",
        "value": "$AWS_REGION"
      },
      {
        "name": "AWS_ACCOUNT_ID",
        "value": "$AWS_ACCOUNT_ID"
      },
      {
        "name": "IMAGE_REPO_NAME",
        "value": "$ECR_REPO_NAME"
      }
    ]
  },
  "serviceRole": "$ROLE_ARN",
  "timeoutInMinutes": 60
}
EOF

# Delete existing project if it exists
aws codebuild delete-project --name "$PROJECT_NAME" 2>/dev/null || true

# Create new project
aws codebuild create-project \
    --cli-input-json file:///tmp/codebuild-project.json

echo "✅ CodeBuild project created: $PROJECT_NAME"

# Step 6: Start the build
echo "🚀 Starting build..."
BUILD_ID=$(aws codebuild start-build \
    --project-name "$PROJECT_NAME" \
    --query 'build.id' \
    --output text)

echo "Build started with ID: $BUILD_ID"
echo "Monitoring build progress..."

# Step 7: Monitor build
while true; do
    BUILD_STATUS=$(aws codebuild batch-get-builds \
        --ids "$BUILD_ID" \
        --query 'builds[0].buildStatus' \
        --output text)
    
    case $BUILD_STATUS in
        "IN_PROGRESS")
            echo "Build in progress... (checking again in 30s)"
            sleep 30
            ;;
        "SUCCEEDED")
            echo "✅ Build completed successfully!"
            echo ""
            echo "🎉 SOGS container built and pushed to ECR:"
            echo "   $ECR_URI:latest"
            echo ""
            echo "You can now test it with:"
            echo "   python3 infrastructure/containers/compressor/test_sogs_production.py"
            break
            ;;
        "FAILED"|"FAULT"|"STOPPED"|"TIMED_OUT")
            echo "❌ Build failed with status: $BUILD_STATUS"
            
            # Get build logs
            echo "Fetching build logs..."
            LOG_GROUP=$(aws codebuild batch-get-builds --ids "$BUILD_ID" \
                --query 'builds[0].logs.cloudWatchLogs.groupName' \
                --output text)
            LOG_STREAM=$(aws codebuild batch-get-builds --ids "$BUILD_ID" \
                --query 'builds[0].logs.cloudWatchLogs.streamName' \
                --output text)
            
            if [ "$LOG_GROUP" != "None" ] && [ "$LOG_STREAM" != "None" ]; then
                echo "Build logs:"
                aws logs get-log-events \
                    --log-group-name "$LOG_GROUP" \
                    --log-stream-name "$LOG_STREAM" \
                    --query 'events[].message' \
                    --output text
            fi
            
            exit 1
            ;;
        *)
            echo "Unknown build status: $BUILD_STATUS"
            sleep 10
            ;;
    esac
done

# Cleanup
rm -f /tmp/trust-policy.json /tmp/codebuild-policy.json /tmp/buildspec.yml /tmp/codebuild-project.json /tmp/sogs-source.zip

echo ""
echo "🎯 Next steps:"
echo "1. Test the container: python3 infrastructure/containers/compressor/test_sogs_production.py"
echo "2. Update your ML pipeline to use: $ECR_URI:latest"
echo "3. Run end-to-end pipeline test" 