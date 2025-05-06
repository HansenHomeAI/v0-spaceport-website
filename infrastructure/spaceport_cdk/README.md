# Spaceport Website Infrastructure

This is the AWS CDK infrastructure for the Spaceport Website. It includes:

- API Gateway for drone flight path generation and file uploads
- Lambda functions for backend processing
- S3 bucket for file storage
- DynamoDB tables for metadata storage

## Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Deploy the infrastructure
cdk deploy
``` 