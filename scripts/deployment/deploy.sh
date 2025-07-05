#!/bin/bash
set -e

# Unified Production Deployment Script
# Builds and deploys specified container(s) to AWS ECR for the correct platform.

# --- Configuration ---
AWS_REGION="us-west-2"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

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

# --- Main Functions ---

# Function to log in to AWS ECR
login_ecr() {
  log "Authenticating with AWS ECR..."
  aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
  log "ECR login successful."
}

# Function to get repository name for a container
get_repo_name() {
    case "$1" in
        "sfm") echo "spaceport/sfm";;
        "3dgs") echo "spaceport/3dgs";;
        "compressor") echo "spaceport/compressor";;
        *) error "Invalid container name provided to get_repo_name: $1";;
    esac
}

# Function to build and push a single container
deploy_container() {
  local container_name=$1
  local repo_name
  repo_name=$(get_repo_name "$container_name")

  log "--- Starting deployment for: ${container_name} ---"

  local ecr_uri="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${repo_name}"
  local container_dir="${PROJECT_ROOT}/infrastructure/containers/${container_name}"

  if [[ ! -d "$container_dir" ]]; then
    error "Container directory not found: ${container_dir}"
  fi

  log "Building container from: ${container_dir}"
  
  # Build for the correct platform for SageMaker
  docker build --platform linux/amd64 -f "${container_dir}/Dockerfile" -t "${repo_name}:latest" "${container_dir}"
  log "Build complete."

  log "Tagging images..."
  docker tag "${repo_name}:latest" "${ecr_uri}:latest"
  docker tag "${repo_name}:latest" "${ecr_uri}:${TIMESTAMP}"
  log "Tags created: latest, ${TIMESTAMP}"

  log "Pushing images to ECR..."
  docker push "${ecr_uri}:latest"
  docker push "${ecr_uri}:${TIMESTAMP}"
  log "Successfully pushed to ${ecr_uri}"
  log "--- Finished deployment for: ${container_name} ---"
  echo
}

# --- Script Main ---
main() {
  if [[ $# -eq 0 ]]; then
    error "Usage: $0 [sfm|3dgs|compressor|all] or multiple containers separated by spaces"
  fi

  login_ecr
  echo

  # Handle multiple arguments - either "all" or specific container names
  if [[ "$*" == *"all"* ]]; then
    log "Deploying all containers..."
    for container in "sfm" "3dgs" "compressor"; do
      deploy_container "$container"
    done
    log "All containers deployed successfully!"
  else
    # Deploy specific containers passed as arguments
    log "Deploying specific containers: $*"
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
    log "Specified containers deployed successfully!"
  fi

  log "Deployment script finished."
}

main "$@" 