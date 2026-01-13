#!/usr/bin/env python3
"""
End-to-end lifecycle check for model payment enforcement.
Requires real AWS + Stripe config.
"""

import hashlib
import hmac
import json
import os
import sys
import time
from typing import Dict, Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import boto3


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def _post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request) as response:
            data = response.read().decode("utf-8")
            return {"status": response.status, "body": data}
    except HTTPError as exc:
        data = exc.read().decode("utf-8")
        return {"status": exc.code, "body": data}


def _sign_stripe_payload(payload: str, secret: str) -> str:
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def main() -> int:
    send_url = _require_env("MODEL_DELIVERY_SEND_URL")
    admin_jwt = _require_env("MODEL_DELIVERY_ADMIN_JWT")
    client_email = _require_env("TEST_CLIENT_EMAIL")
    project_id = _require_env("TEST_PROJECT_ID")
    model_link = _require_env("TEST_MODEL_LINK")
    user_sub = os.environ.get("TEST_USER_SUB")

    region = os.environ.get("AWS_REGION", "us-west-2")
    projects_table_name = _require_env("PROJECTS_TABLE_NAME")
    enforce_lambda = _require_env("ENFORCE_MODEL_PAYMENTS_LAMBDA_NAME")

    viewer_slug = os.environ.get("TEST_VIEWER_SLUG")
    viewer_title = os.environ.get("TEST_VIEWER_TITLE")

    payload = {
        "clientEmail": client_email,
        "projectId": project_id,
        "modelLink": model_link,
    }
    if viewer_slug:
        payload["viewerSlug"] = viewer_slug
    if viewer_title:
        payload["viewerTitle"] = viewer_title

    print("Step 1: Trigger delivery and payment session...")
    response = _post_json(
        send_url,
        payload,
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {admin_jwt}",
        },
    )
    if response["status"] != 200:
        print(response["body"])
        raise SystemExit("Delivery API failed.")

    body = json.loads(response["body"])
    payment = body.get("payment") or {}
    payment_link = payment.get("paymentLink")
    if not payment_link:
        raise SystemExit("Missing payment link in response.")

    if not user_sub:
        user_sub = body.get("project", {}).get("userSub")
    if not user_sub:
        raise SystemExit("Missing TEST_USER_SUB or project.userSub.")

    dynamodb = boto3.resource("dynamodb", region_name=region)
    projects_table = dynamodb.Table(projects_table_name)

    project = projects_table.get_item(Key={"userSub": user_sub, "projectId": project_id}).get("Item")
    if not project or project.get("paymentLink") != payment_link:
        raise SystemExit("Payment link not stored on project record.")

    print("Step 2: Force deadline to past and invoke enforcement lambda...")
    overdue_deadline = int(time.time()) - 3600
    projects_table.update_item(
        Key={"userSub": user_sub, "projectId": project_id},
        UpdateExpression="SET paymentDeadline = :deadline, paymentStatus = :status, #status = :project_status",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":deadline": overdue_deadline,
            ":status": "pending",
            ":project_status": "delivered",
        },
    )

    lambda_client = boto3.client("lambda", region_name=region)
    lambda_client.invoke(
        FunctionName=enforce_lambda,
        InvocationType="RequestResponse",
        Payload=b"{}",
    )

    project = projects_table.get_item(Key={"userSub": user_sub, "projectId": project_id}).get("Item")
    if not project or project.get("status") != "revoked":
        raise SystemExit("Project status did not change to revoked.")

    webhook_url = os.environ.get("SUBSCRIPTION_WEBHOOK_URL")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if webhook_url and webhook_secret:
        print("Step 3: Simulate Stripe webhook payment...")
        event = {
            "id": "evt_test_model_payment",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_model_payment",
                    "subscription": "sub_test_model_payment",
                    "metadata": {
                        "projectId": project_id,
                        "userSub": user_sub,
                    },
                }
            },
        }
        payload_json = json.dumps(event)
        signature = _sign_stripe_payload(payload_json, webhook_secret)
        response = _post_json(
            webhook_url,
            event,
            {
                "Content-Type": "application/json",
                "Stripe-Signature": signature,
            },
        )
        if response["status"] != 200:
            print(response["body"])
            raise SystemExit("Webhook call failed.")

        project = projects_table.get_item(Key={"userSub": user_sub, "projectId": project_id}).get("Item")
        if project.get("paymentStatus") != "paid":
            raise SystemExit("Payment status did not update to paid.")
        if project.get("status") != "delivered":
            raise SystemExit("Project was not restored to delivered status.")
    else:
        print("Step 3: Skipped webhook simulation (missing SUBSCRIPTION_WEBHOOK_URL or STRIPE_WEBHOOK_SECRET).")

    print("Lifecycle test completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
