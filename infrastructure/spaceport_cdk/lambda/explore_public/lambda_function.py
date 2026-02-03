import base64
import json
import os
from typing import Any, Dict, Optional

import boto3
from boto3.dynamodb.conditions import Key, Attr


dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('EXPLORE_LISTINGS_TABLE_NAME')
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
        'body': json.dumps(body),
    }


def _encode_cursor(key: Optional[Dict[str, Any]]) -> Optional[str]:
    if not key:
        return None
    raw = json.dumps(key).encode('utf-8')
    return base64.urlsafe_b64encode(raw).decode('utf-8')


def _decode_cursor(cursor: Optional[str]) -> Optional[Dict[str, Any]]:
    if not cursor:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode('utf-8'))
        return json.loads(raw.decode('utf-8'))
    except Exception:
        return None


def _shape_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': item.get('listingId') or item.get('projectId') or item.get('viewerSlug') or '',
        'title': item.get('viewerTitle') or item.get('projectTitle') or 'Untitled',
        'location': item.get('cityState') or '',
        'viewerUrl': item.get('viewerUrl') or item.get('modelLink') or '',
        'thumbnailUrl': item.get('thumbnailUrl') or '',
        'updatedAt': item.get('updatedAt') or 0,
    }


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

    # Ensure a predictable order when we fall back to a scan.
    items.sort(key=lambda item: item.get('updatedAt', 0), reverse=True)
    shaped = [_shape_item(item) for item in items if item.get('viewerUrl')]
    next_cursor = _encode_cursor(response.get('LastEvaluatedKey'))

    return _response(200, {
        'items': shaped,
        'nextCursor': next_cursor,
    })
