import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "enforce_md1_leaf_submit_readiness.py"
SPEC = importlib.util.spec_from_file_location("enforce_md1_leaf_submit_readiness_test_module", MODULE_PATH)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(gate)


def strategy() -> dict:
    return {
        "selected_tile_ids": ["tile_04", "tile_10"],
        "submitted_jobs": [],
        "v18_review_manifest_s3_uri": "s3://bucket/v18-review",
        "cost_estimate": {"estimated_usd": 3.333},
        "post_leaf_preflight_gates": [
            {"tile_id": "tile_04"},
            {"tile_id": "tile_10"},
        ],
        "stages": [
            {
                "tile_id": "tile_04",
                "environment": {
                    "TARGETED_QUALITY_BLOCKERS": "boundary_no_required_improvement",
                    "BOUNDARY_CONTEXT_TILE_IDS": "tile_13",
                },
            },
            {
                "tile_id": "tile_10",
                "environment": {
                    "TARGETED_QUALITY_BLOCKERS": "boundary_no_required_improvement",
                    "BOUNDARY_CONTEXT_TILE_IDS": "tile_13",
                },
            },
        ],
    }


def allowed_summary(**overrides) -> dict:
    params = {
        "strategy": strategy(),
        "quality_gate": {"decision": "paid_retry_allowed"},
        "merge_review_gate": {
            "decision": "merge_review_blocked",
            "block_reasons": [
                "leaf_gate_summary_missing:tile_04",
                "leaf_gate_summary_missing:tile_10",
            ],
        },
        "required_tile_ids": ["tile_04", "tile_10"],
        "required_context_tile_ids": ["tile_13"],
        "required_targeted_blockers": ["boundary_no_required_improvement"],
        "exact_head": "abc123",
        "git_head": "abc123",
        "workflow_conclusion": "success",
        "v18_review_manifest_s3_uri": "s3://bucket/v18-review",
        "training_jobs_in_progress": [],
        "processing_jobs_in_progress": [],
        "max_estimated_usd": 4.0,
        "prior_leaf_gates": [],
    }
    params.update(overrides)
    return gate.evaluate_gate(**params)


def allowed_leaf(tile_id: str) -> dict:
    return {
        "tile_id": tile_id,
        "expected_tile_id": tile_id,
        "decision": "merge_review_allowed",
        "block_reasons": [],
    }


class EnforceMd1LeafSubmitReadinessTests(unittest.TestCase):
    def test_allows_exact_head_green_idle_leaf_only_scope(self):
        summary = allowed_summary()

        self.assertEqual(summary["decision"], "leaf_submit_allowed")
        self.assertEqual(summary["block_reasons"], [])

    def test_allows_nested_candidate_objective_gate_decision(self):
        summary = allowed_summary(
            quality_gate={
                "candidate_objective_gate": {
                    "decision": "paid_retry_allowed",
                }
            }
        )

        self.assertEqual(summary["decision"], "leaf_submit_allowed")
        self.assertEqual(summary["quality_strategy_decision"], "paid_retry_allowed")

    def test_blocks_when_live_training_job_exists(self):
        summary = allowed_summary(training_jobs_in_progress=["active-job"])

        self.assertEqual(summary["decision"], "leaf_submit_blocked")
        self.assertIn("training_jobs_in_progress", summary["block_reasons"])

    def test_blocks_when_quality_gate_is_not_allowed(self):
        summary = allowed_summary(quality_gate={"decision": "paid_retry_blocked"})

        self.assertEqual(summary["decision"], "leaf_submit_blocked")
        self.assertIn("quality_strategy_gate_not_allowed", summary["block_reasons"])

    def test_blocks_when_merge_review_gate_is_already_allowed(self):
        summary = allowed_summary(merge_review_gate={"decision": "merge_review_allowed", "block_reasons": []})

        self.assertEqual(summary["decision"], "leaf_submit_blocked")
        self.assertIn("merge_review_gate_not_blocked_only_on_leaf_summaries", summary["block_reasons"])

    def test_blocks_full_14tile_scope(self):
        candidate = strategy()
        candidate["selected_tile_ids"] = [f"tile_{index:02d}" for index in range(14)]
        summary = allowed_summary(strategy=candidate)

        self.assertEqual(summary["decision"], "leaf_submit_blocked")
        self.assertIn("full_14tile_scope_not_allowed", summary["block_reasons"])

    def test_blocks_missing_v18_review_manifest(self):
        candidate = strategy()
        candidate["v18_review_manifest_s3_uri"] = ""
        summary = allowed_summary(strategy=candidate, v18_review_manifest_s3_uri="")

        self.assertEqual(summary["decision"], "leaf_submit_blocked")
        self.assertIn("v18_review_manifest_missing", summary["block_reasons"])

    def test_blocks_mismatched_v18_review_manifest(self):
        summary = allowed_summary(v18_review_manifest_s3_uri="s3://bucket/other-v18-review")

        self.assertEqual(summary["decision"], "leaf_submit_blocked")
        self.assertIn("strategy_v18_review_manifest_mismatch", summary["block_reasons"])

    def test_reads_generic_context_support_from_stage_environment(self):
        candidate = strategy()
        for stage in candidate["stages"]:
            stage["environment"].pop("BOUNDARY_CONTEXT_TILE_IDS")
            stage["environment"]["CONTEXT_SUPPORT_TILE_IDS"] = "tile_13,tile_01"
        summary = allowed_summary(
            strategy=candidate,
            required_context_tile_ids=["tile_13", "tile_01"],
        )

        self.assertEqual(summary["decision"], "leaf_submit_allowed")
        self.assertEqual(summary["block_reasons"], [])

    def test_allows_subset_retry_when_prior_leaf_gate_passed(self):
        candidate = strategy()
        candidate["selected_tile_ids"] = ["tile_10"]
        candidate["post_leaf_preflight_gates"] = [{"tile_id": "tile_10"}]
        candidate["stages"] = [candidate["stages"][1]]
        summary = allowed_summary(
            strategy=candidate,
            merge_review_gate={
                "decision": "merge_review_blocked",
                "block_reasons": ["leaf_gate_summary_missing:tile_10"],
            },
            prior_leaf_gates=[allowed_leaf("tile_04")],
            max_estimated_usd=4.0,
        )

        self.assertEqual(summary["decision"], "leaf_submit_allowed")
        self.assertEqual(summary["block_reasons"], [])
        self.assertEqual(summary["passing_prior_leaf_tile_ids"], ["tile_04"])

    def test_blocks_subset_retry_without_prior_leaf_gate(self):
        candidate = strategy()
        candidate["selected_tile_ids"] = ["tile_10"]
        candidate["post_leaf_preflight_gates"] = [{"tile_id": "tile_10"}]
        candidate["stages"] = [candidate["stages"][1]]
        summary = allowed_summary(
            strategy=candidate,
            merge_review_gate={
                "decision": "merge_review_blocked",
                "block_reasons": ["leaf_gate_summary_missing:tile_10"],
            },
        )

        self.assertEqual(summary["decision"], "leaf_submit_blocked")
        self.assertIn("required_tile_not_selected_or_prior_passing:tile_04", summary["block_reasons"])


if __name__ == "__main__":
    unittest.main()
