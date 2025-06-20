#!/bin/bash
set -e

echo "🧪 Testing SfM Container Locally..."

# Build the container
echo "📦 Building container..."
docker build -t spaceport/sfm:latest .

# Create test directories
TEST_DIR="/tmp/sfm_test"
mkdir -p "$TEST_DIR"/{input,output}

# Test with mock environment variables
echo "🚀 Running container test..."
docker run --rm \
    -v "$TEST_DIR/input:/opt/ml/processing/input" \
    -v "$TEST_DIR/output:/opt/ml/processing/output" \
    -e S3_INPUT_URL="s3://test-bucket/test-images.zip" \
    -e OUTPUT_BUCKET="test-output-bucket" \
    -e JOB_NAME="test-job-$(date +%s)" \
    -e AWS_ACCESS_KEY_ID="test" \
    -e AWS_SECRET_ACCESS_KEY="test" \
    -e AWS_DEFAULT_REGION="us-west-2" \
    spaceport/sfm:latest

echo "✅ Container test completed!"
echo "Check output in: $TEST_DIR/output" 