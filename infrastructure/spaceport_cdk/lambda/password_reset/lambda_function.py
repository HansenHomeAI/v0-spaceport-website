import json
import os
import boto3
import resend
import random
import string
from datetime import datetime, timedelta
from typing import Optional

# Initialize Resend
resend.api_key = os.environ.get('RESEND_API_KEY')

cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
RESET_CODES_TABLE = os.environ.get('RESET_CODES_TABLE', 'Spaceport-PasswordResetCodes-prod')


def _response(status, body):
    return {
        'statusCode': status,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'POST,OPTIONS',
        },
        'body': json.dumps(body),
    }


def lambda_handler(event, context):
    # Preflight
    if event.get('httpMethod') == 'OPTIONS':
        return _response(200, {})
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            data = json.loads(event['body'])
        else:
            data = event.get('body', {})
        
        email = data.get('email')
        if not email:
            return _response(400, {'error': 'Email is required'})
        
        # Check if user exists in Cognito
        try:
            cognito.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=email
            )
        except cognito.exceptions.UserNotFoundException:
            return _response(400, {'error': 'User not found'})
        except Exception as e:
            print(f"Error checking user: {e}")
            return _response(500, {'error': 'Failed to verify user'})
        
        # Generate 6-digit reset code
        reset_code = generate_reset_code()
        
        # Store code in DynamoDB with 15-minute expiration
        store_reset_code(email, reset_code)
        
        # Send password reset email with code
        send_password_reset_email(email, reset_code)
        
        return _response(200, {
            'message': 'Password reset code sent to your email',
            'email': email
        })
            
    except Exception as e:
        print(f"Unexpected error: {e}")
        return _response(500, {'error': 'Internal server error'})


def generate_reset_code() -> str:
    """Generate a 6-digit reset code"""
    return ''.join(random.choices(string.digits, k=6))

def store_reset_code(email: str, reset_code: str) -> None:
    """Store reset code in DynamoDB with 15-minute expiration"""
    table = dynamodb.Table(RESET_CODES_TABLE)
    
    # Calculate expiration time (15 minutes from now)
    expires_at = datetime.utcnow() + timedelta(minutes=15)
    
    table.put_item(
        Item={
            'email': email,
            'reset_code': reset_code,
            'expires_at': expires_at.isoformat(),
            'created_at': datetime.utcnow().isoformat(),
            'used': False
        }
    )

def send_password_reset_email(email: str, reset_code: str) -> None:
    """Send password reset email with code via Resend"""
    subject = 'Reset your Spaceport AI password'
    
    body_text = f"""
Hi,

You requested to reset your password for Spaceport AI.

Your password reset code is: {reset_code}

This code will expire in 15 minutes.

To reset your password:
1. Go to https://spcprt.com/create
2. Click "Forgot Password"
3. Enter this code: {reset_code}
4. Choose your new password

If you didn't request this password reset, please ignore this email.

Best regards,
Spaceport AI Team
    """.strip()
    
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2563eb;">Reset your Spaceport AI password</h2>
            
            <p>Hi,</p>
            
            <p>You requested to reset your password for Spaceport AI.</p>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                <h3 style="margin: 0; color: #2563eb; font-size: 24px; letter-spacing: 4px;">{reset_code}</h3>
                <p style="margin: 10px 0 0 0; color: #666;">Your password reset code</p>
            </div>
            
            <p><strong>This code will expire in 15 minutes.</strong></p>
            
            <p>To reset your password:</p>
            <ol>
                <li>Go to <a href="https://spcprt.com/create" style="color: #2563eb;">spcprt.com/create</a></li>
                <li>Click "Forgot Password"</li>
                <li>Enter this code: <strong>{reset_code}</strong></li>
                <li>Choose your new password</li>
            </ol>
            
            <p>If you didn't request this password reset, please ignore this email.</p>
            
            <p>Best regards,<br>Spaceport AI Team</p>
        </div>
    </body>
    </html>
    """
    
    # Send via Resend
    params = {
        "from": "Spaceport AI <hello@spcprt.com>",
        "to": [email],
        "subject": subject,
        "html": body_html,
        "text": body_text,
    }
    
    email_response = resend.Emails.send(params)
    print(f"Password reset email sent to {email} with code {reset_code}: {email_response}")
