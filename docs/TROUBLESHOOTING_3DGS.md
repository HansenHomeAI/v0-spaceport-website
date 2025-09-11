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

# Troubleshooting 3DGS ML Pipeline

## Common Issues and Solutions

### 1. GitHub Actions Workflow Parsing Failures

#### Issue: "This run likely failed because of a workflow file issue" (No jobs created)

**Symptoms:**
- Workflow fails immediately upon triggering
- No jobs are created or started
- Generic "workflow file issue" error message
- Workflow appears to fail before any execution begins

**Root Cause:**
Heredoc syntax (`<< 'EOF'`) within GitHub Actions `run: |` blocks can cause YAML parsing failures due to indentation requirements. Specifically:

```yaml
# ❌ PROBLEMATIC - EOF not at column 0
run: |
  cat > file.json << 'EOF'
  {
    "key": "value"
  }
  EOF  # This EOF must start at column 0, not indented
```

**Solution:**
Replace heredocs with echo-based file creation to avoid shell parsing issues:

```yaml
# ✅ SOLUTION - Use echo statements instead of heredocs
run: |
  echo '{' > file.json
  echo '  "key": "value"' >> file.json
  echo '}' >> file.json
```

**Files Affected:**
- `.github/workflows/build-containers.yml` - Fixed heredoc EOF alignment issues

**Verification:**
- Local YAML validation: `python -c "import yaml; yaml.safe_load(open('.github/workflows/build-containers.yml'))"`
- Ruby YAML parser: `ruby -e "require 'psych'; Psych.safe_load(File.read('.github/workflows/build-containers.yml'))"`

**Lessons Learned:**
1. **Heredoc Delimiters**: The closing delimiter (EOF) must start at column 0 relative to the script content, not indented
2. **YAML Parsing**: GitHub Actions validates YAML before execution; syntax errors prevent any jobs from starting
3. **Debugging Approach**: Use multiple YAML parsers (Python, Ruby) to identify specific syntax issues
4. **Alternative Solutions**: Echo-based file creation is more reliable than heredocs in complex YAML contexts

**Example Fix Applied:**
```yaml
# Before (problematic):
cat > trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "codebuild.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# After (working):
echo '{' > trust.json
echo '  "Version": "2012-10-17",' >> trust.json
echo '  "Statement": [' >> trust.json
echo '    {' >> trust.json
echo '      "Effect": "Allow",' >> trust.json
echo '      "Principal": {"Service": "codebuild.amazonaws.com"},' >> trust.json
echo '      "Action": "sts:AssumeRole"' >> trust.json
echo '    }' >> trust.json
echo '  ]' >> trust.json
echo '}' >> trust.json
```

### 2. AWS Credential Configuration Issues

#### Issue: "Credentials could not be loaded, please check your action inputs"

**Symptoms:**
- Workflow fails during AWS credential configuration step
- Error: "Could not load credentials from any providers"
- Workflow appears to start but fails at credential step

**Root Cause:**
Missing environment secrets in GitHub repository environments:
- `staging` environment missing `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- `production` environment missing `AWS_ROLE_TO_ASSUME`

**Solution:**
1. **For Staging Environment**: Use personal AWS access keys
   ```bash
   gh secret set AWS_ACCESS_KEY_ID --env staging
   gh secret set AWS_SECRET_ACCESS_KEY --env staging
   ```

2. **For Production Environment**: Use OIDC role assumption
   ```bash
   gh secret set AWS_ROLE_TO_ASSUME --env production
   ```

**Verification:**
```bash
# Check environment secrets
gh secret list --env staging
gh secret list --env production

# Verify environments exist
gh api repos/:owner/:repo/environments
```

### 3. CDK Bootstrap Trust Policy Issues

#### Issue: "Invalid principal in policy: arn:aws:iam::ACCOUNT:role/GithubActionsProdRole"

**Symptoms:**
- CDK deployment fails during bootstrap step
- Error about invalid principal in trust policy
- Cross-account role reference issues

**Root Cause:**
CDK bootstrap command referencing production role while deploying to staging account:
```bash
# ❌ PROBLEMATIC - References production role in staging account
cdk bootstrap --trust arn:aws:iam::$ACCOUNT:role/GithubActionsProdRole
```

**Solution:**
Conditional credential configuration based on branch:
```yaml
- name: Configure AWS credentials (production via OIDC)
  if: github.ref_name == 'main'
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_TO_ASSUME }}
    aws-region: us-west-2

- name: Configure AWS credentials (staging via access keys)
  if: github.ref_name != 'main'
  uses: aws-actions/configure-aws-credentials@v4
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: us-west-2
```

## Debugging Workflow Failures

### Step-by-Step Investigation Process

1. **Check Workflow Status**
   ```bash
   gh run list --limit 5 --json status,conclusion,workflowName,headBranch
   ```

2. **Examine Specific Run**
   ```bash
   gh run view <RUN_ID> --log
   ```

3. **Identify Failure Point**
   - No jobs created → YAML syntax issue
   - Credential failure → Missing environment secrets
   - Runtime failure → Code logic or AWS permission issue

4. **Validate YAML Locally**
   ```bash
   # Python
   python -c "import yaml; yaml.safe_load(open('.github/workflows/workflow.yml'))"
   
   # Ruby
   ruby -e "require 'psych'; Psych.safe_load(File.read('.github/workflows/workflow.yml'))"
   ```

5. **Check Environment Secrets**
   ```bash
   gh secret list --env <ENVIRONMENT_NAME>
   ```

## Prevention and Best Practices

1. **YAML Syntax**
   - Avoid complex heredocs in GitHub Actions
   - Use echo-based file creation for JSON/configuration files
   - Validate YAML locally before pushing

2. **Credential Management**
   - Separate environments for staging and production
   - Use OIDC for production (more secure)
   - Use access keys for staging (simpler setup)

3. **Testing**
   - Test workflow changes on development branch first
   - Use `workflow_dispatch` for manual testing
   - Monitor workflow runs immediately after changes

4. **Documentation**
   - Document all environment-specific configurations
   - Maintain troubleshooting guides for common issues
   - Record successful fixes and their root causes

---

**Last Updated**: 2025-08-21 - GitHub Actions Workflow Parsing Issues Resolved
**Status**: Production Ready ✅
**Next Steps**: Monitor workflow stability and document any new issues 