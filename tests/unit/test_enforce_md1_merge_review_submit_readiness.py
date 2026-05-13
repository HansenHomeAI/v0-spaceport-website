import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "enforce_md1_merge_review_submit_readiness.py"
SPEC = importlib.util.spec_from_file_location("enforce_md1_merge_review_submit_readiness_test_module", MODULE_PATH)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(gate)


def leaf_reuse_summary() -> dict:
    return {
        "selected_tile_ids": ["tile_04", "tile_10"],
        "submitted_jobs": [],
        "training_jobs_to_submit": 0,
        "stages": [
            {"tile_id": "tile_04", "source_artifact_uri": "s3://bucket/tile04/model.tar.gz"},
            {"tile_id": "tile_10", "source_artifact_uri": "s3://bucket/tile10/model.tar.gz"},
        ],
    }


def merge_plan() -> dict:
    return {
        "selected_tile_ids": ["tile_04", "tile_10"],
        "artifact_inputs": [
            {"artifact_input_name": "artifact-00", "artifact_uri": "s3://bucket/tile04/model.tar.gz"},
            {"artifact_input_name": "artifact-01", "artifact_uri": "s3://bucket/tile10/model.tar.gz"},
        ],
        "tiles": [
            {"tile_id": "tile_04", "artifact_input_name": "artifact-00"},
            {"tile_id": "tile_10", "artifact_input_name": "artifact-01"},
        ],
    }


def payload() -> dict:
    return {
        "ProcessingInputs": [
            {"InputName": "merge-plan"},
            {"InputName": "tile-selection"},
            {"InputName": "artifact-00"},
            {"InputName": "artifact-01"},
        ],
        "StoppingCondition": {"MaxRuntimeInSeconds": 3600},
    }


def readiness_plan() -> dict:
    return {
        "merge_plan": {
            "required": True,
            "no_training": True,
            "max_estimated_usd": 0.5,
            "max_runtime_seconds": 3600,
        },
        "review_plan": {
            "required": True,
            "v18_non_regression_required": True,
            "v18_review_manifest_s3_uri": "s3://bucket/v18-review",
            "candidate_model_artifact_s3_uri": "s3://bucket/merged/model.tar.gz",
            "max_estimated_usd": 0.5,
            "max_runtime_seconds": 1800,
        },
        "visual_qa_plan": {
            "required": True,
            "extract_only_visual_assets": True,
            "evaluate_gate_required": True,
            "ai_assisted_review_manifest_required": True,
        },
        "viewer_smoke_plan": {
            "required": True,
            "post_review_or_compressed_artifact_required": True,
            "no_local_model_weight_bloat": True,
            "checks": ["nonblank_canvas", "camera_navigation", "serious_console_errors"],
        },
        "input_materialization": {
            "required": True,
            "merge_plan_uploaded": True,
            "tile_manifest_available": True,
            "view_buckets_available": True,
            "artifact_inputs_available": True,
        },
    }


def allowed_summary(**overrides) -> dict:
    params = {
        "leaf_reuse_summary": leaf_reuse_summary(),
        "merge_plan": merge_plan(),
        "payload": payload(),
        "merge_review_gate": {"decision": "merge_review_allowed", "block_reasons": []},
        "readiness_plan": readiness_plan(),
        "required_tile_ids": ["tile_04", "tile_10"],
        "exact_head": "abc123",
        "git_head": "abc123",
        "workflow_conclusion": "success",
        "training_jobs_in_progress": [],
        "processing_jobs_in_progress": [],
        "max_merge_estimated_usd": 0.5,
        "max_merge_runtime_seconds": 3600,
        "max_review_estimated_usd": 0.5,
        "max_review_runtime_seconds": 1800,
    }
    params.update(overrides)
    return gate.evaluate_gate(**params)


class EnforceMd1MergeReviewSubmitReadinessTests(unittest.TestCase):
    def test_allows_exact_head_idle_merge_review_with_quality_plans(self):
        summary = allowed_summary()

        self.assertEqual(summary["decision"], "merge_review_submit_allowed")
        self.assertEqual(summary["block_reasons"], [])

    def test_blocks_active_processing_job(self):
        summary = allowed_summary(processing_jobs_in_progress=["active-processing"])

        self.assertEqual(summary["decision"], "merge_review_submit_blocked")
        self.assertIn("processing_jobs_in_progress", summary["block_reasons"])

    def test_blocks_training_scope(self):
        summary_payload = leaf_reuse_summary()
        summary_payload["training_jobs_to_submit"] = 1
        summary = allowed_summary(leaf_reuse_summary=summary_payload)

        self.assertEqual(summary["decision"], "merge_review_submit_blocked")
        self.assertIn("leaf_reuse_summary_has_training_jobs_to_submit", summary["block_reasons"])

    def test_blocks_missing_visual_qa_plan(self):
        plan = readiness_plan()
        plan["visual_qa_plan"]["ai_assisted_review_manifest_required"] = False
        summary = allowed_summary(readiness_plan=plan)

        self.assertEqual(summary["decision"], "merge_review_submit_blocked")
        self.assertIn("visual_qa_plan_missing", summary["block_reasons"])

    def test_blocks_payload_runtime_above_cap(self):
        processing_payload = payload()
        processing_payload["StoppingCondition"]["MaxRuntimeInSeconds"] = 7200
        summary = allowed_summary(payload=processing_payload)

        self.assertEqual(summary["decision"], "merge_review_submit_blocked")
        self.assertIn("payload_runtime_above_cap", summary["block_reasons"])

    def test_blocks_unsupported_merge_environment(self):
        processing_payload = payload()
        processing_payload["Environment"] = {"MERGE_PROTECTED_OVERLAP_MODE": "boundary"}
        summary = allowed_summary(payload=processing_payload)

        self.assertEqual(summary["decision"], "merge_review_submit_blocked")
        self.assertIn("payload_unsupported_merge_environment", summary["block_reasons"])

    def test_blocks_missing_materialized_inputs(self):
        plan = readiness_plan()
        plan["input_materialization"]["tile_manifest_available"] = False
        summary = allowed_summary(readiness_plan=plan)

        self.assertEqual(summary["decision"], "merge_review_submit_blocked")
        self.assertIn("merge_inputs_not_materialized", summary["block_reasons"])


if __name__ == "__main__":
    unittest.main()
