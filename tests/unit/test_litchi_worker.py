import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[2] / "infrastructure" / "spaceport_cdk" / "lambda" / "litchi_worker" / "lambda_function.py"

SPEC = importlib.util.spec_from_file_location("litchi_worker", MODULE_PATH)
litchi_worker = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(litchi_worker)


class FakeKMS:
    def encrypt(self, KeyId, Plaintext):
        return {"CiphertextBlob": Plaintext[::-1]}

    def decrypt(self, CiphertextBlob):
        return {"Plaintext": CiphertextBlob[::-1]}


class LitchiWorkerTests(unittest.TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        with patch.object(litchi_worker, "_kms_client", return_value=FakeKMS()):
            ciphertext = litchi_worker._encrypt_text("hello", "key")
            plaintext = litchi_worker._decrypt_text(ciphertext)
            self.assertEqual(plaintext, "hello")

    def test_jitter_seconds_range(self):
        for _ in range(50):
            value = litchi_worker._jitter_seconds()
            self.assertGreaterEqual(value, 12)
            self.assertLessEqual(value, 25)

    def test_detect_rate_limit(self):
        self.assertTrue(litchi_worker._detect_rate_limit("Too many requests"))
        self.assertTrue(litchi_worker._detect_rate_limit("HTTP 429"))
        self.assertFalse(litchi_worker._detect_rate_limit("All good"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
