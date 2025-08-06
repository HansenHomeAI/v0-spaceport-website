#!/bin/bash

# SES Email Verification Script
# This script helps verify and check the status of SES email addresses

EMAIL_ADDRESS="gabriel@spcprt.com"
REGION="us-west-2"

echo "🔍 SES Email Verification for Spaceport AI"
echo "=========================================="
echo ""

echo "📧 Email Address: $EMAIL_ADDRESS"
echo "🌍 AWS Region: $REGION"
echo ""

# Check current verification status
echo "📋 Checking current verification status..."
STATUS=$(aws ses get-identity-verification-attributes --identities $EMAIL_ADDRESS --region $REGION --query "VerificationAttributes.$EMAIL_ADDRESS.VerificationStatus" --output text 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "✅ Status: $STATUS"
    
    if [ "$STATUS" = "Success" ]; then
        echo "🎉 Email is verified and ready to use!"
        echo ""
        echo "🚀 You can now deploy the waitlist infrastructure:"
        echo "   ./scripts/deployment/deploy_waitlist.sh"
    elif [ "$STATUS" = "Pending" ]; then
        echo "⏳ Email verification is pending."
        echo "📬 Check your email inbox for a verification link from AWS."
        echo "🔗 Click the link to complete verification."
        echo ""
        echo "💡 To resend verification email:"
        echo "   aws ses verify-email-identity --email-address $EMAIL_ADDRESS --region $REGION"
    else
        echo "❌ Email is not verified."
        echo ""
        echo "📧 Sending verification request..."
        aws ses verify-email-identity --email-address $EMAIL_ADDRESS --region $REGION
        echo "✅ Verification email sent! Check your inbox."
    fi
else
    echo "❌ Error checking verification status."
    echo "📧 Sending verification request..."
    aws ses verify-email-identity --email-address $EMAIL_ADDRESS --region $REGION
    echo "✅ Verification email sent! Check your inbox."
fi

echo ""
echo "📊 To check verification status manually:"
echo "   aws ses get-identity-verification-attributes --identities $EMAIL_ADDRESS --region $REGION"
echo ""
echo "📧 To resend verification email:"
echo "   aws ses verify-email-identity --email-address $EMAIL_ADDRESS --region $REGION" 