import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "plan_md1_leaf_reuse_merge.py"
SPEC = importlib.util.spec_from_file_location("plan_md1_leaf_reuse_merge", MODULE_PATH)
planner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = planner
SPEC.loader.exec_module(planner)


def base_summary() -> dict:
    return {
        "candidate_label": "old-candidate",
        "experiment_id": "old-experiment",
        "submitted_jobs": [{"job_name": "old"}],
        "completed_jobs": [{"job_name": "old"}],
        "training_jobs_to_submit": 1,
        "cost_estimate": {"estimated_usd": 1.0, "training_stage_count": 1},
        "stages": [
            {
                "stage_name": "T0_tile_04_old",
                "stage_type": "train",
                "tile_id": "tile_04",
                "source_artifact_uri": "s3://bucket/old-tile04/model.tar.gz",
                "model_artifact_s3_uri": "s3://bucket/old-tile04/model.tar.gz",
            },
            {
                "stage_name": "T0_tile_10",
                "stage_type": "context_density_tile",
                "tile_id": "tile_10",
                "source_artifact_uri": "s3://bucket/v18/model.tar.gz",
                "model_artifact_s3_uri": "s3://bucket/v18/model.tar.gz",
            },
        ],
    }


def passed_preflight(tile_id: str = "tile_04") -> dict:
    return {
        "decision": "leaf_preflight_passed_cache_candidate",
        "block_reasons": [],
        "tile_id": tile_id,
        "artifact_uri": "s3://bucket/new-tile04/model.tar.gz",
        "splat_vertex_count": 1081440,
        "training_selection": {"selected_image_count": 188},
    }


def passed_gate(tile_id: str = "tile_04") -> dict:
    return {
        "decision": "merge_review_allowed",
        "block_reasons": [],
        "expected_tile_id": tile_id,
        "splat_reference_guard": {
            "reference_splat_count": 956277,
            "observed_reference_ratio": 1.13,
        },
    }


class MD1LeafReuseMergeTests(unittest.TestCase):
    def test_replaces_passed_leaf_artifact_and_zeros_training_spend(self):
        leaf = planner.validate_passed_leaf(
            preflight=passed_preflight(),
            gate=passed_gate(),
            preflight_json="leaf-preflight.json",
            gate_json="leaf-gate.json",
        )

        summary = planner.build_leaf_reuse_summary(
            base_summary=base_summary(),
            base_summary_json="base.json",
            passed_leaves=[leaf],
            candidate_label="new-leaf-reuse",
            experiment_id="new-experiment",
        )

        tile04 = next(stage for stage in summary["stages"] if stage["tile_id"] == "tile_04")
        tile10 = next(stage for stage in summary["stages"] if stage["tile_id"] == "tile_10")

        self.assertEqual(summary["candidate_label"], "new-leaf-reuse")
        self.assertEqual(summary["training_jobs_to_submit"], 0)
        self.assertEqual(summary["submitted_jobs"], [])
        self.assertEqual(summary["completed_jobs"], [])
        self.assertEqual(tile04["source_artifact_uri"], "s3://bucket/new-tile04/model.tar.gz")
        self.assertEqual(tile04["stage_type"], "train")
        self.assertEqual(tile04["cache_status"], "validated_leaf_reuse")
        self.assertEqual(tile04["quality_gate_status"], "leaf_gate_passed_merge_review_allowed")
        self.assertEqual(tile04["splat_vertex_count"], 1081440)
        self.assertEqual(tile10["source_artifact_uri"], "s3://bucket/v18/model.tar.gz")
        self.assertEqual(summary["leaf_reuse_merge"]["replaced_tile_ids"], ["tile_04"])
        self.assertEqual(summary["post_leaf_preflight_gates"][0]["tile_id"], "tile_04")
        self.assertEqual(summary["post_leaf_preflight_gates"][0]["gate_summary_json"], "leaf-gate.json")

    def test_records_current_objective_context_for_merge_review_gate(self):
        leaf = planner.validate_passed_leaf(
            preflight=passed_preflight(),
            gate=passed_gate(),
            preflight_json="leaf-preflight.json",
            gate_json="leaf-gate.json",
        )

        summary = planner.build_leaf_reuse_summary(
            base_summary=base_summary(),
            base_summary_json="base.json",
            passed_leaves=[leaf],
            candidate_label="new-leaf-reuse",
            experiment_id="new-experiment",
            targeted_quality_blockers=["boundary_no_required_improvement", "horizon_psnr_regression"],
            context_tile_ids=["tile_10"],
        )

        self.assertEqual(
            summary["targeted_quality_blockers"],
            ["boundary_no_required_improvement", "horizon_psnr_regression"],
        )
        self.assertEqual(summary["context_support_tile_ids"], ["tile_10"])
        self.assertEqual(summary["reuse_context_tile_ids"], ["tile_10"])
        self.assertEqual(
            summary["leaf_reuse_merge"]["targeted_quality_blockers"],
            ["boundary_no_required_improvement", "horizon_psnr_regression"],
        )
        self.assertEqual(summary["leaf_reuse_merge"]["context_tile_ids"], ["tile_10"])

    def test_rejects_nonpassing_leaf_gate(self):
        with self.assertRaisesRegex(ValueError, "leaf_gate_not_merge_review_allowed"):
            planner.validate_passed_leaf(
                preflight=passed_preflight(),
                gate={"decision": "merge_review_blocked", "block_reasons": []},
                preflight_json="leaf-preflight.json",
                gate_json="leaf-gate.json",
            )

    def test_rejects_mismatched_leaf_tile_ids(self):
        with self.assertRaisesRegex(ValueError, "leaf_tile_id_mismatch"):
            planner.validate_passed_leaf(
                preflight=passed_preflight("tile_04"),
                gate=passed_gate("tile_10"),
                preflight_json="leaf-preflight.json",
                gate_json="leaf-gate.json",
            )

    def test_rejects_leaf_missing_from_base_summary(self):
        leaf = planner.validate_passed_leaf(
            preflight=passed_preflight("tile_09"),
            gate=passed_gate("tile_09"),
            preflight_json="leaf-preflight.json",
            gate_json="leaf-gate.json",
        )

        with self.assertRaisesRegex(ValueError, "leaf tiles missing"):
            planner.build_leaf_reuse_summary(
                base_summary=base_summary(),
                base_summary_json="base.json",
                passed_leaves=[leaf],
                candidate_label="new-leaf-reuse",
                experiment_id="new-experiment",
            )


if __name__ == "__main__":
    unittest.main()
