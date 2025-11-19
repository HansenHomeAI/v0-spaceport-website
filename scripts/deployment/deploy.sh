#!/bin/bash
set -e

# Unified Production Deployment Script - OPTIMIZED FOR EFFICIENCY
# Builds and deploys specified container(s) to AWS ECR with advanced caching.

# --- Configuration ---
AWS_REGION="us-west-2"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BRANCH_SUFFIX="${BRANCH_SUFFIX:-}"

# Enable Docker BuildKit for better caching and performance
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain

# Get the absolute path to the project root
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/../.." &>/dev/null && pwd)

# --- Helper Functions ---
log() {
  echo "✅ [$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error() {
  echo "❌ [$(date +'%Y-%m-%d %H:%M:%S')] $1" >&2
  exit 1
}

# --- Optimization Functions ---

# Function to set up Docker layer caching
setup_docker_cache() {
  log "Setting up Docker layer caching..."
  
  # Create cache directory
  mkdir -p /tmp/docker-cache
  
  # Set up buildx for caching if not already done
  if ! docker buildx ls | grep -q "mybuilder"; then
    log "Creating Docker buildx instance..."
    docker buildx create --name mybuilder --use || true
    docker buildx inspect --bootstrap || true
  fi
  
  log "Docker caching setup complete."
}

# Function to pull base images for caching
cache_base_images() {
  log "Caching base images..."
  
  # Pull common base images in parallel
  {
    docker pull public.ecr.aws/nvidia/cuda:11.8.0-devel-ubuntu22.04 || true &
    docker pull public.ecr.aws/nvidia/cuda:12.9.1-runtime-ubuntu22.04 || true &
    docker pull python:3.9-slim || true &
    wait
  }
  
  log "Base images cached."
}

# --- Main Functions ---

# Function to log in to AWS ECR
login_ecr() {
  log "Authenticating with AWS ECR..."
  aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
  
  log "Authenticating with SageMaker ECR registry..."
  aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "763104351884.dkr.ecr.${AWS_REGION}.amazonaws.com"
  
  log "ECR login successful."
}

# Function to get repository name for a container
# Accepts optional branch suffix for branch-specific repos
get_repo_name() {
    local container_name=$1
    local branch_suffix=${BRANCH_SUFFIX:-""}
    
    local base_repo
    case "$container_name" in
        "sfm") base_repo="spaceport/sfm";;
        "3dgs") base_repo="spaceport/3dgs";;
        "compressor") base_repo="spaceport/compressor";;
        *) error "Invalid container name provided to get_repo_name: $container_name";;
    esac
    
    # If branch suffix exists, append it to repo name
    if [ -n "$branch_suffix" ]; then
        echo "${base_repo}-${branch_suffix}"
    else
        echo "$base_repo"
    fi
}

# Function to build and push a single container with caching
deploy_container() {
  local container_name=$1
  local repo_name
  repo_name=$(get_repo_name "$container_name")

  log "--- Starting OPTIMIZED deployment for: ${container_name} ---"

  local ecr_uri="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${repo_name}"
  local container_dir="${PROJECT_ROOT}/infrastructure/containers/${container_name}"

  if [[ ! -d "$container_dir" ]]; then
    error "Container directory not found: ${container_dir}"
  fi

  log "Building container from: ${container_dir}"
  
  # Try to pull existing image for layer caching
  log "Pulling existing image for layer caching..."
  docker pull "${ecr_uri}:latest" || {
    log "No existing image found, building from scratch..."
  }
  
  # Build with advanced caching options
  log "Building with Docker BuildKit and layer caching..."
  docker buildx build \
    --platform linux/amd64 \
    --file "${container_dir}/Dockerfile" \
    --tag "${repo_name}:latest" \
    --cache-from "${ecr_uri}:latest" \
    --cache-from "${ecr_uri}:cache" \
    --cache-to "type=local,dest=/tmp/docker-cache/${container_name}" \
    --cache-to "type=inline" \
    --progress plain \
    --load \
    "${container_dir}"
  
  log "Build complete with caching optimizations."

  log "Tagging images..."
  docker tag "${repo_name}:latest" "${ecr_uri}:latest"
  docker tag "${repo_name}:latest" "${ecr_uri}:${TIMESTAMP}"
  docker tag "${repo_name}:latest" "${ecr_uri}:cache"
  log "Tags created: latest, ${TIMESTAMP}, cache"

  log "Pushing images to ECR..."
  # Push in parallel for faster deployment
  {
    docker push "${ecr_uri}:latest" &
    docker push "${ecr_uri}:${TIMESTAMP}" &
    docker push "${ecr_uri}:cache" &
    wait
  }
  
  log "Successfully pushed to ${ecr_uri}"
  
  # Clean up local images to save space
  log "Cleaning up local images..."
  docker rmi "${repo_name}:latest" || true
  docker rmi "${ecr_uri}:latest" || true
  docker rmi "${ecr_uri}:${TIMESTAMP}" || true
  docker rmi "${ecr_uri}:cache" || true
  
  log "--- Finished OPTIMIZED deployment for: ${container_name} ---"
  echo
}

# Function to clean up after deployment
cleanup() {
  log "Performing cleanup..."
  
  # Remove unused images and containers
  docker system prune -f --volumes || true
  
  # Clean up buildx cache older than 7 days
  find /tmp/docker-cache -type f -mtime +7 -delete 2>/dev/null || true
  
  log "Cleanup complete."
}

# --- Script Main ---
main() {
  if [[ $# -eq 0 ]]; then
    error "Usage: $0 [sfm|3dgs|compressor|all] or multiple containers separated by spaces"
  fi

  # Setup optimization
  setup_docker_cache
  cache_base_images
  login_ecr
  echo

  # Handle multiple arguments - either "all" or specific container names
  if [[ "$*" == *"all"* ]]; then
    log "Deploying all containers with optimization..."
    for container in "sfm" "3dgs" "compressor"; do
      deploy_container "$container"
    done
    log "All containers deployed successfully with optimization!"
  else
    # Deploy specific containers passed as arguments
    log "Deploying specific containers with optimization: $*"
    for container in "$@"; do
      # Validate each container name
      case "$container" in
          "sfm"|"3dgs"|"compressor")
              deploy_container "$container"
              ;;
          *)
              error "Invalid container name: $container. Must be one of: sfm, 3dgs, compressor, all."
              ;;
      esac
    done
    log "Specified containers deployed successfully with optimization!"
  fi

  cleanup
  log "Optimized deployment script finished."
}

main "$@" 
