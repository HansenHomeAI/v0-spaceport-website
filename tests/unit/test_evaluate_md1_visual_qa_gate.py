import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "evaluate_md1_visual_qa_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("evaluate_md1_visual_qa_gate_test_module", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def make_manifest() -> dict:
    return {
        "view_count": 1,
        "panel_count": 1,
        "views": [
            {
                "bucket": "boundary",
                "image_name": "DJI_0068.JPG",
                "assets": {
                    "reference_image": {"artifact_relative_path": "quality_review/reference/boundary/DJI_0068.JPG"},
                    "merged_render": {"artifact_relative_path": "quality_review/merged/boundary/DJI_0068.png"},
                    "merged_no_background_render": {
                        "artifact_relative_path": "quality_review/merged_no_background/boundary/DJI_0068.png"
                    },
                    "diff_heatmap": {"artifact_relative_path": "quality_review/diff_heatmaps/boundary/DJI_0068.png"},
                    "side_by_side_panel": {
                        "artifact_relative_path": "quality_review/visual_panels/boundary/DJI_0068.png"
                    },
                },
            }
        ],
    }


class EvaluateMd1VisualQaGateTests(unittest.TestCase):
    def test_ready_when_assets_exist_and_ai_passes(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for view in make_manifest()["views"]:
                for asset in view["assets"].values():
                    path = root / asset["artifact_relative_path"]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"x")

            summary = module.evaluate_visual_qa_gate(
                visual_qa_manifest=make_manifest(),
                asset_root=root,
                ai_review={
                    "overall_status": "pass",
                    "blocking_defects": [],
                    "per_view_findings": [],
                    "confidence": 0.9,
                    "recommended_next_action": "continue",
                },
            )

            self.assertEqual(summary["decision"], "visual_qa_ready")
            self.assertEqual(summary["block_reasons"], [])

    def test_blocks_missing_assets_and_ai_blocking_findings(self):
        module = load_module()
        manifest = make_manifest()
        del manifest["views"][0]["assets"]["side_by_side_panel"]

        summary = module.evaluate_visual_qa_gate(
            visual_qa_manifest=manifest,
            ai_review={
                "overall_status": "block",
                "blocking_defects": ["boundary_seam"],
                "per_view_findings": [{"severity": "blocking", "image_name": "DJI_0068.JPG"}],
            },
        )

        self.assertEqual(summary["decision"], "visual_qa_blocked")
        self.assertIn("visual_qa_required_assets_missing", summary["block_reasons"])
        self.assertIn("ai_visual_review_status_block", summary["block_reasons"])
        self.assertIn("ai_visual_review_blocking_defects", summary["block_reasons"])
        self.assertIn("ai_visual_review_blocking_view_findings", summary["block_reasons"])


if __name__ == "__main__":
    unittest.main()
