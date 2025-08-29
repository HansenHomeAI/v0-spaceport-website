#!/usr/bin/env bash
set -euo pipefail

# Grant beta access admin permissions to an employee
# Requirements: awscli, jq configured with access to the target AWS account/region.
# Usage:
#   ./scripts/admin/grant_beta_access.sh EMAIL [--revoke]
#
# This script manages beta access admin permissions for employees, allowing them
# to send invitations through the web dashboard interface.

if ! command -v aws >/dev/null 2>&1; then echo "aws CLI not found" >&2; exit 1; fi
if ! command -v jq >/dev/null 2>&1; then echo "jq not found" >&2; exit 1; fi

if [ $# -lt 1 ]; then
  echo "Usage: $0 EMAIL [--revoke]" >&2
  echo "  EMAIL: Employee email address to grant/revoke beta access admin permissions" >&2
  echo "  --revoke: Remove beta access admin permissions (default: grant)" >&2
  exit 1
fi

EMAIL="$1"; shift || true
REVOKE=false
if [ "${1:-}" = "--revoke" ]; then REVOKE=true; fi

# Fetch Auth stack outputs
echo "Fetching Auth stack configuration..."
OUT=$(aws cloudformation describe-stacks --stack-name SpaceportAuthStagingStack --query "Stacks[0].Outputs" --output json)
USER_POOL_ID=$(echo "$OUT" | jq -r '.[] | select(.OutputKey=="CognitoUserPoolIdV2") | .OutputValue')
PERMISSIONS_TABLE="Spaceport-BetaAccessPermissions-staging"

# If we can't find the table name from stack outputs, try common names
if [ -z "$PERMISSIONS_TABLE" ] || [ "$PERMISSIONS_TABLE" = "None" ]; then
  # Try to find the table name dynamically
  PERMISSIONS_TABLE=$(aws dynamodb list-tables --query "TableNames[?contains(@, 'BetaAccessPermissions')]" --output text | head -1)
  if [ -z "$PERMISSIONS_TABLE" ]; then
    PERMISSIONS_TABLE="Spaceport-BetaAccessPermissions"
  fi
fi

if [ -z "$USER_POOL_ID" ] || [ "$USER_POOL_ID" = "null" ]; then 
  echo "CognitoUserPoolIdV2 not found in SpaceportAuthStack outputs" >&2
  exit 1
fi

echo "Using Cognito User Pool: $USER_POOL_ID"
echo "Using Permissions Table: $PERMISSIONS_TABLE"

# Get user ID from Cognito
echo "Looking up user: $EMAIL"
USER_INFO=$(aws cognito-idp admin-get-user --user-pool-id "$USER_POOL_ID" --username "$EMAIL" --output json 2>/dev/null || echo "{}")

if [ "$USER_INFO" = "{}" ]; then
  echo "Error: User $EMAIL not found in Cognito pool $USER_POOL_ID" >&2
  echo "Make sure the user has been invited and exists in the system first." >&2
  exit 1
fi

# Extract user ID (sub attribute)
USER_ID=$(echo "$USER_INFO" | jq -r '.UserAttributes[] | select(.Name=="sub") | .Value')
if [ -z "$USER_ID" ] || [ "$USER_ID" = "null" ]; then
  echo "Error: Could not extract user ID for $EMAIL" >&2
  exit 1
fi

echo "Found user ID: $USER_ID"

if [ "$REVOKE" = true ]; then
  # Revoke permissions by deleting the record
  echo "Revoking beta access admin permissions for $EMAIL..."
  aws dynamodb delete-item \
    --table-name "$PERMISSIONS_TABLE" \
    --key "{\"user_id\": {\"S\": \"$USER_ID\"}}" \
    --output text >/dev/null
  
  echo "✅ Beta access admin permissions revoked for $EMAIL"
  echo "   The user will no longer see the invitation interface on their dashboard."
else
  # Grant permissions by creating/updating the record
  echo "Granting beta access admin permissions for $EMAIL..."
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  
  aws dynamodb put-item \
    --table-name "$PERMISSIONS_TABLE" \
    --item "{
      \"user_id\": {\"S\": \"$USER_ID\"},
      \"email\": {\"S\": \"$EMAIL\"},
      \"has_beta_access_permission\": {\"BOOL\": true},
      \"granted_at\": {\"S\": \"$TIMESTAMP\"},
      \"granted_by\": {\"S\": \"admin-script\"}
    }" \
    --output text >/dev/null
  
  echo "✅ Beta access admin permissions granted to $EMAIL"
  echo "   The user will now see the beta invitation interface on their dashboard."
  echo "   They can invite new users by entering email addresses and clicking 'Grant Access'."
fi

# Verify the change
echo ""
echo "Verifying permissions..."
CURRENT_PERMISSION=$(aws dynamodb get-item \
  --table-name "$PERMISSIONS_TABLE" \
  --key "{\"user_id\": {\"S\": \"$USER_ID\"}}" \
  --query "Item.has_beta_access_permission.BOOL" \
  --output text 2>/dev/null || echo "false")

if [ "$CURRENT_PERMISSION" = "true" ]; then
  echo "✓ Current status: $EMAIL HAS beta access admin permissions"
elif [ "$CURRENT_PERMISSION" = "false" ] || [ "$CURRENT_PERMISSION" = "None" ]; then
  echo "✓ Current status: $EMAIL does NOT have beta access admin permissions"
else
  echo "⚠ Could not verify current status"
fi

echo ""
echo "Done! Changes will be reflected immediately on the user's dashboard."