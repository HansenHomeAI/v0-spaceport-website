#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
CDK_PACKAGE_ROOT = REPO_ROOT / "infrastructure" / "spaceport_cdk"
if str(CDK_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(CDK_PACKAGE_ROOT))

from spaceport_cdk.deployment_context import resolve_deployment_context


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve Spaceport deployment context for a git branch.")
    parser.add_argument("--branch", required=True, help="Full git branch name.")
    parser.add_argument(
        "--format",
        choices=("json", "shell"),
        default="json",
        help="Output format.",
    )
    args = parser.parse_args()

    context = resolve_deployment_context(args.branch)
    payload = context.to_dict()

    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    for key, value in payload.items():
        shell_key = key.upper()
        if isinstance(value, bool):
            shell_value = "true" if value else "false"
        else:
            shell_value = str(value)
        print(f"{shell_key}={shell_value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
