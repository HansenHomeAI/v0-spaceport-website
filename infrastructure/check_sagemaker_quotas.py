#!/usr/bin/env python3
"""
Script to check SageMaker service quotas
"""
import boto3
import json

def check_sagemaker_quotas():
    """Check SageMaker service quotas for processing jobs"""
    
    # Initialize clients
    service_quotas = boto3.client('service-quotas', region_name='us-west-2')
    sagemaker = boto3.client('sagemaker', region_name='us-west-2')
    
    print("🔍 Checking SageMaker Service Quotas...")
    print("=" * 50)
    
    # Common instance types for processing jobs
    instance_types = [
        'ml.c6i.2xlarge',
        'ml.c6i.4xlarge', 
        'ml.c6i.8xlarge',
        'ml.g4dn.xlarge',
        'ml.m5.large',
        'ml.m5.xlarge',
        'ml.c5.large',
        'ml.c5.xlarge',
        'ml.c5.2xlarge'
    ]
    
    try:
        # Get SageMaker service quotas
        quotas = service_quotas.list_service_quotas(ServiceCode='sagemaker')
        
        processing_quotas = {}
        training_quotas = {}
        
        for quota in quotas['Quotas']:
            quota_name = quota['QuotaName']
            quota_value = quota['Value']
            
            # Check for processing job quotas
            if 'processing job usage' in quota_name.lower():
                for instance_type in instance_types:
                    if instance_type in quota_name:
                        processing_quotas[instance_type] = quota_value
                        
            # Check for training job quotas  
            elif 'training job usage' in quota_name.lower():
                for instance_type in instance_types:
                    if instance_type in quota_name:
                        training_quotas[instance_type] = quota_value
        
        print("📊 Processing Job Quotas:")
        for instance_type in instance_types:
            quota = processing_quotas.get(instance_type, "Not found")
            print(f"  {instance_type}: {quota}")
            
        print("\n🏋️ Training Job Quotas:")
        for instance_type in instance_types:
            quota = training_quotas.get(instance_type, "Not found") 
            print(f"  {instance_type}: {quota}")
            
        # Check current usage
        print("\n📈 Current SageMaker Usage:")
        try:
            processing_jobs = sagemaker.list_processing_jobs(StatusEquals='InProgress')
            training_jobs = sagemaker.list_training_jobs(StatusEquals='InProgress')
            
            print(f"  Active Processing Jobs: {len(processing_jobs['ProcessingJobSummaries'])}")
            print(f"  Active Training Jobs: {len(training_jobs['TrainingJobSummaries'])}")
            
        except Exception as e:
            print(f"  Could not get current usage: {e}")
            
    except Exception as e:
        print(f"❌ Error checking quotas: {e}")
        print("\n💡 Trying alternative approach...")
        
        # Alternative: Check specific quotas we need
        quota_codes = [
            'L-1FFEBC8A',  # ml.m5.large for processing
            'L-09023B8C',  # ml.g4dn.xlarge for training
        ]
        
        for quota_code in quota_codes:
            try:
                quota = service_quotas.get_service_quota(
                    ServiceCode='sagemaker',
                    QuotaCode=quota_code
                )
                print(f"  {quota['Quota']['QuotaName']}: {quota['Quota']['Value']}")
            except Exception as e:
                print(f"  Could not get quota {quota_code}: {e}")

if __name__ == "__main__":
    check_sagemaker_quotas() 