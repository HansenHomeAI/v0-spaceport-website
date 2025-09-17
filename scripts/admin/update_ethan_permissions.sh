#!/bin/bash
set -euo pipefail

# Update Ethan Pixton's IAM user permissions for full read access
# This script attaches the comprehensive read-only policy to the existing ethan-spcprt user

echo "🔧 Updating Ethan Pixton's IAM User Permissions"
echo "=============================================="

# Configuration
USER_NAME="ethan-spcprt"
POLICY_NAME="SpaceportReadOnlyAccess"
POLICY_FILE="scripts/admin/ethan_readonly_policy.json"
AWS_REGION="us-west-2"
AWS_ACCOUNT_ID="356638455876"

# Verify AWS CLI is configured
if ! command -v aws >/dev/null 2>&1; then
    echo "❌ AWS CLI not found. Please install and configure AWS CLI first."
    exit 1
fi

# Verify we're in the right account
CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
if [ "$CURRENT_ACCOUNT" != "$AWS_ACCOUNT_ID" ]; then
    echo "❌ Wrong AWS account! Current: $CURRENT_ACCOUNT, Expected: $AWS_ACCOUNT_ID"
    echo "Please configure AWS CLI for the production account (356638455876)"
    exit 1
fi

echo "✅ Confirmed production account: $CURRENT_ACCOUNT"

# Check if user exists
echo "🔍 Checking if user $USER_NAME exists..."
if ! aws iam get-user --user-name "$USER_NAME" >/dev/null 2>&1; then
    echo "❌ User $USER_NAME not found in account $AWS_ACCOUNT_ID"
    echo "Please create the user first or check the username."
    exit 1
fi

echo "✅ User $USER_NAME found"

# Create or update the policy
echo "📝 Creating/updating IAM policy: $POLICY_NAME"

# Check if policy already exists
if aws iam get-policy --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}" >/dev/null 2>&1; then
    echo "🔄 Policy exists, updating..."
    # Create new version
    aws iam create-policy-version \
        --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}" \
        --policy-document file://"$POLICY_FILE" \
        --set-as-default
    echo "✅ Policy updated successfully"
else
    echo "🆕 Creating new policy..."
    aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file://"$POLICY_FILE" \
        --description "Comprehensive read-only access for Ethan Pixton to all Spaceport resources"
    echo "✅ Policy created successfully"
fi

# Attach policy to user
echo "🔗 Attaching policy to user $USER_NAME..."

# Check if policy is already attached
if aws iam list-attached-user-policies --user-name "$USER_NAME" --query "AttachedPolicies[?PolicyName=='$POLICY_NAME']" --output text | grep -q "$POLICY_NAME"; then
    echo "✅ Policy already attached to user"
else
    aws iam attach-user-policy \
        --user-name "$USER_NAME" \
        --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"
    echo "✅ Policy attached to user successfully"
fi

# List current policies for verification
echo ""
echo "📋 Current policies attached to $USER_NAME:"
aws iam list-attached-user-policies --user-name "$USER_NAME" --query "AttachedPolicies[].PolicyName" --output table

echo ""
echo "🎉 SUCCESS! Ethan Pixton now has comprehensive read access to:"
echo "   • All DynamoDB tables (FileMetadata, DroneFlightPaths, Waitlist, Projects, Users, etc.)"
echo "   • All S3 buckets (uploads, ML processing)"
echo "   • CloudWatch logs for all services"
echo "   • Cognito user pools and users"
echo "   • Lambda functions and configurations"
echo "   • Step Functions executions"
echo "   • SageMaker jobs and endpoints"
echo "   • ECR repositories"
echo ""
echo "🧪 Test access with:"
echo "   aws dynamodb scan --table-name Spaceport-Waitlist-prod --max-items 5"
echo "   aws s3 ls s3://spaceport-uploads-prod/"
echo "   aws logs describe-log-groups --log-group-name-prefix '/aws/lambda/Spaceport-'"
