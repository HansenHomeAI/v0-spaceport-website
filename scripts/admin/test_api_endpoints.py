#!/usr/bin/env python3
"""
Comprehensive API Endpoint Testing Script
Tests all Spaceport API endpoints to verify they're working correctly
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class APITester:
    def __init__(self):
        self.results = []
        self.base_urls = {
            # Staging URLs (from CloudFormation outputs)
            'staging': {
                'drone_path': 'https://yhpjmfhdxf.execute-api.us-west-2.amazonaws.com/prod',
                'waitlist': 'https://h6ogvocgk4.execute-api.us-west-2.amazonaws.com/prod',
                'file_upload': 'https://xv4bpkwlb8.execute-api.us-west-2.amazonaws.com/prod',
                'password_reset': 'https://mx549qsbel.execute-api.us-west-2.amazonaws.com/prod',
                'invite': 'https://xtmhni13l2.execute-api.us-west-2.amazonaws.com/prod/invite',
                'projects': 'https://mca9yf1vgl.execute-api.us-west-2.amazonaws.com/prod/projects',
                'beta_access_admin': 'https://y5fej7zgx8.execute-api.us-west-2.amazonaws.com/prod',
                'subscription': 'https://xduxbyklm1.execute-api.us-west-2.amazonaws.com/prod',
                'feedback': 'https://pending-feedback-api.execute-api.us-west-2.amazonaws.com/prod'
            }
        }
    
    def test_endpoint(self, name: str, url: str, method: str = 'GET', 
                     data: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict:
        """Test a single API endpoint"""
        result = {
            'name': name,
            'url': url,
            'method': method,
            'status': 'unknown',
            'response_code': None,
            'response_time': None,
            'error': None,
            'success': False
        }
        
        try:
            start_time = datetime.now()
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method.upper() == 'OPTIONS':
                response = requests.options(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            result.update({
                'status': 'success' if response.status_code < 500 else 'error',
                'response_code': response.status_code,
                'response_time': response_time,
                'success': response.status_code < 500
            })
            
            # Try to parse JSON response
            try:
                result['response_body'] = response.json()
            except:
                result['response_body'] = response.text[:200]  # First 200 chars
            
        except requests.exceptions.Timeout:
            result.update({
                'status': 'timeout',
                'error': 'Request timed out after 10 seconds'
            })
        except requests.exceptions.ConnectionError:
            result.update({
                'status': 'connection_error',
                'error': 'Could not connect to endpoint'
            })
        except Exception as e:
            result.update({
                'status': 'error',
                'error': str(e)
            })
        
        return result
    
    def test_waitlist_endpoint(self, base_url: str) -> Dict:
        """Test waitlist endpoint with actual data"""
        url = f"{base_url}/waitlist"
        data = {
            "name": "API Test User",
            "email": "test@example.com"
        }
        headers = {
            "Content-Type": "application/json"
        }
        return self.test_endpoint("Waitlist API", url, "POST", data, headers)
    
    def test_drone_path_endpoint(self, base_url: str) -> Dict:
        """Test drone path endpoint"""
        url = f"{base_url}/drone-path"
        data = {
            "start_lat": 40.7128,
            "start_lon": -74.0060,
            "end_lat": 40.7589,
            "end_lon": -73.9851
        }
        headers = {
            "Content-Type": "application/json"
        }
        return self.test_endpoint("Drone Path API", url, "POST", data, headers)
    
    def test_file_upload_endpoint(self, base_url: str) -> Dict:
        """Test file upload endpoint (just check if it's accessible)"""
        url = f"{base_url}/upload"
        return self.test_endpoint("File Upload API", url, "OPTIONS")
    
    def test_projects_endpoint(self, base_url: str) -> Dict:
        """Test projects endpoint (requires auth, so just check CORS)"""
        url = f"{base_url}/projects"
        return self.test_endpoint("Projects API", url, "OPTIONS")
    
    def test_password_reset_endpoint(self, base_url: str) -> Dict:
        """Test password reset endpoint"""
        url = f"{base_url}/password-reset"
        return self.test_endpoint("Password Reset API", url, "OPTIONS")
    
    def test_invite_endpoint(self, base_url: str) -> Dict:
        """Test invite endpoint"""
        url = f"{base_url}/invite"
        return self.test_endpoint("Invite API", url, "OPTIONS")
    
    def test_beta_access_admin_endpoint(self, base_url: str) -> Dict:
        """Test beta access admin endpoint"""
        url = f"{base_url}/beta-access"
        return self.test_endpoint("Beta Access Admin API", url, "OPTIONS")
    
    def test_subscription_endpoint(self, base_url: str) -> Dict:
        """Test subscription endpoint"""
        url = f"{base_url}/subscription"
        return self.test_endpoint("Subscription API", url, "OPTIONS")

    def test_feedback_endpoint(self, base_url: str) -> Dict:
        """Test feedback endpoint (POST feedback message)"""
        url = f"{base_url}/feedback"
        data = {
            "message": "Automated feedback test submission.",
            "pageUrl": "https://staging.spaceport.ai/test-script"
        }
        headers = {
            "Content-Type": "application/json"
        }
        return self.test_endpoint("Feedback API", url, "POST", data, headers)
    
    def run_all_tests(self, environment: str = 'staging') -> List[Dict]:
        """Run all API tests for the specified environment"""
        print(f"🧪 Testing {environment.upper()} API Endpoints")
        print("=" * 50)
        
        if environment not in self.base_urls:
            print(f"❌ Unknown environment: {environment}")
            return []
        
        base_urls = self.base_urls[environment]
        results = []
        
        # Test each endpoint
        test_functions = [
            ('waitlist', self.test_waitlist_endpoint),
            ('drone_path', self.test_drone_path_endpoint),
            ('file_upload', self.test_file_upload_endpoint),
            ('projects', self.test_projects_endpoint),
            ('password_reset', self.test_password_reset_endpoint),
            ('invite', self.test_invite_endpoint),
            ('beta_access_admin', self.test_beta_access_admin_endpoint),
            ('subscription', self.test_subscription_endpoint),
            ('feedback', self.test_feedback_endpoint)
        ]
        
        for endpoint_name, test_func in test_functions:
            if endpoint_name in base_urls:
                print(f"\n🔍 Testing {endpoint_name.replace('_', ' ').title()}...")
                result = test_func(base_urls[endpoint_name])
                results.append(result)
                
                # Print result
                if result['success']:
                    print(f"   ✅ {result['response_code']} - {result['response_time']:.2f}s")
                else:
                    print(f"   ❌ {result['status']} - {result['error'] or result['response_code']}")
            else:
                print(f"⚠️  No URL found for {endpoint_name}")
        
        return results
    
    def generate_report(self, results: List[Dict]) -> str:
        """Generate a comprehensive test report"""
        report = []
        report.append("\n📊 API ENDPOINT TEST REPORT")
        report.append("=" * 50)
        
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r['success'])
        failed_tests = total_tests - successful_tests
        
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Successful: {successful_tests}")
        report.append(f"Failed: {failed_tests}")
        report.append(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        
        report.append("\n📋 DETAILED RESULTS:")
        report.append("-" * 30)
        
        for result in results:
            status_icon = "✅" if result['success'] else "❌"
            report.append(f"{status_icon} {result['name']}")
            report.append(f"   URL: {result['url']}")
            report.append(f"   Status: {result['status']}")
            if result['response_code']:
                report.append(f"   Response Code: {result['response_code']}")
            if result['response_time']:
                report.append(f"   Response Time: {result['response_time']:.2f}s")
            if result['error']:
                report.append(f"   Error: {result['error']}")
            report.append("")
        
        return "\n".join(report)
    
    def generate_github_secrets_update(self, results: List[Dict]) -> str:
        """Generate GitHub secrets update commands"""
        commands = []
        commands.append("\n🔧 GITHUB SECRETS UPDATE COMMANDS:")
        commands.append("=" * 40)
        commands.append("# Copy these commands to update your GitHub secrets")
        commands.append("")
        
        # Map endpoint names to GitHub secret names
        secret_mapping = {
            'waitlist': 'WAITLIST_API_URL_PREVIEW',
            'drone_path': 'DRONE_PATH_API_URL_PREVIEW',
            'file_upload': 'FILE_UPLOAD_API_URL_PREVIEW',
            'projects': 'PROJECTS_API_URL_PREVIEW',
            'password_reset': 'PASSWORD_RESET_API_URL_PREVIEW',
            'invite': 'INVITE_API_URL_PREVIEW',
            'beta_access_admin': 'BETA_ACCESS_API_URL_PREVIEW',
            'subscription': 'SUBSCRIPTION_API_URL_PREVIEW',
            'feedback': 'FEEDBACK_API_URL_PREVIEW'
        }
        
        for result in results:
            if result['success'] and result['name'] in secret_mapping:
                secret_name = secret_mapping[result['name']]
                url = result['url']
                commands.append(f"# {result['name']}")
                commands.append(f"gh secret set {secret_name} --body '{url}'")
                commands.append("")
        
        return "\n".join(commands)

def main():
    tester = APITester()
    
    # Test staging environment
    results = tester.run_all_tests('staging')
    
    # Generate and print report
    report = tester.generate_report(results)
    print(report)
    
    # Generate GitHub secrets update commands
    secrets_commands = tester.generate_github_secrets_update(results)
    print(secrets_commands)
    
    # Exit with error code if any tests failed
    failed_tests = sum(1 for r in results if not r['success'])
    if failed_tests > 0:
        print(f"\n⚠️  {failed_tests} tests failed. Check the report above.")
        sys.exit(1)
    else:
        print("\n🎉 All tests passed!")

if __name__ == "__main__":
    main()
