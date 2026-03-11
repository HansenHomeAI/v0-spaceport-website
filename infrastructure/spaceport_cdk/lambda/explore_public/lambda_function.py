import base64
import json
import os
from typing import Any, Dict, List, Optional, Tuple

import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal


dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('EXPLORE_LISTINGS_TABLE_NAME')
PROJECTS_TABLE_NAME = os.environ.get('PROJECTS_TABLE_NAME')
VISIBILITY_INDEX = os.environ.get('EXPLORE_LISTINGS_VISIBILITY_INDEX', 'visibility-updatedAt-index')
DEFAULT_LIMIT = 24
MAX_LIMIT = 100


def _cors_headers() -> Dict[str, str]:
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,authorization,X-Amz-Date,X-Amz-Security-Token,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,OPTIONS',
        'Cache-Control': 'public, max-age=60',
    }


def _response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'statusCode': status,
        'headers': _cors_headers(),
        'body': json.dumps(body, default=_json_default),
    }


def _encode_cursor(key: Optional[Dict[str, Any]]) -> Optional[str]:
    if not key:
        return None
    raw = json.dumps(key, default=_json_default).encode('utf-8')
    return base64.urlsafe_b64encode(raw).decode('utf-8')


def _decode_cursor(cursor: Optional[str]) -> Optional[Dict[str, Any]]:
    if not cursor:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode('utf-8'))
        return json.loads(raw.decode('utf-8'))
    except Exception:
        return None


def _json_default(value: Any):
    if isinstance(value, Decimal):
        as_int = int(value)
        return as_int if value == as_int else float(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _to_number(value: Any) -> int:
    if isinstance(value, Decimal):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _shape_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': item.get('listingId') or item.get('projectId') or item.get('viewerSlug') or '',
        'title': item.get('viewerTitle') or item.get('projectTitle') or 'Untitled',
        'location': item.get('cityState') or '',
        'viewerUrl': item.get('viewerUrl') or item.get('modelLink') or '',
        'thumbnailUrl': item.get('thumbnailUrl') or '',
        'updatedAt': _to_number(item.get('updatedAt')),
    }


def _resolve_project_value(project: Dict[str, Any], keys: List[str]) -> str:
    delivery = project.get('delivery') or {}
    for key in keys:
        value = delivery.get(key) or project.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def _build_thumbnail_url(viewer_url: str) -> str:
    return f"{viewer_url.rstrip('/')}/thumb.jpg"


def _shape_project_item(project: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if (project.get('status') or '').lower() != 'delivered':
        return None
    if (project.get('paymentStatus') or '').lower() != 'paid':
        return None

    viewer_url = _resolve_project_value(
        project,
        [
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
        ],
    )
    if not viewer_url:
        return None

    return {
        'id': project.get('projectId') or _resolve_project_value(project, ['viewerSlug', 'viewer_slug']) or '',
        'title': _resolve_project_value(project, ['viewerTitle', 'viewer_title']) or project.get('title') or 'Untitled',
        'location': project.get('cityState') or '',
        'viewerUrl': viewer_url,
        'thumbnailUrl': project.get('thumbnailUrl') or _build_thumbnail_url(viewer_url),
        'updatedAt': max(_to_number(project.get('updatedAt')), _to_number(project.get('createdAt'))),
    }


def _load_listing_items(
    table,
    *,
    visibility: str,
    limit: int,
    cursor: Optional[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    response: Dict[str, Any] = {}
    try:
        query_params: Dict[str, Any] = {
            'IndexName': VISIBILITY_INDEX,
            'KeyConditionExpression': Key('visibility').eq(visibility),
            'Limit': limit,
            'ScanIndexForward': False,
        }
        if cursor:
            query_params['ExclusiveStartKey'] = cursor
        response = table.query(**query_params)
        items = response.get('Items', []) or []
    except Exception:
        items = []
        scan_start_key = cursor
        while True:
            scan_params: Dict[str, Any] = {
                'FilterExpression': Attr('visibility').eq(visibility),
                'Limit': limit,
            }
            if scan_start_key:
                scan_params['ExclusiveStartKey'] = scan_start_key
            response = table.scan(**scan_params)
            items.extend(response.get('Items', []) or [])
            scan_start_key = response.get('LastEvaluatedKey')
            if len(items) >= limit or not scan_start_key:
                break
        items = items[:limit]

    items.sort(key=lambda item: item.get('updatedAt', 0), reverse=True)
    return items, response.get('LastEvaluatedKey')


def _load_project_fallback_items(limit: int) -> List[Dict[str, Any]]:
    if not PROJECTS_TABLE_NAME:
        return []

    table = dynamodb.Table(PROJECTS_TABLE_NAME)
    items: List[Dict[str, Any]] = []
    scan_start_key = None

    while True:
        scan_params: Dict[str, Any] = {
            'Limit': max(limit * 3, 50),
        }
        if scan_start_key:
            scan_params['ExclusiveStartKey'] = scan_start_key
        response = table.scan(**scan_params)
        for project in response.get('Items', []) or []:
            shaped = _shape_project_item(project)
            if shaped:
                items.append(shaped)
        scan_start_key = response.get('LastEvaluatedKey')
        if len(items) >= limit or not scan_start_key:
            break

    items.sort(key=lambda item: item.get('updatedAt', 0), reverse=True)
    return items


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return _response(200, {'ok': True})

    if not TABLE_NAME:
        return _response(500, {'error': 'Explore listings table not configured'})

    table = dynamodb.Table(TABLE_NAME)
    params = event.get('queryStringParameters') or {}
    limit_raw = params.get('limit') or ''
    cursor = _decode_cursor(params.get('cursor'))
    visibility = (params.get('visibility') or 'public').strip().lower() or 'public'

    try:
        limit = int(limit_raw) if str(limit_raw).isdigit() else DEFAULT_LIMIT
    except ValueError:
        limit = DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))

    items, next_key = _load_listing_items(
        table,
        visibility=visibility,
        limit=limit,
        cursor=cursor,
    )

    shaped = [_shape_item(item) for item in items if item.get('viewerUrl')]
    if not shaped:
        project_fallbacks = _load_project_fallback_items(limit)
        by_viewer_url = {
            item['viewerUrl']: item
            for item in shaped
            if item.get('viewerUrl')
        }
        for item in project_fallbacks:
            if item['viewerUrl'] not in by_viewer_url:
                by_viewer_url[item['viewerUrl']] = item
        shaped = sorted(
            by_viewer_url.values(),
            key=lambda item: item.get('updatedAt', 0),
            reverse=True,
        )[:limit]
        next_cursor = None
    else:
        next_cursor = _encode_cursor(next_key)

    return _response(200, {
        'items': shaped,
        'nextCursor': next_cursor,
    })
