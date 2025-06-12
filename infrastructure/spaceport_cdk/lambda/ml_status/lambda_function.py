import json
import boto3
import os
from datetime import datetime

# Initialize AWS clients
stepfunctions = boto3.client('stepfunctions')

def lambda_handler(event, context):
    """
    Lambda function to get ML processing pipeline status
    Expects: GET /api/ml-pipeline/status/{jobId}
    Returns: { "status": "...", "currentStage": "...", "details": "..." }
    """
    
    try:
        # Extract job ID from path parameters
        job_id = event.get('pathParameters', {}).get('jobId')
        
        if not job_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Missing job ID in path parameters'
                })
            }
        
        # Get environment variables
        state_machine_arn = os.environ.get('STATE_MACHINE_ARN')
        if not state_machine_arn:
            raise ValueError("STATE_MACHINE_ARN environment variable not set")
        
        # Construct execution ARN from job ID
        execution_arn = f"{state_machine_arn.replace(':stateMachine:', ':execution:')}:execution-{job_id}"
        
        # Get execution status
        try:
            response = stepfunctions.describe_execution(
                executionArn=execution_arn
            )
        except stepfunctions.exceptions.ExecutionDoesNotExist:
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Job not found'
                })
            }
        
        # Parse execution status
        status = response['status']  # RUNNING, SUCCEEDED, FAILED, TIMED_OUT, ABORTED
        start_time = response['startDate']
        
        # Get detailed execution history to determine current stage
        history_response = stepfunctions.get_execution_history(
            executionArn=execution_arn,
            maxResults=100,
            reverseOrder=True  # Get most recent events first
        )
        
        current_stage, details = parse_execution_history(history_response['events'], status)
        
        # Calculate elapsed time
        elapsed_seconds = (datetime.now(start_time.tzinfo) - start_time).total_seconds()
        
        # Estimate completion time based on current stage
        completion_estimate = estimate_completion_time(current_stage, elapsed_seconds)
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET, OPTIONS'
            },
            'body': json.dumps({
                'jobId': job_id,
                'status': status,
                'currentStage': current_stage,
                'details': details,
                'startTime': start_time.isoformat(),
                'elapsedSeconds': int(elapsed_seconds),
                'estimatedCompletionSeconds': completion_estimate
            })
        }
        
    except Exception as e:
        print(f"Error getting ML pipeline status: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET, OPTIONS'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }

def parse_execution_history(events, status):
    """
    Parse Step Functions execution history to determine current stage
    """
    if status == 'SUCCEEDED':
        return 'completed', 'Processing completed successfully'
    
    if status == 'FAILED':
        # Find the failure reason
        for event in events:
            if event['type'] == 'ExecutionFailed':
                return 'failed', event.get('executionFailedEventDetails', {}).get('error', 'Unknown error')
        return 'failed', 'Processing failed'
    
    if status != 'RUNNING':
        return 'unknown', f'Status: {status}'
    
    # Analyze recent events to determine current stage
    stage_keywords = {
        'sfm': ['SfMProcessingJob', 'sfm', 'colmap'],
        '3dgs': ['GaussianTrainingJob', '3dgs', 'gaussian', 'training'],
        'compression': ['CompressionJob', 'compression', 'sogs']
    }
    
    current_stage = 'starting'
    details = 'Initializing pipeline...'
    
    for event in events:
        event_type = event['type']
        
        if 'StateEntered' in event_type or 'TaskStateEntered' in event_type:
            state_name = event.get('stateEnteredEventDetails', {}).get('name', '') or \
                        event.get('taskStateEnteredEventDetails', {}).get('name', '')
            
            # Determine stage from state name
            for stage, keywords in stage_keywords.items():
                if any(keyword.lower() in state_name.lower() for keyword in keywords):
                    current_stage = stage
                    details = f"Running {state_name}..."
                    break
        
        elif 'TaskStateSucceeded' in event_type:
            state_name = event.get('taskStateSucceededEventDetails', {}).get('name', '')
            
            # Check if a major stage just completed
            for stage, keywords in stage_keywords.items():
                if any(keyword.lower() in state_name.lower() for keyword in keywords):
                    if stage == 'sfm':
                        current_stage = '3dgs'
                        details = 'Starting 3D Gaussian Splatting training...'
                    elif stage == '3dgs':
                        current_stage = 'compression'
                        details = 'Starting model compression...'
                    break
    
    return current_stage, details

def estimate_completion_time(current_stage, elapsed_seconds):
    """
    Estimate remaining completion time based on current stage and elapsed time
    """
    stage_durations = {
        'starting': 60,      # 1 minute
        'sfm': 360,          # 6 minutes
        '3dgs': 360,         # 6 minutes  
        'compression': 60,   # 1 minute
        'completed': 0
    }
    
    total_expected = sum(stage_durations.values())
    
    if current_stage == 'completed':
        return 0
    
    # Calculate time spent in previous stages
    stages_order = ['starting', 'sfm', '3dgs', 'compression']
    current_index = stages_order.index(current_stage) if current_stage in stages_order else 0
    
    time_for_previous_stages = sum(stage_durations[stage] for stage in stages_order[:current_index])
    time_for_remaining_stages = sum(stage_durations[stage] for stage in stages_order[current_index + 1:])
    
    # Estimate remaining time for current stage
    current_stage_duration = stage_durations.get(current_stage, 300)
    time_in_current_stage = elapsed_seconds - time_for_previous_stages
    remaining_in_current = max(0, current_stage_duration - time_in_current_stage)
    
    return int(remaining_in_current + time_for_remaining_stages) 