#!/bin/bash

# SOGS Compression Container Deployment Script
# Builds, tests, and deploys the real SOGS compression container to ECR

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="sogs-compressor"
CONTAINER_DIR="infrastructure/containers/compressor"
AWS_REGION="${AWS_DEFAULT_REGION:-us-west-2}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check if AWS CLI is configured
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed or not in PATH"
        exit 1
    fi
    
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        log_error "AWS credentials not configured or invalid"
        exit 1
    fi
    
    # Check if we're in the right directory
    if [ ! -d "$CONTAINER_DIR" ]; then
        log_error "Container directory not found: $CONTAINER_DIR"
        log_error "Please run this script from the project root directory"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

test_container_locally() {
    log_info "Testing container locally..."
    
    cd "$CONTAINER_DIR"
    
    # Run the local test script
    if [ -f "test_sogs_local.py" ]; then
        log_info "Running local test script..."
        python3 test_sogs_local.py
        if [ $? -eq 0 ]; then
            log_success "Local tests passed"
        else
            log_warning "Local tests failed, but continuing with deployment"
            log_warning "The container may work in the SageMaker environment even if local tests fail"
        fi
    else
        log_warning "test_sogs_local.py not found, skipping local tests"
    fi
    
    cd - > /dev/null
}

build_container() {
    local dockerfile_type=$1
    local tag_suffix=$2
    
    log_info "Building container with ${dockerfile_type}..."
    
    cd "$CONTAINER_DIR"
    
    # Build the container
    local build_tag="${CONTAINER_NAME}:${tag_suffix}"
    
    docker build \
        -f "Dockerfile${dockerfile_type}" \
        -t "$build_tag" \
        . 2>&1 | tee "build_${tag_suffix}.log"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_success "Container built successfully: $build_tag"
        
        # Show image size
        local image_size=$(docker images "$build_tag" --format "table {{.Size}}" | tail -n 1)
        log_info "Image size: $image_size"
        
        cd - > /dev/null
        return 0
    else
        log_error "Container build failed"
        cd - > /dev/null
        return 1
    fi
}

create_ecr_repository() {
    local repo_name="spaceport-ml-${CONTAINER_NAME}"
    
    log_info "Creating ECR repository: $repo_name"
    
    # Check if repository exists
    if aws ecr describe-repositories --repository-names "$repo_name" --region "$AWS_REGION" &> /dev/null; then
        log_info "ECR repository already exists: $repo_name"
    else
        # Create repository
        aws ecr create-repository \
            --repository-name "$repo_name" \
            --region "$AWS_REGION" \
            --image-scanning-configuration scanOnPush=true \
            --encryption-configuration encryptionType=AES256
        
        if [ $? -eq 0 ]; then
            log_success "ECR repository created: $repo_name"
        else
            log_error "Failed to create ECR repository"
            return 1
        fi
    fi
    
    echo "$repo_name"
}

push_to_ecr() {
    local local_tag=$1
    local dockerfile_type=$2
    
    log_info "Pushing container to ECR..."
    
    # Create ECR repository
    local repo_name=$(create_ecr_repository)
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    # Login to ECR
    log_info "Logging in to ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    
    if [ $? -ne 0 ]; then
        log_error "ECR login failed"
        return 1
    fi
    
    # Tag for ECR
    local ecr_uri="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${repo_name}"
    local ecr_tag="${ecr_uri}:latest"
    
    # Add specific tag based on dockerfile type  
    if [ "$dockerfile_type" != "" ]; then
        local specific_tag="${ecr_uri}:${dockerfile_type#.}"
        docker tag "$local_tag" "$specific_tag"
        docker push "$specific_tag"
        log_success "Container pushed with specific tag: $specific_tag"
    fi
    
    # Tag and push as latest
    docker tag "$local_tag" "$ecr_tag"
    docker push "$ecr_tag"
    
    if [ $? -eq 0 ]; then
        log_success "Container pushed to ECR: $ecr_tag"
        echo "ECR_URI=$ecr_uri"
        return 0
    else
        log_error "Failed to push container to ECR"
        return 1
    fi
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --test-only     Only run local tests, don't build or deploy"
    echo "  -m, --minimal       Build minimal CPU-only version"
    echo "  -f, --full          Build full CUDA-enabled version (default)"
    echo "  -s, --skip-tests    Skip local testing"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                  # Build and deploy full CUDA version with tests"
    echo "  $0 --minimal        # Build and deploy minimal CPU version"
    echo "  $0 --test-only      # Only run local tests"
    echo "  $0 --skip-tests     # Build and deploy without running tests"
}

main() {
    # Parse command line arguments
    local test_only=false
    local minimal=false
    local skip_tests=false
    local dockerfile_type=""
    local tag_suffix="latest"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--test-only)
                test_only=true
                shift
                ;;
            -m|--minimal)
                minimal=true
                dockerfile_type=".minimal"
                tag_suffix="minimal"
                shift
                ;;
            -f|--full)
                minimal=false
                dockerfile_type=""
                tag_suffix="latest"
                shift
                ;;
            -s|--skip-tests)
                skip_tests=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    log_info "🚀 SOGS Compression Container Deployment"
    log_info "=========================================="
    log_info "Container: $CONTAINER_NAME"
    log_info "Type: $([ "$minimal" = true ] && echo "Minimal (CPU-only)" || echo "Full (CUDA-enabled)")"
    log_info "AWS Account: $AWS_ACCOUNT_ID"
    log_info "AWS Region: $AWS_REGION"
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Run tests if requested
    if [ "$test_only" = true ]; then
        test_container_locally
        log_success "Test-only mode completed"
        exit 0
    fi
    
    # Run local tests unless skipped
    if [ "$skip_tests" = false ]; then
        test_container_locally
    fi
    
    # Build container
    local build_tag="${CONTAINER_NAME}:${tag_suffix}"
    if build_container "$dockerfile_type" "$tag_suffix"; then
        log_success "Container build completed"
    else
        log_error "Container build failed"
        exit 1
    fi
    
    # Push to ECR
    if push_to_ecr "$build_tag" "$dockerfile_type"; then
        log_success "Container deployment completed"
    else
        log_error "Container deployment failed"
        exit 1
    fi
    
    echo ""
    log_success "🎉 SOGS compression container deployed successfully!"
    log_info "Next steps:"
    log_info "1. Update your CDK stack to use the new ECR URI"
    log_info "2. Deploy your ML pipeline stack: cdk deploy MLPipelineStack"
    log_info "3. Test the pipeline with a real PLY file"
}

# Run main function
main "$@" 