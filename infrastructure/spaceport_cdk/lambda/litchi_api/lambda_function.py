import json
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _cors_headers() -> Dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,authorization,X-Amz-Date,X-Amz-Security-Token,X-Api-Key",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    }


def _response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": _cors_headers(),
        "body": json.dumps(body),
    }


def _get_user_from_jwt(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    request_context = event.get("requestContext", {})
    authorizer = request_context.get("authorizer", {})
    claims = authorizer.get("claims", {})
    if not claims:
        logger.warning("Missing JWT claims in request context")
        return None

    return {
        "user_id": claims.get("sub"),
        "email": claims.get("email"),
        "preferred_username": claims.get("preferred_username"),
        "name": claims.get("name"),
    }


def _parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body")
    if not body:
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _table():
    table_name = os.environ.get("LITCHI_CREDENTIALS_TABLE")
    if not table_name:
        raise RuntimeError("LITCHI_CREDENTIALS_TABLE is not configured")
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)


def _invoke_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
    worker_name = os.environ.get("LITCHI_WORKER_FUNCTION")
    if not worker_name:
        raise RuntimeError("LITCHI_WORKER_FUNCTION is not configured")

    lambda_client = boto3.client("lambda")
    response = lambda_client.invoke(
        FunctionName=worker_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    status_code = response.get("StatusCode", 500)
    if status_code >= 400:
        raise RuntimeError(f"Worker invocation failed with status {status_code}")

    payload_stream = response.get("Payload")
    if not payload_stream:
        return {}

    raw_payload = payload_stream.read().decode("utf-8")
    if not raw_payload:
        return {}

    try:
        return json.loads(raw_payload)
    except json.JSONDecodeError:
        return {"raw": raw_payload}


def _handle_status(user_id: str) -> Dict[str, Any]:
    table = _table()
    item = table.get_item(Key={"userId": user_id}).get("Item", {})
    status = item.get("status", "not_connected")
    response = {
        "status": status,
        "connected": status == "active",
        "lastUsed": item.get("lastUsed"),
        "updatedAt": item.get("updatedAt"),
        "message": item.get("message"),
        "progress": item.get("progress"),
        "logs": item.get("logs", []),
        "needsTwoFactor": status == "pending_2fa",
    }
    return _response(200, response)


def _handle_connect(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    username = payload.get("username")
    password = payload.get("password")
    two_factor_code = payload.get("twoFactorCode")

    if not username or not password:
        return _response(400, {"error": "username and password are required"})

    worker_payload = {
        "mode": "login",
        "userId": user_id,
        "username": username,
        "password": password,
        "twoFactorCode": two_factor_code,
        "requestedAt": _now_iso(),
    }

    result = _invoke_worker(worker_payload)
    return _response(200, result if isinstance(result, dict) else {"result": result})


def _handle_test_connection(user_id: str) -> Dict[str, Any]:
    worker_payload = {
        "mode": "test",
        "userId": user_id,
        "requestedAt": _now_iso(),
    }
    result = _invoke_worker(worker_payload)
    return _response(200, result if isinstance(result, dict) else {"result": result})


def _handle_upload(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    missions = payload.get("missions")
    if not isinstance(missions, list) or not missions:
        return _response(400, {"error": "missions must be a non-empty list"})

    state_machine_arn = os.environ.get("LITCHI_STATE_MACHINE_ARN")
    if not state_machine_arn:
        return _response(500, {"error": "LITCHI_STATE_MACHINE_ARN is not configured"})

    sfn_client = boto3.client("stepfunctions")
    execution_name = f"litchi-{user_id[:8]}-{int(datetime.now(timezone.utc).timestamp())}"
    input_payload = {
        "userId": user_id,
        "missions": missions,
        "totalMissions": len(missions),
        "requestedAt": _now_iso(),
    }
    response = sfn_client.start_execution(
        stateMachineArn=state_machine_arn,
        name=execution_name,
        input=json.dumps(input_payload),
    )
    return _response(200, {
        "executionArn": response.get("executionArn"),
        "startDate": response.get("startDate").isoformat() if response.get("startDate") else None,
    })


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    if event.get("httpMethod") == "OPTIONS":
        return _response(200, {"ok": True})

    user = _get_user_from_jwt(event)
    if not user or not user.get("user_id"):
        return _response(401, {"error": "Unauthorized"})

    path = (event.get("path") or "").lower()
    method = event.get("httpMethod")
    payload = _parse_body(event)

    if method == "GET" and path.endswith("/status"):
        return _handle_status(user["user_id"])

    if method == "POST" and path.endswith("/connect"):
        return _handle_connect(user["user_id"], payload)

    if method == "POST" and path.endswith("/test-connection"):
        return _handle_test_connection(user["user_id"])

    if method == "POST" and path.endswith("/upload"):
        return _handle_upload(user["user_id"], payload)

    return _response(404, {"error": "Not found"})
