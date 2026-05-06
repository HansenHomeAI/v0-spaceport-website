import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "plan_md1_quality_strategy.py"
SPEC = importlib.util.spec_from_file_location("plan_md1_quality_strategy_test_module", MODULE_PATH)
planner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(planner)


def review_comparison(*blockers: str) -> dict:
    return {
        "promotion_decision": {
            "status": "blocked" if blockers else "promoted",
            "block_reasons": list(blockers),
            "per_bucket": {
                "boundary": {
                    "delta": {
                        "psnr": 0.1,
                        "ssim": 0.002,
                        "lpips": -0.004,
                    }
                }
            },
            "thresholds": {
                "boundary": {
                    "required_improvement": {
                        "psnr": 0.5,
                        "ssim": 0.01,
                        "lpips": -0.025,
                    }
                }
            },
        }
    }


def strategy(*targets: str) -> dict:
    return {
        "targeted_quality_blockers": list(targets),
        "no_full_14tile_training": True,
        "submitted_jobs": [],
        "planned_cost_estimate": {"estimated_usd": 1.25},
    }


class PlanMd1QualityStrategyTests(unittest.TestCase):
    def test_reports_boundary_improvement_gap(self):
        report = planner.plan_quality_strategy(
            review_comparison=review_comparison("boundary_no_required_improvement"),
            candidate_strategy=strategy("boundary_no_required_improvement"),
            max_estimated_usd=2.5,
        )

        self.assertEqual(report["boundary_improvement_gap"]["remaining_gap"]["psnr"], 0.4)
        self.assertEqual(report["boundary_improvement_gap"]["remaining_gap"]["ssim"], 0.008)
        self.assertAlmostEqual(report["boundary_improvement_gap"]["remaining_gap"]["lpips"], 0.021)

    def test_holds_paid_retry_when_current_blocker_is_not_targeted(self):
        report = planner.plan_quality_strategy(
            review_comparison=review_comparison("boundary_no_required_improvement"),
            candidate_strategy=strategy("horizon_v18_sky_score_regression"),
            max_estimated_usd=2.5,
        )

        self.assertEqual(report["recommendation"], "hold_paid_retry")
        self.assertFalse(report["paid_retry_recommended"])
        self.assertEqual(report["missing_targeted_blockers"], ["boundary_no_required_improvement"])

    def test_recommends_candidate_strategy_only_when_current_blockers_are_targeted(self):
        report = planner.plan_quality_strategy(
            review_comparison=review_comparison("boundary_no_required_improvement"),
            candidate_strategy=strategy("boundary_no_required_improvement"),
            max_estimated_usd=2.5,
        )

        self.assertEqual(report["recommendation"], "candidate_strategy_targets_current_blockers")
        self.assertTrue(report["paid_retry_recommended"])

    def test_holds_paid_retry_when_strategy_exceeds_budget(self):
        over_budget = strategy("boundary_no_required_improvement")
        over_budget["planned_cost_estimate"] = {"estimated_usd": 3.0}

        report = planner.plan_quality_strategy(
            review_comparison=review_comparison("boundary_no_required_improvement"),
            candidate_strategy=over_budget,
            max_estimated_usd=2.5,
        )

        self.assertEqual(report["recommendation"], "hold_paid_retry")
        self.assertFalse(report["paid_retry_recommended"])

    def test_promoted_review_has_clear_recommendation(self):
        report = planner.plan_quality_strategy(
            review_comparison=review_comparison(),
            candidate_strategy=None,
            max_estimated_usd=2.5,
        )

        self.assertEqual(report["recommendation"], "quality_blockers_clear")
        self.assertFalse(report["paid_retry_recommended"])


if __name__ == "__main__":
    unittest.main()
