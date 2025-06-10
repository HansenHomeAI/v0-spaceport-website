#!/bin/bash

# Enhanced Container Build and Push Script for Spaceport ML Pipeline
# Usage: ./build-and-push.sh [container_name] [tag]

set -e

# Configuration
AWS_REGION=${AWS_REGION:-us-west-2}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BASE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Container definitions (using arrays for compatibility)
CONTAINER_NAMES=("sfm" "3dgs" "compressor")
CONTAINER_REPOS=("spaceport/sfm" "spaceport/3dgs" "spaceport/compressor")

get_repo_name() {
    local container_name=$1
    case $container_name in
        "sfm") echo "spaceport/sfm" ;;
        "3dgs") echo "spaceport/3dgs" ;;
        "compressor") echo "spaceport/compressor" ;;
        *) echo "" ;;
    esac
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Function to check if ECR repository exists
check_ecr_repo() {
    local repo_name=$1
    log "Checking if ECR repository exists: $repo_name"
    
    if aws ecr describe-repositories --repository-names "$repo_name" --region "$AWS_REGION" >/dev/null 2>&1; then
        success "ECR repository exists: $repo_name"
        return 0
    else
        warning "ECR repository does not exist: $repo_name"
        return 1
    fi
}

# Function to authenticate Docker with ECR
ecr_login() {
    log "Authenticating Docker with ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_BASE_URI"
    success "ECR authentication successful"
}

# Function to build and push a single container
build_and_push_container() {
    local container_name=$1
    local tag=${2:-latest}
    local repo_name=$(get_repo_name "$container_name")
    local container_dir="../$container_name"
    
    if [[ -z "$repo_name" ]]; then
        error "Unknown container: $container_name"
    fi
    
    if [[ ! -d "$container_dir" ]]; then
        error "Container directory not found: $container_dir"
    fi
    
    local image_uri="${ECR_BASE_URI}/${repo_name}:${tag}"
    
    log "Building container: $container_name"
    log "Directory: $container_dir"
    log "Image URI: $image_uri"
    
    # Check if ECR repository exists
    if ! check_ecr_repo "$repo_name"; then
        error "ECR repository $repo_name does not exist. Please deploy CDK stack first."
    fi
    
    # Build the container
    log "Building Docker image..."
    cd "$container_dir"
    
    # Choose the appropriate Dockerfile
    local dockerfile="Dockerfile"
    if [[ "$container_name" == "sfm" ]]; then
        # For SfM, use the safer Dockerfile that doesn't require CUDA
        if [[ -f "Dockerfile.safer" ]]; then
            dockerfile="Dockerfile.safer"
            log "Using Dockerfile.safer for SfM container"
        fi
    fi
    
    docker build -f "$dockerfile" --platform linux/amd64 -t "$image_uri" .
    success "Docker build completed: $container_name"
    
    # Push to ECR
    log "Pushing to ECR..."
    docker push "$image_uri"
    success "Push completed: $image_uri"
    
    # Tag as cuda-disabled for SfM
    if [[ "$container_name" == "sfm" ]]; then
        local cuda_disabled_uri="${ECR_BASE_URI}/${repo_name}:cuda-disabled"
        log "Tagging SfM container as cuda-disabled..."
        docker tag "$image_uri" "$cuda_disabled_uri"
        docker push "$cuda_disabled_uri"
        success "SfM container tagged and pushed as cuda-disabled"
    fi
    
    cd - >/dev/null
}

# Function to display usage
usage() {
    echo "Usage: $0 [container_name] [tag]"
    echo ""
    echo "Available containers:"
    for i in "${!CONTAINER_NAMES[@]}"; do
        echo "  - ${CONTAINER_NAMES[$i]} (${CONTAINER_REPOS[$i]})"
    done
    echo ""
    echo "Examples:"
    echo "  $0                    # Build and push all containers with 'latest' tag"
    echo "  $0 sfm               # Build and push only SfM container"
    echo "  $0 3dgs v1.0         # Build and push 3DGS container with tag 'v1.0'"
    echo ""
}

# Main script logic
main() {
    local container_name=$1
    local tag=${2:-latest}
    
    # Change to script directory
    cd "$(dirname "$0")"
    
    log "Enhanced Container Build and Push Script"
    log "AWS Account: $AWS_ACCOUNT_ID"
    log "AWS Region: $AWS_REGION"
    log "ECR Base URI: $ECR_BASE_URI"
    
    # Authenticate with ECR
    ecr_login
    
    if [[ -z "$container_name" ]]; then
        # Build all containers
        log "Building all containers..."
        for container in "${CONTAINER_NAMES[@]}"; do
            echo ""
            log "========================================"
            log "Building container: $container"
            log "========================================"
            build_and_push_container "$container" "$tag"
        done
        echo ""
        success "All containers built and pushed successfully!"
    else
        # Build specific container
        if [[ -z "$(get_repo_name "$container_name")" ]]; then
            error "Unknown container: $container_name"
        fi
        
        build_and_push_container "$container_name" "$tag"
        success "Container $container_name built and pushed successfully!"
    fi
    
    echo ""
    log "========================================"
    log "Container Build Summary"
    log "========================================"
    
    if [[ -z "$container_name" ]]; then
        for container in "${CONTAINER_NAMES[@]}"; do
            local repo_name=$(get_repo_name "$container")
            echo "  📦 $container: ${ECR_BASE_URI}/${repo_name}:${tag}"
        done
    else
        local repo_name=$(get_repo_name "$container_name")
        echo "  📦 $container_name: ${ECR_BASE_URI}/${repo_name}:${tag}"
    fi
    
    echo ""
    success "🎉 Container build and push completed!"
    warning "Remember to update your CDK Lambda environment variables if needed."
}

# Check dependencies
if ! command -v docker &> /dev/null; then
    error "Docker is not installed or not in PATH"
fi

if ! command -v aws &> /dev/null; then
    error "AWS CLI is not installed or not in PATH"
fi

# Check if help was requested
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    usage
    exit 0
fi

# Run main function
main "$@" 