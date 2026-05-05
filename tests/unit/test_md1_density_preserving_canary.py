import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "plan_md1_density_preserving_canary.py"
SPEC = importlib.util.spec_from_file_location("plan_md1_density_preserving_canary", MODULE_PATH)
planner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = planner
SPEC.loader.exec_module(planner)


class MD1DensityPreservingCanaryTests(unittest.TestCase):
    def test_build_plan_uses_v18_rollback_for_under_dense_candidate(self):
        reference = {
            "tiles": [
                {"tile_id": "tile_00", "retained_gaussians": 1000},
                {"tile_id": "tile_01", "retained_gaussians": 2000},
            ]
        }
        candidate = {
            "merge_report": {
                "tiles": [
                    {"tile_id": "tile_00", "retained_gaussians": 970},
                    {"tile_id": "tile_01", "retained_gaussians": 500},
                ]
            },
            "merge_plan": {
                "tiles": [
                    {
                        "tile_id": "tile_00",
                        "stage_type": "cached_tile",
                        "artifact_uri": "s3://bucket/t00.tar.gz",
                        "v18_non_regression_status": "passed",
                    },
                    {"tile_id": "tile_01", "stage_type": "cached_tile", "artifact_uri": "s3://bucket/t01.tar.gz"},
                ]
            },
        }
        context_manifest = {
            "context_density_tiles": [
                {
                    "tile_id": "tile_01",
                    "context_density_status": "passed",
                    "retained_gaussians": 2000,
                    "reference_retained_gaussians": 2000,
                    "artifact_s3_uri": "s3://bucket/v18.tar.gz",
                }
            ]
        }

        plan = planner.build_plan(
            reference_merge_report=reference,
            candidate_summary=candidate,
            context_density_manifest=context_manifest,
            candidate_label="cheap",
            min_retained_ratio=0.95,
            min_context_density_ratio=0.95,
        )

        by_tile = {entry["tile_id"]: entry for entry in plan["tile_plan"]}
        self.assertEqual(plan["status"], "full_scene_canary_ready_with_v18_rollback")
        self.assertEqual(by_tile["tile_00"]["selected_source"], "candidate")
        self.assertEqual(by_tile["tile_01"]["selected_source"], "context_density_rollback")
        self.assertTrue(by_tile["tile_01"]["retrain_required_if_no_v18_rollback"])
        self.assertEqual(plan["summary"]["v18_rollback_tile_ids"], ["tile_01"])
        self.assertEqual(plan["training_jobs_to_submit"], 0)

    def test_build_plan_blocks_when_dense_fallback_missing(self):
        reference = {"tiles": [{"tile_id": "tile_00", "retained_gaussians": 1000}]}
        candidate = {"merge_report": {"tiles": [{"tile_id": "tile_00", "retained_gaussians": 100}]}}

        plan = planner.build_plan(
            reference_merge_report=reference,
            candidate_summary=candidate,
            context_density_manifest={"context_density_tiles": []},
            candidate_label="cheap",
            min_retained_ratio=0.95,
            min_context_density_ratio=0.95,
        )

        self.assertEqual(plan["status"], "blocked_missing_dense_fallback")
        self.assertFalse(plan["canary_submit_allowed"])
        self.assertEqual(plan["summary"]["retrain_required_tile_ids"], ["tile_00"])

    def test_cached_tile_without_quality_proof_falls_back_even_when_dense(self):
        reference = {"tiles": [{"tile_id": "tile_10", "retained_gaussians": 1000}]}
        candidate = {
            "merge_report": {"tiles": [{"tile_id": "tile_10", "retained_gaussians": 990}]},
            "merge_plan": {
                "tiles": [
                    {"tile_id": "tile_10", "stage_type": "cached_tile", "artifact_uri": "s3://bucket/tile10.tar.gz"}
                ]
            },
        }
        context_manifest = {
            "context_density_tiles": [
                {
                    "tile_id": "tile_10",
                    "context_density_status": "passed",
                    "retained_gaussians": 1000,
                    "reference_retained_gaussians": 1000,
                    "artifact_s3_uri": "s3://bucket/v18.tar.gz",
                }
            ]
        }

        plan = planner.build_plan(
            reference_merge_report=reference,
            candidate_summary=candidate,
            context_density_manifest=context_manifest,
            candidate_label="cheap",
            min_retained_ratio=0.95,
            min_context_density_ratio=0.95,
        )

        tile = plan["tile_plan"][0]
        self.assertEqual(tile["candidate_status"], "quality_unproven")
        self.assertEqual(tile["selected_source"], "context_density_rollback")
        self.assertIn("candidate_quality_status_not_passing", tile["reasons"])
        self.assertEqual(plan["summary"]["v18_rollback_tile_ids"], ["tile_10"])

    def test_build_benchmark_summary_from_plan_emits_mergeable_stages(self):
        plan = {
            "generated_at": "2026-05-05T18:25:19Z",
            "candidate_label": "cheap",
            "status": "full_scene_canary_ready_with_v18_rollback",
            "summary": {"v18_rollback_tile_ids": ["tile_01"]},
            "decision": {"production_quality_status": "not_new"},
            "tile_plan": [
                {
                    "tile_id": "tile_00",
                    "selected_stage_type": "cached_tile",
                    "selected_source": "candidate",
                    "selected_artifact_uri": "s3://bucket/tile00/model.tar.gz",
                    "candidate_status": "density_pass",
                    "candidate_quality_status": "passed",
                    "candidate_retained_ratio": 1.0,
                    "context_density_ratio": None,
                    "reference_retained_gaussians": 10,
                    "candidate_retained_gaussians": 10,
                },
                {
                    "tile_id": "tile_01",
                    "selected_stage_type": "context_density_tile",
                    "selected_source": "context_density_rollback",
                    "selected_artifact_uri": "s3://bucket/v18/model.tar.gz",
                    "candidate_status": "density_fail",
                    "candidate_quality_status": None,
                    "candidate_retained_ratio": 0.2,
                    "context_density_ratio": 1.0,
                    "reference_retained_gaussians": 20,
                    "candidate_retained_gaussians": 4,
                },
            ],
        }

        summary = planner.build_benchmark_summary_from_plan(
            plan=plan,
            base_summary={"branch": "agent", "image_uri": "image", "merge_mode": "support_weighted_overlap"},
            experiment_id="proof",
        )

        self.assertEqual(summary["experiment_id"], "proof")
        self.assertEqual(summary["selected_tile_ids"], ["tile_00", "tile_01"])
        self.assertEqual(summary["training_jobs_to_submit"], 0)
        self.assertEqual(summary["stages"][0]["stage_type"], "cached_tile")
        self.assertEqual(summary["stages"][0]["cache_status"], "hit")
        self.assertEqual(summary["stages"][1]["stage_type"], "context_density_tile")
        self.assertEqual(summary["stages"][1]["cache_status"], "context_density_hit")
        self.assertEqual(summary["stages"][1]["source_artifact_uri"], "s3://bucket/v18/model.tar.gz")


if __name__ == "__main__":
    unittest.main()
