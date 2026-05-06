import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "enforce_md1_merge_review_gate.py"
SPEC = importlib.util.spec_from_file_location("enforce_md1_merge_review_gate_test_module", MODULE_PATH)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(gate)


def strategy() -> dict:
    return {
        "selected_tile_ids": ["tile_04", "tile_10"],
        "submitted_jobs": [],
        "post_leaf_preflight_gates": [
            {"tile_id": "tile_04"},
            {"tile_id": "tile_10"},
        ],
        "stages": [
            {
                "environment": {
                    "TARGETED_QUALITY_BLOCKERS": "boundary_no_required_improvement",
                    "BOUNDARY_CONTEXT_TILE_IDS": "tile_13",
                }
            }
        ],
    }


def allowed_leaf(tile_id: str) -> dict:
    return {
        "tile_id": tile_id,
        "expected_tile_id": tile_id,
        "decision": "merge_review_allowed",
        "block_reasons": [],
    }


class EnforceMd1MergeReviewGateTests(unittest.TestCase):
    def test_blocks_until_all_required_leaf_gates_are_present(self):
        summary = gate.evaluate_gate(
            strategy=strategy(),
            required_tile_ids=["tile_04", "tile_10"],
            required_context_tile_ids=["tile_13"],
            required_targeted_blockers=["boundary_no_required_improvement"],
            leaf_gates=[],
        )

        self.assertEqual(summary["decision"], "merge_review_blocked")
        self.assertIn("leaf_gate_summary_missing:tile_04", summary["block_reasons"])
        self.assertIn("leaf_gate_summary_missing:tile_10", summary["block_reasons"])

    def test_allows_merge_review_when_required_leaf_gates_pass(self):
        summary = gate.evaluate_gate(
            strategy=strategy(),
            required_tile_ids=["tile_04", "tile_10"],
            required_context_tile_ids=["tile_13"],
            required_targeted_blockers=["boundary_no_required_improvement"],
            leaf_gates=[allowed_leaf("tile_04"), allowed_leaf("tile_10")],
        )

        self.assertEqual(summary["decision"], "merge_review_allowed")
        self.assertEqual(summary["block_reasons"], [])

    def test_blocks_when_boundary_context_support_is_missing(self):
        candidate = strategy()
        candidate["stages"][0]["environment"]["BOUNDARY_CONTEXT_TILE_IDS"] = ""
        summary = gate.evaluate_gate(
            strategy=candidate,
            required_tile_ids=["tile_04", "tile_10"],
            required_context_tile_ids=["tile_13"],
            required_targeted_blockers=["boundary_no_required_improvement"],
            leaf_gates=[allowed_leaf("tile_04"), allowed_leaf("tile_10")],
        )

        self.assertEqual(summary["decision"], "merge_review_blocked")
        self.assertIn("context_support_tile_missing:tile_13", summary["block_reasons"])

    def test_blocks_non_dryrun_strategy(self):
        candidate = strategy()
        candidate["submitted_jobs"] = [{"job_name": "already-spent"}]
        summary = gate.evaluate_gate(
            strategy=candidate,
            required_tile_ids=["tile_04", "tile_10"],
            required_context_tile_ids=["tile_13"],
            required_targeted_blockers=["boundary_no_required_improvement"],
            leaf_gates=[allowed_leaf("tile_04"), allowed_leaf("tile_10")],
        )

        self.assertEqual(summary["decision"], "merge_review_blocked")
        self.assertIn("strategy_has_submitted_jobs", summary["block_reasons"])


if __name__ == "__main__":
    unittest.main()
