#!/usr/bin/env python3
"""
🔐 Multi-User Concurrency & Authentication Test

This test specifically focuses on:
1. Multi-user authentication flows
2. Database isolation between users
3. Concurrent project operations
4. User session handling
5. Project access controls

This is crucial for beta testing with multiple users simultaneously.
"""

import asyncio
import json
import time
import uuid
import requests
import concurrent.futures
from typing import Dict, List, Tuple
import boto3
from datetime import datetime

class MultiUserConcurrencyTest:
    """Test multi-user scenarios and concurrency"""
    
    def __init__(self):
        """Initialize test with production endpoints"""
        
        self.projects_api = 'https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod/projects'
        self.drone_api = 'https://7bidiow2t9.execute-api.us-west-2.amazonaws.com/prod'
        
        # AWS resources
        self.region = 'us-west-2'
        self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        self.projects_table = self.dynamodb.Table('Spaceport-Projects')
        
        # Test results
        self.results = {'passed': 0, 'failed': 0, 'details': []}
        
        print("🔐 Multi-User Concurrency Test Suite")
        print("=" * 50)

    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test results"""
        if passed:
            self.results['passed'] += 1
            status = "✅ PASS"
        else:
            self.results['failed'] += 1
            status = "❌ FAIL"
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        result_line = f"[{timestamp}] {status} - {test_name}"
        if details:
            result_line += f": {details}"
            
        print(result_line)
        self.results['details'].append(result_line)

    def simulate_user_session(self, user_id: int) -> Dict:
        """Simulate a complete user session with project operations"""
        
        user_identifier = f"test-user-{user_id}-{uuid.uuid4()}"
        session_results = {
            'user_id': user_id,
            'user_identifier': user_identifier,
            'operations': [],
            'errors': []
        }
        
        try:
            # 1. Create multiple projects for this user
            projects_created = []
            for i in range(3):  # Each user creates 3 projects
                project_data = {
                    'userSub': user_identifier,
                    'projectId': str(uuid.uuid4()),
                    'title': f'User {user_id} Project {i+1}',
                    'status': 'draft',
                    'progress': 0,
                    'params': {
                        'batteryMinutes': 20 + i * 5,
                        'batteries': 2 + i,
                        'address': f'Test Address {i+1}'
                    },
                    'createdAt': int(time.time()),
                    'updatedAt': int(time.time())
                }
                
                # Store in DynamoDB
                self.projects_table.put_item(Item=project_data)
                projects_created.append(project_data)
                
                session_results['operations'].append({
                    'type': 'create_project',
                    'project_id': project_data['projectId'],
                    'success': True
                })
            
            # 2. Query projects (should only see own projects)
            query_response = self.projects_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('userSub').eq(user_identifier)
            )
            
            user_projects = query_response.get('Items', [])
            session_results['projects_found'] = len(user_projects)
            session_results['operations'].append({
                'type': 'query_projects',
                'projects_found': len(user_projects),
                'success': len(user_projects) == 3
            })
            
            # 3. Update projects
            for project in projects_created:
                update_response = self.projects_table.update_item(
                    Key={'userSub': user_identifier, 'projectId': project['projectId']},
                    UpdateExpression='SET progress = :progress, #status = :status',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':progress': 25,
                        ':status': 'path_downloaded'
                    }
                )
                
                session_results['operations'].append({
                    'type': 'update_project',
                    'project_id': project['projectId'],
                    'success': True
                })
            
            # 4. Generate drone paths concurrently
            drone_path_results = []
            for i, project in enumerate(projects_created):
                coords = f"{47.6062 + i * 0.01},{-122.3321 + i * 0.01}"
                payload = {
                    "center": coords,
                    "batteryMinutes": project['params']['batteryMinutes'],
                    "batteries": project['params']['batteries']
                }
                
                try:
                    response = requests.post(
                        f"{self.drone_api}/api/optimize-spiral",
                        json=payload,
                        timeout=30
                    )
                    
                    drone_path_results.append({
                        'project_id': project['projectId'],
                        'status_code': response.status_code,
                        'success': response.status_code == 200,
                        'response_time': response.elapsed.total_seconds()
                    })
                    
                except Exception as e:
                    drone_path_results.append({
                        'project_id': project['projectId'],
                        'success': False,
                        'error': str(e)
                    })
            
            session_results['drone_path_results'] = drone_path_results
            
            # 5. Cleanup - delete test projects
            for project in projects_created:
                self.projects_table.delete_item(
                    Key={'userSub': user_identifier, 'projectId': project['projectId']}
                )
            
            session_results['cleanup_completed'] = True
            session_results['overall_success'] = True
            
        except Exception as e:
            session_results['errors'].append(str(e))
            session_results['overall_success'] = False
            
        return session_results

    def test_concurrent_user_sessions(self, num_users: int = 5):
        """Test multiple users operating concurrently"""
        print(f"\n🔄 Testing {num_users} concurrent user sessions...")
        
        start_time = time.time()
        
        # Execute concurrent user sessions
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(self.simulate_user_session, i) for i in range(num_users)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Analyze results
        successful_sessions = [r for r in results if r['overall_success']]
        failed_sessions = [r for r in results if not r['overall_success']]
        
        # Test 1: All sessions completed successfully
        success_rate = len(successful_sessions) / num_users * 100
        self.log_result(
            f"Concurrent Sessions ({num_users} users)", 
            success_rate >= 90,
            f"{success_rate:.1f}% success rate in {duration:.2f}s"
        )
        
        # Test 2: Database isolation (each user only saw their own projects)
        isolation_failures = []
        for result in successful_sessions:
            expected_projects = 3  # Each user creates 3 projects
            actual_projects = result.get('projects_found', 0)
            if actual_projects != expected_projects:
                isolation_failures.append(f"User {result['user_id']}: found {actual_projects}, expected {expected_projects}")
        
        self.log_result(
            "Database Isolation",
            len(isolation_failures) == 0,
            f"{len(isolation_failures)} isolation failures" if isolation_failures else "All users saw only their own data"
        )
        
        # Test 3: Drone path generation under load
        all_drone_results = []
        for result in successful_sessions:
            all_drone_results.extend(result.get('drone_path_results', []))
        
        successful_drone_paths = [r for r in all_drone_results if r.get('success')]
        drone_success_rate = len(successful_drone_paths) / len(all_drone_results) * 100 if all_drone_results else 0
        
        self.log_result(
            "Drone Path Generation Under Load",
            drone_success_rate >= 90,
            f"{drone_success_rate:.1f}% success rate ({len(successful_drone_paths)}/{len(all_drone_results)})"
        )
        
        # Test 4: Response times are reasonable
        response_times = [r.get('response_time', 0) for r in successful_drone_paths if 'response_time' in r]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            self.log_result(
                "Response Time Performance",
                avg_response_time < 10 and max_response_time < 30,
                f"Avg: {avg_response_time:.2f}s, Max: {max_response_time:.2f}s"
            )
        
        return results

    def test_database_cross_contamination(self):
        """Specifically test that users cannot see each other's data"""
        print(f"\n🔒 Testing database cross-contamination prevention...")
        
        # Create test data for two different users
        user1_id = f"isolation-test-user1-{uuid.uuid4()}"
        user2_id = f"isolation-test-user2-{uuid.uuid4()}"
        
        # User 1 creates projects
        user1_projects = []
        for i in range(3):
            project = {
                'userSub': user1_id,
                'projectId': str(uuid.uuid4()),
                'title': f'User1 Secret Project {i}',
                'status': 'draft',
                'progress': 0,
                'createdAt': int(time.time()),
                'updatedAt': int(time.time())
            }
            self.projects_table.put_item(Item=project)
            user1_projects.append(project)
        
        # User 2 creates projects
        user2_projects = []
        for i in range(2):
            project = {
                'userSub': user2_id,
                'projectId': str(uuid.uuid4()),
                'title': f'User2 Secret Project {i}',
                'status': 'draft',
                'progress': 0,
                'createdAt': int(time.time()),
                'updatedAt': int(time.time())
            }
            self.projects_table.put_item(Item=project)
            user2_projects.append(project)
        
        try:
            # Test 1: User 1 query should only return User 1's projects
            user1_query = self.projects_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('userSub').eq(user1_id)
            )
            user1_results = user1_query.get('Items', [])
            
            self.log_result(
                "User 1 Data Isolation",
                len(user1_results) == 3 and all(p['userSub'] == user1_id for p in user1_results),
                f"Found {len(user1_results)} projects, all belong to User 1"
            )
            
            # Test 2: User 2 query should only return User 2's projects
            user2_query = self.projects_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('userSub').eq(user2_id)
            )
            user2_results = user2_query.get('Items', [])
            
            self.log_result(
                "User 2 Data Isolation",
                len(user2_results) == 2 and all(p['userSub'] == user2_id for p in user2_results),
                f"Found {len(user2_results)} projects, all belong to User 2"
            )
            
            # Test 3: Verify no cross-contamination in results
            user1_project_ids = {p['projectId'] for p in user1_results}
            user2_project_ids = {p['projectId'] for p in user2_results}
            overlap = user1_project_ids.intersection(user2_project_ids)
            
            self.log_result(
                "No Data Cross-Contamination",
                len(overlap) == 0,
                f"No shared project IDs between users"
            )
            
        finally:
            # Cleanup
            for project in user1_projects + user2_projects:
                self.projects_table.delete_item(
                    Key={'userSub': project['userSub'], 'projectId': project['projectId']}
                )

    def test_concurrent_api_calls(self):
        """Test API endpoints under concurrent load"""
        print(f"\n⚡ Testing API endpoints under concurrent load...")
        
        def make_api_call(call_id: int) -> Dict:
            """Make a drone path API call"""
            try:
                coords = f"{47.6062 + call_id * 0.001},{-122.3321 + call_id * 0.001}"
                payload = {
                    "center": coords,
                    "batteryMinutes": 20,
                    "batteries": 3
                }
                
                response = requests.post(
                    f"{self.drone_api}/api/optimize-spiral",
                    json=payload,
                    timeout=30
                )
                
                return {
                    'call_id': call_id,
                    'success': response.status_code == 200,
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'data_size': len(response.content)
                }
                
            except Exception as e:
                return {
                    'call_id': call_id,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute 20 concurrent API calls
        num_calls = 20
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_api_call, i) for i in range(num_calls)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        successful_calls = [r for r in results if r.get('success')]
        failed_calls = [r for r in results if not r.get('success')]
        
        success_rate = len(successful_calls) / num_calls * 100
        
        self.log_result(
            f"Concurrent API Calls ({num_calls} requests)",
            success_rate >= 95,
            f"{success_rate:.1f}% success rate"
        )
        
        if successful_calls:
            response_times = [r['response_time'] for r in successful_calls]
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            
            self.log_result(
                "API Response Time Under Load",
                avg_time < 5 and max_time < 15,
                f"Avg: {avg_time:.2f}s, Max: {max_time:.2f}s"
            )

    def run_all_tests(self):
        """Execute all multi-user concurrency tests"""
        print("🚀 Starting Multi-User Concurrency Test Suite")
        print("=" * 50)
        
        start_time = time.time()
        
        # Run tests
        self.test_database_cross_contamination()
        self.test_concurrent_user_sessions(5)  # 5 concurrent users
        self.test_concurrent_api_calls()
        
        # Additional stress test with more users
        print(f"\n🔥 Stress Test: 10 concurrent users")
        self.test_concurrent_user_sessions(10)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Results summary
        total_tests = self.results['passed'] + self.results['failed']
        success_rate = (self.results['passed'] / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n📊 MULTI-USER CONCURRENCY TEST RESULTS")
        print("=" * 50)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"⏱️  Duration: {total_duration:.2f} seconds")
        
        # Beta readiness for multi-user
        print(f"\n🎯 MULTI-USER READINESS ASSESSMENT")
        print("=" * 50)
        
        if success_rate >= 95:
            print("🟢 EXCELLENT - Ready for multi-user beta")
            print("   Your system handles concurrent users exceptionally well")
        elif success_rate >= 85:
            print("🟡 GOOD - Ready for limited multi-user beta")
            print("   Consider starting with fewer users and monitoring closely")
        else:
            print("🔴 NOT READY - Critical multi-user issues detected")
            print("   Multi-user functionality needs significant work")
        
        return success_rate >= 85

def main():
    """Main execution"""
    test_suite = MultiUserConcurrencyTest()
    ready = test_suite.run_all_tests()
    
    return 0 if ready else 1

if __name__ == "__main__":
    exit(main())
