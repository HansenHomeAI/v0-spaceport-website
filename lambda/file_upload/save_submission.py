import json
import os
import boto3
import uuid
from datetime import datetime

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Get environment variables
metadata_table_name = os.environ.get('METADATA_TABLE_NAME')
metadata_table = dynamodb.Table(metadata_table_name)

def handler(event, context):
    """
    Lambda function to save submission metadata to DynamoDB.
    
    This function stores metadata about the uploaded file in DynamoDB,
    including user information and file details.
    """
    try:
        # Parse the request body
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        
        # Extract metadata fields
        email = body.get('email', '')
        property_title = body.get('propertyTitle', '')
        listing_description = body.get('listingDescription', '')
        address_of_property = body.get('addressOfProperty', '')
        optional_notes = body.get('optionalNotes', '')
        object_key = body.get('objectKey', '')
        
        # Validate required fields
        if not email or not property_title or not object_key:
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
        
        # Generate a unique ID for this submission
        submission_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Store metadata in DynamoDB
        metadata_table.put_item(
            Item={
                'id': submission_id,
                'email': email,
                'propertyTitle': property_title,
                'listingDescription': listing_description,
                'addressOfProperty': address_of_property,
                'optionalNotes': optional_notes,
                'objectKey': object_key,
                'timestamp': timestamp,
                'status': 'received'
            }
        )
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'id': submission_id,
                'status': 'success',
                'message': 'Submission metadata saved successfully'
            })
        }
        
    except Exception as e:
        # Log error and return error response
        print(f"Error saving submission metadata: {str(e)}")
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