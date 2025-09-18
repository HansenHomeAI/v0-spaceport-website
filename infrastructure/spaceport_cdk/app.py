#!/usr/bin/env python3
from aws_cdk import App
from spaceport_cdk.spaceport_stack import SpaceportStack
from spaceport_cdk.auth_stack import AuthStack
from spaceport_cdk.ml_pipeline_stack import MLPipelineStack

app = App()

# Environment detection from context or default to staging
env_name = app.node.try_get_context('environment') or 'staging'

# Handle agent environments
if env_name.startswith('agent-'):
    # Agent environment - create dynamic config
    agent_id = env_name.replace('agent-', '')
    env_config = {
        'region': 'us-west-2',
        'resourceSuffix': agent_id,
        'domain': f'agent-{agent_id}.spaceport-staging.com',
        'useOIDC': False
    }
    stack_name = f"SpaceportAgent{agent_id.title().replace('-', '')}Stack"
else:
    # Standard environment
    env_config = app.node.try_get_context('environments')[env_name]
    stack_name = f"Spaceport{env_name.title()}Stack"

print(f"Deploying to environment: {env_name}")
print(f"Environment config: {env_config}")
print(f"Stack name: {stack_name}")

# Deploy the main Spaceport stack with environment context
spaceport_stack = SpaceportStack(
    app,
    stack_name,
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