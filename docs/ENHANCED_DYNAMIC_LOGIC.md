# Enhanced Dynamic CDK Logic - Data-Aware Resource Management

## Overview

The enhanced dynamic logic builds upon the existing robust resource creation/import system by adding **data-aware decision making**. This ensures that valuable data is preserved during environment transitions and resource migrations.

## Enhanced Logic Flow

### **Updated Decision Matrix:**

1. **Preferred name exists + has data** → **Import it** ✅
2. **Preferred name exists + empty** → **Check fallback name**
3. **Fallback name exists + has data** → **Create preferred, migrate data, then import preferred** 🔄
4. **Fallback name exists + empty** → **Create preferred name**
5. **Neither exists** → **Create preferred name** 🆕

### **Key Enhancements:**

- **Data Detection**: Checks if resources contain actual data before making decisions
- **Automatic Migration**: Migrates data from fallback to preferred resources when needed
- **Comprehensive Logging**: Detailed progress tracking with emojis for visibility
- **Conservative Approach**: Treats errors as "no data" to avoid false positives

## Implementation Details

### **Data Detection Methods:**

```python
def _bucket_has_data(self, bucket_name: str) -> bool:
    """Check if S3 bucket contains any objects"""
    try:
        response = self.s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
        return 'Contents' in response and len(response['Contents']) > 0
    except Exception as e:
        print(f"⚠️  Error checking bucket data for {bucket_name}: {e}")
        return False  # Conservative approach

def _dynamodb_table_has_data(self, table_name: str) -> bool:
    """Check if DynamoDB table contains any data"""
    try:
        response = self.dynamodb_client.scan(
            TableName=table_name,
            Select='COUNT',
            Limit=1
        )
        return response['Count'] > 0
    except Exception as e:
        print(f"⚠️  Error checking table data for {table_name}: {e}")
        return False  # Conservative approach
```

### **Migration Methods:**

```python
def _migrate_dynamodb_data(self, source_table: str, target_table: str) -> bool:
    """Migrate data from source DynamoDB table to target table"""
    # Scans all items and writes in batches of 25
    # Provides progress updates during migration

def _migrate_s3_data(self, source_bucket: str, target_bucket: str) -> bool:
    """Migrate data from source S3 bucket to target bucket"""
    # Uses pagination to handle large buckets
    # Copies objects with progress tracking
```

## Usage Examples

### **Scenario 1: Staging Environment Setup**
```
✅ Importing existing S3 bucket with data: spaceport-uploads-staging
✅ Importing existing DynamoDB table with data: Spaceport-Waitlist-staging
```

### **Scenario 2: Production Migration**
```
🔄 Fallback table has data, creating preferred and migrating: Spaceport-Waitlist → Spaceport-Waitlist-prod
📊 Found 78 items to migrate
✅ Migrated batch 1/4
✅ Migrated batch 2/4
✅ Migrated batch 3/4
✅ Migrated batch 4/4
✅ Successfully migrated data to Spaceport-Waitlist-prod
```

### **Scenario 3: Empty Resources**
```
ℹ️  Preferred bucket exists but is empty: spaceport-ml-processing-staging
ℹ️  Fallback bucket exists but is empty: spaceport-ml-processing
🆕 Creating new S3 bucket: spaceport-ml-processing-staging
```

## Benefits

1. **Data Preservation**: No data loss during environment transitions
2. **Automatic Migration**: Seamless data copying when needed
3. **Clear Visibility**: Detailed logging shows exactly what's happening
4. **Conservative Safety**: Errors are handled gracefully
5. **Backward Compatibility**: Existing logic still works, just enhanced

## Deployment Impact

- **First Deployment**: May take longer if data migration is needed
- **Subsequent Deployments**: Same speed as before
- **Migration Frequency**: Only happens when transitioning from fallback to preferred resources
- **Data Size**: Optimized for small to medium datasets (no chunking needed)

## Error Handling

- **Migration Failures**: Resource is still created, migration can be retried
- **Permission Issues**: Logged as warnings, conservative fallback
- **Network Issues**: Retry logic built into AWS SDK calls
- **Data Corruption**: Source data remains untouched during migration

## Monitoring

The enhanced logic provides detailed console output during deployment:

- ✅ **Success indicators** for imports and migrations
- 🔄 **Progress tracking** for data migrations
- ⚠️ **Warning messages** for potential issues
- ℹ️ **Info messages** for empty resources
- 🆕 **Creation indicators** for new resources

This ensures complete visibility into the resource management process and helps with troubleshooting if needed.
