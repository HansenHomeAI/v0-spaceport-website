import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "infrastructure"
    / "spaceport_cdk"
    / "lambda"
    / "ml_publish_bundle"
    / "lambda_function.py"
)


class _FakePaginator:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def paginate(self, **kwargs):
        self.calls.append(kwargs)
        return list(self.pages)


class _FakeS3Client:
    def __init__(self, pages):
        self.paginator = _FakePaginator(pages)
        self.copy_calls = []

    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return self.paginator

    def copy_object(self, **kwargs):
        self.copy_calls.append(kwargs)


def _load_module(fake_s3):
    if "boto3" in sys.modules:
        del sys.modules["boto3"]

    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.client = lambda service_name, *args, **kwargs: fake_s3
    sys.modules["boto3"] = fake_boto3

    spec = importlib.util.spec_from_file_location("ml_publish_bundle_lambda", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PublishBundleLambdaTests(unittest.TestCase):
    def setUp(self):
        os.environ["DELIVERY_BUCKET"] = "edge-bundles"
        os.environ["EDGE_DISTRIBUTION_DOMAIN"] = "d111111abcdef8.cloudfront.net"

    def test_copies_bundle_with_expected_headers_and_url(self):
        fake_s3 = _FakeS3Client(
            [
                {
                    "Contents": [
                        {"Key": "compressed/job-123/supersplat_bundle/meta.json"},
                        {"Key": "compressed/job-123/supersplat_bundle/lod-meta.json"},
                        {"Key": "compressed/job-123/supersplat_bundle/0_0/meta.json"},
                        {"Key": "compressed/job-123/supersplat_bundle/means_l.webp"},
                        {"Key": "compressed/job-123/supersplat_bundle/0_0/means_l.webp"},
                        {"Key": "compressed/job-123/supersplat_bundle/skybox/kloppenheim_06_puresky_equirect.webp"},
                    ]
                }
            ]
        )
        module = _load_module(fake_s3)

        result = module.lambda_handler(
            {"jobId": "job-123", "compressedOutputS3Uri": "s3://ml-bucket/compressed/job-123/"},
            None,
        )

        self.assertEqual(
            result["edgeBundleUrl"],
            "https://d111111abcdef8.cloudfront.net/models/job-123/supersplat_bundle/meta.json",
        )
        self.assertEqual(
            result["edgeLodBundleUrl"],
            "https://d111111abcdef8.cloudfront.net/models/job-123/supersplat_bundle/lod-meta.json",
        )
        self.assertEqual(result["copiedObjectCount"], 6)
        self.assertEqual(fake_s3.paginator.calls[0]["Prefix"], "compressed/job-123/supersplat_bundle/")
        self.assertEqual(fake_s3.copy_calls[0]["ContentType"], "application/json")
        self.assertEqual(fake_s3.copy_calls[1]["ContentType"], "application/json")
        self.assertEqual(fake_s3.copy_calls[2]["ContentType"], "application/json")
        self.assertEqual(fake_s3.copy_calls[3]["ContentType"], "image/webp")
        self.assertEqual(fake_s3.copy_calls[4]["ContentType"], "image/webp")
        self.assertEqual(fake_s3.copy_calls[5]["ContentType"], "image/webp")
        self.assertEqual(
            fake_s3.copy_calls[4]["CacheControl"],
            "public, max-age=31536000, s-maxage=31536000, immutable",
        )

    def test_raises_when_meta_json_is_missing(self):
        fake_s3 = _FakeS3Client(
            [{"Contents": [{"Key": "compressed/job-123/supersplat_bundle/means_l.webp"}]}]
        )
        module = _load_module(fake_s3)

        with self.assertRaises(ValueError):
            module.lambda_handler(
                {"jobId": "job-123", "compressedOutputS3Uri": "s3://ml-bucket/compressed/job-123/"},
                None,
            )
