#!/bin/bash
set -e

# Simple Container Push Script
# Builds and pushes CPU-only SOGS container for immediate testing

echo "🚀 Building and Pushing Simple SOGS Container"
echo "============================================="

# Configuration
AWS_REGION=${AWS_REGION:-"us-west-2"}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO_NAME="spaceport-ml-sogs-compressor"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "AWS Account: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"
echo "ECR Repository: $ECR_URI"
echo ""

# Step 1: Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI

# Step 2: Build simple container
echo "🏗️ Building simple SOGS container (CPU-only)..."
cd infrastructure/containers/compressor
docker build -f Dockerfile.simple -t sogs-simple:latest .
docker tag sogs-simple:latest $ECR_URI:simple

# Step 3: Push to ECR
echo "📤 Pushing container to ECR..."
docker push $ECR_URI:simple

echo ""
echo "✅ Simple SOGS container pushed successfully!"
echo "   Image URI: $ECR_URI:simple"
echo ""
echo "🎯 Testing the container..."

# Step 4: Test the container immediately
python3 test_sogs_production.py --region $AWS_REGION

echo ""
echo "🎉 Container build and test completed!"
echo ""
echo "Next steps:"
echo "1. If tests pass, the container is working correctly"
echo "2. You can now use it in your ML pipeline"
echo "3. Later, build the CUDA version for better performance" 