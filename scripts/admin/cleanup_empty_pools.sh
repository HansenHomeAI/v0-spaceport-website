#!/bin/bash

# Cleanup Empty User Pools Script
# This script safely deletes empty user pools to prevent proliferation

set -e

echo "🧹 Starting cleanup of empty user pools..."

# Function to check if pool has users
check_pool_users() {
    local pool_id=$1
    local profile=$2
    local region=$3
    
    count=$(aws cognito-idp list-users \
        --user-pool-id "$pool_id" \
        --region "$region" \
        --profile "$profile" \
        --query 'length(Users)' \
        --output text 2>/dev/null || echo "0")
    
    echo "$count"
}

# Function to delete empty pool
delete_empty_pool() {
    local pool_id=$1
    local profile=$2
    local region=$3
    
    echo "🗑️  Deleting empty pool: $pool_id"
    aws cognito-idp delete-user-pool \
        --user-pool-id "$pool_id" \
        --region "$region" \
        --profile "$profile"
    echo "✅ Deleted pool: $pool_id"
}

# STAGING ACCOUNT CLEANUP
echo ""
echo "🔵 Cleaning up STAGING account (975050048887)..."

# Pools to KEEP (have users)
STAGING_KEEP_POOLS=(
    "us-west-2_0dVDGIChG"    # 5 users
    "us-west-2_a2jf3ldGV"   # 11 users - MAIN STAGING POOL
    "us-west-2_dfcyr31KZ"   # 11 users - DUPLICATE
    "us-west-2_OFfTa3OT9"    # 1 user
    "us-west-2_WG2FqehDE"   # 3 users
    "us-west-2_oqa9D3eIn"   # 1 user
)

# Pools to DELETE (empty)
STAGING_DELETE_POOLS=(
    "us-west-2_4gwqYU7GC"    # 0 users
    "us-west-2_ilUDwBxjJ"    # 0 users
    "us-west-2_rjAFUXlM2"    # 0 users
    "us-west-2_vKey14Q4x"    # 0 users - EXPECTED PROD POOL
    "us-west-2_vsNUylBC4"    # 0 users
    "us-west-2_z3uKF2o5l"   # 0 users
)

echo "Keeping staging pools with users:"
for pool in "${STAGING_KEEP_POOLS[@]}"; do
    count=$(check_pool_users "$pool" "spaceport-dev" "us-west-2")
    echo "  $pool: $count users"
done

echo ""
echo "Deleting empty staging pools:"
for pool in "${STAGING_DELETE_POOLS[@]}"; do
    count=$(check_pool_users "$pool" "spaceport-dev" "us-west-2")
    if [ "$count" -eq 0 ]; then
        echo "  $pool: $count users - DELETING"
        delete_empty_pool "$pool" "spaceport-dev" "us-west-2"
    else
        echo "  $pool: $count users - SKIPPING (has users)"
    fi
done

# PRODUCTION ACCOUNT CLEANUP
echo ""
echo "🔴 Cleaning up PRODUCTION account (356638455876)..."

# Check which production pool actually has users
echo "Checking production pools for users..."

PRODUCTION_POOLS=(
    "us-west-2_3Rx92caFz"
    "us-west-2_5yxjMGfbC"
    "us-west-2_8uJgvMEo2"
    "us-west-2_XG1pxvNzr"
    "us-west-2_XUCpFG4z5"
    "us-west-2_aGWexDowy"
    "us-west-2_cMqRZ68O1"
    "us-west-2_tEP8gS6lO"
)

PRODUCTION_KEEP_POOLS=()
PRODUCTION_DELETE_POOLS=()

for pool in "${PRODUCTION_POOLS[@]}"; do
    count=$(check_pool_users "$pool" "spaceport-prod" "us-west-2")
    echo "  $pool: $count users"
    
    if [ "$count" -gt 0 ]; then
        PRODUCTION_KEEP_POOLS+=("$pool")
        echo "    -> KEEPING (has users)"
    else
        PRODUCTION_DELETE_POOLS+=("$pool")
        echo "    -> DELETING (empty)"
    fi
done

echo ""
echo "Keeping production pools with users:"
for pool in "${PRODUCTION_KEEP_POOLS[@]}"; do
    count=$(check_pool_users "$pool" "spaceport-prod" "us-west-2")
    echo "  $pool: $count users"
done

echo ""
echo "Deleting empty production pools:"
for pool in "${PRODUCTION_DELETE_POOLS[@]}"; do
    count=$(check_pool_users "$pool" "spaceport-prod" "us-west-2")
    if [ "$count" -eq 0 ]; then
        echo "  $pool: $count users - DELETING"
        delete_empty_pool "$pool" "spaceport-prod" "us-west-2"
    else
        echo "  $pool: $count users - SKIPPING (has users)"
    fi
done

echo ""
echo "✅ Cleanup completed!"
echo ""
echo "📊 SUMMARY:"
echo "  Staging pools kept: ${#STAGING_KEEP_POOLS[@]}"
echo "  Staging pools deleted: ${#STAGING_DELETE_POOLS[@]}"
echo "  Production pools kept: ${#PRODUCTION_KEEP_POOLS[@]}"
echo "  Production pools deleted: ${#PRODUCTION_DELETE_POOLS[@]}"
echo ""
echo "🎯 TARGET STATE:"
echo "  Staging: us-west-2_a2jf3ldGV (11 users)"
echo "  Production: [IDENTIFY ACTUAL PRODUCTION POOL]"
