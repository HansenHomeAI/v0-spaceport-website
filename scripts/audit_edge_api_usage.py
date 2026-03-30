#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

REPO_ROOT = Path(__file__).resolve().parents[1]
CDK_PACKAGE_ROOT = REPO_ROOT / "infrastructure" / "spaceport_cdk"
if str(CDK_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(CDK_PACKAGE_ROOT))

from spaceport_cdk.deployment_context import resolve_deployment_context


PREVIEW_API_PATTERNS = (
    re.compile(r"^spaceport-(?:drone-path|feedback|file-upload|waitlist)-api-br-([0-9a-f]{10})$"),
    re.compile(r"^Spaceport-ML-API-br-([0-9a-f]{10})$"),
)
PREVIEW_STACK_PATTERNS = (
    re.compile(r"^SpaceportPreview([0-9A-F]{10})Stack$"),
    re.compile(r"^SpaceportMLPreview([0-9A-F]{10})Stack$"),
)
SHARED_AUTH_PREFIXES = (
    "Spaceport-InviteApi",
    "Spaceport-ProjectsApi",
    "Spaceport-ExplorePublicApi",
    "Spaceport-SubscriptionApi",
    "SubscriptionApiGateway",
    "Spaceport-BetaAccessAdminApi",
    "Spaceport-ModelDeliveryAdminApi",
    "Spaceport-PasswordResetApi",
)


@dataclass(frozen=True)
class RestApiRecord:
    api_id: str
    name: str
    endpoint_type: str
    category: str
    branch_id: Optional[str]


@dataclass(frozen=True)
class PreviewStackRecord:
    stack_name: str
    status: str
    branch_id: str


def extract_preview_branch_id(name: str, patterns: Sequence[re.Pattern[str]]) -> Optional[str]:
    for pattern in patterns:
        match = pattern.match(name)
        if match:
            return match.group(1).lower()
    return None


def classify_rest_api(name: str) -> tuple[str, Optional[str]]:
    branch_id = extract_preview_branch_id(name, PREVIEW_API_PATTERNS)
    if branch_id:
        return "preview", branch_id
    if name.startswith(SHARED_AUTH_PREFIXES):
        return "shared-auth", None
    return "other", None


def collect_rest_apis(region: str) -> List[RestApiRecord]:
    import boto3

    client = boto3.client("apigateway", region_name=region)
    paginator = client.get_paginator("get_rest_apis")
    records: List[RestApiRecord] = []

    for page in paginator.paginate(limit=500):
        for item in page.get("items", []):
            endpoint_types = item.get("endpointConfiguration", {}).get("types") or []
            endpoint_type = endpoint_types[0] if endpoint_types else "EDGE"
            category, branch_id = classify_rest_api(item["name"])
            records.append(
                RestApiRecord(
                    api_id=item["id"],
                    name=item["name"],
                    endpoint_type=endpoint_type,
                    category=category,
                    branch_id=branch_id,
                )
            )

    return records


def collect_preview_stacks(region: str) -> List[PreviewStackRecord]:
    import boto3

    client = boto3.client("cloudformation", region_name=region)
    paginator = client.get_paginator("describe_stacks")
    records: List[PreviewStackRecord] = []

    for page in paginator.paginate():
        for stack in page.get("Stacks", []):
            branch_id = extract_preview_branch_id(stack["StackName"], PREVIEW_STACK_PATTERNS)
            if not branch_id:
                continue
            records.append(
                PreviewStackRecord(
                    stack_name=stack["StackName"],
                    status=stack["StackStatus"],
                    branch_id=branch_id,
                )
            )

    return records


def list_origin_branches(repo_root: Path) -> List[str]:
    command = [
        "git",
        "for-each-ref",
        "--format=%(refname:short)",
        "refs/remotes/origin",
    ]
    result = subprocess.run(command, cwd=repo_root, check=True, capture_output=True, text=True)
    branches: List[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line == "origin/HEAD":
            continue
        if not line.startswith("origin/"):
            continue
        branches.append(line.removeprefix("origin/"))
    return branches


def resolve_active_preview_branch_ids(repo_root: Path) -> Set[str]:
    active_ids: Set[str] = set()
    for branch_name in list_origin_branches(repo_root):
        context = resolve_deployment_context(branch_name)
        if context.deployment_class == "branch-preview":
            active_ids.add(context.branch_id)
    return active_ids


def stale_preview_branch_ids(rest_apis: Sequence[RestApiRecord], preview_stacks: Sequence[PreviewStackRecord], active_branch_ids: Set[str]) -> List[str]:
    seen: Set[str] = set()
    for rest_api in rest_apis:
        if rest_api.category == "preview" and rest_api.branch_id:
            seen.add(rest_api.branch_id)
    for stack in preview_stacks:
        seen.add(stack.branch_id)
    return sorted(branch_id for branch_id in seen if branch_id not in active_branch_ids)


def summarize(rest_apis: Sequence[RestApiRecord], stale_branch_ids: Sequence[str]) -> Dict[str, object]:
    endpoint_counts = Counter(api.endpoint_type for api in rest_apis)
    preview_apis = [api for api in rest_apis if api.category == "preview"]
    shared_auth_apis = [api for api in rest_apis if api.category == "shared-auth"]

    return {
        "edge_total": endpoint_counts.get("EDGE", 0),
        "regional_total": endpoint_counts.get("REGIONAL", 0),
        "rest_api_total": len(rest_apis),
        "preview_edge_total": sum(1 for api in preview_apis if api.endpoint_type == "EDGE"),
        "preview_regional_total": sum(1 for api in preview_apis if api.endpoint_type == "REGIONAL"),
        "shared_auth_edge_total": sum(1 for api in shared_auth_apis if api.endpoint_type == "EDGE"),
        "shared_auth_regional_total": sum(1 for api in shared_auth_apis if api.endpoint_type == "REGIONAL"),
        "stale_preview_branch_ids": list(stale_branch_ids),
    }


def delete_stale_preview_stacks(region: str, preview_stacks: Sequence[PreviewStackRecord], stale_branch_ids: Set[str]) -> List[str]:
    import boto3

    client = boto3.client("cloudformation", region_name=region)
    deleted: List[str] = []
    for stack in preview_stacks:
        if stack.branch_id not in stale_branch_ids:
            continue
        if stack.status.startswith("DELETE_"):
            continue
        client.delete_stack(StackName=stack.stack_name)
        deleted.append(stack.stack_name)
    return deleted


def delete_stale_orphan_preview_apis(region: str, rest_apis: Sequence[RestApiRecord], preview_stacks: Sequence[PreviewStackRecord], stale_branch_ids: Set[str]) -> List[str]:
    import boto3
    from botocore.exceptions import ClientError

    client = boto3.client("apigateway", region_name=region)
    stack_branch_ids = {stack.branch_id for stack in preview_stacks if not stack.status.startswith("DELETE_")}
    deleted: List[str] = []

    for api in rest_apis:
        if api.category != "preview" or api.branch_id not in stale_branch_ids:
            continue
        if api.branch_id in stack_branch_ids:
            continue
        attempts = 0
        while True:
            try:
                client.delete_rest_api(restApiId=api.api_id)
                break
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") != "TooManyRequestsException" or attempts >= 4:
                    raise
                attempts += 1
                time.sleep(2 * attempts)
        deleted.append(api.name)

    return deleted


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory and optionally clean stale preview EDGE APIs.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root used to inspect remote branches.")
    parser.add_argument("--region", default="us-west-2", help="AWS region.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    parser.add_argument(
        "--delete-stale-preview-stacks",
        action="store_true",
        help="Delete preview CloudFormation stacks for branch IDs that no longer exist on origin.",
    )
    parser.add_argument(
        "--delete-stale-orphan-preview-apis",
        action="store_true",
        help="Delete stale preview APIs whose branch ID no longer exists and that no longer have a matching stack.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    rest_apis = collect_rest_apis(args.region)
    preview_stacks = collect_preview_stacks(args.region)
    active_branch_ids = resolve_active_preview_branch_ids(repo_root)
    stale_branch_ids = stale_preview_branch_ids(rest_apis, preview_stacks, active_branch_ids)
    summary = summarize(rest_apis, stale_branch_ids)

    deleted_stacks: List[str] = []
    deleted_apis: List[str] = []
    stale_id_set = set(stale_branch_ids)
    if args.delete_stale_preview_stacks:
        deleted_stacks = delete_stale_preview_stacks(args.region, preview_stacks, stale_id_set)
    if args.delete_stale_orphan_preview_apis:
        deleted_apis = delete_stale_orphan_preview_apis(args.region, rest_apis, preview_stacks, stale_id_set)

    payload = {
        "summary": summary,
        "deleted_stacks": deleted_stacks,
        "deleted_orphan_preview_apis": deleted_apis,
        "active_preview_branch_ids": sorted(active_branch_ids),
        "stale_preview_edge_apis": [
            asdict(api)
            for api in rest_apis
            if api.category == "preview" and api.endpoint_type == "EDGE" and api.branch_id in stale_id_set
        ],
        "shared_auth_edge_apis": [
            asdict(api)
            for api in rest_apis
            if api.category == "shared-auth" and api.endpoint_type == "EDGE"
        ],
    }

    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print(
        "EDGE={edge_total} REGIONAL={regional_total} TOTAL={rest_api_total}".format(
            **summary
        )
    )
    print(
        "Preview EDGE={preview_edge_total} REGIONAL={preview_regional_total} | "
        "Shared auth EDGE={shared_auth_edge_total} REGIONAL={shared_auth_regional_total}".format(
            **summary
        )
    )
    if stale_branch_ids:
        print("Stale preview branch IDs:", ", ".join(stale_branch_ids))
    else:
        print("Stale preview branch IDs: none")
    if deleted_stacks:
        print("Deleted stale preview stacks:", ", ".join(deleted_stacks))
    if deleted_apis:
        print("Deleted stale orphan preview APIs:", ", ".join(deleted_apis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
