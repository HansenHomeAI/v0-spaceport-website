import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.config import Config
from botocore.exceptions import ClientError
import resend


logger = logging.getLogger()
logger.setLevel(logging.INFO)

PROJECTS_TABLE_NAME = os.environ.get('PROJECTS_TABLE_NAME')
PERMISSIONS_TABLE_NAME = os.environ.get('PERMISSIONS_TABLE_NAME', 'Spaceport-BetaAccessPermissions')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
R2_ENDPOINT = os.environ.get('R2_ENDPOINT')
R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', 'spaces-viewers')
R2_REGION = os.environ.get('R2_REGION', 'auto')

if not PROJECTS_TABLE_NAME:
    raise RuntimeError('PROJECTS_TABLE_NAME must be configured')

resend.api_key = RESEND_API_KEY

dynamodb = boto3.resource('dynamodb')
projects_table = dynamodb.Table(PROJECTS_TABLE_NAME)
permissions_table = dynamodb.Table(PERMISSIONS_TABLE_NAME)


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


def _filter_admin_projects(projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    for project in projects:
        user_sub = project.get('userSub')
        if user_sub and _check_user_is_admin(user_sub):
            logger.info('Skipping admin project %s from payment enforcement', project.get('projectId'))
            continue
        filtered.append(project)
    return filtered


def _get_r2_client() -> Optional[Any]:
    if not (R2_ENDPOINT and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY):
        logger.warning('R2 configuration missing; skipping viewer updates.')
        return None

    return boto3.client(
        's3',
        region_name=R2_REGION,
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4'),
    )


def _r2_object_exists(client: Any, bucket: str, key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        code = exc.response.get('Error', {}).get('Code')
        if code in ('404', 'NoSuchKey', 'NotFound'):
            return False
        raise


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


def _placeholder_html(project_title: str, payment_link: Optional[str]) -> str:
    heading = project_title or 'Hosting paused'
    payment_block = ''
    if payment_link:
        payment_block = f"""
        <a class="link" href="{payment_link}">Complete payment</a>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Hosting paused</title>
  <style>
    :root {{ color-scheme: dark; }}
    body {{
      margin: 0;
      font-family: "Helvetica Neue", Arial, sans-serif;
      background: #050505;
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 32px;
    }}
    .card {{
      max-width: 520px;
      background: #0b0b0b;
      border-radius: 25px;
      padding: 32px;
      text-align: center;
      border: 1px solid rgba(255, 255, 255, 0.08);
      box-shadow: 0 18px 40px rgba(0, 0, 0, 0.45);
    }}
    .title {{
      font-size: 24px;
      margin: 0 0 12px;
    }}
    .body {{
      font-size: 16px;
      line-height: 1.6;
      color: rgba(255, 255, 255, 0.5);
      margin: 0 0 20px;
    }}
    .link {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 12px 20px;
      border-radius: 25px;
      border: 1px solid rgba(255, 255, 255, 0.5);
      color: #ffffff;
      text-decoration: none;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1 class="title">{heading}</h1>
    <p class="body">
      Hosting is paused while payment is pending. Please complete payment to restore access.
    </p>
    {payment_block}
  </div>
</body>
</html>
"""


def _send_revocation_email(recipient_email: str, project_title: str, payment_link: Optional[str]) -> None:
    if not RESEND_API_KEY:
        logger.warning('RESEND_API_KEY not configured; skipping revocation email.')
        return

    subject = f'Hosting paused: {project_title or "Spaceport AI Project"}'
    payment_line = f"\nPayment link: {payment_link}\n" if payment_link else ""

    text_body = (
        f"Hosting is paused for {project_title or 'your project'}.\n"
        "Payment was not received within 14 days, so the viewer is temporarily offline.\n"
        "Complete payment to restore access."
        f"{payment_line}"
        "\n- Spaceport AI"
    )

    payment_button = ''
    if payment_link:
        payment_button = f"""
        <p style="text-align:center;margin:24px 0;">
          <a href="{payment_link}" style="display:inline-flex;padding:12px 20px;border-radius:25px;border:1px solid rgba(255,255,255,0.6);color:#ffffff;text-decoration:none;font-weight:600;">
            Complete payment
          </a>
        </p>
        """

    html_body = f"""
    <html>
      <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background-color:#050505;color:#ffffff;padding:32px;">
        <h1 style="font-size:24px;margin-bottom:16px;">Hosting paused</h1>
        <p style="font-size:16px;line-height:1.6;color:rgba(255,255,255,0.6);">
          Payment was not received within 14 days for {project_title or 'your project'}.
          The viewer has been paused until payment is completed.
        </p>
        {payment_button}
        <p style="font-size:14px;margin-top:32px;color:rgba(255,255,255,0.6);">- Spaceport AI</p>
      </body>
    </html>
    """

    resend.Emails.send({
        'from': 'Spaceport AI <hello@spcprt.com>',
        'to': [recipient_email],
        'subject': subject,
        'html': html_body,
        'text': text_body,
    })


def _soft_revoke_viewer(project: Dict[str, Any]) -> None:
    if not R2_BUCKET_NAME:
        logger.warning('R2_BUCKET_NAME missing; cannot update viewer.')
        return

    slug = _resolve_viewer_slug(project)
    if not slug:
        logger.warning('Unable to resolve viewer slug for project revoke.')
        return

    client = _get_r2_client()
    if not client:
        return

    index_key = f"models/{slug}/index.html"
    original_key = f"models/{slug}/original.html"

    try:
        if not _r2_object_exists(client, R2_BUCKET_NAME, original_key):
            if _r2_object_exists(client, R2_BUCKET_NAME, index_key):
                client.copy_object(
                    Bucket=R2_BUCKET_NAME,
                    CopySource={'Bucket': R2_BUCKET_NAME, 'Key': index_key},
                    Key=original_key,
                )
                logger.info('Saved original viewer for slug %s', slug)
            else:
                logger.warning('index.html missing for slug %s; creating placeholder only.', slug)
        else:
            logger.info('original.html already exists for slug %s; leaving as-is.', slug)

        placeholder = _placeholder_html(project.get('title') or project.get('projectTitle'), project.get('paymentLink'))
        client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=index_key,
            Body=placeholder.encode('utf-8'),
            ContentType='text/html; charset=utf-8',
            CacheControl='no-store',
        )
    except ClientError as exc:
        logger.error('Failed to revoke viewer for slug %s: %s', slug, exc)


def _extract_recipient_email(project: Dict[str, Any]) -> Optional[str]:
    delivery = project.get('delivery') or {}
    return (
        delivery.get('recipientEmail')
        or project.get('clientEmail')
        or project.get('email')
    )


def _revoke_project(project: Dict[str, Any]) -> None:
    user_sub = project.get('userSub')
    project_id = project.get('projectId')
    if not user_sub or not project_id:
        logger.warning('Project missing keys; cannot revoke.')
        return

    now_epoch = int(datetime.now(timezone.utc).timestamp())

    projects_table.update_item(
        Key={'userSub': user_sub, 'projectId': project_id},
        UpdateExpression='SET #status = :status, revokedAt = :revokedAt, updatedAt = :updatedAt',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':status': 'revoked',
            ':revokedAt': now_epoch,
            ':updatedAt': now_epoch,
        },
    )

    _soft_revoke_viewer(project)

    recipient_email = _extract_recipient_email(project)
    if recipient_email:
        _send_revocation_email(recipient_email, project.get('title') or project.get('projectTitle'), project.get('paymentLink'))
    else:
        logger.warning('No recipient email found for project %s', project_id)


def _scan_overdue_projects(now_epoch: int) -> List[Dict[str, Any]]:
    overdue: List[Dict[str, Any]] = []
    filter_expression = (
        Attr('paymentStatus').eq('pending')
        & Attr('paymentDeadline').lt(now_epoch)
        & Attr('status').eq('delivered')
    )

    last_evaluated_key = None
    while True:
        scan_kwargs = {'FilterExpression': filter_expression}
        if last_evaluated_key:
            scan_kwargs['ExclusiveStartKey'] = last_evaluated_key

        response = projects_table.scan(**scan_kwargs)
        overdue.extend(response.get('Items', []))
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

    return overdue


def _scan_revoked_projects(now_epoch: int) -> List[Dict[str, Any]]:
    revoked: List[Dict[str, Any]] = []
    filter_expression = (
        Attr('paymentStatus').eq('pending')
        & Attr('paymentDeadline').lt(now_epoch)
        & Attr('status').eq('revoked')
    )

    last_evaluated_key = None
    while True:
        scan_kwargs = {'FilterExpression': filter_expression}
        if last_evaluated_key:
            scan_kwargs['ExclusiveStartKey'] = last_evaluated_key

        response = projects_table.scan(**scan_kwargs)
        revoked.extend(response.get('Items', []))
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

    return revoked


def lambda_handler(event, context):
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    overdue_projects = _filter_admin_projects(_scan_overdue_projects(now_epoch))
    revoked_projects = _filter_admin_projects(_scan_revoked_projects(now_epoch))

    logger.info('Found %s overdue projects', len(overdue_projects))
    if revoked_projects:
        logger.info('Found %s revoked projects to reapply', len(revoked_projects))

    for project in overdue_projects:
        try:
            _revoke_project(project)
        except Exception as exc:
            logger.error('Failed to revoke project %s: %s', project.get('projectId'), exc)

    for project in revoked_projects:
        try:
            _soft_revoke_viewer(project)
        except Exception as exc:
            logger.error('Failed to reapply revocation for project %s: %s', project.get('projectId'), exc)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'revokedCount': len(overdue_projects),
            'reappliedCount': len(revoked_projects),
        }),
    }
