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
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Credentials': 'true'
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
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS',
                    'Access-Control-Allow-Credentials': 'true'
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
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS',
                    'Access-Control-Allow-Credentials': 'true'
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
                        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
                        'Access-Control-Allow-Methods': 'POST,OPTIONS',
                        'Access-Control-Allow-Credentials': 'true'
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
        
        # Send confirmation email to the user
        try:
            send_confirmation_email(name, email)
        except Exception as e:
            print(f"Failed to send confirmation email: {e}")
            # Don't fail the request if confirmation email fails
        
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
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Credentials': 'true'
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
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({
                'error': 'Internal server error'
            })
        }

def send_confirmation_email(name, email):
    """
    Send confirmation email to new waitlist signup
    """
    ses = boto3.client('ses')
    
    subject = 'Welcome to Spaceport AI - You\'re on the Waitlist!'
    
    body_text = f"""Hi {name},

This is Gabriel, the founder of Spaceport AI. Thanks for signing up for our waitlist!

We're excited about your interest in our 3D reconstruction and drone path optimization platform. You'll be among the first to know when we launch and get early access to our features.

Stay tuned for updates on:
• 3D Gaussian Splatting reconstruction
• Drone path optimization
• Real-time 3D visualization
• And much more!

Best regards,
Gabriel
Founder, Spaceport AI

---
You can unsubscribe from these emails by replying with "unsubscribe"."""

    body_html = f"""<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .signature {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #666; text-align: center; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Welcome to Spaceport AI</h1>
        <p>You're on the waitlist!</p>
    </div>
    
    <div class="content">
        <p>Hi {name},</p>
        
        <p>This is Gabriel, the founder of Spaceport AI. Thanks for signing up for our waitlist!</p>
        
        <p>We're excited about your interest in our 3D reconstruction and drone path optimization platform. You'll be among the first to know when we launch and get early access to our features.</p>
        
        <p><strong>Stay tuned for updates on:</strong></p>
        <ul>
            <li>3D Gaussian Splatting reconstruction</li>
            <li>Drone path optimization</li>
            <li>Real-time 3D visualization</li>
            <li>And much more!</li>
        </ul>
        
        <div class="signature">
            <p><strong>Best regards,</strong><br>
            Gabriel<br>
            Founder, Spaceport AI</p>
        </div>
    </div>
    
    <div class="footer">
        <p>You can unsubscribe from these emails by replying with "unsubscribe".</p>
    </div>
</body>
</html>"""

    try:
        response = ses.send_email(
            Source='gabriel@spcprt.com',
            Destination={
                'ToAddresses': [email]
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
        print(f"Confirmation email sent to {email}: {response['MessageId']}")
    except ClientError as e:
        print(f"Failed to send confirmation email to {email}: {e}")
        raise

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