import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ['WAITLIST_TABLE_NAME']
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    """
    Handle waitlist submissions and store them in DynamoDB
    """
    
    # Handle OPTIONS request for CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({'message': 'CORS preflight'})
        }
    
    try:
        # Parse the request body
        if isinstance(event['body'], str):
            body = json.loads(event['body'])
        else:
            body = event['body']
        
        # Extract data from the request
        name = body.get('name', '').strip()
        email = body.get('email', '').strip().lower()
        
        # Validate required fields
        if not name or not email:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Name and email are required'
                })
            }
        
        # Basic email validation
        if '@' not in email or '.' not in email:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'Please provide a valid email address'
                })
            }
        
        # Check if email already exists
        try:
            response = table.get_item(
                Key={
                    'email': email
                }
            )
            
            if 'Item' in response:
                return {
                    'statusCode': 409,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Methods': 'POST, OPTIONS'
                    },
                    'body': json.dumps({
                        'error': 'This email is already on the waitlist'
                    })
                }
        except ClientError as e:
            print(f"Error checking existing email: {e}")
        
        # Create timestamp
        timestamp = datetime.utcnow().isoformat()
        
        # Store in DynamoDB
        item = {
            'email': email,
            'name': name,
            'timestamp': timestamp,
            'source': 'website',
            'status': 'active'
        }
        
        table.put_item(Item=item)
        
        # Optional: Send notification email to admin
        try:
            send_admin_notification(name, email)
        except Exception as e:
            print(f"Failed to send admin notification: {e}")
            # Don't fail the request if notification fails
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'message': 'Successfully added to waitlist',
                'email': email
            })
        }
        
    except Exception as e:
        print(f"Error processing waitlist submission: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'error': 'Internal server error'
            })
        }

def send_admin_notification(name, email):
    """
    Send notification email to admin about new waitlist signup
    """
    ses = boto3.client('ses')
    
    subject = 'New Waitlist Signup - Spaceport AI'
    body_text = f"""New waitlist signup:
    
Name: {name}
Email: {email}
Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

This person will be notified when Spaceport AI launches."""

    body_html = f"""<html>
<head></head>
<body>
    <h2>New Waitlist Signup</h2>
    <p><strong>Name:</strong> {name}</p>
    <p><strong>Email:</strong> {email}</p>
    <p><strong>Date:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    <p>This person will be notified when Spaceport AI launches.</p>
</body>
</html>"""

    try:
        response = ses.send_email(
            Source='gabriel@spcprt.com',  # Your preferred email address
            Destination={
                'ToAddresses': ['gabriel@spcprt.com']
            },
            Message={
                'Subject': {
                    'Data': subject
                },
                'Body': {
                    'Text': {
                        'Data': body_text
                    },
                    'Html': {
                        'Data': body_html
                    }
                }
            }
        )
        print(f"Admin notification sent: {response['MessageId']}")
    except ClientError as e:
        print(f"Failed to send admin notification: {e}")
        raise 