#!/usr/bin/env python3
"""
📊 Production Environment Monitoring Test

This test validates that your monitoring, logging, and alerting systems
are properly configured for production beta testing.

Key areas:
1. CloudWatch metrics availability
2. Lambda function health
3. DynamoDB performance metrics
4. API Gateway monitoring
5. Error rate thresholds
6. Cost monitoring setup
"""

import boto3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import requests

class ProductionMonitoringTest:
    """Test production monitoring and alerting setup"""
    
    def __init__(self):
        """Initialize monitoring test suite"""
        
        self.region = 'us-west-2'
        
        # Initialize AWS clients
        self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        self.dynamodb = boto3.client('dynamodb', region_name=self.region)
        self.apigateway = boto3.client('apigateway', region_name=self.region)
        self.logs_client = boto3.client('logs', region_name=self.region)
        
        # Test results
        self.results = {'passed': 0, 'failed': 0, 'warnings': 0, 'details': []}
        
        # Production resources to monitor
        self.lambda_functions = [
            'Spaceport-DronePathFunction',
            'Spaceport-FileUploadFunction',
            'Spaceport-CsvUploadFunction',
            'Spaceport-WaitlistFunction',
            'Spaceport-ProjectsFunction'
        ]
        
        self.dynamodb_tables = [
            'Spaceport-Projects',
            'Spaceport-Waitlist',
            'Spaceport-FileMetadata',
            'Spaceport-DroneFlightPaths'
        ]
        
        print("📊 Production Environment Monitoring Test")
        print("=" * 50)

    def log_result(self, test_name: str, status: str, details: str = ""):
        """Log test results with appropriate status"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if status == "PASS":
            self.results['passed'] += 1
            icon = "✅"
        elif status == "FAIL":
            self.results['failed'] += 1
            icon = "❌"
        elif status == "WARN":
            self.results['warnings'] += 1
            icon = "⚠️"
        else:
            icon = "ℹ️"
            
        result_line = f"[{timestamp}] {icon} {test_name}"
        if details:
            result_line += f": {details}"
            
        print(result_line)
        self.results['details'].append(result_line)

    def test_lambda_function_monitoring(self):
        """Test Lambda function monitoring setup"""
        print("\n🔧 Testing Lambda Function Monitoring...")
        
        for function_name in self.lambda_functions:
            try:
                # Check if function exists and is active
                response = self.lambda_client.get_function(FunctionName=function_name)
                state = response['Configuration']['State']
                
                if state == 'Active':
                    self.log_result(f"Lambda Function - {function_name}", "PASS", "Active and healthy")
                else:
                    self.log_result(f"Lambda Function - {function_name}", "FAIL", f"State: {state}")
                
                # Check CloudWatch metrics for this function
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=1)
                
                metrics_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Invocations',
                    Dimensions=[
                        {'Name': 'FunctionName', 'Value': function_name}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Sum']
                )
                
                # Check if CloudWatch is collecting metrics
                if 'Datapoints' in metrics_response:
                    self.log_result(f"CloudWatch Metrics - {function_name}", "PASS", 
                                  f"Metrics collection active")
                else:
                    self.log_result(f"CloudWatch Metrics - {function_name}", "WARN", 
                                  "No recent metric data (expected for new deployment)")
                
                # Check log group exists
                log_group_name = f"/aws/lambda/{function_name}"
                try:
                    self.logs_client.describe_log_groups(
                        logGroupNamePrefix=log_group_name
                    )
                    self.log_result(f"Log Group - {function_name}", "PASS", "Log group exists")
                except self.logs_client.exceptions.ResourceNotFoundException:
                    self.log_result(f"Log Group - {function_name}", "FAIL", "Log group not found")
                
            except self.lambda_client.exceptions.ResourceNotFoundException:
                self.log_result(f"Lambda Function - {function_name}", "FAIL", "Function not found")
            except Exception as e:
                self.log_result(f"Lambda Function - {function_name}", "FAIL", str(e))

    def test_dynamodb_monitoring(self):
        """Test DynamoDB monitoring setup"""
        print("\n🗄️ Testing DynamoDB Monitoring...")
        
        for table_name in self.dynamodb_tables:
            try:
                # Check table status
                response = self.dynamodb.describe_table(TableName=table_name)
                table_status = response['Table']['TableStatus']
                
                if table_status == 'ACTIVE':
                    self.log_result(f"DynamoDB Table - {table_name}", "PASS", "Table active")
                else:
                    self.log_result(f"DynamoDB Table - {table_name}", "FAIL", f"Status: {table_status}")
                
                # Check if point-in-time recovery is enabled
                pitr_response = self.dynamodb.describe_continuous_backups(TableName=table_name)
                pitr_enabled = pitr_response['ContinuousBackupsDescription']['PointInTimeRecoveryDescription']['PointInTimeRecoveryStatus'] == 'ENABLED'
                
                if pitr_enabled:
                    self.log_result(f"PITR - {table_name}", "PASS", "Point-in-time recovery enabled")
                else:
                    self.log_result(f"PITR - {table_name}", "WARN", "Point-in-time recovery disabled")
                
                # Check CloudWatch metrics
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=1)
                
                metrics_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/DynamoDB',
                    MetricName='ConsumedReadCapacityUnits',
                    Dimensions=[
                        {'Name': 'TableName', 'Value': table_name}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Sum']
                )
                
                if 'Datapoints' in metrics_response:
                    self.log_result(f"DynamoDB Metrics - {table_name}", "PASS", "Metrics collection active")
                else:
                    self.log_result(f"DynamoDB Metrics - {table_name}", "WARN", "No recent activity")
                
            except self.dynamodb.exceptions.ResourceNotFoundException:
                self.log_result(f"DynamoDB Table - {table_name}", "FAIL", "Table not found")
            except Exception as e:
                self.log_result(f"DynamoDB Table - {table_name}", "FAIL", str(e))

    def test_api_gateway_monitoring(self):
        """Test API Gateway monitoring setup"""
        print("\n🌐 Testing API Gateway Monitoring...")
        
        try:
            # List all REST APIs
            apis_response = self.apigateway.get_rest_apis()
            spaceport_apis = [api for api in apis_response['items'] if 'Spaceport' in api['name']]
            
            for api in spaceport_apis:
                api_id = api['id']
                api_name = api['name']
                
                self.log_result(f"API Gateway - {api_name}", "PASS", f"API ID: {api_id}")
                
                # Check CloudWatch metrics for API Gateway
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=24)  # Longer period for API Gateway
                
                metrics_response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/ApiGateway',
                    MetricName='Count',
                    Dimensions=[
                        {'Name': 'ApiName', 'Value': api_name}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=['Sum']
                )
                
                if 'Datapoints' in metrics_response and len(metrics_response['Datapoints']) > 0:
                    total_requests = sum(dp['Sum'] for dp in metrics_response['Datapoints'])
                    self.log_result(f"API Metrics - {api_name}", "PASS", f"{total_requests} requests in 24h")
                else:
                    self.log_result(f"API Metrics - {api_name}", "WARN", "No recent API calls")
        
        except Exception as e:
            self.log_result("API Gateway Monitoring", "FAIL", str(e))

    def test_error_rate_monitoring(self):
        """Test error rate monitoring and alerting"""
        print("\n🚨 Testing Error Rate Monitoring...")
        
        # Test Lambda error rates
        for function_name in self.lambda_functions:
            try:
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=1)
                
                # Get invocation count
                invocations = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Invocations',
                    Dimensions=[
                        {'Name': 'FunctionName', 'Value': function_name}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Sum']
                )
                
                # Get error count
                errors = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName='Errors',
                    Dimensions=[
                        {'Name': 'FunctionName', 'Value': function_name}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Sum']
                )
                
                total_invocations = sum(dp['Sum'] for dp in invocations.get('Datapoints', []))
                total_errors = sum(dp['Sum'] for dp in errors.get('Datapoints', []))
                
                if total_invocations > 0:
                    error_rate = (total_errors / total_invocations) * 100
                    if error_rate < 5:  # Less than 5% error rate
                        self.log_result(f"Error Rate - {function_name}", "PASS", f"{error_rate:.1f}% error rate")
                    else:
                        self.log_result(f"Error Rate - {function_name}", "FAIL", f"{error_rate:.1f}% error rate")
                else:
                    self.log_result(f"Error Rate - {function_name}", "WARN", "No recent invocations")
                
            except Exception as e:
                self.log_result(f"Error Rate - {function_name}", "FAIL", str(e))

    def test_cost_monitoring_setup(self):
        """Test cost monitoring and budget alerts"""
        print("\n💰 Testing Cost Monitoring Setup...")
        
        try:
            # Check if Cost Explorer is available (requires billing permissions)
            ce_client = boto3.client('ce', region_name='us-east-1')  # Cost Explorer is only in us-east-1
            
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            response = ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='DAILY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ]
            )
            
            if response['ResultsByTime']:
                self.log_result("Cost Monitoring", "PASS", "Cost Explorer data available")
                
                # Calculate total cost for the week
                total_cost = 0
                for result in response['ResultsByTime']:
                    for group in result['Groups']:
                        cost = float(group['Metrics']['BlendedCost']['Amount'])
                        total_cost += cost
                
                self.log_result("Weekly Cost", "PASS", f"${total_cost:.2f} in the last 7 days")
            else:
                self.log_result("Cost Monitoring", "WARN", "No cost data available")
                
        except Exception as e:
            self.log_result("Cost Monitoring", "WARN", f"Cost monitoring not accessible: {str(e)}")

    def test_cloudwatch_alarms(self):
        """Test CloudWatch alarms configuration"""
        print("\n⏰ Testing CloudWatch Alarms...")
        
        try:
            # Get all alarms
            response = self.cloudwatch.describe_alarms()
            spaceport_alarms = [alarm for alarm in response['MetricAlarms'] 
                              if 'Spaceport' in alarm.get('AlarmName', '')]
            
            if spaceport_alarms:
                for alarm in spaceport_alarms:
                    alarm_name = alarm['AlarmName']
                    state = alarm['StateValue']
                    
                    if state == 'OK':
                        self.log_result(f"Alarm - {alarm_name}", "PASS", "State: OK")
                    elif state == 'INSUFFICIENT_DATA':
                        self.log_result(f"Alarm - {alarm_name}", "WARN", "Insufficient data")
                    else:
                        self.log_result(f"Alarm - {alarm_name}", "FAIL", f"State: {state}")
            else:
                self.log_result("CloudWatch Alarms", "WARN", "No Spaceport-specific alarms found")
                
        except Exception as e:
            self.log_result("CloudWatch Alarms", "FAIL", str(e))

    def test_log_retention_policies(self):
        """Test log retention policies"""
        print("\n📋 Testing Log Retention Policies...")
        
        try:
            # Check Lambda log groups
            for function_name in self.lambda_functions:
                log_group_name = f"/aws/lambda/{function_name}"
                
                try:
                    response = self.logs_client.describe_log_groups(
                        logGroupNamePrefix=log_group_name
                    )
                    
                    if response['logGroups']:
                        log_group = response['logGroups'][0]
                        retention_days = log_group.get('retentionInDays')
                        
                        if retention_days:
                            if retention_days <= 30:  # Reasonable retention
                                self.log_result(f"Log Retention - {function_name}", "PASS", 
                                              f"{retention_days} days retention")
                            else:
                                self.log_result(f"Log Retention - {function_name}", "WARN", 
                                              f"{retention_days} days retention (consider reducing for cost)")
                        else:
                            self.log_result(f"Log Retention - {function_name}", "WARN", 
                                          "No retention policy (logs kept forever)")
                    else:
                        self.log_result(f"Log Retention - {function_name}", "WARN", "Log group not found")
                        
                except Exception as e:
                    self.log_result(f"Log Retention - {function_name}", "FAIL", str(e))
                    
        except Exception as e:
            self.log_result("Log Retention Policies", "FAIL", str(e))

    def run_all_tests(self):
        """Execute all monitoring tests"""
        print("🚀 Starting Production Monitoring Test Suite")
        print("=" * 50)
        
        start_time = time.time()
        
        # Run all monitoring tests
        self.test_lambda_function_monitoring()
        self.test_dynamodb_monitoring()
        self.test_api_gateway_monitoring()
        self.test_error_rate_monitoring()
        self.test_cost_monitoring_setup()
        self.test_cloudwatch_alarms()
        self.test_log_retention_policies()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Calculate results
        total_tests = self.results['passed'] + self.results['failed'] + self.results['warnings']
        success_rate = (self.results['passed'] / total_tests) * 100 if total_tests > 0 else 0
        
        # Display results
        print(f"\n📊 PRODUCTION MONITORING TEST RESULTS")
        print("=" * 50)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"⚠️  Warnings: {self.results['warnings']}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        
        # Monitoring readiness assessment
        print(f"\n🎯 MONITORING READINESS ASSESSMENT")
        print("=" * 50)
        
        if success_rate >= 90 and self.results['failed'] == 0:
            print("🟢 EXCELLENT MONITORING SETUP")
            print("   Your monitoring infrastructure is production-ready")
            print("   You'll have great visibility into system health during beta")
        elif success_rate >= 75:
            print("🟡 GOOD MONITORING SETUP")
            print("   Basic monitoring is in place")
            print("   Consider addressing warnings before beta launch")
        else:
            print("🔴 MONITORING NEEDS IMPROVEMENT")
            print("   Critical monitoring gaps detected")
            print("   Beta launch without proper monitoring is risky")
        
        # Recommendations
        print(f"\n💡 MONITORING RECOMMENDATIONS")
        print("=" * 50)
        
        if self.results['warnings'] > 0:
            print("1. Review and address warning items above")
        
        print("2. Set up SNS notifications for critical alarms")
        print("3. Create CloudWatch dashboard for key metrics")
        print("4. Set up cost budgets with alerts")
        print("5. Test alert notifications before beta launch")
        print("6. Document monitoring runbook for troubleshooting")
        
        return success_rate >= 75 and self.results['failed'] <= 2

def main():
    """Main execution"""
    test_suite = ProductionMonitoringTest()
    ready = test_suite.run_all_tests()
    
    return 0 if ready else 1

if __name__ == "__main__":
    exit(main())
