#!/bin/bash

# Update Production GitHub Secrets with Correct API URLs
# This script ensures all production secrets are set with the correct URLs including proper paths

set -e

echo "🚀 Updating Production GitHub Secrets with Correct API URLs"
echo "=========================================================="

# Production API URLs from CloudFormation outputs
PROJECTS_API_URL="https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod/projects"
DRONE_PATH_API_URL="https://0r3y4bx7lc.execute-api.us-west-2.amazonaws.com/prod"
FILE_UPLOAD_API_URL="https://rf3fnnejg2.execute-api.us-west-2.amazonaws.com/prod"
ML_PIPELINE_API_URL="https://3xzfdyvwpd.execute-api.us-west-2.amazonaws.com/prod"
INVITE_API_URL="https://gxlmbhtbi4.execute-api.us-west-2.amazonaws.com/prod/invite"

# Cognito Configuration (Production)
COGNITO_USER_POOL_ID="us-west-2_a2jf3ldGV"
COGNITO_USER_POOL_CLIENT_ID="3ctkuqu98pmug5k5kgc119sq67"
COGNITO_REGION="us-west-2"

# Waitlist API (from staging - same as production for now)
WAITLIST_API_URL="https://dbzo05n671.execute-api.us-west-2.amazonaws.com/prod/waitlist"
# Feedback API placeholder (update with actual API ID after deployment)
FEEDBACK_API_URL="https://pending-feedback-api.execute-api.us-west-2.amazonaws.com/prod/feedback"
# Contact API placeholder (update with actual API ID after deployment)
CONTACT_API_URL="https://pending-contact-api.execute-api.us-west-2.amazonaws.com/prod/contact"

echo "📋 Production API URLs:"
echo "  Projects API: $PROJECTS_API_URL"
echo "  Drone Path API: $DRONE_PATH_API_URL"
echo "  File Upload API: $FILE_UPLOAD_API_URL"
echo "  ML Pipeline API: $ML_PIPELINE_API_URL"
echo "  Invite API: $INVITE_API_URL"
echo "  Waitlist API: $WAITLIST_API_URL"
echo "  Feedback API: $FEEDBACK_API_URL"
echo "  Contact API: $CONTACT_API_URL"
echo ""

echo "🔐 Cognito Configuration:"
echo "  User Pool ID: $COGNITO_USER_POOL_ID"
echo "  Client ID: $COGNITO_USER_POOL_CLIENT_ID"
echo "  Region: $COGNITO_REGION"
echo ""

# Update GitHub Secrets
echo "🔄 Updating GitHub Secrets..."

# Frontend API URLs (used by Next.js)
gh secret set NEXT_PUBLIC_PROJECTS_API_URL_PROD --body "$PROJECTS_API_URL"
echo "✅ Updated NEXT_PUBLIC_PROJECTS_API_URL_PROD"

gh secret set NEXT_PUBLIC_DRONE_PATH_API_URL_PROD --body "$DRONE_PATH_API_URL"
echo "✅ Updated NEXT_PUBLIC_DRONE_PATH_API_URL_PROD"

gh secret set NEXT_PUBLIC_FILE_UPLOAD_API_URL_PROD --body "$FILE_UPLOAD_API_URL"
echo "✅ Updated NEXT_PUBLIC_FILE_UPLOAD_API_URL_PROD"

gh secret set NEXT_PUBLIC_ML_PIPELINE_API_URL_PROD --body "$ML_PIPELINE_API_URL"
echo "✅ Updated NEXT_PUBLIC_ML_PIPELINE_API_URL_PROD"

gh secret set NEXT_PUBLIC_WAITLIST_API_URL_PROD --body "$WAITLIST_API_URL"
echo "✅ Updated NEXT_PUBLIC_WAITLIST_API_URL_PROD"

gh secret set NEXT_PUBLIC_FEEDBACK_API_URL_PROD --body "$FEEDBACK_API_URL"
echo "✅ Updated NEXT_PUBLIC_FEEDBACK_API_URL_PROD"

gh secret set NEXT_PUBLIC_CONTACT_API_URL_PROD --body "$CONTACT_API_URL"
echo "✅ Updated NEXT_PUBLIC_CONTACT_API_URL_PROD"

# Cognito Configuration
gh secret set COGNITO_USER_POOL_ID_PROD --body "$COGNITO_USER_POOL_ID"
echo "✅ Updated COGNITO_USER_POOL_ID_PROD"

gh secret set COGNITO_USER_POOL_CLIENT_ID_PROD --body "$COGNITO_USER_POOL_CLIENT_ID"
echo "✅ Updated COGNITO_USER_POOL_CLIENT_ID_PROD"

gh secret set COGNITO_REGION_PROD --body "$COGNITO_REGION"
echo "✅ Updated COGNITO_REGION_PROD"

# Admin API URLs (for internal use)
gh secret set INVITE_API_URL_PROD --body "$INVITE_API_URL"
echo "✅ Updated INVITE_API_URL_PROD"

echo ""
echo "🎉 All production secrets updated successfully!"
echo ""
echo "📝 Summary of Changes:"
echo "  - All API URLs now include proper paths (/projects, /invite, etc.)"
echo "  - Cognito configuration updated for production"
echo "  - Frontend and admin API secrets synchronized"
echo ""
echo "🚀 Next steps:"
echo "  1. Production Cloudflare Pages will automatically rebuild with new secrets"
echo "  2. Test production site to ensure all APIs work correctly"
echo "  3. Grant Ethan production beta access permissions"
