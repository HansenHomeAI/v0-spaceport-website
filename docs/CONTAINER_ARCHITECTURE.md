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

### **SfM Container** (`infrastructure/containers/sfm/`)
- **Purpose**: Structure-from-Motion using COLMAP 3.11.1
- **Instance**: `ml.c6i.2xlarge` (8 vCPUs, 16 GB RAM)
- **Entry Point**: `run_colmap_production.sh`
- **ECR URI**: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:latest`
- **Expected Runtime**: 15-30 minutes for typical datasets

### **3DGS Container** (`infrastructure/containers/3dgs/`)
- **Purpose**: 3D Gaussian Splatting training with optimization
- **Instance**: `ml.g4dn.xlarge` (4 vCPUs, 16 GB RAM, 1x NVIDIA T4 GPU)
- **Entry Point**: `train_gaussian_production.py`
- **Features**: Progressive resolution, PSNR plateau termination, early stopping
- **ECR URI**: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest`
- **Expected Runtime**: 1-2 hours for convergence (NOT 90 seconds)

### **Compressor Container** (`infrastructure/containers/compressor/`)
- **Purpose**: SOGS-style Gaussian splat compression
- **Instance**: `ml.c6i.4xlarge` (16 vCPUs, 32 GB RAM)
- **Entry Point**: `compress.py` (NOT `compress_model.py`)
- **ECR URI**: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor:latest`
- **Expected Runtime**: 10-15 minutes for optimization

## 🔧 **Build Process (STANDARDIZED)**

### **Single Build Script**: `scripts/deployment/deploy.sh`
```bash
# Build single container
./scripts/deployment/deploy.sh sfm
./scripts/deployment/deploy.sh 3dgs  
./scripts/deployment/deploy.sh compressor

# Build all containers
./scripts/deployment/deploy.sh all
```

### **Platform Specification**: MANDATORY
All containers MUST be built with `--platform linux/amd64` for SageMaker compatibility.

### **GitHub Actions**: Primary Build Method
- **File**: `.github/workflows/build-containers.yml`
- **Triggers**: Manual, or changes to container files
- **Environment**: Ubuntu Linux (bypasses Mac Docker issues)
- **Automatic**: ECR login, build, tag, and push

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

### **Build Validation** ✅
- [ ] Single Dockerfile per container
- [ ] Builds successfully with `--platform linux/amd64`
- [ ] Pushes to ECR without errors
- [ ] No duplicate or experimental files

### **Runtime Validation** ⚠️
- [ ] SfM takes 15-30 minutes (not 2-3 minutes)
- [ ] 3DGS takes 1-2 hours (not 90 seconds) 
- [ ] Compressor produces meaningful compression
- [ ] End-to-end pipeline completes successfully

### **Integration Validation** ⚠️
- [ ] Step Functions workflow succeeds
- [ ] All three containers work together
- [ ] Output quality meets production standards
- [ ] Error handling works correctly

## 🎯 **Current Status**

### **Completed** ✅
- Container organization and cleanup
- Standardized build process
- GitHub Actions automation
- Documentation updates

### **Next Steps** ⚠️
- End-to-end pipeline validation
- Performance benchmarking
- Production deployment testing

## 🔍 **Troubleshooting Common Issues**

### **"Multiple Dockerfiles" Problem**
If you see multiple Dockerfiles in a container directory:
1. **STOP** - Do not create more
2. **Identify** which is the production version
3. **Remove** all others
4. **Update** this documentation

### **"Container Build Fails" Problem**
1. **Use GitHub Actions** instead of local builds
2. **Check platform specification** (`--platform linux/amd64`)
3. **Verify ECR permissions** and authentication
4. **Review container logs** in GitHub Actions

### **"Pipeline Takes Too Long/Short" Problem**
1. **Check container entry points** (not using dummy/test scripts)
2. **Verify instance types** match specifications above
3. **Review CloudWatch logs** for actual execution details
4. **Validate input data** is being processed correctly

---

**Last Updated**: December 2024 - After major container cleanup and standardization
**Next Review**: After successful end-to-end pipeline validation 