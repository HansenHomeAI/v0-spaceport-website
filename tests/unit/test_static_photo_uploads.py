import importlib.util
import json
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
    / "projects"
    / "lambda_function.py"
)


class _FakeTable:
    def __init__(self):
        self.items = {
            ("user-123", "project-abc"): {
                "userSub": "user-123",
                "projectId": "project-abc",
                "title": "Static Photo Project",
            }
        }
        self.updated = None

    def get_item(self, Key):
        item = self.items.get((Key["userSub"], Key["projectId"]))
        return {"Item": item} if item else {}

    def query(self, **kwargs):
        return {"Items": []}

    def put_item(self, Item):
        self.items[(Item["userSub"], Item["projectId"])] = Item

    def update_item(self, **kwargs):
        self.updated = kwargs
        return {}


class _FakeDynamoResource:
    def __init__(self, table):
        self.table = table

    def Table(self, name):
        return self.table


class _FakeR2Client:
    def __init__(self):
        self.calls = []

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        self.calls.append((operation, Params, ExpiresIn))
        return f"https://upload.example.test/{Params['Key']}"


def _load_module(fake_table, fake_r2):
    for name in ("boto3", "botocore", "botocore.config", "botocore.exceptions", "stripe"):
        if name in sys.modules:
            del sys.modules[name]

    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.resource = lambda *args, **kwargs: _FakeDynamoResource(fake_table)
    fake_boto3.client = lambda *args, **kwargs: fake_r2
    fake_boto3.dynamodb = types.SimpleNamespace(
        conditions=types.SimpleNamespace(Key=lambda name: name)
    )
    sys.modules["boto3"] = fake_boto3

    fake_botocore = types.ModuleType("botocore")
    fake_botocore_config = types.ModuleType("botocore.config")
    fake_botocore_config.Config = lambda *args, **kwargs: None
    fake_botocore_exceptions = types.ModuleType("botocore.exceptions")
    fake_botocore_exceptions.ClientError = Exception
    sys.modules["botocore"] = fake_botocore
    sys.modules["botocore.config"] = fake_botocore_config
    sys.modules["botocore.exceptions"] = fake_botocore_exceptions

    fake_stripe = types.ModuleType("stripe")
    fake_stripe.api_key = None
    fake_stripe.checkout = types.SimpleNamespace(Session=types.SimpleNamespace(create=lambda **kwargs: None))
    fake_stripe.Subscription = types.SimpleNamespace(delete=lambda subscription_id: None)
    fake_stripe.error = types.SimpleNamespace(StripeError=Exception)
    sys.modules["stripe"] = fake_stripe

    os.environ["PROJECTS_TABLE_NAME"] = "Projects"
    os.environ["R2_ENDPOINT"] = "https://example.r2.cloudflarestorage.com"
    os.environ["R2_ACCESS_KEY_ID"] = "key"
    os.environ["R2_SECRET_ACCESS_KEY"] = "secret"
    os.environ["R2_BUCKET_NAME"] = "spaces-viewers"
    os.environ["R2_PUBLIC_BASE_URL"] = "https://spcprt.com/spaces/media"

    spec = importlib.util.spec_from_file_location("projects_lambda", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _event(path, body):
    return {
        "httpMethod": "POST",
        "path": path,
        "pathParameters": {"id": "project-abc"},
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "user-123",
                    "email": "owner@example.test",
                }
            }
        },
        "body": json.dumps(body),
    }


class StaticPhotoUploadTests(unittest.TestCase):
    def test_photo_keys_preserve_safe_folder_structure(self):
        module = _load_module(_FakeTable(), _FakeR2Client())

        key = module._build_static_photo_key(
            user_sub="user-123",
            project_id="project-abc",
            relative_path="Interior/Kitchen Hero.JPG",
        )

        self.assertEqual(
            key,
            "users/user-123/projects/project-abc/photos/Interior/Kitchen%20Hero.JPG",
        )

    def test_presign_endpoint_returns_public_urls_and_metadata(self):
        fake_table = _FakeTable()
        fake_r2 = _FakeR2Client()
        module = _load_module(fake_table, fake_r2)

        response = module.lambda_handler(
            _event(
                "/projects/project-abc/photo-upload-urls",
                {
                    "files": [
                        {
                            "name": "Kitchen Hero.JPG",
                            "relativePath": "Interior/Kitchen Hero.JPG",
                            "contentType": "image/jpeg",
                            "sizeBytes": 2048,
                        }
                    ]
                },
            ),
            None,
        )

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["bucket"], "spaces-viewers")
        self.assertEqual(body["publicBaseUrl"], "https://spcprt.com/spaces/media")
        self.assertEqual(
            body["files"][0]["objectKey"],
            "users/user-123/projects/project-abc/photos/Interior/Kitchen%20Hero.JPG",
        )
        self.assertEqual(
            body["files"][0]["publicUrl"],
            "https://spcprt.com/spaces/media/users/user-123/projects/project-abc/photos/Interior/Kitchen%20Hero.JPG",
        )
        self.assertEqual(fake_r2.calls[0][0], "put_object")
        self.assertEqual(fake_r2.calls[0][1]["ContentType"], "image/jpeg")

    def test_project_patch_accepts_photo_library_metadata(self):
        fake_table = _FakeTable()
        module = _load_module(fake_table, _FakeR2Client())

        response = module.lambda_handler(
            {
                "httpMethod": "PATCH",
                "path": "/projects/project-abc",
                "pathParameters": {"id": "project-abc"},
                "requestContext": {
                    "authorizer": {
                        "claims": {
                            "sub": "user-123",
                            "email": "owner@example.test",
                        }
                    }
                },
                "body": json.dumps(
                    {
                        "photoLibrary": {
                            "mode": "static_photos",
                            "bucket": "spaces-viewers",
                            "publicBaseUrl": "https://spcprt.com/spaces/media",
                            "folders": ["Interior"],
                            "files": [
                                {
                                    "originalName": "Kitchen Hero.JPG",
                                    "relativePath": "Interior/Kitchen Hero.JPG",
                                    "contentType": "image/jpeg",
                                    "sizeBytes": 2048,
                                    "objectKey": "users/user-123/projects/project-abc/photos/Interior/Kitchen%20Hero.JPG",
                                    "publicUrl": "https://spcprt.com/spaces/media/users/user-123/projects/project-abc/photos/Interior/Kitchen%20Hero.JPG",
                                    "uploadedAt": 1770000000000,
                                }
                            ],
                            "uploadedAt": 1770000000000,
                        }
                    }
                ),
            },
            None,
        )

        self.assertEqual(response["statusCode"], 200)
        expression_names = fake_table.updated["ExpressionAttributeNames"]
        self.assertIn("#photoLibrary", expression_names)
        self.assertEqual(expression_names["#photoLibrary"], "photoLibrary")


if __name__ == "__main__":
    unittest.main()
