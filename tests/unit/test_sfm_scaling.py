import sys
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2] / "infrastructure" / "containers" / "sfm"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from sfm_scaling import normalize_profile_override, select_sfm_runtime_plan


class SfmScalingTests(unittest.TestCase):
    def test_small_gps_dataset_uses_quality_profile(self):
        plan = select_sfm_runtime_plan(
            286,
            has_gps_priors=True,
            profile_override="auto",
            cpu_count=8,
            median_relative_altitude_m=40.0,
        )

        self.assertEqual(plan["selected_profile"], "quality")
        self.assertEqual(plan["segment_worker_count"], 1)
        self.assertEqual(plan["segment_target_size"], 400)
        self.assertEqual(plan["spatial_matcher_neighbors"], 12)
        self.assertEqual(plan["spatial_matcher_distance_m"], 100)

    def test_medium_gps_dataset_uses_two_workers(self):
        plan = select_sfm_runtime_plan(
            500,
            has_gps_priors=True,
            profile_override="auto",
            cpu_count=16,
            median_relative_altitude_m=45.0,
        )

        self.assertEqual(plan["selected_profile"], "medium_dataset")
        self.assertEqual(plan["segment_worker_count"], 2)
        self.assertEqual(plan["segment_count_estimate"], 1)
        self.assertEqual(plan["worker_threads"], 8)

    def test_large_gps_dataset_uses_large_dataset_profile(self):
        plan = select_sfm_runtime_plan(
            1800,
            has_gps_priors=True,
            profile_override="auto",
            cpu_count=24,
            median_relative_altitude_m=50.0,
        )

        self.assertEqual(plan["selected_profile"], "large_dataset")
        self.assertEqual(plan["segment_worker_count"], 4)
        self.assertGreater(plan["segment_count_estimate"], 1)
        self.assertEqual(plan["spatial_matcher_distance_m"], 125)
        self.assertEqual(plan["stage_timeouts"]["job_total"], 10800)

    def test_large_no_gps_dataset_uses_lower_pair_budget(self):
        plan = select_sfm_runtime_plan(
            1800,
            has_gps_priors=False,
            profile_override="auto",
            cpu_count=24,
        )

        self.assertEqual(plan["selected_profile"], "no_gps_large_dataset")
        self.assertEqual(plan["spatial_matcher_neighbors"], 8)
        self.assertEqual(plan["segment_worker_count"], 4)

    def test_invalid_override_raises(self):
        with self.assertRaises(ValueError):
            normalize_profile_override("unknown")


if __name__ == "__main__":
    unittest.main()
