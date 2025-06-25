# 🔧 3DGS Container Runtime Troubleshooting Guide

> **PURPOSE**: Comprehensive guide for debugging the current 3DGS container runtime failure issue

## 🎯 **Current Issue Summary**

**Status**: 3DGS container builds successfully via GitHub Actions but fails at SageMaker runtime
**Last Successful Build**: December 2024 via GitHub Actions (10m 36s)
**Failure Point**: SageMaker Training Job execution
**Impact**: Pipeline completes SfM successfully but fails at 3DGS stage

## 📊 **Evidence & Symptoms**

### **✅ What's Working**
- GitHub Actions container build completes successfully
- Container pushes to ECR without errors
- SfM processing stage works perfectly (12.5 minutes, 52.55 MB output)
- Step Functions workflow initiates and orchestrates correctly
- Infrastructure (ECR, SageMaker, S3) all operational

### **❌ What's Failing**
- 3DGS SageMaker Training Job fails with no output files
- Pipeline execution status: FAILED after ~12.5 minutes
- No .ply files generated in S3 output location
- CloudWatch logs need investigation for specific error details

### **🔍 Container Specifications**
- **ECR URI**: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest`
- **Entry Point**: `train_gaussian_production.py`
- **Instance Type**: `ml.g4dn.xlarge` (4 vCPUs, 16 GB RAM, 1x NVIDIA T4 GPU)
- **Expected Runtime**: 60-120 minutes (NOT failing immediately)

## 🔍 **Investigation Methodology**

### **Step 1: Container Analysis**
Check the actual container contents and entry point:

```bash
# Verify container entry point
aws ecr describe-images --repository-name spaceport/3dgs --query 'imageDetails[0]'

# Pull and inspect container locally (if Mac Docker allows)
docker pull 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest
docker run --platform linux/amd64 --entrypoint /bin/bash -it \
  975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest

# Inside container, check:
ls -la /opt/ml/code/
python3 /opt/ml/code/train_gaussian_production.py --help
```

### **Step 2: CloudWatch Log Analysis**
Find the specific SageMaker training job logs:

```bash
# List recent training jobs
aws sagemaker list-training-jobs --max-results 10 --sort-by CreationTime --sort-order Descending

# Get CloudWatch log group for the failed job
aws logs describe-log-groups --log-group-name-prefix "/aws/sagemaker/TrainingJobs"

# Download logs for specific job (replace JOB_NAME)
aws logs get-log-events --log-group-name "/aws/sagemaker/TrainingJobs/JOB_NAME" \
  --log-stream-name "JOB_NAME/algo-1-TIMESTAMP" --output text
```

### **Step 3: Step Functions Execution Details**
Get detailed execution information:

```bash
# Get the specific failed execution
aws stepfunctions describe-execution \
  --execution-arn "arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline:prod-validation-1750876231"

# Check execution history for detailed state transitions
aws stepfunctions get-execution-history \
  --execution-arn "arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline:prod-validation-1750876231"
```

## 🎯 **Likely Root Causes & Solutions**

### **1. Entry Point Script Issues**
**Symptoms**: Container fails immediately upon execution
**Causes**: 
- Script not executable (`chmod +x` missing)
- Incorrect shebang line
- Script path mismatch

**Investigation**:
```bash
# Check Dockerfile for proper entry point
cat infrastructure/containers/3dgs/Dockerfile | grep -E "(CMD|ENTRYPOINT|RUN chmod)"
```

**Fix**: Ensure Dockerfile has:
```dockerfile
RUN chmod +x /opt/ml/code/train_gaussian_production.py
CMD ["python3", "/opt/ml/code/train_gaussian_production.py"]
```

### **2. CUDA/GPU Library Issues**
**Symptoms**: Container starts but fails when accessing GPU
**Causes**:
- CUDA version mismatch
- PyTorch GPU support not installed
- NVIDIA drivers not available in container

**Investigation**:
```bash
# Check CUDA version in container
docker run --platform linux/amd64 \
  975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest \
  nvidia-smi

# Check PyTorch GPU support
docker run --platform linux/amd64 \
  975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest \
  python3 -c "import torch; print(torch.cuda.is_available())"
```

**Fix**: Update Dockerfile base image and CUDA installation:
```dockerfile
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04
# Install PyTorch with CUDA support
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### **3. Python Dependencies Issues**
**Symptoms**: Import errors, missing packages
**Causes**:
- Missing required packages
- Version conflicts
- Incorrect Python environment

**Investigation**:
```bash
# Check installed packages
docker run --platform linux/amd64 \
  975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest \
  pip list

# Test critical imports
docker run --platform linux/amd64 \
  975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest \
  python3 -c "import torch, gsplat, numpy"
```

**Fix**: Review and update requirements.txt:
```txt
torch>=2.0.0
gsplat
numpy
Pillow
tqdm
```

### **4. SageMaker Environment Issues**
**Symptoms**: Container works locally but fails in SageMaker
**Causes**:
- Hyperparameter passing issues
- Input/output path problems
- Resource allocation problems

**Investigation**: Check Step Functions state definition for proper parameter passing

**Fix**: Verify hyperparameters match script expectations

### **5. File Permissions/Path Issues**  
**Symptoms**: Permission denied errors, file not found
**Causes**:
- Incorrect file permissions
- Path mismatches between container and SageMaker
- Missing input files

**Investigation**:
```bash
# Check file structure in container
docker run --platform linux/amd64 \
  975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest \
  find /opt/ml -type f -name "*.py" -exec ls -la {} \;
```

## 🔧 **Debugging Workflow**

### **Phase 1: Quick Validation** (30 minutes)
1. **Check CloudWatch logs** for immediate error messages
2. **Verify container entry point** in Dockerfile
3. **Test basic container functionality** locally
4. **Check recent GitHub Actions build logs** for warnings

### **Phase 2: Deep Investigation** (1-2 hours)
1. **Full container inspection** - all dependencies, paths, permissions
2. **SageMaker training job analysis** - specific failure modes
3. **Step Functions parameter validation** - hyperparameter passing
4. **GPU/CUDA environment testing** - hardware compatibility

### **Phase 3: Fix Implementation** (1-3 hours)
1. **Implement identified fixes** in Dockerfile/scripts
2. **Rebuild container via GitHub Actions**
3. **Test with minimal dataset** first
4. **Full pipeline validation** once basic functionality confirmed

## 📋 **Debugging Checklist**

### **Container Build Validation**
- [ ] GitHub Actions build completed successfully
- [ ] No warnings or errors in build logs  
- [ ] Container pushed to ECR with latest tag
- [ ] Dockerfile follows linux/amd64 platform specification

### **Runtime Environment Validation**
- [ ] Entry point script exists and is executable
- [ ] Python dependencies installed correctly
- [ ] CUDA/GPU libraries available and compatible
- [ ] File permissions set correctly

### **SageMaker Integration Validation**
- [ ] Hyperparameters passed correctly from Step Functions
- [ ] Input/output paths configured properly
- [ ] Instance type (ml.g4dn.xlarge) has GPU access
- [ ] CloudWatch logging enabled and accessible

### **Production Readiness Validation**
- [ ] Container produces expected .ply output files
- [ ] Processing time within expected range (60-120 minutes)
- [ ] Error handling works correctly
- [ ] Integration with compression stage functional

## 🚨 **Emergency Procedures**

### **If Container Issue Blocks Production**
1. **Identify last working ECR tag** (if any)
2. **Temporarily update Step Functions** to use previous tag  
3. **Document current issue** for systematic debugging
4. **Fix container systematically** without time pressure

### **If Debugging Takes Too Long**
1. **Create minimal reproduction case** - simple test script
2. **Test each component individually** - avoid complex interactions
3. **Use known working components** as comparison baseline
4. **Seek additional expertise** if needed

---

**Created**: December 2024 - For current 3DGS container runtime failure  
**Status**: Investigation guide - to be updated as debugging progresses  
**Next Update**: After CloudWatch log analysis and specific error identification 