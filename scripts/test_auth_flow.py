#!/usr/bin/env python3
"""
Test script to diagnose authentication flow issues with Cognito invite system.
This script helps identify why users get "Invalid username or password" errors.
"""

import boto3
import json
import sys
import time
from datetime import datetime
import argparse

def test_user_pool_config(user_pool_id, region='us-west-2'):
    """Check user pool configuration"""
    print("\n=== Testing User Pool Configuration ===")
    
    client = boto3.client('cognito-idp', region_name=region)
    
    try:
        # Get user pool details
        pool = client.describe_user_pool(UserPoolId=user_pool_id)['UserPool']
        
        print(f"✓ User Pool Name: {pool.get('Name')}")
        print(f"✓ User Pool ID: {user_pool_id}")
        
        # Check sign-in options
        print("\n📝 Sign-in Configuration:")
        alias_attrs = pool.get('AliasAttributes', [])
        username_attrs = pool.get('UsernameAttributes', [])
        
        if alias_attrs:
            print(f"  - Alias Attributes: {', '.join(alias_attrs)}")
        if username_attrs:
            print(f"  - Username Attributes: {', '.join(username_attrs)}")
        
        if 'email' in alias_attrs or 'email' in username_attrs:
            print("  ✓ Email sign-in is enabled")
        else:
            print("  ⚠️ Email sign-in might not be properly configured!")
        
        # Check password policy
        policy = pool.get('Policies', {}).get('PasswordPolicy', {})
        print(f"\n🔒 Password Policy:")
        print(f"  - Min Length: {policy.get('MinimumLength', 'Not set')}")
        print(f"  - Require Uppercase: {policy.get('RequireUppercase', False)}")
        print(f"  - Require Lowercase: {policy.get('RequireLowercase', False)}")
        print(f"  - Require Numbers: {policy.get('RequireNumbers', False)}")
        print(f"  - Require Symbols: {policy.get('RequireSymbols', False)}")
        print(f"  - Temp Password Validity: {policy.get('TemporaryPasswordValidityDays', 7)} days")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking user pool: {e}")
        return False


def check_user_status(email, user_pool_id, region='us-west-2'):
    """Check if a user exists and their status"""
    print(f"\n=== Checking User Status for {email} ===")
    
    client = boto3.client('cognito-idp', region_name=region)
    
    try:
        # List users with email filter
        response = client.list_users(
            UserPoolId=user_pool_id,
            Filter=f'email = "{email}"',
            Limit=10
        )
        
        if not response.get('Users'):
            print(f"❌ No user found with email: {email}")
            return None
        
        for user in response['Users']:
            print(f"\n📤 User Found:")
            print(f"  - Username: {user['Username']}")
            print(f"  - Status: {user['UserStatus']}")
            print(f"  - Created: {user.get('UserCreateDate', 'Unknown')}")
            print(f"  - Modified: {user.get('UserLastModifiedDate', 'Unknown')}")
            
            # Check attributes
            attrs = {attr['Name']: attr['Value'] for attr in user.get('Attributes', [])}
            print(f"\n  Attributes:")
            for key, value in attrs.items():
                if key in ['email', 'email_verified', 'preferred_username', 'name']:
                    print(f"    - {key}: {value}")
            
            # Check what the user should sign in with
            print(f"\n  🔑 Sign-in Instructions:")
            print(f"    - Use email: {attrs.get('email', email)}")
            print(f"    - Status indicates: ", end="")
            
            status = user['UserStatus']
            if status == 'FORCE_CHANGE_PASSWORD':
                print("User must change password on next login")
            elif status == 'CONFIRMED':
                print("User is confirmed and should be able to sign in")
            elif status == 'UNCONFIRMED':
                print("User needs to confirm their account")
            elif status == 'COMPROMISED':
                print("User account is compromised")
            elif status == 'ARCHIVED':
                print("User account is archived")
            elif status == 'RESET_REQUIRED':
                print("Password reset is required")
            else:
                print(f"Unknown status: {status}")
                
            return user
            
    except Exception as e:
        print(f"❌ Error checking user: {e}")
        return None


def test_authentication(email, password, user_pool_id, client_id, region='us-west-2'):
    """Test authentication with given credentials"""
    print(f"\n=== Testing Authentication ===")
    print(f"  Email: {email}")
    print(f"  Password: {'*' * len(password)}")
    
    client = boto3.client('cognito-idp', region_name=region)
    
    # Try different authentication methods
    methods_to_try = [
        ('USER_PASSWORD_AUTH', {'USERNAME': email, 'PASSWORD': password}),
        ('USER_SRP_AUTH', None),  # SRP requires more complex flow
    ]
    
    for auth_flow, auth_params in methods_to_try:
        if auth_flow == 'USER_SRP_AUTH':
            print(f"\n  ℹ️ Skipping {auth_flow} (requires complex SRP flow)")
            continue
            
        print(f"\n  Testing {auth_flow}...")
        
        try:
            response = client.initiate_auth(
                ClientId=client_id,
                AuthFlow=auth_flow,
                AuthParameters=auth_params
            )
            
            if 'ChallengeName' in response:
                print(f"  ✓ Auth initiated, challenge required: {response['ChallengeName']}")
                if response['ChallengeName'] == 'NEW_PASSWORD_REQUIRED':
                    print("    → User needs to set a new password")
                    return 'NEW_PASSWORD_REQUIRED'
            elif 'AuthenticationResult' in response:
                print(f"  ✓ Authentication successful!")
                return 'SUCCESS'
            else:
                print(f"  ⚠️ Unexpected response: {response}")
                
        except client.exceptions.NotAuthorizedException as e:
            error_msg = str(e)
            print(f"  ❌ Not Authorized: {error_msg}")
            
            # Parse specific error messages
            if 'Incorrect username or password' in error_msg:
                print("    → The username or password is incorrect")
            elif 'User does not exist' in error_msg:
                print("    → User not found with this username")
            elif 'Password attempts exceeded' in error_msg:
                print("    → Too many failed attempts, account may be locked")
                
        except client.exceptions.UserNotFoundException:
            print(f"  ❌ User not found with email: {email}")
            
        except client.exceptions.UserNotConfirmedException:
            print(f"  ❌ User is not confirmed")
            
        except client.exceptions.InvalidParameterException as e:
            print(f"  ❌ Invalid parameter: {e}")
            print("    → This might indicate the auth flow is not enabled")
            
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
    
    return None


def reset_user_password(email, new_password, user_pool_id, region='us-west-2'):
    """Admin reset user password for testing"""
    print(f"\n=== Resetting Password for {email} ===")
    
    client = boto3.client('cognito-idp', region_name=region)
    
    try:
        # First, find the user
        response = client.list_users(
            UserPoolId=user_pool_id,
            Filter=f'email = "{email}"',
            Limit=1
        )
        
        if not response.get('Users'):
            print(f"❌ User not found: {email}")
            return False
        
        username = response['Users'][0]['Username']
        print(f"  Found user: {username}")
        
        # Set new temporary password
        client.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=username,
            Password=new_password,
            Permanent=False  # Force password change on next login
        )
        
        print(f"  ✓ Password reset to: {new_password}")
        print(f"  ℹ️ User will need to change password on next login")
        return True
        
    except Exception as e:
        print(f"❌ Error resetting password: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Test Cognito authentication flow')
    parser.add_argument('--user-pool-id', required=True, help='Cognito User Pool ID')
    parser.add_argument('--client-id', required=True, help='Cognito Client ID')
    parser.add_argument('--email', help='Email address to test')
    parser.add_argument('--password', help='Password to test')
    parser.add_argument('--reset-password', help='Reset password to this value (admin only)')
    parser.add_argument('--region', default='us-west-2', help='AWS region')
    parser.add_argument('--check-only', action='store_true', help='Only check user status, don\'t test auth')
    
    args = parser.parse_args()
    
    print("🔍 Cognito Authentication Flow Tester")
    print("=" * 50)
    
    # Test user pool configuration
    if not test_user_pool_config(args.user_pool_id, args.region):
        print("\n❌ Failed to check user pool configuration")
        return 1
    
    # Check user status if email provided
    if args.email:
        user = check_user_status(args.email, args.user_pool_id, args.region)
        
        if args.reset_password and user:
            reset_user_password(args.email, args.reset_password, args.user_pool_id, args.region)
            # Re-check status after reset
            check_user_status(args.email, args.user_pool_id, args.region)
        
        # Test authentication if password provided
        if args.password and not args.check_only:
            result = test_authentication(
                args.email, 
                args.password, 
                args.user_pool_id,
                args.client_id,
                args.region
            )
            
            if result == 'SUCCESS':
                print("\n✅ Authentication successful!")
            elif result == 'NEW_PASSWORD_REQUIRED':
                print("\n⚠️ Authentication requires password change")
            else:
                print("\n❌ Authentication failed")
                
                # Provide debugging suggestions
                print("\n💡 Debugging Suggestions:")
                print("1. Verify the email address is correct")
                print("2. Check if the temporary password has expired (7 days)")
                print("3. Ensure you're using the exact password from the invite email")
                print("4. Try resetting the password with --reset-password option")
                print("5. Check CloudWatch logs for the Lambda function")
    
    print("\n" + "=" * 50)
    print("Test completed")
    return 0


if __name__ == '__main__':
    sys.exit(main())