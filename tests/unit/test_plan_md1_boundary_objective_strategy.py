import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "plan_md1_boundary_objective_strategy.py"
SPEC = importlib.util.spec_from_file_location("plan_md1_boundary_objective_strategy_test_module", MODULE_PATH)
planner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(planner)


def quality_strategy() -> dict:
    return {
        "current_quality_blockers": ["boundary_no_required_improvement"],
        "boundary_improvement_gap": {
            "actual_delta": {"psnr": 0.13, "ssim": 0.005, "lpips": -0.002},
            "required_improvement": {"psnr": 0.5, "ssim": 0.01, "lpips": -0.025},
            "remaining_gap": {"psnr": 0.37, "ssim": 0.005, "lpips": 0.023},
        },
    }


def responsible_tiles() -> dict:
    return {
        "current_quality_blockers": ["boundary_no_required_improvement"],
        "boundary_frozen_cameras": ["DJI_0067.JPG", "DJI_0068.JPG", "DJI_0069.JPG", "DJI_0070.JPG"],
        "horizon_frozen_cameras": ["DJI_0066.JPG", "DJI_0073.JPG"],
        "primary_responsible_tile_ids": ["tile_04", "tile_10"],
        "horizon_primary_responsible_tile_ids": ["tile_01", "tile_04"],
        "combined_support_tile_ids": ["tile_04", "tile_10", "tile_13", "tile_00", "tile_01"],
    }


def attribution() -> dict:
    return {
        "block_reasons": {"protected": ["boundary_no_required_improvement"]},
        "density_v2_minus_baseline_bucket_delta": {
            "boundary": {"psnr": -0.015, "ssim": -0.0012, "lpips": 0.0019}
        },
        "protected_minus_baseline_merge_delta": {"retained_gaussians": 18104},
        "protected_minus_baseline_bucket_delta": {
            "boundary": {"psnr": 0, "ssim": 0, "lpips": 0}
        },
        "v18_non_regression_status": {
            "protected": "blocked",
            "protected_block_reasons": ["horizon_v18_median_ssim_regression"],
        },
    }


def overdense_leaf_attribution() -> dict:
    attr = attribution()
    attr.update(
        {
            "leaf_gate_block_reasons": [
                "leaf_preflight_decision_not_pass",
                "splat_vertex_count_above_reference_ratio",
                "splat_vertex_count_above_hard_max",
            ],
            "splat_vertex_count": 1_967_919,
            "reference_splat_count": 956_277,
            "observed_reference_ratio": 2.0579,
        }
    )
    return attr


def valid_candidate() -> dict:
    return {
        "targeted_quality_blockers": ["boundary_no_required_improvement"],
        "selected_tile_ids": ["tile_04"],
        "context_support_tile_ids": ["tile_10", "tile_13", "tile_01"],
        "boundary_camera_ids": ["DJI_0067.JPG", "DJI_0068.JPG", "DJI_0069.JPG", "DJI_0070.JPG"],
        "horizon_camera_ids": ["DJI_0066.JPG", "DJI_0073.JPG"],
        "expected_metric_axes": ["boundary.required_improvement", "boundary.psnr", "boundary.ssim"],
        "objective_changes": ["boundary_camera_weighting", "boundary_loss_weighting"],
        "objective_implementation": {
            "source_file": "infrastructure/containers/3dgs/train_nerfstudio_production.py",
            "training_config": {"ssim_lambda": 0.35},
            "environment": {"SSIM_LAMBDA": "0.35"},
        },
        "planned_cost_estimate": {"estimated_usd": 1.5},
        "submitted_jobs": [],
        "no_full_14tile_training": True,
    }


class PlanMd1BoundaryObjectiveStrategyTests(unittest.TestCase):
    def test_blocks_without_candidate_objective(self):
        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=attribution(),
            candidate_objective=None,
            max_estimated_usd=2.0,
        )

        self.assertEqual(report["recommendation"], "no_paid_retry_until_objective_redesign")
        self.assertFalse(report["paid_retry_allowed"])
        self.assertEqual(report["candidate_objective_gate"]["block_reasons"], ["candidate_objective_missing"])
        self.assertEqual(report["primary_boundary_tile_ids"], ["tile_04", "tile_10"])

    def test_records_density_and_overlap_as_failed_hypotheses(self):
        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=attribution(),
            candidate_objective=None,
            max_estimated_usd=2.0,
        )

        hypotheses = {item["hypothesis"] for item in report["failed_hypotheses"]}
        self.assertEqual(hypotheses, {"tile10_density_v2", "protected_overlap_retention"})
        overlap = next(item for item in report["failed_hypotheses"] if item["hypothesis"] == "protected_overlap_retention")
        self.assertEqual(overlap["merge_delta_vs_rollback_bg10"]["retained_gaussians"], 18104)

    def test_allows_candidate_that_targets_boundary_objective_with_context(self):
        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=attribution(),
            candidate_objective=valid_candidate(),
            max_estimated_usd=2.0,
        )

        gate = report["candidate_objective_gate"]
        self.assertEqual(gate["decision"], "paid_retry_allowed")
        self.assertEqual(gate["block_reasons"], [])
        self.assertEqual(gate["covered_tile_ids"], ["tile_01", "tile_04", "tile_10", "tile_13"])
        self.assertEqual(gate["loss_weighting_implementation"]["environment"], {"SSIM_LAMBDA": "0.35"})
        self.assertTrue(report["paid_retry_allowed"])

    def test_blocks_loss_weighting_claim_without_implemented_knob(self):
        candidate = valid_candidate()
        candidate.pop("objective_implementation")

        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=attribution(),
            candidate_objective=candidate,
            max_estimated_usd=2.0,
        )

        self.assertIn(
            "objective_missing_loss_weighting_implementation",
            report["candidate_objective_gate"]["block_reasons"],
        )
        self.assertFalse(report["paid_retry_allowed"])

    def test_blocks_density_only_candidate_even_when_tiles_and_cameras_match(self):
        candidate = valid_candidate()
        candidate["objective_changes"] = ["tile10_density_only", "protected_overlap_retention_only"]

        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=attribution(),
            candidate_objective=candidate,
            max_estimated_usd=2.0,
        )

        reasons = report["candidate_objective_gate"]["block_reasons"]
        self.assertIn("objective_lacks_camera_or_loss_weighting_change", reasons)
        self.assertIn("objective_repeats_failed_density_or_merge_only_hypothesis", reasons)
        self.assertFalse(report["paid_retry_allowed"])

    def test_records_and_blocks_frame_repeat_without_loss_weighting(self):
        attr = attribution()
        attr["camera_weighting_minus_reference_bucket_delta"] = {
            "boundary": {"psnr": -0.12, "ssim": -0.007, "lpips": -0.003},
            "horizon": {"psnr": -0.49, "ssim": 0.006, "lpips": -0.012},
        }
        candidate = valid_candidate()
        candidate["objective_changes"] = [
            "boundary_camera_weighting",
            "boundary_frame_repeat_weighting",
            "frozen_camera_weighting",
        ]

        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=attr,
            candidate_objective=candidate,
            max_estimated_usd=2.0,
        )

        hypotheses = {item["hypothesis"] for item in report["failed_hypotheses"]}
        self.assertIn("boundary_frame_repeat_weighting", hypotheses)
        reasons = report["candidate_objective_gate"]["block_reasons"]
        self.assertIn("objective_repeats_failed_frame_repeat_without_loss_weighting", reasons)
        self.assertFalse(report["paid_retry_allowed"])

    def test_blocks_candidate_above_budget(self):
        candidate = valid_candidate()
        candidate["planned_cost_estimate"] = {"estimated_usd": 3.0}

        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=attribution(),
            candidate_objective=candidate,
            max_estimated_usd=2.0,
        )

        self.assertIn("objective_estimated_cost_above_cap", report["candidate_objective_gate"]["block_reasons"])
        self.assertFalse(report["paid_retry_allowed"])

    def test_horizon_psnr_blocker_requires_horizon_psnr_axis(self):
        qs = quality_strategy()
        qs["current_quality_blockers"] = ["boundary_no_required_improvement", "horizon_psnr_regression"]
        rt = responsible_tiles()
        rt["current_quality_blockers"] = ["boundary_no_required_improvement", "horizon_psnr_regression"]
        candidate = valid_candidate()
        candidate["expected_metric_axes"] = ["boundary.required_improvement", "boundary.psnr", "boundary.ssim"]

        report = planner.plan_boundary_objective_strategy(
            quality_strategy=qs,
            responsible_tiles=rt,
            attribution=attribution(),
            candidate_objective=candidate,
            max_estimated_usd=2.0,
        )

        self.assertIn("objective_missing_horizon_psnr_axis", report["candidate_objective_gate"]["block_reasons"])
        self.assertFalse(report["paid_retry_allowed"])

    def test_records_overdense_leaf_as_failed_hypothesis(self):
        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=overdense_leaf_attribution(),
            candidate_objective=None,
            max_estimated_usd=2.0,
        )

        hypotheses = {item["hypothesis"] for item in report["failed_hypotheses"]}
        self.assertIn("loss_weighting_overdense_leaf", hypotheses)
        loss_hypothesis = next(
            item for item in report["failed_hypotheses"] if item["hypothesis"] == "loss_weighting_overdense_leaf"
        )
        self.assertEqual(loss_hypothesis["splat_vertex_count"], 1_967_919)
        self.assertEqual(loss_hypothesis["reference_splat_count"], 956_277)

    def test_blocks_next_candidate_without_density_controls_after_overdense_leaf(self):
        candidate = valid_candidate()
        candidate["targeted_quality_blockers"].extend(
            ["splat_vertex_count_above_reference_ratio", "splat_vertex_count_above_hard_max"]
        )
        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=overdense_leaf_attribution(),
            candidate_objective=candidate,
            max_estimated_usd=2.0,
        )

        gate = report["candidate_objective_gate"]
        self.assertIn("objective_missing_density_control_after_overdense_leaf", gate["block_reasons"])
        self.assertFalse(report["paid_retry_allowed"])

    def test_allows_next_candidate_with_density_controls_after_overdense_leaf(self):
        candidate = valid_candidate()
        candidate["targeted_quality_blockers"].extend(
            ["splat_vertex_count_above_reference_ratio", "splat_vertex_count_above_hard_max"]
        )
        candidate["objective_implementation"]["environment"].update(
            {
                "TRAINING_MAX_GAUSS_RATIO": "3.0",
                "TRAINING_STOP_SPLIT_AT": "6500",
            }
        )

        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=overdense_leaf_attribution(),
            candidate_objective=candidate,
            max_estimated_usd=2.0,
        )

        gate = report["candidate_objective_gate"]
        self.assertEqual(gate["decision"], "paid_retry_allowed")
        self.assertEqual(gate["block_reasons"], [])
        self.assertEqual(
            gate["density_control_implementation"]["environment"],
            {"TRAINING_MAX_GAUSS_RATIO": "3.0", "TRAINING_STOP_SPLIT_AT": "6500"},
        )


if __name__ == "__main__":
    unittest.main()
