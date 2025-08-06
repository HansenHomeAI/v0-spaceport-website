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
        
        # Allow multiple entries with the same email for testing purposes
        # Commented out duplicate check to allow repeated testing
        # try:
        #     response = table.get_item(
        #         Key={
        #             'email': email
        #         }
        #     )
        #     
        #     if 'Item' in response:
        #         return {
        #             'statusCode': 409,
        #             'headers': {
        #                 'Access-Control-Allow-Origin': '*',
        #                 'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent',
        #                 'Access-Control-Allow-Methods': 'POST,OPTIONS',
        #                 'Access-Control-Allow-Credentials': 'true'
        #             },
        #             'body': json.dumps({
        #                 'error': 'This email is already on the waitlist'
        #             })
        #         }
        # except ClientError as e:
        #     print(f"Error checking existing email: {e}")
        
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
        body {{ font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f7; }}
        .container {{ background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); border: 3px solid rgba(128, 128, 128, 0.2); }}
        .logo {{ text-align: center; padding: 40px 30px 20px; }}
        .logo img {{ max-width: 200px; height: auto; }}
        .content {{ padding: 30px; }}
        .signature {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e5e7; }}
        .footer {{ padding: 20px 30px; font-size: 12px; color: #86868b; text-align: center; background-color: #f5f5f7; }}
        h1 {{ font-size: 28px; font-weight: 600; margin: 0 0 10px 0; color: #1d1d1f; }}
        p {{ margin: 0 0 16px 0; color: #1d1d1f; }}
        ul {{ margin: 16px 0; padding-left: 20px; }}
        li {{ margin: 8px 0; color: #1d1d1f; }}
        strong {{ font-weight: 600; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <img src="https://spaceport.ai/assets/SpaceportIcons/SpaceportColoredLogoFull.svg" alt="Spaceport AI" />
        </div>
        
        <div class="content">
            <h1>Welcome to Spaceport AI</h1>
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