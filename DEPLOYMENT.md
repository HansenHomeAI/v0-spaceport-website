# 🚀 Deployment Guide & Troubleshooting

Complete deployment guide for the Spaceport ML Pipeline with troubleshooting and maintenance information.

## 📋 Prerequisites

### Required Software
- **AWS CLI**: Configured with credentials for account `975050048887`
- **Docker**: Latest version, with BuildKit enabled
- **Node.js**: 18+ and npm
- **Python**: 3.9+ with pip
- **Git**: For repository management

### AWS Account Setup
- **Region**: `us-west-2` (all resources must be in this region)
- **Quotas**: Production quotas already approved for all required SageMaker instances
- **Permissions**: Ensure your AWS credentials have sufficient permissions for CDK deployment

## 🏗️ Infrastructure Deployment

### Step 1: Deploy AWS Infrastructure

```bash
# Clone repository
git clone <repository-url>
cd Spaceport-Website

# Navigate to CDK directory
cd infrastructure/spaceport_cdk

# Activate Python virtual environment
source venv/bin/activate

# Install dependencies (if not already done)
pip install -r requirements.txt

# Deploy all stacks
cdk deploy --all --require-approval never

# Note the outputs - you'll need the ECR repository URIs
```

**Expected CDK Outputs:**
```
SpaceportMLPipelineStack.SfMRepositoryUri = 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm
SpaceportMLPipelineStack.GaussianRepositoryUri = 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs
SpaceportMLPipelineStack.CompressorRepositoryUri = 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor
SpaceportMLPipelineStack.MLApiUrl = https://[api-id].execute-api.us-west-2.amazonaws.com/prod/
```

### Step 2: Build and Push ML Containers

```bash
# Navigate to containers directory
cd ../containers

# Login to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 975050048887.dkr.ecr.us-west-2.amazonaws.com

# Build all containers with correct platform
./scripts/build-all.sh

# Or build individually:
# SfM Container
cd sfm
docker build --platform linux/amd64 -t 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:latest -f Dockerfile.minimal .
docker push 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:latest

# 3DGS Container  
cd ../3dgs
docker build --platform linux/amd64 -t 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest -f Dockerfile.minimal .
docker push 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest

# Compression Container
cd ../compressor
docker build --platform linux/amd64 -t 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor:latest -f Dockerfile.minimal .
docker push 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor:latest
```

### Step 3: Frontend Deployment

```bash
# Navigate to project root
cd ../../

# Install frontend dependencies
npm install

# Build for production
npm run build

# Deploy to S3 (handled by CDK CloudFront distribution)
# The build files are automatically deployed via the SpaceportStack
```

## 🧪 Testing the Deployment

### API Test
```bash
# Test the ML pipeline API
curl -X POST https://[your-api-url]/prod/start-job \
  -H "Content-Type: application/json" \
  -d '{
    "s3Url": "s3://spaceport-uploads/test-images.zip",
    "email": "your-email@example.com",
    "pipelineStep": "sfm"
  }'
```

### Expected Response
```json
{
  "jobId": "uuid-job-id",
  "executionArn": "arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline:execution-uuid",
  "message": "ML processing job started successfully"
}
```

### Monitor Pipeline Execution
```bash
# Check Step Functions execution
aws stepfunctions describe-execution \
  --execution-arn "arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline:execution-[job-id]" \
  --region us-west-2

# Check SageMaker jobs
aws sagemaker list-processing-jobs --region us-west-2 --sort-by CreationTime --sort-order Descending --max-items 5
aws sagemaker list-training-jobs --region us-west-2 --sort-by CreationTime --sort-order Descending --max-items 5
```

## 🔧 Maintenance & Updates

### Updating ML Containers
```bash
# Make changes to container code
# Rebuild with platform flag
docker build --platform linux/amd64 -t 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/[container]:latest .

# Push to ECR
docker push 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/[container]:latest

# No CDK redeployment needed - SageMaker will pull latest image
```

### Updating Infrastructure
```bash
# Make changes to CDK code
cd infrastructure/spaceport_cdk

# Deploy changes
cdk deploy SpaceportMLPipelineStack --require-approval never
```

### Updating Frontend
```bash
# Make changes to React code
npm run build

# Deploy via CDK (if S3/CloudFront changes needed)
cd infrastructure/spaceport_cdk
cdk deploy SpaceportStack
```

## 🚨 Troubleshooting Guide

### Common Issues & Solutions

#### 1. Container Platform Mismatch
**Symptom**: SageMaker jobs fail with "no matching manifest for linux/amd64"
**Solution**: Always rebuild containers with `--platform linux/amd64`
```bash
docker build --platform linux/amd64 -t [image-name] .
```

#### 2. Job Naming Conflicts
**Symptom**: SageMaker jobs fail with "job with this name already exists"
**Solution**: Pipeline now uses unique names automatically:
- SfM: `{jobName}-sfm`
- 3DGS: `{jobName}-3dgs`  
- Compression: `{jobName}-compression`

#### 3. Container Script Errors
**Symptom**: Exit code 127 or "command not found"
**Solution**: Check container entrypoint in ML pipeline stack:
```python
"ContainerEntrypoint": ["python", "script_name.py"]  # Not shell script
```

#### 4. S3 Permission Errors
**Symptom**: Access denied when reading/writing S3
**Solution**: Verify SageMaker execution role has proper S3 permissions
```bash
# Check role policies in AWS Console or via CLI
aws iam list-attached-role-policies --role-name SpaceportMLPipelineStack-SageMakerExecutionRole
```

#### 5. Step Functions Timeout
**Symptom**: Step Functions execution times out
**Solution**: Check individual SageMaker job status and CloudWatch logs
```bash
# Check job details
aws sagemaker describe-processing-job --processing-job-name [job-name] --region us-west-2
aws sagemaker describe-training-job --training-job-name [job-name] --region us-west-2
```

### Debugging Resources

#### CloudWatch Log Groups
- `/aws/stepfunctions/SpaceportMLPipeline`
- `/aws/sagemaker/ProcessingJobs/[job-name]`
- `/aws/sagemaker/TrainingJobs/[job-name]`
- `/aws/lambda/[function-name]`

#### Useful AWS CLI Commands
```bash
# List recent SageMaker jobs
aws sagemaker list-processing-jobs --region us-west-2 --sort-by CreationTime --sort-order Descending --max-items 10
aws sagemaker list-training-jobs --region us-west-2 --sort-by CreationTime --sort-order Descending --max-items 10

# Check Step Functions executions
aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline --region us-west-2

# View CloudWatch logs
aws logs tail /aws/stepfunctions/SpaceportMLPipeline --follow --region us-west-2
```

## 📊 Performance Monitoring

### Key Metrics to Track
- **Step Function Success Rate**: Target >95%
- **SageMaker Job Duration**: 
  - SfM: ~30 seconds (test), ~30 minutes (production)
  - 3DGS: ~60 seconds (test), ~2 hours (production)
  - Compression: ~30 seconds (test), ~15 minutes (production)
- **API Gateway Latency**: <2 seconds for job initiation
- **Error Rate**: <5% across all components

### Cost Optimization
- **SageMaker Instance Usage**: Monitor actual vs allocated time
- **S3 Storage**: Implement lifecycle policies for temporary data
- **CloudWatch Logs**: Set retention periods appropriately
- **Lambda Duration**: Optimize function performance

## 🔄 Backup & Recovery

### Critical Data
- **CDK Code**: Version controlled in Git
- **Container Images**: Stored in ECR with versioning
- **User Uploads**: Stored in S3 with versioning enabled
- **ML Results**: Stored in S3 with cross-region replication (if configured)

### Recovery Procedures
1. **Infrastructure Recovery**: Redeploy via CDK from version control
2. **Container Recovery**: Rebuild and push from Dockerfiles
3. **Data Recovery**: Restore from S3 versioning or backups
4. **Configuration Recovery**: All configuration is code-based via CDK

## 📈 Scaling Considerations

### Current Quotas
- **ml.g4dn.xlarge**: 1 instance (can request increase if needed)
- **ml.c6i.2xlarge**: 1 instance (sufficient for current workload)
- **ml.c6i.4xlarge**: 2 instances (can handle parallel compression jobs)

### Scaling Triggers
- Increase quotas when concurrent job requests exceed current capacity
- Consider Spot instances for cost optimization on non-critical workloads
- Implement auto-scaling for Lambda functions handling high API traffic

---

**Emergency Contacts**: Check AWS Support for quota increases or infrastructure issues  
**Last Updated**: After successful end-to-end pipeline validation and compression fix 