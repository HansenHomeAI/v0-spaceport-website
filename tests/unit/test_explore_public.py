import importlib.util
import json
import sys
import types
import unittest
from decimal import Decimal
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "infrastructure"
    / "spaceport_cdk"
    / "lambda"
    / "explore_public"
    / "lambda_function.py"
)

SPEC = importlib.util.spec_from_file_location("explore_public_lambda", MODULE_PATH)
explore_public_module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader

if "boto3" not in sys.modules:
    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.resource = lambda *args, **kwargs: None
    sys.modules["boto3"] = fake_boto3

if "boto3.dynamodb" not in sys.modules:
    sys.modules["boto3.dynamodb"] = types.ModuleType("boto3.dynamodb")

if "boto3.dynamodb.conditions" not in sys.modules:
    fake_conditions = types.ModuleType("boto3.dynamodb.conditions")

    class _FakeCondition:
        def eq(self, value):
            return ("eq", value)

    fake_conditions.Key = lambda *args, **kwargs: _FakeCondition()
    fake_conditions.Attr = lambda *args, **kwargs: _FakeCondition()
    sys.modules["boto3.dynamodb.conditions"] = fake_conditions

SPEC.loader.exec_module(explore_public_module)


class _FakeTable:
    def __init__(self, *, query_response=None, scan_responses=None, query_error=None):
        self.query_response = query_response or {}
        self.scan_responses = list(scan_responses or [])
        self.query_error = query_error

    def query(self, **kwargs):
        if self.query_error:
            raise self.query_error
        return self.query_response

    def scan(self, **kwargs):
        if self.scan_responses:
            return self.scan_responses.pop(0)
        return {"Items": []}


class _FakeDynamoResource:
    def __init__(self, tables):
        self.tables = tables

    def Table(self, name):
        return self.tables[name]


class ExplorePublicLambdaTests(unittest.TestCase):
    def test_shape_item_serializes_decimal_fields(self):
        shaped = explore_public_module._shape_item(
            {
                "listingId": "listing-123",
                "viewerTitle": "Forest Creek",
                "cityState": "St. George, UT",
                "viewerUrl": "https://example.com/spaces/forest-creek",
                "thumbnailUrl": "https://example.com/spaces/forest-creek/thumb.jpg",
                "updatedAt": Decimal("1700000000"),
            }
        )

        self.assertEqual(
            shaped,
            {
                "id": "listing-123",
                "title": "Forest Creek",
                "location": "St. George, UT",
                "viewerUrl": "https://example.com/spaces/forest-creek",
                "thumbnailUrl": "https://example.com/spaces/forest-creek/thumb.jpg",
                "updatedAt": 1700000000,
            },
        )

    def test_scan_fallback_filters_blank_viewers_and_sorts_descending(self):
        table = _FakeTable(
            query_error=RuntimeError("gsi missing"),
            scan_responses=[
                {
                    "Items": [
                        {
                            "listingId": "older",
                            "viewerTitle": "Older",
                            "viewerUrl": "https://example.com/older",
                            "thumbnailUrl": "https://example.com/older/thumb.jpg",
                            "updatedAt": Decimal("10"),
                        },
                        {
                            "listingId": "skip-me",
                            "viewerTitle": "No Viewer",
                            "viewerUrl": "",
                            "updatedAt": Decimal("50"),
                        },
                        {
                            "listingId": "newer",
                            "viewerTitle": "Newer",
                            "viewerUrl": "https://example.com/newer",
                            "thumbnailUrl": "https://example.com/newer/thumb.jpg",
                            "updatedAt": Decimal("20"),
                        },
                    ]
                }
            ],
        )
        explore_public_module.TABLE_NAME = "ExploreListings"
        explore_public_module.PROJECTS_TABLE_NAME = None
        explore_public_module.dynamodb = _FakeDynamoResource({"ExploreListings": table})

        response = explore_public_module.lambda_handler(
            {
                "httpMethod": "GET",
                "queryStringParameters": {"visibility": "public", "limit": "5"},
            },
            None,
        )

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual([item["id"] for item in body["items"]], ["newer", "older"])
        self.assertEqual(body["items"][0]["updatedAt"], 20)
        self.assertIsNone(body["nextCursor"])

    def test_projects_fallback_supplements_sparse_listing_results(self):
        listings_table = _FakeTable(
            query_response={
                "Items": [
                    {
                        "listingId": "listed",
                        "viewerTitle": "Listed Model",
                        "viewerUrl": "https://spcprt.com/spaces/listed-model",
                        "thumbnailUrl": "https://spcprt.com/spaces/listed-model/thumb.jpg",
                        "updatedAt": Decimal("30"),
                    }
                ]
            }
        )
        projects_table = _FakeTable(
            scan_responses=[
                {
                    "Items": [
                        {
                            "projectId": "proj-new",
                            "status": "delivered",
                            "paymentStatus": "paid",
                            "title": "Newest Project",
                            "modelLink": "https://spcprt.com/spaces/newest-project",
                            "updatedAt": Decimal("50"),
                            "createdAt": Decimal("40"),
                        },
                        {
                            "projectId": "proj-dup",
                            "status": "delivered",
                            "paymentStatus": "paid",
                            "title": "Duplicate Project",
                            "modelLink": "https://spcprt.com/spaces/listed-model",
                            "updatedAt": Decimal("45"),
                            "createdAt": Decimal("45"),
                        },
                        {
                            "projectId": "proj-unpaid",
                            "status": "delivered",
                            "paymentStatus": "pending",
                            "title": "Unpaid Project",
                            "modelLink": "https://spcprt.com/spaces/unpaid-project",
                            "updatedAt": Decimal("60"),
                            "createdAt": Decimal("60"),
                        },
                    ]
                }
            ]
        )
        explore_public_module.TABLE_NAME = "ExploreListings"
        explore_public_module.PROJECTS_TABLE_NAME = "Projects"
        explore_public_module.dynamodb = _FakeDynamoResource(
            {
                "ExploreListings": listings_table,
                "Projects": projects_table,
            }
        )

        response = explore_public_module.lambda_handler(
            {
                "httpMethod": "GET",
                "queryStringParameters": {"visibility": "public", "limit": "5"},
            },
            None,
        )

        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(
            [item["id"] for item in body["items"]],
            ["proj-new", "listed"],
        )
        self.assertEqual(
            body["items"][0]["thumbnailUrl"],
            "https://spcprt.com/spaces/newest-project/thumb.jpg",
        )
        self.assertIsNone(body["nextCursor"])


if __name__ == "__main__":
    unittest.main()
