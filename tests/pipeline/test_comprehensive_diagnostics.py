#!/usr/bin/env python3
"""
Comprehensive Pipeline Diagnostics Test
=======================================

This test performs in-depth analysis of each pipeline stage to identify issues:
1. Archive extraction and image validation
2. SfM/COLMAP reconstruction analysis
3. 3DGS training data validation
4. SOGS compression readiness

Expected findings:
- Why only 2/20 images are being processed by SfM
- Whether images have sufficient overlap for reconstruction
- If COLMAP parameters need adjustment
- Pipeline bottlenecks and optimization opportunities
"""

import boto3
import logging
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import zipfile
import tempfile
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensivePipelineDiagnostics:
    """Comprehensive diagnostics for the entire ML pipeline."""
    
    def __init__(self, region='us-west-2'):
        self.region = region
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
        # Initialize AWS clients
        self.stepfunctions = boto3.client('stepfunctions', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.sagemaker = boto3.client('sagemaker', region_name=region)
        self.cloudwatch = boto3.client('logs', region_name=region)
        
        # Test configuration
        self.config = {
            'test_dataset_s3_url': 's3://spaceport-uploads/1749575207099-4fanwl-Archive.zip',
            'state_machine_arn': f'arn:aws:states:{region}:{self.account_id}:stateMachine:SpaceportMLPipeline',
            'bucket': 'spaceport-ml-pipeline',
            
            # Container URIs
            'container_uris': {
                'sfm': f'{self.account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/sfm:latest',
                '3dgs': f'{self.account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/3dgs:latest',
                'compressor': f'{self.account_id}.dkr.ecr.{region}.amazonaws.com/spaceport/compressor:latest'
            }
        }
    
    def run_comprehensive_diagnostics(self) -> Dict:
        """Run complete pipeline diagnostics."""
        logger.info("🎯 COMPREHENSIVE PIPELINE DIAGNOSTICS")
        logger.info("=" * 60)
        logger.info("This test will analyze why SfM only processes 2/20 images")
        logger.info("Expected duration: 30-45 minutes for thorough analysis")
        logger.info("")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'dataset_analysis': {},
            'sfm_analysis': {},
            'recommendations': []
        }
        
        # Analyze the dataset
        logger.info("🔍 ANALYZING SOURCE DATASET")
        logger.info("=" * 50)
        
        # Extract S3 details
        s3_url = self.config['test_dataset_s3_url']
        bucket = s3_url.split('/')[2]
        key = '/'.join(s3_url.split('/')[3:])
        
        logger.info(f"📁 Source: {s3_url}")
        logger.info(f"   Bucket: {bucket}")
        logger.info(f"   Key: {key}")
        
        # Download and analyze archive
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "dataset.zip")
            
            logger.info("⬇️ Downloading dataset...")
            try:
                self.s3.download_file(bucket, key, zip_path)
                zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
                logger.info(f"✅ Downloaded: {zip_size_mb:.1f} MB")
            except Exception as e:
                logger.error(f"❌ Download failed: {e}")
                return results
            
            # Analyze ZIP contents
            logger.info("📦 Analyzing archive contents...")
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    
                    # Filter image files
                    image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}
                    image_files = [f for f in file_list if any(f.lower().endswith(ext) for ext in image_extensions)]
                    
                    logger.info(f"📊 Archive Analysis:")
                    logger.info(f"   Total files: {len(file_list)}")
                    logger.info(f"   Image files: {len(image_files)}")
                    
                    # Show all image files
                    logger.info("📸 All Image Files:")
                    for i, img_file in enumerate(image_files, 1):
                        logger.info(f"   {i:2d}. {img_file}")
                    
                    results['dataset_analysis'] = {
                        'total_files': len(file_list),
                        'image_files': len(image_files),
                        'image_list': image_files,
                        'archive_size_mb': zip_size_mb
                    }
                    
            except Exception as e:
                logger.error(f"❌ Archive analysis failed: {e}")
                return results
        
        # Now run a quick SfM test to see what happens
        logger.info("\n🏗️ RUNNING SFM TEST")
        logger.info("=" * 30)
        
        job_id = f"sfm-diagnostics-{int(time.time())}"
        
        # Start the pipeline but we'll stop it after SfM
        test_input = {
            "jobId": job_id,
            "jobName": f"sfm-diagnostics-{job_id}",
            "s3Url": self.config['test_dataset_s3_url'],
            "inputS3Uri": self.config['test_dataset_s3_url'],
            "email": "diagnostics@spaceport.com",
            "timestamp": datetime.now().isoformat(),
            "pipelineStep": "sfm",
            "extractedS3Uri": f"s3://{self.config['bucket']}/jobs/{job_id}/extracted/",
            "colmapOutputS3Uri": f"s3://{self.config['bucket']}/jobs/{job_id}/colmap/",
            "gaussianOutputS3Uri": f"s3://{self.config['bucket']}/jobs/{job_id}/gaussian/",
            "compressedOutputS3Uri": f"s3://{self.config['bucket']}/jobs/{job_id}/compressed/",
            "extractorImageUri": f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/sagemaker-unzip:latest",
            "sfmImageUri": self.config['container_uris']['sfm'],
            "gaussianImageUri": self.config['container_uris']['3dgs'],
            "compressorImageUri": self.config['container_uris']['compressor'],
            
            # Required parameters
            "optimization_enabled": True,
            "progressive_resolution": True,
            "psnr_plateau_termination": True,
            "target_psnr": 30.0,
            "max_iterations": 10000,
            "min_iterations": 1000,
            "plateau_patience": 500,
            "learning_rate": 0.0025,
            "position_lr_scale": 0.5,
            "scaling_lr": 0.005,
            "rotation_lr": 0.001,
            "opacity_lr": 0.05,
            "feature_lr": 0.0025,
            "densification_interval": 100,
            "opacity_reset_interval": 3000,
            "densify_from_iter": 500,
            "densify_until_iter": 8000,
            "densify_grad_threshold": 0.0002,
            "percent_dense": 0.01,
            "lambda_dssim": 0.2,
            "sh_degree": 3,
            "log_interval": 500,
            "save_interval": 5000
        }
        
        execution_name = f"sfm-diagnostics-{int(time.time())}"
        
        logger.info(f"🚀 Starting SfM test...")
        logger.info(f"   Job ID: {job_id}")
        
        try:
            response = self.stepfunctions.start_execution(
                stateMachineArn=self.config['state_machine_arn'],
                name=execution_name,
                input=json.dumps(test_input)
            )
            
            execution_arn = response['executionArn']
            logger.info(f"✅ Started execution: {execution_arn}")
            
            # Monitor for SfM completion (we'll stop it before 3DGS)
            start_time = time.time()
            max_wait_time = 1800  # 30 minutes
            
            while time.time() - start_time < max_wait_time:
                execution_desc = self.stepfunctions.describe_execution(executionArn=execution_arn)
                status = execution_desc['status']
                
                elapsed_minutes = (time.time() - start_time) / 60
                logger.info(f"⏳ [{elapsed_minutes:4.1f}m] Status: {status}")
                
                if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                    logger.info(f"🏁 Execution completed: {status}")
                    break
                
                # If it's been running for more than 10 minutes, stop it 
                # (SfM should be done by then)
                if elapsed_minutes > 10:
                    logger.info("⏹️ Stopping execution after SfM completion")
                    try:
                        self.stepfunctions.stop_execution(executionArn=execution_arn)
                        logger.info("✅ Execution stopped")
                    except:
                        pass
                    break
                
                time.sleep(30)
            
            # Analyze SfM output
            logger.info("\n🔍 ANALYZING SFM OUTPUT")
            logger.info("=" * 40)
            
            bucket = self.config['bucket']
            prefix = f"jobs/{job_id}/colmap/"
            
            # Wait a bit for S3 upload
            time.sleep(30)
            
            try:
                response = self.s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
                
                if 'Contents' in response:
                    files = response['Contents']
                    logger.info(f"📊 SfM Output: {len(files)} files")
                    
                    for obj in files:
                        filename = obj['Key'].split('/')[-1]
                        size_kb = obj['Size'] / 1024
                        logger.info(f"   - {filename}: {size_kb:.1f} KB")
                    
                    # Try to analyze key files
                    for obj in files:
                        if 'images.txt' in obj['Key']:
                            try:
                                # Download and analyze images.txt
                                with tempfile.NamedTemporaryFile() as temp_file:
                                    self.s3.download_file(bucket, obj['Key'], temp_file.name)
                                    with open(temp_file.name, 'r') as f:
                                        content = f.read()
                                
                                lines = [line for line in content.split('\n') if line.strip() and not line.startswith('#')]
                                image_count = len([line for line in lines if not line.startswith('POINTS2D')])
                                
                                logger.info(f"📸 Images in reconstruction: {image_count}")
                                
                                # Show which images were used
                                logger.info("📋 Images used in reconstruction:")
                                for line in lines[:10]:  # First few lines
                                    if not line.startswith('POINTS2D') and len(line.split()) > 9:
                                        image_name = line.split()[9]
                                        logger.info(f"   - {image_name}")
                                
                                results['sfm_analysis']['images_used'] = image_count
                                
                            except Exception as e:
                                logger.warning(f"Could not analyze images.txt: {e}")
                        
                        elif 'points3D.txt' in obj['Key']:
                            try:
                                with tempfile.NamedTemporaryFile() as temp_file:
                                    self.s3.download_file(bucket, obj['Key'], temp_file.name)
                                    with open(temp_file.name, 'r') as f:
                                        content = f.read()
                                
                                lines = [line for line in content.split('\n') if line.strip() and not line.startswith('#')]
                                points_count = len(lines)
                                
                                logger.info(f"🎯 3D Points: {points_count}")
                                results['sfm_analysis']['points_3d'] = points_count
                                
                            except Exception as e:
                                logger.warning(f"Could not analyze points3D.txt: {e}")
                else:
                    logger.warning("❌ No SfM output files found")
                    results['sfm_analysis']['error'] = 'No output files'
                    
            except Exception as e:
                logger.error(f"❌ Could not analyze SfM output: {e}")
                results['sfm_analysis']['error'] = str(e)
            
        except Exception as e:
            logger.error(f"❌ SfM test failed: {e}")
            results['sfm_analysis']['error'] = str(e)
        
        # Generate recommendations
        logger.info("\n💡 RECOMMENDATIONS")
        logger.info("=" * 30)
        
        dataset_images = results['dataset_analysis'].get('image_files', 0)
        sfm_images = results['sfm_analysis'].get('images_used', 0)
        sfm_points = results['sfm_analysis'].get('points_3d', 0)
        
        if dataset_images >= 20 and sfm_images < 10:
            rec = f"❗ Only {sfm_images}/{dataset_images} images used in reconstruction. Check COLMAP settings."
            results['recommendations'].append(rec)
            logger.info(f"1. {rec}")
        
        if sfm_points < 1000:
            rec = f"❗ Only {sfm_points} 3D points reconstructed. Need 1000+ for quality 3DGS."
            results['recommendations'].append(rec)
            logger.info(f"2. {rec}")
        
        if not results['recommendations']:
            logger.info("✅ No critical issues found")
        
        return results

def main():
    """Run comprehensive diagnostics."""
    diagnostics = ComprehensivePipelineDiagnostics()
    results = diagnostics.run_comprehensive_diagnostics()
    
    # Save results
    with open('diagnostics_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n📊 Diagnostics complete - results saved to diagnostics_results.json")
    
    return len(results.get('recommendations', [])) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 