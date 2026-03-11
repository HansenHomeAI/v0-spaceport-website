import sys
import types
import unittest
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "infrastructure"
    / "spaceport_cdk"
    / "lambda"
    / "drone_path"
    / "lambda_function.py"
)


if "requests" not in sys.modules:
    fake_requests = types.SimpleNamespace(get=lambda *args, **kwargs: None)
    sys.modules["requests"] = fake_requests

SPEC = importlib.util.spec_from_file_location("drone_path_lambda", MODULE_PATH)
drone_path_module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(drone_path_module)


class DronePathOptimizerTests(unittest.TestCase):
    def setUp(self):
        with patch("builtins.print"):
            self.designer = drone_path_module.SpiralDesigner()

    def optimize(self, **kwargs):
        with patch("builtins.print"):
            return self.designer.optimize_spiral_for_battery(**kwargs)

    def assert_fits_battery(self, optimized, battery_minutes: float):
        self.assertLessEqual(float(optimized["estimated_time_minutes"]), battery_minutes * 0.98 + 0.05)

    def test_default_mode_stays_within_battery_and_exposes_late_bounce_metadata(self):
        optimized = self.optimize(
            target_battery_minutes=20,
            num_batteries=3,
            center_lat=41.0,
            center_lon=-111.0,
        )

        self.assert_fits_battery(optimized, 20)
        self.assertEqual(optimized["expansionMode"], "default")
        self.assertIsNone(optimized["actualMinExpansionDist"])
        self.assertIsNone(optimized["actualMaxExpansionDist"])
        self.assertGreater(float(optimized["actualOuterRadius"]), 0.0)
        self.assertIn("requestedBounceSeed", optimized)
        self.assertTrue(bool(optimized["adjustedBounceCount"]))
        self.assertNotEqual(int(optimized["N"]), int(optimized["requestedBounceSeed"]))

    def test_custom_spacing_reduces_bounces_before_tightening(self):
        optimized = self.optimize(
            target_battery_minutes=20,
            num_batteries=3,
            center_lat=41.0,
            center_lon=-111.0,
            min_expansion_dist=100.0,
            max_expansion_dist=200.0,
        )

        self.assert_fits_battery(optimized, 20)
        self.assertEqual(optimized["expansionMode"], "custom")
        self.assertEqual(float(optimized["actualMinExpansionDist"]), 100.0)
        self.assertEqual(float(optimized["actualMaxExpansionDist"]), 200.0)
        self.assertFalse(bool(optimized["adjustedExpansion"]))
        self.assertTrue(bool(optimized["adjustedBounceCount"]))
        self.assertLess(int(optimized["N"]), int(optimized["requestedBounceSeed"]))

    def test_custom_spacing_tightens_when_requested_spacing_is_impossible(self):
        optimized = self.optimize(
            target_battery_minutes=20,
            num_batteries=3,
            center_lat=41.0,
            center_lon=-111.0,
            min_expansion_dist=500000.0,
            max_expansion_dist=500000.0,
        )

        self.assert_fits_battery(optimized, 20)
        self.assertEqual(optimized["expansionMode"], "custom")
        self.assertTrue(bool(optimized["adjustedExpansion"]))
        self.assertLess(float(optimized["actualMinExpansionDist"]), 500000.0)
        self.assertLess(float(optimized["actualMaxExpansionDist"]), 500000.0)

    def test_single_slice_custom_spacing_respects_waypoint_budget(self):
        optimized = self.optimize(
            target_battery_minutes=20,
            num_batteries=1,
            center_lat=37.1972,
            center_lon=-113.6187,
            min_expansion_dist=100.0,
        )

        self.assert_fits_battery(optimized, 20)
        self.assertLessEqual(int(optimized["N"]), self.designer.max_bounces_for_waypoint_budget(1))

    def test_optimize_endpoint_returns_requested_final_constraints_and_adjustments(self):
        with patch("builtins.print"):
            response = drone_path_module.handle_optimize_spiral(
                self.designer,
                {
                    "batteryMinutes": 20,
                    "batteries": 3,
                    "center": "41.0, -111.0",
                    "minExpansionDist": 100,
                    "maxExpansionDist": 200,
                },
                {},
            )

        self.assertEqual(response["statusCode"], 200)
        payload = json.loads(response["body"])
        self.assertIn("optimized_params", payload)
        self.assertIn("optimization_info", payload)
        self.assertIn("requested_constraints", payload["optimization_info"])
        self.assertIn("final_constraints", payload["optimization_info"])
        self.assertIsInstance(payload["optimization_info"].get("adjustments"), list)
        self.assertGreater(len(payload["optimization_info"]["adjustments"]), 0)

    def test_battery_csv_download_accepts_actual_expansion_fields(self):
        body = {
            "slices": 3,
            "N": 7,
            "r0": 200,
            "rHold": 1250,
            "center": "41.0, -111.0",
            "minHeight": 120,
            "actualMinExpansionDist": 100,
            "actualMaxExpansionDist": 200,
        }

        with patch("builtins.print"):
            response = drone_path_module.handle_battery_csv_download(
                self.designer,
                body,
                "1",
                {},
            )

        self.assertEqual(response["statusCode"], 200)
        self.assertIn("latitude,longitude", response["body"])


if __name__ == "__main__":
    unittest.main()
