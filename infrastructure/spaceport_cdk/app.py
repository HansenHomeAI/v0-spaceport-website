#!/usr/bin/env python3
import os
from aws_cdk import core as cdk

from spaceport_cdk.spaceport_stack import SpaceportStack

app = cdk.App()

SpaceportStack(
    app, 
    "SpaceportStack",
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION", "us-west-2")
    ),
)

app.synth() 