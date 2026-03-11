import sys
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2] / "infrastructure" / "spaceport_cdk"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from spaceport_cdk.deployment_context import build_env_config, resolve_deployment_context


class DeploymentContextTests(unittest.TestCase):
    def test_main_resolves_production_context(self):
        context = resolve_deployment_context("main")

        self.assertEqual(context.deployment_class, "production")
        self.assertEqual(context.resource_suffix, "prod")
        self.assertEqual(context.spaceport_stack_name, "SpaceportProductionStack")
        self.assertEqual(context.ml_stack_name, "SpaceportMLPipelineProductionStack")
        self.assertEqual(context.auth_stack_name, "SpaceportAuthProductionStack")
        self.assertTrue(context.deploy_auth_stack)

    def test_development_resolves_shared_staging_context(self):
        context = resolve_deployment_context("development")

        self.assertEqual(context.deployment_class, "shared-staging")
        self.assertEqual(context.resource_suffix, "staging")
        self.assertEqual(context.spaceport_stack_name, "SpaceportStagingStack")
        self.assertEqual(context.ml_stack_name, "SpaceportMLPipelineStagingStack")
        self.assertEqual(context.auth_stack_name, "SpaceportAuthStagingStack")
        self.assertTrue(context.allow_fallback_imports)
        self.assertFalse(context.reuse_shared_ecr)

    def test_feature_branch_resolves_deterministic_branch_preview_context(self):
        branch_name = "codex/agent-26030402-preview-backend-isolation"

        first = resolve_deployment_context(branch_name)
        second = resolve_deployment_context(branch_name)

        self.assertEqual(first.branch_id, second.branch_id)
        self.assertRegex(first.branch_id, r"^[0-9a-f]{10}$")
        self.assertEqual(first.resource_suffix, f"br-{first.branch_id}")
        self.assertEqual(first.deployment_class, "branch-preview")
        self.assertEqual(first.auth_stack_name, "SpaceportAuthStagingStack")
        self.assertFalse(first.deploy_auth_stack)
        self.assertFalse(first.allow_fallback_imports)
        self.assertTrue(first.reuse_shared_auth)
        self.assertTrue(first.reuse_shared_ecr)
        self.assertEqual(first.spaceport_stack_name, f"SpaceportPreview{first.branch_id.upper()}Stack")
        self.assertEqual(first.ml_stack_name, f"SpaceportMLPreview{first.branch_id.upper()}Stack")

    def test_different_branch_names_get_different_branch_ids(self):
        first = resolve_deployment_context("codex/agent-26030402-preview-backend-isolation")
        second = resolve_deployment_context("codex/agent-26030403-something-else")

        self.assertNotEqual(first.branch_id, second.branch_id)

    def test_build_env_config_merges_resolved_context(self):
        base_env_config = {
            "region": "us-west-2",
            "domain": "staging.spcprt.com",
            "resourceSuffix": "staging",
        }
        context = resolve_deployment_context("codex/agent-26030402-preview-backend-isolation")

        env_config = build_env_config(base_env_config, context)

        self.assertEqual(env_config["resourceSuffix"], context.resource_suffix)
        self.assertEqual(env_config["deploymentClass"], "branch-preview")
        self.assertEqual(env_config["branchName"], context.branch_name)
        self.assertEqual(env_config["branchId"], context.branch_id)
        self.assertEqual(env_config["spaceportStackName"], context.spaceport_stack_name)
        self.assertEqual(env_config["mlStackName"], context.ml_stack_name)
        self.assertEqual(env_config["sharedAuthStackName"], "SpaceportAuthStagingStack")


if __name__ == "__main__":
    unittest.main()
