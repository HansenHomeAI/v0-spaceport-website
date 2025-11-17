#!/usr/bin/env python3
"""Utility to programmatically set a user's subscription plan in DynamoDB using the
lambda's business logic so front-end gating can be exercised in tests."""

import argparse
import importlib.util
import os
import sys
from pathlib import Path

DEFAULT_TABLE = "Spaceport-Users-staging"
DEFAULT_REGION = "us-west-2"
VALID_PLANS = {"single", "starter", "growth", "enterprise", "beta"}
VALID_STATUS = {"active", "trialing", "past_due", "canceled"}


def load_lambda_module():
    module_path = Path('infrastructure/lambda/subscription_manager/lambda_function.py').resolve()
    spec = importlib.util.spec_from_file_location('subscription_lambda', module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load subscription manager module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description="Set a user's subscription plan using Lambda logic")
    parser.add_argument('--user-sub', required=True, help="Cognito user sub (userSub/id)")
    parser.add_argument('--plan', required=True, choices=sorted(VALID_PLANS), help="Subscription plan type")
    parser.add_argument('--status', default='active', choices=sorted(VALID_STATUS), help="Subscription status")
    parser.add_argument('--table', default=DEFAULT_TABLE, help="DynamoDB table name")
    parser.add_argument('--region', default=DEFAULT_REGION, help="AWS region")
    parser.add_argument('--subscription-id', default='sub_manual_test', help="Subscription identifier to persist")
    parser.add_argument('--base-plan', default=None, help="Optional base plan override (defaults to existing/base beta)")

    args = parser.parse_args()

    os.environ.setdefault('AWS_DEFAULT_REGION', args.region)
    os.environ['USERS_TABLE'] = args.table
    # Allow lambda helper to call Dynamo without attempting Cognito attribute writes when not needed
    os.environ.setdefault('COGNITO_USER_POOL_ID', os.environ.get('COGNITO_USER_POOL_ID', ''))

    module = load_lambda_module()

    # Cognito custom attributes are optional in staging; stub out updates when pool id is missing
    if not os.environ.get('COGNITO_USER_POOL_ID'):
        module.update_cognito_subscription_attributes = lambda *_, **__: None  # type: ignore[attr-defined]

    # Optionally override base plan type before applying upgrade so additive math aligns
    if args.base_plan:
        table, key_name = module._resolve_users_table()  # type: ignore[attr-defined]
        table.update_item(
            Key=module._build_user_key(key_name, args.user_sub),  # type: ignore[attr-defined]
            UpdateExpression='SET basePlanType = :base',
            ExpressionAttributeValues={':base': args.base_plan}
        )

    module.update_user_subscription(args.user_sub, args.subscription_id, args.plan, args.status)
    print(f"Updated {args.user_sub} to plan={args.plan} status={args.status} in {args.table}")


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # pragma: no cover - CLI convenience
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
