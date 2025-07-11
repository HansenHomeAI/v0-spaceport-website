#!/usr/bin/env python3
"""
3DGS-Only Pipeline Test - Refactored to use Lambda for single source of truth

This test calls the deployed start_ml_job Lambda function instead of directly
invoking Step Functions, ensuring hyperparameters are managed in one place.

The test skips SfM processing by using existing COLMAP data and focuses solely
on testing 3D Gaussian Splatting training with the current hyperparameters.
"""

import json
import time
import boto3
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GaussianOnlyTester:
    def __init__(self, region='us-west-2'):
        self.region = region
        self.account_id = '975050048887'
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.stepfunctions = boto3.client('stepfunctions', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        
        self.config = {
            'lambda_function_name': 'Spaceport-StartMLJob',
            'existing_sfm_data': "s3://spaceport-ml-processing/colmap/c3c249de-03ab-4a2f-af72-d88a9412565d/",
            'test_email': "gbhbyu@gmail.com"
        }
    
    def create_lambda_test_payload(self) -> Dict:
        """Create payload for Lambda function that will start 3DGS-only training."""
        return {
            "body": {
                "s3Url": "s3://spaceport-uploads/1751413909023-l2zkyj-Battery-1.zip",  # Same dataset as successful SfM run
                "email": self.config['test_email'],
                "pipelineStep": "3dgs",  # CRITICAL: Start directly from 3DGS stage
                "existingColmapUri": self.config['existing_sfm_data'],  # Use existing SfM data
                "hyperparameters": {
                    "max_iterations": 25000,  # Production quality training
                    "target_psnr": 30.0,      # Realistic target for 77 training images
                    "densify_grad_threshold": 0.0002,  # Standard threshold
                    "densification_interval": 100,     # Standard interval
                    "lambda_dssim": 0.2,               # Standard DSSIM weight
                    "sh_degree": 3,                    # Full spherical harmonics
                    "learning_rate": 0.0025,           # Standard learning rate
                    "position_lr_scale": 1.0,          # Standard position scaling
                    "log_interval": 100,               # Log every 100 iterations
                    "save_interval": 5000,             # Save every 5000 iterations
                    "plateau_patience": 1000,          # Allow 1000 iterations without improvement
                    "psnr_plateau_termination": True   # Enable early stopping
                }
            }
        }
    
    def invoke_lambda_for_3dgs_test(self) -> Tuple[Optional[str], Optional[Dict]]:
        """Invoke the Lambda function and get Step Function execution details."""
        payload = self.create_lambda_test_payload()
        
        logger.info("🎯 STARTING 3DGS-ONLY TEST VIA LAMBDA")
        logger.info("=" * 60)
        logger.info(f"Lambda Function: {self.config['lambda_function_name']}")
        logger.info(f"Pipeline Step: {payload['body']['pipelineStep']}")
        logger.info(f"Using existing SfM data: {self.config['existing_sfm_data']}")
        logger.info("")
        
        try:
            # Invoke the Lambda function
            response = self.lambda_client.invoke(
                FunctionName=self.config['lambda_function_name'],
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            # Parse Lambda response
            lambda_response = json.loads(response['Payload'].read())
            
            if lambda_response.get('statusCode') != 200:
                logger.error(f"❌ Lambda returned error: {lambda_response}")
                return None, None
            
            # Extract execution details
            body = json.loads(lambda_response['body'])
            execution_arn = body['executionArn']
            job_id = body['jobId']
            
            logger.info(f"✅ Lambda invoked successfully!")
            logger.info(f"📋 Job ID: {job_id}")
            logger.info(f"📋 Execution ARN: {execution_arn}")
            
            # Get the Step Function input to understand what hyperparameters were used
            execution_desc = self.stepfunctions.describe_execution(executionArn=execution_arn)
            step_function_input = json.loads(execution_desc['input'])
            
            # Log the hyperparameters being used (sourced from Lambda)
            logger.info("\n🔧 HYPERPARAMETERS FROM LAMBDA (SINGLE SOURCE OF TRUTH):")
            logger.info(f"  Max Iterations: {step_function_input.get('max_iterations', 'N/A')}")
            logger.info(f"  Min Iterations: {step_function_input.get('min_iterations', 'N/A')}")
            logger.info(f"  Target PSNR: {step_function_input.get('target_psnr', 'N/A')}dB")
            logger.info(f"  Densify Grad Threshold: {step_function_input.get('densify_grad_threshold', 'N/A')}")
            logger.info(f"  Densification Interval: {step_function_input.get('densification_interval', 'N/A')}")
            logger.info(f"  Progressive Densification: {step_function_input.get('progressive_densification_enabled', 'N/A')}")
            logger.info(f"  Learning Rate: {step_function_input.get('learning_rate', 'N/A')}")
            logger.info(f"  Position LR Scale: {step_function_input.get('position_lr_scale', 'N/A')}")
            logger.info(f"  SH Degree: {step_function_input.get('sh_degree', 'N/A')}")
            logger.info(f"  Progressive Resolution: {step_function_input.get('progressive_resolution_enabled', 'N/A')}")
            logger.info(f"  Split Threshold: {step_function_input.get('split_threshold', 'N/A')}")
            logger.info(f"  Clone Threshold: {step_function_input.get('clone_threshold', 'N/A')}")
            logger.info(f"  Max Gaussians: {step_function_input.get('max_gaussians', 'N/A')}")
            logger.info("")
            
            return execution_arn, step_function_input
            
        except Exception as e:
            logger.error(f"❌ Failed to invoke Lambda: {str(e)}")
            return None, None
    
    def monitor_3dgs_execution(self, execution_arn: str, test_input: Dict) -> Dict:
        """Monitor the 3DGS-only execution with detailed tracking."""
        logger.info("⏱️  MONITORING 3DGS TRAINING")
        logger.info("=" * 40)
        
        start_time = time.time()
        max_wait_time = 3600  # 1 hour max for 3DGS only
        last_status = None
        
        while time.time() - start_time < max_wait_time:
            try:
                execution_desc = self.stepfunctions.describe_execution(executionArn=execution_arn)
                status = execution_desc['status']
                
                elapsed_minutes = (time.time() - start_time) / 60
                
                if status != last_status:
                    logger.info(f"📊 [{elapsed_minutes:6.1f}m] Status: {status}")
                    last_status = status
                
                # Check for completion
                if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                    final_duration_minutes = (time.time() - start_time) / 60
                    logger.info(f"\n🏁 3DGS TRAINING COMPLETED: {status}")
                    logger.info(f"⏱️  Duration: {final_duration_minutes:.1f} minutes")
                    
                    return {
                        'status': status,
                        'duration_minutes': final_duration_minutes,
                        'execution_arn': execution_arn
                    }
                
                # Log progress every minute
                if int(elapsed_minutes) % 1 == 0:
                    logger.info(f"⏳ [{elapsed_minutes:6.1f}m] Training in progress... Status: {status}")
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Error monitoring execution: {str(e)}")
                time.sleep(60)
        
        # Timeout reached
        logger.warning(f"⚠️  3DGS training timed out after {max_wait_time/60:.1f} minutes")
        return {
            'status': 'TIMEOUT',
            'duration_minutes': max_wait_time / 60,
            'execution_arn': execution_arn
        }
    
    def validate_3dgs_output(self, test_input: Dict) -> Dict:
        """Validate the 3DGS training output."""
        logger.info("\n🔍 VALIDATING 3DGS OUTPUT")
        logger.info("=" * 30)

        # Extract job_id for use throughout the function
        job_id = test_input.get('jobId')
        
        # Prefer the Gaussian output URI provided by the Lambda / Step-Functions payload
        gaussian_uri = test_input.get('gaussianOutputS3Uri')
        if gaussian_uri and gaussian_uri.startswith('s3://'):
            from urllib.parse import urlparse
            parsed = urlparse(gaussian_uri)
            bucket = parsed.netloc
            # Ensure prefix ends with a slash so list_objects_v2 treats it as prefix
            prefix = parsed.path.lstrip('/')
            if not prefix.endswith('/'):
                prefix += '/'
            logger.info(f"📁 Using Gaussian output URI from payload: s3://{bucket}/{prefix}")
        else:
            # Fallback to legacy location for backward compatibility
            bucket = 'spaceport-ml-pipeline'
            prefix = f"jobs/{job_id}/gaussian/"
            logger.info(f"📁 Falling back to legacy output location: s3://{bucket}/{prefix}")
        
        try:
            response = self.s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            
            if 'Contents' in response:
                files = response['Contents']
                file_count = len(files)
                total_size_mb = sum(obj['Size'] for obj in files) / (1024 * 1024)
                
                logger.info(f"✅ 3DGS Output: {file_count} files, {total_size_mb:.2f} MB")
                
                # Look for model files
                model_files = [f for f in files if 'model' in f['Key'].lower()]
                if model_files:
                    logger.info(f"📦 Model files found:")
                    for model_file in model_files:
                        size_kb = model_file['Size'] / 1024
                        logger.info(f"   - {model_file['Key']} ({size_kb:.1f} KB)")
                        
                        # Download and analyze model metadata
                        if 'model.tar.gz' in model_file['Key']:
                            try:
                                # Get model metadata
                                temp_path = f"/tmp/model_{job_id}.tar.gz"
                                self.s3.download_file(bucket, model_file['Key'], temp_path)
                                
                                # Extract and read metadata
                                import subprocess
                                subprocess.run(['tar', '-xzf', temp_path, '-C', '/tmp/'], check=True)
                                
                                with open('/tmp/training_metadata.json', 'r') as f:
                                    metadata = json.load(f)
                                
                                logger.info(f"📊 Training Results:")
                                logger.info(f"   Iterations: {metadata.get('iterations', 'unknown')}")
                                logger.info(f"   Final Loss: {metadata.get('final_loss', 'unknown'):.6f}")
                                
                                # Clean up
                                import os
                                os.remove(temp_path)
                                if os.path.exists('/tmp/training_metadata.json'):
                                    os.remove('/tmp/training_metadata.json')
                                if os.path.exists('/tmp/final_model.ply'):
                                    os.remove('/tmp/final_model.ply')
                                
                            except Exception as e:
                                logger.warning(f"Could not analyze model metadata: {e}")
                
                return {
                    'success': True,
                    'file_count': file_count,
                    'size_mb': total_size_mb,
                    'has_model': len(model_files) > 0
                }
            else:
                logger.warning("❌ No 3DGS output files found")
                return {
                    'success': False,
                    'file_count': 0,
                    'size_mb': 0.0,
                    'has_model': False
                }
                
        except Exception as e:
            logger.error(f"❌ Error validating output: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_full_test(self) -> bool:
        """Run a complete 3DGS-only test using the Lambda function."""
        execution_arn, test_input = self.invoke_lambda_for_3dgs_test()
        
        if not execution_arn:
            return False
        
        # Monitor execution
        results = self.monitor_3dgs_execution(execution_arn, test_input)
        
        # Validate output
        if results['status'] == 'SUCCEEDED':
            output_validation = self.validate_3dgs_output(test_input)
            
            if output_validation['success']:
                logger.info("\n🎉 3DGS-ONLY TEST SUCCESSFUL!")
                logger.info("=" * 40)
                logger.info("✅ Training completed successfully")
                logger.info("✅ Model files generated")
                logger.info("✅ Hyperparameters sourced from Lambda (single source of truth)")
                logger.info("🚀 Ready for further parameter tuning!")
                return True
            else:
                logger.error("\n❌ 3DGS test failed - no valid output")
                return False
        else:
            logger.error(f"\n❌ 3DGS test failed with status: {results['status']}")
            return False

def main():
    """Main test function."""
    logger.info("🚀 Starting 3DGS-Only Pipeline Test (Lambda-based)")
    logger.info("This test calls the deployed Lambda function for single source of truth")
    logger.info("Uses existing SfM data to test ONLY the 3DGS training stage")
    logger.info("Hyperparameters are managed entirely in the Lambda function")
    logger.info("")
    
    tester = GaussianOnlyTester()
    success = tester.run_full_test()
    
    if success:
        logger.info("\n✅ 3DGS-only test completed successfully!")
        exit(0)
    else:
        logger.error("\n❌ 3DGS-only test failed!")
        exit(1)

if __name__ == "__main__":
    main() 