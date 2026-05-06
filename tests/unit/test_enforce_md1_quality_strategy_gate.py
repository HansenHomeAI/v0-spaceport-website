import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "enforce_md1_quality_strategy_gate.py"
SPEC = importlib.util.spec_from_file_location("enforce_md1_quality_strategy_gate_test_module", MODULE_PATH)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(gate)


def readiness(*blockers: str, promotion_ready: bool = False) -> dict:
    return {
        "promotion_ready": promotion_ready,
        "quality_gate": {
            "status": "passed" if promotion_ready else "blocked",
            "block_reasons": list(blockers),
        },
    }


def strategy(*targets: str) -> dict:
    return {
        "no_full_14tile_training": True,
        "submitted_jobs": [],
        "planned_cost_estimate": {"estimated_usd": 1.25},
        "targeted_quality_blockers": list(targets),
    }


class EnforceMd1QualityStrategyGateTests(unittest.TestCase):
    def test_blocks_paid_retry_without_targeted_quality_blockers(self):
        summary = gate.evaluate_gate(
            readiness_report=readiness("boundary_no_required_improvement"),
            strategy={
                "no_full_14tile_training": True,
                "submitted_jobs": [],
                "planned_cost_estimate": {"estimated_usd": 1.25},
            },
            max_estimated_usd=2.5,
        )

        self.assertEqual(summary["decision"], "paid_retry_blocked")
        self.assertIn("quality_strategy_missing_targeted_blockers", summary["block_reasons"])
        self.assertEqual(summary["missing_targeted_blockers"], ["boundary_no_required_improvement"])

    def test_blocks_paid_retry_when_any_current_blocker_is_not_targeted(self):
        summary = gate.evaluate_gate(
            readiness_report=readiness(
                "boundary_no_required_improvement",
                "horizon_v18_sky_score_regression",
            ),
            strategy=strategy("horizon_v18_sky_score_regression"),
            max_estimated_usd=2.5,
        )

        self.assertEqual(summary["decision"], "paid_retry_blocked")
        self.assertIn("quality_strategy_does_not_target_current_blockers", summary["block_reasons"])
        self.assertEqual(summary["missing_targeted_blockers"], ["boundary_no_required_improvement"])

    def test_allows_dryrun_strategy_that_targets_current_blockers_under_budget(self):
        summary = gate.evaluate_gate(
            readiness_report=readiness("boundary_no_required_improvement"),
            strategy=strategy("boundary_no_required_improvement"),
            max_estimated_usd=2.5,
        )

        self.assertEqual(summary["decision"], "paid_retry_allowed")
        self.assertEqual(summary["block_reasons"], [])

    def test_blocks_full_14tile_and_already_submitted_strategies(self):
        bad_strategy = strategy("boundary_no_required_improvement")
        bad_strategy["no_full_14tile_training"] = False
        bad_strategy["submitted_jobs"] = [{"job_name": "already-started"}]

        summary = gate.evaluate_gate(
            readiness_report=readiness("boundary_no_required_improvement"),
            strategy=bad_strategy,
            max_estimated_usd=2.5,
        )

        self.assertEqual(summary["decision"], "paid_retry_blocked")
        self.assertIn("no_full_14tile_training_not_confirmed", summary["block_reasons"])
        self.assertIn("strategy_already_submitted_jobs", summary["block_reasons"])

    def test_blocks_strategy_over_budget(self):
        over_budget = strategy("boundary_no_required_improvement")
        over_budget["planned_cost_estimate"] = {"estimated_usd": 3.0}

        summary = gate.evaluate_gate(
            readiness_report=readiness("boundary_no_required_improvement"),
            strategy=over_budget,
            max_estimated_usd=2.5,
        )

        self.assertEqual(summary["decision"], "paid_retry_blocked")
        self.assertIn("strategy_estimated_cost_above_cap", summary["block_reasons"])

    def test_promotion_ready_does_not_require_quality_target_labels(self):
        summary = gate.evaluate_gate(
            readiness_report=readiness(promotion_ready=True),
            strategy={
                "no_full_14tile_training": True,
                "submitted_jobs": [],
                "planned_cost_estimate": {"estimated_usd": 0.0},
            },
            max_estimated_usd=1.0,
        )

        self.assertEqual(summary["decision"], "paid_retry_allowed")
        self.assertEqual(summary["block_reasons"], [])


if __name__ == "__main__":
    unittest.main()
