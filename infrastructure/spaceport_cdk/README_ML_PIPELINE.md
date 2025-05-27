# Spaceport ML Pipeline Deployment Guide

This guide covers the deployment of the production-grade Gaussian-splat ML pipeline infrastructure.

## Architecture Overview

The ML pipeline consists of:

1. **API Gateway** → **Lambda** → **Step Functions** → **SageMaker Jobs** → **Notification Lambda**
2. **Three SageMaker Jobs**: SfM Processing (COLMAP) → 3DGS Training → Compression (SOGS)
3. **S3 Buckets**: Input uploads, COLMAP outputs, 3DGS outputs, compressed outputs
4. **ECR Repositories**: Container images for each processing step
5. **CloudWatch**: Logging and monitoring

## Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **AWS CDK** installed (`npm install -g aws-cdk`)
3. **Python 3.9+** and pip
4. **Docker** for building container images
5. **SES Email Verification** for notifications

## Deployment Steps

### 1. Install Dependencies

```bash
cd infrastructure/spaceport_cdk
pip install -r requirements.txt
```

### 2. Bootstrap CDK (if not done already)

```bash
cdk bootstrap
```

### 3. Deploy the Infrastructure

```bash
# Deploy both stacks
cdk deploy --all

# Or deploy just the ML pipeline stack
cdk deploy SpaceportMLPipelineStack
```

### 4. Build and Push Container Images

After deployment, you'll need to build and push the ML container images to the ECR repositories.

#### SfM Container (COLMAP)
```bash
# Get the ECR repository URI from CDK outputs
SFM_REPO_URI=$(aws cloudformation describe-stacks \
  --stack-name SpaceportMLPipelineStack \
  --query 'Stacks[0].Outputs[?OutputKey==`SfMRepositoryUri`].OutputValue' \
  --output text)

# Build and push
cd infrastructure/containers/sfm
docker build -t spaceport-sfm .
docker tag spaceport-sfm:latest $SFM_REPO_URI:latest

# Login to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $SFM_REPO_URI

# Push
docker push $SFM_REPO_URI:latest
```

#### 3DGS Container (Gaussian Splatting)
```bash
# Get the ECR repository URI
GAUSSIAN_REPO_URI=$(aws cloudformation describe-stacks \
  --stack-name SpaceportMLPipelineStack \
  --query 'Stacks[0].Outputs[?OutputKey==`GaussianRepositoryUri`].OutputValue' \
  --output text)

# Build your 3DGS container (you'll need to create this)
cd infrastructure/containers/3dgs
docker build -t spaceport-3dgs .
docker tag spaceport-3dgs:latest $GAUSSIAN_REPO_URI:latest
docker push $GAUSSIAN_REPO_URI:latest
```

#### Compressor Container (SOGS)
```bash
# Get the ECR repository URI
COMPRESSOR_REPO_URI=$(aws cloudformation describe-stacks \
  --stack-name SpaceportMLPipelineStack \
  --query 'Stacks[0].Outputs[?OutputKey==`CompressorRepositoryUri`].OutputValue' \
  --output text)

# Build your compressor container (you'll need to create this)
cd infrastructure/containers/compressor
docker build -t spaceport-compressor .
docker tag spaceport-compressor:latest $COMPRESSOR_REPO_URI:latest
docker push $COMPRESSOR_REPO_URI:latest
```

### 5. Configure SES Email

The notification system requires SES to be configured:

```bash
# Verify the sender email address
aws ses verify-email-identity --email-address noreply@hansenhome.ai

# If using a custom domain, verify the domain
aws ses verify-domain-identity --domain hansenhome.ai
```

### 6. Update Frontend Configuration

Update the API Gateway URL in `script.js`:

```javascript
// Get the API URL from CDK outputs
const ML_API_BASE_URL = 'https://your-api-gateway-id.execute-api.us-west-2.amazonaws.com/prod';
```

You can get the API URL from the CDK outputs:
```bash
aws cloudformation describe-stacks \
  --stack-name SpaceportMLPipelineStack \
  --query 'Stacks[0].Outputs[?OutputKey==`MLApiUrl`].OutputValue' \
  --output text
```

## Testing the Pipeline

### 1. Upload Test Data

Upload a ZIP file of drone photos to your S3 upload bucket:

```bash
aws s3 cp test-photos.zip s3://spaceport-uploads/test/
```

### 2. Trigger Processing

Use the frontend interface or call the API directly:

```bash
curl -X POST https://your-api-gateway-url/prod/start-job \
  -H "Content-Type: application/json" \
  -d '{
    "s3Url": "https://spaceport-uploads.s3.amazonaws.com/test/test-photos.zip",
    "email": "your-email@example.com"
  }'
```

### 3. Monitor Progress

- **Step Functions Console**: Monitor the execution progress
- **CloudWatch Logs**: View detailed logs from each step
- **SageMaker Console**: Monitor job status and resource usage

## Monitoring and Troubleshooting

### CloudWatch Dashboards

Key metrics to monitor:
- Step Function execution success/failure rates
- SageMaker job duration and costs
- Lambda function errors and duration
- S3 bucket usage

### Common Issues

1. **Container Build Failures**: Ensure Docker is running and you have sufficient disk space
2. **SageMaker Job Failures**: Check CloudWatch logs for specific error messages
3. **Email Notifications Not Sent**: Verify SES configuration and sender email verification
4. **S3 Access Denied**: Ensure IAM roles have proper S3 permissions

### Log Locations

- **Step Functions**: `/aws/stepfunctions/ml-pipeline`
- **SfM Processing**: `/aws/sagemaker/processing-jobs/sfm`
- **3DGS Training**: `/aws/sagemaker/training-jobs/3dgs`
- **Compression**: `/aws/sagemaker/processing-jobs/compressor`
- **Lambda Functions**: `/aws/lambda/Spaceport-StartMLJob` and `/aws/lambda/Spaceport-MLNotification`

## Cost Optimization

1. **Instance Types**: Adjust SageMaker instance types based on workload requirements
2. **Spot Instances**: Consider using spot instances for training jobs
3. **S3 Lifecycle**: Configure lifecycle rules to move old data to cheaper storage classes
4. **CloudWatch Logs**: Set appropriate retention periods

## Security Considerations

1. **IAM Roles**: Follow principle of least privilege
2. **VPC**: Consider running SageMaker jobs in a VPC for additional security
3. **Encryption**: Enable S3 bucket encryption and EBS volume encryption
4. **API Gateway**: Add authentication/authorization as needed

## Scaling Considerations

1. **Concurrent Executions**: Step Functions can handle multiple concurrent executions
2. **SageMaker Limits**: Be aware of SageMaker service limits in your region
3. **S3 Performance**: Use appropriate prefixes for high-throughput scenarios

## Next Steps

1. **Container Optimization**: Optimize container images for faster startup times
2. **Model Versioning**: Implement model versioning and A/B testing
3. **Advanced Monitoring**: Set up custom CloudWatch alarms and SNS notifications
4. **Cost Tracking**: Implement detailed cost tracking with tags

## Support

For issues or questions:
- Check CloudWatch logs first
- Review the Step Functions execution history
- Contact the development team with specific error messages and execution ARNs 