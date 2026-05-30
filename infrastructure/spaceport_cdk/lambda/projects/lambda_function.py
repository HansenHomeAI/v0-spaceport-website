import json
import logging
import os
import time
import urllib.request
from decimal import Decimal
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import stripe


# Helper function to convert Decimal to int/float for JSON serialization
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError


# Helper function to convert float types to Decimal for DynamoDB
def convert_floats_to_decimal(data):
    """Recursively convert float values to Decimal for DynamoDB compatibility"""
    if isinstance(data, float):
        return Decimal(str(data))
    elif isinstance(data, dict):
        return {k: convert_floats_to_decimal(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_floats_to_decimal(v) for v in data]
    else:
        return data


logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['PROJECTS_TABLE_NAME']
table = dynamodb.Table(TABLE_NAME)
PERMISSIONS_TABLE_NAME = os.environ.get('PERMISSIONS_TABLE_NAME', 'Spaceport-BetaAccessPermissions')
permissions_table = dynamodb.Table(PERMISSIONS_TABLE_NAME)

STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
stripe.api_key = STRIPE_SECRET_KEY
STRIPE_MODEL_TRAINING_PRICE = os.environ.get('STRIPE_MODEL_TRAINING_PRICE')
STRIPE_MODEL_HOSTING_PRICE = os.environ.get('STRIPE_MODEL_HOSTING_PRICE')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://spcprt.com')

R2_ENDPOINT = os.environ.get('R2_ENDPOINT')
R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', 'spaces-viewers')
R2_REGION = os.environ.get('R2_REGION', 'auto')
R2_PUBLIC_BASE_URL = (os.environ.get('R2_PUBLIC_BASE_URL') or '').rstrip('/')

MAX_STATIC_PHOTO_FILES = 500
MAX_STATIC_PHOTO_SIZE_BYTES = 50 * 1024 * 1024
STATIC_PHOTO_UPLOAD_EXPIRES_SECONDS = 15 * 60


def _cors_headers() -> Dict[str, str]:
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,authorization,X-Amz-Date,X-Amz-Security-Token,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    }


def _response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'statusCode': status,
        'headers': _cors_headers(),
        'body': json.dumps(body, default=decimal_default),
    }


class AuthError(Exception):
    pass


def _load_json_url(url: str) -> Dict[str, Any]:
    with urllib.request.urlopen(url) as r:  # nosec - trusted AWS domain from token iss
        return json.loads(r.read().decode('utf-8'))


def _get_cognito_claims_from_apig(event: Dict[str, Any]) -> Dict[str, Any]:
    """Extract Cognito JWT claims injected by API Gateway authorizer.

    API Gateway REST API with Cognito User Pools authorizer places claims under
    event['requestContext']['authorizer']['claims'].
    """
    rc = event.get('requestContext') or {}
    auth = rc.get('authorizer') or {}
    # Common shape: { claims: {...}, principalId: 'cognitoUserPool:<sub>' }
    claims = auth.get('claims') or {}
    if not claims:
        # Some deployments may nest JWT differently; fall back to empty dict
        return {}
    return claims


def _get_r2_client() -> Optional[Any]:
    if not (R2_ENDPOINT and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET_NAME):
        return None

    return boto3.client(
        's3',
        region_name=R2_REGION,
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4'),
    )


def _safe_key_segment(value: str) -> str:
    cleaned = ''.join(ch for ch in str(value or '').strip() if ch not in '\x00\r\n')
    if cleaned in ('', '.', '..'):
        cleaned = 'untitled'
    return quote(cleaned, safe='._-()')


def _sanitize_relative_path(relative_path: str) -> str:
    normalized = str(relative_path or '').replace('\\', '/').strip('/')
    parts = []
    for raw_part in normalized.split('/'):
        part = raw_part.strip()
        if not part or part in ('.', '..'):
            continue
        parts.append(_safe_key_segment(part))
    if not parts:
        parts.append('untitled')
    return '/'.join(parts)


def _build_static_photo_key(user_sub: str, project_id: str, relative_path: str) -> str:
    return '/'.join([
        'users',
        _safe_key_segment(user_sub),
        'projects',
        _safe_key_segment(project_id),
        'photos',
        _sanitize_relative_path(relative_path),
    ])


def _public_url_for_key(object_key: str) -> str:
    if not R2_PUBLIC_BASE_URL:
        raise RuntimeError('R2_PUBLIC_BASE_URL is not configured for static photo uploads. Set R2_PUBLIC_BASE_URL_STAGING or R2_PUBLIC_BASE_URL_PROD.')
    return f"{R2_PUBLIC_BASE_URL}/{object_key}"


def _validate_static_photo_request(files: Any) -> list[Dict[str, Any]]:
    if not isinstance(files, list) or not files:
        raise ValueError('files must be a non-empty list')
    if len(files) > MAX_STATIC_PHOTO_FILES:
        raise ValueError(f'files cannot exceed {MAX_STATIC_PHOTO_FILES} items')

    validated = []
    for index, file_info in enumerate(files):
        if not isinstance(file_info, dict):
            raise ValueError(f'files[{index}] must be an object')
        name = (file_info.get('name') or '').strip()
        relative_path = (file_info.get('relativePath') or name).strip()
        content_type = (file_info.get('contentType') or 'application/octet-stream').strip()
        size_bytes = int(file_info.get('sizeBytes') or 0)
        if not name:
            raise ValueError(f'files[{index}].name is required')
        if not content_type.startswith('image/'):
            raise ValueError(f'files[{index}] must be an image')
        if size_bytes <= 0:
            raise ValueError(f'files[{index}].sizeBytes must be positive')
        if size_bytes > MAX_STATIC_PHOTO_SIZE_BYTES:
            raise ValueError(f'files[{index}] exceeds the 50MB per-photo limit')
        validated.append({
            'name': name,
            'relativePath': relative_path,
            'contentType': content_type,
            'sizeBytes': size_bytes,
        })
    return validated


def _create_static_photo_upload_urls(user_sub: str, project_id: str, files: Any) -> Dict[str, Any]:
    client = _get_r2_client()
    if not client:
        raise RuntimeError('R2 is not configured for static photo uploads.')
    if not R2_PUBLIC_BASE_URL:
        raise RuntimeError('R2_PUBLIC_BASE_URL is not configured for static photo uploads. Set R2_PUBLIC_BASE_URL_STAGING or R2_PUBLIC_BASE_URL_PROD.')

    validated_files = _validate_static_photo_request(files)
    results = []
    for file_info in validated_files:
        object_key = _build_static_photo_key(
            user_sub=user_sub,
            project_id=project_id,
            relative_path=file_info['relativePath'],
        )
        upload_url = client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': R2_BUCKET_NAME,
                'Key': object_key,
                'ContentType': file_info['contentType'],
            },
            ExpiresIn=STATIC_PHOTO_UPLOAD_EXPIRES_SECONDS,
        )
        results.append({
            **file_info,
            'objectKey': object_key,
            'publicUrl': _public_url_for_key(object_key),
            'uploadUrl': upload_url,
        })

    return {
        'bucket': R2_BUCKET_NAME,
        'publicBaseUrl': R2_PUBLIC_BASE_URL,
        'expiresIn': STATIC_PHOTO_UPLOAD_EXPIRES_SECONDS,
        'files': results,
    }


def _resolve_viewer_slug(project: Dict[str, Any]) -> Optional[str]:
    for key in ('viewerSlug', 'viewer_slug', 'slug'):
        slug = project.get(key)
        if slug:
            return slug

    delivery = project.get('delivery') or {}
    for key in ('viewerSlug', 'viewer_slug'):
        slug = delivery.get(key)
        if slug:
            return slug

    model_link = delivery.get('modelLink') or project.get('modelLink')
    if model_link:
        parsed = urlparse(model_link)
        path = parsed.path or ''
        if '/spaces/' in path:
            slug = path.split('/spaces/', 1)[1].strip('/').split('/')[0]
            if slug:
                return slug
        parts = [part for part in path.split('/') if part]
        if parts:
            return parts[-1]

    return None


def _append_query_params(url: str, params: Dict[str, str]) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key, value in params.items():
        query[key] = [value]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _resolve_model_link(project: Dict[str, Any]) -> Optional[str]:
    candidates = [
        'modelLink',
        'model_link',
        'modelUrl',
        'model_url',
        'viewerLink',
        'viewer_link',
        'viewerUrl',
        'viewer_url',
        'finalModelUrl',
        'final_model_url',
        'finalViewerUrl',
        'final_viewer_url',
    ]
    delivery = project.get('delivery') or {}
    for key in candidates:
        value = delivery.get(key) or project.get(key)
        if isinstance(value, str) and value.strip().startswith(('http://', 'https://')):
            return value.strip()
    return None


def _check_user_is_admin(user_id: str) -> bool:
    try:
        item = permissions_table.get_item(Key={'user_id': user_id}).get('Item')
        if not item:
            return False

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
        logger.error('Error checking admin permissions for user %s: %s', user_id, exc)
        return False


def _admin_payment_deadline() -> int:
    return int(time.time()) + (3650 * 24 * 60 * 60)


def _create_payment_session(project: Dict[str, Any], user_email: str) -> Dict[str, str]:
    if not STRIPE_SECRET_KEY:
        raise RuntimeError('Stripe is not configured for payments.')
    if not STRIPE_MODEL_TRAINING_PRICE or not STRIPE_MODEL_HOSTING_PRICE:
        raise RuntimeError('Stripe price IDs for model payments are not configured.')

    model_link = _resolve_model_link(project) or FRONTEND_URL
    success_url = _append_query_params(model_link, {'payment': 'success'})
    cancel_url = _append_query_params(model_link, {'payment': 'canceled'})

    metadata = {
        'projectId': project.get('projectId', ''),
        'userSub': project.get('userSub', ''),
        'clientEmail': user_email or project.get('email', ''),
        'viewerSlug': _resolve_viewer_slug(project) or '',
        'projectTitle': project.get('title') or '',
        'source': 'project_portal',
    }

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode='subscription',
        client_reference_id=project.get('projectId'),
        customer_email=user_email or project.get('email'),
        line_items=[
            {
                'price': STRIPE_MODEL_TRAINING_PRICE,
                'quantity': 1,
            },
            {
                'price': STRIPE_MODEL_HOSTING_PRICE,
                'quantity': 1,
            },
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
        subscription_data={
            'trial_period_days': 30,
            'metadata': metadata,
        },
    )

    if not session or not getattr(session, 'url', None):
        raise RuntimeError('Stripe checkout session is missing a payment URL')

    return {
        'id': session.id,
        'url': session.url,
    }


def _cleanup_hosting(project: Dict[str, Any]) -> Optional[str]:
    status = (project.get('status') or '').lower()
    if status not in ('delivered', 'revoked'):
        return None

    slug = _resolve_viewer_slug(project)
    if not slug:
        return 'Unable to resolve viewer slug for cleanup.'

    client = _get_r2_client()
    if not client:
        return 'R2 is not configured for cleanup.'

    try:
        client.delete_object(Bucket=R2_BUCKET_NAME, Key=f"models/{slug}/index.html")
        client.delete_object(Bucket=R2_BUCKET_NAME, Key=f"models/{slug}/original.html")
    except ClientError as exc:
        logger.error('Failed to delete viewer for slug %s: %s', slug, exc)
        return 'Failed to delete hosted viewer.'

    return None


def _expire_checkout_session(session_id: str) -> Optional[str]:
    if not session_id:
        return None
    if not STRIPE_SECRET_KEY:
        return 'Stripe is not configured for cleanup.'
    try:
        stripe.checkout.Session.expire(session_id)
    except stripe.error.StripeError as exc:
        logger.error('Failed to expire checkout session %s: %s', session_id, exc)
        return 'Failed to expire Stripe checkout session.'
    return None


def _cancel_subscription(subscription_id: str) -> Optional[str]:
    if not subscription_id:
        return None
    if not STRIPE_SECRET_KEY:
        return 'Stripe is not configured for cleanup.'
    try:
        stripe.Subscription.delete(subscription_id)
    except stripe.error.StripeError as exc:
        logger.error('Failed to cancel subscription %s: %s', subscription_id, exc)
        return 'Failed to cancel Stripe subscription.'
    return None


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return _response(200, {'ok': True})

    # Authorization is enforced by API Gateway (Cognito User Pool authorizer).
    # We only read the already-verified claims exposed by API Gateway.
    claims = _get_cognito_claims_from_apig(event)
    if not claims:
        return _response(401, {'error': 'Unauthorized'})

    user_sub = claims.get('sub') or ''
    user_email = claims.get('email') or ''
    path = event.get('path', '')
    method = (event.get('httpMethod') or 'GET').upper()

    # Parse body
    raw_body = event.get('body') or '{}'
    body = json.loads(raw_body) if isinstance(raw_body, str) else (raw_body or {})

    # Routing
    # Expected resources configured:
    #   /projects
    #   /projects/{id}
    project_id = None
    path_params = (event.get('pathParameters') or {})
    if 'id' in path_params:
        project_id = path_params['id']

    try:
        now = int(time.time())
        if method == 'GET' and project_id:
            # Fetch single project
            res = table.get_item(Key={'userSub': user_sub, 'projectId': project_id})
            item = res.get('Item')
            if not item:
                return _response(404, {'error': 'Not found'})
            return _response(200, {'project': item})

        if method == 'GET':
            # List by userSub
            res = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('userSub').eq(user_sub)
            )
            items = res.get('Items', [])
            return _response(200, {'projects': items})

        if method == 'POST' and project_id and path.endswith('/photo-upload-urls'):
            res = table.get_item(Key={'userSub': user_sub, 'projectId': project_id})
            project = res.get('Item')
            if not project:
                return _response(404, {'error': 'Not found'})

            try:
                upload_payload = _create_static_photo_upload_urls(
                    user_sub=user_sub,
                    project_id=project_id,
                    files=body.get('files'),
                )
            except ValueError as exc:
                return _response(400, {'error': str(exc)})
            except RuntimeError as exc:
                return _response(500, {'error': str(exc)})

            return _response(200, upload_payload)

        if method == 'POST' and not project_id:
            # Create project
            import uuid
            pid = body.get('projectId') or str(uuid.uuid4())
            title = (body.get('title') or 'Untitled').strip()
            item = {
                'userSub': user_sub,
                'projectId': pid,
                'title': title or 'Untitled',
                'email': user_email,
                'status': body.get('status') or 'draft',
                'progress': int(body.get('progress') or 0),
                'params': convert_floats_to_decimal(body.get('params') or {}),
                'createdAt': now,
                'updatedAt': now,
            }
            table.put_item(Item=item)
            return _response(200, {'project': item})

        if method in ('PUT', 'PATCH') and project_id:
            # Update mutable fields
            update_fields = {}
            for key in ('title', 'status', 'progress', 'params', 'upload', 'ml', 'photoLibrary'):
                if key in body:
                    # Convert floats to Decimal for DynamoDB compatibility
                    update_fields[key] = convert_floats_to_decimal(body[key])
            if not update_fields:
                return _response(400, {'error': 'No updatable fields provided'})

            # Build UpdateExpression
            exp = [f"#{k} = :{k}" for k in update_fields.keys()]
            names = {f"#{k}": k for k in update_fields.keys()}
            values = {f":{k}": v for k, v in update_fields.items()}
            exp.append('#updatedAt = :updatedAt')
            names['#updatedAt'] = 'updatedAt'
            values[':updatedAt'] = now

            table.update_item(
                Key={'userSub': user_sub, 'projectId': project_id},
                UpdateExpression='SET ' + ', '.join(exp),
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
            )
            return _response(200, {'ok': True})

        if method == 'POST' and project_id and path.endswith('/payment-session'):
            res = table.get_item(Key={'userSub': user_sub, 'projectId': project_id})
            project = res.get('Item')
            if not project:
                return _response(404, {'error': 'Not found'})

            payment_status = (project.get('paymentStatus') or '').lower()
            if _check_user_is_admin(user_sub):
                if payment_status != 'paid':
                    table.update_item(
                        Key={'userSub': user_sub, 'projectId': project_id},
                        UpdateExpression=(
                            'SET paymentStatus = :paymentStatus, '
                            'paymentDeadline = :paymentDeadline, '
                            '#updatedAt = :updatedAt'
                        ),
                        ExpressionAttributeNames={
                            '#updatedAt': 'updatedAt',
                        },
                        ExpressionAttributeValues={
                            ':paymentStatus': 'paid',
                            ':paymentDeadline': _admin_payment_deadline(),
                            ':updatedAt': now,
                        },
                    )
                model_link = _resolve_model_link(project) or FRONTEND_URL
                return _response(200, {'paymentLink': model_link})

            if payment_status == 'paid':
                return _response(409, {'error': 'Payment already completed'})

            try:
                payment_session = _create_payment_session(project, user_email)
            except RuntimeError as exc:
                return _response(500, {'error': str(exc)})

            payment_deadline = int(time.time()) + (14 * 24 * 60 * 60)
            table.update_item(
                Key={'userSub': user_sub, 'projectId': project_id},
                UpdateExpression=(
                    'SET paymentSessionId = :sessionId, '
                    'paymentLink = :paymentLink, '
                    'paymentStatus = :paymentStatus, '
                    '#updatedAt = :updatedAt, '
                    'paymentDeadline = if_not_exists(paymentDeadline, :paymentDeadline)'
                ),
                ExpressionAttributeNames={
                    '#updatedAt': 'updatedAt',
                },
                ExpressionAttributeValues={
                    ':sessionId': payment_session['id'],
                    ':paymentLink': payment_session['url'],
                    ':paymentStatus': 'pending',
                    ':updatedAt': now,
                    ':paymentDeadline': payment_deadline,
                },
            )

            return _response(200, {'paymentLink': payment_session['url']})

        if method == 'DELETE' and project_id:
            res = table.get_item(Key={'userSub': user_sub, 'projectId': project_id})
            project = res.get('Item')
            if not project:
                return _response(404, {'error': 'Not found'})

            payment_status = (project.get('paymentStatus') or '').lower()
            payment_session_id = project.get('paymentSessionId')
            payment_subscription_id = project.get('paymentSubscriptionId')

            if payment_status != 'paid' and payment_session_id:
                error = _expire_checkout_session(payment_session_id)
                if error:
                    return _response(502, {'error': error})

            if payment_subscription_id:
                error = _cancel_subscription(payment_subscription_id)
                if error:
                    return _response(502, {'error': error})

            cleanup_error = _cleanup_hosting(project)
            if cleanup_error:
                return _response(502, {'error': cleanup_error})

            table.delete_item(Key={'userSub': user_sub, 'projectId': project_id})
            return _response(200, {'ok': True})

        return _response(405, {'error': 'Method not allowed'})

    except Exception as e:
        print('Error:', e)
        return _response(500, {'error': 'Internal server error'})
