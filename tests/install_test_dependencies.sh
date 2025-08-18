#!/bin/bash

# 🔧 Install Beta Readiness Test Dependencies
# This script installs all required Python packages for the beta readiness test suite

echo "🚀 Installing Beta Readiness Test Dependencies"
echo "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip first."
    exit 1
fi

echo "✅ pip3 found: $(pip3 --version)"

# Install required packages
echo ""
echo "📦 Installing required Python packages..."

packages=(
    "boto3>=1.26.0"
    "requests>=2.28.0"
    "pytest>=7.0.0"
    "asyncio"
    "concurrent.futures"
)

for package in "${packages[@]}"; do
    echo "Installing $package..."
    pip3 install "$package" --quiet
    if [ $? -eq 0 ]; then
        echo "✅ $package installed successfully"
    else
        echo "❌ Failed to install $package"
        exit 1
    fi
done

echo ""
echo "🔑 Checking AWS CLI configuration..."

# Check if AWS CLI is installed
if command -v aws &> /dev/null; then
    echo "✅ AWS CLI found: $(aws --version)"
    
    # Check if AWS credentials are configured
    if aws sts get-caller-identity &> /dev/null; then
        echo "✅ AWS credentials are configured"
        echo "   Account: $(aws sts get-caller-identity --query Account --output text)"
        echo "   Region: $(aws configure get region)"
    else
        echo "⚠️  AWS credentials not configured or invalid"
        echo "   Please run: aws configure"
        echo "   Or set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
    fi
else
    echo "⚠️  AWS CLI not found. Tests will use boto3 with environment variables."
    echo "   Install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
fi

echo ""
echo "🧪 Testing package imports..."

# Test imports
python3 -c "
import boto3
import requests
import json
import concurrent.futures
import asyncio
print('✅ All packages imported successfully')
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ All packages working correctly"
else
    echo "❌ Package import test failed"
    exit 1
fi

echo ""
echo "📋 Installation Summary:"
echo "✅ Python packages installed"
echo "✅ Import tests passed"
echo "✅ Ready to run beta readiness tests"

echo ""
echo "🚀 Next Steps:"
echo "1. Configure AWS credentials if not already done:"
echo "   aws configure"
echo ""
echo "2. Run the comprehensive beta readiness test suite:"
echo "   python3 tests/run_beta_readiness_suite.py"
echo ""
echo "3. Or run a quick test:"
echo "   python3 tests/run_beta_readiness_suite.py --quick"
echo ""
echo "4. For individual test suites:"
echo "   python3 tests/beta_readiness_comprehensive_test.py"
echo "   python3 tests/multi_user_concurrency_test.py"
echo "   python3 tests/production_monitoring_test.py"

echo ""
echo "🎉 Setup complete! Your system is ready for beta readiness testing."
