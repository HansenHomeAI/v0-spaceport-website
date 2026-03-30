#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
CDK_PACKAGE_ROOT = REPO_ROOT / "infrastructure" / "spaceport_cdk"
if str(CDK_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(CDK_PACKAGE_ROOT))

from spaceport_cdk.deployment_context import resolve_deployment_context


def endpoint_types_for_rest_api(resource: Dict[str, object]) -> List[str]:
    properties = resource.get("Properties", {})
    if not isinstance(properties, dict):
        return []

    endpoint_config = properties.get("EndpointConfiguration", {})
    if not isinstance(endpoint_config, dict):
        return []

    types = endpoint_config.get("Types", [])
    if not isinstance(types, list):
        return []

    normalized: List[str] = []
    for entry in types:
        if isinstance(entry, str):
            normalized.append(entry)
    return normalized


def collect_rest_api_endpoint_types(template: Dict[str, object]) -> Dict[str, List[str]]:
    resources = template.get("Resources", {})
    if not isinstance(resources, dict):
        return {}

    collected: Dict[str, List[str]] = {}
    for logical_id, resource in resources.items():
        if not isinstance(resource, dict):
            continue
        if resource.get("Type") != "AWS::ApiGateway::RestApi":
            continue
        collected[logical_id] = endpoint_types_for_rest_api(resource)
    return collected


def find_regional_violations(
    templates_by_stack: Dict[str, Dict[str, object]],
    required_regional_stacks: Sequence[str],
) -> List[str]:
    violations: List[str] = []

    for stack_name in required_regional_stacks:
        template = templates_by_stack.get(stack_name)
        if template is None:
            violations.append(f"{stack_name}: synthesized template missing")
            continue

        rest_apis = collect_rest_api_endpoint_types(template)
        if not rest_apis:
            violations.append(f"{stack_name}: no AWS::ApiGateway::RestApi resources found")
            continue

        for logical_id, endpoint_types in sorted(rest_apis.items()):
            if endpoint_types != ["REGIONAL"]:
                rendered = ",".join(endpoint_types) if endpoint_types else "<default EDGE>"
                violations.append(f"{stack_name}:{logical_id} -> {rendered}")

    return violations


def load_templates(template_dir: Path, stack_names: Iterable[str]) -> Dict[str, Dict[str, object]]:
    templates: Dict[str, Dict[str, object]] = {}
    for stack_name in stack_names:
        template_path = template_dir / f"{stack_name}.template.json"
        if not template_path.exists():
            continue
        templates[stack_name] = json.loads(template_path.read_text(encoding="utf-8"))
    return templates


def resolve_required_regional_stacks(branch_name: str, deploy_auth_stack: bool) -> List[str]:
    context = resolve_deployment_context(branch_name)
    required: List[str] = []

    if context.deployment_class == "branch-preview":
        required.extend([context.spaceport_stack_name, context.ml_stack_name])

    if deploy_auth_stack and branch_name != "main":
        auth_context = resolve_deployment_context("development")
        required.append(auth_context.auth_stack_name)

    return required


def synthesize_templates(repo_root: Path, branch_name: str, deploy_auth_stack: bool, stack_names: Sequence[str]) -> Path:
    cdk_dir = repo_root / "infrastructure" / "spaceport_cdk"
    output_dir = Path(tempfile.mkdtemp(prefix="cdk-endpoint-policy-"))
    if shutil.which("docker") is None:
        raise RuntimeError("docker is required for CDK asset bundling during endpoint policy synthesis")

    command = [
        shutil.which("cdk") or "cdk",
        "synth",
        *stack_names,
        "--output",
        str(output_dir),
        "--context",
        f"branch_name={branch_name}",
        "--context",
        f"deploy_auth_stack={'true' if deploy_auth_stack else 'false'}",
    ]

    subprocess.run(command, cwd=cdk_dir, check=True)
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail when preview or shared-staging CDK synth drifts back to EDGE API Gateway endpoints.")
    parser.add_argument("--branch", required=True, help="Git branch name to synthesize.")
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root.",
    )
    parser.add_argument(
        "--deploy-auth-stack",
        choices=("true", "false"),
        required=True,
        help="Whether the synth should include the auth stack.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    deploy_auth_stack = args.deploy_auth_stack == "true"

    context = resolve_deployment_context(args.branch)
    stack_names = [context.spaceport_stack_name, context.ml_stack_name]
    if deploy_auth_stack:
        auth_context = resolve_deployment_context("main" if args.branch == "main" else "development")
        stack_names.append(auth_context.auth_stack_name)

    required_regional = resolve_required_regional_stacks(args.branch, deploy_auth_stack)
    if not required_regional:
        print(f"No non-production regional endpoint assertions required for branch {args.branch}.")
        return 0

    try:
        output_dir = synthesize_templates(repo_root, args.branch, deploy_auth_stack, stack_names)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    templates = load_templates(output_dir, stack_names)
    violations = find_regional_violations(templates, required_regional)

    print(f"Checked regional endpoint policy for branch {args.branch}")
    for stack_name in required_regional:
        print(f"- require REGIONAL: {stack_name}")

    if violations:
        print("Endpoint policy violations detected:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    print("Endpoint policy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
