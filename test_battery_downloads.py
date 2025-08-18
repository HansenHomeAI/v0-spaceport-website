#!/usr/bin/env python3
"""
Rapid CLI testing for battery download Lambda performance
Tests the exact flow: Optimization -> Battery 1 -> Battery 2 -> Battery 3 -> Battery 4
"""

import json
import time
import boto3
import requests
from typing import Dict, Any

# Configuration
API_BASE = "https://7bidiow2t9.execute-api.us-west-2.amazonaws.com/prod"
TEST_PARAMS = {
    "batteryMinutes": 19,
    "batteries": 5,
    "center": "41.74253337851678, -111.78932496414215",
    "minHeight": 200,
    "maxHeight": 400
}

def test_optimization_endpoint():
    """Test the optimization endpoint first"""
    print("🚀 Testing optimization endpoint...")
    
    url = f"{API_BASE}/api/optimize-spiral"
    start_time = time.time()
    
    try:
        response = requests.post(url, json=TEST_PARAMS, timeout=60)
        elapsed = time.time() - start_time
        
        print(f"⏱️  Optimization took {elapsed:.2f}s")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Optimization successful: {json.dumps(data, indent=2)}")
            return data
        else:
            print(f"❌ Optimization failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Optimization error: {e}")
        return None

def test_battery_download(battery_num: int, optimized_params: Dict[str, Any]):
    """Test downloading a specific battery CSV"""
    print(f"🔋 Testing battery {battery_num} download...")
    
    url = f"{API_BASE}/api/csv/battery/{battery_num}"
    start_time = time.time()
    
    # Use the optimized_params but add the center coordinates
    request_data = optimized_params["optimized_params"].copy()
    request_data["center"] = TEST_PARAMS["center"]
    request_data["minHeight"] = TEST_PARAMS["minHeight"] 
    request_data["maxHeight"] = TEST_PARAMS["maxHeight"]
    
    try:
        response = requests.post(url, json=request_data, timeout=60)
        elapsed = time.time() - start_time
        
        print(f"⏱️  Battery {battery_num} took {elapsed:.2f}s")
        
        if response.status_code == 200:
            csv_content = response.text
            waypoint_count = len(csv_content.strip().split('\n')) - 1  # Subtract header
            print(f"✅ Battery {battery_num} success: {waypoint_count} waypoints")
            return True
        else:
            print(f"❌ Battery {battery_num} failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Battery {battery_num} error: {e}")
        return False

def test_lambda_logs(function_name: str):
    """Check recent Lambda logs for performance insights"""
    print("📊 Checking Lambda logs...")
    
    try:
        logs_client = boto3.client('logs', region_name='us-west-2')
        
        # Get logs from last 5 minutes
        end_time = int(time.time() * 1000)
        start_time = end_time - (5 * 60 * 1000)
        
        response = logs_client.filter_log_events(
            logGroupName=f'/aws/lambda/{function_name}',
            startTime=start_time,
            endTime=end_time
        )
        
        optimization_calls = 0
        elevation_calls = 0
        timeouts = 0
        
        for event in response['events']:
            message = event['message']
            if 'Optimizing for' in message:
                optimization_calls += 1
            elif 'elevation' in message.lower():
                elevation_calls += 1
            elif 'timeout' in message.lower():
                timeouts += 1
        
        print(f"📈 Log Analysis:")
        print(f"   - Optimization calls: {optimization_calls}")
        print(f"   - Elevation-related logs: {elevation_calls}")
        print(f"   - Timeouts: {timeouts}")
        
    except Exception as e:
        print(f"❌ Log analysis failed: {e}")

def main():
    """Run the complete battery download test sequence"""
    print("🧪 Starting Battery Download Performance Test")
    print("=" * 50)
    
    # Step 1: Test optimization
    optimized_params = test_optimization_endpoint()
    if not optimized_params:
        print("❌ Cannot proceed without optimization")
        return
    
    print("\n" + "=" * 50)
    
    # Step 2: Test all battery downloads in sequence
    battery_results = []
    for battery_num in [1, 2, 3, 4, 5]:
        success = test_battery_download(battery_num, optimized_params)
        battery_results.append((battery_num, success))
        time.sleep(1)  # Brief pause between downloads
    
    print("\n" + "=" * 50)
    
    # Step 3: Check Lambda logs
    test_lambda_logs('Spaceport-DronePathFunction')
    
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY:")
    
    successful_batteries = sum(1 for _, success in battery_results if success)
    print(f"✅ Successful batteries: {successful_batteries}/5")
    
    for battery_num, success in battery_results:
        status = "✅" if success else "❌"
        print(f"   {status} Battery {battery_num}")
    
    if successful_batteries == 5:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {5 - successful_batteries} batteries failed")

if __name__ == "__main__":
    main()
