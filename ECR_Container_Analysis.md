# ECR Container Analysis Report
*Analysis Date: January 2025*

## Executive Summary

Based on a comprehensive analysis of your codebase, infrastructure, and ML pipeline configuration, I've identified which containers are actively used in production vs. potentially redundant test/development containers that could be costing you money in ECR storage.

## 🎯 **PRODUCTION CONTAINERS** (Keep - Currently Used)

### Core ML Pipeline Containers (Used in Production)

1. **`spaceport/sfm:real-colmap-fixed-final`** ✅ **PRODUCTION ACTIVE**
   - **Used by**: Production Lambda (`start_ml_job/lambda_function.py` line 101)
   - **Purpose**: Structure-from-Motion processing using COLMAP 3.11.1
   - **Instance Type**: `ml.c6i.4xlarge` (changed from c6i.2xlarge)
   - **Status**: ✅ **KEEP - PRODUCTION CRITICAL**

2. **`spaceport/3dgs:latest`** ✅ **PRODUCTION ACTIVE**
   - **Used by**: Production Lambda (`start_ml_job/lambda_function.py` line 102)
   - **Purpose**: 3D Gaussian Splatting training
   - **Instance Type**: `ml.g4dn.xlarge` (GPU instance)
   - **Status**: ✅ **KEEP - PRODUCTION CRITICAL**

3. **`spaceport/compressor:latest`** ✅ **PRODUCTION ACTIVE**
   - **Used by**: Production Lambda (`start_ml_job/lambda_function.py` line 103)
   - **Purpose**: SOGS-style Gaussian splat compression
   - **Instance Type**: `ml.c6i.4xlarge`
   - **Status**: ✅ **KEEP - PRODUCTION CRITICAL**

## ⚠️ **POTENTIAL REDUNDANCIES** (Review for Deletion)

### Development/Test Tag Variants

1. **`spaceport/sfm:latest`** ⚠️ **POTENTIALLY REDUNDANT**
   - **Found in**: Test files, documentation
   - **Used by**: Tests only (not production Lambda)
   - **Issue**: Production uses `:real-colmap-fixed-final` tag, not `:latest`
   - **Recommendation**: ⚠️ **DELETE if different from production tag**

### Legacy Container Names

2. **`spaceport-ml-sogs-compressor:latest`** 🚨 **LIKELY REDUNDANT**
   - **Found in**: Old test files and documentation
   - **Current replacement**: `spaceport/compressor:latest`
   - **Status**: 🚨 **DELETE - Legacy naming convention**

3. **`spaceport-ml-sogs-compressor:simple`** 🚨 **TEST CONTAINER**
   - **Found in**: Test fallback scripts only
   - **Purpose**: Testing/development only
   - **Status**: 🚨 **DELETE - Test artifact**

4. **`sagemaker-unzip:latest`** ❓ **UNCLEAR STATUS**
   - **Found in**: Test files, referenced as "extractorImageUri"
   - **Purpose**: File extraction (possibly unused in current pipeline)
   - **Status**: ❓ **INVESTIGATE - May be unused**

### Timestamped Development Tags

5. **Container versions with timestamps** ⚠️ **DEVELOPMENT ARTIFACTS**
   - **Pattern**: `spaceport/*:YYYYMMDD-HHMMSS` format
   - **Created by**: Deployment script (`deploy.sh` line 67)
   - **Purpose**: Development/testing iterations
   - **Status**: ⚠️ **DELETE older than 30 days**

### Optimized Variants

6. **`spaceport/3dgs:optimized-v1`** (if exists) ❓ **UNCLEAR STATUS**
   - **Found in**: Production deployment script references
   - **May exist from**: `production_deploy.sh` container tagging
   - **Status**: ❓ **INVESTIGATE - May be duplicate of :latest**

## 🔍 **DISCREPANCIES FOUND**

### Critical Production vs Test Inconsistencies

1. **SfM Container Tag Mismatch**
   - **Production**: Uses `spaceport/sfm:real-colmap-fixed-final`
   - **Tests**: Use `spaceport/sfm:latest`
   - **Risk**: Tests may not match production behavior
   - **Action**: Verify if these are the same image

2. **Missing Container in Production**
   - **Tests reference**: `sagemaker-unzip:latest` as "extractorImageUri"
   - **Production**: No reference to extraction container
   - **Conclusion**: Likely unused in current pipeline

## 💰 **COST OPTIMIZATION RECOMMENDATIONS**

### Immediate Actions (High Impact)

1. **Delete Legacy Containers** 🚨
   ```bash
   # DELETE these if they exist:
   - spaceport-ml-sogs-compressor:*
   - sagemaker-unzip:latest (if unused)
   ```

2. **Review :latest vs Production Tags** ⚠️
   ```bash
   # Verify if these are duplicates:
   - spaceport/sfm:latest vs spaceport/sfm:real-colmap-fixed-final
   ```

3. **Clean Up Timestamped Tags** 📅
   ```bash
   # Delete development tags older than 30 days
   # Pattern: spaceport/*:YYYYMMDD-HHMMSS
   ```

### ECR Lifecycle Rules Verification

Your CDK stack includes lifecycle rules (10 image limit), but verify they're working:

```typescript
// From ml_pipeline_stack.py lines 57-61
lifecycle_rules=[
    ecr.LifecycleRule(
        max_image_count=10,
        rule_priority=1,
        description="Keep only 10 most recent images"
    )
]
```

## 📋 **VERIFICATION CHECKLIST**

### Before Deleting Any Container

- [ ] **Check actual ECR registry** to see what tags exist
- [ ] **Verify production Lambda** is using correct tags
- [ ] **Test pipeline** after any deletions
- [ ] **Confirm lifecycle rules** are active and working

### Commands to Check ECR (when you have access)

```bash
# List all repositories
aws ecr describe-repositories --region us-east-1

# List images in each repository
aws ecr describe-images --repository-name spaceport/sfm --region us-east-1
aws ecr describe-images --repository-name spaceport/3dgs --region us-east-1
aws ecr describe-images --repository-name spaceport/compressor --region us-east-1

# Check for legacy repositories
aws ecr describe-images --repository-name spaceport-ml-sogs-compressor --region us-east-1
aws ecr describe-images --repository-name sagemaker-unzip --region us-east-1
```

## 🎯 **FINAL RECOMMENDATIONS**

### Definite Keepers (Production Critical)
- `spaceport/sfm:real-colmap-fixed-final`
- `spaceport/3dgs:latest`
- `spaceport/compressor:latest`

### Likely Safe to Delete
- `spaceport-ml-sogs-compressor:*` (all tags)
- `sagemaker-unzip:latest` (if not used)
- Any timestamped development tags older than 30 days

### Investigate Further
- `spaceport/sfm:latest` (compare with production tag)
- Any `spaceport/3dgs:optimized-*` variants

## 💡 **COST SAVINGS ESTIMATE**

- **Legacy containers**: Could save $5-20/month
- **Old development tags**: Could save $10-50/month depending on count
- **Duplicate `:latest` tags**: Could save $5-15/month

**Total potential savings**: $20-85/month in ECR storage costs.

---

*This analysis is based on code inspection. Always verify with actual ECR registry contents before making deletions.*