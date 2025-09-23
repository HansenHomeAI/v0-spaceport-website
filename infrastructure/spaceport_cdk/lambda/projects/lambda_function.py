import json
import os
import time
import urllib.request
from typing import Any, Dict, Optional
from decimal import Decimal

import boto3


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


dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['PROJECTS_TABLE_NAME']
table = dynamodb.Table(TABLE_NAME)


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
            for key in ('title', 'status', 'progress', 'params', 'upload', 'ml', 'delivery'):
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

        if method == 'DELETE' and project_id:
            table.delete_item(Key={'userSub': user_sub, 'projectId': project_id})
            return _response(200, {'ok': True})

        return _response(405, {'error': 'Method not allowed'})

    except Exception as e:
        print('Error:', e)
        return _response(500, {'error': 'Internal server error'})

