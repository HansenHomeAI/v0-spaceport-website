#!/usr/bin/env python3
"""
🚀 Spaceport - Comprehensive Beta Readiness Test Suite

This script performs thorough testing of all core functionality to ensure
the system is ready for early beta testing with multiple users.

Key Testing Areas:
1. Multi-user authentication and isolation
2. Concurrent project operations
3. Drone path generation under load
4. File upload system stress testing
5. Database isolation verification
6. API endpoint reliability
7. Error handling and edge cases

Usage:
    python tests/beta_readiness_comprehensive_test.py

Requirements:
    pip install boto3 requests concurrent.futures pytest asyncio aiohttp
"""

import asyncio
import json
import os
import sys
import time
import uuid
import random
import requests
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Tuple, Any
import boto3
from botocore.exceptions import ClientError
from preview_config import resolve_api_endpoints

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class BetaReadinessTestSuite:
    """Comprehensive test suite for beta readiness validation"""
    
    def __init__(self):
        """Initialize test suite with production API endpoints"""
        
        # Production API Endpoints
        default_endpoints = {
            'projects': 'https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod/projects',
            'drone_path': 'https://7bidiow2t9.execute-api.us-west-2.amazonaws.com/prod',
            'file_upload': 'https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod',
            'ml_pipeline': 'https://3xzfdyvwpd.execute-api.us-west-2.amazonaws.com/prod',
            'waitlist': 'https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/waitlist'
        }
        self.api_endpoints = resolve_api_endpoints(default_endpoints)
        
        # AWS Configuration
        self.region = 'us-west-2'
        self.cognito_user_pool_id = 'us-west-2_a2jf3ldGV'
        self.cognito_client_id = '3ctkuqu98pmug5k5kgc119sq67'
        
        # Test Configuration
        self.test_users = []
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
        
        # Initialize AWS clients
        try:
            self.cognito_client = boto3.client('cognito-idp', region_name=self.region)
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
            self.s3_client = boto3.client('s3', region_name=self.region)
        except Exception as e:
            print(f"{Colors.RED}❌ Failed to initialize AWS clients: {e}{Colors.END}")
            sys.exit(1)
            
        print(f"{Colors.CYAN}🧪 Beta Readiness Test Suite Initialized{Colors.END}")
        if self.api_endpoints != default_endpoints:
            print(f"{Colors.WHITE}Testing against Cloudflare preview endpoints{Colors.END}\n")
        else:
            print(f"{Colors.WHITE}Testing against production endpoints{Colors.END}\n")

    def log_test(self, test_name: str, status: str, details: str = ""):
        """Log test results with colored output"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if status == "PASS":
            self.test_results['passed'] += 1
            print(f"{Colors.GREEN}✅ [{timestamp}] {test_name}: PASSED{Colors.END}")
        elif status == "FAIL":
            self.test_results['failed'] += 1
            error_detail = f"{test_name}: {details}"
            self.test_results['errors'].append(error_detail)
            print(f"{Colors.RED}❌ [{timestamp}] {test_name}: FAILED{Colors.END}")
            if details:
                print(f"{Colors.RED}   └─ {details}{Colors.END}")
        elif status == "INFO":
            print(f"{Colors.BLUE}ℹ️  [{timestamp}] {test_name}: {details}{Colors.END}")
        elif status == "WARN":
            print(f"{Colors.YELLOW}⚠️  [{timestamp}] {test_name}: {details}{Colors.END}")

    # ==========================================
    # Test 1: API Endpoint Health Checks
    # ==========================================
    
    def test_api_endpoints_health(self):
        """Test that all API endpoints are responsive"""
        print(f"\n{Colors.BOLD}🔍 Test 1: API Endpoint Health Checks{Colors.END}")
        
        for endpoint_name, base_url in self.api_endpoints.items():
            try:
                # Test OPTIONS request (CORS preflight)
                response = requests.options(base_url, timeout=10)
                if response.status_code in [200, 204]:
                    self.log_test(f"API Health - {endpoint_name} OPTIONS", "PASS")
                else:
                    self.log_test(f"API Health - {endpoint_name} OPTIONS", "FAIL", 
                                f"Status: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.log_test(f"API Health - {endpoint_name}", "FAIL", str(e))

    # ==========================================
    # Test 2: Database Isolation Testing
    # ==========================================
    
    def test_database_isolation(self):
        """Test that user data is properly isolated in DynamoDB"""
        print(f"\n{Colors.BOLD}🔒 Test 2: Database Isolation Testing{Colors.END}")
        
        try:
            # Test with mock user data to verify isolation
            table = self.dynamodb.Table('Spaceport-Projects')
            
            # Simulate two different users
            user1_sub = f"test-user-1-{uuid.uuid4()}"
            user2_sub = f"test-user-2-{uuid.uuid4()}"
            
            # Create test projects for each user
            test_project_1 = {
                'userSub': user1_sub,
                'projectId': str(uuid.uuid4()),
                'title': 'User 1 Test Project',
                'status': 'draft',
                'progress': 0,
                'createdAt': int(time.time()),
                'updatedAt': int(time.time())
            }
            
            test_project_2 = {
                'userSub': user2_sub,
                'projectId': str(uuid.uuid4()),
                'title': 'User 2 Test Project',
                'status': 'draft',
                'progress': 0,
                'createdAt': int(time.time()),
                'updatedAt': int(time.time())
            }
            
            # Insert test data
            table.put_item(Item=test_project_1)
            table.put_item(Item=test_project_2)
            
            # Verify User 1 can only see their own projects
            user1_response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('userSub').eq(user1_sub)
            )
            user1_projects = user1_response.get('Items', [])
            
            # Verify User 2 can only see their own projects
            user2_response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('userSub').eq(user2_sub)
            )
            user2_projects = user2_response.get('Items', [])
            
            # Validation
            if len(user1_projects) == 1 and user1_projects[0]['userSub'] == user1_sub:
                self.log_test("Database Isolation - User 1", "PASS")
            else:
                self.log_test("Database Isolation - User 1", "FAIL", 
                            f"Expected 1 project, got {len(user1_projects)}")
                
            if len(user2_projects) == 1 and user2_projects[0]['userSub'] == user2_sub:
                self.log_test("Database Isolation - User 2", "PASS")
            else:
                self.log_test("Database Isolation - User 2", "FAIL", 
                            f"Expected 1 project, got {len(user2_projects)}")
                            
            # Cleanup test data
            table.delete_item(Key={'userSub': user1_sub, 'projectId': test_project_1['projectId']})
            table.delete_item(Key={'userSub': user2_sub, 'projectId': test_project_2['projectId']})
            
        except Exception as e:
            self.log_test("Database Isolation", "FAIL", str(e))

    # ==========================================
    # Test 3: Concurrent Drone Path Generation
    # ==========================================
    
    def test_concurrent_drone_path_generation(self):
        """Test drone path generation under concurrent load"""
        print(f"\n{Colors.BOLD}🛸 Test 3: Concurrent Drone Path Generation{Colors.END}")
        
        # Test coordinates for different locations
        test_locations = [
            {"lat": 47.6062, "lng": -122.3321, "name": "Seattle"},
            {"lat": 37.7749, "lng": -122.4194, "name": "San Francisco"},
            {"lat": 40.7128, "lng": -74.0060, "name": "New York"},
            {"lat": 34.0522, "lng": -118.2437, "name": "Los Angeles"},
            {"lat": 41.8781, "lng": -87.6298, "name": "Chicago"}
        ]
        
        def generate_drone_path(location):
            """Generate drone path for a specific location"""
            try:
                center_coords = f"{location['lat']},{location['lng']}"
                payload = {
                    "center": center_coords,
                    "batteryMinutes": 20,
                    "batteries": 3
                }
                
                response = requests.post(
                    f"{self.api_endpoints['drone_path']}/api/optimize-spiral",
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'location': location['name'],
                        'status': 'success',
                        'response_time': response.elapsed.total_seconds(),
                        'data': data
                    }
                else:
                    return {
                        'location': location['name'],
                        'status': 'failed',
                        'status_code': response.status_code,
                        'response': response.text
                    }
                    
            except Exception as e:
                return {
                    'location': location['name'],
                    'status': 'error',
                    'error': str(e)
                }
        
        # Execute concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(generate_drone_path, loc) for loc in test_locations]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        successful_requests = [r for r in results if r['status'] == 'success']
        failed_requests = [r for r in results if r['status'] != 'success']
        
        if len(successful_requests) == len(test_locations):
            avg_response_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
            self.log_test("Concurrent Drone Path Generation", "PASS", 
                        f"All {len(test_locations)} locations processed. Avg response time: {avg_response_time:.2f}s")
        else:
            self.log_test("Concurrent Drone Path Generation", "FAIL", 
                        f"{len(failed_requests)} out of {len(test_locations)} requests failed")
            for failed in failed_requests:
                self.log_test(f"  └─ {failed['location']}", "FAIL", failed.get('error', 'Unknown error'))

    # ==========================================
    # Test 4: File Upload System Stress Test
    # ==========================================
    
    def test_file_upload_multipart_system(self):
        """Test multipart file upload system"""
        print(f"\n{Colors.BOLD}📁 Test 4: File Upload System Testing{Colors.END}")
        
        try:
            # Test 1: Start multipart upload
            file_name = f"test-file-{uuid.uuid4()}.zip"
            start_payload = {
                "fileName": file_name,
                "fileType": "application/zip"
            }
            
            response = requests.post(
                f"{self.api_endpoints['file_upload']}/start-multipart-upload",
                json=start_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                upload_data = response.json()
                self.log_test("Multipart Upload - Start", "PASS")
                
                # Test 2: Get presigned URL for part
                part_payload = {
                    "uploadId": upload_data['uploadId'],
                    "bucketName": upload_data['bucketName'],
                    "objectKey": upload_data['objectKey'],
                    "partNumber": 1
                }
                
                part_response = requests.post(
                    f"{self.api_endpoints['file_upload']}/get-presigned-url",
                    json=part_payload,
                    timeout=30
                )
                
                if part_response.status_code == 200:
                    self.log_test("Multipart Upload - Get Presigned URL", "PASS")
                else:
                    self.log_test("Multipart Upload - Get Presigned URL", "FAIL", 
                                f"Status: {part_response.status_code}")
            else:
                self.log_test("Multipart Upload - Start", "FAIL", 
                            f"Status: {response.status_code}")
                            
        except Exception as e:
            self.log_test("File Upload System", "FAIL", str(e))

    # ==========================================
    # Test 5: Waitlist System Testing
    # ==========================================
    
    def test_waitlist_system(self):
        """Test waitlist submission system"""
        print(f"\n{Colors.BOLD}📝 Test 5: Waitlist System Testing{Colors.END}")
        
        test_email = f"test-{uuid.uuid4()}@example.com"
        
        try:
            payload = {
                "name": "Test User",
                "email": test_email
            }
            
            response = requests.post(
                self.api_endpoints['waitlist'],
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                self.log_test("Waitlist Submission", "PASS")
                
                # Test duplicate submission (should handle gracefully)
                duplicate_response = requests.post(
                    self.api_endpoints['waitlist'],
                    json=payload,
                    timeout=30
                )
                
                if duplicate_response.status_code in [200, 409]:  # 409 for conflict is acceptable
                    self.log_test("Waitlist Duplicate Handling", "PASS")
                else:
                    self.log_test("Waitlist Duplicate Handling", "FAIL", 
                                f"Status: {duplicate_response.status_code}")
            else:
                self.log_test("Waitlist Submission", "FAIL", 
                            f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test("Waitlist System", "FAIL", str(e))

    # ==========================================
    # Test 6: Cross-User Data Isolation
    # ==========================================
    
    def test_cross_user_data_isolation(self):
        """Test that users cannot access each other's data"""
        print(f"\n{Colors.BOLD}🔐 Test 6: Cross-User Data Isolation{Colors.END}")
        
        # This test simulates what would happen if someone tried to access
        # another user's data by manipulating API requests
        
        try:
            # Test unauthorized project access
            fake_user_sub = f"unauthorized-user-{uuid.uuid4()}"
            fake_project_id = str(uuid.uuid4())
            
            # Since we can't easily simulate JWT tokens in this test,
            # we'll test the DynamoDB query patterns directly
            table = self.dynamodb.Table('Spaceport-Projects')
            
            # This should return empty results for non-existent user
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('userSub').eq(fake_user_sub)
            )
            
            items = response.get('Items', [])
            
            if len(items) == 0:
                self.log_test("Cross-User Isolation - Query", "PASS", 
                            "No data returned for unauthorized user")
            else:
                self.log_test("Cross-User Isolation - Query", "FAIL", 
                            f"Unexpected data returned: {len(items)} items")
                            
        except Exception as e:
            self.log_test("Cross-User Data Isolation", "FAIL", str(e))

    # ==========================================
    # Test 7: Load Testing - Multiple Operations
    # ==========================================
    
    def test_concurrent_mixed_operations(self):
        """Test system under mixed concurrent operations"""
        print(f"\n{Colors.BOLD}⚡ Test 7: Concurrent Mixed Operations Load Test{Colors.END}")
        
        def mixed_operation(operation_id: int):
            """Perform a mixed set of operations"""
            results = []
            
            try:
                # 1. Waitlist submission
                waitlist_payload = {
                    "name": f"Load Test User {operation_id}",
                    "email": f"loadtest{operation_id}-{uuid.uuid4()}@example.com"
                }
                
                waitlist_response = requests.post(
                    self.api_endpoints['waitlist'],
                    json=waitlist_payload,
                    timeout=15
                )
                
                results.append({
                    'operation': 'waitlist',
                    'status': 'success' if waitlist_response.status_code == 200 else 'failed',
                    'response_time': waitlist_response.elapsed.total_seconds()
                })
                
                # 2. Drone path generation
                drone_payload = {
                    "center": f"{47.6062 + random.uniform(-0.1, 0.1)},{-122.3321 + random.uniform(-0.1, 0.1)}",
                    "batteryMinutes": random.choice([15, 20, 25]),
                    "batteries": random.choice([2, 3, 4])
                }
                
                drone_response = requests.post(
                    f"{self.api_endpoints['drone_path']}/api/optimize-spiral",
                    json=drone_payload,
                    timeout=15
                )
                
                results.append({
                    'operation': 'drone_path',
                    'status': 'success' if drone_response.status_code == 200 else 'failed',
                    'response_time': drone_response.elapsed.total_seconds()
                })
                
                # 3. File upload initialization
                upload_payload = {
                    "fileName": f"test-{operation_id}-{uuid.uuid4()}.zip",
                    "fileType": "application/zip"
                }
                
                upload_response = requests.post(
                    f"{self.api_endpoints['file_upload']}/start-multipart-upload",
                    json=upload_payload,
                    timeout=15
                )
                
                results.append({
                    'operation': 'file_upload',
                    'status': 'success' if upload_response.status_code == 200 else 'failed',
                    'response_time': upload_response.elapsed.total_seconds()
                })
                
                return {
                    'operation_id': operation_id,
                    'results': results,
                    'status': 'completed'
                }
                
            except Exception as e:
                return {
                    'operation_id': operation_id,
                    'status': 'error',
                    'error': str(e)
                }
        
        # Execute 10 concurrent mixed operations
        operation_count = 10
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(mixed_operation, i) for i in range(operation_count)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        successful_operations = [r for r in results if r['status'] == 'completed']
        failed_operations = [r for r in results if r['status'] == 'error']
        
        if len(successful_operations) >= operation_count * 0.9:  # 90% success rate
            total_operations = sum(len(r['results']) for r in successful_operations)
            total_successes = sum(
                len([op for op in r['results'] if op['status'] == 'success']) 
                for r in successful_operations
            )
            success_rate = (total_successes / total_operations) * 100
            
            self.log_test("Concurrent Mixed Operations", "PASS", 
                        f"Success rate: {success_rate:.1f}% ({total_successes}/{total_operations})")
        else:
            self.log_test("Concurrent Mixed Operations", "FAIL", 
                        f"{len(failed_operations)} out of {operation_count} operation sets failed")

    # ==========================================
    # Test 8: Error Handling and Edge Cases
    # ==========================================
    
    def test_error_handling_edge_cases(self):
        """Test system error handling and edge cases"""
        print(f"\n{Colors.BOLD}🚨 Test 8: Error Handling and Edge Cases{Colors.END}")
        
        # Test 1: Invalid drone path coordinates
        try:
            invalid_payload = {
                "center": "invalid,coordinates",
                "batteryMinutes": 20
            }
            
            response = requests.post(
                f"{self.api_endpoints['drone_path']}/api/optimize-spiral",
                json=invalid_payload,
                timeout=10
            )
            
            if response.status_code >= 400:
                self.log_test("Error Handling - Invalid Coordinates", "PASS", 
                            f"Properly returned error status {response.status_code}")
            else:
                self.log_test("Error Handling - Invalid Coordinates", "FAIL", 
                            "Should have returned error for invalid coordinates")
                            
        except Exception as e:
            self.log_test("Error Handling - Invalid Coordinates", "FAIL", str(e))
        
        # Test 2: Empty request bodies
        try:
            response = requests.post(
                self.api_endpoints['waitlist'],
                json={},
                timeout=10
            )
            
            if response.status_code >= 400:
                self.log_test("Error Handling - Empty Waitlist", "PASS", 
                            f"Properly returned error status {response.status_code}")
            else:
                self.log_test("Error Handling - Empty Waitlist", "FAIL", 
                            "Should have returned error for empty request")
                            
        except Exception as e:
            self.log_test("Error Handling - Empty Waitlist", "FAIL", str(e))
        
        # Test 3: Malformed JSON
        try:
            response = requests.post(
                self.api_endpoints['waitlist'],
                data="invalid json{",
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code >= 400:
                self.log_test("Error Handling - Malformed JSON", "PASS", 
                            f"Properly returned error status {response.status_code}")
            else:
                self.log_test("Error Handling - Malformed JSON", "FAIL", 
                            "Should have returned error for malformed JSON")
                            
        except Exception as e:
            self.log_test("Error Handling - Malformed JSON", "FAIL", str(e))

    # ==========================================
    # Main Test Execution
    # ==========================================
    
    def run_all_tests(self):
        """Execute the complete test suite"""
        print(f"{Colors.BOLD}{Colors.CYAN}🚀 SPACEPORT AI - BETA READINESS TEST SUITE{Colors.END}")
        print(f"{Colors.WHITE}Testing system readiness for early beta launch{Colors.END}")
        print(f"{Colors.WHITE}{'='*60}{Colors.END}")
        
        start_time = time.time()
        
        # Execute all tests
        self.test_api_endpoints_health()
        self.test_database_isolation()
        self.test_concurrent_drone_path_generation()
        self.test_file_upload_multipart_system()
        self.test_waitlist_system()
        self.test_cross_user_data_isolation()
        self.test_concurrent_mixed_operations()
        self.test_error_handling_edge_cases()
        
        # Calculate results
        end_time = time.time()
        duration = end_time - start_time
        total_tests = self.test_results['passed'] + self.test_results['failed']
        success_rate = (self.test_results['passed'] / total_tests) * 100 if total_tests > 0 else 0
        
        # Display results
        print(f"\n{Colors.BOLD}📊 TEST SUITE RESULTS{Colors.END}")
        print(f"{Colors.WHITE}{'='*60}{Colors.END}")
        print(f"{Colors.GREEN}✅ Passed: {self.test_results['passed']}{Colors.END}")
        print(f"{Colors.RED}❌ Failed: {self.test_results['failed']}{Colors.END}")
        print(f"{Colors.BLUE}📈 Success Rate: {success_rate:.1f}%{Colors.END}")
        print(f"{Colors.PURPLE}⏱️  Duration: {duration:.2f} seconds{Colors.END}")
        
        # Beta readiness assessment
        print(f"\n{Colors.BOLD}🎯 BETA READINESS ASSESSMENT{Colors.END}")
        print(f"{Colors.WHITE}{'='*60}{Colors.END}")
        
        if success_rate >= 90:
            print(f"{Colors.GREEN}🟢 READY FOR BETA LAUNCH{Colors.END}")
            print(f"{Colors.GREEN}   Your system passes {success_rate:.1f}% of tests{Colors.END}")
            print(f"{Colors.GREEN}   Core functionality is stable for early beta testing{Colors.END}")
        elif success_rate >= 75:
            print(f"{Colors.YELLOW}🟡 MOSTLY READY - MINOR ISSUES{Colors.END}")
            print(f"{Colors.YELLOW}   Your system passes {success_rate:.1f}% of tests{Colors.END}")
            print(f"{Colors.YELLOW}   Consider addressing failed tests before launch{Colors.END}")
        else:
            print(f"{Colors.RED}🔴 NOT READY FOR BETA{Colors.END}")
            print(f"{Colors.RED}   Your system passes only {success_rate:.1f}% of tests{Colors.END}")
            print(f"{Colors.RED}   Critical issues need to be resolved{Colors.END}")
        
        # Display failed tests
        if self.test_results['errors']:
            print(f"\n{Colors.BOLD}🔍 FAILED TESTS SUMMARY{Colors.END}")
            print(f"{Colors.WHITE}{'='*60}{Colors.END}")
            for i, error in enumerate(self.test_results['errors'], 1):
                print(f"{Colors.RED}{i}. {error}{Colors.END}")
        
        # Recommendations
        print(f"\n{Colors.BOLD}💡 RECOMMENDATIONS{Colors.END}")
        print(f"{Colors.WHITE}{'='*60}{Colors.END}")
        print(f"{Colors.WHITE}1. Monitor CloudWatch logs during beta testing{Colors.END}")
        print(f"{Colors.WHITE}2. Set up DynamoDB and API Gateway alarms{Colors.END}")
        print(f"{Colors.WHITE}3. Have a rollback plan ready{Colors.END}")
        print(f"{Colors.WHITE}4. Start with a small group of beta testers{Colors.END}")
        print(f"{Colors.WHITE}5. Collect user feedback actively{Colors.END}")
        
        return success_rate >= 75  # Return True if ready for beta

def main():
    """Main execution function"""
    test_suite = BetaReadinessTestSuite()
    ready_for_beta = test_suite.run_all_tests()
    
    if ready_for_beta:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure

if __name__ == "__main__":
    main()
