import json
import os
import boto3
from typing import Dict, Any, Optional
import logging
import urllib.request
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS services
cognito_idp = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

# Environment variables
USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID')
INVITE_API_URL = os.environ.get('INVITE_API_URL')
INVITE_API_KEY = os.environ.get('INVITE_API_KEY')

def _cors_headers() -> Dict[str, str]:
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,authorization,X-Amz-Date,X-Amz-Security-Token,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    }

def _response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'statusCode': status,
        'headers': _cors_headers(),
        'body': json.dumps(body),
    }

def _get_cognito_claims_from_apig(event: Dict[str, Any]) -> Dict[str, Any]:
    """Extract Cognito JWT claims injected by API Gateway authorizer."""
    rc = event.get('requestContext') or {}
    auth = rc.get('authorizer') or {}
    claims = auth.get('claims') or {}
    return claims

def check_beta_invite_permission(user_sub: str) -> bool:
    """Check if user has permission to invite beta users"""
    try:
        response = cognito_idp.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=user_sub
        )
        
        # Check for custom:can_invite_beta attribute
        for attr in response.get('UserAttributes', []):
            if attr['Name'] == 'custom:can_invite_beta' and attr['Value'].lower() == 'true':
                return True
        
        return False
    except Exception as e:
        logger.error(f"Error checking beta invite permission: {str(e)}")
        return False

def send_beta_invitation(email: str, name: str = "", requester_email: str = "") -> Dict[str, Any]:
    """Send beta invitation using the existing invite API"""
    try:
        # Prepare invitation data
        invite_data = {
            'email': email.strip().lower(),
            'name': name.strip(),
            'suppress': True  # Use custom email instead of Cognito default
        }
        
        # Add handle if name is provided
        if name:
            handle = name.lower().replace(' ', '').replace('@', '')[:20]
            invite_data['handle'] = handle
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Add API key if configured
        if INVITE_API_KEY:
            headers['x-api-key'] = INVITE_API_KEY
        
        # Prepare HTTP request data
        request_data = json.dumps(invite_data).encode('utf-8')
        
        # Make request to invite API using urllib
        req = urllib.request.Request(
            INVITE_API_URL,
            data=request_data,
            headers=headers,
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode('utf-8')
                result = json.loads(response_data)
                
                logger.info(f"Beta invitation sent successfully to {email} by {requester_email}")
                return {
                    'success': True,
                    'message': f'Beta invitation sent to {email}',
                    'email': email
                }
        except urllib.error.HTTPError as e:
            error_response = e.read().decode('utf-8') if e.fp else str(e)
            error_msg = f"Failed to send invitation: {e.code} - {error_response}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
            
    except Exception as e:
        error_msg = f"Error sending beta invitation: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for beta invitation management
    """
    try:
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return _response(200, {'ok': True})
        
        # Get user claims from API Gateway
        claims = _get_cognito_claims_from_apig(event)
        if not claims:
            return _response(401, {'error': 'Unauthorized'})
        
        user_sub = claims.get('sub', '')
        user_email = claims.get('email', '')
        
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        
        logger.info(f"Processing {http_method} request to {path} for user {user_email}")
        
        # Check if user has beta invite permissions
        if not check_beta_invite_permission(user_sub):
            return _response(403, {
                'error': 'You do not have permission to invite beta users',
                'canInvite': False
            })
        
        if http_method == 'GET' and 'check-permission' in path:
            # Check permission endpoint
            return _response(200, {
                'canInvite': True,
                'message': 'You have permission to invite beta users'
            })
        
        elif http_method == 'POST' and 'send-invitation' in path:
            # Send invitation endpoint
            body = json.loads(event.get('body', '{}'))
            
            email = body.get('email', '').strip().lower()
            name = body.get('name', '').strip()
            
            if not email:
                return _response(400, {'error': 'Email is required'})
            
            # Validate email format
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                return _response(400, {'error': 'Invalid email format'})
            
            # Send the invitation
            result = send_beta_invitation(email, name, user_email)
            
            if result['success']:
                return _response(200, result)
            else:
                return _response(500, result)
        
        else:
            return _response(400, {'error': 'Invalid endpoint'})
            
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return _response(500, {'error': 'Internal server error'})