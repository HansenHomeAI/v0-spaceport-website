import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[2] / "infrastructure" / "spaceport_cdk" / "lambda" / "litchi_api" / "lambda_function.py"

sys.modules.setdefault(
    "boto3",
    types.SimpleNamespace(
        client=lambda *_args, **_kwargs: None,
        resource=lambda *_args, **_kwargs: None,
    ),
)

SPEC = importlib.util.spec_from_file_location("litchi_api", MODULE_PATH)
litchi_api = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(litchi_api)


class FakeTable:
    def __init__(self, item):
        self.item = item

    def get_item(self, Key):
        return {"Item": self.item}


class FakeStepFunctions:
    def __init__(self):
        self.calls = []

    def start_execution(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "executionArn": "arn:aws:states:us-west-2:123:execution:litchi:test",
            "startDate": litchi_api.datetime(2026, 5, 28, tzinfo=litchi_api.timezone.utc),
        }


class LitchiApiTests(unittest.TestCase):
    def test_status_reports_cached_hosted_browser_session(self):
        table = FakeTable({
            "status": "active",
            "storageState": "encrypted-browser-state",
            "credentials": "encrypted-credentials",
        })

        with patch.object(litchi_api, "_table", return_value=table):
            response = litchi_api._handle_status("user-123")

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue(body["connected"])
        self.assertTrue(body["sessionCached"])
        self.assertTrue(body["storageStateCached"])
        self.assertTrue(body["credentialsCached"])
        self.assertFalse(body["requiresReconnect"])

    def test_status_requires_reconnect_when_no_session_is_cached(self):
        table = FakeTable({"status": "expired"})

        with patch.object(litchi_api, "_table", return_value=table):
            response = litchi_api._handle_status("user-123")

        body = json.loads(response["body"])
        self.assertFalse(body["connected"])
        self.assertFalse(body["sessionCached"])
        self.assertFalse(body["storageStateCached"])
        self.assertFalse(body["credentialsCached"])
        self.assertTrue(body["requiresReconnect"])

    def test_upload_validates_empty_missions(self):
        response = litchi_api._handle_upload("user-123", {"missions": []})

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"], "missions must be a non-empty list")

    def test_upload_rejects_large_batches(self):
        response = litchi_api._handle_upload(
            "user-123",
            {"missions": [{"name": f"m-{idx}", "csv": "lat,lng\n"} for idx in range(13)]},
        )

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("cannot exceed 12", body["error"])

    def test_upload_sanitizes_names_and_starts_execution(self):
        fake_sfn = FakeStepFunctions()

        with patch.dict(litchi_api.os.environ, {"LITCHI_STATE_MACHINE_ARN": "arn:machine"}, clear=False):
            with patch.object(litchi_api.boto3, "client", return_value=fake_sfn):
                response = litchi_api._handle_upload(
                    "user-123456789",
                    {
                        "idempotencyKey": "batch 1!",
                        "missions": [{
                            "name": "Edgewood / Flight 🚁",
                            "csv": "latitude,longitude\n1,2\n",
                        }],
                    },
                )

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["executionArn"], "arn:aws:states:us-west-2:123:execution:litchi:test")
        self.assertEqual(fake_sfn.calls[0]["stateMachineArn"], "arn:machine")
        self.assertEqual(fake_sfn.calls[0]["name"], "litchi-user-123-batch-1")
        payload = json.loads(fake_sfn.calls[0]["input"])
        self.assertEqual(payload["totalMissions"], 1)
        self.assertEqual(payload["missions"][0]["name"], "Edgewood Flight")
        self.assertEqual(payload["missions"][0]["csv"], "latitude,longitude\n1,2\n")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
