import json
import os
import boto3
from datetime import datetime

def handler(event, context):
    """
    Lambda handler for drone path generation.
    """
    # For preflight CORS requests
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': ''
        }
    
    try:
        # Parse input from event
        body = json.loads(event.get('body', '{}'))
        
        # Log request for debugging
        print(f"Received request: {json.dumps(body)}")
        
        # Get table name from environment variable
        table_name = os.environ.get('DYNAMODB_TABLE_NAME')
        
        # Create a mock response for now
        result = {
            'message': 'Drone path generation placeholder',
            'requestReceived': body,
            'timestamp': datetime.now().isoformat()
        }
        
        # Return successful response
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': str(e)
            })
        } 