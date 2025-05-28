#!/bin/bash
# Development workflow helper

case "$1" in
    "test-local")
        echo "🧪 Testing container locally..."
        docker run --rm -it \
            -e INPUT_BUCKET=test-bucket \
            -e OUTPUT_BUCKET=test-bucket \
            -e JOB_NAME=test-job \
            spaceport/$2:latest
        ;;
    "build-test")
        echo "🔨 Building and testing $2..."
        ./infrastructure/containers/scripts/build-single.sh $2
        ./infrastructure/containers/scripts/dev-workflow.sh test-local $2
        ;;
    "deploy")
        echo "🚀 Building and deploying $2..."
        ./infrastructure/containers/scripts/build-single.sh $2 --push
        ;;
    *)
        echo "Usage: $0 {test-local|build-test|deploy} <container-name>"
        echo "Examples:"
        echo "  $0 build-test sfm"
        echo "  $0 deploy 3dgs"
        ;;
esac 