#!/bin/bash
set -e

echo "🚀 PRODUCTION-READY 3DGS CONTAINER DEPLOYMENT"
echo "============================================="

# Configuration - Fixed for us-west-2 region
AWS_REGION="us-west-2"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO_NAME="spaceport/3dgs"
CONTAINER_TAG="optimized-v1"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "📋 Configuration:"
echo "   AWS Account: ${AWS_ACCOUNT_ID}"
echo "   AWS Region: ${AWS_REGION}"
echo "   ECR Repository: ${ECR_URI}"
echo "   Container Tag: ${CONTAINER_TAG}"
echo ""

# Step 1: Login to ECR
echo "🔐 Step 1: ECR Login..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# Step 2: Build optimized container
echo "🏗️  Step 2: Building optimized 3DGS container..."
docker build -f Dockerfile.optimized -t spaceport-3dgs-optimized:latest .
docker tag spaceport-3dgs-optimized:latest ${ECR_URI}:${CONTAINER_TAG}

# Step 3: Push to ECR
echo "📤 Step 3: Pushing to ECR..."
docker push ${ECR_URI}:${CONTAINER_TAG}

ECR_IMAGE_URI="${ECR_URI}:${CONTAINER_TAG}"
echo ""
echo "✅ OPTIMIZED CONTAINER DEPLOYED SUCCESSFULLY!"
echo "   Image URI: ${ECR_IMAGE_URI}"
echo ""

# Step 4: Create test configuration
echo "📝 Step 4: Creating production test configuration..."
cat > production_test_config.json << EOF
{
  "jobName": "production-test-optimized-3dgs-$(date +%s)",
  "s3Url": "s3://spaceport-uploads/1748664812459-5woqcu-Archive.zip",
  "email": "test@spaceport.com",
  "imageUri": "${ECR_IMAGE_URI}",
  "optimizations": {
    "progressive_resolution": true,
    "initial_resolution_factor": 0.125,
    "final_resolution_factor": 1.0,
    "psnr_plateau_termination": true,
    "psnr_plateau_patience": 1000,
    "target_psnr": 35.0,
    "significance_pruning": true,
    "late_densification": true
  },
  "expected_improvements": {
    "storage_reduction": "23x smaller models",
    "training_speedup": "1.7x faster",
    "rendering_speedup": "2x faster",
    "cost_reduction": "30-40% lower training costs"
  }
}
EOF

echo "✅ Production test configuration created: production_test_config.json"
echo ""

# Step 5: Performance validation script
echo "📊 Step 5: Creating performance validation script..."
cat > validate_performance.py << 'EOF'
#!/usr/bin/env python3
"""
Production Performance Validation Script
Validates 3DGS training results against production requirements
"""

import json
import boto3
import time
from pathlib import Path

def validate_training_results(job_name, s3_bucket, s3_prefix):
    """Validate training results meet production standards"""
    s3 = boto3.client('s3', region_name='us-west-2')
    
    # Expected performance criteria
    criteria = {
        'min_psnr': 35.0,
        'max_model_size_mb': 50.0,
        'max_training_time_hours': 2.0,
        'min_gaussians': 50000,
        'max_gaussians': 500000
    }
    
    print("🔍 PRODUCTION VALIDATION CHECKLIST")
    print("=" * 40)
    
    validation_results = {
        'passed': True,
        'criteria_met': {},
        'performance_metrics': {}
    }
    
    try:
        # Check for optimization_params.json
        response = s3.get_object(
            Bucket=s3_bucket,
            Key=f"{s3_prefix}/optimization_params.json"
        )
        params = json.loads(response['Body'].read())
        
        # Extract metrics
        final_psnr = params['training_results']['final_psnr']
        model_size_mb = params['model_stats']['model_size_estimate_mb']
        training_time_hours = params['training_results']['training_time_seconds'] / 3600
        final_gaussians = params['training_results']['final_gaussians']
        converged_early = params['training_results']['converged_early']
        
        validation_results['performance_metrics'] = {
            'final_psnr': final_psnr,
            'model_size_mb': model_size_mb,
            'training_time_hours': training_time_hours,
            'final_gaussians': final_gaussians,
            'converged_early': converged_early
        }
        
        # Validate criteria
        validation_results['criteria_met']['psnr'] = final_psnr >= criteria['min_psnr']
        validation_results['criteria_met']['model_size'] = model_size_mb <= criteria['max_model_size_mb']
        validation_results['criteria_met']['training_time'] = training_time_hours <= criteria['max_training_time_hours']
        validation_results['criteria_met']['gaussian_count'] = criteria['min_gaussians'] <= final_gaussians <= criteria['max_gaussians']
        
        # Overall pass/fail
        validation_results['passed'] = all(validation_results['criteria_met'].values())
        
        # Print results
        print(f"✅ PSNR: {final_psnr:.2f}dB (min: {criteria['min_psnr']}dB) - {'PASS' if validation_results['criteria_met']['psnr'] else 'FAIL'}")
        print(f"✅ Model Size: {model_size_mb:.1f}MB (max: {criteria['max_model_size_mb']}MB) - {'PASS' if validation_results['criteria_met']['model_size'] else 'FAIL'}")
        print(f"✅ Training Time: {training_time_hours:.2f}h (max: {criteria['max_training_time_hours']}h) - {'PASS' if validation_results['criteria_met']['training_time'] else 'FAIL'}")
        print(f"✅ Gaussians: {final_gaussians:,} (range: {criteria['min_gaussians']:,}-{criteria['max_gaussians']:,}) - {'PASS' if validation_results['criteria_met']['gaussian_count'] else 'FAIL'}")
        print(f"✅ Early Convergence: {'YES' if converged_early else 'NO'}")
        
        print("\n" + "=" * 40)
        if validation_results['passed']:
            print("🎉 PRODUCTION VALIDATION: PASSED")
            print("   Container is ready for production deployment!")
        else:
            print("❌ PRODUCTION VALIDATION: FAILED")
            print("   Container needs optimization before production use")
        
    except Exception as e:
        print(f"❌ Validation failed: {str(e)}")
        validation_results['passed'] = False
        validation_results['error'] = str(e)
    
    return validation_results

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python validate_performance.py <job_name> <s3_bucket> <s3_prefix>")
        sys.exit(1)
    
    job_name, s3_bucket, s3_prefix = sys.argv[1:4]
    results = validate_training_results(job_name, s3_bucket, s3_prefix)
    sys.exit(0 if results['passed'] else 1)
EOF

chmod +x validate_performance.py
echo "✅ Performance validation script created: validate_performance.py"
echo ""

echo "🎯 PRODUCTION DEPLOYMENT COMPLETE!"
echo ""
echo "📋 NEXT STEPS FOR PRODUCTION TESTING:"
echo "1. Use the optimized container URI: ${ECR_IMAGE_URI}"
echo "2. Run test job with small dataset (22 photos)"
echo "3. Validate performance with validate_performance.py"
echo "4. Scale to larger datasets once validated"
echo ""
echo "🚀 Expected Improvements:"
echo "   • 23× smaller storage (1GB → ~45MB)"
echo "   • 1.7× faster training convergence"
echo "   • 2× faster rendering performance"
echo "   • 30-40% cost reduction"
echo "   • PSNR plateau early termination"
echo ""
echo "Ready for production testing! 🌟" 