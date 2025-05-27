#!/usr/bin/env python3
from aws_cdk import App
from spaceport_cdk.spaceport_stack import SpaceportStack
from spaceport_cdk.ml_pipeline_stack import MLPipelineStack

app = App()

# Deploy the existing Spaceport stack
spaceport_stack = SpaceportStack(app, "SpaceportStack",
    env={
        'account': app.node.try_get_context('account') or None,
        'region': app.node.try_get_context('region') or 'us-west-2'
    }
)

# Deploy the new ML pipeline stack
ml_pipeline_stack = MLPipelineStack(app, "SpaceportMLPipelineStack",
    env={
        'account': app.node.try_get_context('account') or None,
        'region': app.node.try_get_context('region') or 'us-west-2'
    }
)

app.synth() 