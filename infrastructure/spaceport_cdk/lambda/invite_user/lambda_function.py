import json
import os
import boto3
import resend
from typing import Optional

# Initialize Resend
resend.api_key = os.environ.get('RESEND_API_KEY')

cognito = boto3.client('cognito-idp')

USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
INVITE_GROUP = os.environ.get('INVITE_GROUP', 'beta-testers')
INVITE_API_KEY = os.environ.get('INVITE_API_KEY')


def _response(status, body):
    return {
        'statusCode': status,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,x-api-key',
            'Access-Control-Allow-Methods': 'POST,OPTIONS',
        },
        'body': json.dumps(body),
    }


def lambda_handler(event, context):
    # Preflight
    if event.get('httpMethod') == 'OPTIONS':
        return _response(200, {'ok': True})

    # AuthN via simple x-api-key (rotate this key if leaked)
    if INVITE_API_KEY:
        headers = event.get('headers') or {}
        presented = headers.get('x-api-key') or headers.get('X-Api-Key')
        if presented != INVITE_API_KEY:
            return _response(401, {'error': 'Unauthorized'})

    try:
        body = event.get('body') or '{}'
        if isinstance(body, str):
            data = json.loads(body)
        else:
            data = body

        email = (data.get('email') or '').strip().lower()
        name = (data.get('name') or '').strip()
        group = (data.get('group') or INVITE_GROUP).strip()
        handle = (data.get('handle') or '').strip()

        if not email:
            return _response(400, {'error': 'email is required'})

        # Build attributes per pool schema; include preferred_username if provided
        user_attributes = [
            {'Name': 'email', 'Value': email},
            {'Name': 'email_verified', 'Value': 'true' if data.get('emailVerified') else 'false'},
        ]
        if name:
            user_attributes.append({'Name': 'name', 'Value': name})
        if handle:
            user_attributes.append({'Name': 'preferred_username', 'Value': handle})

        # Create user with auto-generated temporary password by default; optionally suppress and send custom SES email
        # Only include MessageAction when explicitly set; omitting it triggers default invite email behavior
        create_params = {
            'UserPoolId': USER_POOL_ID,
            'Username': email,
            'UserAttributes': user_attributes,
            'DesiredDeliveryMediums': ['EMAIL'],
        }

        if data.get('resend'):
            create_params['MessageAction'] = 'RESEND'
        elif data.get('suppress'):
            create_params['MessageAction'] = 'SUPPRESS'
            # Provide a memorable but policy-compliant temporary password when suppressing
            create_params['TemporaryPassword'] = generate_temp_password()

        resp = cognito.admin_create_user(**create_params)
        print(f"User created successfully: {email}, UserStatus: {resp.get('User', {}).get('UserStatus')}")

        # If suppressed, send a custom SES email with clear next steps
        if data.get('suppress'):
            try:
                send_custom_invite_email(
                    email=email,
                    name=name,
                    temp_password=create_params.get('TemporaryPassword')
                )
                print(f"Custom invite email sent successfully to {email}")
            except Exception as e:
                print(f"Failed to send custom invite email: {e}")
                # Don't fail the entire operation if email fails

        # Add to group
        if group:
            cognito.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=email,
                GroupName=group,
            )

        return _response(200, {'message': 'Invite sent', 'email': email, 'group': group, 'handle': handle or None})

    except cognito.exceptions.UsernameExistsException:
        return _response(200, {'message': 'User already exists. If they did not receive email, you can use resend=true', 'email': email})
    except Exception as e:
        return _response(500, {'error': str(e)})
def generate_temp_password() -> str:
    import random
    import string
    
    # Generate a more robust temporary password that meets all Cognito requirements
    # Length >= 8, includes lower, upper, digit, and symbol
    lowercase = ''.join(random.choice(string.ascii_lowercase) for _ in range(2))
    uppercase = ''.join(random.choice(string.ascii_uppercase) for _ in range(2))
    digits = ''.join(random.choice(string.digits) for _ in range(2))
    symbols = ''.join(random.choice('!@#$%^&*') for _ in range(2))
    
    # Combine and shuffle
    password_chars = list(lowercase + uppercase + digits + symbols)
    random.shuffle(password_chars)
    
    return ''.join(password_chars)


def send_custom_invite_email(email: str, name: str, temp_password: Optional[str]) -> None:
    subject = 'You have been invited to Spaceport AI'
    greeting = f"Hi {name},\n\n" if name else "Hi,\n\n"
    body_text = (
        greeting
        + "You've been approved for access. Follow these steps to sign in and finish setup:\n\n"
        + "1) Go to https://spcprt.com/create\n"
        + f"2) Sign in with your email ({email}) and the temporary password: {temp_password or '<check your email>'}\n"
        + "3) You'll be prompted to choose a new password and set your handle.\n\n"
        + "If you need help, just reply to this email.\n\n— Spaceport AI"
    )

    body_html = f"""
    <html><body>
      <p>{'Hi ' + name + ',' if name else 'Hi,'}</p>
      <p>You've been approved for access. Follow these steps to sign in and finish setup:</p>
      <ol>
        <li>Go to <a href=\"https://spcprt.com/create\">spcprt.com/create</a></li>
        <li>Sign in with your email (<strong>{email}</strong>) and the temporary password: <code>{temp_password or '&lt;check your email&gt;'}</code></li>
        <li>You'll be prompted to choose a new password and set your handle.</li>
      </ol>
      <p>If you need help, just reply to this email.</p>
      <p>— Spaceport AI</p>
    </body></html>
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
    print(f"Invite email sent via Resend: {email_response}")

