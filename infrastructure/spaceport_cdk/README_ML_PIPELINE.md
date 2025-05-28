# Spaceport ML Pipeline - Complete Documentation

## 🎯 Project Overview

This is a **production-grade AWS CDK stack** that implements a **Gaussian Splatting ML pipeline** for processing drone photography into 3D models. The pipeline takes uploaded ZIP files containing drone photos and processes them through a multi-stage ML workflow to generate compressed 3D Gaussian Splat models.

### Business Context
- **Company**: Spaceport (drone photography service)
- **Use Case**: Convert drone photo collections into 3D models for real estate and property visualization
- **Input**: ZIP files containing drone photos uploaded to S3
- **Output**: Compressed 3D Gaussian Splat models delivered via email

## 🏗️ Architecture Overview

### High-Level Flow
```
Frontend (S3 URL Input) → API Gateway → Lambda → Step Functions → SageMaker Jobs → Email Notification
```

### Detailed Architecture
1. **Frontend Integration**: User inputs S3 URL and email on website
2. **API Gateway**: `/start-job` endpoint receives requests
3. **Lambda Trigger**: Validates S3 URL, starts Step Functions execution
4. **Step Functions Orchestration**: Coordinates three sequential SageMaker jobs
5. **SageMaker Processing**: Runs containerized ML workloads
6. **Email Notification**: Sends results to user via SES

### AWS Services Used
- **AWS CDK**: Infrastructure as Code
- **API Gateway**: REST API endpoint
- **Lambda**: Serverless functions for orchestration and notifications
- **Step Functions**: Workflow orchestration
- **SageMaker**: ML job execution (Processing Jobs + Training Jobs)
- **ECR**: Container registry for ML images
- **S3**: File storage and processing
- **SES**: Email notifications
- **CloudWatch**: Logging and monitoring
- **IAM**: Security and permissions

## 🔄 ML Pipeline Stages

### Stage 1: Structure from Motion (SfM) Processing
- **Container**: `spaceport/sfm` (COLMAP-based)
- **Input**: ZIP file with drone photos
- **Output**: 3D point cloud and camera poses
- **SageMaker**: Processing Job on `ml.c5.2xlarge`
- **Duration**: ~30-60 minutes

### Stage 2: 3D Gaussian Splatting Training
- **Container**: `spaceport/3dgs` (Custom 3DGS implementation)
- **Input**: SfM output (point cloud + poses)
- **Output**: 3D Gaussian Splat model
- **SageMaker**: Training Job on `ml.g4dn.xlarge` (GPU)
- **Duration**: ~2-6 hours

### Stage 3: Model Compression
- **Container**: `spaceport/compressor` (Model optimization)
- **Input**: Raw 3DGS model
- **Output**: Compressed, web-optimized model
- **SageMaker**: Processing Job on `ml.c5.xlarge`
- **Duration**: ~15-30 minutes

## 📁 Project Structure

```
infrastructure/
├── spaceport_cdk/
│   ├── app.py                          # CDK app entry point
│   ├── cdk.json                        # CDK configuration
│   ├── requirements.txt                # Python dependencies
│   ├── spaceport_cdk/
│   │   ├── ml_pipeline_stack.py        # Main ML pipeline CDK stack
│   │   └── spaceport_stack.py          # Original website stack
│   └── lambda/
│       ├── start_ml_job/               # API trigger Lambda
│       │   └── lambda_function.py
│       └── ml_notification/            # Email notification Lambda
│           └── lambda_function.py
├── containers/
│   ├── sfm/                           # COLMAP SfM container
│   │   ├── Dockerfile
│   │   ├── process_sfm.py
│   │   └── run_sfm_fast.sh
│   ├── 3dgs/                          # 3D Gaussian Splatting container
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── train_gaussian.py
│   ├── compressor/                    # Model compression container
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── compress_model.py
│   └── scripts/
│       ├── build-all.sh               # Build all containers
│       └── build-single.sh            # Build individual container
└── README_ML_PIPELINE.md              # This documentation
```

## 🚀 Deployment Status

### Current State: **PRODUCTION READY** ✅

**Last Updated**: May 28, 2025

### Deployed Infrastructure
- **CDK Stacks**: Both `SpaceportStack` and `SpaceportMLPipelineStack` deployed
- **API Endpoint**: `https://3xzfdyvwpd.execute-api.us-west-2.amazonaws.com/prod/start-job`
- **Step Function**: `arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline`
- **S3 Buckets**: 
  - `spaceport-uploads` (existing)
  - `spaceport-ml-processing` (new)

### Container Images Status
All containers built and pushed to ECR:
- ✅ **SfM**: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:latest`
- ✅ **3DGS**: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest`
- ✅ **Compressor**: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor:latest`

### Frontend Integration
- **URL Validation**: Accepts both `s3://bucket/key` and `https://bucket.s3.amazonaws.com/key` formats
- **API Integration**: Connected to deployed API Gateway endpoint
- **User Experience**: S3 URL input + email → processing status → email notification

## 🔧 Technical Implementation Details

### S3 URL Validation Strategy
**Problem Solved**: Frontend initially only accepted HTTPS S3 URLs, but users were copying `s3://` protocol URLs from AWS console.

**Solution**: Updated both frontend JavaScript and backend Lambda to accept multiple formats:
- `s3://bucket-name/file.zip`
- `https://bucket-name.s3.amazonaws.com/file.zip`
- `https://s3.amazonaws.com/bucket-name/file.zip`

### SageMaker Configuration
**Critical Fix Applied**: Added missing `S3UploadMode: "EndOfJob"` to processing job configurations.

**Why This Matters**: SageMaker requires this field for S3 output configuration. Without it, jobs fail with validation errors.

### Container Build Strategy
**Approach**: Multi-stage Docker builds with platform-specific optimizations
- **SfM**: Based on `colmap/colmap` for photogrammetry
- **3DGS**: Ubuntu 20.04 base with custom ML dependencies
- **Compressor**: Python 3.9 slim for model optimization

**Build Process**:
```bash
# Build all containers
./infrastructure/containers/scripts/build-all.sh --push

# Build individual container
./infrastructure/containers/scripts/build-single.sh sfm --push
```

### Error Handling & Monitoring
- **CloudWatch Alarms**: Automatic alerts on Step Function failures
- **Email Notifications**: Success/failure notifications with detailed status
- **Comprehensive Logging**: All components log to CloudWatch
- **Retry Logic**: Built into Step Functions for transient failures

## 🐛 Known Issues & Solutions

### Issue 1: SageMaker S3UploadMode Missing (RESOLVED)
**Symptom**: Step Functions failing with "Value null at 's3UploadMode'" error
**Root Cause**: Missing required field in SageMaker processing job configuration
**Solution**: Added `"S3UploadMode": "EndOfJob"` to all processing job outputs
**Status**: ✅ Fixed in latest deployment

### Issue 2: Container Base Image Availability
**Symptom**: Docker builds failing for CUDA images
**Root Cause**: NVIDIA CUDA base images not available on ARM64 architecture
**Solution**: Switched to Ubuntu base images with manual CUDA installation where needed
**Status**: ✅ Resolved

### Issue 3: S3 URL Format Validation
**Symptom**: Frontend rejecting valid S3 URLs copied from AWS console
**Root Cause**: Regex only accepting HTTPS format, not `s3://` protocol
**Solution**: Updated validation to accept multiple S3 URL formats
**Status**: ✅ Fixed

## 🔄 Deployment Process

### GitHub Auto-Deploy Setup
The project uses GitHub Actions for automatic CDK deployment:
1. **Push to main branch** → Triggers deployment
2. **CDK diff** → Shows changes
3. **CDK deploy** → Applies infrastructure updates
4. **Container builds** → Automatically triggered on container changes

### Manual Deployment (if needed)
```bash
# Navigate to CDK directory
cd infrastructure/spaceport_cdk

# Activate virtual environment
source venv/bin/activate

# Deploy ML pipeline stack
cdk deploy SpaceportMLPipelineStack --require-approval never

# Build and push containers
cd ../containers
./scripts/build-all.sh --push
```

## 📊 Monitoring & Observability

### CloudWatch Dashboards
- **Step Functions**: Execution status, duration, failure rates
- **SageMaker**: Job status, resource utilization, costs
- **Lambda**: Invocation counts, duration, errors
- **API Gateway**: Request counts, latency, error rates

### Alarms Configured
- **Step Function Failures**: Triggers on any pipeline failure
- **Lambda Errors**: Alerts on function failures
- **SageMaker Job Failures**: Notifications for job failures

### Log Groups
- `/aws/stepfunctions/ml-pipeline`: Step Functions execution logs
- `/aws/lambda/Spaceport-StartMLJob`: API trigger logs
- `/aws/lambda/Spaceport-MLNotification`: Email notification logs
- `/aws/sagemaker/processing-jobs/*`: SageMaker job logs

## 💰 Cost Optimization

### Resource Sizing Strategy
- **SfM Processing**: `ml.c5.2xlarge` (CPU-intensive photogrammetry)
- **3DGS Training**: `ml.g4dn.xlarge` (GPU required for neural rendering)
- **Compression**: `ml.c5.xlarge` (CPU-only model optimization)

### Cost Controls
- **Spot Instances**: Not used (reliability over cost for production)
- **Auto-scaling**: Single instance per job (batch processing)
- **Lifecycle Policies**: ECR images limited to 10 per repository
- **S3 Lifecycle**: Automatic cleanup of incomplete multipart uploads

## 🔐 Security Considerations

### IAM Principle of Least Privilege
- **SageMaker Role**: Only necessary S3 and ECR permissions
- **Lambda Roles**: Scoped to specific resources and actions
- **Step Functions Role**: Limited to SageMaker and Lambda invocation

### Data Security
- **S3 Encryption**: Server-side encryption enabled
- **VPC**: Not required (using managed services)
- **Secrets**: No hardcoded credentials (IAM roles only)

### API Security
- **CORS**: Configured for frontend domain
- **Rate Limiting**: API Gateway default limits
- **Input Validation**: S3 URL and email format validation

## 🚀 Future Enhancements

### Planned Improvements
1. **Real-time Status Updates**: WebSocket integration for live progress
2. **Batch Processing**: Multiple files in single pipeline execution
3. **Model Variants**: Different quality/size trade-offs
4. **Cost Optimization**: Spot instance integration
5. **Advanced Monitoring**: Custom metrics and dashboards

### Scalability Considerations
- **Concurrent Jobs**: Currently limited by SageMaker quotas
- **Storage**: S3 scales automatically
- **API**: API Gateway handles high throughput
- **Containers**: ECR supports high pull rates

## 📞 Support & Troubleshooting

### Common Issues
1. **Job Failures**: Check CloudWatch logs for specific error messages
2. **S3 Access**: Verify bucket permissions and object existence
3. **Container Issues**: Check ECR repository and image availability
4. **Email Delivery**: Verify SES configuration and domain verification

### Debug Commands
```bash
# Check Step Function execution
aws stepfunctions describe-execution --execution-arn <arn>

# View SageMaker job logs
aws logs get-log-events --log-group-name /aws/sagemaker/processing-jobs/sfm

# Test API endpoint
curl -X POST https://3xzfdyvwpd.execute-api.us-west-2.amazonaws.com/prod/start-job \
  -H "Content-Type: application/json" \
  -d '{"s3Url":"s3://bucket/file.zip","email":"test@example.com"}'
```

### Contact Information
- **Primary Developer**: Gabriel Hansen
- **Email**: gbhbyu@gmail.com
- **GitHub**: Repository with auto-deploy configured

---

## 📝 Change Log

### 2025-05-28: Production Deployment
- ✅ Fixed SageMaker S3UploadMode validation error
- ✅ Deployed complete ML pipeline infrastructure
- ✅ Built and pushed all container images to ECR
- ✅ Integrated frontend with deployed API
- ✅ Configured monitoring and alerting

### 2025-05-27: Initial Development
- 🏗️ Created CDK infrastructure stack
- 🐳 Developed ML container images
- 🔗 Built API Gateway and Lambda functions
- 📧 Implemented email notification system

---

*This documentation provides complete context for any future development or troubleshooting of the Spaceport ML Pipeline system.* 