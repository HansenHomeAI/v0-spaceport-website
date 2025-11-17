import json
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
import resend


logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment configuration
USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID')
PROJECTS_TABLE_NAME = os.environ.get('PROJECTS_TABLE_NAME')
PERMISSIONS_TABLE_NAME = os.environ.get('PERMISSIONS_TABLE_NAME', 'Spaceport-BetaAccessPermissions')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')


if not USER_POOL_ID or not PROJECTS_TABLE_NAME:
    raise RuntimeError('COGNITO_USER_POOL_ID and PROJECTS_TABLE_NAME must be configured')

if not RESEND_API_KEY:
    logger.warning('RESEND_API_KEY is not configured; model delivery emails will fail')

resend.api_key = RESEND_API_KEY


# AWS clients/resources
cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')
projects_table = dynamodb.Table(PROJECTS_TABLE_NAME)
permissions_table = dynamodb.Table(PERMISSIONS_TABLE_NAME)


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError


def convert_floats_to_decimal(data: Any) -> Any:
    if isinstance(data, float):
        return Decimal(str(data))
    if isinstance(data, dict):
        return {key: convert_floats_to_decimal(value) for key, value in data.items()}
    if isinstance(data, list):
        return [convert_floats_to_decimal(item) for item in data]
    return data


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
        'body': json.dumps(body, default=decimal_default),
    }


def _get_user_from_jwt(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})

        if not claims:
            logger.error('Missing JWT claims in request context')
            return None

        return {
            'user_id': claims.get('sub'),
            'email': claims.get('email'),
            'preferred_username': claims.get('preferred_username'),
            'name': claims.get('name'),
        }
    except Exception as exc:
        logger.error(f'Failed to extract user from JWT: {exc}')
        return None


def _check_employee_permission(user_id: str) -> bool:
    try:
        item = permissions_table.get_item(Key={'user_id': user_id}).get('Item')
        if not item:
            return False

        # Support legacy and new schemas
        if item.get('has_beta_access_permission') is True:
            return True

        permission_type = (item.get('permission_type') or '').lower()
        status = (item.get('status') or '').lower()

        if permission_type in ('model_delivery_admin', 'beta_access_admin') and status != 'revoked':
            return True

        if item.get('model_delivery_permission') is True:
            return True

        return False
    except Exception as exc:
        logger.error(f'Error checking permissions for user {user_id}: {exc}')
        return False


def _resolve_client(email: str) -> Optional[Dict[str, Any]]:
    if not email:
        return None

    normalized_email = email.strip().lower()

    try:
        user = cognito.admin_get_user(UserPoolId=USER_POOL_ID, Username=normalized_email)
    except cognito.exceptions.UserNotFoundException:
        logger.info(f'admin_get_user miss for {normalized_email}, attempting list_users filter')
        users = cognito.list_users(
            UserPoolId=USER_POOL_ID,
            Filter=f'email = "{normalized_email}"'
        ).get('Users', [])
        if not users:
            return None
        user = users[0]
    except Exception as exc:
        logger.error(f'Failed to resolve client {normalized_email}: {exc}')
        return None

    attributes = user.get('UserAttributes', []) if isinstance(user, dict) else user['UserAttributes']
    attr_map = {attr['Name']: attr['Value'] for attr in attributes}

    return {
        'user_id': attr_map.get('sub') or user.get('Username'),
        'email': attr_map.get('email') or normalized_email,
        'name': attr_map.get('name') or attr_map.get('preferred_username') or user.get('Username') or normalized_email,
        'preferred_username': attr_map.get('preferred_username'),
        'status': user.get('UserStatus'),
    }


def _fetch_projects_for_user(user_sub: str) -> List[Dict[str, Any]]:
    projects: List[Dict[str, Any]] = []
    try:
        last_evaluated_key = None
        while True:
            query_kwargs = {
                'KeyConditionExpression': Key('userSub').eq(user_sub),
            }
            if last_evaluated_key:
                query_kwargs['ExclusiveStartKey'] = last_evaluated_key

            result = projects_table.query(**query_kwargs)
            projects.extend(result.get('Items', []))
            last_evaluated_key = result.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
    except Exception as exc:
        logger.error(f'Failed to load projects for userSub={user_sub}: {exc}')
    return projects


def _send_delivery_email(recipient_email: str, project_title: str, model_link: str) -> Dict[str, Any]:
    if not RESEND_API_KEY:
        raise RuntimeError('Resend API key is not configured')

    subject = f'Your 3D model is ready: {project_title or "Spaceport AI Project"}'

    html_body = f"""
    <html>
      <body style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background-color:#050505;color:#ffffff;padding:32px;\">
        <h1 style=\"font-size:24px;margin-bottom:16px;\">Your 3D model is live</h1>
        <p style=\"font-size:16px;line-height:1.6;margin-bottom:24px;color:rgba(255,255,255,0.75);\">
          {project_title or 'Your project'} is ready. Open the interactive viewer below to explore the completed model.
        </p>
        <p style=\"text-align:center;margin:32px 0;\">
          <a href=\"{model_link}\" style=\"display:inline-flex;padding:14px 28px;border-radius:999px;background:#ffffff;color:#050505;font-weight:600;text-decoration:none;\">
            Open 3D model
          </a>
        </p>
        <p style=\"font-size:14px;line-height:1.6;color:rgba(255,255,255,0.6);\">
          If the button does not work, copy and paste this link into your browser:<br/>
          <span style=\"color:#ffffff;\">{model_link}</span>
        </p>
        <p style=\"font-size:14px;margin-top:32px;color:rgba(255,255,255,0.6);\">— Spaceport AI</p>
      </body>
    </html>
    """

    text_body = (
        f"Your 3D model is ready.\n\n"
        f"Project: {project_title or 'Spaceport AI Project'}\n"
        f"Open the model: {model_link}\n\n"
        "If the link does not open, copy and paste it into your browser.\n\n"
        "— Spaceport AI"
    )

    params = {
        'from': 'Spaceport AI <hello@spcprt.com>',
        'to': [recipient_email],
        'subject': subject,
        'html': html_body,
        'text': text_body,
    }

    logger.info(f'Sending model delivery email via Resend to {recipient_email}')
    response = resend.Emails.send(params)
    logger.info(f'Model delivery email sent: {response}')
    return response


def _persist_delivery(
    project: Dict[str, Any],
    model_link: str,
    message_id: str,
    employee: Dict[str, Any],
    recipient: Dict[str, Any],
) -> Dict[str, Any]:
    user_sub = project['userSub']
    project_id = project['projectId']
    now_iso = datetime.now(timezone.utc).isoformat()
    now_epoch = int(datetime.now(timezone.utc).timestamp())

    history: List[Dict[str, Any]] = project.get('deliveryHistory', []) or []
    duplicate_entry = None
    for entry in history:
        if (
            entry.get('modelLink') == model_link
            and entry.get('recipientEmail') == recipient['email']
        ):
            duplicate_entry = entry
            break

    history_entry = {
        'modelLink': model_link,
        'recipientEmail': recipient['email'],
        'projectId': project_id,
        'projectTitle': project.get('title'),
        'sentAt': now_iso,
        'messageId': message_id,
        'sentBy': {
            'userId': employee.get('user_id'),
            'email': employee.get('email'),
            'name': employee.get('preferred_username') or employee.get('email'),
        },
    }

    if duplicate_entry:
        duplicate_entry.update(history_entry)
    else:
        history.append(history_entry)

    delivery_state = {
        'modelLink': model_link,
        'lastSentAt': now_iso,
        'sentBy': history_entry['sentBy'],
        'recipientEmail': recipient['email'],
        'messageId': message_id,
    }

    new_status = project.get('status') or 'delivered'
    if new_status.lower() != 'delivered':
        new_status = 'delivered'

    new_progress = max(int(project.get('progress') or 0), 100)

    update_expression = (
        'SET #delivery = :delivery, '
        '#deliveryHistory = :history, '
        '#status = :status, '
        '#progress = :progress, '
        '#updatedAt = :updatedAt'
    )

    expr_attr_names = {
        '#delivery': 'delivery',
        '#deliveryHistory': 'deliveryHistory',
        '#status': 'status',
        '#progress': 'progress',
        '#updatedAt': 'updatedAt',
    }

    expr_attr_values = convert_floats_to_decimal({
        ':delivery': delivery_state,
        ':history': history,
        ':status': new_status,
        ':progress': new_progress,
        ':updatedAt': now_epoch,
    })

    projects_table.update_item(
        Key={'userSub': user_sub, 'projectId': project_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expr_attr_names,
        ExpressionAttributeValues=expr_attr_values,
    )

    project_copy = project.copy()
    project_copy['delivery'] = delivery_state
    project_copy['deliveryHistory'] = history
    project_copy['status'] = new_status
    project_copy['progress'] = new_progress
    project_copy['updatedAt'] = now_epoch

    return project_copy


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return _response(200, {'ok': True})

    try:
        employee = _get_user_from_jwt(event)
        if not employee or not employee.get('user_id'):
            return _response(401, {'error': 'Unauthorized'})

        method = (event.get('httpMethod') or 'GET').upper()
        path = event.get('path', '')

        if method == 'GET' and path.endswith('check-permission'):
            allowed = _check_employee_permission(employee['user_id'])
            return _response(200, {
                'has_model_delivery_permission': allowed,
                'user_email': employee.get('email'),
            })

        if not _check_employee_permission(employee['user_id']):
            return _response(403, {'error': 'Forbidden - insufficient permissions'})

        body_raw = event.get('body') or '{}'
        data = json.loads(body_raw) if isinstance(body_raw, str) else (body_raw or {})

        if method == 'POST' and path.endswith('resolve-client'):
            client_email = (data.get('email') or '').strip()
            if not client_email:
                return _response(400, {'error': 'Client email is required'})

            client = _resolve_client(client_email)
            if not client:
                return _response(404, {'error': 'Client not found'})

            projects = _fetch_projects_for_user(client['user_id'])
            return _response(200, {
                'client': client,
                'projects': projects,
            })

        if method == 'POST' and path.endswith('send'):
            client_email = (data.get('clientEmail') or '').strip().lower()
            project_id = (data.get('projectId') or '').strip()
            model_link = (data.get('modelLink') or '').strip()

            if not client_email or not project_id or not model_link:
                return _response(400, {'error': 'clientEmail, projectId, and modelLink are required'})

            if not (model_link.startswith('http://') or model_link.startswith('https://')):
                return _response(400, {'error': 'Model link must be a valid http(s) URL'})

            client = _resolve_client(client_email)
            if not client:
                return _response(404, {'error': 'Client not found'})

            project_result = projects_table.get_item(
                Key={'userSub': client['user_id'], 'projectId': project_id}
            )
            project = project_result.get('Item')
            if not project:
                return _response(404, {'error': 'Project not found for client'})

            email_response = _send_delivery_email(
                recipient_email=client['email'],
                project_title=project.get('title') or data.get('projectTitle'),
                model_link=model_link,
            )

            message_id = (
                email_response.get('id')
                if isinstance(email_response, dict)
                else email_response
            )

            updated_project = _persist_delivery(
                project=project,
                model_link=model_link,
                message_id=str(message_id),
                employee=employee,
                recipient=client,
            )

            audit_log = {
                'action': 'model_link_sent',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'projectId': project_id,
                'clientEmail': client['email'],
                'employeeEmail': employee.get('email'),
                'messageId': message_id,
            }
            logger.info(f'Model delivery audit: {json.dumps(audit_log)}')

            return _response(200, {
                'ok': True,
                'messageId': message_id,
                'project': updated_project,
            })

        return _response(404, {'error': 'Not found'})

    except Exception as exc:
        logger.exception(f'Unhandled error processing request: {exc}')
        return _response(500, {'error': 'Internal server error'})
