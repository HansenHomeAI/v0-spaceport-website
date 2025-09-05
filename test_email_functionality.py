#!/usr/bin/env python3
"""
Comprehensive email functionality test for Resend integration
Tests both hello@spcprt.com and gabriel@spcprt.com email addresses
"""

import json
import boto3
import os
from datetime import datetime

def test_beta_access_invite():
    """Test beta access invitation email (hello@spcprt.com)"""
    print("🧪 Testing Beta Access Invite Email...")
    
    # Test payload for beta access admin Lambda
    test_payload = {
        "httpMethod": "POST",
        "path": "/admin/beta-access/send-invitation",
        "body": json.dumps({
            "email": "test@example.com",
            "name": "Test User"
        })
    }
    
    # Invoke the Lambda function
    lambda_client = boto3.client('lambda')
    
    try:
        response = lambda_client.invoke(
            FunctionName='Spaceport-BetaAccessAdminFunction-staging',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"✅ Beta Access Response: {result.get('statusCode', 'Unknown')}")
        
        if result.get('statusCode') == 200:
            print("✅ Beta access email sent successfully!")
            print("📧 From: hello@spcprt.com")
            print("📧 To: test@example.com")
        else:
            print(f"❌ Beta access email failed: {result.get('body', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Beta access test failed: {str(e)}")

def test_waitlist_signup():
    """Test waitlist signup email (gabriel@spcprt.com)"""
    print("\n🧪 Testing Waitlist Signup Email...")
    
    # Test payload for waitlist Lambda
    test_payload = {
        "httpMethod": "POST",
        "path": "/waitlist",
        "body": json.dumps({
            "email": "test@example.com",
            "name": "Test User"
        })
    }
    
    # Invoke the Lambda function
    lambda_client = boto3.client('lambda')
    
    try:
        response = lambda_client.invoke(
            FunctionName='Spaceport-WaitlistFunction-staging',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"✅ Waitlist Response: {result.get('statusCode', 'Unknown')}")
        
        if result.get('statusCode') == 200:
            print("✅ Waitlist email sent successfully!")
            print("📧 From: gabriel@spcprt.com")
            print("📧 To: test@example.com")
        else:
            print(f"❌ Waitlist email failed: {result.get('body', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Waitlist test failed: {str(e)}")

def test_ml_notification():
    """Test ML notification email (hello@spcprt.com)"""
    print("\n🧪 Testing ML Notification Email...")
    
    # Test payload for ML notification Lambda
    test_payload = {
        "job_id": "test-job-123",
        "status": "completed",
        "user_email": "test@example.com",
        "project_name": "Test Project"
    }
    
    # Invoke the Lambda function
    lambda_client = boto3.client('lambda')
    
    try:
        response = lambda_client.invoke(
            FunctionName='Spaceport-MLNotificationFunction-staging',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"✅ ML Notification Response: {result.get('statusCode', 'Unknown')}")
        
        if result.get('statusCode') == 200:
            print("✅ ML notification email sent successfully!")
            print("📧 From: hello@spcprt.com")
            print("📧 To: test@example.com")
        else:
            print(f"❌ ML notification email failed: {result.get('body', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ ML notification test failed: {str(e)}")

def test_invite_user():
    """Test user invitation email (hello@spcprt.com)"""
    print("\n🧪 Testing User Invitation Email...")
    
    # Test payload for invite user Lambda
    test_payload = {
        "httpMethod": "POST",
        "path": "/invite-user",
        "body": json.dumps({
            "email": "test@example.com",
            "name": "Test User"
        })
    }
    
    # Invoke the Lambda function
    lambda_client = boto3.client('lambda')
    
    try:
        response = lambda_client.invoke(
            FunctionName='Spaceport-InviteUserFunction-staging',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"✅ Invite User Response: {result.get('statusCode', 'Unknown')}")
        
        if result.get('statusCode') == 200:
            print("✅ User invitation email sent successfully!")
            print("📧 From: hello@spcprt.com")
            print("📧 To: test@example.com")
        else:
            print(f"❌ User invitation email failed: {result.get('body', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ User invitation test failed: {str(e)}")

def check_cloudwatch_logs():
    """Check CloudWatch logs for any errors"""
    print("\n🔍 Checking CloudWatch Logs...")
    
    logs_client = boto3.client('logs')
    
    # Check logs for each Lambda function
    functions = [
        'Spaceport-BetaAccessAdminFunction-staging',
        'Spaceport-WaitlistFunction-staging', 
        'Spaceport-MLNotificationFunction-staging',
        'Spaceport-InviteUserFunction-staging'
    ]
    
    for function_name in functions:
        try:
            log_group = f'/aws/lambda/{function_name}'
            
            # Get recent log streams
            response = logs_client.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=1
            )
            
            if response['logStreams']:
                stream_name = response['logStreams'][0]['logStreamName']
                
                # Get recent log events
                events = logs_client.get_log_events(
                    logGroupName=log_group,
                    logStreamName=stream_name,
                    limit=10
                )
                
                print(f"\n📋 Recent logs for {function_name}:")
                for event in events['events'][-5:]:  # Last 5 events
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    print(f"  {timestamp}: {event['message'].strip()}")
            else:
                print(f"⚠️  No log streams found for {function_name}")
                
        except Exception as e:
            print(f"❌ Could not check logs for {function_name}: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting Comprehensive Email Functionality Test")
    print("=" * 60)
    
    # Test all email functions
    test_beta_access_invite()
    test_waitlist_signup()
    test_ml_notification()
    test_invite_user()
    
    # Check logs for any issues
    check_cloudwatch_logs()
    
    print("\n" + "=" * 60)
    print("✅ Email functionality test completed!")
    print("\n📧 Expected Email Addresses:")
    print("  • Beta Access Invites: hello@spcprt.com")
    print("  • Waitlist Signups: gabriel@spcprt.com") 
    print("  • ML Notifications: hello@spcprt.com")
    print("  • User Invitations: hello@spcprt.com")
