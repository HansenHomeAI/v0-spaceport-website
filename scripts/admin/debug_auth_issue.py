#!/usr/bin/env python3
"""
Debug authentication issues by testing the full user invitation and sign-in flow.
This script helps identify where the authentication process might be failing.
"""

import boto3
import json
import sys
import time
from datetime import datetime

def debug_auth_flow():
    """Debug the complete authentication flow"""
    
    # Initialize AWS clients
    cognito = boto3.client('cognito-idp', region_name='us-west-2')
    
    # Get user pool ID from environment or prompt
    user_pool_id = input("Enter Cognito User Pool ID: ").strip()
    if not user_pool_id:
        print("❌ User Pool ID is required")
        return
    
    test_email = input("Enter test email address: ").strip()
    if not test_email:
        print("❌ Test email is required")
        return
    
    print(f"\n🔍 Debugging authentication flow for {test_email}")
    print("=" * 60)
    
    # Step 1: Check if user exists
    print("\n1️⃣ Checking if user exists...")
    try:
        user_info = cognito.admin_get_user(
            UserPoolId=user_pool_id,
            Username=test_email
        )
        print(f"✅ User exists: {user_info['Username']}")
        print(f"   Status: {user_info['UserStatus']}")
        print(f"   Enabled: {user_info['Enabled']}")
        print(f"   Created: {user_info['UserCreateDate']}")
        
        # Check user attributes
        print("\n📋 User Attributes:")
        for attr in user_info.get('UserAttributes', []):
            if attr['Name'] in ['email', 'email_verified', 'preferred_username']:
                print(f"   {attr['Name']}: {attr['Value']}")
        
        # Check if user is in any groups
        try:
            groups = cognito.admin_list_groups_for_user(
                UserPoolId=user_pool_id,
                Username=test_email
            )
            if groups['Groups']:
                print(f"\n👥 User Groups:")
                for group in groups['Groups']:
                    print(f"   - {group['GroupName']}")
            else:
                print("\n⚠️  User is not in any groups")
        except Exception as e:
            print(f"❌ Error checking groups: {e}")
            
    except cognito.exceptions.UserNotFoundException:
        print("❌ User not found - they need to be invited first")
        return
    except Exception as e:
        print(f"❌ Error checking user: {e}")
        return
    
    # Step 2: Test sign-in with temporary password
    print(f"\n2️⃣ Testing sign-in...")
    temp_password = input("Enter the temporary password from the invite email: ").strip()
    
    if not temp_password:
        print("❌ Temporary password is required")
        return
    
    try:
        # Attempt to sign in
        auth_result = cognito.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=input("Enter Cognito Client ID: ").strip(),
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': test_email,
                'PASSWORD': temp_password
            }
        )
        
        print(f"✅ Sign-in successful!")
        print(f"   Challenge: {auth_result.get('ChallengeName', 'None')}")
        
        if auth_result.get('ChallengeName') == 'NEW_PASSWORD_REQUIRED':
            print("   ⚠️  User needs to set a new password (this is expected)")
        else:
            print("   ✅ User is fully authenticated")
            
    except cognito.exceptions.NotAuthorizedException:
        print("❌ Invalid username or password")
        print("   Possible causes:")
        print("   - Wrong temporary password")
        print("   - Password expired")
        print("   - User account disabled")
    except cognito.exceptions.UserNotFoundException:
        print("❌ User not found")
    except cognito.exceptions.UserNotConfirmedException:
        print("❌ User not confirmed - check email verification")
    except cognito.exceptions.TooManyRequestsException:
        print("❌ Too many failed attempts - rate limited")
    except Exception as e:
        print(f"❌ Sign-in failed: {e}")
    
    # Step 3: Check user pool configuration
    print(f"\n3️⃣ Checking User Pool configuration...")
    try:
        pool_info = cognito.describe_user_pool(UserPoolId=user_pool_id)
        pool = pool_info['UserPool']
        
        print(f"   Pool Name: {pool['Name']}")
        print(f"   Self Sign-up: {pool.get('AdminCreateUserConfig', {}).get('AllowAdminCreateUserOnly', True)}")
        print(f"   Email Verification: {pool.get('AutoVerifiedAttributes', [])}")
        
        # Check password policy
        policy = pool.get('Policies', {}).get('PasswordPolicy', {})
        print(f"\n🔒 Password Policy:")
        print(f"   Min Length: {policy.get('MinimumLength', 'Not set')}")
        print(f"   Require Lowercase: {policy.get('RequireLowercase', False)}")
        print(f"   Require Uppercase: {policy.get('RequireUppercase', False)}")
        print(f"   Require Numbers: {policy.get('RequireNumbers', False)}")
        print(f"   Require Symbols: {policy.get('RequireSymbols', False)}")
        print(f"   Temp Password Validity: {policy.get('TemporaryPasswordValidityDays', 'Not set')} days")
        
    except Exception as e:
        print(f"❌ Error checking user pool: {e}")
    
    print(f"\n🏁 Debug complete!")
    print("=" * 60)

if __name__ == "__main__":
    debug_auth_flow()