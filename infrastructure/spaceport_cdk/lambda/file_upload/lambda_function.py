import json
import boto3
import os
import random
import string
import time
from botocore.exceptions import ClientError
from urllib.parse import urlparse
import requests
from botocore.config import Config

# Initialize AWS clients
# Force regional, SigV4, virtual-hosted style URLs to avoid cross-region redirects
AWS_REGION = os.environ.get('AWS_REGION', 'us-west-2')
s3_client = boto3.client(
    's3',
    region_name=AWS_REGION,
    endpoint_url=f'https://s3.{AWS_REGION}.amazonaws.com',
    config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'})
)
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')

# Environment variables from CDK
UPLOAD_BUCKET = os.environ.get('UPLOAD_BUCKET')
FILE_METADATA_TABLE = os.environ.get('FILE_METADATA_TABLE')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')

def send_email_notification(to_address, subject, body_text, body_html=None):
    """Send email notification using Resend API"""
    if not RESEND_API_KEY:
        print("Warning: RESEND_API_KEY not configured")
        return
        
    url = "https://api.resend.com/emails"
    
    payload = {
        "from": "Spaceport AI <hello@spcprt.com>",
        "to": [to_address],
        "subject": subject,
        "text": body_text
    }
    
    if body_html:
        payload["html"] = body_html
    
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending email: {e}")
        raise

def lambda_handler(event, context):
    print(f"Event received: {json.dumps(event)}")
    
    # Common CORS headers for all responses
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }
    
    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'OPTIONS request'})
        }
    
    # Parse request body
    try:
        if isinstance(event.get('body'), str):
            body = json.loads(event['body']) if event.get('body') else {}
        else:
            body = event.get('body', {})
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON body: {e}")
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON'})
        }
    
    path = event.get('resource') or event.get('path')
    print(f"Path: {path}")
    
    try:
        # ----------------------------------------------------------------------
        # 1) START MULTIPART UPLOAD
        #    POST /start-multipart-upload
        # ----------------------------------------------------------------------
        if path == '/start-multipart-upload':
            file_name = body.get('fileName')
            if not file_name:
                raise ValueError("Missing fileName")
            
            # Generate a random + timestamp-based key
            random_key_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            timestamp = int(time.time() * 1000)  # milliseconds
            final_key = f"{timestamp}-{random_key_part}-{file_name}"
            
            # Initiate multipart upload
            response = s3_client.create_multipart_upload(
                Bucket=UPLOAD_BUCKET,
                Key=final_key,
                ACL='bucket-owner-full-control'
            )
            
            print(f"Multipart upload initiated: {response}")
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'uploadId': response['UploadId'],
                    'bucketName': response['Bucket'],
                    'objectKey': response['Key']
                })
            }
        
        # ----------------------------------------------------------------------
        # 2) GET PRESIGNED URL FOR PART
        #    POST /get-presigned-url
        # ----------------------------------------------------------------------
        elif path == '/get-presigned-url':
            upload_id = body.get('uploadId')
            bucket_name = body.get('bucketName')
            object_key = body.get('objectKey')
            part_number = body.get('partNumber')
            
            if not all([upload_id, bucket_name, object_key, part_number]):
                raise ValueError("Missing uploadId, bucketName, objectKey, or partNumber")
            
            # Generate presigned URL for upload part
            url = s3_client.generate_presigned_url(
                'upload_part',
                Params={
                    'Bucket': bucket_name,
                    'Key': object_key,
                    'UploadId': upload_id,
                    'PartNumber': int(part_number)
                },
                ExpiresIn=3600  # 1 hour
            )
            
            print(f"Presigned URL for part {part_number}: {url}")
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'url': url,
                    'partNumber': part_number
                })
            }
        
        # ----------------------------------------------------------------------
        # 3) COMPLETE MULTIPART UPLOAD
        #    POST /complete-multipart-upload
        # ----------------------------------------------------------------------
        elif path == '/complete-multipart-upload':
            upload_id = body.get('uploadId')
            bucket_name = body.get('bucketName')
            object_key = body.get('objectKey')
            parts = body.get('parts')
            
            if not all([upload_id, bucket_name, object_key, parts]):
                raise ValueError("Missing one or more required fields to complete upload")
            
            # Sort parts by PartNumber ascending
            sorted_parts = sorted(parts, key=lambda x: x['PartNumber'])
            
            # Format parts for AWS API
            multipart_upload_parts = [
                {
                    'ETag': part['ETag'],
                    'PartNumber': part['PartNumber']
                }
                for part in sorted_parts
            ]
            
            # Complete multipart upload
            response = s3_client.complete_multipart_upload(
                Bucket=bucket_name,
                Key=object_key,
                UploadId=upload_id,
                MultipartUpload={'Parts': multipart_upload_parts}
            )
            
            print(f"Multipart upload completed: {response}")
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Upload complete',
                    'location': response['Location']
                })
            }
        
        # ----------------------------------------------------------------------
        # OPTIONAL: Single-part presigned URL (legacy support)
        # POST /generate-presigned-url
        # ----------------------------------------------------------------------
        elif path == '/generate-presigned-url':
            file_name = body.get('fileName')
            file_type = body.get('fileType')
            
            if not file_name or not file_type:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Missing fileName or fileType'})
                }
            
            # Generate random key
            random_key_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            timestamp = int(time.time() * 1000)
            final_key = f"{timestamp}-{random_key_part}-{file_name}"
            
            # Generate presigned URL for PUT operation
            url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': UPLOAD_BUCKET,
                    'Key': final_key,
                    'ContentType': file_type
                },
                ExpiresIn=300  # 5 minutes
            )
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({'url': url})
            }
        
        # ----------------------------------------------------------------------
        # 4) SAVE SUBMISSION METADATA (& Send Email Notifications)
        #     POST /save-submission
        # ----------------------------------------------------------------------
        elif path == '/save-submission':
            email = body.get('email')
            property_title = body.get('propertyTitle')
            listing_description = body.get('listingDescription')
            address_of_property = body.get('addressOfProperty')
            optional_notes = body.get('optionalNotes', '')
            object_key = body.get('objectKey')
            
            if not all([object_key, email, property_title]):
                raise ValueError("Missing required fields: objectKey, email, or propertyTitle")
            
            # Save to DynamoDB
            table = dynamodb.Table(FILE_METADATA_TABLE)
            item = {
                'id': object_key,  # using the unique S3 object key as primary key
                'Email': email,
                'PropertyTitle': property_title,
                'ListingDescription': listing_description or '',
                'Address': address_of_property or '',
                'OptionalNotes': optional_notes,
                'Timestamp': int(time.time() * 1000)
            }
            
            table.put_item(Item=item)
            print(f"Metadata saved to DynamoDB: {item}")
            
            # Send email notifications
            try:
                user_subject = "We've Received Your Drone Photos!"
                user_body = f"""Hello,

Thank you for your submission! We have received your photos and will start processing them soon.
Your upload ID is: {object_key}

Best,
The Spaceport Team
"""
                
                user_body_html = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                  <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2563eb;">We've Received Your Drone Photos!</h2>
                    
                    <p>Hello,</p>
                    
                    <p>Thank you for your submission! We have received your photos and will start processing them soon.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                      <p><strong>Upload ID:</strong> {object_key}</p>
                    </div>
                    
                    <p>Best regards,<br>The Spaceport Team</p>
                  </div>
                </body>
                </html>
                """
                
                admin_subject = "New Upload Received"
                admin_body = f"""New drone photo submission received:

Email: {email}
Property Title: {property_title}
Description: {listing_description}
Address: {address_of_property}
Optional Notes: {optional_notes}
Upload ID: {object_key}

Please process this submission accordingly."""
                
                admin_body_html = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                  <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #dc3545;">New Upload Received</h2>
                    
                    <p>New drone photo submission received:</p>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                      <p><strong>Email:</strong> {email}</p>
                      <p><strong>Property Title:</strong> {property_title}</p>
                      <p><strong>Description:</strong> {listing_description}</p>
                      <p><strong>Address:</strong> {address_of_property}</p>
                      <p><strong>Optional Notes:</strong> {optional_notes}</p>
                      <p><strong>Upload ID:</strong> {object_key}</p>
                    </div>
                    
                    <p>Please process this submission accordingly.</p>
                  </div>
                </body>
                </html>
                """
                
                # Send both emails
                send_email_notification(email, user_subject, user_body, user_body_html)
                send_email_notification("gabriel@spcprt.com", admin_subject, admin_body, admin_body_html)
                
                print("Email notifications sent via Resend.")
            except Exception as email_err:
                print(f"Error sending email notifications: {email_err}")
                # Not raising here, so we still return 200 if metadata was saved
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({'message': 'Submission saved successfully'})
            }
        
        # ----------------------------------------------------------------------
        # If none of the above matched, return 404
        # ----------------------------------------------------------------------
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'No matching path'})
            }
    
    except Exception as err:
        print(f"Error handling request: {err}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(err)})
        }
