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


def valid_candidate() -> dict:
    return {
        "targeted_quality_blockers": ["boundary_no_required_improvement"],
        "selected_tile_ids": ["tile_04"],
        "context_support_tile_ids": ["tile_10", "tile_13", "tile_01"],
        "boundary_camera_ids": ["DJI_0067.JPG", "DJI_0068.JPG", "DJI_0069.JPG", "DJI_0070.JPG"],
        "horizon_camera_ids": ["DJI_0066.JPG", "DJI_0073.JPG"],
        "expected_metric_axes": ["boundary.required_improvement", "boundary.psnr", "boundary.ssim"],
        "objective_changes": ["boundary_camera_weighting", "boundary_loss_weighting"],
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
        self.assertTrue(report["paid_retry_allowed"])

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


if __name__ == "__main__":
    unittest.main()
