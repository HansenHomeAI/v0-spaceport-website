import json
import sys
import types
import unittest
import importlib.util
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[2] / "infrastructure" / "lambda" / "subscription_manager" / "lambda_function.py"

if "stripe" not in sys.modules:
    fake_stripe = types.SimpleNamespace()
    fake_stripe.api_key = None
    fake_stripe.checkout = types.SimpleNamespace(
        Session=types.SimpleNamespace(create=lambda **_kwargs: types.SimpleNamespace(id="sess", url=""))
    )
    fake_stripe.Webhook = types.SimpleNamespace(construct_event=lambda *args, **kwargs: {})
    fake_stripe.Subscription = types.SimpleNamespace(modify=lambda *args, **kwargs: None)
    fake_stripe.error = types.SimpleNamespace(SignatureVerificationError=Exception)
    sys.modules["stripe"] = fake_stripe
SPEC = importlib.util.spec_from_file_location("subscription_lambda", MODULE_PATH)
subscription_module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(subscription_module)


class FakeTable:
    def __init__(self):
        self._items = {}

    def get_item(self, Key):
        user_sub = Key.get("userSub")
        if user_sub in self._items:
            return {"Item": deepcopy(self._items[user_sub])}
        return {}

    def put_item(self, Item):
        self._items[Item["userSub"]] = deepcopy(Item)


class FakeDynamoResource:
    def __init__(self, table):
        self._table = table

    def Table(self, _name):
        return self._table


class FakeCognitoClient:
    def admin_update_user_attributes(self, **_kwargs):
        return None


class SubscriptionManagerTests(unittest.TestCase):
    def setUp(self):
        self.table = FakeTable()
        self.dynamo_patch = patch.object(subscription_module, "dynamodb", FakeDynamoResource(self.table))
        self.cognito_patch = patch.object(subscription_module, "cognito_idp", FakeCognitoClient())
        self.dynamo_patch.start()
        self.cognito_patch.start()
        self.addCleanup(self.dynamo_patch.stop)
        self.addCleanup(self.cognito_patch.stop)

    def _bootstrap_user(self, user_sub: str = "user-123"):
        subscription_module.create_default_user_profile(user_sub)
        return user_sub

    def test_update_user_subscription_additive_limit(self):
        user_sub = self._bootstrap_user()

        subscription_module.update_user_subscription(user_sub, "sub_test", "starter", "active")
        record = deepcopy(self.table._items[user_sub])

        self.assertEqual(record["maxModels"], 10)
        self.assertEqual(record["planFeatures"]["maxModels"], 10)
        self.assertEqual(record["planFeatures"].get("addonMaxModels"), 5)

        # Idempotent reprocessing keeps the limit stable
        subscription_module.update_user_subscription(user_sub, "sub_test", "starter", "active")
        record_again = deepcopy(self.table._items[user_sub])
        self.assertEqual(record_again["maxModels"], 10)
        self.assertEqual(record_again["planFeatures"]["maxModels"], 10)

    def test_canceled_subscription_reverts_to_base_limit(self):
        user_sub = self._bootstrap_user()
        subscription_module.update_user_subscription(user_sub, "sub_test", "starter", "active")
        subscription_module.update_user_subscription(user_sub, "sub_test", "starter", "canceled")

        record = deepcopy(self.table._items[user_sub])
        self.assertEqual(record["maxModels"], 5)
        self.assertEqual(record["planFeatures"]["maxModels"], 5)
        self.assertEqual(record["status"], "canceled")

    def test_get_subscription_status_returns_expected_payload(self):
        user_sub = self._bootstrap_user()
        subscription_module.update_user_subscription(user_sub, "sub_test", "starter", "active")

        event = {
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": user_sub
                    }
                }
            }
        }

        response = subscription_module.get_subscription_status(event)
        self.assertEqual(response["statusCode"], 200)

        body = json.loads(response["body"])
        subscription = body["subscription"]
        self.assertEqual(subscription["status"], "active")
        self.assertEqual(subscription["planType"], "starter")
        self.assertEqual(subscription["planFeatures"]["maxModels"], 10)
        self.assertEqual(subscription["maxModels"], 10)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
