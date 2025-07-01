import json
import boto3
import os
from botocore.exceptions import ClientError

# Initialize S3 client
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    Generate presigned URL for CSV file upload
    """
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        file_name = body.get('fileName')
        file_type = body.get('fileType', 'text/csv')
        object_key = body.get('objectKey')
        
        if not file_name or not object_key:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Missing required fields: fileName and objectKey'
                })
            }
        
        # Get ML bucket name from environment
        ml_bucket = os.environ['ML_BUCKET']
        
        # Generate presigned URL for PUT operation
        try:
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': ml_bucket,
                    'Key': object_key,
                    'ContentType': file_type
                },
                ExpiresIn=300  # 5 minutes
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'url': presigned_url,
                    'objectKey': object_key,
                    'bucket': ml_bucket
                })
            }
            
        except ClientError as e:
            print(f"Error generating presigned URL: {e}")
            return {
                'statusCode': 500,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Failed to generate upload URL'
                })
            }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        } 