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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
