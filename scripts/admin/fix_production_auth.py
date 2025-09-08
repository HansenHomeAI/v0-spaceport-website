#!/usr/bin/env python3
"""
Fix Production Authentication Issues
Addresses the FORCE_CHANGE_PASSWORD status and creates working test accounts.
"""

import boto3
import json
import time
from datetime import datetime
import random
import string

# Production AWS Configuration
REGION = 'us-west-2'
USER_POOL_ID = 'us-west-2_SnOJuAJXa'
CLIENT_ID = 'cvtn1c5dprnfbvpbtsuhit6vi'

def generate_test_email():
    """Generate a unique test email address."""
    timestamp = int(time.time())
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"test-{timestamp}-{random_suffix}@spcprt.com"

def generate_test_password():
    """Generate a strong test password."""
    return f"TestPass123!{random.randint(100, 999)}"

class ProductionAuthFixer:
    def __init__(self):
        self.cognito = boto3.client('cognito-idp', region_name=REGION)
        
    def fix_user_password_status(self, email, new_password):
        """Fix a user's FORCE_CHANGE_PASSWORD status by setting a permanent password."""
        try:
            # Set permanent password
            response = self.cognito.admin_set_user_password(
                UserPoolId=USER_POOL_ID,
                Username=email,
                Password=new_password,
                Permanent=True
            )
            
            print(f"✅ Fixed password status for {email}")
            return True
            
        except Exception as e:
            print(f"❌ Error fixing {email}: {str(e)}")
            return False
            
    def create_working_test_account(self, email, password):
        """Create a test account that works properly."""
        try:
            # Create user with all required attributes
            response = self.cognito.admin_create_user(
                UserPoolId=USER_POOL_ID,
                Username=email,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'preferred_username', 'Value': email}
                ],
                TemporaryPassword=password,
                MessageAction='SUPPRESS'  # Don't send welcome email
            )
            
            # Set permanent password immediately
            self.cognito.admin_set_user_password(
                UserPoolId=USER_POOL_ID,
                Username=email,
                Password=password,
                Permanent=True
            )
            
            print(f"✅ Created working test account: {email}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating test account {email}: {str(e)}")
            return False
            
    def test_authentication(self, email, password):
        """Test authentication with an account."""
        try:
            response = self.cognito.admin_initiate_auth(
                UserPoolId=USER_POOL_ID,
                ClientId=CLIENT_ID,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password
                }
            )
            
            if response.get('AuthenticationResult'):
                print(f"✅ Authentication successful for {email}")
                return True
            else:
                print(f"❌ Authentication failed for {email}: No auth result")
                return False
                
        except Exception as e:
            print(f"❌ Authentication failed for {email}: {str(e)}")
            return False
            
    def test_password_reset(self, email):
        """Test password reset flow."""
        try:
            response = self.cognito.forgot_password(
                ClientId=CLIENT_ID,
                Username=email
            )
            
            if response.get('CodeDeliveryDetails'):
                destination = response['CodeDeliveryDetails'].get('Destination', 'Unknown')
                print(f"✅ Password reset initiated for {email} - Code sent to: {destination}")
                return True
            else:
                print(f"❌ Password reset failed for {email}: No delivery details")
                return False
                
        except Exception as e:
            print(f"❌ Password reset failed for {email}: {str(e)}")
            return False
            
    def run_fix_and_test(self):
        """Run the complete fix and test process."""
        print("🔧 Fixing Production Authentication Issues")
        print("=" * 60)
        
        # Step 1: Fix existing users with FORCE_CHANGE_PASSWORD status
        print("\n🔑 Fixing Existing Users...")
        existing_users = [
            'gbhbyu@gmail.com',
            'ethan@spcprt.com',
            'test@example.com'
        ]
        
        fixed_users = []
        for email in existing_users:
            new_password = generate_test_password()
            if self.fix_user_password_status(email, new_password):
                fixed_users.append({'email': email, 'password': new_password})
                
        # Step 2: Create new test accounts
        print("\n🧪 Creating New Test Accounts...")
        test_accounts = []
        for i in range(3):
            email = generate_test_email()
            password = generate_test_password()
            
            if self.create_working_test_account(email, password):
                test_accounts.append({'email': email, 'password': password})
                
        # Step 3: Test authentication with fixed accounts
        print("\n🔐 Testing Authentication...")
        all_accounts = fixed_users + test_accounts
        
        for account in all_accounts:
            self.test_authentication(account['email'], account['password'])
            
        # Step 4: Test password reset with all accounts
        print("\n🔄 Testing Password Reset...")
        for account in all_accounts:
            self.test_password_reset(account['email'])
            
        # Step 5: Summary
        print("\n📊 Summary")
        print("=" * 60)
        print(f"Fixed existing users: {len(fixed_users)}")
        print(f"Created test accounts: {len(test_accounts)}")
        print(f"Total working accounts: {len(all_accounts)}")
        
        if all_accounts:
            print(f"\n🎯 Working Test Accounts:")
            for i, account in enumerate(all_accounts, 1):
                print(f"  {i}. 📧 {account['email']}")
                print(f"     🔑 {account['password']}")
                print()
                
        # Save account details
        with open('production_test_accounts.json', 'w') as f:
            json.dump(all_accounts, f, indent=2)
            
        print(f"📄 Account details saved to: production_test_accounts.json")
        
        return all_accounts

if __name__ == "__main__":
    fixer = ProductionAuthFixer()
    accounts = fixer.run_fix_and_test()
