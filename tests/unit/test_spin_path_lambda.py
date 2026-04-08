import csv
import importlib.util
import io
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "infrastructure"
    / "spaceport_cdk"
    / "lambda"
    / "spin_path"
    / "lambda_function.py"
)


if "requests" not in sys.modules:
    sys.modules["requests"] = types.SimpleNamespace(get=lambda *args, **kwargs: None)

SPEC = importlib.util.spec_from_file_location("spin_path_lambda", MODULE_PATH)
spin_path_module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(spin_path_module)


class SpinPathLambdaTests(unittest.TestCase):
    def setUp(self):
        with patch("builtins.print"):
            self.designer = spin_path_module.SpiralDesigner()
        self.center = "37.1972,-113.6187"
        self.params = {"slices": 2, "N": 6, "r0": 100, "rHold": 1000}
        self.raw_overlap_config = {
            "speedFts": 24.93,
            "speedMph": 17.0,
            "speedEnvLoAglFt": 200.0,
            "speedEnvLoMph": 17.0,
            "speedEnvHiAglFt": 400.0,
            "speedEnvHiMph": 22.0,
            "captureSpacingFt": 12.0,
            "captureIntervalSeconds": 0.5,
            "captureIntervalUnit": "s",
            "captureDistanceIntervalFt": 12.0,
            "captureTimeIntervalSeconds": 0.5,
            "yawRateDegPerSec": 90.0,
            "captureArcDeg": 180.0,
            "maxHeadingDeltaDeg": 179.0,
            "defaultPitchDeg": -25.0,
            "pitchSequenceNeg": [-20.0, -25.0, -30.0, -35.0],
        }
        self.parsed_overlap_config = spin_path_module._parse_real_path_overlap_config(self.raw_overlap_config)

    def _patch_terrain_dependencies(self):
        return patch.object(self.designer, "get_elevation_feet", return_value=1000.0), \
            patch.object(self.designer, "get_elevations_feet_optimized", side_effect=lambda locs: [1000.0] * len(locs)), \
            patch.object(self.designer, "adaptive_terrain_sampling", return_value=[]), \
            patch("builtins.print")

    def _build_export(self):
        terrain_patches = self._patch_terrain_dependencies()
        with terrain_patches[0], terrain_patches[1], terrain_patches[2], terrain_patches[3]:
            return spin_path_module._build_real_path_battery_export(
                designer=self.designer,
                params=self.params,
                center_str=self.center,
                battery_index=0,
                min_height=120.0,
                max_height=360.0,
                form_to_terrain=False,
                overlap_config=self.parsed_overlap_config,
            )

    def _parse_csv_rows(self, csv_text):
        return list(csv.DictReader(io.StringIO(csv_text)))

    def test_optimize_handler_returns_preview_paths_and_overlap_telemetry(self):
        terrain_patches = self._patch_terrain_dependencies()
        with terrain_patches[0], terrain_patches[1], terrain_patches[2], terrain_patches[3]:
            response = spin_path_module.handle_spin_path_optimize(
                self.designer,
                {
                    "center": self.center,
                    "batteryMinutes": 20,
                    "batteries": 2,
                    "minHeight": 120,
                    "maxHeight": 360,
                    "formToTerrain": False,
                    "overlapConfig": self.raw_overlap_config,
                },
                {},
            )

        self.assertEqual(response["statusCode"], 200)
        payload = json.loads(response["body"])
        self.assertEqual(len(payload["previewPaths"]), 2)
        self.assertEqual(len(payload["previewBatteries"]), 2)
        self.assertEqual(len(payload["batterySummaries"]), 2)
        self.assertEqual(payload["overlapTelemetry"]["captureSpacingFeet"], 12.0)
        self.assertEqual(payload["overlapTelemetry"]["yawRateDegPerSec"], 90.0)
        self.assertGreater(payload["previewBatteries"][0]["telemetry"]["waypointCount"], 99)
        self.assertEqual(payload["overlapTelemetry"]["captureTriggerMode"], "s")

    def test_optimize_handler_skips_adaptive_terrain_sampling_for_preview(self):
        with patch.object(self.designer, "get_elevation_feet", return_value=1000.0), \
             patch.object(self.designer, "get_elevations_feet_optimized", side_effect=lambda locs: [1000.0] * len(locs)), \
             patch.object(self.designer, "adaptive_terrain_sampling", side_effect=AssertionError("preview optimize should skip terrain sampling")), \
             patch("builtins.print"):
            response = spin_path_module.handle_spin_path_optimize(
                self.designer,
                {
                    "center": self.center,
                    "batteryMinutes": 18,
                    "batteries": 2,
                    "minHeight": 200,
                    "maxHeight": 400,
                    "formToTerrain": True,
                    "minExpansionDist": 200,
                    "maxExpansionDist": 200,
                    "overlapConfig": self.raw_overlap_config,
                },
                {},
            )

        self.assertEqual(response["statusCode"], 200)

    def test_rendered_path_follows_curved_turn_geometry(self):
        waypoint_records = [
            {"x": 0.0, "y": 0.0, "altitude": 120.0, "curve_size_meters": 0.0},
            {
                "x": 200.0,
                "y": 0.0,
                "altitude": 180.0,
                "curve_size_meters": 40.0 * spin_path_module.SpiralDesigner.FT2M,
            },
            {"x": 200.0, "y": 200.0, "altitude": 240.0, "curve_size_meters": 0.0},
        ]

        with patch("builtins.print"):
            designer = spin_path_module.SpiralDesigner()
        rendered_points = spin_path_module._build_rendered_local_path_points(waypoint_records, designer)

        self.assertGreater(len(rendered_points), 8)
        self.assertFalse(
            any(abs(point["x"] - 200.0) < 1e-6 and abs(point["y"]) < 1e-6 for point in rendered_points)
        )
        self.assertTrue(
            any(160.0 < point["x"] < 200.0 and 0.0 < point["y"] < 40.0 for point in rendered_points)
        )

    def test_export_limits_heading_deltas_and_preserves_spin_direction(self):
        export_data = self._build_export()
        preview_waypoints = export_data["previewWaypoints"]
        telemetry = export_data["telemetry"]

        heading_deltas = [
            (preview_waypoints[index + 1]["headingDeg"] - preview_waypoints[index]["headingDeg"]) % 360.0
            for index in range(len(preview_waypoints) - 1)
        ]

        self.assertTrue(heading_deltas)
        self.assertTrue(all(delta >= 0.0 for delta in heading_deltas))
        self.assertLessEqual(max(heading_deltas), 179.0 + 1e-6)
        self.assertLessEqual(telemetry["maxHeadingDeltaDeg"], 179.0 + 1e-6)
        self.assertAlmostEqual(telemetry["estimatedYawRateDegPerSec"], 90.0, places=3)

    def test_export_uses_min_to_max_altitude_profile(self):
        export_data = self._build_export()
        altitudes = [waypoint["altitudeFeet"] for waypoint in export_data["previewWaypoints"]]

        self.assertTrue(altitudes)
        self.assertAlmostEqual(altitudes[0], 120.0, places=2)
        self.assertAlmostEqual(altitudes[-1], 360.0, places=2)
        self.assertGreater(max(altitudes), 350.0)
        self.assertLess(min(altitudes), 130.0)
        self.assertGreater(altitudes[len(altitudes) // 2], altitudes[0])

    def test_export_handler_skips_google_elevation_when_terrain_is_off(self):
        with patch.object(self.designer, "get_elevation_feet", side_effect=AssertionError("should not fetch elevation")), \
             patch.object(self.designer, "get_elevations_feet_optimized", side_effect=AssertionError("should not batch fetch elevation")), \
             patch.object(self.designer, "adaptive_terrain_sampling", side_effect=AssertionError("should not terrain sample")), \
             patch("builtins.print"):
            response = spin_path_module.handle_spin_path_export_battery(
                self.designer,
                {
                    "center": self.center,
                    "slices": 2,
                    "N": 6,
                    "r0": 100,
                    "rHold": 1000,
                    "minHeight": 120,
                    "maxHeight": 360,
                    "formToTerrain": False,
                    "overlapConfig": self.raw_overlap_config,
                },
                "1",
                {},
            )

        self.assertEqual(response["statusCode"], 200)

    def test_stage_split_exports_keep_overlap_continuity_past_99_waypoints(self):
        export_data = self._build_export()
        stages = export_data["stages"]

        self.assertGreater(len(stages), 1)
        self.assertTrue(all(stage["waypointCount"] <= 99 for stage in stages))

        stage_one_rows = self._parse_csv_rows(stages[0]["csvText"])
        stage_two_rows = self._parse_csv_rows(stages[1]["csvText"])
        overlap_keys = ["latitude", "longitude", "altitude(ft)", "heading(deg)"]
        self.assertEqual(
            {key: stage_one_rows[-1][key] for key in overlap_keys},
            {key: stage_two_rows[0][key] for key in overlap_keys},
        )
        self.assertEqual(export_data["telemetry"]["stageWaypointCounts"][0], len(stage_one_rows))
        self.assertEqual(export_data["telemetry"]["stageWaypointCounts"][1], len(stage_two_rows))

    def test_stage_average_speed_tracks_stage_average_agl(self):
        export_data = self._build_export()

        stage_average_agl = export_data["telemetry"]["stageAverageAglFeet"]
        stage_average_speed = export_data["telemetry"]["stageAverageSpeedMph"]

        self.assertTrue(stage_average_agl)
        self.assertEqual(len(stage_average_agl), len(stage_average_speed))
        self.assertGreater(stage_average_speed[-1], stage_average_speed[0])
        self.assertEqual(export_data["stages"][0]["averageSpeedMph"], stage_average_speed[0])

    def test_split_stage_points_forces_outbound_inbound_split_under_limit(self):
        point_templates = [
            {
                "latitude": 39.7392 + (index * 0.0001),
                "longitude": -104.9903,
                "altitude": 120.0 + (index * 10.0),
                "curve_ft": 0.0,
                "gimbalpitchangle": -25,
                "distance_ft": float(index * 20),
            }
            for index in range(10)
        ]

        stage_sets = spin_path_module._split_real_path_stage_points(
            point_templates,
            stage_limit=99,
            overlap_rows=1,
            preferred_split_distance_ft=95.0,
        )

        self.assertEqual(len(stage_sets), 2)
        self.assertEqual(stage_sets[0][-1]["distance_ft"], stage_sets[1][0]["distance_ft"])
        self.assertLess(len(stage_sets[0]), 99)
        self.assertLess(len(stage_sets[1]), 99)

    def test_distance_trigger_mode_exports_distance_interval_without_extra_waypoints(self):
        raw_overlap_config = dict(self.raw_overlap_config)
        raw_overlap_config["captureIntervalUnit"] = "ft"
        raw_overlap_config["captureDistanceIntervalFt"] = 12.0
        overlap_config = spin_path_module._parse_real_path_overlap_config(raw_overlap_config)

        terrain_patches = self._patch_terrain_dependencies()
        with terrain_patches[0], terrain_patches[1], terrain_patches[2], terrain_patches[3]:
            export_data = spin_path_module._build_real_path_battery_export(
                designer=self.designer,
                params=self.params,
                center_str=self.center,
                battery_index=0,
                min_height=120.0,
                max_height=360.0,
                form_to_terrain=False,
                overlap_config=overlap_config,
            )

        stage_rows = self._parse_csv_rows(export_data["stages"][0]["csvText"])
        self.assertEqual(stage_rows[0]["photo_timeinterval"], "0")
        self.assertEqual(stage_rows[0]["photo_distinterval"], "12.0")
        self.assertEqual(stage_rows[-1]["photo_distinterval"], "0")


if __name__ == "__main__":
    unittest.main()
