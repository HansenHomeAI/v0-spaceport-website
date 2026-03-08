import sys
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2] / "infrastructure" / "containers" / "sfm"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from sfm_scaling import normalize_profile_override, select_sfm_runtime_plan


class SfmScalingTests(unittest.TestCase):
    def test_small_gps_dataset_keeps_quality_profile(self):
        plan = select_sfm_runtime_plan(
            286,
            has_gps_priors=True,
            profile_override="auto",
            cpu_count=8,
        )

        self.assertEqual(plan["selected_profile"], "quality")
        self.assertEqual(plan["selected_neighbors"], 30)
        self.assertEqual(plan["estimated_pairs"], 8580)
        self.assertEqual(plan["config"]["feature_process_size"], 2048)
        self.assertEqual(plan["stage_timeouts"]["match_features"], 2400)
        self.assertEqual(plan["stage_timeouts"]["reconstruct"], 7200)

    def test_medium_gps_dataset_reduces_matching_budget(self):
        plan = select_sfm_runtime_plan(
            500,
            has_gps_priors=True,
            profile_override="auto",
            cpu_count=16,
        )

        self.assertEqual(plan["selected_profile"], "medium_dataset")
        self.assertLessEqual(plan["selected_neighbors"], 20)
        self.assertGreaterEqual(plan["selected_neighbors"], 10)
        self.assertLessEqual(plan["estimated_pairs"], 10000)
        self.assertEqual(plan["config"]["processes"], 6)
        self.assertEqual(plan["stage_timeouts"]["match_features"], 7200)

    def test_large_gps_dataset_uses_large_dataset_profile(self):
        plan = select_sfm_runtime_plan(
            898,
            has_gps_priors=True,
            profile_override="auto",
            cpu_count=16,
        )

        self.assertEqual(plan["selected_profile"], "large_dataset")
        self.assertLessEqual(plan["selected_neighbors"], 12)
        self.assertGreaterEqual(plan["selected_neighbors"], 8)
        self.assertLessEqual(plan["estimated_pairs"], 10776)
        self.assertEqual(plan["config"]["processes"], 4)
        self.assertEqual(plan["stage_timeouts"]["match_features"], 14400)
        self.assertEqual(plan["stage_timeouts"]["reconstruct"], 21600)

    def test_large_no_gps_dataset_extends_reconstruct_budget(self):
        plan = select_sfm_runtime_plan(
            898,
            has_gps_priors=False,
            profile_override="auto",
            cpu_count=16,
        )

        self.assertEqual(plan["selected_profile"], "no_gps_large_dataset")
        self.assertLessEqual(plan["selected_neighbors"], 8)
        self.assertGreaterEqual(plan["selected_neighbors"], 6)
        self.assertLessEqual(plan["estimated_pairs"], 7184)
        self.assertEqual(plan["stage_timeouts"]["match_features"], 14400)
        self.assertEqual(plan["stage_timeouts"]["reconstruct"], 21600)

    def test_quality_override_respects_requested_profile(self):
        plan = select_sfm_runtime_plan(
            898,
            has_gps_priors=True,
            profile_override="quality",
            cpu_count=16,
        )

        self.assertEqual(plan["selected_profile"], "quality")
        self.assertEqual(plan["selected_neighbors"], 30)
        self.assertEqual(plan["config"]["feature_max_num_features"], 20000)

    def test_invalid_override_raises(self):
        with self.assertRaises(ValueError):
            normalize_profile_override("unknown")


if __name__ == "__main__":
    unittest.main()
