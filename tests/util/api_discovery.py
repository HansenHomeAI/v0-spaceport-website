"""Utilities for discovering API Gateway endpoints dynamically."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Iterable, Optional

import boto3

DEFAULT_STAGE_PREFERENCE: tuple[str, ...] = ("prod", "production", "staging", "stage", "dev", "beta")


def _pick_stage(stages: list[dict], preference: Iterable[str]) -> str:
    by_name = {stage["stageName"]: stage for stage in stages}
    for candidate in preference:
        if candidate in by_name:
            return candidate
    if stages:
        return stages[0]["stageName"]
    raise RuntimeError("No deployment stages available for API Gateway")


@lru_cache(maxsize=None)
def discover_api_endpoint(
    name_prefix: str,
    *,
    region: Optional[str] = None,
    resource_path: str = "",
    stage_preference: Iterable[str] = DEFAULT_STAGE_PREFERENCE,
) -> str:
    """Return a base URL for the newest API Gateway whose name matches prefix.

    Args:
        name_prefix: Prefix (case sensitive) of the API Gateway name as configured
            in CDK (for example ``"Spaceport-ProjectsApi"``).
        region: AWS region to query. Defaults to ``AWS_REGION`` env var or ``us-west-2``.
        resource_path: Optional resource path segment appended to the base stage URL.
        stage_preference: Ordered iterable of stage names to prefer when multiple
            deployments exist (defaults to prod -> staging -> dev).

    Raises:
        RuntimeError: If no matching API Gateway can be found.
    """

    aws_region = region or os.environ.get("AWS_REGION", "us-west-2")
    client = boto3.client("apigateway", region_name=aws_region)

    paginator = client.get_paginator("get_rest_apis")
    matches: list[dict] = []
    for page in paginator.paginate():
        for item in page.get("items", []):
            if item.get("name", "").startswith(name_prefix):
                matches.append(item)

    if not matches:
        raise RuntimeError(f"No API Gateway found with prefix '{name_prefix}'")

    matches.sort(key=lambda api: api.get("createdDate"), reverse=True)
    chosen = matches[0]

    stages = client.get_stages(restApiId=chosen["id"]).get("item", [])
    stage = _pick_stage(stages, stage_preference)

    base_url = f"https://{chosen['id']}.execute-api.{aws_region}.amazonaws.com/{stage}"
    resource = resource_path.strip("/")
    if resource:
        return f"{base_url}/{resource}"
    return base_url
