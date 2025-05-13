#!/usr/bin/env python3
from aws_cdk import App
from spaceport_cdk.spaceport_stack import SpaceportStack

app = App()
SpaceportStack(app, "SpaceportStack",
    env={
        'account': app.node.try_get_context('account') or None,
        'region': app.node.try_get_context('region') or 'us-west-2'
    }
)
app.synth() 