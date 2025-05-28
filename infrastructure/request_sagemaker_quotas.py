#!/usr/bin/env python3
"""
Script to request SageMaker service quota increases
"""
import boto3
import json

def request_sagemaker_quotas():
    """Request SageMaker service quota increases"""
    
    service_quotas = boto3.client('service-quotas', region_name='us-west-2')
    
    print("📝 Requesting SageMaker Service Quota Increases...")
    print("=" * 60)
    
    # Quotas we need to request
    quota_requests = [
        {
            'quota_code': 'L-1FFEBC8A',  # ml.c6i.4xlarge for SfM processing (COLMAP)
            'desired_value': 2,
            'description': 'ml.c6i.4xlarge for processing job usage (SfM/COLMAP)'
        },
        {
            'quota_code': 'L-09023B8C',  # ml.g4dn.xlarge for 3DGS training (GPU)
            'desired_value': 1,
            'description': 'ml.g4dn.xlarge for training job usage (3D Gaussian Splatting)'
        },
        {
            'quota_code': 'L-8B5D8F6E',  # ml.c6i.2xlarge for compression
            'desired_value': 1, 
            'description': 'ml.c6i.2xlarge for processing job usage (Model Compression)'
        },
        {
            'quota_code': 'L-2D1D8F6E',  # ml.c6i.8xlarge for heavy datasets (optional)
            'desired_value': 1,
            'description': 'ml.c6i.8xlarge for processing job usage (Heavy SfM workloads)'
        }
    ]
    
    for request in quota_requests:
        try:
            print(f"\n🔄 Requesting quota increase for {request['description']}...")
            
            # Check current quota first
            try:
                current_quota = service_quotas.get_service_quota(
                    ServiceCode='sagemaker',
                    QuotaCode=request['quota_code']
                )
                current_value = current_quota['Quota']['Value']
                print(f"   Current quota: {current_value}")
                
                if current_value >= request['desired_value']:
                    print(f"   ✅ Quota already sufficient ({current_value} >= {request['desired_value']})")
                    continue
                    
            except Exception as e:
                print(f"   ⚠️ Could not get current quota: {e}")
                current_value = 0
            
            # Request quota increase
            response = service_quotas.request_service_quota_increase(
                ServiceCode='sagemaker',
                QuotaCode=request['quota_code'],
                DesiredValue=request['desired_value']
            )
            
            case_id = response['RequestedQuota']['CaseId']
            status = response['RequestedQuota']['Status']
            
            print(f"   ✅ Quota increase requested!")
            print(f"   📋 Case ID: {case_id}")
            print(f"   📊 Status: {status}")
            print(f"   🎯 Requested Value: {request['desired_value']}")
            
        except Exception as e:
            if 'QuotaExceededException' in str(e):
                print(f"   ⚠️ Quota increase already pending for {request['description']}")
            elif 'InvalidParameterValueException' in str(e):
                print(f"   ❌ Invalid quota code: {request['quota_code']}")
            else:
                print(f"   ❌ Error requesting quota: {e}")
    
    print(f"\n📞 Note: Quota increases typically take 24-48 hours to process.")
    print(f"💡 You can check status in the AWS Service Quotas console.")
    print(f"🔗 https://console.aws.amazon.com/servicequotas/home/services/sagemaker/quotas")

def list_pending_requests():
    """List pending quota requests"""
    
    service_quotas = boto3.client('service-quotas', region_name='us-west-2')
    
    try:
        print("\n📋 Checking pending quota requests...")
        
        requests = service_quotas.list_requested_service_quota_change_history(
            ServiceCode='sagemaker'
        )
        
        pending_requests = [r for r in requests['RequestedQuotas'] 
                          if r['Status'] in ['PENDING', 'CASE_OPENED']]
        
        if pending_requests:
            print(f"   Found {len(pending_requests)} pending requests:")
            for req in pending_requests:
                print(f"   - {req['QuotaName']}: {req['DesiredValue']} (Status: {req['Status']})")
        else:
            print("   No pending requests found.")
            
    except Exception as e:
        print(f"   ❌ Error checking pending requests: {e}")

if __name__ == "__main__":
    request_sagemaker_quotas()
    list_pending_requests() 