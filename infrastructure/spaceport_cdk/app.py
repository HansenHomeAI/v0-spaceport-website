#!/usr/bin/env python3
from aws_cdk import App
from spaceport_cdk.spaceport_stack import SpaceportStack
from spaceport_cdk.auth_stack import AuthStack
from spaceport_cdk.ml_pipeline_stack import MLPipelineStack
from spaceport_cdk.branch_utils import get_resource_suffix, sanitize_branch_name

app = App()

# Environment detection from context or default to staging
env_name = app.node.try_get_context('environment') or 'staging'
branch_name = app.node.try_get_context('branch')  # Optional branch name for dynamic environments

# Get predefined environments from context
predefined_environments = app.node.try_get_context('environments') or {}

# If branch is provided and it's an agent/feature branch (not main/development), create dynamic config
# Standard branches (main/development) use predefined environments
if branch_name and branch_name not in ['main', 'development']:
    # Generate dynamic environment config for agent/feature branches
    sanitized_suffix = get_resource_suffix(branch_name)
    env_config = {
        'region': 'us-west-2',
        'resourceSuffix': sanitized_suffix,
        'domain': f'{sanitized_suffix}.spcprt.com',  # Dynamic domain
        'useOIDC': False  # Agent branches use access keys, not OIDC
    }
    print(f"Creating dynamic environment config for branch: {branch_name}")
    print(f"Sanitized suffix: {sanitized_suffix}")
else:
    # Use predefined environment config
    env_config = predefined_environments.get(env_name)
    if not env_config:
        raise ValueError(f"Environment '{env_name}' not found in predefined environments and no branch provided")

print(f"Deploying to environment: {env_name}")
if branch_name:
    print(f"Branch name: {branch_name}")
print(f"Environment config: {env_config}")

# Deploy the main Spaceport stack with environment context
spaceport_stack = SpaceportStack(
    app,
    f"Spaceport{env_name.title()}Stack",
    env_config=env_config,
    env={
        'account': app.node.try_get_context('account') or None,  # Dynamically resolved
        'region': env_config['region']
    }
)

# Deploy the ML pipeline stack with environment context
ml_pipeline_stack = MLPipelineStack(
    app,
    f"SpaceportMLPipeline{env_name.title()}Stack",
    env_config=env_config,
    env={
        'account': app.node.try_get_context('account') or None,  # Dynamically resolved
        'region': env_config['region']
    }
)

# Deploy the Auth stack with environment context
auth_stack = AuthStack(
    app,
    f"SpaceportAuth{env_name.title()}Stack",
    env_config=env_config,
    env={
        'account': app.node.try_get_context('account') or None,  # Dynamically resolved
        'region': env_config['region']
    }
)

app.synth() 