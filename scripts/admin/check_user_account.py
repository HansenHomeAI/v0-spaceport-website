#!/usr/bin/env python3
"""
Check if a user exists in staging or production Cognito pools
"""

import boto3
import sys
from typing import List, Dict, Optional

# Known pool IDs from documentation
STAGING_POOLS = [
    "us-west-2_0dVDGIChG",    # Spaceport-Users (5 users)
    "us-west-2_a2jf3ldGV",    # Spaceport-Users-v2 (11 users) - MAIN STAGING
    "us-west-2_dfcyr31KZ",    # Spaceport-Users-staging (11 users)
    "us-west-2_OFfTa3OT9",    # Spaceport-Users-v3-staging (1 user)
    "us-west-2_WG2FqehDE",    # spaceport-crm-users (3 users)
    "us-west-2_oqa9D3eIn",    # Spaceport-Users-staging (1 user)
]

PRODUCTION_POOLS = [
    "us-west-2_SnOJuAJXa",    # From test_production_auth.py
]

REGION = 'us-west-2'

def find_user_in_pool(cognito_client, pool_id: str, email: str) -> Optional[Dict]:
    """Find a user by email in a specific pool"""
    try:
        paginator = cognito_client.get_paginator('list_users')
        for page in paginator.paginate(UserPoolId=pool_id):
            for user in page.get('Users', []):
                user_email = next(
                    (attr['Value'] for attr in user.get('Attributes', []) 
                     if attr['Name'] == 'email'),
                    None
                )
                if user_email and user_email.lower() == email.lower():
                    return {
                        'pool_id': pool_id,
                        'username': user.get('Username'),
                        'email': user_email,
                        'status': user.get('UserStatus'),
                        'enabled': user.get('Enabled'),
                        'created': user.get('UserCreateDate'),
                        'modified': user.get('UserLastModifiedDate'),
                    }
    except Exception as e:
        print(f"  ⚠️  Error checking pool {pool_id}: {e}")
    return None

def check_pools(profile: str, pool_ids: List[str], environment: str, email: str):
    """Check multiple pools in an environment"""
    print(f"\n{'='*60}")
    print(f"🔍 Checking {environment.upper()} environment")
    print(f"   Profile: {profile}")
    print(f"   Email: {email}")
    print(f"{'='*60}")
    
    try:
        session = boto3.Session(profile_name=profile)
        cognito_client = session.client('cognito-idp', region_name=REGION)
        
        found = False
        for pool_id in pool_ids:
            print(f"\n📋 Checking pool: {pool_id}")
            user = find_user_in_pool(cognito_client, pool_id, email)
            if user:
                found = True
                print(f"  ✅ FOUND!")
                print(f"     Username: {user['username']}")
                print(f"     Email: {user['email']}")
                print(f"     Status: {user['status']}")
                print(f"     Enabled: {user['enabled']}")
                print(f"     Created: {user['created']}")
                print(f"     Modified: {user['modified']}")
            else:
                print(f"  ❌ Not found in this pool")
        
        if not found:
            print(f"\n❌ User {email} not found in any {environment} pools")
        
        return found
        
    except Exception as e:
        print(f"❌ Error accessing {environment} environment: {e}")
        return False

def list_all_pools(profile: str, environment: str):
    """List all user pools in an environment"""
    print(f"\n📋 Listing all pools in {environment.upper()}...")
    try:
        session = boto3.Session(profile_name=profile)
        cognito_client = session.client('cognito-idp', region_name=REGION)
        
        response = cognito_client.list_user_pools(MaxResults=60)
        pools = response.get('UserPools', [])
        
        print(f"Found {len(pools)} pools:")
        for pool in pools:
            pool_id = pool['Id']
            pool_name = pool['Name']
            print(f"  - {pool_id}: {pool_name}")
        
        return [pool['Id'] for pool in pools]
        
    except Exception as e:
        print(f"❌ Error listing pools: {e}")
        return []

def main():
    if len(sys.argv) < 2:
        email = "hello@spcprt.com"
    else:
        email = sys.argv[1]
    
    print(f"🔍 Searching for user: {email}")
    print(f"   Region: {REGION}")
    
    # Check staging
    staging_profile = "spaceport-dev"  # Common profile name for staging
    staging_found = False
    
    # First, try to list all pools to get current state
    print("\n" + "="*60)
    print("📋 DISCOVERING POOLS...")
    print("="*60)
    
    staging_pools = []
    prod_pools = []
    
    try:
        staging_pools = list_all_pools(staging_profile, "staging")
    except:
        print(f"⚠️  Could not list staging pools with profile '{staging_profile}'")
        print(f"   Trying with known pool IDs...")
        staging_pools = STAGING_POOLS
    
    prod_profile = "spaceport-prod"
    try:
        prod_pools = list_all_pools(prod_profile, "production")
    except:
        print(f"⚠️  Could not list production pools with profile '{prod_profile}'")
        print(f"   Trying with known pool IDs...")
        prod_pools = PRODUCTION_POOLS
    
    # Check staging pools
    staging_found = check_pools(staging_profile, staging_pools, "STAGING", email)
    
    # Check production pools
    prod_found = check_pools(prod_profile, prod_pools, "PRODUCTION", email)
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"Staging: {'✅ FOUND' if staging_found else '❌ NOT FOUND'}")
    print(f"Production: {'✅ FOUND' if prod_found else '❌ NOT FOUND'}")
    
    if not staging_found and not prod_found:
        print(f"\n⚠️  User {email} was not found in any environment")
        sys.exit(1)
    else:
        print(f"\n✅ User {email} found in at least one environment")
        sys.exit(0)

if __name__ == "__main__":
    main()
