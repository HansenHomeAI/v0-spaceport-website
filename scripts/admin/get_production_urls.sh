#!/bin/bash
# Get Production API URLs from CloudFormation
# Run this after deploying to main branch

set -euo pipefail

echo "🏭 GETTING PRODUCTION API URLS"
echo "=============================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install it first."
    exit 1
fi

print_status "Fetching production API URLs from CloudFormation..."

# Get URLs from different stacks
echo ""
echo "📋 PRODUCTION API URLS:"
echo "======================="

# Main Spaceport Stack
print_status "Getting URLs from SpaceportStack..."
aws cloudformation describe-stacks \
    --stack-name SpaceportStack \
    --query "Stacks[0].Outputs[?contains(OutputKey, 'ApiUrl')].{Key:OutputKey,Value:OutputValue}" \
    --output table 2>/dev/null || print_warning "SpaceportStack not found or no API URLs"

echo ""

# Auth Stack  
print_status "Getting URLs from SpaceportAuthStack..."
aws cloudformation describe-stacks \
    --stack-name SpaceportAuthStack \
    --query "Stacks[0].Outputs[?contains(OutputKey, 'ApiUrl')].{Key:OutputKey,Value:OutputValue}" \
    --output table 2>/dev/null || print_warning "SpaceportAuthStack not found or no API URLs"

echo ""

# ML Pipeline Stack
print_status "Getting URLs from SpaceportMLPipelineStack..."
aws cloudformation describe-stacks \
    --stack-name SpaceportMLPipelineStack \
    --query "Stacks[0].Outputs[?contains(OutputKey, 'ApiUrl')].{Key:OutputKey,Value:OutputValue}" \
    --output table 2>/dev/null || print_warning "SpaceportMLPipelineStack not found or no API URLs"

echo ""
echo "🔧 UPDATE PRODUCTION SECRETS:"
echo "============================="
echo "Copy and run these commands to update your production secrets:"
echo ""

# Generate the commands (you'll need to fill in the actual URLs)
cat << 'EOF'
# Update these with the actual production URLs from above:

gh secret set WAITLIST_API_URL_PROD --body 'PRODUCTION_WAITLIST_URL'
gh secret set PROJECTS_API_URL_PROD --body 'PRODUCTION_PROJECTS_URL'  
gh secret set DRONE_PATH_API_URL_PROD --body 'PRODUCTION_DRONE_PATH_URL'
gh secret set FILE_UPLOAD_API_URL_PROD --body 'PRODUCTION_FILE_UPLOAD_URL'
gh secret set ML_PIPELINE_API_URL_PROD --body 'PRODUCTION_ML_PIPELINE_URL'
gh secret set BETA_ACCESS_API_URL_PROD --body 'PRODUCTION_BETA_ACCESS_URL'

# Example:
# gh secret set WAITLIST_API_URL_PROD --body 'https://abc123.execute-api.us-west-2.amazonaws.com/prod'
EOF

echo ""
echo "📝 NOTES:"
echo "========="
echo "• Replace 'PRODUCTION_*_URL' with the actual URLs from the CloudFormation outputs above"
echo "• Make sure all stacks deployed successfully before updating secrets"
echo "• Test the production site after updating secrets"
