#!/usr/bin/env python3
import os
import aws_cdk as cdk
from spaceport_cdk.spaceport_stack import SpaceportStack
from spaceport_cdk.ml_pipeline_stack import MLPipelineStack
from spaceport_cdk.codebuild_stack import CodeBuildStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region=os.getenv('CDK_DEFAULT_REGION')
)

# Main website stack
spaceport_stack = SpaceportStack(
    app, "SpaceportStack",
    env=env,
    description="Spaceport website infrastructure with S3, CloudFront, and API Gateway"
)

# ML Pipeline stack
ml_pipeline_stack = MLPipelineStack(
    app, "SpaceportMLPipelineStack", 
    env=env,
    description="ML pipeline infrastructure for 3D Gaussian Splatting with SageMaker"
)

# CodeBuild stack for SOGS container builds
codebuild_stack = CodeBuildStack(
    app, "SpaceportCodeBuildStack",
    env=env,
    description="CodeBuild infrastructure for building SOGS compression containers on AWS"
)

# Add tags to all stacks
for stack in [spaceport_stack, ml_pipeline_stack, codebuild_stack]:
    cdk.Tags.of(stack).add("Project", "Spaceport")
    cdk.Tags.of(stack).add("Environment", "Production")
    cdk.Tags.of(stack).add("Owner", "SpaceportTeam")

app.synth() 