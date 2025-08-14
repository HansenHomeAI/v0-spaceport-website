import json
import os
import time
import urllib.request
from typing import Any, Dict, Optional

import boto3
from jose import jwk, jwt
from jose.utils import base64url_decode


dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['PROJECTS_TABLE_NAME']
table = dynamodb.Table(TABLE_NAME)


def _cors_headers() -> Dict[str, str]:
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    }


def _response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'statusCode': status,
        'headers': _cors_headers(),
        'body': json.dumps(body),
    }


class AuthError(Exception):
    pass


def _load_json_url(url: str) -> Dict[str, Any]:
    with urllib.request.urlopen(url) as r:  # nosec - trusted AWS domain from token iss
        return json.loads(r.read().decode('utf-8'))


def _verify_cognito_jwt(auth_header: Optional[str]) -> Dict[str, Any]:
    if not auth_header or not auth_header.lower().startswith('bearer '):
        raise AuthError('Missing or invalid Authorization header')
    token = auth_header.split(' ', 1)[1]

    # Decode unverified to obtain issuer and kid
    unverified = jwt.get_unverified_claims(token)
    header = jwt.get_unverified_header(token)
    kid = header.get('kid')
    iss = unverified.get('iss')
    if not iss or not kid:
        raise AuthError('Invalid token')

    # Fetch JWKS for this issuer
    jwks_url = f"{iss}/.well-known/jwks.json"
    keys = _load_json_url(jwks_url).get('keys', [])
    key = next((k for k in keys if k.get('kid') == kid), None)
    if not key:
        raise AuthError('Signing key not found')

    public_key = jwk.construct(key)
    message, encoded_sig = str(token).rsplit('.', 1)
    decoded_sig = base64url_decode(encoded_sig.encode('utf-8'))
    if not public_key.verify(message.encode('utf-8'), decoded_sig):
        raise AuthError('Invalid signature')

    # Validate standard claims (issuer, exp). Skip audience to support multiple clients
    claims = jwt.decode(token, public_key.to_pem().decode('utf-8'), options={'verify_aud': False}, issuer=iss)
    return claims


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return _response(200, {'ok': True})

    try:
        claims = _verify_cognito_jwt((event.get('headers') or {}).get('Authorization'))
    except AuthError as e:
        return _response(401, {'error': str(e)})
    except Exception:
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
                'params': body.get('params') or {},
                'createdAt': now,
                'updatedAt': now,
            }
            table.put_item(Item=item)
            return _response(200, {'project': item})

        if method in ('PUT', 'PATCH') and project_id:
            # Update mutable fields
            update_fields = {}
            for key in ('title', 'status', 'progress', 'params', 'upload', 'ml'):
                if key in body:
                    update_fields[key] = body[key]
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


