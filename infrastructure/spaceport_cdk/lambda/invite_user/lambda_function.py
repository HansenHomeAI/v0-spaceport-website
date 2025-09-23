import json
import os
import boto3
import resend
from typing import Optional

from ..shared.password_utils import generate_user_friendly_password

# Initialize Resend
resend.api_key = os.environ.get('RESEND_API_KEY')

cognito = boto3.client('cognito-idp')

USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
INVITE_GROUP = os.environ.get('INVITE_GROUP', 'beta-testers')
INVITE_API_KEY = os.environ.get('INVITE_API_KEY')
LOG_INVITE_DEBUG = os.environ.get('LOG_INVITE_DEBUG', 'false').lower() in ('1', 'true', 'yes', 'on')


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

        user_already_existed = False
        temp_password = None

        if data.get('resend'):
            create_params['MessageAction'] = 'RESEND'
        elif data.get('suppress'):
            create_params['MessageAction'] = 'SUPPRESS'
            # Provide a memorable but policy-compliant temporary password when suppressing
            temp_password = generate_temp_password()
            create_params['TemporaryPassword'] = temp_password

        try:
            cognito.admin_create_user(**create_params)
        except cognito.exceptions.UsernameExistsException:
            user_already_existed = True
            if not data.get('suppress'):
                return _response(200, {'message': 'User already exists. If they did not receive email, you can use resend=true', 'email': email})

        if data.get('suppress'):
            # Ensure attributes stay in sync and reset the temporary password for existing users
            updatable_attributes = [attr for attr in user_attributes if attr['Name'] != 'preferred_username']

            try:
                if updatable_attributes:
                    cognito.admin_update_user_attributes(
                        UserPoolId=USER_POOL_ID,
                        Username=email,
                        UserAttributes=updatable_attributes,
                    )
            except Exception as attr_err:
                print(f"Failed to update attributes for {email}: {attr_err}")

            try:
                cognito.admin_set_user_password(
                    UserPoolId=USER_POOL_ID,
                    Username=email,
                    Password=temp_password,
                    Permanent=False,
                )
            except Exception as pwd_err:
                return _response(500, {'error': f'Failed to set temporary password: {pwd_err}'})

            if LOG_INVITE_DEBUG and temp_password:
                print(f"INVITE_DEBUG email={email} temp_password={temp_password}")

        # If suppressed, send a custom SES email with clear next steps
        if data.get('suppress'):
            try:
                send_custom_invite_email(
                    email=email,
                    name=name,
                    temp_password=temp_password
                )
            except Exception as e:
                print(f"Failed to send custom invite email: {e}")

        # Add to group
        if group:
            cognito.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=email,
                GroupName=group,
            )

        response_message = 'Invite sent'
        if user_already_existed and data.get('suppress'):
            response_message = 'Existing user reset and invite sent'

        return _response(200, {'message': response_message, 'email': email, 'group': group, 'handle': handle or None})

    except Exception as e:
        return _response(500, {'error': str(e)})
def generate_temp_password() -> str:
    return generate_user_friendly_password()


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
