from __future__ import annotations

SHARED_PREVIEW_RESOURCE_SUFFIX = "staging"


def should_reuse_shared_preview_resources(deployment_class: str) -> bool:
    return deployment_class == "branch-preview"


def shared_preview_bucket_name(prefix: str, shared_suffix: str = SHARED_PREVIEW_RESOURCE_SUFFIX) -> str:
    return f"{prefix}-{shared_suffix}"


def shared_preview_table_name(prefix: str, shared_suffix: str = SHARED_PREVIEW_RESOURCE_SUFFIX) -> str:
    return f"{prefix}-{shared_suffix}"


def shared_preview_role_name(prefix: str, shared_suffix: str = SHARED_PREVIEW_RESOURCE_SUFFIX) -> str:
    return f"{prefix}{shared_suffix}"
