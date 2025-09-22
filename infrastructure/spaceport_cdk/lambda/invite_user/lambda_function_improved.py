import json
import os
import boto3
import resend
from typing import Optional
import logging
from datetime import datetime
import hashlib

# Configure detailed logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Resend
resend.api_key = os.environ.get('RESEND_API_KEY')

cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
INVITE_GROUP = os.environ.get('INVITE_GROUP', 'beta-testers')
INVITE_API_KEY = os.environ.get('INVITE_API_KEY')

# DynamoDB table for tracking invites (create if needed)
INVITE_TRACKING_TABLE = os.environ.get('INVITE_TRACKING_TABLE', 'Spaceport-InviteTracking')


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


def get_or_create_tracking_table():
    """Ensure invite tracking table exists"""
    try:
        table = dynamodb.Table(INVITE_TRACKING_TABLE)
        table.load()
        return table
    except:
        logger.warning(f"Invite tracking table {INVITE_TRACKING_TABLE} not found")
        return None


def get_existing_invite(email: str, table):
    """Check if user has existing invite and return temp password if exists"""
    if not table:
        return None
    
    try:
        response = table.get_item(Key={'email': email.lower()})
        item = response.get('Item')
        if item:
            logger.info(f"Found existing invite for {email}")
            return item
        return None
    except Exception as e:
        logger.error(f"Error checking existing invite: {e}")
        return None


def store_invite_info(email: str, temp_password: str, table):
    """Store invite information for tracking"""
    if not table:
        return
    
    try:
        table.put_item(
            Item={
                'email': email.lower(),
                'temp_password': temp_password,
                'created_at': datetime.utcnow().isoformat(),
                'invite_count': 1,
                'last_invite': datetime.utcnow().isoformat()
            }
        )
        logger.info(f"Stored invite info for {email}")
    except Exception as e:
        logger.error(f"Error storing invite info: {e}")


def update_invite_count(email: str, table):
    """Update invite count for re-invites"""
    if not table:
        return
    
    try:
        table.update_item(
            Key={'email': email.lower()},
            UpdateExpression='SET invite_count = invite_count + :inc, last_invite = :now',
            ExpressionAttributeValues={
                ':inc': 1,
                ':now': datetime.utcnow().isoformat()
            }
        )
        logger.info(f"Updated invite count for {email}")
    except Exception as e:
        logger.error(f"Error updating invite count: {e}")


def generate_stable_temp_password(email: str) -> str:
    """Generate a stable temporary password based on email hash"""
    # Use email hash to generate consistent password for same email
    email_hash = hashlib.sha256(email.lower().encode()).hexdigest()
    # Take first 4 hex chars and convert to 4-digit number
    digits = str(int(email_hash[:4], 16))[-4:].zfill(4)
    # Must meet pool policy: length>=8, includes lower, upper, digit
    return f"Spcprt{digits}A"


def verify_user_exists(email: str) -> dict:
    """Check if user already exists in Cognito"""
    try:
        # Try to get user by email
        response = cognito.list_users(
            UserPoolId=USER_POOL_ID,
            Filter=f'email = "{email}"',
            Limit=1
        )
        
        if response.get('Users'):
            user = response['Users'][0]
            logger.info(f"User {email} already exists with status: {user.get('UserStatus')}")
            return {
                'exists': True,
                'username': user.get('Username'),
                'status': user.get('UserStatus'),
                'attributes': {attr['Name']: attr['Value'] for attr in user.get('Attributes', [])}
            }
        
        return {'exists': False}
    except Exception as e:
        logger.error(f"Error checking if user exists: {e}")
        return {'exists': False, 'error': str(e)}


def lambda_handler(event, context):
    # Preflight
    if event.get('httpMethod') == 'OPTIONS':
        return _response(200, {'ok': True})

    # AuthN via simple x-api-key (rotate this key if leaked)
    if INVITE_API_KEY:
        headers = event.get('headers') or {}
        presented = headers.get('x-api-key') or headers.get('X-Api-Key')
        if presented != INVITE_API_KEY:
            logger.warning(f"Invalid API key presented")
            return _response(401, {'error': 'Unauthorized'})

    tracking_table = get_or_create_tracking_table()

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
        force_resend = data.get('resend', False)
        suppress_email = data.get('suppress', False)

        if not email:
            return _response(400, {'error': 'email is required'})

        logger.info(f"Processing invite for {email} (name={name}, handle={handle}, resend={force_resend})")

        # Check if user already exists
        existing_user = verify_user_exists(email)
        
        if existing_user.get('exists'):
            user_status = existing_user.get('status')
            
            # Handle different user states
            if user_status == 'CONFIRMED':
                logger.info(f"User {email} is already confirmed")
                return _response(200, {
                    'message': 'User already exists and is confirmed',
                    'email': email,
                    'status': 'CONFIRMED',
                    'action': 'User can sign in with their existing password'
                })
            elif user_status == 'FORCE_CHANGE_PASSWORD':
                # User needs to change password - resend invite
                if not force_resend:
                    return _response(200, {
                        'message': 'User exists but needs password change. Use resend=true to send new invite',
                        'email': email,
                        'status': user_status
                    })
            elif user_status == 'UNCONFIRMED':
                # User created but not confirmed
                logger.info(f"User {email} exists but is unconfirmed, will resend")

        # Check for existing invite to use same password
        existing_invite = get_existing_invite(email, tracking_table)
        
        # Generate or retrieve temp password
        if existing_invite and not force_resend:
            temp_password = existing_invite.get('temp_password')
            logger.info(f"Using existing temp password for {email}")
            update_invite_count(email, tracking_table)
        else:
            # Generate stable password based on email
            temp_password = generate_stable_temp_password(email)
            logger.info(f"Generated new temp password for {email}")

        # Build attributes
        user_attributes = [
            {'Name': 'email', 'Value': email},
            {'Name': 'email_verified', 'Value': 'true'},  # Always verify email for invites
        ]
        if name:
            user_attributes.append({'Name': 'name', 'Value': name})
        
        # Set preferred_username - use handle if provided, otherwise use email
        preferred_username = handle if handle else email
        user_attributes.append({'Name': 'preferred_username', 'Value': preferred_username})

        # Create or update user
        try:
            if existing_user.get('exists'):
                # User exists - update attributes and reset password
                username = existing_user.get('username')
                logger.info(f"Updating existing user {username}")
                
                # Update attributes
                for attr in user_attributes:
                    try:
                        cognito.admin_update_user_attributes(
                            UserPoolId=USER_POOL_ID,
                            Username=username,
                            UserAttributes=[attr]
                        )
                    except Exception as e:
                        logger.warning(f"Could not update attribute {attr['Name']}: {e}")
                
                # Set new temporary password
                cognito.admin_set_user_password(
                    UserPoolId=USER_POOL_ID,
                    Username=username,
                    Password=temp_password,
                    Permanent=False  # Force password change on next login
                )
                
                action = 'updated'
            else:
                # Create new user
                create_params = {
                    'UserPoolId': USER_POOL_ID,
                    'Username': email,  # Use email as username for consistency
                    'UserAttributes': user_attributes,
                    'TemporaryPassword': temp_password,
                    'DesiredDeliveryMediums': ['EMAIL'],
                    'MessageAction': 'SUPPRESS' if suppress_email else 'RESEND' if force_resend else None
                }
                
                # Remove None values
                create_params = {k: v for k, v in create_params.items() if v is not None}
                
                logger.info(f"Creating user with params: {json.dumps({k: v for k, v in create_params.items() if k != 'TemporaryPassword'})}")
                resp = cognito.admin_create_user(**create_params)
                action = 'created'
                
        except cognito.exceptions.UsernameExistsException:
            logger.info(f"Username exists, attempting to get user and update")
            # This shouldn't happen with our checks, but handle it
            existing_user = verify_user_exists(email)
            if existing_user.get('exists'):
                username = existing_user.get('username')
                cognito.admin_set_user_password(
                    UserPoolId=USER_POOL_ID,
                    Username=username,
                    Password=temp_password,
                    Permanent=False
                )
                action = 'password_reset'
            else:
                raise

        # Store invite info for tracking
        store_invite_info(email, temp_password, tracking_table)

        # Send custom email if suppressed or always for consistency
        if suppress_email or True:  # Always send our custom email for consistency
            try:
                send_custom_invite_email(
                    email=email,
                    name=name,
                    temp_password=temp_password
                )
                logger.info(f"Custom invite email sent to {email}")
            except Exception as e:
                logger.error(f"Failed to send custom invite email: {e}")
                # Don't fail the whole operation if email fails
                # User can still be sent password through other means

        # Add to group
        if group:
            try:
                # Get the actual username (might be different from email)
                if existing_user.get('exists'):
                    username = existing_user.get('username')
                else:
                    username = email
                    
                cognito.admin_add_user_to_group(
                    UserPoolId=USER_POOL_ID,
                    Username=username,
                    GroupName=group,
                )
                logger.info(f"Added {username} to group {group}")
            except Exception as e:
                logger.warning(f"Could not add user to group {group}: {e}")

        return _response(200, {
            'message': f'User {action} and invite sent',
            'email': email,
            'group': group,
            'handle': preferred_username,
            'action': action,
            'temp_password_hint': 'Check email for temporary password'
        })

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return _response(500, {'error': str(e)})


def send_custom_invite_email(email: str, name: str, temp_password: Optional[str]) -> None:
    subject = 'Welcome to Spaceport AI - Your Account is Ready'
    greeting = f"Hi {name},\n\n" if name else "Hi,\n\n"
    
    # More explicit instructions
    body_text = (
        greeting
        + "Your Spaceport AI account has been created! Here's how to get started:\n\n"
        + "**IMPORTANT: Save this email - you'll need the information below to sign in**\n\n"
        + "Sign-in Instructions:\n"
        + "1. Go to https://spcprt.com/create\n"
        + f"2. Enter your email: {email}\n"
        + f"3. Enter this temporary password exactly as shown: {temp_password}\n"
        + "4. You'll be prompted to create your own password\n\n"
        + "Troubleshooting:\n"
        + "- Make sure you're using the email address shown above\n"
        + "- Copy and paste the temporary password to avoid typos\n"
        + "- The temporary password is case-sensitive\n"
        + "- If you still can't sign in, reply to this email for help\n\n"
        + "This temporary password expires in 7 days.\n\n"
        + "— The Spaceport AI Team"
    )

    body_html = f"""
    <html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
      <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2563eb;">Welcome to Spaceport AI!</h2>
        <p>{'Hi ' + name + ',' if name else 'Hi,'}</p>
        <p>Your Spaceport AI account has been created! Here's how to get started:</p>
        
        <div style="background-color: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin: 20px 0;">
          <strong>⚠️ IMPORTANT: Save this email - you'll need the information below to sign in</strong>
        </div>
        
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
          <h3 style="margin-top: 0; color: #2563eb;">Sign-in Instructions:</h3>
          <ol style="margin: 10px 0;">
            <li>Go to <a href="https://spcprt.com/create" style="color: #2563eb;">spcprt.com/create</a></li>
            <li>Enter your email: <strong style="background-color: #e3f2fd; padding: 2px 5px; border-radius: 3px;">{email}</strong></li>
            <li>Enter this temporary password exactly as shown:<br>
                <code style="background-color: #fff; border: 2px solid #2563eb; padding: 8px 12px; border-radius: 5px; font-size: 16px; font-weight: bold; display: inline-block; margin: 10px 0; letter-spacing: 1px;">{temp_password}</code>
            </li>
            <li>You'll be prompted to create your own password</li>
          </ol>
        </div>
        
        <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
          <h4 style="margin-top: 0; color: #666;">Troubleshooting Tips:</h4>
          <ul style="margin: 5px 0; color: #666; font-size: 14px;">
            <li>Make sure you're using the email address shown above</li>
            <li>Copy and paste the temporary password to avoid typos</li>
            <li>The temporary password is case-sensitive</li>
            <li>If you still can't sign in, reply to this email for help</li>
          </ul>
        </div>
        
        <p style="color: #666; font-size: 14px;">This temporary password expires in 7 days.</p>
        
        <p>Best regards,<br><strong>The Spaceport AI Team</strong></p>
      </div>
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
    logger.info(f"Invite email sent via Resend: {email_response}")