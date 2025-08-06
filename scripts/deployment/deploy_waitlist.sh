#!/bin/bash

# Deploy Waitlist Infrastructure
# This script deploys the DynamoDB table and Lambda function for the waitlist functionality

set -e

echo "🚀 Deploying Spaceport Waitlist Infrastructure..."

# Check SES email verification status
echo "📧 Checking SES email verification status..."
EMAIL_STATUS=$(aws ses get-identity-verification-attributes --identities gabriel@spcprt.com --region us-west-2 --query "VerificationAttributes.gabriel@spcprt.com.VerificationStatus" --output text 2>/dev/null || echo "NotVerified")

if [ "$EMAIL_STATUS" != "Success" ]; then
    echo "⚠️  Warning: gabriel@spcprt.com is not verified in SES (Status: $EMAIL_STATUS)"
    echo "📬 Please check your email and click the verification link from AWS."
    echo "💡 Run this command to check status: aws ses get-identity-verification-attributes --identities gabriel@spcprt.com --region us-west-2"
    echo ""
    echo "🔄 Continuing with deployment... (email notifications will fail until verified)"
    echo ""
else
    echo "✅ SES email verified successfully!"
    echo ""
fi

# Navigate to the CDK directory
cd infrastructure/spaceport_cdk

# Install Python dependencies if needed
if [ ! -d ".venv" ]; then
    echo "📦 Installing Python dependencies..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    pip install aws-cdk-lib
else
    echo "📦 Activating Python virtual environment..."
    source .venv/bin/activate
fi

# Deploy the Spaceport stack (which now includes the waitlist functionality)
echo "🏗️  Deploying Spaceport Stack with waitlist functionality..."
cdk deploy SpaceportStack --require-approval never

echo "✅ Waitlist infrastructure deployed successfully!"
echo ""
echo "📋 What was deployed:"
echo "   • DynamoDB table: Spaceport-Waitlist"
echo "   • Lambda function: Spaceport-WaitlistFunction"
echo "   • API Gateway endpoint: /waitlist"
echo ""
echo "🔗 API Endpoint: https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/waitlist"
echo ""
echo "📧 Admin notifications will be sent to: gabriel@spcprt.com"
echo ""
echo "🎯 Next steps:"
echo "   1. Test the waitlist form on your website"
echo "   2. Check DynamoDB console to see entries"
echo "   3. Verify email notifications are working" 