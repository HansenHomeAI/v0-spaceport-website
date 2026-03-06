#!/usr/bin/env python3
"""
Helper script to print sanitized branch suffixes that match CDK behavior.

Usage:
    python scripts/get_branch_suffix.py <branch-name> [--mode ecr|resource]
"""

from __future__ import annotations

import argparse
import os
import sys


def _resolve_repo_root() -> str:
    script_dir = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(script_dir, ".."))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("branch", help="Raw branch name (e.g. agent-123-work)")
    parser.add_argument(
        "--mode",
        choices=("sanitized", "ecr", "resource"),
        default="sanitized",
        help="Sanitized: plain identifier, ecr: shared branches -> empty, resource: prod/staging mapping",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=None,
        help="Limit suffix length (applies to sanitized mode only)",
    )
    args = parser.parse_args()

    repo_root = _resolve_repo_root()
    sys.path.append(os.path.join(repo_root, "infrastructure", "spaceport_cdk"))

    from spaceport_cdk.branch_utils import (  # pylint: disable=import-error
        get_ecr_branch_suffix,
        get_limited_suffix,
        get_resource_suffix,
        sanitize_branch_name,
    )

    if args.mode == "ecr":
        value = get_ecr_branch_suffix(args.branch)
    elif args.mode == "resource":
        value = get_resource_suffix(args.branch)
    else:
        if args.max_length is not None:
            value = get_limited_suffix(args.branch, args.max_length)
        else:
            value = sanitize_branch_name(args.branch)

    sys.stdout.write(value)


if __name__ == "__main__":
    main()
