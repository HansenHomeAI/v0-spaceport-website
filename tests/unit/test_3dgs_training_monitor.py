import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "monitor_3dgs_training_cost.py"
SPEC = importlib.util.spec_from_file_location("monitor_3dgs_training_cost_test_module", MODULE_PATH)
monitor = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(monitor)


class TrainingCostMonitorTests(unittest.TestCase):
    def test_estimate_training_spend_prefers_billable_seconds(self):
        spend = monitor.estimate_training_spend(
            {
                "TrainingTimeInSeconds": 7200,
                "BillableTimeInSeconds": 3600,
                "ResourceConfig": {"InstanceType": "ml.g5.2xlarge"},
            }
        )

        self.assertEqual(spend["instance_type"], "ml.g5.2xlarge")
        self.assertAlmostEqual(spend["estimated_usd"], 1.515, places=3)
        self.assertAlmostEqual(spend["billable_hours"], 1.0, places=3)

    def test_evaluate_training_health_blocks_over_budget_stale_logs_and_low_gpu(self):
        health = monitor.evaluate_training_health(
            training_job={
                "TrainingJobName": "md1-cost-test",
                "TrainingJobStatus": "InProgress",
                "SecondaryStatus": "Training",
                "TrainingTimeInSeconds": 7200,
                "ResourceConfig": {"InstanceType": "ml.g5.2xlarge"},
            },
            latest_log_age_seconds=1800,
            gpu_average_percent=1.5,
            s3_output_object_count=0,
            max_estimated_usd=2.0,
            max_log_staleness_seconds=900,
            low_gpu_threshold_percent=5.0,
            low_gpu_warmup_seconds=600,
        )

        self.assertEqual(health["status"], "blocked")
        self.assertIn("estimated_spend_over_budget", health["block_reasons"])
        self.assertIn("cloudwatch_log_stale", health["block_reasons"])
        self.assertIn("gpu_low_after_warmup", health["block_reasons"])

    def test_evaluate_training_health_blocks_completed_without_artifact(self):
        health = monitor.evaluate_training_health(
            training_job={
                "TrainingJobName": "md1-cost-test",
                "TrainingJobStatus": "Completed",
                "TrainingTimeInSeconds": 60,
                "ResourceConfig": {"InstanceType": "ml.g5.2xlarge"},
            },
            latest_log_age_seconds=0,
            gpu_average_percent=None,
            s3_output_object_count=0,
            max_estimated_usd=10.0,
        )

        self.assertEqual(health["status"], "blocked")
        self.assertIn("completed_without_model_artifact", health["block_reasons"])


if __name__ == "__main__":
    unittest.main()
