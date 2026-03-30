import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_cdk_endpoint_policy import (
    collect_rest_api_endpoint_types,
    find_regional_violations,
    load_templates,
    resolve_required_regional_stacks,
)


class CdkEndpointPolicyTests(unittest.TestCase):
    def test_collect_rest_api_endpoint_types_defaults_to_edge_when_missing(self):
        template = {
            "Resources": {
                "PreviewApi": {
                    "Type": "AWS::ApiGateway::RestApi",
                    "Properties": {},
                }
            }
        }

        self.assertEqual(
            collect_rest_api_endpoint_types(template),
            {"PreviewApi": []},
        )

    def test_find_regional_violations_flags_missing_endpoint_type(self):
        templates = {
            "SpaceportPreviewABCDEF1234Stack": {
                "Resources": {
                    "PreviewApi": {
                        "Type": "AWS::ApiGateway::RestApi",
                        "Properties": {},
                    }
                }
            }
        }

        violations = find_regional_violations(templates, ["SpaceportPreviewABCDEF1234Stack"])

        self.assertEqual(
            violations,
            ["SpaceportPreviewABCDEF1234Stack:PreviewApi -> <default EDGE>"],
        )

    def test_find_regional_violations_accepts_regional_endpoints(self):
        templates = {
            "SpaceportPreviewABCDEF1234Stack": {
                "Resources": {
                    "PreviewApi": {
                        "Type": "AWS::ApiGateway::RestApi",
                        "Properties": {
                            "EndpointConfiguration": {"Types": ["REGIONAL"]},
                        },
                    }
                }
            }
        }

        self.assertEqual(
            find_regional_violations(templates, ["SpaceportPreviewABCDEF1234Stack"]),
            [],
        )

    def test_resolve_required_regional_stacks_for_preview_without_auth(self):
        required = resolve_required_regional_stacks(
            "agent-26033012-edge-api-quota-remediation",
            deploy_auth_stack=False,
        )

        self.assertEqual(len(required), 2)
        self.assertTrue(any(name.startswith("SpaceportPreview") for name in required))
        self.assertTrue(any(name.startswith("SpaceportMLPreview") for name in required))

    def test_resolve_required_regional_stacks_for_shared_staging_auth(self):
        required = resolve_required_regional_stacks("development", deploy_auth_stack=True)

        self.assertEqual(required, ["SpaceportAuthStagingStack"])

    def test_load_templates_reads_stack_template_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            template_path = directory / "SpaceportPreviewABCDEF1234Stack.template.json"
            template_path.write_text(
                json.dumps({"Resources": {"PreviewApi": {"Type": "AWS::ApiGateway::RestApi"}}}),
                encoding="utf-8",
            )

            templates = load_templates(directory, ["SpaceportPreviewABCDEF1234Stack"])

        self.assertIn("SpaceportPreviewABCDEF1234Stack", templates)


if __name__ == "__main__":
    unittest.main()
