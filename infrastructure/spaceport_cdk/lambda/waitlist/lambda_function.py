import json
import boto3
import os
import resend
from datetime import datetime
from botocore.exceptions import ClientError

# Initialize Resend
resend.api_key = os.environ.get('RESEND_API_KEY')

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ['WAITLIST_TABLE_NAME']
table = dynamodb.Table(table_name)

def _detect_invocation_source(event: dict) -> dict:
    """Best-effort detection of how this Lambda was invoked for auditability."""
    source: str = "unknown"
    details: dict = {}
    try:
        # API Gateway REST (v1) adds requestContext with identity
        if isinstance(event, dict) and 'requestContext' in event:
            rc = event.get('requestContext', {}) or {}
            if 'stage' in rc or 'identity' in rc:
                source = 'apigw-rest-v1'
                details = {
                    'httpMethod': event.get('httpMethod'),
                    'path': event.get('path'),
                    'stage': rc.get('stage'),
                    'sourceIp': (rc.get('identity') or {}).get('sourceIp'),
                    'userAgent': (rc.get('identity') or {}).get('userAgent'),
                }
        # API Gateway HTTP (v2) style
        elif isinstance(event, dict) and 'requestContext' in event and 'http' in event['requestContext']:
            http = event['requestContext'].get('http', {})
            source = 'apigw-http-v2'
            details = {
                'method': http.get('method'),
                'path': http.get('path'),
                'sourceIp': event['requestContext'].get('http', {}).get('sourceIp')
            }
        # Lambda Function URL adds requestContext with domainName starting with lambda-url
        elif isinstance(event, dict) and 'requestContext' in event and str(event['requestContext'].get('domainName','')).endswith('.lambda-url.us-west-2.on.aws'):
            source = 'lambda-function-url'
        # Console test or direct invoke usually lacks requestContext and httpMethod
        elif isinstance(event, dict) and 'httpMethod' not in event and 'requestContext' not in event:
            source = 'direct-invoke-or-console-test'
        # Fallback
        else:
            source = 'unknown'
    except Exception as _:
        source = 'unknown'
    return {'source': source, 'details': details}

def lambda_handler(event, context):
    """
    Handle waitlist submissions and store them in DynamoDB
    """
    
    # Trace invocation source for forensic evidence
    try:
        src = _detect_invocation_source(event)
        print(f"InvocationSource: {json.dumps(src)}")
    except Exception as e:
        print(f"InvocationSource detection error: {e}")

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
    
    subject = 'Welcome to Spaceport AI - You\'re on the Waitlist!'
    
    body_text = f"""Hi {name},

This is Gabriel, the founder of Spaceport AI. On behalf of our team, thanks for signing up for our waitlist!

You'll be among the first to know when we launch and get early access to our features. If selected, you'll have the option to become one of our early beta users.

Stay tuned for updates by following our socials!

Best regards,

Gabriel Hansen
Founder, CEO
Spaceport AI

Follow us:
Instagram: https://instagram.com/Spaceport_AI
Facebook: https://www.facebook.com/profile.php?id=61578856815066
LinkedIn: https://www.linkedin.com/company/spaceport-ai/

---
You can unsubscribe from these emails by replying with "unsubscribe"."""

    body_html = f"""<html>
<head>
    <style>
        body {{ font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f7; }}
        .container {{ background: white; border-radius: 25px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
        .logo {{ text-align: center; padding: 40px 30px 20px; }}
        .logo svg {{ max-width: 350px; height: auto; }}
        .content {{ padding: 30px; text-align: left; }}
        .signature {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e5e7; }}
        .social-links {{
            margin: 30px 0;
            text-align: center;
            display: flex;
            justify-content: center;
            gap: 30px;
        }}
        .social-text-link {{
            color: #007aff;
            text-decoration: none;
            font-weight: 500;
            font-size: 16px;
            transition: color 0.2s ease;
        }}
        .social-text-link:hover {{
            color: #0056cc;
            text-decoration: underline;
        }}
        .footer {{ padding: 20px 30px; font-size: 12px; color: #86868b; text-align: center; background-color: #f5f5f7; }}
        h1 {{ font-size: 28px; font-weight: 500; margin: 0 0 10px 0; color: #1d1d1f; }}
        p {{ margin: 0 0 16px 0; color: #1d1d1f; font-weight: 400; }}
        ul {{ margin: 16px 0; padding-left: 20px; }}
        li {{ margin: 8px 0; color: #1d1d1f; font-weight: 400; }}
        strong {{ font-weight: 500; }}
    </style>
</head>
<body>
    <div class="container">

        
        <div class="content">
            <p>Hi {name},</p>
            
            <p>This is Gabriel, the founder of Spaceport AI. On behalf of our team, thanks for signing up for our waitlist!</p>
            
            <p>You'll be among the first to know when we launch and get early access to our features. If selected, you'll have the option to become one of our early beta users.</p>
            
            <p><strong>Stay tuned for updates by following our socials!</strong></p>
            
            <div class="signature">
                <p><strong>Best regards,</strong></p>
                <p>Gabriel Hansen<br>
                Founder, CEO<br>
                Spaceport AI</p>
            </div>
            
            <div class="social-links">
                <a href="https://instagram.com/Spaceport_AI" class="social-text-link">Instagram</a>
                <a href="https://www.facebook.com/profile.php?id=61578856815066" class="social-text-link">Facebook</a>
                <a href="https://www.linkedin.com/company/spaceport-ai/" class="social-text-link">LinkedIn</a>
            </div>
        </div>
        
        <div class="footer">
            <p>You can unsubscribe from these emails by replying with "unsubscribe".</p>
        </div>
    </div>
</body>
</html>"""

    try:
        # Send via Resend
        params = {
            "from": "Spaceport AI <hello@spcprt.com>",
            "to": [email],
            "subject": subject,
            "html": body_html,
            "text": body_text,
        }
        
        response = resend.Emails.send(params)
        print(f"Confirmation email sent to {email} via Resend: {response}")
    except Exception as e:
        print(f"Failed to send confirmation email to {email}: {e}")
        raise

def send_admin_notification(name, email):
    """
    Send notification email to admin about new waitlist signup
    """
    
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
        # Send via Resend
        params = {
            "from": "Spaceport AI <hello@spcprt.com>",
            "to": ['gabriel@spcprt.com', 'ethan@spcprt.com'],
            "subject": subject,
            "html": body_html,
            "text": body_text,
        }
        
        response = resend.Emails.send(params)
        print(f"Admin notification sent via Resend: {response}")
    except Exception as e:
        print(f"Failed to send admin notification: {e}")
        raise 