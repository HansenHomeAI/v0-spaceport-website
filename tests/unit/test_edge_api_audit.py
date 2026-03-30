import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.audit_edge_api_usage import (
    PreviewStackRecord,
    RestApiRecord,
    classify_rest_api,
    stale_preview_branch_ids,
    summarize,
)


class EdgeApiAuditTests(unittest.TestCase):
    def test_classify_rest_api_marks_preview_branch_resources(self):
        category, branch_id = classify_rest_api("spaceport-file-upload-api-br-45ee130fef")

        self.assertEqual(category, "preview")
        self.assertEqual(branch_id, "45ee130fef")

    def test_classify_rest_api_marks_shared_auth_resources(self):
        category, branch_id = classify_rest_api("Spaceport-ProjectsApi-staging")

        self.assertEqual(category, "shared-auth")
        self.assertIsNone(branch_id)

    def test_stale_preview_branch_ids_compare_against_active_remotes(self):
        rest_apis = [
            RestApiRecord("api-1", "spaceport-file-upload-api-br-45ee130fef", "EDGE", "preview", "45ee130fef"),
            RestApiRecord("api-2", "spaceport-file-upload-api-br-ac4b75bc57", "REGIONAL", "preview", "ac4b75bc57"),
        ]
        preview_stacks = [
            PreviewStackRecord("SpaceportPreview45EE130FEFStack", "CREATE_COMPLETE", "45ee130fef"),
            PreviewStackRecord("SpaceportPreviewAC4B75BC57Stack", "UPDATE_COMPLETE", "ac4b75bc57"),
        ]

        stale = stale_preview_branch_ids(rest_apis, preview_stacks, {"ac4b75bc57"})

        self.assertEqual(stale, ["45ee130fef"])

    def test_summarize_reports_edge_and_regional_counts(self):
        rest_apis = [
            RestApiRecord("api-1", "spaceport-file-upload-api-br-45ee130fef", "EDGE", "preview", "45ee130fef"),
            RestApiRecord("api-2", "spaceport-feedback-api-br-ac4b75bc57", "REGIONAL", "preview", "ac4b75bc57"),
            RestApiRecord("api-3", "Spaceport-ProjectsApi-staging", "REGIONAL", "shared-auth", None),
        ]

        summary = summarize(rest_apis, ["45ee130fef"])

        self.assertEqual(summary["edge_total"], 1)
        self.assertEqual(summary["regional_total"], 2)
        self.assertEqual(summary["preview_edge_total"], 1)
        self.assertEqual(summary["shared_auth_regional_total"], 1)
        self.assertEqual(summary["stale_preview_branch_ids"], ["45ee130fef"])


if __name__ == "__main__":
    unittest.main()
