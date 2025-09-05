import json
import os
import boto3
from typing import Optional, Dict, Any
import logging
import resend

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
PERMISSIONS_TABLE_NAME = os.environ.get('PERMISSIONS_TABLE_NAME', 'Spaceport-BetaAccessPermissions')
INVITE_API_KEY = os.environ.get('INVITE_API_KEY')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')

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
        return item.get('has_beta_access_permission', False)
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
        
        # Create user with suppressed email (we'll send custom email)
        create_params = {
            'UserPoolId': USER_POOL_ID,
            'Username': email,
            'UserAttributes': user_attributes,
            'DesiredDeliveryMediums': ['EMAIL'],
            'MessageAction': 'SUPPRESS',
            'TemporaryPassword': _generate_temp_password(),
        }
        
        resp = cognito.admin_create_user(**create_params)
        
        # Send custom SES email
        _send_custom_invite_email(
            email=email,
            name=name,
            temp_password=create_params.get('TemporaryPassword')
        )
        
        # Add to beta-testers-v2 group
        cognito.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=email,
            GroupName='beta-testers-v2',
        )
        
        return {
            'success': True,
            'message': 'Invitation sent successfully',
            'email': email
        }
        
    except cognito.exceptions.UsernameExistsException:
        return {
            'success': True,
            'message': 'User already exists - invitation resent',
            'email': email
        }
    except Exception as e:
        logger.error(f"Failed to send invitation to {email}: {e}")
        raise e


def _generate_temp_password() -> str:
    """Generate a policy-compliant temporary password"""
    import random
    digits = ''.join(random.choice('0123456789') for _ in range(4))
    return f"Spcprt{digits}A"


def _send_custom_invite_email(email: str, name: str, temp_password: Optional[str]) -> None:
    """Send custom invitation email via Resend"""
    
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY environment variable not set")
        raise Exception("Email service not configured")
    
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

    # Set the API key as shown in Resend documentation
    resend.api_key = RESEND_API_KEY
    
    # Use Resend SDK exactly as documented
    r = resend.Emails.send({
        "from": "Spaceport AI <hello@spcprt.com>",
        "to": [email],
        "subject": subject,
        "text": body_text,
        "html": body_html
    })
    
    logger.info(f"Email sent successfully via Resend to {email}")


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