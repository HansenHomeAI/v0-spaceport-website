import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    fake_boto3 = types.SimpleNamespace(client=lambda *_args, **_kwargs: object())
    with mock.patch.dict(sys.modules, {"boto3": fake_boto3}):
        spec.loader.exec_module(module)
    return module


class TestStateMachineArnResolution(unittest.TestCase):
    def test_start_ml_job_uses_state_machine_arn(self):
        with mock.patch.dict(
            os.environ,
            {"AWS_DEFAULT_REGION": "us-west-2", "STATE_MACHINE_ARN": "arn:state"},
            clear=False,
        ):
            module = _load_module(
                "start_ml_job_lambda",
                "infrastructure/spaceport_cdk/lambda/start_ml_job/lambda_function.py",
            )
            self.assertEqual(module.resolve_state_machine_arn(), "arn:state")

    def test_start_ml_job_falls_back_to_step_function_arn(self):
        with mock.patch.dict(
            os.environ,
            {"AWS_DEFAULT_REGION": "us-west-2", "STEP_FUNCTION_ARN": "arn:step"},
            clear=True,
        ):
            module = _load_module(
                "start_ml_job_lambda_fallback",
                "infrastructure/spaceport_cdk/lambda/start_ml_job/lambda_function.py",
            )
            self.assertEqual(module.resolve_state_machine_arn(), "arn:step")

    def test_ml_status_falls_back_to_step_function_arn(self):
        with mock.patch.dict(
            os.environ,
            {"AWS_DEFAULT_REGION": "us-west-2", "STEP_FUNCTION_ARN": "arn:step"},
            clear=True,
        ):
            module = _load_module(
                "ml_status_lambda_fallback",
                "infrastructure/spaceport_cdk/lambda/ml_status/lambda_function.py",
            )
            self.assertEqual(module.resolve_state_machine_arn(), "arn:step")


class TestStepFunctionsFailureSemantics(unittest.TestCase):
    def test_notify_error_chains_to_fail_state(self):
        stack_file = REPO_ROOT / "infrastructure/spaceport_cdk/spaceport_cdk/ml_pipeline_stack.py"
        source = stack_file.read_text()
        self.assertIn('sfn.Fail(', source)
        self.assertIn('notify_error.next(fail_pipeline)', source)
        self.assertIn('"PipelineFailed"', source)


if __name__ == "__main__":
    unittest.main()
