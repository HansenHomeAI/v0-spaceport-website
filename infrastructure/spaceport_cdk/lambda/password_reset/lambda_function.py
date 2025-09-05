import json
import os
import boto3
import resend
from typing import Optional

# Initialize Resend
resend.api_key = os.environ.get('RESEND_API_KEY')

cognito = boto3.client('cognito-idp')

USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']


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
        
        # Initiate password reset using Cognito
        try:
            response = cognito.forgot_password(
                ClientId=os.environ['COGNITO_USER_POOL_CLIENT_ID'],
                Username=email
            )
            
            # Get the confirmation code from the response
            # Note: In production, Cognito sends the code via email
            # We'll send our own custom email with the code
            code_delivery_details = response.get('CodeDeliveryDetails', {})
            delivery_medium = code_delivery_details.get('DeliveryMedium', 'EMAIL')
            
            if delivery_medium == 'EMAIL':
                # Send custom password reset email via Resend
                send_password_reset_email(email)
                
                return _response(200, {
                    'message': 'Password reset code sent to your email',
                    'email': email
                })
            else:
                return _response(400, {'error': 'Email delivery not available'})
                
        except cognito.exceptions.UserNotFoundException:
            return _response(400, {'error': 'User not found'})
        except cognito.exceptions.InvalidParameterException as e:
            return _response(400, {'error': f'Invalid request: {str(e)}'})
        except Exception as e:
            print(f"Error initiating password reset: {e}")
            return _response(500, {'error': 'Failed to initiate password reset'})
            
    except Exception as e:
        print(f"Unexpected error: {e}")
        return _response(500, {'error': 'Internal server error'})


def send_password_reset_email(email: str) -> None:
    """Send password reset email via Resend"""
    subject = 'Reset your Spaceport AI password'
    
    body_text = f"""
Hi,

You requested to reset your password for Spaceport AI.

To reset your password, please go to https://spcprt.com/create and use the "Forgot Password" feature.

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
            
            <p>To reset your password, please go to <a href="https://spcprt.com/create" style="color: #2563eb;">spcprt.com/create</a> and use the "Forgot Password" feature.</p>
            
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
    print(f"Password reset email sent to {email}: {email_response}")
