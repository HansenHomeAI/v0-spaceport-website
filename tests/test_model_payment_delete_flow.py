#!/usr/bin/env python3
"""
Validate project deletion cleanup:
- Expire pending checkout sessions
- Cancel active subscriptions
- Remove hosted viewer assets
"""

import hashlib
import hmac
import json
import time
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import stripe


REGION = "us-west-2"
MODEL_LAMBDA = "Spaceport-ModelDeliveryAdminFunction-staging"
PROJECTS_LAMBDA = "Spaceport-ProjectsFunction-staging"
SUBSCRIPTION_LAMBDA = "Spaceport-SubscriptionManager-staging"


def _get_lambda_env(lambda_client, name):
    cfg = lambda_client.get_function_configuration(FunctionName=name)
    return cfg.get("Environment", {}).get("Variables", {})


def _create_admin_permission(table, admin_user_id):
    table.put_item(
        Item={
            "user_id": admin_user_id,
            "permission_type": "model_delivery_admin",
            "status": "active",
            "created_at": int(time.time()),
        }
    )


def _invoke_model_delivery(lambda_client, admin_user_id, client_email, project_id, model_link, viewer_slug, viewer_title):
    event = {
        "httpMethod": "POST",
        "path": "/admin/model-delivery/send",
        "body": json.dumps(
            {
                "clientEmail": client_email,
                "projectId": project_id,
                "modelLink": model_link,
                "viewerSlug": viewer_slug,
                "viewerTitle": viewer_title,
            }
        ),
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": admin_user_id,
                    "email": "admin-test@spcprt.com",
                    "preferred_username": "admin-test",
                }
            }
        },
    }
    response = lambda_client.invoke(
        FunctionName=MODEL_LAMBDA,
        InvocationType="RequestResponse",
        Payload=json.dumps(event).encode("utf-8"),
    )
    payload = json.loads(response["Payload"].read().decode("utf-8"))
    if payload.get("statusCode") != 200:
        raise RuntimeError(f"Delivery lambda failed: {payload}")
    return json.loads(payload.get("body") or "{}")


def _invoke_project_delete(lambda_client, user_sub, project_id):
    event = {
        "httpMethod": "DELETE",
        "path": f"/projects/{project_id}",
        "pathParameters": {"id": project_id},
        "requestContext": {
            "authorizer": {"claims": {"sub": user_sub, "email": "client-test@spcprt.com"}}
        },
    }
    response = lambda_client.invoke(
        FunctionName=PROJECTS_LAMBDA,
        InvocationType="RequestResponse",
        Payload=json.dumps(event).encode("utf-8"),
    )
    payload = json.loads(response["Payload"].read().decode("utf-8"))
    if payload.get("statusCode") != 200:
        raise RuntimeError(f"Project delete failed: {payload}")


def _head_missing(client, bucket, key):
    try:
        client.head_object(Bucket=bucket, Key=key)
        return False
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in ("404", "NoSuchKey", "NotFound"):
            return True
        raise


def _sign_stripe_payload(payload: str, secret: str) -> str:
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def _invoke_webhook(lambda_client, webhook_secret, project_id, user_sub, subscription_id):
    event_payload = {
        "id": "evt_test_project_delete",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_project_delete",
                "subscription": subscription_id,
                "metadata": {
                    "projectId": project_id,
                    "userSub": user_sub,
                },
            }
        },
    }
    raw_body = json.dumps(event_payload)
    sig_header = _sign_stripe_payload(raw_body, webhook_secret)
    webhook_event = {
        "httpMethod": "POST",
        "path": "/webhook",
        "headers": {"Stripe-Signature": sig_header},
        "body": raw_body,
        "isBase64Encoded": False,
    }
    response = lambda_client.invoke(
        FunctionName=SUBSCRIPTION_LAMBDA,
        InvocationType="RequestResponse",
        Payload=json.dumps(webhook_event).encode("utf-8"),
    )
    payload = json.loads(response["Payload"].read().decode("utf-8"))
    if payload.get("statusCode") != 200:
        raise RuntimeError(f"Webhook invocation failed: {payload}")


def main() -> int:
    lambda_client = boto3.client("lambda", region_name=REGION)
    model_env = _get_lambda_env(lambda_client, MODEL_LAMBDA)
    projects_env = _get_lambda_env(lambda_client, PROJECTS_LAMBDA)
    subscription_env = _get_lambda_env(lambda_client, SUBSCRIPTION_LAMBDA)

    required = [
        ("COGNITO_USER_POOL_ID", model_env.get("COGNITO_USER_POOL_ID")),
        ("PROJECTS_TABLE_NAME", model_env.get("PROJECTS_TABLE_NAME")),
        ("PERMISSIONS_TABLE_NAME", model_env.get("PERMISSIONS_TABLE_NAME")),
        ("STRIPE_SECRET_KEY", projects_env.get("STRIPE_SECRET_KEY")),
        ("STRIPE_WEBHOOK_SECRET", subscription_env.get("STRIPE_WEBHOOK_SECRET")),
        ("R2_ENDPOINT", projects_env.get("R2_ENDPOINT")),
        ("R2_ACCESS_KEY_ID", projects_env.get("R2_ACCESS_KEY_ID")),
        ("R2_SECRET_ACCESS_KEY", projects_env.get("R2_SECRET_ACCESS_KEY")),
        ("R2_BUCKET_NAME", projects_env.get("R2_BUCKET_NAME")),
    ]
    missing = [name for name, value in required if not value]
    if missing:
        raise SystemExit(f"Missing required env vars for test: {missing}")

    stripe.api_key = projects_env["STRIPE_SECRET_KEY"]

    r2_client = boto3.client(
        "s3",
        region_name=projects_env.get("R2_REGION", "auto"),
        endpoint_url=projects_env["R2_ENDPOINT"],
        aws_access_key_id=projects_env["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=projects_env["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
    )
    r2_bucket = projects_env["R2_BUCKET_NAME"]

    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    projects_table = dynamodb.Table(model_env["PROJECTS_TABLE_NAME"])
    permissions_table = dynamodb.Table(model_env["PERMISSIONS_TABLE_NAME"])
    user_pool_id = model_env["COGNITO_USER_POOL_ID"]
    cognito = boto3.client("cognito-idp", region_name=REGION)

    run_id = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
    admin_user_id = f"admin-delete-{run_id}"

    scenario_artifacts = []

    try:
        # Scenario A: pending checkout session is expired on delete.
        client_email_a = f"stripe-delete-pending+{run_id}@spcprt.com"
        preferred_username = f"stripe-delete-{run_id}"
        user_sub_a = None
        created_user_a = False
        try:
            resp = cognito.admin_create_user(
                UserPoolId=user_pool_id,
                Username=client_email_a,
                UserAttributes=[
                    {"Name": "email", "Value": client_email_a},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "name", "Value": "Stripe Delete Test"},
                    {"Name": "preferred_username", "Value": preferred_username},
                ],
                MessageAction="SUPPRESS",
            )
            created_user_a = True
            attrs = {a["Name"]: a["Value"] for a in resp["User"]["Attributes"]}
            user_sub_a = attrs.get("sub")
        except cognito.exceptions.UsernameExistsException:
            user = cognito.admin_get_user(UserPoolId=user_pool_id, Username=client_email_a)
            attrs = {a["Name"]: a["Value"] for a in user.get("UserAttributes", [])}
            user_sub_a = attrs.get("sub")

        if not user_sub_a:
            raise RuntimeError("Failed to resolve user sub for scenario A")

        _create_admin_permission(permissions_table, admin_user_id)

        project_id_a = f"project-pending-{run_id}"
        viewer_slug_a = f"delete-pending-{run_id}"
        viewer_title_a = "Pending Delete Viewer"
        model_link_a = f"https://spcprt.com/spaces/{viewer_slug_a}"

        now_epoch = int(time.time())
        projects_table.put_item(
            Item={
                "userSub": user_sub_a,
                "projectId": project_id_a,
                "title": viewer_title_a,
                "status": "delivered",
                "progress": 100,
                "viewerSlug": viewer_slug_a,
                "modelLink": model_link_a,
                "createdAt": now_epoch,
                "updatedAt": now_epoch,
            }
        )

        r2_client.put_object(
            Bucket=r2_bucket,
            Key=f"models/{viewer_slug_a}/index.html",
            Body=f"<html><body><h1>{viewer_title_a}</h1></body></html>",
            ContentType="text/html",
        )
        r2_client.put_object(
            Bucket=r2_bucket,
            Key=f"models/{viewer_slug_a}/original.html",
            Body="original content",
            ContentType="text/html",
        )

        delivery_body = _invoke_model_delivery(
            lambda_client,
            admin_user_id,
            client_email_a,
            project_id_a,
            model_link_a,
            viewer_slug_a,
            viewer_title_a,
        )
        payment = delivery_body.get("payment") or {}
        session_id = payment.get("paymentSessionId") or delivery_body.get("project", {}).get("paymentSessionId")
        if not session_id:
            session_id = projects_table.get_item(Key={"userSub": user_sub_a, "projectId": project_id_a}).get("Item", {}).get("paymentSessionId")
        if not session_id:
            raise RuntimeError("Missing payment session ID")

        _invoke_project_delete(lambda_client, user_sub_a, project_id_a)

        session = stripe.checkout.Session.retrieve(session_id)
        if session.status != "expired":
            raise RuntimeError(f"Checkout session not expired (status={session.status})")

        if not _head_missing(r2_client, r2_bucket, f"models/{viewer_slug_a}/index.html"):
            raise RuntimeError("index.html still exists after delete")
        if not _head_missing(r2_client, r2_bucket, f"models/{viewer_slug_a}/original.html"):
            raise RuntimeError("original.html still exists after delete")

        remaining = projects_table.get_item(Key={"userSub": user_sub_a, "projectId": project_id_a}).get("Item")
        if remaining:
            raise RuntimeError("Project record still exists after delete")

        scenario_artifacts.append(("scenario_a", user_sub_a, project_id_a, created_user_a, client_email_a))

        # Scenario B: active subscription is canceled on delete.
        client_email_b = f"stripe-delete-paid+{run_id}@spcprt.com"
        preferred_username_b = f"stripe-delete-paid-{run_id}"
        user_sub_b = None
        created_user_b = False
        try:
            resp = cognito.admin_create_user(
                UserPoolId=user_pool_id,
                Username=client_email_b,
                UserAttributes=[
                    {"Name": "email", "Value": client_email_b},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "name", "Value": "Stripe Delete Paid"},
                    {"Name": "preferred_username", "Value": preferred_username_b},
                ],
                MessageAction="SUPPRESS",
            )
            created_user_b = True
            attrs = {a["Name"]: a["Value"] for a in resp["User"]["Attributes"]}
            user_sub_b = attrs.get("sub")
        except cognito.exceptions.UsernameExistsException:
            user = cognito.admin_get_user(UserPoolId=user_pool_id, Username=client_email_b)
            attrs = {a["Name"]: a["Value"] for a in user.get("UserAttributes", [])}
            user_sub_b = attrs.get("sub")

        if not user_sub_b:
            raise RuntimeError("Failed to resolve user sub for scenario B")

        project_id_b = f"project-paid-{run_id}"
        viewer_slug_b = f"delete-paid-{run_id}"
        viewer_title_b = "Paid Delete Viewer"
        model_link_b = f"https://spcprt.com/spaces/{viewer_slug_b}"

        customer = stripe.Customer.create(email=client_email_b)
        price_id = model_env.get("STRIPE_MODEL_HOSTING_PRICE")
        if not price_id:
            raise RuntimeError("Missing STRIPE_MODEL_HOSTING_PRICE in model delivery env")

        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": price_id}],
            collection_method="send_invoice",
            days_until_due=30,
        )

        now_epoch = int(time.time())
        projects_table.put_item(
            Item={
                "userSub": user_sub_b,
                "projectId": project_id_b,
                "title": viewer_title_b,
                "status": "delivered",
                "progress": 100,
                "viewerSlug": viewer_slug_b,
                "modelLink": model_link_b,
                "createdAt": now_epoch,
                "updatedAt": now_epoch,
            }
        )

        r2_client.put_object(
            Bucket=r2_bucket,
            Key=f"models/{viewer_slug_b}/index.html",
            Body=f"<html><body><h1>{viewer_title_b}</h1></body></html>",
            ContentType="text/html",
        )

        _invoke_webhook(
            lambda_client,
            subscription_env["STRIPE_WEBHOOK_SECRET"],
            project_id_b,
            user_sub_b,
            subscription.id,
        )

        updated = projects_table.get_item(Key={"userSub": user_sub_b, "projectId": project_id_b}).get("Item")
        if not updated or updated.get("paymentSubscriptionId") != subscription.id:
            raise RuntimeError("paymentSubscriptionId not stored after webhook")
        if updated.get("paymentStatus") != "paid":
            raise RuntimeError("paymentStatus not updated after webhook")

        _invoke_project_delete(lambda_client, user_sub_b, project_id_b)

        subscription_after = stripe.Subscription.retrieve(subscription.id)
        if subscription_after.status not in ("canceled", "cancelled"):
            raise RuntimeError(f"Subscription not canceled (status={subscription_after.status})")

        if not _head_missing(r2_client, r2_bucket, f"models/{viewer_slug_b}/index.html"):
            raise RuntimeError("index.html still exists after delete (paid)")

        remaining = projects_table.get_item(Key={"userSub": user_sub_b, "projectId": project_id_b}).get("Item")
        if remaining:
            raise RuntimeError("Project record still exists after delete (paid)")

        scenario_artifacts.append(("scenario_b", user_sub_b, project_id_b, created_user_b, client_email_b))

        print("Delete flow test passed.")
        return 0
    finally:
        for _, user_sub, project_id, created_user, email in scenario_artifacts:
            try:
                projects_table.delete_item(Key={"userSub": user_sub, "projectId": project_id})
            except Exception:
                pass
            try:
                if created_user:
                    cognito.admin_delete_user(UserPoolId=user_pool_id, Username=email)
            except Exception:
                pass
        try:
            permissions_table.delete_item(Key={"user_id": admin_user_id})
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
