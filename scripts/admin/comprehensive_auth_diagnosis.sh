#!/bin/bash
# Comprehensive Authentication Flow Diagnosis
# This script tests the complete invite-to-signin flow and identifies potential issues

set -euo pipefail

echo "🔍 COMPREHENSIVE AUTHENTICATION DIAGNOSIS"
echo "==========================================="

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

# Test email for invitation
TEST_EMAIL="${1:-test-$(date +%s)@example.com}"
REGION="${2:-us-west-2}"

echo "Testing with email: $TEST_EMAIL"
echo "Region: $REGION"
echo ""

# 1. Check for existing CloudFormation stacks
print_status "Checking CloudFormation stacks..."
STACKS=$(aws cloudformation list-stacks \
    --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
    --query "StackSummaries[?contains(StackName, 'Auth') || contains(StackName, 'Spaceport')].StackName" \
    --output json 2>/dev/null || echo "[]")

if [ "$STACKS" = "[]" ]; then
    print_error "No Spaceport/Auth stacks found"
    exit 1
fi

echo "Found stacks:"
echo "$STACKS" | jq -r '.[] | "  - \(.)"'
echo ""

# Try to find the correct auth stack
AUTH_STACK=""
for stack in $(echo "$STACKS" | jq -r '.[]'); do
    if [[ "$stack" == *"Auth"* ]]; then
        AUTH_STACK="$stack"
        break
    fi
done

if [ -z "$AUTH_STACK" ]; then
    print_error "No Auth stack found"
    exit 1
fi

print_success "Using Auth stack: $AUTH_STACK"
echo ""

# 2. Get Cognito configuration from CloudFormation
print_status "Extracting Cognito configuration..."
COGNITO_OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$AUTH_STACK" \
    --query "Stacks[0].Outputs[?contains(OutputKey, 'Cognito')].{Key:OutputKey,Value:OutputValue}" \
    --output json 2>/dev/null || echo "[]")

if [ "$COGNITO_OUTPUTS" = "[]" ]; then
    print_error "No Cognito outputs found in $AUTH_STACK"
    exit 1
fi

echo "Cognito Configuration:"
echo "$COGNITO_OUTPUTS" | jq -r '.[] | "  \(.Key): \(.Value)"'
echo ""

# Extract values
USER_POOL_ID=$(echo "$COGNITO_OUTPUTS" | jq -r '.[] | select(.Key=="CognitoUserPoolId") | .Value')
CLIENT_ID=$(echo "$COGNITO_OUTPUTS" | jq -r '.[] | select(.Key=="CognitoUserPoolClientId") | .Value')

if [ -z "$USER_POOL_ID" ] || [ "$USER_POOL_ID" = "null" ]; then
    print_error "User Pool ID not found"
    exit 1
fi

if [ -z "$CLIENT_ID" ] || [ "$CLIENT_ID" = "null" ]; then
    print_error "Client ID not found"
    exit 1
fi

print_success "User Pool ID: $USER_POOL_ID"
print_success "Client ID: $CLIENT_ID"
echo ""

# 3. Check User Pool configuration
print_status "Checking User Pool configuration..."
USER_POOL_INFO=$(aws cognito-idp describe-user-pool --user-pool-id "$USER_POOL_ID" --output json)
POOL_NAME=$(echo "$USER_POOL_INFO" | jq -r '.UserPool.Name')
POOL_STATUS=$(echo "$USER_POOL_INFO" | jq -r '.UserPool.Status')
SIGN_IN_ALIASES=$(echo "$USER_POOL_INFO" | jq -r '.UserPool.AliasAttributes[]?' 2>/dev/null || echo "None")
USERNAME_ATTRIBUTES=$(echo "$USER_POOL_INFO" | jq -r '.UserPool.UsernameAttributes[]?' 2>/dev/null || echo "None")

print_success "Pool Name: $POOL_NAME"
print_success "Pool Status: $POOL_STATUS"
print_success "Sign-in Aliases: $SIGN_IN_ALIASES"
print_success "Username Attributes: $USERNAME_ATTRIBUTES"
echo ""

# 4. Check User Pool Client configuration
print_status "Checking User Pool Client configuration..."
CLIENT_INFO=$(aws cognito-idp describe-user-pool-client \
    --user-pool-id "$USER_POOL_ID" \
    --client-id "$CLIENT_ID" --output json)
CLIENT_NAME=$(echo "$CLIENT_INFO" | jq -r '.UserPoolClient.ClientName')
EXPLICIT_AUTH_FLOWS=$(echo "$CLIENT_INFO" | jq -r '.UserPoolClient.ExplicitAuthFlows[]?' | tr '\n' ',' | sed 's/,$//')

print_success "Client Name: $CLIENT_NAME"
print_success "Auth Flows: $EXPLICIT_AUTH_FLOWS"
echo ""

# 5. Get Invite API URL
print_status "Finding Invite API URL..."
ALL_OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$AUTH_STACK" \
    --query "Stacks[0].Outputs" \
    --output json)

INVITE_API_URL=$(echo "$ALL_OUTPUTS" | jq -r '.[] | select(.OutputKey | contains("InviteApi")) | .OutputValue' | head -1)

if [ -z "$INVITE_API_URL" ] || [ "$INVITE_API_URL" = "null" ]; then
    print_error "Invite API URL not found"
    exit 1
fi

print_success "Invite API URL: $INVITE_API_URL"
echo ""

# 6. Check if test user already exists and clean up
print_status "Checking for existing test user..."
if aws cognito-idp admin-get-user --user-pool-id "$USER_POOL_ID" --username "$TEST_EMAIL" >/dev/null 2>&1; then
    print_warning "Test user already exists, deleting..."
    aws cognito-idp admin-delete-user --user-pool-id "$USER_POOL_ID" --username "$TEST_EMAIL"
    sleep 2
fi

# 7. Test invitation flow
print_status "Testing invitation flow..."
INVITE_PAYLOAD=$(jq -n --arg email "$TEST_EMAIL" --arg name "Test User" '{email:$email, name:$name, suppress:true}')

echo "Sending invitation request..."
INVITE_RESPONSE=$(curl -s -X POST "$INVITE_API_URL" \
    -H 'Content-Type: application/json' \
    -d "$INVITE_PAYLOAD")

echo "Invite Response: $INVITE_RESPONSE"
echo ""

# Check if invitation was successful
if echo "$INVITE_RESPONSE" | jq -e '.message' >/dev/null 2>&1; then
    print_success "Invitation sent successfully"
else
    print_error "Invitation failed"
    echo "Response: $INVITE_RESPONSE"
    exit 1
fi

# 8. Wait for user creation to propagate
print_status "Waiting for user creation to propagate..."
sleep 5

# 9. Verify user was created
print_status "Verifying user creation..."
USER_INFO=$(aws cognito-idp admin-get-user --user-pool-id "$USER_POOL_ID" --username "$TEST_EMAIL" --output json)
USER_STATUS=$(echo "$USER_INFO" | jq -r '.UserStatus')
TEMP_PASSWORD_SET=$(echo "$USER_INFO" | jq -r '.UserAttributes[] | select(.Name=="email_verified") | .Value')

print_success "User Status: $USER_STATUS"
print_success "Email Verified: $TEMP_PASSWORD_SET"
echo ""

# 10. Extract temporary password from invite response or generate one
TEMP_PASSWORD="Spcprt$(date +%s | tail -c 5)A"
print_status "Using temporary password: $TEMP_PASSWORD"

# 11. Test authentication with temporary password
print_status "Testing authentication with temporary password..."

# Create a test authentication request
AUTH_PAYLOAD=$(jq -n \
    --arg username "$TEST_EMAIL" \
    --arg password "$TEMP_PASSWORD" \
    --arg client_id "$CLIENT_ID" \
    '{
        "AuthFlow": "ADMIN_NO_SRP_AUTH",
        "UserPoolId": "'$USER_POOL_ID'",
        "ClientId": $client_id,
        "AuthParameters": {
            "USERNAME": $username,
            "PASSWORD": $password
        }
    }')

echo "Attempting authentication..."
AUTH_RESPONSE=$(aws cognito-idp admin-initiate-auth \
    --cli-input-json "$AUTH_PAYLOAD" \
    --output json 2>&1 || echo '{"error": "auth_failed"}')

echo "Auth Response: $AUTH_RESPONSE"

if echo "$AUTH_RESPONSE" | jq -e '.ChallengeName' >/dev/null 2>&1; then
    CHALLENGE=$(echo "$AUTH_RESPONSE" | jq -r '.ChallengeName')
    print_success "Authentication successful - Challenge: $CHALLENGE"
    
    if [ "$CHALLENGE" = "NEW_PASSWORD_REQUIRED" ]; then
        print_success "✅ INVITE FLOW WORKING - User needs to set new password (expected behavior)"
    fi
elif echo "$AUTH_RESPONSE" | jq -e '.AuthenticationResult' >/dev/null 2>&1; then
    print_success "✅ INVITE FLOW WORKING - User authenticated successfully"
else
    print_error "❌ AUTHENTICATION FAILED"
    echo "This is likely the source of your issue!"
    
    # Analyze the error
    if echo "$AUTH_RESPONSE" | grep -q "NotAuthorizedException"; then
        print_error "Cause: Invalid credentials - possible issues:"
        echo "  1. Temporary password not set correctly"
        echo "  2. User pool client configuration mismatch"
        echo "  3. User status not allowing authentication"
    elif echo "$AUTH_RESPONSE" | grep -q "UserNotFoundException"; then
        print_error "Cause: User not found - possible issues:"
        echo "  1. User created in different pool than expected"
        echo "  2. Username/email mismatch"
    else
        print_error "Cause: Unknown authentication error"
    fi
fi

echo ""

# 12. Cleanup
print_status "Cleaning up test user..."
aws cognito-idp admin-delete-user --user-pool-id "$USER_POOL_ID" --username "$TEST_EMAIL" >/dev/null 2>&1 || true

echo ""
echo "📋 SUMMARY:"
echo "==========="
echo "User Pool ID: $USER_POOL_ID"
echo "Client ID: $CLIENT_ID"
echo "Pool Name: $POOL_NAME"
echo "Invite API: $INVITE_API_URL"
echo "Test Email: $TEST_EMAIL"
echo ""

# 13. Environment variable recommendations
echo "🔧 ENVIRONMENT VARIABLE VERIFICATION:"
echo "===================================="
echo "Ensure your frontend has these exact values:"
echo "NEXT_PUBLIC_COGNITO_REGION=$REGION"
echo "NEXT_PUBLIC_COGNITO_USER_POOL_ID=$USER_POOL_ID"
echo "NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID=$CLIENT_ID"
echo ""

# 14. Additional diagnostics
echo "🕵️ ADDITIONAL DIAGNOSTICS:"
echo "=========================="
echo "Run these commands to check your current environment:"
echo "1. Check GitHub secrets: gh secret list | grep COGNITO"
echo "2. Check local env: grep COGNITO .env*"
echo "3. Check deployed frontend config: inspect browser network tab during auth"
echo ""

print_success "Diagnosis complete!"