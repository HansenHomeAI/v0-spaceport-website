#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict


AUTH_MARKER_RELATIVE_PATH = Path(".spaceport/deploy-auth-preview")


def resolve_auth_deploy_mode(branch_name: str, repo_root: Path) -> Dict[str, str]:
    if not branch_name:
        raise ValueError("branch_name is required")

    marker_path = repo_root / AUTH_MARKER_RELATIVE_PATH
    auth_opt_in = marker_path.exists()

    if branch_name == "main":
        reason = "default-production"
        deploy_auth_stack = True
    elif branch_name == "development":
        reason = "default-development"
        deploy_auth_stack = True
    elif auth_opt_in:
        reason = "preview-opt-in"
        deploy_auth_stack = True
    else:
        reason = "preview-read-only"
        deploy_auth_stack = False

    return {
        "auth_marker_relative_path": AUTH_MARKER_RELATIVE_PATH.as_posix(),
        "auth_opt_in": "true" if auth_opt_in else "false",
        "auth_marker_exists": "true" if auth_opt_in else "false",
        "deploy_auth_stack_effective": "true" if deploy_auth_stack else "false",
        "auth_deploy_reason": reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve whether the current branch should deploy the auth stack.")
    parser.add_argument("--branch", required=True, help="Git branch name.")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used to check for the auth opt-in marker.",
    )
    parser.add_argument("--format", choices=("json", "shell"), default="json", help="Output format.")
    args = parser.parse_args()

    payload = resolve_auth_deploy_mode(args.branch, Path(args.repo_root).resolve())

    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    for key, value in payload.items():
        print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
