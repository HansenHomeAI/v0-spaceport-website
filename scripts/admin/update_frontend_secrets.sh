#!/bin/bash
# Update Frontend-Used API Secrets Only
# Based on actual frontend usage analysis

set -euo pipefail

echo "🔧 UPDATING FRONTEND API SECRETS"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_status "Starting frontend API secrets update..."

# Define ONLY the APIs actually used by the frontend
# Using simple arrays for better compatibility
SECRETS=(
    "WAITLIST_API_URL_PREVIEW"
    "PROJECTS_API_URL_PREVIEW"
    "DRONE_PATH_API_URL_PREVIEW"
    "FILE_UPLOAD_API_URL_PREVIEW"
    "ML_PIPELINE_API_URL_PREVIEW"
    "BETA_ACCESS_API_URL_PREVIEW"
    "FEEDBACK_API_URL_PREVIEW"
)

URLS=(
    "https://h6ogvocgk4.execute-api.us-west-2.amazonaws.com/prod"
    "https://mca9yf1vgl.execute-api.us-west-2.amazonaws.com/prod"
    "https://yhpjmfhdxf.execute-api.us-west-2.amazonaws.com/prod"
    "https://xv4bpkwlb8.execute-api.us-west-2.amazonaws.com/prod"
    "https://wz0ezgptue.execute-api.us-west-2.amazonaws.com/prod"
    "https://y5fej7zgx8.execute-api.us-west-2.amazonaws.com/prod"
    "https://pending-feedback-api.execute-api.us-west-2.amazonaws.com/prod/feedback"
)

# Update each frontend-used secret
for i in "${!SECRETS[@]}"; do
    secret_name="${SECRETS[$i]}"
    url="${URLS[$i]}"
    
    print_status "Updating $secret_name..."
    
    if gh secret set "$secret_name" --body "$url"; then
        print_success "Updated $secret_name"
    else
        print_error "Failed to update $secret_name"
        exit 1
    fi
done

print_success "All frontend API secrets updated successfully!"

echo ""
echo "📋 SUMMARY:"
echo "==========="
echo "Updated ${#SECRETS[@]} frontend-used API secrets"
echo ""
echo "🔍 API USAGE BREAKDOWN:"
echo "======================="
echo "✅ FRONTEND-USED APIs (Updated):"
echo "   • WAITLIST_API_URL_PREVIEW - Waitlist signups"
echo "   • PROJECTS_API_URL_PREVIEW - Project management"
echo "   • DRONE_PATH_API_URL_PREVIEW - Flight path optimization"
echo "   • FILE_UPLOAD_API_URL_PREVIEW - File uploads"
echo "   • ML_PIPELINE_API_URL_PREVIEW - ML processing"
echo "   • BETA_ACCESS_API_URL_PREVIEW - Employee beta access management"
echo "   • FEEDBACK_API_URL_PREVIEW - Footer feedback submissions"
echo ""
echo "❌ NOT USED by Frontend (Skipped):"
echo "   • PASSWORD_RESET_API_URL_PREVIEW - Frontend uses Cognito directly"
echo "   • INVITE_API_URL_PREVIEW - CLI-only admin tool"
echo "   • SUBSCRIPTION_API_URL_PREVIEW - Internal admin use"
echo ""
echo "🔧 FIXED ISSUES:"
echo "================"
echo "✅ Fixed hardcoded ML Pipeline URL in frontend"
echo "✅ Updated only APIs actually used by frontend"
echo "✅ Kept admin APIs for internal use"
echo "✅ Configured beta access API (used by employees on frontend)"
echo ""
echo "🏭 PRODUCTION DEPLOYMENT:"
echo "========================="
echo "When you deploy to production (main branch), update these *_PROD secrets:"
echo "  gh secret set WAITLIST_API_URL_PROD --body 'PRODUCTION_URL'"
echo "  gh secret set PROJECTS_API_URL_PROD --body 'PRODUCTION_URL'"
echo "  gh secret set DRONE_PATH_API_URL_PROD --body 'PRODUCTION_URL'"
echo "  gh secret set FILE_UPLOAD_API_URL_PROD --body 'PRODUCTION_URL'"
echo "  gh secret set ML_PIPELINE_API_URL_PROD --body 'PRODUCTION_URL'"
echo "  gh secret set BETA_ACCESS_API_URL_PROD --body 'PRODUCTION_URL'"
echo "  gh secret set FEEDBACK_API_URL_PROD --body 'PRODUCTION_URL'"
