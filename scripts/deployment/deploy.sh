#!/bin/bash
set -e

# Unified Production Deployment Script - OPTIMIZED FOR EFFICIENCY
# Builds and deploys specified container(s) to AWS ECR with advanced caching.

# --- Configuration ---
AWS_REGION="us-west-2"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
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
get_repo_name() {
    local container_name=$1
    
    case "$container_name" in
        "sfm") echo "spaceport/sfm";;
        "3dgs") echo "spaceport/3dgs";;
        "compressor") echo "spaceport/compressor";;
        *) error "Invalid container name provided to get_repo_name: $container_name";;
    esac
}

# Function to build and push a single container with caching
deploy_container() {
  local container_name=$1
  local repo_name
  repo_name=$(get_repo_name "$container_name")
  local build_cache_ref
  build_cache_ref="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${repo_name}:buildcache"
  local branch_tag="${BRANCH_SUFFIX:-}"
  local base_image="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${repo_name}:base"
  local build_stage="app"

  log "--- Starting OPTIMIZED deployment for: ${container_name} ---"

  local ecr_uri="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${repo_name}"
  local container_dir="${PROJECT_ROOT}/infrastructure/containers/${container_name}"

  if [[ ! -d "$container_dir" ]]; then
    error "Container directory not found: ${container_dir}"
  fi

  log "Building container from: ${container_dir}"
  
  # Try to pull existing image for layer caching
  log "Pulling existing image and cache for layer reuse..."
  docker pull "${ecr_uri}:latest" || log "No existing image found, building from scratch..."
  docker pull "${build_cache_ref}" || log "No registry cache yet for ${container_name}"
  docker pull "${base_image}" || log "No base image yet for ${container_name}"
  
  # Build base image if missing
  if ! aws ecr describe-images --region "${AWS_REGION}" --repository-name "${repo_name}" --image-ids imageTag=base >/dev/null 2>&1; then
    local base_file="${container_dir}/Dockerfile.base"
    if [[ -f "$base_file" ]]; then
      log "Building base image for ${container_name}..."
      docker buildx build \
        --platform linux/amd64 \
        --file "${base_file}" \
        --tag "${repo_name}:base" \
        --progress plain \
        --load \
        "${container_dir}"
      docker tag "${repo_name}:base" "${base_image}"
      docker push "${base_image}"
      log "Base image built and pushed: ${base_image}"
    else
      log "No Dockerfile.base for ${container_name}; skipping base build."
    fi
  fi

  # Build with advanced caching options
  log "Building with Docker BuildKit and layer caching..."
  docker buildx build \
    --platform linux/amd64 \
    --file "${container_dir}/Dockerfile" \
    --build-arg BASE_IMAGE="${base_image}" \
    --tag "${repo_name}:latest" \
    --cache-from "type=registry,ref=${build_cache_ref}" \
    --cache-from "type=registry,ref=${ecr_uri}:latest" \
    --cache-from "${base_image}" \
    --cache-to "type=registry,mode=max,ref=${build_cache_ref}" \
    --progress plain \
    --load \
    "${container_dir}"
  
  log "Build complete with caching optimizations."

  log "Tagging images..."
  docker tag "${repo_name}:latest" "${ecr_uri}:latest"
  if [ -n "$branch_tag" ]; then
    docker tag "${repo_name}:latest" "${ecr_uri}:${branch_tag}"
    log "Tags created: latest, ${branch_tag}"
  else
    log "Tags created: latest"
  fi

  log "Pushing images to ECR..."
  docker push "${ecr_uri}:latest"
  if [ -n "$branch_tag" ]; then
    docker push "${ecr_uri}:${branch_tag}"
  fi
  log "Successfully pushed to ${ecr_uri}"
  
  # Clean up local images to save space
  log "Cleaning up local images..."
  docker rmi "${repo_name}:latest" || true
  docker rmi "${ecr_uri}:latest" || true
  if [ -n "$branch_tag" ]; then
    docker rmi "${ecr_uri}:${branch_tag}" || true
  fi
  
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
