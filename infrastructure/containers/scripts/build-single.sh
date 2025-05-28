#!/bin/bash
set -e

# Build a single container
# Usage: ./build-single.sh <container-name> [--push]

CONTAINER_NAME=$1
PUSH_FLAG=$2
REGION=${AWS_DEFAULT_REGION:-us-west-2}

if [ -z "$CONTAINER_NAME" ]; then
    echo "Usage: $0 <container-name> [--push]"
    echo "Available containers: sfm, 3dgs, compressor"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🐳 Building container: $CONTAINER_NAME${NC}"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/spaceport/$CONTAINER_NAME"

# Check if container directory exists
if [ ! -d "infrastructure/containers/$CONTAINER_NAME" ]; then
    echo -e "${RED}❌ Container directory not found: infrastructure/containers/$CONTAINER_NAME${NC}"
    exit 1
fi

# Build the container
echo -e "${YELLOW}📦 Building Docker image...${NC}"
docker build -t "spaceport/$CONTAINER_NAME:latest" \
    -t "$ECR_URI:latest" \
    "infrastructure/containers/$CONTAINER_NAME"

echo -e "${GREEN}✅ Built: spaceport/$CONTAINER_NAME:latest${NC}"

# Push if requested
if [ "$PUSH_FLAG" = "--push" ]; then
    echo -e "${YELLOW}🚀 Pushing to ECR...${NC}"
    
    # Login to ECR
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI
    
    # Push the image
    docker push "$ECR_URI:latest"
    echo -e "${GREEN}✅ Pushed: $ECR_URI:latest${NC}"
fi

echo -e "${GREEN}🎉 Container $CONTAINER_NAME ready!${NC}" 