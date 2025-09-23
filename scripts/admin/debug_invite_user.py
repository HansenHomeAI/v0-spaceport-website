#!/usr/bin/env python3
"""Utility to create or reset a Cognito invite for testing and surface the temp password."""

import argparse
import json
import re
import sys
import time
from typing import Dict, List, Optional

import boto3

_WORDS = [
    "orbit",
    "rocket",
    "nova",
    "astro",
    "comet",
    "vector",
    "launch",
    "stellar",
    "apollo",
    "saturn",
    "galaxy",
    "fusion",
    "cosmic",
    "nebula",
    "zenith",
    "quasar",
    "meteor",
    "lunar",
    "solis",
]
_DIGITS = "23456789"
_LOWER = "abcdefghjkmnpqrstuvwxyz"
_UPPER = "ABCDEFGHJKMNPQRSTUVWXYZ"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or reset a Cognito invite and print credentials")
    parser.add_argument("email", nargs="?", help="Email to invite. If omitted a unique test email is generated.")
    parser.add_argument("handle", nargs="?", help="Preferred username/handle")
    parser.add_argument("name", nargs="?", help="Display name")
    parser.add_argument("--profile", default=None, help="AWS named profile to use")
    parser.add_argument("--region", default="us-west-2", help="AWS region")
    parser.add_argument("--stack", default="SpaceportAuthStack", help="CloudFormation stack with Cognito outputs")
    parser.add_argument("--pool-output-key", default="CognitoUserPoolIdV2", help="Output key for the user pool id")
    parser.add_argument("--group", default=None, help="Cognito group to add the user to (defaults to lambda setting)")
    parser.add_argument("--dry-run", action="store_true", help="Print the request without touching Cognito")
    return parser.parse_args()


def _load_pool_and_group(session: boto3.Session, region: str, stack_name: str, pool_key: str) -> Dict[str, str]:
    cf = session.client("cloudformation", region_name=region)
    stacks = cf.describe_stacks(StackName=stack_name)
    outputs = {item["OutputKey"]: item["OutputValue"] for item in stacks["Stacks"][0].get("Outputs", [])}
    pool = outputs.get(pool_key)
    if not pool:
        raise SystemExit(f"Could not find output {pool_key} on stack {stack_name}")

    return {
        "pool": pool,
        "group": outputs.get("InviteGroupName", outputs.get("InviteGroupNameV2", "beta-testers-v2")),
    }


def _sanitize_handle(raw: str) -> str:
    cleaned = raw.strip().lower()
    cleaned = re.sub(r"[^a-z0-9-_]", "", cleaned)
    return cleaned or f"user{int(time.time())}"


def _generate_email() -> str:
    stamp = int(time.time())
    return f"invite-test+{stamp}@spcprt.dev"


def _generate_temp_password() -> str:
    import secrets

    word = secrets.choice(_WORDS)
    digits = ''.join(secrets.choice(_DIGITS) for _ in range(2))
    suffix_upper = secrets.choice(_UPPER)
    suffix_lower = secrets.choice(_LOWER)
    return f"{word.capitalize()}{digits}{suffix_upper}{suffix_lower}"


def _build_attributes(email: str, name: Optional[str], handle: Optional[str]) -> List[Dict[str, str]]:
    attrs: List[Dict[str, str]] = [
        {"Name": "email", "Value": email},
        {"Name": "email_verified", "Value": "true"},
    ]
    if name:
        attrs.append({"Name": "name", "Value": name.strip()})
    if handle:
        attrs.append({"Name": "preferred_username", "Value": handle})
    return attrs


def main() -> None:
    args = parse_args()

    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    region = args.region

    info = _load_pool_and_group(session, region, args.stack, args.pool_output_key)
    pool_id = info["pool"]
    group_name = args.group or info["group"]

    email = (args.email or _generate_email()).strip().lower()
    handle = _sanitize_handle(args.handle or email.split("@")[0])
    name = args.name or "Test User"

    attributes = _build_attributes(email, name, handle)
    temp_password = _generate_temp_password()

    result = {
        "email": email,
        "temporary_password": temp_password,
        "handle": handle,
        "group": group_name,
        "pool_id": pool_id,
    }

    if args.dry_run:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return

    cognito = session.client("cognito-idp", region_name=region)

    user_already_existed = False
    try:
        cognito.admin_create_user(
            UserPoolId=pool_id,
            Username=email,
            UserAttributes=attributes,
            MessageAction="SUPPRESS",
            DesiredDeliveryMediums=["EMAIL"],
            TemporaryPassword=temp_password,
        )
    except cognito.exceptions.UsernameExistsException:
        user_already_existed = True

    if user_already_existed:
        updatable = [attr for attr in attributes if attr["Name"] != "preferred_username"]
        if updatable:
            cognito.admin_update_user_attributes(
                UserPoolId=pool_id,
                Username=email,
                UserAttributes=updatable,
            )

    cognito.admin_set_user_password(
        UserPoolId=pool_id,
        Username=email,
        Password=temp_password,
        Permanent=False,
    )

    if group_name:
        try:
            cognito.admin_add_user_to_group(
                UserPoolId=pool_id,
                Username=email,
                GroupName=group_name,
            )
        except cognito.exceptions.ResourceNotFoundException:
            pass
        except cognito.exceptions.InvalidParameterException:
            pass

    result["user_already_existed"] = user_already_existed

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
