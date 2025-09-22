import json
import os
import boto3
import resend
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Resend
resend.api_key = os.environ.get('RESEND_API_KEY')

cognito = boto3.client('cognito-idp')

USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
INVITE_GROUP = os.environ.get('INVITE_GROUP', 'beta-testers')
INVITE_API_KEY = os.environ.get('INVITE_API_KEY')

# Enhanced configuration
MAX_RETRIES = 3
RETRY_DELAY = 2
USER_CREATION_TIMEOUT = 30


def _response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'statusCode': status,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,x-api-key',
            'Access-Control-Allow-Methods': 'POST,OPTIONS',
        },
        'body': json.dumps(body),
    }


def generate_temp_password() -> str:
    """Generate a policy-compliant temporary password with enhanced randomness"""
    import random
    import string
    
    # Generate more random digits
    digits = ''.join(random.choices(string.digits, k=6))
    # Add a special character to ensure policy compliance
    special = random.choice('!@#$%')
    
    # Format: Spcprt{6digits}{special}A
    return f"Spcprt{digits}{special}A"


def validate_email(email: str) -> bool:
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def wait_for_user_creation(email: str, timeout: int = USER_CREATION_TIMEOUT) -> bool:
    """Wait for user creation to propagate in Cognito"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            user_info = cognito.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=email
            )
            user_status = user_info['UserStatus']
            logger.info(f"User {email} found with status: {user_status}")
            
            # User exists and is in a valid state
            if user_status in ['FORCE_CHANGE_PASSWORD', 'CONFIRMED', 'UNCONFIRMED']:
                return True
                
        except cognito.exceptions.UserNotFoundException:
            logger.debug(f"User {email} not yet available, waiting...")
        except Exception as e:
            logger.error(f"Error checking user status: {e}")
        
        time.sleep(1)
    
    logger.error(f"User {email} was not created within {timeout} seconds")
    return False


def create_user_with_retry(email: str, user_attributes: list, temp_password: str, 
                          max_retries: int = MAX_RETRIES) -> Dict[str, Any]:
    """Create user with retry logic and comprehensive error handling"""
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Creating user attempt {attempt + 1} for {email}")
            
            create_params = {
                'UserPoolId': USER_POOL_ID,
                'Username': email,
                'UserAttributes': user_attributes,
                'DesiredDeliveryMediums': ['EMAIL'],
                'MessageAction': 'SUPPRESS',
                'TemporaryPassword': temp_password,
            }
            
            response = cognito.admin_create_user(**create_params)
            logger.info(f"User {email} created successfully")
            
            # Wait for user creation to propagate
            if wait_for_user_creation(email):
                return {'success': True, 'response': response}
            else:
                logger.error(f"User {email} created but not accessible")
                return {'success': False, 'error': 'User creation timeout'}
            
        except cognito.exceptions.UsernameExistsException:
            logger.info(f"User {email} already exists")
            
            # Check if existing user is in a good state
            try:
                user_info = cognito.admin_get_user(
                    UserPoolId=USER_POOL_ID,
                    Username=email
                )
                user_status = user_info['UserStatus']
                logger.info(f"Existing user {email} has status: {user_status}")
                
                # If user is in FORCE_CHANGE_PASSWORD state, reset their password
                if user_status == 'FORCE_CHANGE_PASSWORD':
                    try:
                        cognito.admin_set_user_password(
                            UserPoolId=USER_POOL_ID,
                            Username=email,
                            Password=temp_password,
                            Permanent=False
                        )
                        logger.info(f"Reset temporary password for existing user {email}")
                    except Exception as e:
                        logger.error(f"Failed to reset password for existing user: {e}")
                
                return {'success': True, 'response': {'existing': True}}
                
            except Exception as e:
                logger.error(f"Error checking existing user: {e}")
                return {'success': False, 'error': f'Existing user check failed: {e}'}
        
        except cognito.exceptions.InvalidParameterException as e:
            logger.error(f"Invalid parameter for user creation: {e}")
            return {'success': False, 'error': f'Invalid parameter: {e}'}
        
        except cognito.exceptions.InvalidPasswordException as e:
            logger.error(f"Invalid password for user creation: {e}")
            # Try with a new password
            temp_password = generate_temp_password()
            logger.info(f"Retrying with new password: {temp_password}")
            continue
            
        except Exception as e:
            logger.error(f"User creation attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                return {'success': False, 'error': str(e)}
    
    return {'success': False, 'error': 'Max retries exceeded'}


def add_user_to_group_with_retry(email: str, group: str, max_retries: int = MAX_RETRIES) -> bool:
    """Add user to group with retry logic"""
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Adding user {email} to group {group}, attempt {attempt + 1}")
            
            cognito.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=email,
                GroupName=group,
            )
            logger.info(f"Successfully added user {email} to group {group}")
            return True
            
        except cognito.exceptions.UserNotFoundException:
            logger.warning(f"User {email} not found when adding to group, waiting...")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
            continue
            
        except cognito.exceptions.ResourceNotFoundException:
            logger.error(f"Group {group} not found")
            return False
            
        except Exception as e:
            logger.error(f"Failed to add user to group, attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
    
    logger.error(f"Failed to add user {email} to group {group} after {max_retries} attempts")
    return False


def send_custom_invite_email(email: str, name: str, temp_password: str) -> bool:
    """Send custom invitation email via Resend with enhanced error handling"""
    try:
        subject = 'You have been invited to Spaceport AI'
        greeting = f"Hi {name},\n\n" if name else "Hi,\n\n"
        
        body_text = (
            greeting
            + "You've been approved for access to Spaceport AI! 🚀\n\n"
            + "Follow these steps to sign in and finish setup:\n\n"
            + "1) Go to https://spcprt.com/create\n"
            + f"2) Sign in with your email ({email}) and this temporary password:\n"
            + f"   {temp_password}\n\n"
            + "3) You'll be prompted to choose a new password and set your handle.\n\n"
            + "Important notes:\n"
            + "- This temporary password expires in 7 days\n"
            + "- You'll need to set a permanent password on first login\n"
            + "- Your handle will be your unique username on the platform\n\n"
            + "If you have any issues signing in, please reply to this email.\n\n"
            + "Welcome to the future of 3D content creation!\n\n"
            + "— The Spaceport AI Team"
        )

        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="color: white; margin: 0;">Welcome to Spaceport AI! 🚀</h1>
            </div>
            
            <div style="padding: 30px; background: #f8f9fa; border-radius: 0 0 8px 8px;">
                <p>{'Hi ' + name + ',' if name else 'Hi,'}</p>
                
                <p>You've been approved for access to Spaceport AI!</p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea;">
                    <h3 style="margin-top: 0; color: #667eea;">Your Login Credentials</h3>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Temporary Password:</strong> <code style="background: #e9ecef; padding: 2px 6px; border-radius: 4px; font-size: 14px;">{temp_password}</code></p>
                </div>
                
                <h3 style="color: #667eea;">Getting Started</h3>
                <ol style="padding-left: 20px;">
                    <li>Go to <a href="https://spcprt.com/create" style="color: #667eea; text-decoration: none; font-weight: bold;">spcprt.com/create</a></li>
                    <li>Sign in with your email and temporary password above</li>
                    <li>Choose a new password and set your unique handle</li>
                    <li>Start creating amazing 3D content!</li>
                </ol>
                
                <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
                    <h4 style="margin-top: 0; color: #856404;">Important Notes</h4>
                    <ul style="margin-bottom: 0;">
                        <li>This temporary password expires in 7 days</li>
                        <li>You'll need to set a permanent password on first login</li>
                        <li>Your handle will be your unique username on the platform</li>
                    </ul>
                </div>
                
                <p>If you have any issues signing in, please reply to this email and we'll help you out!</p>
                
                <p style="margin-top: 30px;">Welcome to the future of 3D content creation!</p>
                <p><strong>— The Spaceport AI Team</strong></p>
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
        logger.info(f"Invite email sent via Resend to {email}: {email_response}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send custom invite email to {email}: {e}")
        return False


def lambda_handler(event, context):
    """Enhanced Lambda handler with comprehensive error handling and logging"""
    
    # Add request ID for tracking
    request_id = context.aws_request_id if context else 'local-test'
    logger.info(f"Processing invite request {request_id}")
    
    # Preflight
    if event.get('httpMethod') == 'OPTIONS':
        return _response(200, {'ok': True})

    # Enhanced authentication
    if INVITE_API_KEY:
        headers = event.get('headers') or {}
        presented = headers.get('x-api-key') or headers.get('X-Api-Key')
        if presented != INVITE_API_KEY:
            logger.warning(f"Unauthorized access attempt from {headers.get('x-forwarded-for', 'unknown')}")
            return _response(401, {'error': 'Unauthorized'})

    try:
        # Enhanced request parsing
        body = event.get('body') or '{}'
        if isinstance(body, str):
            data = json.loads(body)
        else:
            data = body

        email = (data.get('email') or '').strip().lower()
        name = (data.get('name') or '').strip()
        group = (data.get('group') or INVITE_GROUP).strip()
        handle = (data.get('handle') or '').strip()

        # Enhanced validation
        if not email:
            return _response(400, {'error': 'Email is required'})
            
        if not validate_email(email):
            return _response(400, {'error': 'Invalid email format'})

        logger.info(f"Processing invitation for {email} (name: {name}, group: {group})")

        # Build attributes per pool schema
        user_attributes = [
            {'Name': 'email', 'Value': email},
            {'Name': 'email_verified', 'Value': 'true'},
        ]
        if name:
            user_attributes.append({'Name': 'name', 'Value': name})
        if handle:
            user_attributes.append({'Name': 'preferred_username', 'Value': handle})

        # Generate secure temporary password
        temp_password = generate_temp_password()
        logger.info(f"Generated temporary password for {email}")

        # Create user with enhanced retry logic
        creation_result = create_user_with_retry(email, user_attributes, temp_password)
        
        if not creation_result['success']:
            logger.error(f"User creation failed for {email}: {creation_result['error']}")
            return _response(500, {
                'error': 'Failed to create user',
                'details': creation_result['error'],
                'request_id': request_id
            })

        # Add to group with retry logic
        if group:
            group_success = add_user_to_group_with_retry(email, group)
            if not group_success:
                logger.warning(f"Failed to add {email} to group {group}, but user was created")

        # Send custom invitation email
        email_success = send_custom_invite_email(email, name, temp_password)
        if not email_success:
            logger.error(f"Failed to send invitation email to {email}")
            # Don't fail the request since user was created successfully
            
        # Log successful completion
        logger.info(f"Successfully processed invitation for {email} (request: {request_id})")

        return _response(200, {
            'message': 'Invitation sent successfully',
            'email': email,
            'group': group,
            'handle': handle or None,
            'email_sent': email_success,
            'request_id': request_id,
            'timestamp': datetime.utcnow().isoformat()
        })

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {e}")
        return _response(400, {'error': 'Invalid JSON format'})
        
    except Exception as e:
        logger.error(f"Unexpected error in invite handler: {e}", exc_info=True)
        return _response(500, {
            'error': 'Internal server error',
            'request_id': request_id,
            'timestamp': datetime.utcnow().isoformat()
        })