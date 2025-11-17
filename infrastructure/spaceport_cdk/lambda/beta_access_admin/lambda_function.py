import json
import os
import boto3
import resend
from typing import Optional, Dict, Any
import logging

from shared.password_utils import generate_user_friendly_password

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Resend
resend.api_key = os.environ.get('RESEND_API_KEY')

cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
PERMISSIONS_TABLE_NAME = os.environ.get('PERMISSIONS_TABLE_NAME', 'Spaceport-BetaAccessPermissions')
INVITE_API_KEY = os.environ.get('INVITE_API_KEY')
LOG_INVITE_DEBUG = os.environ.get('LOG_INVITE_DEBUG', 'false').lower() in ('1', 'true', 'yes', 'on')

# Initialize permissions table
permissions_table = dynamodb.Table(PERMISSIONS_TABLE_NAME)


def _response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized API response"""
    return {
        'statusCode': status,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        },
        'body': json.dumps(body),
    }


def _get_user_from_jwt(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract user information from JWT token in Authorization header"""
    try:
        # Get the user info from the JWT claims (added by API Gateway Cognito authorizer)
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})
        
        if not claims:
            logger.error("No claims found in JWT token")
            return None
            
        return {
            'user_id': claims.get('sub'),
            'email': claims.get('email'),
            'preferred_username': claims.get('preferred_username'),
        }
    except Exception as e:
        logger.error(f"Failed to extract user from JWT: {e}")
        return None


def _check_beta_access_permission(user_id: str) -> bool:
    """Check if user has beta access admin permissions"""
    try:
        response = permissions_table.get_item(Key={'user_id': user_id})
        item = response.get('Item', {})

        if not item:
            return False

        if item.get('has_beta_access_permission') is True:
            return True

        permission_type = (item.get('permission_type') or '').lower()
        status = (item.get('status') or '').lower()

        return permission_type == 'beta_access_admin' and status != 'revoked'
    except Exception as e:
        logger.error(f"Failed to check permissions for user {user_id}: {e}")
        return False


def _send_invitation(email: str, name: str = "") -> Dict[str, Any]:
    """Send invitation using the same logic as the existing invite Lambda"""
    try:
        # Validate email
        if not email or '@' not in email:
            raise ValueError("Invalid email address")
        
        email = email.strip().lower()
        
        # Build user attributes
        user_attributes = [
            {'Name': 'email', 'Value': email},
            {'Name': 'email_verified', 'Value': 'true'},
            {'Name': 'preferred_username', 'Value': email},  # Use email as preferred_username
        ]
        if name:
            user_attributes.append({'Name': 'name', 'Value': name.strip()})
        
        temp_password = _generate_temp_password()
        user_already_existed = False

        try:
            create_params = {
                'UserPoolId': USER_POOL_ID,
                'Username': email,
                'UserAttributes': user_attributes,
                'DesiredDeliveryMediums': ['EMAIL'],
                'MessageAction': 'SUPPRESS',
                'TemporaryPassword': temp_password,
            }

            cognito.admin_create_user(**create_params)
        except cognito.exceptions.UsernameExistsException:
            user_already_existed = True
            logger.info(f"User {email} already exists, resetting invite password")

        # Always ensure attributes are trimmed + synced
        updatable_attributes = [attr for attr in user_attributes if attr['Name'] != 'preferred_username']

        try:
            if updatable_attributes:
                cognito.admin_update_user_attributes(
                    UserPoolId=USER_POOL_ID,
                    Username=email,
                    UserAttributes=updatable_attributes,
                )
        except Exception as attr_err:
            logger.warning(f"Failed to update attributes for {email}: {attr_err}")

        password_message = 'Invitation sent successfully'

        try:
            cognito.admin_set_user_password(
                UserPoolId=USER_POOL_ID,
                Username=email,
                Password=temp_password,
                Permanent=False,
            )
            if user_already_existed:
                password_message = 'Existing user reset and invitation sent successfully'
        except Exception as pwd_err:
            logger.error(f"Failed to set temporary password for {email}: {pwd_err}")
            raise

        if LOG_INVITE_DEBUG:
            logger.info(f"INVITE_DEBUG email={email} temp_password={temp_password}")

        _send_custom_invite_email(
            email=email,
            name=name,
            temp_password=temp_password
        )

        return {
            'success': True,
            'message': password_message,
            'email': email
        }
        
    except Exception as e:
        logger.error(f"Failed to send invitation to {email}: {e}")
        raise e


def _generate_temp_password() -> str:
    return generate_user_friendly_password()


def _send_custom_invite_email(email: str, name: str, temp_password: Optional[str]) -> None:
    """Send custom invitation email via Resend"""
    
    # Debug logging to see what email is being sent
    logger.info(f"DEBUG: Sending invitation email to: {email}, name: {name}")
    
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
        <li>Go to <a href="https://spcprt.com/create">spcprt.com/create</a></li>
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
    logger.info(f"Beta invitation email sent via Resend: {email_response}")


def lambda_handler(event, context):
    """Main Lambda handler for beta access admin operations"""
    
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return _response(200, {'ok': True})
    
    try:
        # Get user from JWT
        user = _get_user_from_jwt(event)
        if not user or not user.get('user_id'):
            return _response(401, {'error': 'Unauthorized - invalid token'})
        
        user_id = user['user_id']
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        
        # Check permissions endpoint
        if http_method == 'GET' and 'check-permission' in path:
            has_permission = _check_beta_access_permission(user_id)
            return _response(200, {
                'has_beta_access_permission': has_permission,
                'user_email': user.get('email'),
                'user_id': user_id
            })
        
        # Send invitation endpoint
        if http_method == 'POST' and 'send-invitation' in path:
            # Check if user has beta access permission
            if not _check_beta_access_permission(user_id):
                return _response(403, {'error': 'Forbidden - insufficient permissions'})
            
            # Parse request body
            body = event.get('body') or '{}'
            if isinstance(body, str):
                data = json.loads(body)
            else:
                data = body
            
            email = data.get('email', '').strip().lower()
            name = data.get('name', '').strip()
            
            # Debug logging to see what we received
            logger.info(f"DEBUG: Received invitation request - email: {email}, name: {name}")
            logger.info(f"DEBUG: Full request data: {data}")
            
            if not email:
                return _response(400, {'error': 'Email address is required'})
            
            # Send invitation
            result = _send_invitation(email, name)
            
            # Log the action
            logger.info(f"Beta invitation sent by {user.get('email')} to {email}")
            
            return _response(200, result)
        
        # Unknown endpoint
        return _response(404, {'error': 'Endpoint not found'})
        
    except json.JSONDecodeError:
        return _response(400, {'error': 'Invalid JSON in request body'})
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return _response(500, {'error': 'Internal server error'})
