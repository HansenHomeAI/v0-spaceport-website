import json
import importlib.util
import os
import sys
import types
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from boto3.dynamodb.conditions import Key

if "resend" not in sys.modules:
    fake_resend = types.SimpleNamespace()
    fake_resend.Emails = types.SimpleNamespace(send=lambda *args, **_kwargs: None)
    sys.modules["resend"] = fake_resend

os.environ.setdefault("COGNITO_USER_POOL_ID", "pool-id")
os.environ.setdefault("PROJECTS_TABLE_NAME", "Projects")
os.environ.setdefault("PERMISSIONS_TABLE_NAME", "Permissions")
os.environ.setdefault("APP_BASE_URL", "https://app.spaceport.test")
os.environ.setdefault("RESEND_API_KEY", "dummy")

MODULE_PATH = Path(__file__).resolve().parents[2] / "infrastructure" / "spaceport_cdk" / "lambda" / "model_delivery_admin" / "lambda_function.py"
SPEC = importlib.util.spec_from_file_location("model_delivery_lambda", MODULE_PATH)
model_delivery_module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(model_delivery_module)


class FakeProjectsTable:
    def __init__(self):
        # key: (userSub, projectId)
        self._items = {}

    def put_item(self, Item):  # pragma: no cover - convenience helper
        self._items[(Item["userSub"], Item["projectId"])] = deepcopy(Item)

    def get_item(self, Key):
        key = (Key["userSub"], Key["projectId"])
        if key in self._items:
            return {"Item": deepcopy(self._items[key])}
        return {}

    def update_item(self, Key, UpdateExpression, ExpressionAttributeNames, ExpressionAttributeValues):
        key = (Key["userSub"], Key["projectId"])
        record = deepcopy(self._items[key])
        expression = UpdateExpression.replace("SET", "", 1).strip()
        for assignment in expression.split(","):
            alias_name, alias_value = [segment.strip() for segment in assignment.split("=")]
            attr_name = ExpressionAttributeNames[alias_name]
            value = deepcopy(ExpressionAttributeValues[alias_value])
            record[attr_name] = value
        self._items[key] = record

    def query(self, KeyConditionExpression=None, **_kwargs):
        user_sub = None
        if isinstance(KeyConditionExpression, type(Key("userSub").eq("dummy"))):
            _key_obj, value = KeyConditionExpression._values  # type: ignore[attr-defined]
            user_sub = value
        results = [deepcopy(item) for (sub, _pid), item in self._items.items() if sub == user_sub]
        return {"Items": results}


class FakePermissionsTable:
    def __init__(self, records=None):
        self.records = records or {}

    def get_item(self, Key):
        user_id = Key.get("user_id")
        if user_id in self.records:
            return {"Item": deepcopy(self.records[user_id])}
        return {}


class FakeCognitoClient:
    def __init__(self, directory=None):
        self.directory = directory or {}

    def admin_get_user(self, UserPoolId, Username):  # pylint: disable=unused-argument
        if Username not in self.directory:
            raise self.exceptions.UserNotFoundException  # type: ignore[attr-defined]
        return deepcopy(self.directory[Username])

    class exceptions:  # pylint: disable=too-few-public-methods
        class UserNotFoundException(Exception):
            pass


class ModelDeliveryLambdaTests(unittest.TestCase):
    def setUp(self):
        self.projects_table = FakeProjectsTable()
        self.permissions_table = FakePermissionsTable(
            {
                "admin-user": {
                    "user_id": "admin-user",
                    "permission_type": "model_delivery_admin",
                    "status": "active",
                }
            }
        )
        self.cognito_directory = {
            "client@example.com": {
                "Username": "client@example.com",
                "UserAttributes": [
                    {"Name": "sub", "Value": "client-sub"},
                    {"Name": "preferred_username", "Value": "client-handle"},
                    {"Name": "email", "Value": "client@example.com"},
                ],
            }
        }

        self.projects_table.put_item(
            {
                "userSub": "client-sub",
                "projectId": "proj-123",
                "title": "Downtown Tower",
                "status": "processing",
                "progress": 70,
            }
        )

        self.projects_patch = patch.object(model_delivery_module, "projects_table", self.projects_table)
        self.permissions_patch = patch.object(model_delivery_module, "permissions_table", self.permissions_table)
        self.cognito_patch = patch.object(model_delivery_module, "cognito", FakeCognitoClient(self.cognito_directory))
        self.email_patch = patch.object(model_delivery_module.resend.Emails, "send")

        for patcher in (self.projects_patch, self.permissions_patch, self.cognito_patch, self.email_patch):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _auth_event(self, method: str, path: str, body: dict | None = None, user_id: str = "admin-user"):
        event = {
            "httpMethod": method,
            "path": path,
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": user_id,
                        "email": "admin@example.com",
                        "preferred_username": "admin",
                    }
                }
            },
        }
        if body is not None:
            event["body"] = json.dumps(body)
        return event

    def test_check_permission_honors_permissions_table(self):
        event = self._auth_event("GET", "/admin/model-delivery/check-permission")
        response = model_delivery_module.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 200)
        payload = json.loads(response["body"])
        self.assertTrue(payload["has_model_delivery_permission"])

    def test_list_projects_returns_trimmed_payload(self):
        event = self._auth_event(
            "POST",
            "/admin/model-delivery/list-projects",
            {"email": "client@example.com"},
        )
        response = model_delivery_module.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 200)
        payload = json.loads(response["body"])
        self.assertEqual(len(payload["projects"]), 1)
        project = payload["projects"][0]
        self.assertEqual(project["projectId"], "proj-123")
        self.assertEqual(project["title"], "Downtown Tower")
        self.assertEqual(project["status"], "processing")
        self.assertIn("delivery", project)

    def test_send_delivery_rejects_invalid_url(self):
        event = self._auth_event(
            "POST",
            "/admin/model-delivery/send",
            {"email": "client@example.com", "projectId": "proj-123", "link": "notaurl"},
        )
        response = model_delivery_module.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("Delivery link must be a valid URL", response["body"])

    def test_send_delivery_updates_project_and_sends_email(self):
        event = self._auth_event(
            "POST",
            "/admin/model-delivery/send",
            {
                "email": "client@example.com",
                "projectId": "proj-123",
                "link": "https://cdn.spaceport.ai/models/demo.glb",
            },
        )
        response = model_delivery_module.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 200)
        payload = json.loads(response["body"])
        self.assertTrue(payload["ok"])

        stored = self.projects_table._items[("client-sub", "proj-123")]
        delivery = stored["delivery"]
        self.assertEqual(delivery["link"], "https://cdn.spaceport.ai/models/demo.glb")
        self.assertEqual(stored["progress"], 100)
        model_delivery_module.resend.Emails.send.assert_called_once()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
