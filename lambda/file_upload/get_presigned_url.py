import json
import os
import boto3

# Initialize AWS clients
s3_client = boto3.client('s3')

# Get environment variables
bucket_name = os.environ.get('BUCKET_NAME')

def handler(event, context):
    """
    Lambda function to generate a presigned URL for a specific upload part.
    
    This function creates a presigned URL that allows the client to upload
    a part directly to S3 without needing AWS credentials.
    """
    try:
        # Parse the request body
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        
        # Extract required parameters
        upload_id = body.get('uploadId')
        part_number = body.get('partNumber')
        object_key = body.get('objectKey')
        bucket = body.get('bucketName', bucket_name)
        
        # Validate parameters
        if not upload_id or not part_number or not object_key:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing required parameters'
                })
            }
        
        # Generate a presigned URL for the part upload
        presigned_url = s3_client.generate_presigned_url(
            'upload_part',
            Params={
                'Bucket': bucket,
                'Key': object_key,
                'UploadId': upload_id,
                'PartNumber': part_number
            },
            ExpiresIn=3600  # URL valid for 1 hour
        )
        
        # Return the presigned URL
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'url': presigned_url
            })
        }
        
    except Exception as e:
        # Log error and return error response
        print(f"Error generating presigned URL: {str(e)}")
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