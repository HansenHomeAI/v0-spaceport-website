import sys
import types
import unittest
import importlib.util
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


class DronePathTerrainToggleTests(unittest.TestCase):
    def setUp(self):
        with patch("builtins.print"):
            self.designer = drone_path_module.SpiralDesigner()
        self.params = {"slices": 2, "N": 6, "r0": 100, "rHold": 1000}
        self.center = "37.1972,-113.6187"

    def test_battery_csv_skips_google_elevation_when_toggle_is_off(self):
        with patch.object(self.designer, "get_elevation_feet", side_effect=AssertionError("should not fetch elevation")), \
             patch.object(self.designer, "get_elevations_feet_optimized", side_effect=AssertionError("should not batch fetch elevation")), \
             patch.object(self.designer, "adaptive_terrain_sampling", side_effect=AssertionError("should not terrain sample")), \
             patch("builtins.print"):
            csv_content = self.designer.generate_battery_csv(
                self.params,
                self.center,
                battery_index=0,
                min_height=120.0,
                max_height=180.0,
                form_to_terrain=False,
            )

        rows = csv_content.splitlines()
        self.assertTrue(rows[0].startswith("latitude,longitude,altitude(ft)"))
        self.assertGreater(len(rows), 2)

    def test_full_csv_skips_google_elevation_when_toggle_is_off(self):
        with patch.object(self.designer, "get_elevation_feet", side_effect=AssertionError("should not fetch elevation")), \
             patch.object(self.designer, "get_elevations_feet_optimized", side_effect=AssertionError("should not batch fetch elevation")), \
             patch.object(self.designer, "adaptive_terrain_sampling", side_effect=AssertionError("should not terrain sample")), \
             patch("builtins.print"):
            csv_content = self.designer.generate_csv(
                self.params,
                self.center,
                min_height=120.0,
                max_height=180.0,
                form_to_terrain=False,
            )

        rows = csv_content.splitlines()
        self.assertTrue(rows[0].startswith("latitude,longitude,altitude(ft)"))
        self.assertGreater(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
