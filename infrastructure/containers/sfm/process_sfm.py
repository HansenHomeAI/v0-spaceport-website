#!/usr/bin/env python3
"""
SfM Processing Script with S3 Integration
Downloads images from S3, runs COLMAP, uploads results
"""

import os
import sys
import json
import boto3
import subprocess
import zipfile
from pathlib import Path
from urllib.parse import urlparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SfMProcessor:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.input_dir = Path("/opt/ml/processing/input")
        self.output_dir = Path("/opt/ml/processing/output")
        self.workspace_dir = Path("/tmp/colmap_workspace")
        
        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def download_from_s3(self, s3_url):
        """Download images from S3 URL"""
        logger.info(f"Downloading from S3: {s3_url}")
        
        # Parse S3 URL
        parsed = urlparse(s3_url)
        bucket = parsed.netloc
        key = parsed.path.lstrip('/')
        
        logger.info(f"Bucket: {bucket}, Key: {key}")
        
        # Download file
        local_file = self.input_dir / Path(key).name
        self.s3_client.download_file(bucket, key, str(local_file))
        
        logger.info(f"Downloaded to: {local_file}")
        return local_file

    def extract_images(self, file_path):
        """Extract images from ZIP file or copy individual image"""
        logger.info(f"Processing file: {file_path}")
        
        images_dir = self.workspace_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        if file_path.suffix.lower() == '.zip':
            logger.info("Extracting ZIP file...")
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(images_dir)
        else:
            # Single image file
            import shutil
            shutil.copy2(file_path, images_dir)
        
        # Count images
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp'}
        image_files = [f for f in images_dir.rglob('*') 
                      if f.suffix.lower() in image_extensions]
        
        logger.info(f"Found {len(image_files)} images")
        return len(image_files)

    def run_colmap_processing(self):
        """Run the COLMAP processing script"""
        logger.info("Starting COLMAP processing...")
        
        script_path = "/opt/ml/code/run_sfm_fast.sh"
        result = subprocess.run([script_path], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"COLMAP processing failed: {result.stderr}")
            raise RuntimeError(f"COLMAP processing failed: {result.stderr}")
        
        logger.info("COLMAP processing completed successfully")
        return result.stdout

    def upload_results_to_s3(self, output_bucket, job_name):
        """Upload processing results to S3"""
        logger.info(f"Uploading results to S3: {output_bucket}")
        
        # Upload all files in output directory
        for file_path in self.output_dir.rglob('*'):
            if file_path.is_file():
                # Create S3 key with job name prefix
                relative_path = file_path.relative_to(self.output_dir)
                s3_key = f"sfm-results/{job_name}/{relative_path}"
                
                logger.info(f"Uploading: {file_path} -> s3://{output_bucket}/{s3_key}")
                self.s3_client.upload_file(str(file_path), output_bucket, s3_key)
        
        logger.info("Upload completed")

    def create_processing_metadata(self, job_name, image_count, processing_log):
        """Create metadata about the processing job"""
        metadata = {
            "job_name": job_name,
            "processing_type": "structure_from_motion",
            "input_image_count": image_count,
            "processing_status": "completed",
            "colmap_version": "3.7",
            "outputs": {
                "sparse_reconstruction": "sparse/",
                "dense_reconstruction": "dense/",
                "database": "database.db",
                "summary": "processing_summary.txt"
            },
            "processing_log": processing_log
        }
        
        metadata_file = self.output_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return metadata

def main():
    """Main processing function"""
    logger.info("🎯 Starting SfM Processing with COLMAP...")
    
    # Get environment variables
    s3_url = os.environ.get('S3_INPUT_URL')
    output_bucket = os.environ.get('OUTPUT_BUCKET')
    job_name = os.environ.get('JOB_NAME')
    
    if not all([s3_url, output_bucket, job_name]):
        logger.error("Missing required environment variables")
        logger.error(f"S3_INPUT_URL: {s3_url}")
        logger.error(f"OUTPUT_BUCKET: {output_bucket}")
        logger.error(f"JOB_NAME: {job_name}")
        return 1
    
    try:
        processor = SfMProcessor()
        
        # Step 1: Download images from S3
        downloaded_file = processor.download_from_s3(s3_url)
        
        # Step 2: Extract images
        image_count = processor.extract_images(downloaded_file)
        
        if image_count == 0:
            raise ValueError("No images found in input")
        
        # Step 3: Run COLMAP processing
        processing_log = processor.run_colmap_processing()
        
        # Step 4: Create metadata
        metadata = processor.create_processing_metadata(job_name, image_count, processing_log)
        
        # Step 5: Upload results to S3
        processor.upload_results_to_s3(output_bucket, job_name)
        
        logger.info("✅ SfM Processing completed successfully!")
        logger.info(f"Results uploaded to: s3://{output_bucket}/sfm-results/{job_name}/")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ SfM Processing failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 