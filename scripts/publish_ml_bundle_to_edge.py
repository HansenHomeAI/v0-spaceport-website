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
    return parser.parse_args()


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

    if args.validate_http:
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
