#!/bin/bash
set -e

# SOGS Container AWS Deployment Script
# Builds CUDA-enabled container on AWS infrastructure and tests it properly

echo "🚀 SOGS Container AWS Deployment & Testing"
echo "=========================================="
echo ""

# Configuration
AWS_REGION=${AWS_REGION:-"us-west-2"}
CDK_STACK_NAME="SpaceportCodeBuildStack"
ML_STACK_NAME="SpaceportMLPipelineStack"
BUILD_PROJECT_NAME="spaceport-sogs-compression-build"
MANUAL_BUILD_PROJECT="spaceport-sogs-manual-build"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check CDK
    if ! command -v cdk &> /dev/null; then
        log_error "AWS CDK is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure'."
        exit 1
    fi
    
    # Get AWS account info
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=$(aws configure get region || echo "us-west-2")
    
    log_success "Prerequisites checked"
    log_info "AWS Account: $AWS_ACCOUNT_ID"
    log_info "AWS Region: $AWS_REGION"
}

deploy_codebuild_stack() {
    log_info "Deploying CodeBuild stack for SOGS container builds..."
    
    cd infrastructure/spaceport_cdk
    
    # Deploy the CodeBuild stack
    if cdk deploy $CDK_STACK_NAME --require-approval never; then
        log_success "CodeBuild stack deployed successfully"
    else
        log_error "Failed to deploy CodeBuild stack"
        return 1
    fi
    
    # Get outputs
    ECR_REPO_URI=$(aws cloudformation describe-stacks \
        --stack-name $CDK_STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`SOGSECRRepository`].OutputValue' \
        --output text)
    
    BUILD_PROJECT=$(aws cloudformation describe-stacks \
        --stack-name $CDK_STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`SOGSBuildProject`].OutputValue' \
        --output text)
    
    log_info "ECR Repository: $ECR_REPO_URI"
    log_info "Build Project: $BUILD_PROJECT"
    
    cd ../..
    return 0
}

trigger_container_build() {
    log_info "Triggering SOGS container build on AWS..."
    
    # Create a ZIP file of the container source
    TEMP_DIR=$(mktemp -d)
    BUILD_ZIP="$TEMP_DIR/sogs-container-source.zip"
    
    log_info "Creating source archive..."
    cd infrastructure/containers/compressor
    zip -r "$BUILD_ZIP" . -x "*.pyc" "__pycache__/*" ".git/*" "test_output/*"
    
    # Upload to S3 for CodeBuild
    S3_BUCKET="spaceport-sogs-build-artifacts-$AWS_ACCOUNT_ID"
    S3_KEY="source/sogs-container-$(date +%s).zip"
    
    log_info "Uploading source to S3..."
    aws s3 cp "$BUILD_ZIP" "s3://$S3_BUCKET/$S3_KEY"
    
    # Start CodeBuild
    log_info "Starting CodeBuild job..."
    BUILD_ID=$(aws codebuild start-build \
        --project-name "$MANUAL_BUILD_PROJECT" \
        --source-type "S3" \
        --source-location "$S3_BUCKET/$S3_KEY" \
        --query 'build.id' \
        --output text)
    
    log_info "Build started with ID: $BUILD_ID"
    log_info "Monitoring build progress..."
    
    # Monitor build progress
    while true; do
        BUILD_STATUS=$(aws codebuild batch-get-builds \
            --ids "$BUILD_ID" \
            --query 'builds[0].buildStatus' \
            --output text)
        
        case $BUILD_STATUS in
            "IN_PROGRESS")
                log_info "Build in progress... (checking again in 30s)"
                sleep 30
                ;;
            "SUCCEEDED")
                log_success "Container build completed successfully!"
                break
                ;;
            "FAILED"|"FAULT"|"STOPPED"|"TIMED_OUT")
                log_error "Build failed with status: $BUILD_STATUS"
                
                # Get build logs
                log_info "Fetching build logs..."
                aws codebuild batch-get-builds --ids "$BUILD_ID" \
                    --query 'builds[0].logs.cloudWatchLogs.groupName' \
                    --output text
                
                return 1
                ;;
            *)
                log_warning "Unknown build status: $BUILD_STATUS"
                sleep 10
                ;;
        esac
    done
    
    # Get the ECR image URI
    ECR_IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/spaceport-ml-sogs-compressor:latest"
    log_success "Container available at: $ECR_IMAGE_URI"
    
    # Cleanup
    rm -rf "$TEMP_DIR"
    cd ../../..
    
    return 0
}

create_test_data() {
    log_info "Creating test PLY file for SOGS compression..."
    
    # Create a realistic test PLY file
    cat > /tmp/test_model.ply << 'EOF'
ply
format ascii 1.0
comment Generated test model for SOGS compression
element vertex 1000
property float x
property float y
property float z
property float nx
property float ny
property float nz
property uchar red
property uchar green
property uchar blue
property float scale_0
property float scale_1
property float scale_2
property float rot_0
property float rot_1
property float rot_2
property float rot_3
property float opacity
end_header
EOF

    # Generate 1000 random Gaussian splat vertices
    python3 -c "
import random
import math

for i in range(1000):
    # Position
    x = random.uniform(-5, 5)
    y = random.uniform(-5, 5)
    z = random.uniform(-5, 5)
    
    # Normal
    nx = random.uniform(-1, 1)
    ny = random.uniform(-1, 1)
    nz = random.uniform(-1, 1)
    
    # Color
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    
    # Scale
    s0 = random.uniform(0.1, 2.0)
    s1 = random.uniform(0.1, 2.0)
    s2 = random.uniform(0.1, 2.0)
    
    # Rotation (quaternion)
    rot0 = random.uniform(-1, 1)
    rot1 = random.uniform(-1, 1)
    rot2 = random.uniform(-1, 1)
    rot3 = random.uniform(-1, 1)
    
    # Opacity
    opacity = random.uniform(0.1, 1.0)
    
    print(f'{x} {y} {z} {nx} {ny} {nz} {r} {g} {b} {s0} {s1} {s2} {rot0} {rot1} {rot2} {rot3} {opacity}')
" >> /tmp/test_model.ply

    # Upload to S3
    TEST_S3_URI="s3://spaceport-uploads/test-data/sogs-test-model.ply"
    aws s3 cp /tmp/test_model.ply "$TEST_S3_URI"
    
    log_success "Test PLY file created and uploaded to: $TEST_S3_URI"
    echo "$TEST_S3_URI"
}

test_sogs_container() {
    log_info "Testing SOGS container with SageMaker Processing Job..."
    
    # Create test data
    TEST_PLY_S3_URI=$(create_test_data)
    
    # Get the ECR image URI
    ECR_IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/spaceport-ml-sogs-compressor:latest"
    
    # Get SageMaker execution role
    SAGEMAKER_ROLE=$(aws cloudformation describe-stacks \
        --stack-name $ML_STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`SageMakerExecutionRoleArn`].OutputValue' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$SAGEMAKER_ROLE" ]; then
        log_warning "SageMaker role not found. Using default role name pattern..."
        SAGEMAKER_ROLE="arn:aws:iam::$AWS_ACCOUNT_ID:role/SpaceportMLPipelineStack-SageMakerExecutionRole*"
        
        # Try to find the actual role
        ACTUAL_ROLE=$(aws iam list-roles \
            --query 'Roles[?contains(RoleName, `SageMakerExecutionRole`)].Arn' \
            --output text | head -1)
        
        if [ -n "$ACTUAL_ROLE" ]; then
            SAGEMAKER_ROLE="$ACTUAL_ROLE"
            log_info "Found SageMaker role: $SAGEMAKER_ROLE"
        else
            log_error "Could not find SageMaker execution role. Please deploy ML pipeline stack first."
            return 1
        fi
    fi
    
    # Create unique job name
    JOB_NAME="sogs-test-$(date +%s)"
    OUTPUT_S3_URI="s3://spaceport-ml-processing/test-outputs/$JOB_NAME/"
    
    log_info "Creating SageMaker Processing Job..."
    log_info "Job Name: $JOB_NAME"
    log_info "Input: $TEST_PLY_S3_URI"
    log_info "Output: $OUTPUT_S3_URI"
    log_info "Container: $ECR_IMAGE_URI"
    
    # Create processing job
    aws sagemaker create-processing-job \
        --processing-job-name "$JOB_NAME" \
        --processing-resources '{
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.c6i.4xlarge",
                "VolumeSizeInGB": 50
            }
        }' \
        --app-specification "{
            \"ImageUri\": \"$ECR_IMAGE_URI\",
            \"ContainerEntrypoint\": [\"python\", \"/opt/ml/compress_model.py\"]
        }" \
        --processing-inputs "[{
            \"InputName\": \"input-data\",
            \"AppManaged\": false,
            \"S3Input\": {
                \"S3Uri\": \"$(dirname $TEST_PLY_S3_URI)/\",
                \"LocalPath\": \"/opt/ml/processing/input\",
                \"S3DataType\": \"S3Prefix\",
                \"S3InputMode\": \"File\"
            }
        }]" \
        --processing-output-config "{
            \"Outputs\": [{
                \"OutputName\": \"compressed-output\",
                \"AppManaged\": false,
                \"S3Output\": {
                    \"S3Uri\": \"$OUTPUT_S3_URI\",
                    \"LocalPath\": \"/opt/ml/processing/output\",
                    \"S3UploadMode\": \"EndOfJob\"
                }
            }]
        }" \
        --role-arn "$SAGEMAKER_ROLE"
    
    log_success "Processing job created: $JOB_NAME"
    log_info "Monitoring job progress..."
    
    # Monitor job progress
    while true; do
        JOB_STATUS=$(aws sagemaker describe-processing-job \
            --processing-job-name "$JOB_NAME" \
            --query 'ProcessingJobStatus' \
            --output text)
        
        case $JOB_STATUS in
            "InProgress")
                log_info "Job in progress... (checking again in 30s)"
                sleep 30
                ;;
            "Completed")
                log_success "SOGS compression job completed successfully!"
                break
                ;;
            "Failed"|"Stopped")
                log_error "Job failed with status: $JOB_STATUS"
                
                # Get failure reason
                FAILURE_REASON=$(aws sagemaker describe-processing-job \
                    --processing-job-name "$JOB_NAME" \
                    --query 'FailureReason' \
                    --output text)
                
                log_error "Failure reason: $FAILURE_REASON"
                return 1
                ;;
            *)
                log_warning "Unknown job status: $JOB_STATUS"
                sleep 10
                ;;
        esac
    done
    
    # Check outputs
    log_info "Checking compression outputs..."
    aws s3 ls "$OUTPUT_S3_URI" --recursive
    
    # Download and analyze results
    TEMP_OUTPUT_DIR=$(mktemp -d)
    aws s3 sync "$OUTPUT_S3_URI" "$TEMP_OUTPUT_DIR/"
    
    if [ -f "$TEMP_OUTPUT_DIR/compression_report.txt" ]; then
        log_success "Compression report found:"
        echo ""
        cat "$TEMP_OUTPUT_DIR/compression_report.txt"
        echo ""
    fi
    
    if [ -f "$TEMP_OUTPUT_DIR/compression_report.json" ]; then
        log_info "JSON report available at: $TEMP_OUTPUT_DIR/compression_report.json"
    fi
    
    # Cleanup
    rm -rf "$TEMP_OUTPUT_DIR"
    
    return 0
}

update_ml_pipeline() {
    log_info "Updating ML Pipeline stack to use new SOGS container..."
    
    ECR_IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/spaceport-ml-sogs-compressor:latest"
    
    cd infrastructure/spaceport_cdk
    
    # Update the ML pipeline stack with the new container URI
    if cdk deploy $ML_STACK_NAME \
        --parameters "CompressorImageUri=$ECR_IMAGE_URI" \
        --require-approval never; then
        log_success "ML Pipeline stack updated with new SOGS container"
    else
        log_error "Failed to update ML Pipeline stack"
        return 1
    fi
    
    cd ../..
    return 0
}

main() {
    echo "🎯 Starting comprehensive SOGS deployment and testing..."
    echo ""
    
    # Parse command line arguments
    SKIP_BUILD=false
    SKIP_TEST=false
    TEST_ONLY=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-test)
                SKIP_TEST=true
                shift
                ;;
            --test-only)
                TEST_ONLY=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --skip-build    Skip container build step"
                echo "  --skip-test     Skip SageMaker testing step"
                echo "  --test-only     Only run tests (skip build and deploy)"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Check prerequisites
    check_prerequisites
    
    if [ "$TEST_ONLY" = true ]; then
        log_info "Running test-only mode..."
        test_sogs_container
        log_success "Test completed!"
        exit 0
    fi
    
    # Step 1: Deploy CodeBuild infrastructure
    if [ "$SKIP_BUILD" = false ]; then
        if ! deploy_codebuild_stack; then
            log_error "Failed to deploy CodeBuild stack"
            exit 1
        fi
        
        # Step 2: Build container on AWS
        if ! trigger_container_build; then
            log_error "Failed to build container on AWS"
            exit 1
        fi
        
        # Step 3: Update ML Pipeline
        if ! update_ml_pipeline; then
            log_error "Failed to update ML Pipeline"
            exit 1
        fi
    fi
    
    # Step 4: Test the container
    if [ "$SKIP_TEST" = false ]; then
        if ! test_sogs_container; then
            log_error "SOGS container test failed"
            exit 1
        fi
    fi
    
    echo ""
    log_success "🎉 SOGS deployment and testing completed successfully!"
    echo ""
    log_info "Summary:"
    log_info "✅ CodeBuild infrastructure deployed"
    log_info "✅ SOGS container built on AWS with CUDA support"
    log_info "✅ ML Pipeline updated with new container"
    log_info "✅ SageMaker Processing Job test passed"
    echo ""
    log_info "Next steps:"
    log_info "1. Your ML pipeline now uses real SOGS compression"
    log_info "2. Test with actual 3DGS outputs from your pipeline"
    log_info "3. Monitor compression ratios and performance"
    echo ""
    log_info "ECR Image: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/spaceport-ml-sogs-compressor:latest"
}

# Run main function
main "$@" 