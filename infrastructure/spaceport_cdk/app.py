#!/usr/bin/env python3
import json
import os
from pathlib import Path

from aws_cdk import App
from spaceport_cdk.deployment_context import build_env_config, resolve_deployment_context
from spaceport_cdk.spaceport_stack import SpaceportStack
from spaceport_cdk.auth_stack import AuthStack
from spaceport_cdk.ml_pipeline_stack import MLPipelineStack

app = App()


def _parse_target_stacks() -> set[str]:
    raw_value = app.node.try_get_context("target_stacks") or os.environ.get("CDK_TARGET_STACKS", "")
    return {
        target.strip().lower()
        for target in raw_value.split(",")
        if target.strip()
    }

def _load_environments_context():
    environments = app.node.try_get_context("environments")
    if environments is not None:
        return environments

    cdk_config_path = Path(__file__).with_name("cdk.json")
    with cdk_config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)["context"]["environments"]
explicit_branch_name = app.node.try_get_context("branch_name") or os.environ.get("GITHUB_REF_NAME")
explicit_environment = app.node.try_get_context("environment")
if explicit_branch_name:
    deployment_context = resolve_deployment_context(explicit_branch_name)
elif explicit_environment == "production":
    deployment_context = resolve_deployment_context("main")
else:
    deployment_context = resolve_deployment_context("development")

base_env_config = _load_environments_context()[deployment_context.cdk_environment_name]
env_config = build_env_config(base_env_config, deployment_context)

print(f"Deploying for branch: {deployment_context.branch_name}")
print(f"Resolved deployment context: {deployment_context.to_dict()}")
print(f"Resolved environment config: {env_config}")

deploy_auth_stack_override = str(
    app.node.try_get_context("deploy_auth_stack")
    or os.environ.get("DEPLOY_AUTH_STACK_OVERRIDE", "")
).lower() == "true"
deploy_auth_stack = deployment_context.deploy_auth_stack or deploy_auth_stack_override
env_config["deployAuthStack"] = deploy_auth_stack

auth_deployment_context = deployment_context
auth_env_config = env_config
if deploy_auth_stack and deployment_context.deployment_class == "branch-preview":
    # Branch previews reuse the shared staging auth stack and its shared data.
    auth_deployment_context = resolve_deployment_context("development")
    auth_base_env_config = _load_environments_context()[auth_deployment_context.cdk_environment_name]
    auth_env_config = build_env_config(auth_base_env_config, auth_deployment_context)
    auth_env_config["deployAuthStack"] = True

common_env = {
    "account": app.node.try_get_context("account") or None,
    "region": env_config["region"],
}

target_stacks = _parse_target_stacks()
deploy_spaceport_stack = not target_stacks or "spaceport" in target_stacks
deploy_ml_stack = not target_stacks or "ml" in target_stacks
deploy_auth_stack_selected = deploy_auth_stack and (not target_stacks or "auth" in target_stacks)

print(f"Selected CDK targets: {sorted(target_stacks) if target_stacks else ['spaceport', 'ml', 'auth']}")

if deploy_spaceport_stack:
    SpaceportStack(
        app,
        deployment_context.spaceport_stack_name,
        env_config=env_config,
        env=common_env,
    )

if deploy_ml_stack:
    MLPipelineStack(
        app,
        deployment_context.ml_stack_name,
        env_config=env_config,
        env=common_env,
    )

if deploy_auth_stack_selected:
    AuthStack(
        app,
        auth_deployment_context.auth_stack_name,
        env_config=auth_env_config,
        env=common_env,
    )

app.synth()
