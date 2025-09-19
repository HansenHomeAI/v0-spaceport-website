#!/usr/bin/env python3
from aws_cdk import App
from spaceport_cdk.spaceport_stack import SpaceportStack
from spaceport_cdk.auth_stack import AuthStack
from spaceport_cdk.ml_pipeline_stack import MLPipelineStack

app = App()

# Environment detection from context or default to staging
env_name = app.node.try_get_context('environment') or 'staging'
agent_id = app.node.try_get_context('agent-id')

# Handle agent environments
if agent_id:
    # Agent environment - create dynamic config using staging base with agent suffix
    print(f"🤖 Agent deployment detected: {agent_id}")
    env_config = {
        'region': 'us-west-2',
        'resourceSuffix': f"staging-{agent_id}",  # Use staging account with agent suffix
        'domain': f'staging.spcprt.com',  # Use staging domain
        'useOIDC': False
    }
    # Create unique stack name for agent
    clean_agent_id = agent_id.replace('agent-', '').replace('-', '')
    stack_name = f"SpaceportAgent{clean_agent_id.title()}Stack"
else:
    # Standard environment
    try:
        env_config = app.node.try_get_context('environments')[env_name]
        stack_name = f"Spaceport{env_name.title()}Stack"
    except (TypeError, KeyError):
        # Fallback for missing environments context
        print(f"⚠️ No environments context found, using default staging config")
        env_config = {
            'region': 'us-west-2',
            'resourceSuffix': 'staging',
            'domain': 'staging.spcprt.com',
            'useOIDC': False
        }
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