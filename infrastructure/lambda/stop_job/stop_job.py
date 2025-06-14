import json
import boto3
import os
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    """
    Lambda function to stop ML processing jobs
    """
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'CORS preflight'})
        }
    
    try:
        # Parse request body
        if 'body' not in event:
            raise ValueError("Request body is required")
            
        body = json.loads(event['body'])
        job_id = body.get('jobId')
        execution_arn = body.get('executionArn')
        
        if not job_id or not execution_arn:
            raise ValueError("Both jobId and executionArn are required")
        
        # Initialize AWS clients
        stepfunctions = boto3.client('stepfunctions')
        sagemaker = boto3.client('sagemaker')
        
        stopped_resources = []
        
        # Stop Step Functions execution
        try:
            stepfunctions.stop_execution(
                executionArn=execution_arn,
                error="UserRequested",
                cause="User requested to stop the processing"
            )
            stopped_resources.append("Step Functions execution")
            print(f"✅ Stopped Step Functions execution: {execution_arn}")
        except ClientError as e:
            if e.response['Error']['Code'] != 'ExecutionDoesNotExist':
                print(f"⚠️ Error stopping Step Functions: {e}")
        
        # Stop any running SageMaker jobs related to this job_id
        try:
            # List and stop training jobs
            training_jobs = sagemaker.list_training_jobs(
                StatusEquals='InProgress',
                MaxResults=100
            )
            
            for job in training_jobs['TrainingJobSummaries']:
                if job_id in job['TrainingJobName']:
                    sagemaker.stop_training_job(
                        TrainingJobName=job['TrainingJobName']
                    )
                    stopped_resources.append(f"Training job: {job['TrainingJobName']}")
                    print(f"✅ Stopped training job: {job['TrainingJobName']}")
            
            # List and stop processing jobs
            processing_jobs = sagemaker.list_processing_jobs(
                StatusEquals='InProgress',
                MaxResults=100
            )
            
            for job in processing_jobs['ProcessingJobSummaries']:
                if job_id in job['ProcessingJobName']:
                    sagemaker.stop_processing_job(
                        ProcessingJobName=job['ProcessingJobName']
                    )
                    stopped_resources.append(f"Processing job: {job['ProcessingJobName']}")
                    print(f"✅ Stopped processing job: {job['ProcessingJobName']}")
                    
        except ClientError as e:
            print(f"⚠️ Error stopping SageMaker jobs: {e}")
        
        # Success response
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': 'Processing stopped successfully',
                'jobId': job_id,
                'stoppedResources': stopped_resources
            })
        }
        
    except ValueError as e:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
        
    except Exception as e:
        print(f"❌ Error stopping job: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'success': False,
                'error': 'Internal server error'
            })
        } 