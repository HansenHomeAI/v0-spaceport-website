import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

import resend

# Configure Resend client once at import time
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

ADMIN_RECIPIENTS = [
    "gabriel@spcprt.com",
    "ethan@spcprt.com",
    "hello@spcprt.com",
]

DEFAULT_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Credentials": "true",
}


def _response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Return a JSON API Gateway response with shared headers."""
    return {
        "statusCode": status_code,
        "headers": DEFAULT_HEADERS,
        "body": json.dumps(body),
    }


def _parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body")
    if body is None:
        return {}
    if isinstance(body, dict):
        return body
    try:
        return json.loads(body)
    except (TypeError, json.JSONDecodeError):
        return {}


def _build_email_content(
    message: str,
    *,
    name: Optional[str],
    email: Optional[str],
    page_url: Optional[str],
    user_agent: Optional[str],
) -> Dict[str, str]:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    details_lines = []
    if name:
        details_lines.append(f"Name: {name}")
    if email:
        details_lines.append(f"Email: {email}")
    if page_url:
        details_lines.append(f"Page URL: {page_url}")
    details_lines.append(f"Submitted: {timestamp}")
    if user_agent:
        details_lines.append(f"User Agent: {user_agent}")

    details_text = "\n".join(details_lines)
    details_html = "".join(f"<p><strong>{line.split(': ', 1)[0]}:</strong> {line.split(': ', 1)[1] if ': ' in line else ''}</p>" for line in details_lines)

    message_html = message.replace("\n", "<br />")

    text_body = (
        "New feedback submitted via the Spaceport site.\n\n"
        + (details_text + "\n\n" if details_text else "")
        + "Feedback Message:\n"
        + message
    )

    html_body = (
        "<html><body>"
        "<h2>New Spaceport Feedback</h2>"
        + details_html
        + "<h3>Feedback Message</h3>"
        + f"<p>{message_html}</p>"
        + "</body></html>"
    )

    return {"text": text_body, "html": html_body}


def lambda_handler(event, _context):
    # Support CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return _response(200, {"message": "CORS preflight"})

    if event.get("httpMethod") != "POST":
        return _response(405, {"error": "Method not allowed"})

    if not RESEND_API_KEY:
        print("ERROR: RESEND_API_KEY environment variable is not set.")
        return _response(500, {"error": "Email service not configured"})

    body = _parse_body(event)
    message = (body.get("message") or body.get("feedback") or "").strip()
    name = (body.get("name") or "").strip() or None
    email = (body.get("email") or "").strip() or None
    page_url = (body.get("pageUrl") or body.get("page_url") or "").strip() or None

    if not message:
        return _response(400, {"error": "Feedback message is required"})

    if email and "@" not in email:
        return _response(400, {"error": "Please provide a valid email address"})

    user_agent = None
    headers = event.get("headers") or {}
    if isinstance(headers, dict):
        user_agent = headers.get("User-Agent") or headers.get("user-agent")

    email_content = _build_email_content(
        message,
        name=name,
        email=email,
        page_url=page_url,
        user_agent=user_agent,
    )

    params = {
        "from": "Spaceport AI Feedback <hello@spcprt.com>",
        "to": ADMIN_RECIPIENTS,
        "subject": "New Website Feedback",
        "html": email_content["html"],
        "text": email_content["text"],
    }

    if email:
        params["reply_to"] = [email]

    try:
        print(f"RESEND_REQUEST: {json.dumps({k: v if k != 'html' else '<omitted>' for k, v in params.items()})}")
        response = resend.Emails.send(params)
        print(f"RESEND_RESPONSE: {response}")
    except Exception as exc:
        print(f"RESEND_ERROR: {exc}")
        return _response(502, {"error": "Failed to send feedback"})

    return _response(200, {"message": "Feedback sent successfully"})
