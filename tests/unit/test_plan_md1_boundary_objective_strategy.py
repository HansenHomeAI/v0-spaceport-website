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


def density_capped_regression_attribution() -> dict:
    attr = attribution()
    attr.pop("density_v2_minus_baseline_bucket_delta", None)
    attr["density_capped_minus_reference_bucket_delta"] = {
        "boundary": {"psnr": -0.366, "ssim": -0.0058, "lpips": 0.0726},
        "horizon": {"psnr": -0.784, "ssim": -0.0137, "lpips": 0.0965},
        "near_detail": {"psnr": -0.81, "ssim": 0.0165, "lpips": 0.0623},
    }
    attr["tested_candidate"] = {
        "candidate": "density_capped_loss_weighting_tile04_plus_tile10_rollback_bg10",
        "promotion_block_reasons": [
            "boundary_lpips_regression",
            "boundary_no_required_improvement",
            "horizon_psnr_regression",
            "horizon_ssim_regression",
            "horizon_lpips_regression",
        ],
        "v18_non_regression_block_reasons": [
            "boundary_v18_median_lpips_regression",
            "horizon_v18_median_psnr_regression",
            "horizon_v18_median_lpips_regression",
        ],
    }
    return attr


def soft_density_regression_attribution() -> dict:
    attr = attribution()
    attr.pop("density_v2_minus_baseline_bucket_delta", None)
    attr["soft_density_minus_reference_bucket_delta"] = {
        "boundary": {"psnr": -0.3591, "ssim": -0.0041, "lpips": 0.0621},
        "horizon": {"psnr": -1.0588, "ssim": -0.0039, "lpips": 0.1029},
        "near_detail": {"psnr": -0.3136, "ssim": 0.0152, "lpips": 0.0148},
    }
    attr["tested_candidate"] = {
        "candidate": "soft_density_tile04_plus_tile10_rollback_bg10",
        "promotion_block_reasons": [
            "boundary_lpips_regression",
            "boundary_no_required_improvement",
            "horizon_psnr_regression",
            "horizon_lpips_regression",
        ],
        "v18_non_regression_block_reasons": [
            "near_detail_v18_median_psnr_regression",
            "boundary_v18_median_lpips_regression",
            "horizon_v18_median_psnr_regression",
            "horizon_v18_median_lpips_regression",
        ],
    }
    attr["visual_qa_gate_block_reasons"] = [
        "visual_qa_ai_visual_review_blocking_defects",
        "visual_qa_ai_visual_review_status_block",
    ]
    attr["ai_visual_defect_blockers"] = [
        "ai_visual_horizon_continuity_defect",
        "ai_visual_geometry_alignment_defect",
        "ai_visual_texture_smearing_defect",
        "ai_visual_color_shift_defect",
    ]
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
        "v18_review_manifest_s3_uri": "s3://example/v18-review",
        "visual_qa_required": True,
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

    def test_records_density_capped_quality_regression_as_failed_hypothesis(self):
        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=density_capped_regression_attribution(),
            candidate_objective=None,
            max_estimated_usd=2.0,
        )

        hypotheses = {item["hypothesis"] for item in report["failed_hypotheses"]}
        self.assertIn("density_capped_loss_weighting_quality_regression", hypotheses)
        self.assertIn("boundary_lpips_regression", report["current_quality_blockers"])
        self.assertIn("horizon_lpips_regression", report["current_quality_blockers"])
        self.assertIn("horizon.lpips", report["required_next_hypothesis"]["expected_metric_axes"])

    def test_blocks_next_candidate_that_repeats_hard_density_cap_after_quality_regression(self):
        candidate = valid_candidate()
        candidate["targeted_quality_blockers"] = [
            "boundary_no_required_improvement",
            "boundary_lpips_regression",
            "horizon_psnr_regression",
            "horizon_ssim_regression",
            "horizon_lpips_regression",
        ]
        candidate["expected_metric_axes"] = [
            "boundary.required_improvement",
            "boundary.lpips",
            "horizon.psnr",
            "horizon.ssim",
            "horizon.lpips",
        ]
        candidate["objective_changes"] = [
            "boundary_loss_weighting",
            "density_capped_loss_weighting",
        ]
        candidate["objective_implementation"]["environment"].update(
            {
                "BOUNDARY_LOSS_WEIGHT": "1.15",
                "TRAINING_DENSITY_CAP_ENABLED": "1",
                "TRAINING_MAX_OUTPUT_GAUSSIANS": "984154",
            }
        )

        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=density_capped_regression_attribution(),
            candidate_objective=candidate,
            max_estimated_usd=2.0,
        )

        gate = report["candidate_objective_gate"]
        self.assertIn(
            "objective_repeats_failed_density_cap_loss_weighting_hypothesis",
            gate["block_reasons"],
        )
        self.assertFalse(report["paid_retry_allowed"])

    def test_allows_quality_preserving_density_control_after_density_cap_regression(self):
        candidate = valid_candidate()
        candidate["targeted_quality_blockers"] = [
            "boundary_no_required_improvement",
            "boundary_lpips_regression",
            "horizon_psnr_regression",
            "horizon_ssim_regression",
            "horizon_lpips_regression",
        ]
        candidate["expected_metric_axes"] = [
            "boundary.required_improvement",
            "boundary.lpips",
            "horizon.psnr",
            "horizon.ssim",
            "horizon.lpips",
        ]
        candidate["objective_changes"] = [
            "boundary_loss_weighting",
            "soft_density_control",
            "quality_preserving",
            "horizon_preserving",
        ]
        candidate["objective_implementation"]["environment"].update(
            {
                "BOUNDARY_LOSS_WEIGHT": "1.15",
                "TRAINING_MAX_GAUSS_RATIO": "1.35",
                "TRAINING_STOP_SPLIT_AT": "6500",
            }
        )

        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=density_capped_regression_attribution(),
            candidate_objective=candidate,
            max_estimated_usd=2.0,
        )

        self.assertEqual(report["candidate_objective_gate"]["decision"], "paid_retry_allowed")

    def test_records_soft_density_quality_regression_and_ai_visual_blockers(self):
        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=soft_density_regression_attribution(),
            candidate_objective=None,
            max_estimated_usd=2.0,
        )

        hypotheses = {item["hypothesis"] for item in report["failed_hypotheses"]}
        self.assertIn("soft_density_quality_regression", hypotheses)
        self.assertIn("boundary_lpips_regression", report["current_quality_blockers"])
        self.assertIn("horizon_lpips_regression", report["current_quality_blockers"])
        self.assertIn("ai_visual_color_shift_defect", report["current_quality_blockers"])
        self.assertIn(
            "soft-density/global-SSIM retry without a new appearance, geometry, color, or perceptual objective",
            report["required_next_hypothesis"]["must_not_repeat"],
        )

    def test_blocks_repeating_soft_density_after_visual_quality_failure(self):
        candidate = valid_candidate()
        candidate["targeted_quality_blockers"] = [
            "boundary_no_required_improvement",
            "boundary_lpips_regression",
            "horizon_psnr_regression",
            "horizon_lpips_regression",
            "visual_qa_ai_visual_review_blocking_defects",
            "visual_qa_ai_visual_review_status_block",
            "ai_visual_horizon_continuity_defect",
            "ai_visual_geometry_alignment_defect",
            "ai_visual_texture_smearing_defect",
            "ai_visual_color_shift_defect",
        ]
        candidate["expected_metric_axes"] = [
            "boundary.required_improvement",
            "boundary.lpips",
            "horizon.psnr",
            "horizon.lpips",
        ]
        candidate["objective_changes"] = [
            "boundary_loss_weighting",
            "global_ssim_loss_weighting",
            "soft_density_control",
            "quality_preserving",
            "horizon_preserving",
        ]
        candidate["objective_implementation"]["environment"].update(
            {
                "BOUNDARY_LOSS_WEIGHT": "1.15",
                "TRAINING_MAX_GAUSS_RATIO": "1.35",
                "TRAINING_STOP_SPLIT_AT": "7600",
            }
        )

        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=soft_density_regression_attribution(),
            candidate_objective=candidate,
            max_estimated_usd=2.0,
        )

        self.assertIn(
            "objective_repeats_failed_soft_density_hypothesis",
            report["candidate_objective_gate"]["block_reasons"],
        )
        self.assertFalse(report["paid_retry_allowed"])

    def test_requires_v18_and_visual_qa_plans_after_soft_density_ai_block(self):
        candidate = valid_candidate()
        candidate.pop("v18_review_manifest_s3_uri")
        candidate.pop("visual_qa_required")
        candidate["targeted_quality_blockers"] = [
            "boundary_no_required_improvement",
            "boundary_lpips_regression",
            "horizon_psnr_regression",
            "horizon_lpips_regression",
            "visual_qa_ai_visual_review_blocking_defects",
            "visual_qa_ai_visual_review_status_block",
            "ai_visual_horizon_continuity_defect",
            "ai_visual_geometry_alignment_defect",
            "ai_visual_texture_smearing_defect",
            "ai_visual_color_shift_defect",
        ]
        candidate["expected_metric_axes"] = [
            "boundary.required_improvement",
            "boundary.lpips",
            "horizon.psnr",
            "horizon.lpips",
        ]
        candidate["objective_changes"] = [
            "boundary_loss_weighting",
            "lpips_loss_weighting",
            "appearance_consistency",
            "color_consistency",
        ]
        candidate["objective_implementation"]["environment"].update(
            {
                "BOUNDARY_LOSS_WEIGHT": "1.15",
                "BOUNDARY_LPIPS_LOSS_WEIGHT": "0.10",
            }
        )

        report = planner.plan_boundary_objective_strategy(
            quality_strategy=quality_strategy(),
            responsible_tiles=responsible_tiles(),
            attribution=soft_density_regression_attribution(),
            candidate_objective=candidate,
            max_estimated_usd=2.0,
        )

        reasons = report["candidate_objective_gate"]["block_reasons"]
        self.assertIn("objective_missing_v18_non_regression_plan_after_soft_density_failure", reasons)
        self.assertIn("objective_missing_visual_qa_plan_after_ai_block", reasons)
        self.assertFalse(report["paid_retry_allowed"])


if __name__ == "__main__":
    unittest.main()
