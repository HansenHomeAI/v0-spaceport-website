import importlib.util
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "infrastructure"
    / "spaceport_cdk"
    / "lambda"
    / "presign_ml_artifact"
    / "lambda_function.py"
)


def load_module():
    botocore_stub = types.ModuleType("botocore")
    botocore_config_stub = types.ModuleType("botocore.config")
    botocore_config_stub.Config = lambda **kwargs: kwargs
    sys.modules["botocore"] = botocore_stub
    sys.modules["botocore.config"] = botocore_config_stub
    boto3_stub = types.ModuleType("boto3")
    boto3_stub.client = lambda *_args, **_kwargs: types.SimpleNamespace(generate_presigned_url=lambda **_kw: "")
    sys.modules["boto3"] = boto3_stub
    spec = importlib.util.spec_from_file_location("presign_ml_artifact_lambda", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PresignMlArtifactTests(unittest.TestCase):
    def test_signs_urls_for_current_ml_bucket(self):
        module = load_module()
        event = {
            "httpMethod": "POST",
            "body": json.dumps(
                {
                    "urls": [
                        "https://spaceport-ml-processing-staging.s3.amazonaws.com/colmap/job-123/sparse/0/images.txt"
                    ]
                }
            ),
        }

        with patch.dict(os.environ, {"ML_BUCKET": "spaceport-ml-processing-staging"}, clear=False), patch.object(
            module.s3, "generate_presigned_url", return_value="https://signed.example.com/images.txt"
        ) as presign:
            response = module.lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 200)
        payload = json.loads(response["body"])
        self.assertEqual(
            payload["artifacts"],
            [
                {
                    "sourceUrl": "https://spaceport-ml-processing-staging.s3.amazonaws.com/colmap/job-123/sparse/0/images.txt",
                    "signedUrl": "https://signed.example.com/images.txt",
                }
            ],
        )
        presign.assert_called_once()

    def test_rejects_urls_for_other_buckets(self):
        module = load_module()
        event = {
            "httpMethod": "POST",
            "body": json.dumps(
                {
                    "urls": [
                        "https://spaceport-ml-processing.s3.amazonaws.com/colmap/job-123/sparse/0/images.txt"
                    ]
                }
            ),
        }

        with patch.dict(os.environ, {"ML_BUCKET": "spaceport-ml-processing-staging"}, clear=False):
            response = module.lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 403)
        payload = json.loads(response["body"])
        self.assertIn("not allowed", payload["error"])


if __name__ == "__main__":
    unittest.main()
