import importlib.util
import json
import os
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "infrastructure"
    / "spaceport_cdk"
    / "lambda"
    / "ml_status"
    / "lambda_function.py"
)


class _FakeExecutionDoesNotExist(Exception):
    pass


class _FakeStepFunctionsClient:
    def __init__(self, describe_response, history_response):
        self.describe_response = describe_response
        self.history_response = history_response
        self.exceptions = types.SimpleNamespace(ExecutionDoesNotExist=_FakeExecutionDoesNotExist)

    def describe_execution(self, **kwargs):
        return self.describe_response

    def get_execution_history(self, **kwargs):
        return self.history_response


def _load_module(fake_stepfunctions):
    if "boto3" in sys.modules:
        del sys.modules["boto3"]

    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.client = lambda service_name, *args, **kwargs: fake_stepfunctions
    sys.modules["boto3"] = fake_boto3

    spec = importlib.util.spec_from_file_location("ml_status_lambda", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class MLStatusLambdaTests(unittest.TestCase):
    def setUp(self):
        os.environ["STATE_MACHINE_ARN"] = (
            "arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging"
        )

    def test_returns_edge_bundle_url_when_execution_succeeds(self):
        start_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        fake_stepfunctions = _FakeStepFunctionsClient(
            describe_response={
                "status": "SUCCEEDED",
                "startDate": start_time,
                "output": json.dumps(
                    {
                        "publishResult": {
                            "edgeBundleUrl": "https://d111111abcdef8.cloudfront.net/models/job-123/supersplat_bundle/meta.json",
                            "edgeLodBundleUrl": "https://d111111abcdef8.cloudfront.net/models/job-123/supersplat_bundle/lod-meta.json",
                        }
                    }
                ),
            },
            history_response={"events": []},
        )
        module = _load_module(fake_stepfunctions)

        response = module.lambda_handler({"pathParameters": {"jobId": "job-123"}}, None)

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(
            body["edgeBundleUrl"],
            "https://d111111abcdef8.cloudfront.net/models/job-123/supersplat_bundle/meta.json",
        )
        self.assertEqual(
            body["edgeLodBundleUrl"],
            "https://d111111abcdef8.cloudfront.net/models/job-123/supersplat_bundle/lod-meta.json",
        )

    def test_omits_edge_bundle_url_while_execution_is_running(self):
        start_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        fake_stepfunctions = _FakeStepFunctionsClient(
            describe_response={"status": "RUNNING", "startDate": start_time},
            history_response={"events": []},
        )
        module = _load_module(fake_stepfunctions)

        response = module.lambda_handler({"pathParameters": {"jobId": "job-123"}}, None)

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertNotIn("edgeBundleUrl", body)
        self.assertNotIn("edgeLodBundleUrl", body)
