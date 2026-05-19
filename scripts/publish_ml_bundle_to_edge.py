#!/usr/bin/env python3
"""Publish a compressed SuperSplat bundle to the edge delivery bucket.

This is a thin wrapper around the deployed `ml_publish_bundle` Lambda:
  infrastructure/spaceport_cdk/lambda/ml_publish_bundle/lambda_function.py

It writes the Lambda JSON response and (optionally) validates that the returned
edgeBundleUrl is publicly reachable with browser-friendly headers.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


HOMEBREW_AWS = Path("/opt/homebrew/bin/aws")


def resolve_aws() -> str:
    return str(HOMEBREW_AWS) if HOMEBREW_AWS.exists() else "aws"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--function-name", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--compressed-output-s3-uri", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--validate-http", action="store_true")
    parser.add_argument(
        "--require-browser-headers",
        action="store_true",
        help="Fail if the published meta.json is not browser-readable (HTTP 200, Content-Type JSON, CORS, caching).",
    )
    return parser.parse_args()

def parse_http_headers(raw: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.lower().startswith("http/"):
            headers["__status_line__"] = line.strip()
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    return headers


def assert_browser_readable(head_text: str) -> None:
    headers = parse_http_headers(head_text)
    status = headers.get("__status_line__", "")
    if " 200 " not in status and not status.endswith(" 200"):
        raise RuntimeError(f"edge bundle URL is not reachable (status={status or '<missing>'})")

    content_type = (headers.get("content-type") or "").lower()
    if "json" not in content_type:
        raise RuntimeError(f"edge bundle meta.json Content-Type not JSON: {content_type or '<missing>'}")

    cors = headers.get("access-control-allow-origin") or ""
    if cors not in {"*", ""}:
        raise RuntimeError(f"edge bundle meta.json unexpected CORS header: {cors}")

    cache_control = (headers.get("cache-control") or "").lower()
    if cache_control and "no-store" in cache_control:
        raise RuntimeError(f"edge bundle meta.json cache-control blocks caching: {cache_control}")


def main() -> int:
    args = parse_args()
    payload = {"jobId": args.job_id, "compressedOutputS3Uri": args.compressed_output_s3_uri}
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    aws = resolve_aws()

    invoke_out = output_path.with_suffix(".lambda-response.json")
    subprocess.run(
        [
            aws,
            "lambda",
            "invoke",
            "--cli-binary-format",
            "raw-in-base64-out",
            "--function-name",
            args.function_name,
            "--payload",
            json.dumps(payload),
            str(invoke_out),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    result = json.loads(invoke_out.read_text(encoding="utf-8"))
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    edge_url = (result.get("edgeBundleUrl") or "").strip()
    if not edge_url:
        raise RuntimeError(f"Lambda result missing edgeBundleUrl: {result}")

    print(f"OK edgeBundleUrl={edge_url}")

    if args.validate_http or args.require_browser_headers:
        head_path = output_path.with_suffix(".curl-head.txt")
        head = subprocess.run(
            ["curl", "-sS", "-I", edge_url],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        ).stdout
        head_path.write_text(head, encoding="utf-8")
        print(f"OK httpHead={head_path}")
        if args.require_browser_headers:
            assert_browser_readable(head)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
