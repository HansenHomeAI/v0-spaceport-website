import json
import os
from datetime import datetime
from typing import Any, Dict, List

import resend

# Configure Resend client lazily to avoid issues during cold start tests
API_KEY = os.environ.get("RESEND_API_KEY", "")
if API_KEY:
    resend.api_key = API_KEY

RECIPIENTS_ENV = os.environ.get("FEEDBACK_RECIPIENTS", "")
RECIPIENTS: List[str] = [email.strip() for email in RECIPIENTS_ENV.split(",") if email.strip()]
DEFAULT_RECIPIENTS = [
    "gabriel@spcprt.com",
    "ethan@spcprt.com",
    "hello@spcprt.com",
]

SENDER = os.environ.get("FEEDBACK_FROM_EMAIL", "Spaceport AI <hello@spcprt.com>")
SUBJECT = os.environ.get("FEEDBACK_SUBJECT", "Spaceport AI Website Feedback")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Credentials": "true",
}


def _build_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }


def _resolve_recipients() -> List[str]:
    return RECIPIENTS or DEFAULT_RECIPIENTS


def _extract_payload(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body")
    if isinstance(body, str) and body:
        return json.loads(body)
    if isinstance(body, dict):
        return body
    return {}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return _build_response(200, {"message": "CORS preflight"})

    try:
        payload = _extract_payload(event)
    except json.JSONDecodeError:
        return _build_response(400, {"error": "Invalid JSON payload"})

    feedback_text = (payload.get("feedback") or "").strip()
    contact = (payload.get("contact") or "").strip()

    if not feedback_text:
        return _build_response(400, {"error": "Feedback message is required"})

    if len(feedback_text) > 5000:
        return _build_response(400, {"error": "Feedback message is too long"})

    timestamp = datetime.utcnow().isoformat() + "Z"
    recipients = _resolve_recipients()

    if not API_KEY:
        # Log internally but respond gracefully to avoid leaking secrets expectations
        print("FeedbackEmailWarning: RESEND_API_KEY is not configured")
        return _build_response(500, {"error": "Email service temporarily unavailable"})

    message_lines = [
        f"Received at: {timestamp}",
        "",
        "Feedback:",
        feedback_text,
    ]

    if contact:
        message_lines.extend(["", f"Contact info: {contact}"])

    text_body = "\n".join(message_lines)
    html_body = "<br/>".join(line or "&nbsp;" for line in message_lines)

    try:
        response = resend.Emails.send(
            params={
                "from": SENDER,
                "to": recipients,
                "subject": SUBJECT,
                "text": text_body,
                "html": f"<p>{html_body}</p>",
            }
        )
        message_id = getattr(response, "id", "unknown")
        print(f"FeedbackEmailDispatched: id={message_id} recipients={recipients}")
    except Exception as exc:  # noqa: BLE001
        print(f"FeedbackEmailError: {type(exc).__name__}: {exc}")
        return _build_response(502, {"error": "Failed to send feedback"})

    return _build_response(200, {"message": "Feedback sent successfully"})
