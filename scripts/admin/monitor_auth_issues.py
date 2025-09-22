#!/usr/bin/env python3
"""
Monitor authentication issues by checking CloudWatch logs and user pool metrics.
This helps identify patterns in authentication failures.
"""

import boto3
import json
from datetime import datetime, timedelta
import time

def monitor_auth_issues():
    """Monitor authentication issues"""
    
    # Initialize AWS clients
    cognito = boto3.client('cognito-idp', region_name='us-west-2')
    cloudwatch = boto3.client('cloudwatch', region_name='us-west-2')
    logs = boto3.client('logs', region_name='us-west-2')
    
    user_pool_id = input("Enter Cognito User Pool ID: ").strip()
    if not user_pool_id:
        print("❌ User Pool ID is required")
        return
    
    print(f"\n📊 Monitoring authentication issues for User Pool: {user_pool_id}")
    print("=" * 70)
    
    # Check recent authentication failures
    print("\n1️⃣ Checking recent authentication metrics...")
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        # Get authentication failure metrics
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/Cognito',
            MetricName='AuthenticationFailure',
            Dimensions=[
                {
                    'Name': 'UserPoolId',
                    'Value': user_pool_id
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,  # 1 hour periods
            Statistics=['Sum']
        )
        
        if response['Datapoints']:
            total_failures = sum(point['Sum'] for point in response['Datapoints'])
            print(f"   🔴 Authentication failures in last 24h: {total_failures}")
            
            # Show hourly breakdown
            for point in sorted(response['Datapoints'], key=lambda x: x['Timestamp']):
                hour = point['Timestamp'].strftime('%H:%M')
                failures = int(point['Sum'])
                if failures > 0:
                    print(f"      {hour}: {failures} failures")
        else:
            print("   ✅ No authentication failures in last 24h")
            
    except Exception as e:
        print(f"❌ Error checking metrics: {e}")
    
    # Check CloudWatch logs for Lambda errors
    print("\n2️⃣ Checking Lambda function logs...")
    try:
        # Check invite user Lambda logs
        log_group = f"/aws/lambda/Spaceport-InviteUserFunction"
        
        try:
            # Get recent log streams
            streams_response = logs.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=5
            )
            
            if streams_response['logStreams']:
                print(f"   📋 Recent log streams for {log_group}:")
                for stream in streams_response['logStreams'][:3]:
                    print(f"      {stream['logStreamName']} (Last: {stream['lastEventTime']})")
                    
                    # Get recent events from this stream
                    events_response = logs.get_log_events(
                        logGroupName=log_group,
                        logStreamName=stream['logStreamName'],
                        startTime=int((datetime.utcnow() - timedelta(hours=6)).timestamp() * 1000),
                        limit=50
                    )
                    
                    error_events = [event for event in events_response['events'] 
                                  if 'ERROR' in event['message'] or 'Exception' in event['message']]
                    
                    if error_events:
                        print(f"         🔴 {len(error_events)} error events found")
                        for event in error_events[-3:]:  # Show last 3 errors
                            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                            print(f"            {timestamp}: {event['message'][:100]}...")
                    else:
                        print(f"         ✅ No recent errors")
            else:
                print(f"   ⚠️  No log streams found for {log_group}")
                
        except logs.exceptions.ResourceNotFoundException:
            print(f"   ⚠️  Log group {log_group} not found")
        except Exception as e:
            print(f"   ❌ Error checking logs: {e}")
            
    except Exception as e:
        print(f"❌ Error checking Lambda logs: {e}")
    
    # Check user pool status
    print("\n3️⃣ Checking user pool status...")
    try:
        pool_info = cognito.describe_user_pool(UserPoolId=user_pool_id)
        pool = pool_info['UserPool']
        
        print(f"   Pool Name: {pool['Name']}")
        print(f"   Status: {pool['Status']}")
        print(f"   Creation Date: {pool['CreationDate']}")
        
        # Check if there are any issues with the pool configuration
        issues = []
        
        if not pool.get('AdminCreateUserConfig', {}).get('AllowAdminCreateUserOnly', True):
            issues.append("Self sign-up is enabled (should be disabled for invite-only)")
        
        if 'email' not in pool.get('AutoVerifiedAttributes', []):
            issues.append("Email auto-verification is not enabled")
        
        if issues:
            print("   ⚠️  Potential configuration issues:")
            for issue in issues:
                print(f"      - {issue}")
        else:
            print("   ✅ Pool configuration looks good")
            
    except Exception as e:
        print(f"❌ Error checking user pool: {e}")
    
    # Check recent user activity
    print("\n4️⃣ Checking recent user activity...")
    try:
        # List recent users
        users_response = cognito.list_users(
            UserPoolId=user_pool_id,
            Limit=10
        )
        
        if users_response['Users']:
            print(f"   📋 Recent users (showing last 10):")
            for user in users_response['Users']:
                username = user['Username']
                status = user['UserStatus']
                created = user['UserCreateDate']
                
                # Check if user is enabled
                try:
                    user_info = cognito.admin_get_user(
                        UserPoolId=user_pool_id,
                        Username=username
                    )
                    enabled = user_info['Enabled']
                    status_icon = "✅" if enabled else "❌"
                except:
                    enabled = "Unknown"
                    status_icon = "❓"
                
                print(f"      {status_icon} {username} - {status} - {created.strftime('%Y-%m-%d %H:%M')} - Enabled: {enabled}")
        else:
            print("   ℹ️  No users found")
            
    except Exception as e:
        print(f"❌ Error checking user activity: {e}")
    
    print(f"\n🏁 Monitoring complete!")
    print("=" * 70)
    print("\n💡 Recommendations:")
    print("   - Check CloudWatch logs for specific error patterns")
    print("   - Monitor authentication failure metrics")
    print("   - Verify user pool configuration")
    print("   - Test invitation flow with debug script")

if __name__ == "__main__":
    monitor_auth_issues()