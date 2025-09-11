#!/bin/bash

# Delete Duplicate User Pools Script
# These pools are duplicates of users in the main staging pool

set -e

echo "🗑️  Deleting duplicate user pools..."

# Pools to delete (duplicates of main staging pool)
DUPLICATE_POOLS=(
    "us-west-2_dfcyr31KZ"   # Spaceport-Users-staging (11 users - duplicate)
    "us-west-2_0dVDGIChG"   # Spaceport-Users (5 users - legacy)
    "us-west-2_OFfTa3OT9"   # Spaceport-Users-v3-staging (1 user)
    "us-west-2_oqa9D3eIn"   # Spaceport-Users-staging (1 user)
)

echo "Pools to delete:"
for pool in "${DUPLICATE_POOLS[@]}"; do
    count=$(aws cognito-idp list-users --user-pool-id $pool --region us-west-2 --profile spaceport-dev --query 'length(Users)' --output text)
    echo "  $pool: $count users"
done

echo ""
echo "⚠️  WARNING: This will permanently delete these pools and their users!"
echo "   Users are backed up in main staging pool: us-west-2_a2jf3ldGV"
echo ""
read -p "Proceed with deletion? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Deleting duplicate pools..."
    
    for pool in "${DUPLICATE_POOLS[@]}"; do
        echo "Deleting pool: $pool"
        aws cognito-idp delete-user-pool \
            --user-pool-id $pool \
            --region us-west-2 \
            --profile spaceport-dev
        echo "✅ Deleted pool: $pool"
    done
    
    echo ""
    echo "✅ All duplicate pools deleted!"
    echo ""
    echo "📊 REMAINING POOLS:"
    echo "  us-west-2_a2jf3ldGV: 11 users (Spaceport-Users-v2) ← MAIN STAGING"
    echo "  us-west-2_WG2FqehDE: 3 users (spaceport-crm-users)"
else
    echo "❌ Deletion cancelled"
fi
