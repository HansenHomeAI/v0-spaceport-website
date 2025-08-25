#!/usr/bin/env python3
from aws_cdk import App, DefaultStackSynthesizer
from spaceport_cdk.spaceport_stack import SpaceportStack
from spaceport_cdk.auth_stack import AuthStack
from spaceport_cdk.ml_pipeline_stack import MLPipelineStack
# Subscription functionality will be integrated into AuthStack

app = App()

# Use a fixed qualifier so deployments target the correct bootstrap resources
stack_synthesizer = DefaultStackSynthesizer(qualifier="spcdkprod2")

# Deploy the existing Spaceport stack
spaceport_stack = SpaceportStack(
    app,
    "SpaceportStack",
    env={
        'account': app.node.try_get_context('account') or None,
        'region': app.node.try_get_context('region') or 'us-west-2'
    },
    synthesizer=stack_synthesizer,
)

# Deploy the new ML pipeline stack
ml_pipeline_stack = MLPipelineStack(
    app,
    "SpaceportMLPipelineStack",
    env={
        'account': app.node.try_get_context('account') or None,
        'region': app.node.try_get_context('region') or 'us-west-2'
    },
    synthesizer=stack_synthesizer,
)

# Deploy dedicated Auth stack (v2) to avoid legacy pool immutability
auth_stack = AuthStack(
    app,
    "SpaceportAuthStack",
    env={
        'account': app.node.try_get_context('account') or None,
        'region': app.node.try_get_context('region') or 'us-west-2'
    },
    synthesizer=stack_synthesizer,
)

# Subscription functionality integrated into AuthStack

app.synth() 