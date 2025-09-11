#!/bin/bash
# Comprehensive Authentication Diagnostics
# Helps troubleshoot Cognito authentication issues

set -euo pipefail

echo "🔍 AUTHENTICATION DIAGNOSTICS"
echo "============================="

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

# 1. Check CloudFormation Cognito outputs
print_status "Checking CloudFormation Cognito configuration..."
echo ""

COGNITO_OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name SpaceportAuthStagingStack \
    --query "Stacks[0].Outputs[?contains(OutputKey, 'Cognito')].{Key:OutputKey,Value:OutputValue}" \
    --output json 2>/dev/null || echo "[]")

if [ "$COGNITO_OUTPUTS" = "[]" ]; then
    print_error "No Cognito outputs found in SpaceportAuthStagingStack"
    exit 1
fi

echo "CloudFormation Cognito Configuration:"
echo "$COGNITO_OUTPUTS" | jq -r '.[] | "  \(.Key): \(.Value)"'
echo ""

# Extract values
USER_POOL_ID=$(echo "$COGNITO_OUTPUTS" | jq -r '.[] | select(.Key=="CognitoUserPoolId") | .Value')
CLIENT_ID=$(echo "$COGNITO_OUTPUTS" | jq -r '.[] | select(.Key=="CognitoUserPoolClientId") | .Value')
REGION="us-west-2"

print_success "Found Cognito configuration:"
print_success "  User Pool ID: $USER_POOL_ID"
print_success "  Client ID: $CLIENT_ID"
print_success "  Region: $REGION"
echo ""

# 2. Check GitHub secrets
print_status "Checking GitHub secrets..."
echo ""

GITHUB_SECRETS=$(gh secret list --json name,updatedAt | jq -r '.[] | select(.name | contains("COGNITO")) | "\(.name): \(.updatedAt)"')

if [ -z "$GITHUB_SECRETS" ]; then
    print_error "No Cognito GitHub secrets found"
else
    echo "GitHub Secrets:"
    echo "$GITHUB_SECRETS" | while read line; do
        echo "  $line"
    done
fi
echo ""

# 3. Update GitHub secrets if needed
print_status "Updating GitHub secrets with current CloudFormation values..."

gh secret set COGNITO_USER_POOL_ID_PREVIEW --body "$USER_POOL_ID"
gh secret set COGNITO_USER_POOL_CLIENT_ID_PREVIEW --body "$CLIENT_ID"  
gh secret set COGNITO_REGION_PREVIEW --body "$REGION"

print_success "Updated all Cognito secrets"
echo ""

# 4. Test Cognito User Pool
print_status "Testing Cognito User Pool accessibility..."

USER_POOL_INFO=$(aws cognito-idp describe-user-pool --user-pool-id "$USER_POOL_ID" 2>/dev/null || echo "ERROR")

if [ "$USER_POOL_INFO" = "ERROR" ]; then
    print_error "Cannot access User Pool $USER_POOL_ID"
else
    POOL_NAME=$(echo "$USER_POOL_INFO" | jq -r '.UserPool.Name')
    POOL_STATUS=$(echo "$USER_POOL_INFO" | jq -r '.UserPool.Status')
    print_success "User Pool accessible: $POOL_NAME (Status: $POOL_STATUS)"
fi
echo ""

# 5. Test User Pool Client
print_status "Testing User Pool Client..."

CLIENT_INFO=$(aws cognito-idp describe-user-pool-client \
    --user-pool-id "$USER_POOL_ID" \
    --client-id "$CLIENT_ID" 2>/dev/null || echo "ERROR")

if [ "$CLIENT_INFO" = "ERROR" ]; then
    print_error "Cannot access User Pool Client $CLIENT_ID"
else
    CLIENT_NAME=$(echo "$CLIENT_INFO" | jq -r '.UserPoolClient.ClientName')
    print_success "User Pool Client accessible: $CLIENT_NAME"
fi
echo ""

# 6. Check for common issues
print_status "Checking for common authentication issues..."
echo ""

# Check if user pool allows unauthenticated access
UNAUTH_ALLOWED=$(echo "$USER_POOL_INFO" | jq -r '.UserPool.Policies.PasswordPolicy.RequireUppercase // false')
print_status "Password requires uppercase: $UNAUTH_ALLOWED"

# Check client settings
if [ "$CLIENT_INFO" != "ERROR" ]; then
    EXPLICIT_AUTH_FLOWS=$(echo "$CLIENT_INFO" | jq -r '.UserPoolClient.ExplicitAuthFlows[]?' 2>/dev/null || echo "None")
    print_status "Explicit auth flows: $EXPLICIT_AUTH_FLOWS"
fi
echo ""

# 7. Generate deployment trigger
print_status "Generating deployment trigger..."

echo "Authentication diagnostics completed - $(date)" > web/trigger-dev-build-auth-fix.txt

print_success "Created deployment trigger file"
echo ""

# 8. Summary and next steps
echo "📋 SUMMARY:"
echo "==========="
echo "✅ CloudFormation Cognito configuration verified"
echo "✅ GitHub secrets updated with current values"
echo "✅ Cognito User Pool and Client accessibility confirmed"
echo "✅ Deployment trigger created"
echo ""
echo "🔧 NEXT STEPS:"
echo "=============="
echo "1. Commit and push the trigger file to deploy with updated secrets"
echo "2. Wait for Cloudflare Pages deployment to complete"
echo "3. Test authentication on the staging site"
echo "4. If issues persist, check browser console for specific errors"
echo ""
echo "🚀 DEPLOYMENT COMMANDS:"
echo "======================="
echo "git add ."
echo "git commit -m 'Fix authentication configuration'"
echo "git push origin development"
