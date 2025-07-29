#!/usr/bin/env python3
"""
Simple diagnostic test for the SOGS compression container
Tests basic functionality without full compression
"""

import boto3
import time
import logging
from typing import Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class ContainerDiagnostics:
    def __init__(self, region='us-west-2'):
        self.region = region
        self.sagemaker = boto3.client('sagemaker', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        
    def test_container_startup(self) -> Dict:
        """Test if container can start and run basic commands"""
        logger.info("🚀 Testing container startup and basic functionality")
        
        job_name = f"container-diagnostics-{int(time.time())}"
        
        try:
            # Create a simple processing job that just runs diagnostics
            response = self.sagemaker.create_processing_job(
                ProcessingJobName=job_name,
                RoleArn='arn:aws:iam::975050048887:role/SpaceportMLPipelineStack-SageMakerExecutionRole7843-A4BBnjJAXLs8',
                AppSpecification={
                    'ImageUri': '975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor:latest',
                    'ContainerEntrypoint': [
                        'python3',
                        '/opt/ml/code/diagnostic_script.py'
                    ]
                },
                ProcessingResources={
                    'ClusterConfig': {
                        'InstanceCount': 1,
                        'InstanceType': 'ml.g4dn.xlarge',
                        'VolumeSizeInGB': 30
                    }
                },
                ProcessingOutputConfig={
                    'Outputs': [{
                        'OutputName': 'diagnostics',
                        'S3Output': {
                            'S3Uri': f's3://spaceport-ml-processing/diagnostics/{job_name}/',
                            'LocalPath': '/opt/ml/processing/output',
                            'S3UploadMode': 'EndOfJob'
                        }
                    }]
                },
                StoppingCondition={
                    'MaxRuntimeInSeconds': 300
                }
            )
            
            logger.info(f"✅ Diagnostic job created: {job_name}")
            logger.info(f"ARN: {response['ProcessingJobArn']}")
            
            # Monitor the job
            return self._monitor_diagnostic_job(job_name)
            
        except Exception as e:
            logger.error(f"❌ Failed to create diagnostic job: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def _monitor_diagnostic_job(self, job_name: str) -> Dict:
        """Monitor diagnostic job progress"""
        logger.info(f"⏱️  Monitoring diagnostic job: {job_name}")
        
        start_time = time.time()
        max_wait_time = 300  # 5 minutes
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.sagemaker.describe_processing_job(ProcessingJobName=job_name)
                status = response['ProcessingJobStatus']
                
                elapsed = int(time.time() - start_time)
                logger.info(f"📊 Status: {status} | Elapsed: {elapsed}s")
                
                if status == 'Completed':
                    logger.info("✅ Diagnostic job completed successfully!")
                    return self._analyze_diagnostic_results(response)
                
                elif status == 'Failed':
                    failure_reason = response.get('FailureReason', 'Unknown error')
                    logger.error(f"❌ Diagnostic job failed: {failure_reason}")
                    return {'status': 'failed', 'error': failure_reason}
                
                elif status in ['Stopping', 'Stopped']:
                    logger.error(f"❌ Diagnostic job was stopped: {status}")
                    return {'status': 'stopped'}
                
                # Wait before next check
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"❌ Error monitoring job: {e}")
                raise
        
        logger.error("❌ Diagnostic job timed out")
        return {'status': 'timeout'}
    
    def _analyze_diagnostic_results(self, job_response: Dict) -> Dict:
        """Analyze diagnostic results"""
        logger.info("📊 Analyzing diagnostic results...")
        
        # Get output S3 location
        output_config = job_response['ProcessingOutputConfig']['Outputs'][0]['S3Output']
        output_s3_uri = output_config['S3Uri']
        
        logger.info(f"📁 Output location: {output_s3_uri}")
        
        try:
            # Parse S3 URI
            bucket = output_s3_uri.split('/')[2]
            prefix = '/'.join(output_s3_uri.split('/')[3:])
            
            # List output files
            response = self.s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            
            if 'Contents' not in response:
                logger.error("❌ No output files found")
                return {'status': 'failed', 'error': 'No output files'}
            
            files = response['Contents']
            logger.info(f"📁 Found {len(files)} output files")
            
            for file_obj in files:
                file_key = file_obj['Key']
                file_size = file_obj['Size']
                logger.info(f"  📄 {file_key} ({file_size} bytes)")
                
                # Download and display log files
                if file_key.endswith('.txt') or file_key.endswith('.log'):
                    try:
                        response = self.s3.get_object(Bucket=bucket, Key=file_key)
                        content = response['Body'].read().decode('utf-8')
                        logger.info(f"📋 Content of {file_key}:")
                        logger.info(content)
                    except Exception as e:
                        logger.error(f"❌ Error reading {file_key}: {e}")
            
            return {'status': 'success', 'output_s3_uri': output_s3_uri}
            
        except Exception as e:
            logger.error(f"❌ Error analyzing results: {e}")
            return {'status': 'failed', 'error': str(e)}

def main():
    """Main function"""
    logger.info("🚀 STARTING CONTAINER DIAGNOSTICS")
    logger.info("=" * 60)
    
    diagnostics = ContainerDiagnostics()
    results = diagnostics.test_container_startup()
    
    logger.info("🏁 CONTAINER DIAGNOSTICS COMPLETE")
    logger.info("=" * 60)
    
    if results['status'] == 'success':
        logger.info("✅ SUCCESS: Container diagnostics completed")
    else:
        logger.error(f"❌ FAILED: {results.get('error', 'Unknown error')}")
    
    return results

if __name__ == "__main__":
    main() 