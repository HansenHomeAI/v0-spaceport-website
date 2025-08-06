#!/usr/bin/env python3
"""
Test script for waitlist confirmation email functionality
This script tests the waitlist Lambda function to ensure confirmation emails are sent correctly
"""

import json
import boto3
import os
from datetime import datetime

def test_waitlist_confirmation_email():
    """
    Test the waitlist confirmation email functionality
    """
    print("🧪 Testing Waitlist Confirmation Email Functionality")
    print("=" * 60)
    
    # Test data
    test_name = "Test User"
    test_email = "test@example.com"  # Replace with a real email for testing
    
    # Create test event
    test_event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "name": test_name,
            "email": test_email
        })
    }
    
    print(f"📧 Test Data:")
    print(f"   Name: {test_name}")
    print(f"   Email: {test_email}")
    print()
    
    # Check SES verification status
    print("🔍 Checking SES Email Verification Status...")
    ses = boto3.client('ses', region_name='us-west-2')
    
    try:
        response = ses.get_identity_verification_attributes(
            Identities=['gabriel@spcprt.com']
        )
        
        status = response['VerificationAttributes']['gabriel@spcprt.com']['VerificationStatus']
        print(f"   Status: {status}")
        
        if status != 'Success':
            print("   ⚠️  Warning: gabriel@spcprt.com is not verified in SES")
            print("   📬 Please check your email and click the verification link from AWS")
            print("   💡 Run: aws ses verify-email-identity --email-address gabriel@spcprt.com --region us-west-2")
            print()
            print("   🚫 Confirmation emails will fail until the email is verified")
            return False
        else:
            print("   ✅ SES email verified successfully!")
            print()
            
    except Exception as e:
        print(f"   ❌ Error checking SES status: {e}")
        return False
    
    # Test the Lambda function directly
    print("🚀 Testing Lambda Function...")
    
    # Import the Lambda function
    import sys
    sys.path.append('infrastructure/spaceport_cdk/lambda/waitlist')
    
    try:
        from lambda_function import lambda_handler
        
        # Set environment variable for testing
        os.environ['WAITLIST_TABLE_NAME'] = 'Spaceport-Waitlist'
        
        # Call the Lambda function
        response = lambda_handler(test_event, None)
        
        print(f"   Status Code: {response['statusCode']}")
        print(f"   Response: {response['body']}")
        
        if response['statusCode'] == 200:
            print("   ✅ Lambda function executed successfully!")
            
            # Parse response body
            body = json.loads(response['body'])
            if 'message' in body and 'Successfully added to waitlist' in body['message']:
                print("   ✅ Waitlist signup successful!")
                print("   📧 Confirmation email should have been sent")
                return True
            else:
                print("   ❌ Unexpected response message")
                return False
        else:
            print("   ❌ Lambda function failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing Lambda function: {e}")
        return False

def test_ses_send_email_directly():
    """
    Test sending email directly via SES to verify permissions
    """
    print("\n📧 Testing SES Send Email Directly...")
    print("=" * 40)
    
    ses = boto3.client('ses', region_name='us-west-2')
    
    test_email = "test@example.com"  # Replace with a real email for testing
    
    try:
        response = ses.send_email(
            Source='gabriel@spcprt.com',
            Destination={
                'ToAddresses': [test_email]
            },
            Message={
                'Subject': {
                    'Data': 'Test Email from Spaceport AI'
                },
                'Body': {
                    'Text': {
                        'Data': 'This is a test email to verify SES permissions are working correctly.'
                    },
                    'Html': {
                        'Data': '<h1>Test Email</h1><p>This is a test email to verify SES permissions are working correctly.</p>'
                    }
                }
            }
        )
        
        print(f"   ✅ Test email sent successfully!")
        print(f"   📧 Message ID: {response['MessageId']}")
        print(f"   📬 Check {test_email} for the test email")
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to send test email: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Spaceport AI - Waitlist Confirmation Email Test")
    print("=" * 60)
    print()
    
    # Test SES verification and direct email sending
    ses_test = test_ses_send_email_directly()
    
    if ses_test:
        print("\n✅ SES is working correctly!")
        print("🎯 The confirmation email feature should work once deployed.")
    else:
        print("\n❌ SES is not working correctly.")
        print("🔧 Please check SES configuration and email verification.")
    
    print("\n📋 Next Steps:")
    print("   1. Verify gabriel@spcprt.com in SES console")
    print("   2. Deploy the updated Lambda function")
    print("   3. Test the waitlist form on your website")
    print("   4. Check that confirmation emails are sent to new signups") 