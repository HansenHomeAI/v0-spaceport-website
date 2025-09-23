import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import boto3
import resend
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize third-party clients
resend.api_key = os.environ.get('RESEND_API_KEY', '')

cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
PROJECTS_TABLE_NAME = os.environ['PROJECTS_TABLE_NAME']
PERMISSIONS_TABLE_NAME = os.environ.get('PERMISSIONS_TABLE_NAME', '')
APP_BASE_URL = os.environ.get('APP_BASE_URL', '').rstrip('/')

projects_table = dynamodb.Table(PROJECTS_TABLE_NAME)
permissions_table = dynamodb.Table(PERMISSIONS_TABLE_NAME) if PERMISSIONS_TABLE_NAME else None


def _response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
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
    context = event.get('requestContext') or {}
    authorizer = context.get('authorizer') or {}
    claims = authorizer.get('claims') or {}
    if not claims:
        return None
    return {
        'user_id': claims.get('sub'),
        'email': claims.get('email'),
        'preferred_username': claims.get('preferred_username'),
    }


def _check_permission(user_id: str) -> bool:
    if not permissions_table:
        logger.error('Permissions table not configured')
        return False
    try:
        record = permissions_table.get_item(Key={'user_id': user_id}).get('Item') or {}
        status = record.get('status')
        permission_type = record.get('permission_type')
        raw_extra = record.get('permissions') or []
        if isinstance(raw_extra, str):
            extra = [raw_extra]
        elif isinstance(raw_extra, list):
            extra = raw_extra
        else:
            extra = []

        if status != 'active':
            return False

        if permission_type in ('model_delivery_admin', 'beta_access_admin'):
            return True

        if any(p in ('model_delivery_admin', 'beta_access_admin') for p in extra):
            return True

        return False
    except Exception as exc:
        logger.error('Failed to check permissions for %s: %s', user_id, exc)
        return False


def _get_cognito_user(username: str) -> Dict[str, Any]:
    try:
        result = cognito.admin_get_user(UserPoolId=USER_POOL_ID, Username=username)
        return result
    except cognito.exceptions.UserNotFoundException:
        raise ValueError('User not found')


def _get_attribute(user: Dict[str, Any], name: str) -> Optional[str]:
    for attr in user.get('UserAttributes', []):
        if attr.get('Name') == name:
            return attr.get('Value')
    return None


def _list_projects(email: str) -> List[Dict[str, Any]]:
    user = _get_cognito_user(email)
    user_sub = _get_attribute(user, 'sub')
    if not user_sub:
        raise ValueError('Unable to resolve user ID for account')

    response = projects_table.query(KeyConditionExpression=Key('userSub').eq(user_sub))
    projects = response.get('Items', [])

    trimmed: List[Dict[str, Any]] = []
    for item in projects:
        trimmed.append({
            'projectId': item.get('projectId'),
            'title': item.get('title') or 'Untitled',
            'status': item.get('status') or 'draft',
            'progress': item.get('progress') or 0,
            'updatedAt': item.get('updatedAt'),
            'delivery': item.get('delivery') or None,
        })
    return trimmed


def _validate_link(link: str) -> str:
    cleaned = (link or '').strip()
    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in ('http', 'https') or not parsed.netloc:
        raise ValueError('Delivery link must be a valid URL')
    return cleaned


def _send_delivery_email(email: str, project_title: str, link: str) -> None:
    if not resend.api_key:
        raise RuntimeError('Resend API key is not configured')

    subject = 'Your Spaceport 3D model is ready'
    button_label = 'View 3D Model'

    primary_host = APP_BASE_URL if APP_BASE_URL else ''

    link_block = (
        f'<p style="margin:24px 0;">'
        f'<a href="{link}" style="display:inline-block;padding:12px 20px;border-radius:999px;background:#111827;color:#ffffff;text-decoration:none;font-weight:600;">{button_label}</a>'
        '</p>'
    )

    html_parts = [
        '<div style="font-family:Helvetica,Arial,sans-serif;padding:24px;color:#0b0f19;background:#f8fafc">',
        '<h2 style="margin-top:0;font-size:20px;">Your 3D model is ready ✨</h2>',
        (
            f'<p style="font-size:15px;line-height:22px;">We just finished processing <strong>{project_title or "your project"}</strong>. '
            'You can access the completed model using the secure link below.</p>'
        ),
        link_block,
    ]

    if primary_host:
        html_parts.append(
            f'<p style="font-size:13px;color:#475569;">Need to review the project details? '
            f'<a href="{primary_host}/create" style="color:#111827;text-decoration:underline;">Open your Spaceport dashboard</a>.</p>'
        )

    html_parts.append('<p style="font-size:13px;color:#475569;margin-top:32px;">– The Spaceport team</p></div>')

    text_body = (
        'Your 3D model is ready!\n\n'
        f'Project: {project_title or "your project"}\n'
        f'Link: {link}\n\n'
        'You can also open your Spaceport dashboard for full project context.\n\n'
        '— The Spaceport team'
    )

    resend.Emails.send({
        'from': 'Spaceport AI <hello@spcprt.com>',
        'to': [email],
        'subject': subject,
        'html': ''.join(html_parts),
        'text': text_body,
    })


def _apply_delivery(email: str, project_id: str, link: str, delivered_by: Dict[str, Optional[str]]) -> Dict[str, Any]:
    user = _get_cognito_user(email)
    user_sub = _get_attribute(user, 'sub')
    user_name = _get_attribute(user, 'preferred_username') or email

    if not user_sub:
        raise ValueError('Unable to resolve project owner')

    project_key = {'userSub': user_sub, 'projectId': project_id}
    existing = projects_table.get_item(Key=project_key).get('Item')
    if not existing:
        raise ValueError('Project not found for user')

    now = int(time.time())

    delivery_payload = {
        'link': link,
        'deliveredAt': now,
        'deliveredBySub': delivered_by.get('user_id'),
        'deliveredByEmail': delivered_by.get('email'),
    }

    update_expression = 'SET #delivery = :delivery, #updatedAt = :updatedAt'
    expression_names = {
        '#delivery': 'delivery',
        '#updatedAt': 'updatedAt',
    }
    expression_values = {
        ':delivery': delivery_payload,
        ':updatedAt': now,
    }

    if not existing.get('status') or existing.get('status') == 'draft':
        update_expression += ', #status = :status'
        expression_names['#status'] = 'status'
        expression_values[':status'] = 'delivered'

    if (existing.get('progress') or 0) < 100:
        update_expression += ', #progress = :progress'
        expression_names['#progress'] = 'progress'
        expression_values[':progress'] = 100

    projects_table.update_item(
        Key=project_key,
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_names,
        ExpressionAttributeValues=expression_values,
    )

    _send_delivery_email(email=email, project_title=existing.get('title') or user_name, link=link)

    return {
        'projectId': project_id,
        'title': existing.get('title') or 'Untitled',
        'delivery': delivery_payload,
    }


def lambda_handler(event, _context):
    method = (event.get('httpMethod') or 'GET').upper()
    if method == 'OPTIONS':
        return _response(200, {'ok': True})

    try:
        user = _get_user_from_jwt(event)
        if not user or not user.get('user_id'):
            return _response(401, {'error': 'Unauthorized'})

        path = event.get('path') or ''
        body = event.get('body') or '{}'
        payload = json.loads(body) if isinstance(body, str) else body

        if method == 'GET' and path.endswith('check-permission'):
            has_permission = _check_permission(user['user_id'])
            return _response(200, {'has_model_delivery_permission': has_permission})

        if not _check_permission(user['user_id']):
            return _response(403, {'error': 'Forbidden'})

        if method == 'POST' and path.endswith('list-projects'):
            email = (payload.get('email') or '').strip().lower()
            if not email:
                return _response(400, {'error': 'Email is required'})
            projects = _list_projects(email)
            return _response(200, {'projects': projects})

        if method == 'POST' and path.endswith('send'):
            email = (payload.get('email') or '').strip().lower()
            project_id = (payload.get('projectId') or '').strip()
            link = _validate_link(payload.get('link') or '')

            if not email or not project_id:
                return _response(400, {'error': 'Email and projectId are required'})

            result = _apply_delivery(email, project_id, link, user)
            return _response(200, {'ok': True, 'delivery': result})

        return _response(404, {'error': 'Endpoint not found'})

    except json.JSONDecodeError:
        return _response(400, {'error': 'Invalid JSON payload'})
    except ValueError as exc:
        return _response(400, {'error': str(exc)})
    except RuntimeError as exc:
        logger.error('Configuration error: %s', exc)
        return _response(500, {'error': str(exc)})
    except Exception as exc:  # pragma: no cover - catch-all for unexpected errors
        logger.error('Unexpected error: %s', exc)
        return _response(500, {'error': 'Internal server error'})
