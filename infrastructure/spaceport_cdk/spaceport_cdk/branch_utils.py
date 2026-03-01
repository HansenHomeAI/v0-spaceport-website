"""
Branch name sanitization utilities for AWS resource naming.

Shared by CDK stacks and CI workflows to keep branch-specific resources
consistent regardless of where they are created.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Optional


def sanitize_branch_name(branch_name: str, max_length: int = 50) -> str:
    """
    Sanitize a branch name to be AWS-compliant for resource naming.

    Returns a lowercase alphanumeric string capped at max_length.
    """
    if not branch_name:
        return "default"

    normalized_branch = branch_name.lower()
    sanitized = re.sub(r"[^a-z0-9]", "", normalized_branch)
    hash_suffix = hashlib.sha1(branch_name.encode("utf-8")).hexdigest()[:6]

    base = sanitized or "default"
    keep_length = max_length - len(hash_suffix)
    if keep_length <= 0:
        sanitized = hash_suffix[:max_length]
    else:
        sanitized = f"{base[:keep_length]}{hash_suffix}"

    if len(sanitized) < 3:
        sanitized = sanitized + "br"

    return sanitized


def shorten_identifier(identifier: str, max_length: int) -> str:
    """
    Shorten an identifier deterministically while keeping it AWS-safe.
    """
    if max_length <= 0:
        raise ValueError("max_length must be greater than 0")

    if len(identifier) <= max_length:
        return identifier

    hash_suffix = hashlib.sha1(identifier.encode("utf-8")).hexdigest()[:6]
    keep_length = max_length - len(hash_suffix)

    if keep_length <= 0:
        return hash_suffix[:max_length]

    return f"{identifier[:keep_length]}{hash_suffix}"


def get_resource_suffix(branch_name: str) -> str:
    """
    Get the general resource suffix for a branch name.
    """
    if branch_name == "main":
        return "prod"
    if branch_name == "development":
        return "staging"
    return sanitize_branch_name(branch_name, max_length=40)


def get_ecr_branch_suffix(branch_name: str) -> str:
    """
    Use shared repos for stable branches, otherwise generate a per-branch suffix.
    """
    if branch_name in {"main", "development", "ml-development"}:
        return ""
    return sanitize_branch_name(branch_name)


def get_limited_suffix(branch_name: str, max_suffix_length: int) -> str:
    """
    Sanitize and truncate a branch name to a maximum suffix length.
    """
    sanitized = sanitize_branch_name(branch_name)
    return shorten_identifier(sanitized, max_suffix_length)


def build_scoped_name(
    prefix: str, branch_name: str, max_total_length: Optional[int] = None
) -> str:
    """
    Build a resource name with the branch suffix and enforce the max length.
    """
    suffix = sanitize_branch_name(branch_name)

    if max_total_length is not None:
        allowed_suffix_len = max_total_length - len(prefix)
        if allowed_suffix_len <= 0:
            raise ValueError(
                f"Prefix '{prefix}' is too long for limit {max_total_length}"
            )
        suffix = shorten_identifier(suffix, allowed_suffix_len)

    return f"{prefix}{suffix}"


def is_agent_branch(branch_name: str) -> bool:
    """
    Helper to flag agent branches.
    """
    return branch_name.startswith("agent-") or "agent" in branch_name.lower()
