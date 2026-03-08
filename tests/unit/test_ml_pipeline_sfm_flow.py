import json
import os
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
CDK_ROOT = REPO_ROOT / "infrastructure" / "spaceport_cdk"
if str(CDK_ROOT) not in sys.path:
    sys.path.insert(0, str(CDK_ROOT))

try:
    from aws_cdk import App
    from aws_cdk import aws_lambda as lambda_
    from aws_cdk.assertions import Template
    from spaceport_cdk.ml_pipeline_stack import MLPipelineStack
except ModuleNotFoundError:  # pragma: no cover - depends on local CDK env
    App = None
    lambda_ = None
    Template = None
    MLPipelineStack = None


@contextmanager
def working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def flatten_definition(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(flatten_definition(item) for item in value)
    if isinstance(value, dict):
        if "Fn::Join" in value:
            return "".join(flatten_definition(item) for item in value["Fn::Join"][1])
        return json.dumps(value, sort_keys=True)
    return str(value)


@unittest.skipIf(
    App is None or Template is None or MLPipelineStack is None or lambda_ is None,
    "aws_cdk is not installed",
)
class MlPipelineSfmFlowTests(unittest.TestCase):
    def test_pipeline_step_sfm_terminates_after_sfm_completion(self):
        env_config = {
            "resourceSuffix": "staging",
            "region": "us-west-2",
            "domain": "staging.spcprt.com",
        }

        with working_directory(CDK_ROOT):
            with patch.object(MLPipelineStack, "_bucket_exists", return_value=False), patch.object(
                MLPipelineStack, "_ecr_repo_exists", return_value=False
            ), patch.object(MLPipelineStack, "_validate_bucket_accessibility", return_value=True), patch.object(
                MLPipelineStack, "_check_s3_naming_conflicts", return_value=None
            ), patch.object(
                MLPipelineStack, "_run_preflight_deployment_check", return_value=None
            ), patch.object(
                lambda_.Code,
                "from_asset",
                return_value=lambda_.InlineCode("def handler(event, context):\n    return {}"),
            ):
                app = App()
                stack = MLPipelineStack(app, "TestPipelineStack", env_config=env_config)
                template = Template.from_stack(stack).to_json()

        state_machine = next(
            resource for resource in template["Resources"].values() if resource["Type"] == "AWS::StepFunctions::StateMachine"
        )
        definition = flatten_definition(state_machine["Properties"]["DefinitionString"])

        self.assertIn('"SfMOnlyComplete":{"Type":"Succeed"}', definition)
        self.assertIn('"SfMCompletionMode":{"Type":"Choice"', definition)
        self.assertIn('"PipelineStepChoice":{"Type":"Choice"', definition)
        self.assertIn('"StringEquals":"sfm"', definition)
        self.assertIn('"InstanceType.$":"$.sfmInstanceType"', definition)


if __name__ == "__main__":
    unittest.main()
