#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict


HASH_PATTERN = re.compile(r"Deployment complete! Take a peek over at (https://\S+)")
ALIAS_PATTERN = re.compile(r"Deployment alias URL: (https://\S+)")


def parse_pages_deploy_output(log_path: Path) -> Dict[str, str]:
    text = log_path.read_text(encoding="utf-8")
    hash_match = HASH_PATTERN.search(text)
    if not hash_match:
        raise ValueError("Unable to locate the deployment hash URL in Wrangler output")

    alias_match = ALIAS_PATTERN.search(text)
    hash_url = hash_match.group(1)
    alias_url = alias_match.group(1) if alias_match else ""
    preview_url = alias_url or hash_url

    return {
        "hash_url": hash_url,
        "alias_url": alias_url,
        "preview_url": preview_url,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse Wrangler Pages deploy output and emit URLs.")
    parser.add_argument("--log", required=True, help="Path to the captured Wrangler output log.")
    parser.add_argument("--format", choices=("json", "shell"), default="json", help="Output format.")
    args = parser.parse_args()

    payload = parse_pages_deploy_output(Path(args.log))
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    for key, value in payload.items():
        print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
