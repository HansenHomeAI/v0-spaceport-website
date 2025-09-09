#!/usr/bin/env python3
"""
Production Authentication Testing Script
Tests all authentication endpoints and creates test accounts for comprehensive testing.
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

class ProductionAuthTester:
    def __init__(self):
        self.cognito = boto3.client('cognito-idp', region_name=REGION)
        self.ses = boto3.client('ses', region_name=REGION)
        self.test_results = []
        
    def log_result(self, test_name, success, details=""):
        """Log test results."""
        result = {
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    def test_user_pool_configuration(self):
        """Test 1: Verify user pool configuration."""
        try:
            response = self.cognito.describe_user_pool(UserPoolId=USER_POOL_ID)
            user_pool = response['UserPool']
            
            # Check email configuration
            email_config = user_pool.get('EmailConfiguration', {})
            if email_config.get('EmailSendingAccount') == 'DEVELOPER':
                self.log_result("User Pool Email Config", True, "SES configured correctly")
            else:
                self.log_result("User Pool Email Config", False, f"Unexpected email config: {email_config}")
                
            # Check verification settings
            verification_template = user_pool.get('VerificationMessageTemplate', {})
            if verification_template.get('DefaultEmailOption') == 'CONFIRM_WITH_CODE':
                self.log_result("Verification Template", True, "Code-based verification enabled")
            else:
                self.log_result("Verification Template", False, f"Unexpected verification: {verification_template}")
                
        except Exception as e:
            self.log_result("User Pool Config", False, f"Error: {str(e)}")
            
    def test_client_configuration(self):
        """Test 2: Verify client configuration."""
        try:
            response = self.cognito.describe_user_pool_client(
                UserPoolId=USER_POOL_ID,
                ClientId=CLIENT_ID
            )
            client = response['UserPoolClient']
            
            # Check auth flows
            auth_flows = client.get('ExplicitAuthFlows', [])
            required_flows = ['ALLOW_USER_PASSWORD_AUTH', 'ALLOW_USER_SRP_AUTH']
            missing_flows = [flow for flow in required_flows if flow not in auth_flows]
            
            if not missing_flows:
                self.log_result("Client Auth Flows", True, f"All required flows present: {auth_flows}")
            else:
                self.log_result("Client Auth Flows", False, f"Missing flows: {missing_flows}")
                
            # Check callback URLs
            callback_urls = client.get('CallbackURLs', [])
            if 'https://spcprt.com/' in callback_urls:
                self.log_result("Callback URLs", True, f"Production URL configured: {callback_urls}")
            else:
                self.log_result("Callback URLs", False, f"Production URL missing: {callback_urls}")
                
        except Exception as e:
            self.log_result("Client Config", False, f"Error: {str(e)}")
            
    def test_ses_configuration(self):
        """Test 3: Verify SES email configuration."""
        try:
            response = self.ses.get_identity_verification_attributes(
                Identities=['hello@spcprt.com']
            )
            verification_status = response['VerificationAttributes'].get('hello@spcprt.com', {}).get('VerificationStatus')
            
            if verification_status == 'Success':
                self.log_result("SES Verification", True, "hello@spcprt.com verified")
            else:
                self.log_result("SES Verification", False, f"Status: {verification_status}")
                
        except Exception as e:
            self.log_result("SES Config", False, f"Error: {str(e)}")
            
    def create_test_account(self, email, password):
        """Create a test account."""
        try:
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
            
            # Set permanent password
            self.cognito.admin_set_user_password(
                UserPoolId=USER_POOL_ID,
                Username=email,
                Password=password,
                Permanent=True
            )
            
            return response['User']['Username']
            
        except Exception as e:
            print(f"Error creating test account {email}: {str(e)}")
            return None
            
    def test_password_reset_flow(self, email):
        """Test 4: Test password reset flow."""
        try:
            # Initiate password reset
            response = self.cognito.forgot_password(
                ClientId=CLIENT_ID,
                Username=email
            )
            
            if response.get('CodeDeliveryDetails'):
                self.log_result(f"Password Reset Initiated - {email}", True, 
                              f"Code sent to: {response['CodeDeliveryDetails'].get('Destination', 'Unknown')}")
                return True
            else:
                self.log_result(f"Password Reset Initiated - {email}", False, "No delivery details")
                return False
                
        except Exception as e:
            self.log_result(f"Password Reset Initiated - {email}", False, f"Error: {str(e)}")
            return False
            
    def test_authentication_flow(self, email, password):
        """Test 5: Test authentication flow."""
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
                self.log_result(f"Authentication - {email}", True, "Login successful")
                return True
            else:
                self.log_result(f"Authentication - {email}", False, "No auth result")
                return False
                
        except Exception as e:
            self.log_result(f"Authentication - {email}", False, f"Error: {str(e)}")
            return False
            
    def list_existing_users(self):
        """List all existing users in the user pool."""
        try:
            response = self.cognito.list_users(UserPoolId=USER_POOL_ID)
            users = response.get('Users', [])
            
            print(f"\n📋 Existing Users in Production User Pool ({len(users)} total):")
            print("-" * 80)
            
            for user in users:
                email = next((attr['Value'] for attr in user.get('Attributes', []) if attr['Name'] == 'email'), 'No email')
                status = user.get('UserStatus', 'Unknown')
                enabled = user.get('Enabled', False)
                print(f"  📧 {email}")
                print(f"     Status: {status}")
                print(f"     Enabled: {enabled}")
                print(f"     Username: {user.get('Username', 'Unknown')}")
                print()
                
        except Exception as e:
            print(f"Error listing users: {str(e)}")
            
    def run_comprehensive_test(self):
        """Run all tests and create test accounts."""
        print("🚀 Starting Production Authentication Testing")
        print("=" * 60)
        
        # Test 1: Configuration tests
        print("\n🔧 Testing Configuration...")
        self.test_user_pool_configuration()
        self.test_client_configuration()
        self.test_ses_configuration()
        
        # Test 2: List existing users
        print("\n👥 Listing Existing Users...")
        self.list_existing_users()
        
        # Test 3: Create test accounts
        print("\n🧪 Creating Test Accounts...")
        test_accounts = []
        for i in range(3):
            email = generate_test_email()
            password = generate_test_password()
            
            username = self.create_test_account(email, password)
            if username:
                test_accounts.append({'email': email, 'password': password, 'username': username})
                self.log_result(f"Create Test Account {i+1}", True, f"Created: {email}")
            else:
                self.log_result(f"Create Test Account {i+1}", False, f"Failed to create: {email}")
                
        # Test 4: Test authentication with new accounts
        print("\n🔐 Testing Authentication...")
        for account in test_accounts:
            self.test_authentication_flow(account['email'], account['password'])
            
        # Test 5: Test password reset with new accounts
        print("\n🔄 Testing Password Reset...")
        for account in test_accounts:
            self.test_password_reset_flow(account['email'])
            
        # Summary
        print("\n📊 Test Summary")
        print("=" * 60)
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        print(f"Tests Passed: {passed}/{total}")
        
        if test_accounts:
            print(f"\n🧪 Test Accounts Created:")
            for account in test_accounts:
                print(f"  📧 {account['email']}")
                print(f"  🔑 {account['password']}")
                print()
                
        # Save results
        with open('production_auth_test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
            
        print(f"📄 Detailed results saved to: production_auth_test_results.json")
        
        return self.test_results

if __name__ == "__main__":
    tester = ProductionAuthTester()
    results = tester.run_comprehensive_test()
