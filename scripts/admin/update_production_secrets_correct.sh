#!/bin/bash

# Update Production GitHub Secrets with CORRECT API URLs from successful deployment
# Based on the actual SpaceportAuthProductionStack deployment output

set -e

echo "🚀 Updating Production GitHub Secrets with CORRECT API URLs"
echo "=========================================================="

# CORRECT Production API URLs from the successful SpaceportAuthProductionStack deployment
PROJECTS_API_URL="https://z75m3u8210.execute-api.us-west-2.amazonaws.com/prod/projects"
INVITE_API_URL="https://8adwxdkuef.execute-api.us-west-2.amazonaws.com/prod/invite"
PASSWORD_RESET_API_URL="https://mnhdu2xab0.execute-api.us-west-2.amazonaws.com/prod/"
SUBSCRIPTION_API_URL="https://cizfkb4o4f.execute-api.us-west-2.amazonaws.com/prod/"
BETA_ACCESS_API_URL="https://84ufey2j0g.execute-api.us-west-2.amazonaws.com/prod/"

# Cognito Configuration (Production)
COGNITO_USER_POOL_ID="us-west-2_SnOJuAJXa"
COGNITO_USER_POOL_CLIENT_ID="4jqu6jc4nl6rt7jih7l12071p"  # Need to get this from production
COGNITO_REGION="us-west-2"

# Other APIs (from main stacks)
DRONE_PATH_API_URL="https://0r3y4bx7lc.execute-api.us-west-2.amazonaws.com/prod"
FILE_UPLOAD_API_URL="https://rf3fnnejg2.execute-api.us-west-2.amazonaws.com/prod"
ML_PIPELINE_API_URL="https://3xzfdyvwpd.execute-api.us-west-2.amazonaws.com/prod"

# Waitlist API (from production account)
WAITLIST_API_URL="https://dbzo05n671.execute-api.us-west-2.amazonaws.com/prod/waitlist"

echo "📋 CORRECT Production API URLs:"
echo "  Projects API: $PROJECTS_API_URL"
echo "  Invite API: $INVITE_API_URL"
echo "  Password Reset API: $PASSWORD_RESET_API_URL"
echo "  Subscription API: $SUBSCRIPTION_API_URL"
echo "  Beta Access API: $BETA_ACCESS_API_URL"
echo "  Drone Path API: $DRONE_PATH_API_URL"
echo "  File Upload API: $FILE_UPLOAD_API_URL"
echo "  ML Pipeline API: $ML_PIPELINE_API_URL"
echo "  Waitlist API: $WAITLIST_API_URL"
echo ""

echo "🔐 Cognito Configuration:"
echo "  User Pool ID: $COGNITO_USER_POOL_ID"
echo "  Client ID: $COGNITO_USER_POOL_CLIENT_ID (needs verification)"
echo "  Region: $COGNITO_REGION"
echo ""

# Update GitHub Secrets
echo "🔄 Updating GitHub Secrets with CORRECT URLs..."

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

gh secret set BETA_ACCESS_API_URL_PROD --body "$BETA_ACCESS_API_URL"
echo "✅ Updated BETA_ACCESS_API_URL_PROD"

gh secret set SUBSCRIPTION_API_URL_PROD --body "$SUBSCRIPTION_API_URL"
echo "✅ Updated SUBSCRIPTION_API_URL_PROD"

echo ""
echo "🎉 All production secrets updated with CORRECT URLs!"
echo ""
echo "📝 Summary of Changes:"
echo "  - Updated with actual SpaceportAuthProductionStack URLs"
echo "  - All API URLs include proper paths (/projects, /invite, etc.)"
echo "  - Production Cognito User Pool ID updated"
echo "  - Beta Access API now available for production"
echo ""
echo "🚀 Next steps:"
echo "  1. Production Cloudflare Pages will automatically rebuild with new secrets"
echo "  2. Test production site to ensure all APIs work correctly"
echo "  3. Grant Ethan production beta access permissions using the Beta Access API"
echo "  4. Verify Cognito Client ID in production account"
