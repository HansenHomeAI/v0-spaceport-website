#!/usr/bin/env python3
"""
Test the complete user invitation flow to identify issues.
This script simulates the full invitation process and tests sign-in.
"""

import boto3
import json
import random
import string
import time
from datetime import datetime

def generate_test_password():
    """Generate a test password that meets Cognito requirements"""
    lowercase = ''.join(random.choice(string.ascii_lowercase) for _ in range(2))
    uppercase = ''.join(random.choice(string.ascii_uppercase) for _ in range(2))
    digits = ''.join(random.choice(string.digits) for _ in range(2))
    symbols = ''.join(random.choice('!@#$%^&*') for _ in range(2))
    
    password_chars = list(lowercase + uppercase + digits + symbols)
    random.shuffle(password_chars)
    return ''.join(password_chars)

def test_invitation_flow():
    """Test the complete invitation flow"""
    
    # Configuration
    user_pool_id = input("Enter Cognito User Pool ID: ").strip()
    client_id = input("Enter Cognito Client ID: ").strip()
    test_email = input("Enter test email address: ").strip()
    
    if not all([user_pool_id, client_id, test_email]):
        print("❌ All parameters are required")
        return
    
    cognito = boto3.client('cognito-idp', region_name='us-west-2')
    
    print(f"\n🧪 Testing invitation flow for {test_email}")
    print("=" * 60)
    
    # Step 1: Clean up any existing test user
    print("\n1️⃣ Cleaning up any existing test user...")
    try:
        cognito.admin_delete_user(
            UserPoolId=user_pool_id,
            Username=test_email
        )
        print("✅ Existing test user deleted")
        time.sleep(2)  # Wait for deletion to propagate
    except cognito.exceptions.UserNotFoundException:
        print("ℹ️  No existing user to clean up")
    except Exception as e:
        print(f"⚠️  Error cleaning up: {e}")
    
    # Step 2: Create test user
    print("\n2️⃣ Creating test user...")
    temp_password = generate_test_password()
    print(f"Generated temp password: {temp_password}")
    
    try:
        create_response = cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=test_email,
            UserAttributes=[
                {'Name': 'email', 'Value': test_email},
                {'Name': 'email_verified', 'Value': 'true'},
            ],
            TemporaryPassword=temp_password,
            MessageAction='SUPPRESS'  # Don't send Cognito email
        )
        
        print("✅ User created successfully")
        print(f"   User Status: {create_response['User']['UserStatus']}")
        
        # Add to beta-testers group if it exists
        try:
            cognito.admin_add_user_to_group(
                UserPoolId=user_pool_id,
                Username=test_email,
                GroupName='beta-testers'
            )
            print("✅ User added to beta-testers group")
        except Exception as e:
            print(f"⚠️  Could not add to group (may not exist): {e}")
            
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return
    
    # Step 3: Test sign-in with temporary password
    print("\n3️⃣ Testing sign-in with temporary password...")
    try:
        auth_response = cognito.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': test_email,
                'PASSWORD': temp_password
            }
        )
        
        print("✅ Sign-in successful!")
        print(f"   Challenge: {auth_response.get('ChallengeName', 'None')}")
        
        if auth_response.get('ChallengeName') == 'NEW_PASSWORD_REQUIRED':
            print("   ⚠️  User needs to set new password (expected)")
            
            # Step 4: Test password change
            print("\n4️⃣ Testing password change...")
            new_password = input("Enter new password (min 8 chars, upper, lower, number, symbol): ").strip()
            
            if not new_password:
                print("❌ New password required")
                return
            
            try:
                # Complete the password change
                complete_response = cognito.admin_respond_to_auth_challenge(
                    UserPoolId=user_pool_id,
                    ClientId=client_id,
                    ChallengeName='NEW_PASSWORD_REQUIRED',
                    Session=auth_response['Session'],
                    ChallengeResponses={
                        'USERNAME': test_email,
                        'NEW_PASSWORD': new_password
                    }
                )
                
                print("✅ Password changed successfully!")
                print(f"   Authentication: {complete_response.get('AuthenticationResult', {}).get('AccessToken', 'No token')[:20]}...")
                
            except Exception as e:
                print(f"❌ Error changing password: {e}")
                return
                
        else:
            print("   ✅ User is fully authenticated")
            
    except cognito.exceptions.NotAuthorizedException:
        print("❌ Invalid username or password")
        print("   This is the issue you're experiencing!")
        print("   Possible causes:")
        print("   - Password doesn't meet policy requirements")
        print("   - User account issues")
        print("   - Timing issues with user creation")
        return
    except Exception as e:
        print(f"❌ Sign-in failed: {e}")
        return
    
    # Step 5: Test final sign-in with new password
    print("\n5️⃣ Testing final sign-in with new password...")
    try:
        final_auth = cognito.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': test_email,
                'PASSWORD': new_password
            }
        )
        
        print("✅ Final sign-in successful!")
        print("   🎉 Complete authentication flow works!")
        
    except Exception as e:
        print(f"❌ Final sign-in failed: {e}")
    
    # Cleanup
    print(f"\n🧹 Cleaning up test user...")
    try:
        cognito.admin_delete_user(
            UserPoolId=user_pool_id,
            Username=test_email
        )
        print("✅ Test user cleaned up")
    except Exception as e:
        print(f"⚠️  Error cleaning up: {e}")
    
    print(f"\n🏁 Test complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_invitation_flow()