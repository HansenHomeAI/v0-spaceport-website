import sys
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2] / "infrastructure" / "spaceport_cdk"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from spaceport_cdk.preview_sharing import (
    SHARED_PREVIEW_RESOURCE_SUFFIX,
    shared_preview_bucket_name,
    shared_preview_role_name,
    shared_preview_table_name,
    should_reuse_shared_preview_resources,
)


class PreviewSharingTests(unittest.TestCase):
    def test_branch_preview_reuses_shared_resources(self):
        self.assertTrue(should_reuse_shared_preview_resources("branch-preview"))
        self.assertFalse(should_reuse_shared_preview_resources("shared-staging"))

    def test_shared_preview_names_target_staging_foundation(self):
        self.assertEqual(SHARED_PREVIEW_RESOURCE_SUFFIX, "staging")
        self.assertEqual(shared_preview_bucket_name("spaceport-uploads"), "spaceport-uploads-staging")
        self.assertEqual(shared_preview_table_name("Spaceport-FileMetadata"), "Spaceport-FileMetadata-staging")
        self.assertEqual(shared_preview_role_name("Spaceport-Lambda-Role-"), "Spaceport-Lambda-Role-staging")


if __name__ == "__main__":
    unittest.main()
