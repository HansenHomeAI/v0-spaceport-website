import sys
import types
import unittest
import importlib.util
import os
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

    def test_spiral_designer_uses_real_google_key_when_present(self):
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "prod-key-123"}, clear=False), \
             patch("builtins.print"):
            designer = drone_path_module.SpiralDesigner()

        self.assertEqual(designer.api_key, "prod-key-123")

    def test_spiral_designer_falls_back_when_google_key_is_blank(self):
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": ""}, clear=False), \
             patch("builtins.print"):
            designer = drone_path_module.SpiralDesigner()

        self.assertEqual(designer.api_key, "AIzaSyDkdnE1weVG38PSUO5CWFneFjH16SPYZHU")

    def test_get_elevation_raises_when_live_terrain_is_required_and_google_denies(self):
        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {
                    "status": "REQUEST_DENIED",
                    "error_message": "This API project is not authorized to use this API."
                }

        self.designer.require_live_elevation = True

        with patch.object(drone_path_module.requests, "get", return_value=FakeResponse()):
            with self.assertRaises(drone_path_module.TerrainElevationUnavailableError):
                self.designer.get_elevation_feet(39.6654, -105.2057)

    def test_handle_elevation_returns_service_unavailable_when_google_denies(self):
        with patch.object(
            self.designer,
            "get_elevation_feet",
            side_effect=drone_path_module.TerrainElevationUnavailableError(
                "Terrain following is unavailable because Google Elevation returned REQUEST_DENIED"
            ),
        ):
            response = drone_path_module.handle_elevation(
                self.designer,
                {"center": self.center},
                {},
            )

        self.assertEqual(response["statusCode"], 503)
        self.assertIn("REQUEST_DENIED", response["body"])

    def test_battery_csv_returns_service_unavailable_when_google_denies(self):
        with patch.object(
            self.designer,
            "build_battery_csv_export",
            side_effect=drone_path_module.TerrainElevationUnavailableError(
                "Terrain following is unavailable because Google Elevation returned REQUEST_DENIED"
            ),
        ):
            response = drone_path_module.handle_battery_csv_download(
                self.designer,
                {
                    "slices": 1,
                    "N": 4,
                    "r0": 200,
                    "rHold": 355.869140625,
                    "center": self.center,
                    "minHeight": 120,
                    "maxHeight": "",
                    "formToTerrain": True,
                },
                "1",
                {},
            )

        self.assertEqual(response["statusCode"], 503)
        self.assertIn("REQUEST_DENIED", response["body"])


if __name__ == "__main__":
    unittest.main()
