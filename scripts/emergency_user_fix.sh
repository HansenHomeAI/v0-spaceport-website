#!/bin/bash
# Emergency script to fix a user who can't sign in
# Usage: ./emergency_user_fix.sh user@example.com

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <user_email>"
    exit 1
fi

EMAIL="$1"
REGION="${AWS_REGION:-us-west-2}"
USER_POOL_ID="${COGNITO_USER_POOL_ID}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔧 Emergency User Fix for: $EMAIL${NC}"
echo "================================================"

# Check if user pool ID is set
if [ -z "$USER_POOL_ID" ]; then
    echo -e "${RED}❌ Error: COGNITO_USER_POOL_ID environment variable not set${NC}"
    echo "Please set it first: export COGNITO_USER_POOL_ID=your-pool-id"
    exit 1
fi

# Step 1: Check user status
echo -e "\n${YELLOW}Step 1: Checking user status...${NC}"
USER_INFO=$(aws cognito-idp list-users \
    --user-pool-id "$USER_POOL_ID" \
    --filter "email = \"$EMAIL\"" \
    --region "$REGION" 2>/dev/null || echo "ERROR")

if [ "$USER_INFO" = "ERROR" ]; then
    echo -e "${RED}❌ Failed to query user pool. Check your AWS credentials.${NC}"
    exit 1
fi

USER_COUNT=$(echo "$USER_INFO" | jq '.Users | length')

if [ "$USER_COUNT" -eq 0 ]; then
    echo -e "${RED}❌ User not found: $EMAIL${NC}"
    echo -e "${YELLOW}Would you like to create a new invite? (y/n)${NC}"
    read -r CREATE_INVITE
    
    if [ "$CREATE_INVITE" = "y" ]; then
        echo "Creating new user invite..."
        # Call invite Lambda or create user
        aws lambda invoke \
            --function-name Spaceport-InviteUserFunction \
            --payload "{\"body\": \"{\\\"email\\\": \\\"$EMAIL\\\"}\"}" \
            --region "$REGION" \
            /tmp/invite_response.json
        
        echo -e "${GREEN}✅ Invite sent to $EMAIL${NC}"
        cat /tmp/invite_response.json | jq .
    fi
    exit 0
fi

# Get user details
USERNAME=$(echo "$USER_INFO" | jq -r '.Users[0].Username')
USER_STATUS=$(echo "$USER_INFO" | jq -r '.Users[0].UserStatus')

echo -e "${GREEN}✓ User found:${NC}"
echo "  Username: $USERNAME"
echo "  Status: $USER_STATUS"
echo "  Email: $EMAIL"

# Step 2: Generate new temporary password
echo -e "\n${YELLOW}Step 2: Generating new temporary password...${NC}"

# Generate a memorable but secure password
RANDOM_NUM=$(( RANDOM % 9000 + 1000 ))
TEMP_PASSWORD="Spcprt${RANDOM_NUM}A"

echo -e "New temporary password: ${GREEN}$TEMP_PASSWORD${NC}"

# Step 3: Reset password
echo -e "\n${YELLOW}Step 3: Resetting user password...${NC}"

aws cognito-idp admin-set-user-password \
    --user-pool-id "$USER_POOL_ID" \
    --username "$USERNAME" \
    --password "$TEMP_PASSWORD" \
    --permanent false \
    --region "$REGION"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Password reset successfully!${NC}"
else
    echo -e "${RED}❌ Failed to reset password${NC}"
    exit 1
fi

# Step 4: Send email with new password (optional)
echo -e "\n${YELLOW}Step 4: Sending email with instructions...${NC}"

# Create email template
cat > /tmp/email_body.txt << EOF
Hi,

We've reset your Spaceport AI password. Here are your new sign-in details:

Email: $EMAIL
Temporary Password: $TEMP_PASSWORD

To sign in:
1. Go to https://spcprt.com/create
2. Enter your email: $EMAIL
3. Enter the temporary password: $TEMP_PASSWORD
4. You'll be prompted to create a new password

This temporary password expires in 7 days.

If you continue to have issues, please reply to this email.

Best regards,
Spaceport AI Support
EOF

echo -e "${GREEN}✅ Password reset complete!${NC}"
echo ""
echo "================================================"
echo -e "${GREEN}INSTRUCTIONS FOR USER:${NC}"
echo ""
echo "1. Go to https://spcprt.com/create"
echo "2. Sign in with:"
echo "   Email: $EMAIL"
echo "   Password: $TEMP_PASSWORD"
echo "3. You'll be prompted to set a new password"
echo ""
echo "================================================"
echo ""
echo -e "${YELLOW}📋 Copy this message to send to the user:${NC}"
echo ""
cat /tmp/email_body.txt
echo ""
echo "================================================"

# Step 5: Verify the fix worked
echo -e "\n${YELLOW}Step 5: Verifying user can now sign in...${NC}"

# Re-check user status
USER_STATUS_AFTER=$(aws cognito-idp admin-get-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$USERNAME" \
    --region "$REGION" \
    --query 'UserStatus' \
    --output text)

echo "User status after reset: $USER_STATUS_AFTER"

if [ "$USER_STATUS_AFTER" = "FORCE_CHANGE_PASSWORD" ] || [ "$USER_STATUS_AFTER" = "CONFIRMED" ]; then
    echo -e "${GREEN}✅ User should now be able to sign in!${NC}"
else
    echo -e "${YELLOW}⚠️ User status is: $USER_STATUS_AFTER - they may need additional help${NC}"
fi

# Cleanup
rm -f /tmp/email_body.txt /tmp/invite_response.json

echo ""
echo -e "${GREEN}✅ Emergency fix completed successfully!${NC}"