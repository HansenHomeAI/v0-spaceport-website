#!/bin/bash
set -euo pipefail

AWS_REGION=${AWS_REGION:-us-west-2}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}
BRANCH_SUFFIX=${BRANCH_SUFFIX:-}

if [ -z "$BRANCH_SUFFIX" ]; then
  echo "No branch suffix detected; skipping import step."
  exit 0
fi

if [ $# -eq 0 ]; then
  echo "No containers passed to import script."
  exit 0
fi

import_container() {
  local container_name="$1"
  case "$container_name" in
    sfm|3dgs|compressor) : ;;
    *)
      echo "Skipping unknown container '$container_name'"
      return
      ;;
  esac

  local source_repo="spaceport/${container_name}"
  local target_repo="spaceport/${container_name}-${BRANCH_SUFFIX}"
  local registry="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
  local source_image="${registry}/${source_repo}:latest"
  local target_image="${registry}/${target_repo}:latest"

  echo "Importing ${container_name} from ${source_repo} to ${target_repo} via Docker..."
  docker pull "$source_image"
  docker tag "$source_image" "$target_image"
  docker push "$target_image"
  docker image rm "$target_image" "$source_image" || true
  echo "✔ Imported ${container_name}"
}

for container in "$@"; do
  import_container "$container"
  echo
done

echo "Container import stage complete."
