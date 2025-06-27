#!/usr/bin/env python3
"""
3DGS-Only Pipeline Test
======================
Test ONLY the 3DGS training stage using pre-existing SfM data.
This allows rapid iteration on 3DGS parameters without waiting for SfM.
"""

import boto3
import json
import time
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
        self.stepfunctions = boto3.client('stepfunctions', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        
        self.config = {
            'state_machine_arn': f"arn:aws:states:{region}:{self.account_id}:stateMachine:SpaceportMLPipeline",
            'existing_sfm_data': "s3://spaceport-ml-pipeline/jobs/prod-validation-1750995274/colmap/",
            'container_uri': f"{self.account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/3dgs:latest",
            'test_email': "test@spaceport.com"
        }
    
    def create_3dgs_only_input(self) -> Dict:
        """Create test input that skips SfM and starts directly from 3DGS training."""
        job_id = f"3dgs-only-{int(time.time())}"
        timestamp = datetime.now().isoformat()
        
        return {
            # Required Step Functions fields
            "jobId": job_id,
            "jobName": f"3dgs-only-{job_id}",
            "s3Url": "dummy",  # Not used when skipping SfM
            "inputS3Uri": "dummy",
            "email": self.config['test_email'],
            "timestamp": timestamp,
            
            # CRITICAL: Start directly from 3DGS stage
            "pipelineStep": "gaussian",  # Skip SfM, start from 3DGS
            
            # Use existing SfM data
            "colmapOutputS3Uri": self.config['existing_sfm_data'],
            "gaussianOutputS3Uri": f"s3://spaceport-ml-pipeline/jobs/{job_id}/gaussian/",
            "compressedOutputS3Uri": f"s3://spaceport-ml-pipeline/jobs/{job_id}/compressed/",
            
            # Container URIs
            "gaussianImageUri": self.config['container_uri'],
            "compressorImageUri": f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/spaceport/compressor:latest",
            
            # Enhanced 3DGS training parameters for proper training
            "optimization_enabled": True,
            "progressive_resolution": True,
            "psnr_plateau_termination": False,  # DISABLE early termination for now
            "target_psnr": 35.0,  # Higher target
            "max_iterations": 15000,  # More iterations
            "plateau_patience": 2000,  # More patience
            "min_iterations": 5000,  # Minimum iterations before early stopping
            "learning_rate": 0.0025,  # Lower learning rate for stability
            "position_lr_scale": 0.5,  # Scale position learning rate
            "scaling_lr": 0.005,  # Scaling learning rate
            "rotation_lr": 0.001,  # Rotation learning rate
            "opacity_lr": 0.05,  # Opacity learning rate
            "feature_lr": 0.0025,  # Feature learning rate
            "densification_interval": 100,  # Densify every 100 iterations
            "opacity_reset_interval": 3000,  # Reset opacity every 3000 iterations
            "densify_from_iter": 500,  # Start densification from iteration 500
            "densify_until_iter": 12000,  # Stop densification at iteration 12000
            "densify_grad_threshold": 0.0002,  # Gradient threshold for densification
            "percent_dense": 0.01,  # Percentage of scene to densify
            "lambda_dssim": 0.2,  # SSIM loss weight
            "sh_degree": 3  # Spherical harmonics degree
        }
    
    def start_3dgs_test(self) -> Tuple[Optional[str], Optional[Dict]]:
        """Start a 3DGS-only test execution."""
        test_input = self.create_3dgs_only_input()
        execution_name = f"3dgs-only-{int(time.time())}"
        
        logger.info("🎯 STARTING 3DGS-ONLY TRAINING TEST")
        logger.info("=" * 60)
        logger.info(f"Job ID: {test_input['jobId']}")
        logger.info(f"Execution Name: {execution_name}")
        logger.info(f"Using existing SfM data: {self.config['existing_sfm_data']}")
        logger.info("")
        logger.info("🔧 ENHANCED TRAINING PARAMETERS:")
        logger.info(f"  Max Iterations: {test_input['max_iterations']}")
        logger.info(f"  Min Iterations: {test_input['min_iterations']}")
        logger.info(f"  Target PSNR: {test_input['target_psnr']}dB")
        logger.info(f"  Early Termination: {'DISABLED' if not test_input['psnr_plateau_termination'] else 'ENABLED'}")
        logger.info(f"  Learning Rate: {test_input['learning_rate']}")
        logger.info(f"  Densification: Every {test_input['densification_interval']} iterations")
        logger.info("")
        
        try:
            response = self.stepfunctions.start_execution(
                stateMachineArn=self.config['state_machine_arn'],
                name=execution_name,
                input=json.dumps(test_input)
            )
            
            execution_arn = response['executionArn']
            logger.info(f"✅ 3DGS test started successfully!")
            logger.info(f"📋 Execution ARN: {execution_arn}")
            logger.info("")
            
            return execution_arn, test_input
            
        except Exception as e:
            logger.error(f"❌ Failed to start 3DGS test: {str(e)}")
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
        
        job_id = test_input['jobId']
        bucket = 'spaceport-ml-pipeline'
        prefix = f"jobs/{job_id}/gaussian/"
        
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
                                logger.info(f"   Final PSNR: {metadata.get('final_psnr', 'unknown'):.1f}dB")
                                logger.info(f"   Training Time: {metadata.get('training_time', 'unknown'):.1f}s")
                                logger.info(f"   Num Gaussians: {metadata.get('num_gaussians', 'unknown')}")
                                
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
        """Run a complete 3DGS-only test."""
        execution_arn, test_input = self.start_3dgs_test()
        
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
    logger.info("🚀 Starting 3DGS-Only Pipeline Test")
    logger.info("This test uses existing SfM data to test ONLY the 3DGS training stage")
    logger.info("Allows rapid iteration on 3DGS parameters without SfM overhead")
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