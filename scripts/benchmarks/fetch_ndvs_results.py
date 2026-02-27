#!/usr/bin/env python3
"""Fetch NDVS benchmark rows from the public nvs-bench feed."""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from typing import Any, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-url",
        default="https://raw.githubusercontent.com/nvs-bench/nvs-bench/main/website/lib/results.json",
        help="URL for NDVS-compatible scene-level results JSON.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        required=True,
        help="Output JSON path.",
    )
    return parser.parse_args()


def validate_rows(payload: Any) -> List[dict]:
    if not isinstance(payload, list):
        raise ValueError("Expected NDVS results payload to be a JSON list.")
    return [row for row in payload if isinstance(row, dict)]


def main() -> int:
    args = parse_args()
    with urllib.request.urlopen(args.source_url, timeout=60) as response:
        payload = json.load(response)

    rows = validate_rows(payload)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Fetched {len(rows)} NDVS rows -> {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
