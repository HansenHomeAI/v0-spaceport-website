#!/usr/bin/env bash
set -euo pipefail

# Manage beta invitation access for Spaceport employees.
# This script allows you to grant or revoke permission for users to invite beta testers.
# Requirements: awscli, jq configured with access to the target AWS account/region.
# Usage:
#   ./scripts/admin/manage_beta_invite_access.sh EMAIL grant
#   ./scripts/admin/manage_beta_invite_access.sh EMAIL revoke
#   ./scripts/admin/manage_beta_invite_access.sh EMAIL check

if ! command -v aws >/dev/null 2>&1; then echo "aws CLI not found" >&2; exit 1; fi
if ! command -v jq >/dev/null 2>&1; then echo "jq not found" >&2; exit 1; fi

if [ $# -lt 2 ]; then
  echo "Usage: $0 EMAIL ACTION" >&2
  echo "Actions: grant, revoke, check" >&2
  exit 1
fi

EMAIL="$1"
ACTION="$2"

# Fetch Cognito User Pool ID from the Auth stack outputs
OUT=$(aws cloudformation describe-stacks --stack-name SpaceportAuthStack --query "Stacks[0].Outputs" --output json)
POOL=$(echo "$OUT" | jq -r '.[] | select(.OutputKey=="CognitoUserPoolIdV2") | .OutputValue')

if [ -z "$POOL" ] || [ "$POOL" = "null" ]; then 
  echo "CognitoUserPoolIdV2 not found in SpaceportAuthStack outputs" >&2
  exit 1
fi

echo "Managing beta invite access for: $EMAIL in pool: $POOL"

case "$ACTION" in
  "grant")
    echo "Granting beta invitation access to $EMAIL..."
    aws cognito-idp admin-update-user-attributes \
      --user-pool-id "$POOL" \
      --username "$EMAIL" \
      --user-attributes Name=custom:can_invite_beta,Value=true
    
    echo "✅ Beta invitation access granted to $EMAIL"
    echo "This user can now invite beta testers through the web dashboard."
    ;;
    
  "revoke")
    echo "Revoking beta invitation access from $EMAIL..."
    aws cognito-idp admin-update-user-attributes \
      --user-pool-id "$POOL" \
      --username "$EMAIL" \
      --user-attributes Name=custom:can_invite_beta,Value=false
    
    echo "✅ Beta invitation access revoked from $EMAIL"
    echo "This user can no longer invite beta testers through the web dashboard."
    ;;
    
  "check")
    echo "Checking beta invitation access for $EMAIL..."
    USER_ATTRS=$(aws cognito-idp admin-get-user \
      --user-pool-id "$POOL" \
      --username "$EMAIL" \
      --query "UserAttributes" \
      --output json)
    
    CAN_INVITE=$(echo "$USER_ATTRS" | jq -r '.[] | select(.Name=="custom:can_invite_beta") | .Value // "false"')
    
    if [ "$CAN_INVITE" = "true" ]; then
      echo "✅ $EMAIL HAS beta invitation access"
    else
      echo "❌ $EMAIL does NOT have beta invitation access"
    fi
    ;;
    
  *)
    echo "Invalid action: $ACTION" >&2
    echo "Valid actions: grant, revoke, check" >&2
    exit 1
    ;;
esac

echo ""
echo "Current user details:"
aws cognito-idp admin-get-user --user-pool-id "$POOL" --username "$EMAIL" | jq '.UserAttributes[] | select(.Name | startswith("custom:")) | {(.Name): .Value}'