import sys
import unittest
from pathlib import Path


MODULE_ROOT = Path(__file__).resolve().parents[2] / "infrastructure" / "spaceport_cdk" / "lambda" / "start_ml_job"
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from request_options import normalize_pipeline_step, normalize_sfm_options


class StartMlJobRequestOptionTests(unittest.TestCase):
    def test_pipeline_step_defaults_to_full(self):
        self.assertEqual(normalize_pipeline_step(None), "full")
        self.assertEqual(normalize_pipeline_step(""), "full")

    def test_pipeline_step_accepts_sfm_only(self):
        self.assertEqual(normalize_pipeline_step("sfm"), "sfm")

    def test_pipeline_step_rejects_unknown_values(self):
        with self.assertRaises(ValueError):
            normalize_pipeline_step("invalid-step")

    def test_sfm_options_default_to_cost_aware_runtime(self):
        options = normalize_sfm_options(None)

        self.assertEqual(options["instanceType"], "ml.c6i.4xlarge")
        self.assertEqual(options["profileOverride"], "auto")

    def test_sfm_options_accept_explicit_overrides(self):
        options = normalize_sfm_options(
            {
                "instanceType": "ml.r7i.4xlarge",
                "profileOverride": "large_dataset",
            }
        )

        self.assertEqual(options["instanceType"], "ml.r7i.4xlarge")
        self.assertEqual(options["profileOverride"], "large_dataset")

    def test_sfm_options_reject_invalid_values(self):
        with self.assertRaises(ValueError):
            normalize_sfm_options({"instanceType": "not-an-instance"})

        with self.assertRaises(ValueError):
            normalize_sfm_options({"profileOverride": "fast"})


if __name__ == "__main__":
    unittest.main()
