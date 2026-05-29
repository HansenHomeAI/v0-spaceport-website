import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[2] / "infrastructure" / "spaceport_cdk" / "lambda" / "litchi_worker" / "lambda_function.py"

sys.modules.setdefault(
    "boto3",
    types.SimpleNamespace(
        client=lambda *_args, **_kwargs: None,
        resource=lambda *_args, **_kwargs: None,
    ),
)

SPEC = importlib.util.spec_from_file_location("litchi_worker", MODULE_PATH)
litchi_worker = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(litchi_worker)


class FakeKMS:
    def encrypt(self, KeyId, Plaintext, **_kwargs):
        return {"CiphertextBlob": Plaintext[::-1]}

    def decrypt(self, CiphertextBlob, **_kwargs):
        return {"Plaintext": CiphertextBlob[::-1]}


class FakeTable:
    def __init__(self, item):
        self.item = item

    def get_item(self, Key):
        return {"Item": self.item}

    def put_item(self, Item):
        self.item = Item


class LitchiWorkerTests(unittest.TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        with patch.object(litchi_worker, "_kms_client", return_value=FakeKMS()):
            ciphertext = litchi_worker._encrypt_text("hello", "key")
            plaintext = litchi_worker._decrypt_text(ciphertext)
            self.assertEqual(plaintext, "hello")

    def test_storage_state_roundtrip(self):
        state = {
            "cookies": [{"name": "session", "value": "abc", "domain": ".flylitchi.com"}],
            "origins": [
                {
                    "origin": "https://flylitchi.com",
                    "localStorage": [{"name": "Parse/currentUser", "value": "{}"}],
                }
            ],
        }
        with patch.object(litchi_worker, "_kms_client", return_value=FakeKMS()):
            ciphertext = litchi_worker._serialize_storage_state(state, "key")
            self.assertEqual(litchi_worker._deserialize_storage_state(ciphertext), state)

    def test_jitter_seconds_range(self):
        for _ in range(50):
            value = litchi_worker._jitter_seconds()
            self.assertGreaterEqual(value, 12)
            self.assertLessEqual(value, 25)

    def test_detect_rate_limit(self):
        self.assertTrue(litchi_worker._detect_rate_limit("Too many requests"))
        self.assertTrue(litchi_worker._detect_rate_limit("HTTP 429"))
        self.assertFalse(litchi_worker._detect_rate_limit("All good"))

    def test_dry_run_upload_updates_progress_without_browser(self):
        with patch.object(litchi_worker, "_kms_client", return_value=FakeKMS()):
            cookies = litchi_worker._serialize_cookies([{"name": "session", "value": "abc"}], "key")

        table = FakeTable({"userId": "user-123", "cookies": cookies})

        with patch.dict(litchi_worker.os.environ, {
            "LITCHI_WORKER_DRY_RUN": "1",
            "LITCHI_KMS_KEY_ID": "key",
        }, clear=False):
            with patch.object(litchi_worker, "_kms_client", return_value=FakeKMS()):
                with patch.object(litchi_worker, "_dynamodb_table", return_value=table):
                    result = litchi_worker.lambda_handler({
                        "mode": "upload",
                        "userId": "user-123",
                        "mission": {"name": "edgewood_flight-01-of-02_20260528-1407", "csv": "lat,lng\n"},
                        "missionIndex": 0,
                        "missionTotal": 2,
                    }, None)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(table.item["status"], "active")
        self.assertEqual(table.item["progress"]["label"], "Uploaded 1/2")
        self.assertIn("Uploaded edgewood_flight-01-of-02_20260528-1407 (dry run)", table.item["message"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
