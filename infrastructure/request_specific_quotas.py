#!/usr/bin/env python3
"""
Script to request specific SageMaker quotas for c6i instances
"""
import boto3
import json

def request_quotas_via_support():
    """Request quotas through AWS Support since specific quota codes don't exist"""
    
    print("🎯 SageMaker Quota Request Guide")
    print("=" * 50)
    
    print("\n📋 **STEP 1: Request via AWS Service Quotas Console**")
    print("🔗 https://console.aws.amazon.com/servicequotas/home/services/sagemaker/quotas")
    
    print("\n📝 **Quotas to Request:**")
    quotas_needed = [
        {
            'instance': 'ml.c6i.4xlarge',
            'usage': 'processing job usage', 
            'requested': 2,
            'reason': 'SfM/COLMAP processing for 3D reconstruction pipeline'
        },
        {
            'instance': 'ml.c6i.2xlarge', 
            'usage': 'processing job usage',
            'requested': 1,
            'reason': 'Model compression for 3D Gaussian Splat optimization'
        },
        {
            'instance': 'ml.g4dn.xlarge',
            'usage': 'training job usage', 
            'requested': 1,
            'reason': '3D Gaussian Splatting neural rendering training (requires GPU)'
        }
    ]
    
    for i, quota in enumerate(quotas_needed, 1):
        print(f"\n   {i}. **{quota['instance']} for {quota['usage']}**")
        print(f"      Requested Limit: {quota['requested']} instances")
        print(f"      Business Justification: {quota['reason']}")
    
    print(f"\n📞 **STEP 2: If Service Quotas doesn't have the specific quota:**")
    print(f"   Create AWS Support Case:")
    print(f"   🔗 https://console.aws.amazon.com/support/home#/case/create")
    
    print(f"\n📋 **Support Case Template:**")
    print(f"   Subject: SageMaker Instance Quota Increase Request")
    print(f"   Service: Amazon SageMaker")
    print(f"   Category: Service Limit Increase")
    
    print(f"\n📝 **Case Description:**")
    case_description = """
Hello AWS Support,

I need to request quota increases for SageMaker instances for a production ML pipeline:

**Requested Quotas:**
1. ml.c6i.4xlarge for processing job usage: 2 instances
   - Use case: Structure from Motion (SfM) processing using COLMAP
   - Workload: CPU-intensive photogrammetry for 3D reconstruction

2. ml.c6i.2xlarge for processing job usage: 1 instance  
   - Use case: 3D model compression and optimization
   - Workload: Model post-processing for web delivery

3. ml.g4dn.xlarge for training job usage: 1 instance
   - Use case: 3D Gaussian Splatting neural rendering training
   - Workload: GPU-accelerated neural network training

**Business Context:**
- Production ML pipeline for drone photography to 3D model conversion
- Real estate and property visualization use case
- Expected processing volume: 10-20 jobs per day
- Region: us-west-2

**Current Status:**
All requested instance types currently have 0 quota limit.

Please approve these quota increases to enable our production workload.

Thank you!
"""
    
    print(case_description)
    
    print(f"\n⚡ **STEP 3: Temporary Workaround**")
    print(f"   While waiting for quota approval, we can use smaller instances:")
    print(f"   - ml.t3.medium (should have default quota)")
    print(f"   - ml.m5.large (may have default quota)")

def verify_ses_email():
    """Guide for verifying SES email"""
    
    print(f"\n📧 **SES Email Verification Fix**")
    print("=" * 40)
    
    print(f"\n🔗 **AWS SES Console:**")
    print(f"   https://console.aws.amazon.com/ses/home?region=us-west-2#/verified-identities")
    
    print(f"\n📝 **Steps to Fix:**")
    print(f"   1. Go to SES Console in us-west-2 region")
    print(f"   2. Click 'Create Identity'")
    print(f"   3. Choose 'Email address'")
    print(f"   4. Enter: noreply@hansenhome.ai")
    print(f"   5. Click 'Create Identity'")
    print(f"   6. Check email and click verification link")
    
    print(f"\n💡 **Alternative: Use your verified email**")
    print(f"   - Change notification sender to: gbhbyu@gmail.com")
    print(f"   - This email is likely already verified")

if __name__ == "__main__":
    request_quotas_via_support()
    verify_ses_email() 