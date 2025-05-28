#!/usr/bin/env python3
"""
Script to find SageMaker quota codes for specific instance types
"""
import boto3
import json

def find_quota_codes():
    """Find quota codes for specific instance types"""
    
    service_quotas = boto3.client('service-quotas', region_name='us-west-2')
    
    print("🔍 Finding SageMaker Quota Codes...")
    print("=" * 50)
    
    target_instances = [
        'ml.c6i.2xlarge',
        'ml.c6i.4xlarge', 
        'ml.c6i.8xlarge',
        'ml.g4dn.xlarge'
    ]
    
    try:
        # Get all SageMaker quotas
        quotas = service_quotas.list_service_quotas(ServiceCode='sagemaker')
        
        print("📋 All SageMaker Quotas containing our target instances:")
        print("-" * 60)
        
        found_quotas = {}
        
        for quota in quotas['Quotas']:
            quota_name = quota['QuotaName']
            quota_code = quota['QuotaCode']
            quota_value = quota['Value']
            
            # Check if any of our target instances are in the quota name
            for instance in target_instances:
                if instance in quota_name:
                    found_quotas[instance] = {
                        'name': quota_name,
                        'code': quota_code,
                        'value': quota_value
                    }
                    print(f"✅ {instance}:")
                    print(f"   Name: {quota_name}")
                    print(f"   Code: {quota_code}")
                    print(f"   Current Value: {quota_value}")
                    print()
        
        # Let's search for ALL processing and training job quotas
        print(f"\n🔍 ALL Processing Job Quotas:")
        print("-" * 40)
        processing_quotas = [q for q in quotas['Quotas'] if 'processing job' in q['QuotaName'].lower()]
        for quota in processing_quotas[:20]:  # Show first 20
            print(f"   {quota['QuotaName']} ({quota['QuotaCode']}): {quota['Value']}")
            
        print(f"\n🔍 ALL Training Job Quotas:")
        print("-" * 40)
        training_quotas = [q for q in quotas['Quotas'] if 'training job' in q['QuotaName'].lower()]
        for quota in training_quotas[:20]:  # Show first 20
            print(f"   {quota['QuotaName']} ({quota['QuotaCode']}): {quota['Value']}")
            
        # Check if there are any quotas with "usage" that might be general
        print(f"\n🔍 General Instance Usage Quotas:")
        print("-" * 40)
        usage_quotas = [q for q in quotas['Quotas'] if 'usage' in q['QuotaName'].lower() and ('c6i' in q['QuotaName'].lower() or 'g4dn' in q['QuotaName'].lower())]
        for quota in usage_quotas:
            print(f"   {quota['QuotaName']} ({quota['QuotaCode']}): {quota['Value']}")
            
        if not found_quotas:
            print("⚠️ No quotas found for target instances. They might:")
            print("   1. Have different quota codes")
            print("   2. Not be available in this region")
            print("   3. Have default unlimited quotas")
            
        # Let's also check what c6i quotas exist
        print(f"\n🔍 All quotas containing 'c6i':")
        c6i_quotas = [q for q in quotas['Quotas'] if 'c6i' in q['QuotaName'].lower()]
        for quota in c6i_quotas:
            print(f"   {quota['QuotaName']} ({quota['QuotaCode']}): {quota['Value']}")
            
        # And g4dn quotas
        print(f"\n🔍 All quotas containing 'g4dn':")
        g4dn_quotas = [q for q in quotas['Quotas'] if 'g4dn' in q['QuotaName'].lower()]
        for quota in g4dn_quotas:
            print(f"   {quota['QuotaName']} ({quota['QuotaCode']}): {quota['Value']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    find_quota_codes() 