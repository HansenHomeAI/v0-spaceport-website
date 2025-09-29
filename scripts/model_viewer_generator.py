#!/usr/bin/env python3
"""CLI tool to generate viewer HTML files via the model file generator Lambda."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import importlib
import importlib.util
import types


def load_overrides(config_path: Optional[Path]) -> Dict[str, Any]:
    if not config_path:
        return {}
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_lambda_module() -> types.ModuleType:
    module_path = Path(__file__).resolve().parents[1] / 'infrastructure' / 'lambda' / 'model_file_generator' / 'lambda_function.py'
    if not module_path.exists():
        raise FileNotFoundError(f'Lambda module not found at {module_path}')
    spec = importlib.util.spec_from_file_location('model_file_generator_lambda', module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError('Unable to load lambda module spec')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def invoke_local(payload: Dict[str, Any]) -> Dict[str, Any]:
    module = load_lambda_module()
    return module.lambda_handler(payload, None)


def invoke_aws(payload: Dict[str, Any], function_name: str, profile: Optional[str]) -> Dict[str, Any]:
    try:
        import boto3  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("boto3 is required for AWS invocation. Install boto3 or use --mode local.") from exc

    session_kwargs: Dict[str, Any] = {}
    if profile:
        session_kwargs["profile_name"] = profile
    session = boto3.Session(**session_kwargs) if session_kwargs else boto3.Session()
    client = session.client("lambda")
    response = client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    payload_stream = response.get("Payload")
    if not payload_stream:
        raise RuntimeError("No payload returned from Lambda")
    body = payload_stream.read().decode("utf-8")
    return {
        "statusCode": response.get("StatusCode"),
        "body": body,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate viewer HTML files via Lambda")
    parser.add_argument("--source-link", dest="source_link", required=True, help="Primary splat source link")
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to JSON file containing fine-tune overrides",
    )
    parser.add_argument(
        "--template",
        dest="template_name",
        help="Optional template name (defaults to viewer_template.html)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to write generated HTML. If omitted, output is printed to stdout",
    )
    parser.add_argument(
        "--mode",
        choices=["local", "aws"],
        default="local",
        help="Invocation mode: local imports the Lambda handler, aws invokes the deployed function",
    )
    parser.add_argument(
        "--function-name",
        default="Spaceport-ModelFileGenerator",
        help="Lambda function name when using --mode aws",
    )
    parser.add_argument(
        "--profile",
        help="AWS profile name used for boto3 Session when invoking remotely",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    overrides = load_overrides(args.config)
    payload: Dict[str, Any] = {
        "source_link": args.source_link,
        "fine_tune_config": overrides,
    }
    if args.template_name:
        payload["template_name"] = args.template_name

    if args.mode == "local":
        response = invoke_local(payload)
    else:
        response = invoke_aws(payload, args.function_name, args.profile)

    status_code = response.get("statusCode", 500)
    try:
        body = response.get("body", "")
        payload_json = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to decode Lambda response body: {exc} -> {body}") from exc

    if status_code and int(status_code) >= 300:
        raise RuntimeError(f"Lambda invocation failed ({status_code}): {payload_json}")

    html = payload_json.get("html")
    if html is None:
        raise RuntimeError("Lambda response missing 'html' field")

    if args.output:
        args.output.write_text(html, encoding="utf-8")
        print(f"Generated viewer HTML written to {args.output}")
    else:
        sys.stdout.write(html)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
