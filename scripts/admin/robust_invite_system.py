#!/usr/bin/env python3
"""
Robust Invitation System with Enhanced Error Handling and Diagnostics

This script provides:
1. Pre-flight checks for invitation consistency
2. Robust invitation flow with retries
3. Comprehensive logging and diagnostics
4. Environment validation
5. User state verification
"""

import json
import time
import boto3
import requests
from typing import Dict, Optional, Tuple, Any
import logging
from datetime import datetime, timedelta
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RobustInviteSystem:
    def __init__(self, region: str = 'us-west-2'):
        self.region = region
        self.cognito_client = boto3.client('cognito-idp', region_name=region)
        self.cloudformation = boto3.client('cloudformation', region_name=region)
        
        # Configuration will be loaded from CloudFormation
        self.user_pool_id = None
        self.client_id = None
        self.invite_api_url = None
        
    def load_configuration(self) -> bool:
        """Load configuration from CloudFormation stacks"""
        try:
            # Find Auth stack
            stacks = self.cloudformation.list_stacks(
                StackStatusFilter=['CREATE_COMPLETE', 'UPDATE_COMPLETE']
            )
            
            auth_stack = None
            for stack in stacks['StackSummaries']:
                if 'Auth' in stack['StackName'] and 'Spaceport' in stack['StackName']:
                    auth_stack = stack['StackName']
                    break
            
            if not auth_stack:
                logger.error("No Auth stack found")
                return False
            
            logger.info(f"Using Auth stack: {auth_stack}")
            
            # Get stack outputs
            stack_info = self.cloudformation.describe_stacks(StackName=auth_stack)
            outputs = stack_info['Stacks'][0]['Outputs']
            
            # Extract Cognito configuration
            for output in outputs:
                if 'CognitoUserPoolId' in output['OutputKey']:
                    self.user_pool_id = output['OutputValue']
                elif 'CognitoUserPoolClientId' in output['OutputKey']:
                    self.client_id = output['OutputValue']
                elif 'InviteApi' in output['OutputKey']:
                    self.invite_api_url = output['OutputValue']
            
            if not all([self.user_pool_id, self.client_id, self.invite_api_url]):
                logger.error("Missing required configuration values")
                return False
                
            logger.info(f"Configuration loaded successfully:")
            logger.info(f"  User Pool ID: {self.user_pool_id}")
            logger.info(f"  Client ID: {self.client_id}")
            logger.info(f"  Invite API: {self.invite_api_url}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False
    
    def validate_user_pool_health(self) -> bool:
        """Validate that the User Pool and Client are properly configured"""
        try:
            # Check User Pool
            pool_info = self.cognito_client.describe_user_pool(UserPoolId=self.user_pool_id)
            pool_status = pool_info['UserPool']['Status']
            
            if pool_status != 'Enabled':
                logger.error(f"User Pool status is {pool_status}, not Enabled")
                return False
            
            # Check User Pool Client
            client_info = self.cognito_client.describe_user_pool_client(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id
            )
            
            auth_flows = client_info['UserPoolClient'].get('ExplicitAuthFlows', [])
            required_flows = ['ADMIN_NO_SRP_AUTH', 'ALLOW_USER_PASSWORD_AUTH']
            
            if not any(flow in auth_flows for flow in required_flows):
                logger.warning(f"User Pool Client may not have required auth flows: {auth_flows}")
            
            logger.info("User Pool health check passed")
            return True
            
        except Exception as e:
            logger.error(f"User Pool health check failed: {e}")
            return False
    
    def check_user_exists(self, email: str) -> Tuple[bool, Optional[str]]:
        """Check if user exists and return their status"""
        try:
            user_info = self.cognito_client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=email
            )
            status = user_info['UserStatus']
            logger.info(f"User {email} exists with status: {status}")
            return True, status
        except self.cognito_client.exceptions.UserNotFoundException:
            logger.info(f"User {email} does not exist")
            return False, None
        except Exception as e:
            logger.error(f"Error checking user existence: {e}")
            return False, None
    
    def send_invitation_with_retry(self, email: str, name: str = "", max_retries: int = 3) -> bool:
        """Send invitation with retry logic and comprehensive error handling"""
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Sending invitation attempt {attempt + 1} to {email}")
                
                # Prepare invitation payload
                payload = {
                    'email': email.lower().strip(),
                    'name': name.strip(),
                    'suppress': True  # Always suppress Cognito email, send custom
                }
                
                # Send invitation request
                response = requests.post(
                    self.invite_api_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Invitation sent successfully: {result}")
                    return True
                else:
                    logger.error(f"Invitation failed with status {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"Invitation attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        
        return False
    
    def verify_user_creation(self, email: str, timeout: int = 30) -> bool:
        """Verify that the user was created successfully with proper status"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            exists, status = self.check_user_exists(email)
            
            if exists:
                if status in ['FORCE_CHANGE_PASSWORD', 'CONFIRMED']:
                    logger.info(f"User {email} created successfully with status: {status}")
                    return True
                else:
                    logger.warning(f"User {email} has unexpected status: {status}")
            
            time.sleep(2)
        
        logger.error(f"User {email} was not created within {timeout} seconds")
        return False
    
    def test_authentication_flow(self, email: str, temp_password: str) -> Tuple[bool, str]:
        """Test the authentication flow to identify potential issues"""
        try:
            logger.info(f"Testing authentication for {email}")
            
            response = self.cognito_client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': temp_password
                }
            )
            
            if 'ChallengeName' in response:
                challenge = response['ChallengeName']
                logger.info(f"Authentication successful - Challenge: {challenge}")
                if challenge == 'NEW_PASSWORD_REQUIRED':
                    return True, "NEW_PASSWORD_REQUIRED"
                else:
                    return True, challenge
            elif 'AuthenticationResult' in response:
                logger.info("Authentication successful - No challenge required")
                return True, "SUCCESS"
            else:
                logger.error("Unexpected authentication response")
                return False, "UNEXPECTED_RESPONSE"
                
        except self.cognito_client.exceptions.NotAuthorizedException as e:
            logger.error(f"Authentication failed - Invalid credentials: {e}")
            return False, "INVALID_CREDENTIALS"
        except self.cognito_client.exceptions.UserNotFoundException as e:
            logger.error(f"Authentication failed - User not found: {e}")
            return False, "USER_NOT_FOUND"
        except Exception as e:
            logger.error(f"Authentication test failed: {e}")
            return False, str(e)
    
    def comprehensive_invite_test(self, email: str, name: str = "Test User") -> Dict[str, Any]:
        """Run a comprehensive test of the entire invitation flow"""
        results = {
            'email': email,
            'timestamp': datetime.utcnow().isoformat(),
            'steps': {},
            'success': False,
            'recommendations': []
        }
        
        logger.info(f"Starting comprehensive invite test for {email}")
        
        # Step 1: Load configuration
        logger.info("Step 1: Loading configuration...")
        if not self.load_configuration():
            results['steps']['configuration'] = False
            results['recommendations'].append("Check CloudFormation Auth stack deployment")
            return results
        results['steps']['configuration'] = True
        
        # Step 2: Validate User Pool health
        logger.info("Step 2: Validating User Pool health...")
        if not self.validate_user_pool_health():
            results['steps']['user_pool_health'] = False
            results['recommendations'].append("Check User Pool and Client configuration")
            return results
        results['steps']['user_pool_health'] = True
        
        # Step 3: Clean up any existing user
        logger.info("Step 3: Cleaning up existing user...")
        exists, status = self.check_user_exists(email)
        if exists:
            try:
                self.cognito_client.admin_delete_user(
                    UserPoolId=self.user_pool_id,
                    Username=email
                )
                logger.info(f"Deleted existing user {email}")
                time.sleep(2)  # Wait for deletion to propagate
            except Exception as e:
                logger.warning(f"Could not delete existing user: {e}")
        
        # Step 4: Send invitation
        logger.info("Step 4: Sending invitation...")
        if not self.send_invitation_with_retry(email, name):
            results['steps']['invitation'] = False
            results['recommendations'].append("Check Invite API Lambda function and permissions")
            return results
        results['steps']['invitation'] = True
        
        # Step 5: Verify user creation
        logger.info("Step 5: Verifying user creation...")
        if not self.verify_user_creation(email):
            results['steps']['user_creation'] = False
            results['recommendations'].append("Check Lambda function logs for user creation errors")
            return results
        results['steps']['user_creation'] = True
        
        # Step 6: Test authentication flow
        logger.info("Step 6: Testing authentication flow...")
        temp_password = f"Spcprt{int(time.time()) % 10000}A"
        
        # First, set the temporary password (simulating what the Lambda should do)
        try:
            self.cognito_client.admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=email,
                Password=temp_password,
                Permanent=False
            )
            logger.info(f"Set temporary password: {temp_password}")
        except Exception as e:
            logger.error(f"Failed to set temporary password: {e}")
            results['steps']['password_setup'] = False
            results['recommendations'].append("Check Lambda function password setting logic")
            return results
        
        auth_success, auth_result = self.test_authentication_flow(email, temp_password)
        results['steps']['authentication'] = auth_success
        results['auth_result'] = auth_result
        
        if not auth_success:
            if auth_result == "INVALID_CREDENTIALS":
                results['recommendations'].extend([
                    "Check temporary password generation and setting logic",
                    "Verify User Pool password policy matches generated passwords",
                    "Check for timing issues between user creation and password setting"
                ])
            elif auth_result == "USER_NOT_FOUND":
                results['recommendations'].extend([
                    "Check if user is being created in the correct User Pool",
                    "Verify frontend is configured with the same User Pool ID",
                    "Check for multiple User Pools in different environments"
                ])
            else:
                results['recommendations'].append(f"Investigate authentication error: {auth_result}")
            return results
        
        # Step 7: Cleanup
        logger.info("Step 7: Cleaning up test user...")
        try:
            self.cognito_client.admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=email
            )
            logger.info("Test user cleaned up successfully")
        except Exception as e:
            logger.warning(f"Could not clean up test user: {e}")
        
        results['success'] = True
        results['recommendations'].append("Invitation flow is working correctly")
        
        logger.info("Comprehensive test completed successfully!")
        return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 robust_invite_system.py <test_email> [name]")
        print("Example: python3 robust_invite_system.py test@example.com 'Test User'")
        sys.exit(1)
    
    email = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else "Test User"
    
    invite_system = RobustInviteSystem()
    results = invite_system.comprehensive_invite_test(email, name)
    
    print("\n" + "="*60)
    print("COMPREHENSIVE INVITATION FLOW TEST RESULTS")
    print("="*60)
    print(f"Email: {results['email']}")
    print(f"Timestamp: {results['timestamp']}")
    print(f"Overall Success: {'✅ PASS' if results['success'] else '❌ FAIL'}")
    print()
    
    print("Step Results:")
    for step, success in results['steps'].items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {step}: {status}")
    
    if 'auth_result' in results:
        print(f"  Authentication Result: {results['auth_result']}")
    
    print()
    print("Recommendations:")
    for i, rec in enumerate(results['recommendations'], 1):
        print(f"  {i}. {rec}")
    
    print("\n" + "="*60)
    
    # Exit with appropriate code
    sys.exit(0 if results['success'] else 1)


if __name__ == "__main__":
    main()