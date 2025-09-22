#!/usr/bin/env python3
"""Run automated subscription scenarios to verify Dynamo updates propagate to the UI."""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

CLIENT_ID = "4jqu6jc4nl6rt7jih7l12071p"
AWS_REGION = "us-west-2"
SET_SCRIPT = Path(__file__).with_name("set_subscription_plan.py").resolve()
CHECK_SCRIPT = Path(__file__).with_name("check_dashboard_plan.mjs").resolve()
FULL_FLOW_SCRIPT = Path(__file__).with_name("run_full_subscription_flow.mjs").resolve()


@dataclass
class Scenario:
    name: str
    plan: str
    status: str
    base_plan: Optional[str]
    expectation: Callable[[Dict[str, str], Dict[str, any]], bool]
    description: str


def run_cmd(cmd: List[str], *, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result


def parse_plan_output(stdout: str) -> Dict[str, str]:
    match = re.search(r"### Result\s*(\{.*?\})", stdout, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    raise ValueError(f"Unable to parse plan output:\n{stdout}")


def fetch_tokens(email: str, password: str) -> Dict[str, str]:
    cmd = [
        "aws", "cognito-idp", "initiate-auth",
        "--region", AWS_REGION,
        "--auth-flow", "USER_PASSWORD_AUTH",
        "--client-id", CLIENT_ID,
        "--auth-parameters", f"USERNAME={email},PASSWORD={password}"
    ]
    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to fetch tokens: {result.stderr.strip()}")
    return json.loads(result.stdout)["AuthenticationResult"]


def fetch_subscription_json(preview_url: str, email: str, password: str) -> Dict[str, any]:
    tokens = fetch_tokens(email, password)
    cmd = [
        "curl", "-s", "-H",
        f"Authorization: Bearer {tokens['IdToken']}",
        f"{preview_url.rstrip('/')}/api/subscription-status"
    ]
    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"Subscription status curl failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def run_full_flow(preview_url: str, email: str, password: str) -> bool:
    cmd = [
        "node", str(FULL_FLOW_SCRIPT),
        preview_url,
        email,
        password
    ]
    result = run_cmd(cmd)
    if result.returncode != 0:
        return False
    summary_match = re.search(r"Summary:\s*(\[.*\])", result.stdout, re.DOTALL)
    if not summary_match:
        return False
    summary = json.loads(summary_match.group(1))
    return not any(item.get("status") == "fail" for item in summary)


def run_check(preview_url: str, email: str, password: str) -> Dict[str, str]:
    cmd = [
        "node", str(CHECK_SCRIPT),
        preview_url,
        email,
        password
    ]
    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"Dashboard check failed: {result.stderr.strip()}")
    return parse_plan_output(result.stdout)


def run_set(user_sub: str, plan: str, status: str, table: str, base_plan: Optional[str]) -> None:
    cmd = [
        "python3", str(SET_SCRIPT),
        "--user-sub", user_sub,
        "--plan", plan,
        "--status", status,
        "--table", table,
        "--region", AWS_REGION,
        "--subscription-id", f"sub_{plan}_test"
    ]
    if base_plan:
        cmd.extend(["--base-plan", base_plan])
    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to set subscription: {result.stderr.strip()}")


def expect_contains(plan_fragment: str, count_fragment: str) -> Callable[[Dict[str, str], Dict[str, any]], bool]:
    def checker(plan_payload: Dict[str, str], api_payload: Dict[str, any]) -> bool:
        plan_ok = plan_payload.get("plan") and plan_fragment.lower() in plan_payload["plan"].lower()
        models_ok = plan_payload.get("models") and count_fragment in plan_payload["models"]
        return bool(plan_ok and models_ok)
    return checker


def expect_status_models(expected_status: str, expected_max: int) -> Callable[[Dict[str, str], Dict[str, any]], bool]:
    def checker(plan_payload: Dict[str, str], api_payload: Dict[str, any]) -> bool:
        subscription = api_payload.get("subscription", {})
        status_ok = subscription.get("status") == expected_status
        models_ok = subscription.get("maxModels") == expected_max
        plan_ok = plan_payload.get("models") and f"/{expected_max}" in plan_payload["models"]
        return status_ok and models_ok and plan_ok
    return checker


def main() -> None:
    parser = argparse.ArgumentParser(description="Run subscription robustness scenarios")
    parser.add_argument("preview_url")
    parser.add_argument("email")
    parser.add_argument("password")
    parser.add_argument("user_sub")
    parser.add_argument("table", default="Spaceport-Users-staging", nargs="?")
    args = parser.parse_args()

    scenarios: List[Scenario] = [
        Scenario(
            name="Starter upgrade",
            plan="starter",
            status="active",
            base_plan=None,
            expectation=lambda plan_payload, api_payload: expect_status_models("active", 10)(plan_payload, api_payload),
            description="Starter subscription exposes 10 model limit"
        ),
        Scenario(
            name="Growth upgrade",
            plan="growth",
            status="active",
            base_plan=None,
            expectation=lambda plan_payload, api_payload: expect_status_models("active", 25)(plan_payload, api_payload),
            description="Growth subscription exposes 25 model limit"
        ),
        Scenario(
            name="Cancel subscription",
            plan="starter",
            status="canceled",
            base_plan=None,
            expectation=lambda plan_payload, api_payload: expect_status_models("canceled", 5)(plan_payload, api_payload),
            description="Cancellation reverts availability to base"
        )
    ]

    results = []

    for scenario in scenarios:
        try:
            run_set(args.user_sub, scenario.plan, scenario.status, args.table, scenario.base_plan)
            plan_payload = run_check(args.preview_url, args.email, args.password)
            api_payload = fetch_subscription_json(args.preview_url, args.email, args.password)
            success = scenario.expectation(plan_payload, api_payload)
            results.append({
                "scenario": scenario.name,
                "description": scenario.description,
                "plan": plan_payload,
                "api": api_payload.get("subscription"),
                "success": success
            })
        except Exception as exc:
            results.append({
                "scenario": scenario.name,
                "description": scenario.description,
                "error": str(exc),
                "success": False
            })

    flow_success = run_full_flow(args.preview_url, args.email, args.password)

    print(json.dumps({
        "results": results,
        "checkout_flow_success": flow_success
    }, indent=2))

    if not flow_success or not all(item["success"] for item in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
