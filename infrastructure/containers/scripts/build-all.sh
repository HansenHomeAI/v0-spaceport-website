#!/bin/bash
set -e

# Build all containers
# Usage: ./build-all.sh [--push]

PUSH_FLAG=$1

echo "🏗️ Building all ML pipeline containers..."

# List of containers to build
CONTAINERS=("sfm" "3dgs" "compressor")

for container in "${CONTAINERS[@]}"; do
    if [ -d "$container" ]; then
        echo "Building $container..."
        ./scripts/build-single.sh "$container" "$PUSH_FLAG"
        echo ""
    else
        echo "⚠️ Skipping $container (directory not found)"
    fi
done

echo "🎉 All containers built!" 