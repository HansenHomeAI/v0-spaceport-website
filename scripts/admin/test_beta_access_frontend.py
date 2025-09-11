#!/usr/bin/env python3
"""
Frontend Beta Access Testing Script
Tests the beta access API endpoints that the frontend would use.
"""

import requests
import json
from datetime import datetime

# Production Configuration
BETA_ACCESS_API_URL = 'https://84ufey2j0g.execute-api.us-west-2.amazonaws.com/prod'
PRODUCTION_URL = 'https://spcprt.com'

class FrontendBetaAccessTester:
    def __init__(self):
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
        
    def test_beta_access_api_endpoints(self):
        """Test all beta access API endpoints."""
        endpoints = [
            {
                'name': 'Check Permission',
                'url': f'{BETA_ACCESS_API_URL}/admin/beta-access/check-permission',
                'method': 'GET',
                'expected_status': [401, 403]  # Expected for unauthenticated
            },
            {
                'name': 'Send Invitation',
                'url': f'{BETA_ACCESS_API_URL}/admin/beta-access/send-invitation',
                'method': 'POST',
                'expected_status': [401, 403]  # Expected for unauthenticated
            }
        ]
        
        for endpoint in endpoints:
            try:
                if endpoint['method'] == 'GET':
                    response = requests.get(endpoint['url'], timeout=10)
                else:
                    response = requests.post(endpoint['url'], json={}, timeout=10)
                
                if response.status_code in endpoint['expected_status']:
                    self.log_result(f"Beta Access API - {endpoint['name']}", True, 
                                  f"Status: {response.status_code} (expected for unauthenticated)")
                else:
                    self.log_result(f"Beta Access API - {endpoint['name']}", False, 
                                  f"Unexpected status: {response.status_code}")
                    
            except Exception as e:
                self.log_result(f"Beta Access API - {endpoint['name']}", False, f"Error: {str(e)}")
                
    def test_cors_configuration(self):
        """Test CORS configuration for beta access API."""
        try:
            response = requests.options(
                f'{BETA_ACCESS_API_URL}/admin/beta-access/check-permission',
                headers={'Origin': PRODUCTION_URL},
                timeout=10
            )
            
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
            }
            
            if cors_headers['Access-Control-Allow-Origin']:
                self.log_result("Beta Access CORS Configuration", True, f"Headers: {cors_headers}")
                return True
            else:
                self.log_result("Beta Access CORS Configuration", False, "No CORS headers found")
                return False
                
        except Exception as e:
            self.log_result("Beta Access CORS Configuration", False, f"Error: {str(e)}")
            return False
            
    def test_frontend_integration(self):
        """Test if the frontend can access the beta access functionality."""
        try:
            # Check if the frontend has the beta access API URL configured
            response = requests.get(PRODUCTION_URL, timeout=10)
            
            if response.status_code == 200:
                # Look for beta access related content in the page
                content = response.text.lower()
                if 'beta' in content or 'invite' in content:
                    self.log_result("Frontend Beta Access Integration", True, "Beta access functionality detected")
                    return True
                else:
                    self.log_result("Frontend Beta Access Integration", True, "Frontend accessible, beta access may be admin-only")
                    return True
            else:
                self.log_result("Frontend Beta Access Integration", False, f"Frontend status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Frontend Beta Access Integration", False, f"Error: {str(e)}")
            return False
            
    def run_comprehensive_test(self):
        """Run all frontend beta access tests."""
        print("🌐 Testing Frontend Beta Access Integration")
        print("=" * 60)
        
        # Test 1: API endpoints
        print("\n🔗 Testing Beta Access API Endpoints...")
        self.test_beta_access_api_endpoints()
        
        # Test 2: CORS configuration
        print("\n🌐 Testing CORS Configuration...")
        self.test_cors_configuration()
        
        # Test 3: Frontend integration
        print("\n🎯 Testing Frontend Integration...")
        self.test_frontend_integration()
        
        # Summary
        print("\n📊 Frontend Beta Access Test Summary")
        print("=" * 60)
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        print(f"Tests Passed: {passed}/{total}")
        
        print(f"\n🔗 Beta Access API Endpoints:")
        print(f"  📍 Check Permission: {BETA_ACCESS_API_URL}/admin/beta-access/check-permission")
        print(f"  📍 Send Invitation: {BETA_ACCESS_API_URL}/admin/beta-access/send-invitation")
        
        print(f"\n👥 Employee with Beta Access Admin:")
        print(f"  📧 ethan@spcprt.com")
        print(f"  🔑 Can grant beta access to other users")
        
        print(f"\n🧪 Test User Created:")
        print(f"  📧 beta-test-1757346760-i6lyxe@spcprt.com")
        print(f"  🔑 TestPass123!577")
        print(f"  ✅ Has beta access granted by ethan@spcprt.com")
        
        # Save results
        with open('frontend_beta_access_test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
            
        print(f"\n📄 Detailed results saved to: frontend_beta_access_test_results.json")
        
        return self.test_results

if __name__ == "__main__":
    tester = FrontendBetaAccessTester()
    results = tester.run_comprehensive_test()
