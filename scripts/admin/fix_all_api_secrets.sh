#!/bin/bash
# Comprehensive API Secrets Fix Script
# Updates all GitHub secrets with correct API Gateway URLs

set -euo pipefail

echo "🔧 FIXING ALL API SECRETS"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    print_error "GitHub CLI not found. Install with: brew install gh"
    exit 1
fi

# Check if user is authenticated
if ! gh auth status &> /dev/null; then
    print_error "Not authenticated with GitHub. Run: gh auth login"
    exit 1
fi

print_status "Starting API secrets update..."

# Define all the API URLs (staging)
declare -A API_URLS=(
    ["WAITLIST_API_URL_PREVIEW"]="https://h6ogvocgk4.execute-api.us-west-2.amazonaws.com/prod"
    ["DRONE_PATH_API_URL_PREVIEW"]="https://yhpjmfhdxf.execute-api.us-west-2.amazonaws.com/prod"
    ["FILE_UPLOAD_API_URL_PREVIEW"]="https://xv4bpkwlb8.execute-api.us-west-2.amazonaws.com/prod"
    ["PROJECTS_API_URL_PREVIEW"]="https://mca9yf1vgl.execute-api.us-west-2.amazonaws.com/prod"
    ["PASSWORD_RESET_API_URL_PREVIEW"]="https://mx549qsbel.execute-api.us-west-2.amazonaws.com/prod"
    ["INVITE_API_URL_PREVIEW"]="https://xtmhni13l2.execute-api.us-west-2.amazonaws.com/prod"
    ["BETA_ACCESS_API_URL_PREVIEW"]="https://y5fej7zgx8.execute-api.us-west-2.amazonaws.com/prod"
    ["SUBSCRIPTION_API_URL_PREVIEW"]="https://xduxbyklm1.execute-api.us-west-2.amazonaws.com/prod"
    ["ML_PIPELINE_API_URL_PREVIEW"]="https://wz0ezgptue.execute-api.us-west-2.amazonaws.com/prod"
)

# Update each secret
for secret_name in "${!API_URLS[@]}"; do
    url="${API_URLS[$secret_name]}"
    
    print_status "Updating $secret_name..."
    
    if gh secret set "$secret_name" --body "$url"; then
        print_success "Updated $secret_name"
    else
        print_error "Failed to update $secret_name"
        exit 1
    fi
done

print_success "All API secrets updated successfully!"

echo ""
echo "📋 SUMMARY:"
echo "==========="
echo "Updated ${#API_URLS[@]} GitHub secrets with current API Gateway URLs"
echo ""
echo "🔍 VERIFICATION:"
echo "================"
echo "To verify the secrets are correct, run:"
echo "  python3 scripts/admin/test_api_endpoints.py"
echo ""
echo "🏭 PRODUCTION DEPLOYMENT:"
echo "========================="
echo "When you deploy to production (main branch), you'll need to:"
echo "1. Get production API URLs from CloudFormation"
echo "2. Update the corresponding *_PROD secrets"
echo ""
echo "Commands for production:"
echo "  aws cloudformation describe-stacks --stack-name SpaceportStack --query \"Stacks[0].Outputs[?contains(OutputKey, 'ApiUrl')].{Key:OutputKey,Value:OutputValue}\" --output table"
echo "  aws cloudformation describe-stacks --stack-name SpaceportAuthStack --query \"Stacks[0].Outputs[?contains(OutputKey, 'ApiUrl')].{Key:OutputKey,Value:OutputValue}\" --output table"
echo "  aws cloudformation describe-stacks --stack-name SpaceportMLPipelineStack --query \"Stacks[0].Outputs[?contains(OutputKey, 'ApiUrl')].{Key:OutputKey,Value:OutputValue}\" --output table"
echo ""
echo "Then update the *_PROD secrets with the production URLs"
