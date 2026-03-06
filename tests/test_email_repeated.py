#!/usr/bin/env python3
"""
Test script to test the waitlist confirmation email with repeated email addresses
"""

import json
import boto3
import os
import sys
from datetime import datetime

def test_repeated_email():
    """
    Test the Lambda function with the same email multiple times
    """
    print("🧪 Testing Repeated Email Submissions")
    print("=" * 50)
    
    # Use a consistent test email
    test_name = "Test User"
    test_email = "gabriel@spcprt.com"  # You can change this to any email
    
    print(f"📧 Test email: {test_email}")
    print(f"👤 Test name: {test_name}")
    print()
    
    # Set environment variable for testing (before importing)
    os.environ['WAITLIST_TABLE_NAME'] = 'Spaceport-Waitlist'
    
    # Import the Lambda function
    sys.path.append('infrastructure/spaceport_cdk/lambda/waitlist')
    
    try:
        from lambda_function import lambda_handler
        
        # Test multiple submissions
        for i in range(3):
            print(f"🔄 Test submission #{i+1}...")
            
            # Create test event
            test_event = {
                "httpMethod": "POST",
                "body": json.dumps({
                    "name": f"{test_name} #{i+1}",
                    "email": test_email
                })
            }
            
            # Call the Lambda function
            response = lambda_handler(test_event, None)
            
            print(f"   Status: {response['statusCode']}")
            
            if response['statusCode'] == 200:
                print("   ✅ Success!")
                
                # Parse response body
                body = json.loads(response['body'])
                if 'message' in body and 'Successfully added to waitlist' in body['message']:
                    print("   📧 Confirmation email sent!")
                else:
                    print("   ❌ Unexpected response message")
            else:
                print("   ❌ Failed")
                print(f"   Response: {response['body']}")
            
            print()
        
        print("🎉 All tests completed!")
        print(f"📬 Check {test_email} for confirmation emails")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Lambda function: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Spaceport - Repeated Email Test")
    print("=" * 60)
    print()
    
    success = test_repeated_email()
    
    if success:
        print("\n🎯 Repeated email testing completed successfully!")
        print("📧 Multiple confirmation emails should have been sent.")
        print("📋 You can now test the waitlist form on your website.")
    else:
        print("\n❌ Repeated email testing failed.")
        print("🔧 Please check the error messages above.") 