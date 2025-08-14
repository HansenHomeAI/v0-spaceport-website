#!/usr/bin/env bash
set -euo pipefail

# Invite a user to Spaceport via the v2 Invite API.
# Requirements: awscli, jq, curl configured with access to the target AWS account/region.
# Usage:
#   ./scripts/admin/invite_user.sh EMAIL [HANDLE] [NAME] [--send-email]
#
# Defaults:
#   - If HANDLE omitted, one will be auto-generated based on the email prefix
#   - Email is suppressed by default (no Cognito email). Pass --send-email to send the default email

if ! command -v aws >/dev/null 2>&1; then echo "aws CLI not found" >&2; exit 1; fi
if ! command -v jq >/dev/null 2>&1; then echo "jq not found" >&2; exit 1; fi
if ! command -v curl >/dev/null 2>&1; then echo "curl not found" >&2; exit 1; fi

if [ $# -lt 1 ]; then
  echo "Usage: $0 EMAIL [HANDLE] [NAME] [--send-email]" >&2
  exit 1
fi

EMAIL="$1"; shift || true
HANDLE="${1:-}"; [ $# -gt 0 ] && shift || true
NAME="${1:-}"; [ $# -gt 0 ] && shift || true
SEND_EMAIL=false
if [ "${1:-}" = "--send-email" ]; then SEND_EMAIL=true; fi

# Fetch Invite API URL from the Auth stack outputs
OUT=$(aws cloudformation describe-stacks --stack-name SpaceportAuthStack --query "Stacks[0].Outputs" --output json)
API=$(echo "$OUT" | jq -r '.[] | select(.OutputKey=="InviteApiUrlV2") | .OutputValue')
POOL=$(echo "$OUT" | jq -r '.[] | select(.OutputKey=="CognitoUserPoolIdV2") | .OutputValue')
GROUP_DEFAULT="beta-testers-v2"

if [ -z "$API" ] || [ "$API" = "null" ]; then echo "InviteApiUrlV2 not found in SpaceportAuthStack outputs" >&2; exit 1; fi

if [ -z "$HANDLE" ]; then
  # derive from email prefix
  HANDLE="$(echo "$EMAIL" | sed 's/@.*//' | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-_')"
  if [ -z "$HANDLE" ]; then HANDLE="user$(date +%s)"; fi
fi

DATA=$(jq -n --arg email "$EMAIL" --arg name "$NAME" --arg handle "$HANDLE" --argjson suppress $([ "$SEND_EMAIL" = true ] && echo false || echo true) '{email:$email, name:$name, handle:$handle, suppress:$suppress}')

echo "Inviting: email=$EMAIL handle=$HANDLE name=${NAME:-} via $API"
curl -sS -X POST "$API" -H 'Content-Type: application/json' -d "$DATA" | tee /tmp/invite_user_resp.json

echo "Verifying user in pool $POOL..."
aws cognito-idp admin-get-user --user-pool-id "$POOL" --username "$EMAIL" | cat


