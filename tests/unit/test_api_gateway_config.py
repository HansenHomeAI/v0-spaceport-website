import sys
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2] / "infrastructure" / "spaceport_cdk"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from spaceport_cdk.api_gateway_config import resolve_auth_api_endpoint_type


class ApiGatewayConfigTests(unittest.TestCase):
    def test_production_auth_keeps_default_endpoint_type(self):
        self.assertIsNone(resolve_auth_api_endpoint_type("production"))

    def test_shared_staging_auth_uses_regional_endpoints(self):
        self.assertEqual(resolve_auth_api_endpoint_type("shared-staging"), "REGIONAL")

    def test_branch_preview_auth_uses_regional_endpoints(self):
        self.assertEqual(resolve_auth_api_endpoint_type("branch-preview"), "REGIONAL")


if __name__ == "__main__":
    unittest.main()
