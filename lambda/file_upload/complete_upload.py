import json
import os
import boto3

# Initialize AWS clients
s3_client = boto3.client('s3')

# Get environment variables
bucket_name = os.environ.get('BUCKET_NAME')

def handler(event, context):
    """
    Lambda function to complete a multipart upload.
    
    This function finalizes the multipart upload process by combining
    all uploaded parts into a single object in S3.
    """
    try:
        # Parse the request body
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        
        # Extract required parameters
        upload_id = body.get('uploadId')
        object_key = body.get('objectKey')
        parts = body.get('parts', [])
        bucket = body.get('bucketName', bucket_name)
        
        # Validate parameters
        if not upload_id or not object_key or not parts:
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
        
        # Prepare the parts list in the format required by S3
        multipart_parts = []
        for part in parts:
            multipart_parts.append({
                'PartNumber': part['PartNumber'],
                'ETag': part['ETag'].strip('"')  # Remove quotes if present
            })
        
        # Complete the multipart upload
        response = s3_client.complete_multipart_upload(
            Bucket=bucket,
            Key=object_key,
            UploadId=upload_id,
            MultipartUpload={
                'Parts': sorted(multipart_parts, key=lambda x: x['PartNumber'])
            }
        )
        
        # Return success response with S3 object details
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'location': response.get('Location', ''),
                'bucket': response.get('Bucket', bucket),
                'key': response.get('Key', object_key),
                'etag': response.get('ETag', ''),
                'completeUpload': True
            })
        }
        
    except Exception as e:
        # Log error and return error response
        print(f"Error completing multipart upload: {str(e)}")
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