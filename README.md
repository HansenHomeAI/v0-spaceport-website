# Spaceport Website

This repository contains the Spaceport Website, a platform for generating drone flight paths and handling user uploads.

## Project Structure

```
spaceport-website/
├── frontend/                    # Frontend application
│   ├── public/                  # Static files served directly
│   │   ├── index.html          # Main HTML file
│   │   └── assets/             # Images, logos, etc.
│   ├── src/                    # Source code
│   │   ├── styles.css          # Stylesheets
│   │   └── script.js           # JavaScript code
│   └── package.json            # Frontend dependencies
├── infrastructure/             # AWS CDK infrastructure code
│   └── spaceport_cdk/
│       ├── lambda/             # Lambda function source code
│       │   ├── file_upload/    # File upload handling
│       │   └── drone_path/     # Drone path generation
│       ├── app.py              # CDK app entry point
│       └── requirements.txt    # Python dependencies
├── .github/                    # GitHub Actions workflows
│   └── workflows/
├── package.json                # Root project configuration
└── README.md                   # This file
```

## Backend Infrastructure

The backend is managed with AWS CDK and includes:

- API Gateway endpoints for drone path generation and file uploads
- Lambda functions for processing requests
- S3 bucket for file storage
- DynamoDB tables for metadata
- SES for email notifications

All AWS resources are prefixed with "Spaceport-" for easy identification.

## Quick Start

### Development

```bash
# Install dependencies
npm install

# Start frontend development server
npm run dev

# Visit http://localhost:8000
```

### Deployment

```bash
# Deploy infrastructure to AWS
npm run deploy
```

## Detailed Setup

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

### Frontend Development

```bash
# Navigate to frontend directory
cd frontend

# Start development server
npm run dev

# Visit http://localhost:8000
```

## Features

- **Drone Path Generation**: Generate optimized flight paths for different property types
- **File Upload**: Secure multipart upload to S3 with progress tracking
- **Email Notifications**: Automated notifications via AWS SES
- **Responsive Design**: Modern, mobile-friendly interface

## Contributing

1. Follow the established directory structure
2. Keep frontend and backend code separated
3. Use meaningful commit messages
4. Test changes locally before pushing

## License

MIT License - see LICENSE file for details 