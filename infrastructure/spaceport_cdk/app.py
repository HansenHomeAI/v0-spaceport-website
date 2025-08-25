#!/usr/bin/env python3
from aws_cdk import App
from spaceport_cdk.spaceport_stack import SpaceportStack
from spaceport_cdk.auth_stack import AuthStack
from spaceport_cdk.ml_pipeline_stack import MLPipelineStack

app = App()

# Environment detection from context or default to staging
env_name = app.node.try_get_context('environment') or 'staging'
env_config = app.node.try_get_context('environments')[env_name]

print(f"Deploying to environment: {env_name}")
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