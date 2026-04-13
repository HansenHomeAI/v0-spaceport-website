import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.resolve_auth_deploy_mode import AUTH_MARKER_RELATIVE_PATH, resolve_auth_deploy_mode


class ResolveAuthDeployModeTests(unittest.TestCase):
    def test_main_always_deploys_auth(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = resolve_auth_deploy_mode("main", Path(tmp))

        self.assertEqual(result["auth_deploy_reason"], "default-production")
        self.assertEqual(result["deploy_auth_stack_effective"], "true")
        self.assertEqual(result["auth_opt_in"], "false")
        self.assertEqual(result["auth_marker_exists"], "false")

    def test_development_always_deploys_auth(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = resolve_auth_deploy_mode("development", Path(tmp))

        self.assertEqual(result["auth_deploy_reason"], "default-development")
        self.assertEqual(result["deploy_auth_stack_effective"], "true")
        self.assertEqual(result["auth_opt_in"], "false")
        self.assertEqual(result["auth_marker_exists"], "false")

    def test_preview_branch_without_marker_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = resolve_auth_deploy_mode("agent-59318427-preview-auth-opt-in", Path(tmp))

        self.assertEqual(result["auth_deploy_reason"], "preview-read-only")
        self.assertEqual(result["deploy_auth_stack_effective"], "false")
        self.assertEqual(result["auth_opt_in"], "false")
        self.assertEqual(result["auth_marker_exists"], "false")

    def test_preview_branch_with_marker_opt_in_deploys_auth(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            marker_path = repo_root / AUTH_MARKER_RELATIVE_PATH
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            marker_path.write_text("enabled\n", encoding="utf-8")

            result = resolve_auth_deploy_mode("agent-59318427-preview-auth-opt-in", repo_root)

        self.assertEqual(result["auth_deploy_reason"], "preview-opt-in")
        self.assertEqual(result["deploy_auth_stack_effective"], "true")
        self.assertEqual(result["auth_opt_in"], "true")
        self.assertEqual(result["auth_marker_exists"], "true")


if __name__ == "__main__":
    unittest.main()
