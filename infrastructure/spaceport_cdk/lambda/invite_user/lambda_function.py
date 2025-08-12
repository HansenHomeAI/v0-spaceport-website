import json
import os
import boto3

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

        if not email:
            return _response(400, {'error': 'email is required'})

        # Create user with auto-generated temporary password; send default Cognito email
        cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true' if data.get('emailVerified') else 'false'},
                *([{'Name': 'name', 'Value': name}] if name else []),
            ],
            DesiredDeliveryMediums=['EMAIL'],
            MessageAction='RESEND' if data.get('resend') else 'SUPPRESS' if data.get('suppress') else None
        )

        # Ensure invite sent if suppressed flag not set
        if data.get('suppress'):
            pass  # advanced flows can use SES to send custom mail

        # Add to group
        if group:
            cognito.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=email,
                GroupName=group,
            )

        return _response(200, {'message': 'Invite sent', 'email': email, 'group': group})

    except cognito.exceptions.UsernameExistsException:
        return _response(200, {'message': 'User already exists. If they did not receive email, you can use resend=true', 'email': email})
    except Exception as e:
        return _response(500, {'error': str(e)})


