# Spaceport Website

This repository contains the Spaceport Website, a platform for generating drone flight paths and handling user uploads.

## Project Structure

- `/` - Root directory containing the website's frontend (HTML, CSS, JS)
- `/assets` - Website assets (images, etc.)
- `/infrastructure` - AWS CDK code for deploying backend resources
- `/lambda` - AWS Lambda function code for backend processing

## Backend Infrastructure

The backend is managed with AWS CDK and includes:

- API Gateway endpoints for drone path generation and file uploads
- Lambda functions for processing requests
- S3 bucket for file storage
- DynamoDB tables for metadata

All AWS resources are prefixed with "Spaceport-" for easy identification.

## Deployment

### Prerequisites

- AWS CLI configured with appropriate credentials
- Node.js and npm installed
- Python 3.9+ installed

### Backend Deployment

```bash
# Navigate to the CDK project directory
cd infrastructure/spaceport_cdk

# Create and activate a Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Deploy the infrastructure
cdk synth  # To generate CloudFormation template
cdk deploy # To deploy resources to AWS
```

### Frontend Deployment

The frontend website can be deployed to any static hosting service. If using AWS:

1. Create an S3 bucket for static website hosting
2. Configure CloudFront for HTTPS support
3. Upload the website files to S3

## Local Development

For local development of the website, you can use a simple HTTP server:

```bash
# Using Python
python -m http.server 8000
```

Then visit `http://localhost:8000` in your browser. 