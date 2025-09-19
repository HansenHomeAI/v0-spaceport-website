"""Lambda handler for website contact form submissions."""
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

import resend

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

CONTACT_RECIPIENT = os.environ.get("CONTACT_RECIPIENT", "admin@spcprt.com")
CONTACT_SENDER = os.environ.get("CONTACT_SENDER", "Spaceport Contact <hello@spcprt.com>")
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

DEFAULT_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Credentials": "true",
}


def _response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
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


def _clean(value: Optional[str]) -> str:
    if not value:
        return ""
    return value.strip()


def _build_email(name: str, email: str, message: str) -> Dict[str, str]:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    safe_message_html = message.replace("\n", "<br />")

    text_body = (
        "A new message was submitted through the Spaceport contact form.\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Received: {timestamp}\n\n"
        "Message:\n"
        f"{message}\n"
    )

    html_body = (
        "<html><body>"
        "<h2>New Contact Form Submission</h2>"
        f"<p><strong>Name:</strong> {name}</p>"
        f"<p><strong>Email:</strong> {email}</p>"
        f"<p><strong>Received:</strong> {timestamp}</p>"
        "<h3>Message</h3>"
        f"<p>{safe_message_html}</p>"
        "</body></html>"
    )

    return {"text": text_body, "html": html_body}


def lambda_handler(event, _context):
    http_method = (event.get("httpMethod") or "").upper()

    if http_method == "OPTIONS":
        return _response(200, {"message": "CORS preflight"})

    if http_method != "POST":
        return _response(405, {"error": "Method not allowed"})

    if not RESEND_API_KEY:
        print("ERROR: RESEND_API_KEY environment variable is not set for contact form lambda.")
        return _response(500, {"error": "Email service not configured"})

    body = _parse_body(event)
    name = _clean(body.get("name"))
    email = _clean(body.get("email"))
    message = _clean(body.get("message"))

    if not name:
        return _response(400, {"error": "Please provide your name"})

    if not email or not EMAIL_REGEX.match(email):
        return _response(400, {"error": "Please provide a valid email address"})

    if not message:
        return _response(400, {"error": "Please include a message"})

    email_payload = _build_email(name, email, message)

    params: Dict[str, Any] = {
        "from": CONTACT_SENDER,
        "to": [CONTACT_RECIPIENT],
        "subject": "New Spaceport Contact Form Submission",
        "text": email_payload["text"],
        "html": email_payload["html"],
        "reply_to": [email],
    }

    try:
        print(f"RESEND_CONTACT_REQUEST: {json.dumps({k: (v if k != 'html' else '<omitted>') for k, v in params.items()})}")
        result = resend.Emails.send(params)
        print(f"RESEND_CONTACT_RESPONSE: {result}")
    except Exception as exc:
        print(f"RESEND_CONTACT_ERROR: {exc}")
        return _response(502, {"error": "Failed to send your message. Please try again."})

    return _response(200, {"message": "Thanks! We'll be in touch soon."})
