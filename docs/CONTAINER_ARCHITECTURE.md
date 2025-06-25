# 🏗️ Container Architecture & Maintenance Guide

> **CRITICAL FOR AI ASSISTANTS**: This document defines the FINAL, PRODUCTION-READY container architecture. DO NOT deviate from these patterns without explicit user approval.

## 📋 **Container Organization Principles**

### **GOLDEN RULE: One Dockerfile Per Container** ✅
Each container has EXACTLY ONE `Dockerfile` in its directory:
```
infrastructure/containers/
├── sfm/
│   └── Dockerfile                    # ✅ ONLY production Dockerfile
├── 3dgs/  
│   └── Dockerfile                    # ✅ ONLY production Dockerfile
└── compressor/
    └── Dockerfile                    # ✅ ONLY production Dockerfile
```

### **NEVER CREATE**: ❌
- `Dockerfile.test`, `Dockerfile.dev`, `Dockerfile.optimized`
- Multiple build scripts per container
- Experimental or duplicate container files
- Any files ending in `.backup`, `.old`, `.temp`

## 🚀 **Production Container Specifications**

### **SfM Container** (`infrastructure/containers/sfm/`) ✅ **OPERATIONAL**
- **Purpose**: Structure-from-Motion using COLMAP 3.11.1
- **Instance**: `ml.c6i.2xlarge` (8 vCPUs, 16 GB RAM)
- **Entry Point**: `run_colmap_production.sh`
- **ECR URI**: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:latest`
- **Expected Runtime**: 15-30 minutes for typical datasets
- **Recent Performance**: ✅ **12.5 minutes, 10 files, 52.55 MB output** (validated)

### **3DGS Container** (`infrastructure/containers/3dgs/`) ⚠️ **DEBUGGING REQUIRED**
- **Purpose**: 3D Gaussian Splatting training with optimization
- **Instance**: `ml.g4dn.xlarge` (4 vCPUs, 16 GB RAM, 1x NVIDIA T4 GPU)
- **Entry Point**: `train_gaussian_production.py`
- **Features**: Progressive resolution, PSNR plateau termination, early stopping
- **ECR URI**: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest`
- **Expected Runtime**: 1-2 hours for convergence (NOT 90 seconds)
- **Current Issue**: ⚠️ **Container built successfully but fails at SageMaker runtime**

### **Compressor Container** (`infrastructure/containers/compressor/`) ⏳ **AWAITING 3DGS**
- **Purpose**: SOGS-style Gaussian splat compression
- **Instance**: `ml.c6i.4xlarge` (16 vCPUs, 32 GB RAM)
- **Entry Point**: `compress.py` (NOT `compress_model.py`)
- **ECR URI**: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor:latest`
- **Expected Runtime**: 10-15 minutes for optimization
- **Status**: Container ready, testing dependent on 3DGS outputs

## 🔧 **Build Process (STANDARDIZED)**

### **GitHub Actions: PRIMARY BUILD METHOD** ✅ **OPERATIONAL**
**File**: `.github/workflows/build-containers.yml`
- **Status**: ✅ **Successfully completed** (10m 36s duration, Dec 2024)
- **Platform**: Proper linux/amd64 builds for SageMaker compatibility
- **Environment**: Ubuntu Linux runners (bypasses Mac Docker issues)
- **Automation**: ECR login, build, tag, and push
- **Triggers**: Manual dispatch or container file changes

### **Local Build Script**: `scripts/deployment/deploy.sh` (BACKUP ONLY)
```bash
# Build single container (if GitHub Actions unavailable)
./scripts/deployment/deploy.sh sfm
./scripts/deployment/deploy.sh 3dgs  
./scripts/deployment/deploy.sh compressor

# Build all containers
./scripts/deployment/deploy.sh all
```
**⚠️ WARNING**: Local builds may fail on Mac due to platform issues. Prefer GitHub Actions.

## 🚨 **CRITICAL MAINTENANCE RULES**

### **FOR AI ASSISTANTS - NEVER DO THIS**: ❌
1. **Create multiple Dockerfiles** in the same container directory
2. **Add experimental or test containers** without explicit approval
3. **Modify container entry points** without understanding the full pipeline
4. **Create "optimized" or "enhanced" versions** alongside production containers
5. **Use local Docker builds** on Mac (known to fail with platform issues)

### **ALWAYS DO THIS**: ✅
1. **Use the existing Dockerfile** in each container directory
2. **Test changes through GitHub Actions** for proper linux/amd64 builds
3. **Update this documentation** when making architectural changes
4. **Validate end-to-end pipeline** after container changes
5. **Maintain single source of truth** for each container's purpose

## 📊 **Container Validation Checklist**

Before considering containers "production ready":

### **Build Validation** ✅ **COMPLETED**
- [x] Single Dockerfile per container
- [x] Builds successfully with `--platform linux/amd64`
- [x] Pushes to ECR without errors
- [x] No duplicate or experimental files
- [x] GitHub Actions workflow operational

### **Runtime Validation** ⚠️ **IN PROGRESS**
- [x] SfM takes 15-30 minutes (validated: 12.5 minutes)
- [ ] 3DGS takes 1-2 hours (currently fails at runtime) 
- [ ] Compressor produces meaningful compression (pending 3DGS)
- [ ] End-to-end pipeline completes successfully

### **Integration Validation** ⚠️ **PENDING 3DGS FIX**
- [x] Step Functions workflow initiates correctly
- [ ] All three containers work together in sequence
- [ ] Output quality meets production standards
- [x] Error handling works correctly (SfM stage proven)

## 🔍 **TROUBLESHOOTING GUIDE**

### **Current Issue: 3DGS Container Runtime Failure** ⚠️

**Symptoms**:
- Container builds successfully via GitHub Actions
- Step Functions execution fails at 3DGS stage
- No output files produced in S3
- SfM stage completes successfully

**Investigation Steps**:
1. **Check CloudWatch Logs**:
   ```bash
   aws logs describe-log-groups --log-group-name-prefix "/aws/sagemaker/TrainingJobs"
   ```

2. **Verify Container Entry Point**:
   - Dockerfile CMD: Should point to `train_gaussian_production.py`
   - Script permissions: Must be executable
   - Dependencies: GPU libraries, Python packages

3. **Test Container Locally** (if possible):
   ```bash
   docker run --platform linux/amd64 \
     975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest \
     /opt/ml/code/train_gaussian_production.py --help
   ```

4. **Check SageMaker Environment**:
   - GPU access in ml.g4dn.xlarge instance
   - CUDA libraries compatibility
   - Python environment and packages

**Likely Root Causes**:
- Entry point script not executable or missing
- CUDA/GPU libraries not properly installed
- Python dependency conflicts
- Path issues in SageMaker environment

### **"Multiple Dockerfiles" Problem** ✅ **RESOLVED**
This issue was resolved during the major cleanup. If encountered again:
1. **STOP** - Do not create more
2. **Identify** which is the production version (usually just `Dockerfile`)
3. **Remove** all others
4. **Update** this documentation

### **"Container Build Fails" Problem**
**Symptoms**: Docker build errors, platform warnings, push failures

**Solutions**:
1. **Use GitHub Actions** instead of local builds
2. **Check platform specification** (`--platform linux/amd64`)
3. **Verify ECR permissions** and authentication
4. **Review build logs** in GitHub Actions interface

### **"Pipeline Takes Too Long/Short" Problem**
**SfM Performance** ✅ **VALIDATED**: 12.5 minutes (within 15-30 minute range)
**3DGS Performance** ⚠️ **UNKNOWN**: Container fails before timing can be measured
**Expected vs Actual**:
- SfM: 15-30 minutes → ✅ 12.5 minutes (good)
- 3DGS: 60-120 minutes → ❌ N/A (fails immediately)
- Compression: 10-15 minutes → ⏳ Pending 3DGS fix

### **Debug Commands for AI Assistants**

**Check recent Step Functions executions**:
```bash
aws stepfunctions list-executions --state-machine-arn "arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline" --max-results 5
```

**Get execution details for failed job**:
```bash
aws stepfunctions describe-execution --execution-arn "EXECUTION_ARN_HERE"
```

**List ECR repositories and latest images**:
```bash
aws ecr describe-repositories --query 'repositories[].repositoryName'
aws ecr describe-images --repository-name spaceport/3dgs --query 'imageDetails[0].imageTags'
```

**Check CloudWatch logs for SageMaker jobs**:
```bash
aws logs describe-log-groups --log-group-name-prefix "/aws/sagemaker"
```

## 🎯 **Current Status & Next Actions**

### **Completed** ✅
- [x] Container organization and cleanup
- [x] Standardized build process via GitHub Actions
- [x] All containers successfully built and pushed to ECR
- [x] SfM container validated with production workloads
- [x] Documentation updates reflecting current architecture

### **In Progress** ⚠️
- [ ] **DEBUG 3DGS CONTAINER**: Investigate runtime failure in SageMaker
- [ ] End-to-end pipeline validation (blocked by 3DGS)
- [ ] Performance benchmarking (partial - SfM complete)

### **Next Steps** ⏳
- [ ] Complete 3DGS debugging and fix
- [ ] Validate compression container
- [ ] Run full production pipeline test
- [ ] Performance optimization and scaling

## 🔄 **Maintenance Procedures**

### **Container Updates**
1. **Modify Dockerfile** in appropriate container directory
2. **Test locally** if possible (prefer GitHub Actions)
3. **Push changes** to trigger GitHub Actions build
4. **Validate** build completion in GitHub Actions interface
5. **Test** container in pipeline before declaring production-ready

### **Emergency Rollback**
1. **Check ECR** for previous image tags
2. **Update Step Functions** to use previous tag temporarily
3. **Fix container issue** and rebuild
4. **Switch back** to `:latest` tag

---

**Last Updated**: December 2024 - After successful GitHub Actions builds and 3DGS debugging initiation
**Current Focus**: Resolve 3DGS container runtime failure for complete pipeline validation
**Next Review**: After successful end-to-end pipeline execution ✅ 