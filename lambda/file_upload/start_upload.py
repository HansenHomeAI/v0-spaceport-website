import json
import os
import boto3
import uuid
from datetime import datetime

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Get environment variables
bucket_name = os.environ.get('BUCKET_NAME')
metadata_table_name = os.environ.get('METADATA_TABLE_NAME')
metadata_table = dynamodb.Table(metadata_table_name)

def handler(event, context):
    """
    Lambda function to start a multipart upload process in S3.
    
    This function creates a new multipart upload in S3 and returns
    the upload ID and object key to the client.
    """
    try:
        # Parse the request body
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        
        # Extract required fields
        property_title = body.get('propertyTitle', '')
        email = body.get('email', '')
        file_name = body.get('fileName', '')
        file_type = body.get('fileType', 'application/zip')
        
        # Generate a unique object key
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        sanitized_title = ''.join(c if c.isalnum() else '_' for c in property_title)
        object_key = f"uploads/{email}/{sanitized_title}_{timestamp}_{unique_id}/{file_name}"
        
        # Create a multipart upload in S3
        response = s3_client.create_multipart_upload(
            Bucket=bucket_name,
            Key=object_key,
            ContentType=file_type,
            Metadata={
                'email': email,
                'propertyTitle': property_title
            }
        )
        
        # Return the upload ID and object information
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'uploadId': response['UploadId'],
                'bucketName': bucket_name,
                'objectKey': object_key
            })
        }
        
    except Exception as e:
        # Log error and return error response
        print(f"Error starting multipart upload: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            })
        } 