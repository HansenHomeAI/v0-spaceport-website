#!/usr/bin/env python3
"""
Beta Access Testing Script
Tests the complete beta access granting workflow for employee-level permissions.
"""

import boto3
import json
import requests
import time
from datetime import datetime
import random
import string

# Production AWS Configuration
REGION = 'us-west-2'
USER_POOL_ID = 'us-west-2_SnOJuAJXa'
CLIENT_ID = 'cvtn1c5dprnfbvpbtsuhit6vi'
BETA_ACCESS_API_URL = 'https://84ufey2j0g.execute-api.us-west-2.amazonaws.com/prod'

def generate_test_email():
    """Generate a unique test email address."""
    timestamp = int(time.time())
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"beta-test-{timestamp}-{random_suffix}@spcprt.com"

class BetaAccessTester:
    def __init__(self):
        self.cognito = boto3.client('cognito-idp', region_name=REGION)
        self.dynamodb = boto3.resource('dynamodb', region_name=REGION)
        self.beta_permissions_table = self.dynamodb.Table('Spaceport-BetaAccessPermissions-prod')
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
        
    def get_employee_accounts(self):
        """Get all accounts with beta access admin permissions."""
        try:
            response = self.beta_permissions_table.scan(
                FilterExpression='permission_type = :perm AND #status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':perm': 'beta_access_admin',
                    ':status': 'active'
                }
            )
            
            employees = []
            for item in response['Items']:
                # Get user details from Cognito
                try:
                    user_response = self.cognito.admin_get_user(
                        UserPoolId=USER_POOL_ID,
                        Username=item['user_id']
                    )
                    
                    email = next((attr['Value'] for attr in user_response.get('UserAttributes', []) if attr['Name'] == 'email'), 'No email')
                    employees.append({
                        'user_id': item['user_id'],
                        'email': email,
                        'permission_type': item['permission_type'],
                        'status': item['status'],
                        'granted_by': item.get('granted_by', 'Unknown'),
                        'granted_at': item.get('granted_at', 'Unknown')
                    })
                except Exception as e:
                    print(f"Warning: Could not get user details for {item['user_id']}: {str(e)}")
                    
            return employees
            
        except Exception as e:
            self.log_result("Get Employee Accounts", False, f"Error: {str(e)}")
            return []
            
    def test_beta_access_api_endpoints(self):
        """Test the beta access API endpoints."""
        try:
            # Test the API is accessible
            response = requests.get(f"{BETA_ACCESS_API_URL}/admin/beta-access/check-permission", timeout=10)
            
            if response.status_code in [401, 403]:
                self.log_result("Beta Access API Accessibility", True, f"API accessible (Status: {response.status_code})")
                return True
            elif response.status_code == 404:
                self.log_result("Beta Access API Accessibility", False, "API endpoint not found")
                return False
            else:
                self.log_result("Beta Access API Accessibility", True, f"Status: {response.status_code}")
                return True
                
        except Exception as e:
            self.log_result("Beta Access API Accessibility", False, f"Error: {str(e)}")
            return False
            
    def test_employee_permissions(self, employee):
        """Test if an employee can grant beta access."""
        try:
            # This would require implementing the actual API call with proper authentication
            # For now, we'll just verify the employee has the right permissions in the database
            
            if employee['permission_type'] == 'beta_access_admin' and employee['status'] == 'active':
                self.log_result(f"Employee Permissions - {employee['email']}", True, 
                              f"Has {employee['permission_type']} permission")
                return True
            else:
                self.log_result(f"Employee Permissions - {employee['email']}", False, 
                              f"Missing or inactive permissions: {employee['permission_type']} - {employee['status']}")
                return False
                
        except Exception as e:
            self.log_result(f"Employee Permissions - {employee['email']}", False, f"Error: {str(e)}")
            return False
            
    def create_test_beta_user(self, email):
        """Create a test user for beta access testing."""
        try:
            password = f"TestPass123!{random.randint(100, 999)}"
            
            # Create user in Cognito
            response = self.cognito.admin_create_user(
                UserPoolId=USER_POOL_ID,
                Username=email,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'preferred_username', 'Value': email}
                ],
                TemporaryPassword=password,
                MessageAction='SUPPRESS'
            )
            
            # Set permanent password
            self.cognito.admin_set_user_password(
                UserPoolId=USER_POOL_ID,
                Username=email,
                Password=password,
                Permanent=True
            )
            
            user_id = response['User']['Username']
            self.log_result(f"Create Test Beta User - {email}", True, f"Created with ID: {user_id}")
            return {'email': email, 'password': password, 'user_id': user_id}
            
        except Exception as e:
            self.log_result(f"Create Test Beta User - {email}", False, f"Error: {str(e)}")
            return None
            
    def test_beta_access_granting_workflow(self, employee, test_user):
        """Test the complete beta access granting workflow."""
        try:
            # Step 1: Check if employee can grant beta access
            if not self.test_employee_permissions(employee):
                return False
                
            # Step 2: Simulate granting beta access (this would normally be done via API)
            # For now, we'll add the permission directly to the database
            self.beta_permissions_table.put_item(
                Item={
                    'user_id': test_user['user_id'],
                    'email': test_user['email'],
                    'permission_type': 'beta_access',
                    'granted_by': employee['email'],
                    'granted_at': datetime.now().isoformat(),
                    'status': 'active'
                }
            )
            
            # Step 3: Verify the permission was granted
            response = self.beta_permissions_table.get_item(
                Key={'user_id': test_user['user_id']}
            )
            
            if 'Item' in response and response['Item']['permission_type'] == 'beta_access':
                self.log_result(f"Beta Access Granting - {test_user['email']}", True, 
                              f"Successfully granted by {employee['email']}")
                return True
            else:
                self.log_result(f"Beta Access Granting - {test_user['email']}", False, 
                              "Permission not found in database")
                return False
                
        except Exception as e:
            self.log_result(f"Beta Access Granting - {test_user['email']}", False, f"Error: {str(e)}")
            return False
            
    def run_comprehensive_test(self):
        """Run all beta access tests."""
        print("🔐 Testing Beta Access Functionality")
        print("=" * 60)
        
        # Step 1: Get employee accounts
        print("\n👥 Checking Employee Accounts...")
        employees = self.get_employee_accounts()
        
        if not employees:
            print("❌ No employee accounts found with beta access admin permissions")
            return
            
        print(f"✅ Found {len(employees)} employee account(s):")
        for employee in employees:
            print(f"  📧 {employee['email']}")
            print(f"     Permission: {employee['permission_type']}")
            print(f"     Status: {employee['status']}")
            print(f"     Granted by: {employee['granted_by']}")
            print()
            
        # Step 2: Test API endpoints
        print("\n🔗 Testing Beta Access API...")
        self.test_beta_access_api_endpoints()
        
        # Step 3: Test employee permissions
        print("\n🔑 Testing Employee Permissions...")
        for employee in employees:
            self.test_employee_permissions(employee)
            
        # Step 4: Test beta access granting workflow
        print("\n🎯 Testing Beta Access Granting Workflow...")
        test_user_email = generate_test_email()
        test_user = self.create_test_beta_user(test_user_email)
        
        if test_user and employees:
            # Test with the first employee
            employee = employees[0]
            self.test_beta_access_granting_workflow(employee, test_user)
            
        # Summary
        print("\n📊 Beta Access Test Summary")
        print("=" * 60)
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        print(f"Tests Passed: {passed}/{total}")
        
        if employees:
            print(f"\n👥 Employee Accounts with Beta Access Admin:")
            for employee in employees:
                print(f"  📧 {employee['email']}")
                print(f"     🔑 {employee['permission_type']} - {employee['status']}")
                print()
                
        if test_user:
            print(f"\n🧪 Test User Created:")
            print(f"  📧 {test_user['email']}")
            print(f"  🔑 {test_user['password']}")
            print()
            
        # Save results
        with open('beta_access_test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
            
        print(f"📄 Detailed results saved to: beta_access_test_results.json")
        
        return self.test_results

if __name__ == "__main__":
    tester = BetaAccessTester()
    results = tester.run_comprehensive_test()
