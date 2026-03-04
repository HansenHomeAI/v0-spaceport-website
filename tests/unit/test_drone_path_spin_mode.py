import csv
import io
import importlib.util
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


class DronePathSpinModeTests(unittest.TestCase):
    def setUp(self):
        with patch("builtins.print"):
            self.designer = drone_path_module.SpiralDesigner()
        self.center = "37.1972,-113.6187"

    def _generate_csv(self, params, spin_mode=False):
        with patch.object(self.designer, "get_elevation_feet", return_value=1000.0), \
             patch.object(self.designer, "get_elevations_feet_optimized", side_effect=lambda locs: [1000.0] * len(locs)), \
             patch.object(self.designer, "adaptive_terrain_sampling", return_value=[]), \
             patch("builtins.print"):
            return self.designer.generate_csv(
                params=params,
                center_str=self.center,
                min_height=120.0,
                max_height=None,
                spin_mode=spin_mode,
            )

    def _generate_battery_csv(self, params, battery_index, spin_mode=False, export_part="single"):
        with patch.object(self.designer, "get_elevation_feet", return_value=1000.0), \
             patch.object(self.designer, "get_elevations_feet_optimized", side_effect=lambda locs: [1000.0] * len(locs)), \
             patch.object(self.designer, "adaptive_terrain_sampling", return_value=[]), \
             patch("builtins.print"):
            return self.designer.generate_battery_csv(
                params=params,
                center_str=self.center,
                battery_index=battery_index,
                min_height=120.0,
                max_height=None,
                spin_mode=spin_mode,
                export_part=export_part,
            )

    def _build_battery_export(self, params, battery_index, spin_mode=False, export_part="single"):
        with patch.object(self.designer, "get_elevation_feet", return_value=1000.0), \
             patch.object(self.designer, "get_elevations_feet_optimized", side_effect=lambda locs: [1000.0] * len(locs)), \
             patch.object(self.designer, "adaptive_terrain_sampling", return_value=[]), \
             patch("builtins.print"):
            return self.designer.build_battery_csv_export(
                params=params,
                center_str=self.center,
                battery_index=battery_index,
                min_height=120.0,
                max_height=None,
                spin_mode=spin_mode,
                export_part=export_part,
            )

    def _parse_rows(self, csv_text):
        return list(csv.DictReader(io.StringIO(csv_text)))

    def _segment_distances_ft(self, rows):
        distances = []
        for i in range(len(rows) - 1):
            lat1 = float(rows[i]["latitude"])
            lon1 = float(rows[i]["longitude"])
            lat2 = float(rows[i + 1]["latitude"])
            lon2 = float(rows[i + 1]["longitude"])
            distance_ft = self.designer.haversine_distance(lat1, lon1, lat2, lon2) * 3.28084
            distances.append(distance_ft)
        return distances

    def test_spin_mode_uses_waypoint_budget_and_limits_rotation_rate(self):
        params = {"slices": 1, "N": 6, "r0": 100, "rHold": 1000}

        base_rows = self._parse_rows(self._generate_csv(params, spin_mode=False))
        spin_rows = self._parse_rows(self._generate_csv(params, spin_mode=True))

        self.assertEqual(len(base_rows), 79)
        self.assertEqual(len(spin_rows), self.designer.MAX_TOTAL_WAYPOINTS)

        base_max_gap = max(self._segment_distances_ft(base_rows))
        spin_distances = self._segment_distances_ft(spin_rows)
        spin_max_gap = max(spin_distances)
        self.assertLessEqual(spin_max_gap, base_max_gap)

        headings = [float(row["heading(deg)"]) for row in spin_rows]
        heading_deltas = [
            (headings[i + 1] - headings[i]) % 360.0 for i in range(len(headings) - 1)
        ]
        self.assertLessEqual(max(heading_deltas), self.designer.SPIN_MAX_HEADING_DELTA_DEG + 1e-6)

        angular_rates = []
        for delta, distance_ft in zip(heading_deltas, spin_distances):
            if distance_ft <= 1e-6:
                continue
            segment_seconds = distance_ft / self.designer.SPEED_FT_PER_SEC
            angular_rates.append(delta / segment_seconds)
        self.assertTrue(angular_rates)
        self.assertLessEqual(
            max(angular_rates),
            self.designer.MAX_ANGULAR_RATE_DEG_PER_SEC + 0.5,
        )

        gimbal_pitches = [int(float(row["gimbalpitchangle"])) for row in spin_rows]
        self.assertTrue(all(-35 <= angle <= -15 for angle in gimbal_pitches))
        self.assertGreaterEqual(len(set(gimbal_pitches)), 8)

        photo_intervals = [float(row["photo_timeinterval"]) for row in spin_rows]
        self.assertTrue(all(abs(v - 2.0) < 1e-9 for v in photo_intervals[:-1]))
        self.assertEqual(photo_intervals[-1], 0.0)

        # Spin mode: no POI (0) so Litchi uses per-waypoint headings
        poi_lats = [float(row["poi_latitude"]) for row in spin_rows]
        self.assertTrue(all(v == 0 for v in poi_lats), "Spin mode should have poi_latitude=0")

    def test_spin_mode_battery_single_and_split_exports(self):
        params = {"slices": 2, "N": 6, "r0": 100, "rHold": 1000}

        base_rows = self._parse_rows(self._generate_battery_csv(params, battery_index=0, spin_mode=False))
        single_rows = self._parse_rows(
            self._generate_battery_csv(params, battery_index=0, spin_mode=True, export_part="single")
        )
        combined_rows = self._parse_rows(
            self._generate_battery_csv(params, battery_index=0, spin_mode=True, export_part="combined")
        )
        part_one_rows = self._parse_rows(
            self._generate_battery_csv(params, battery_index=0, spin_mode=True, export_part="part1")
        )
        part_two_rows = self._parse_rows(
            self._generate_battery_csv(params, battery_index=0, spin_mode=True, export_part="part2")
        )

        self.assertGreater(len(single_rows), len(base_rows))
        self.assertLessEqual(len(single_rows), self.designer.MAX_EXPORT_WAYPOINTS)

        self.assertGreater(len(combined_rows), self.designer.MAX_EXPORT_WAYPOINTS)
        self.assertLessEqual(len(combined_rows), self.designer.MAX_SPLIT_SPIN_WAYPOINTS)
        self.assertLessEqual(len(part_one_rows), self.designer.MAX_EXPORT_WAYPOINTS)
        self.assertLessEqual(len(part_two_rows), self.designer.MAX_EXPORT_WAYPOINTS)

        overlap_keys = ["latitude", "longitude", "altitude(ft)", "heading(deg)"]
        self.assertEqual(
            {key: part_one_rows[-1][key] for key in overlap_keys},
            {key: part_two_rows[0][key] for key in overlap_keys},
        )

        rebuilt_rows = part_one_rows[:-1] + part_two_rows
        self.assertEqual(combined_rows, rebuilt_rows)

        self.assertNotEqual(float(part_two_rows[1]["heading(deg)"]), 0.0)
        self.assertEqual(float(part_one_rows[-1]["photo_timeinterval"]), 0.0)
        self.assertEqual(float(part_two_rows[-1]["photo_timeinterval"]), 0.0)
        self.assertGreater(float(part_two_rows[0]["photo_timeinterval"]), 0.0)

        export_data = self._build_battery_export(params, battery_index=0, spin_mode=True, export_part="combined")
        telemetry = export_data["telemetry"]
        self.assertIsNotNone(telemetry)
        self.assertGreater(telemetry["combined_waypoints"], self.designer.MAX_EXPORT_WAYPOINTS)
        self.assertGreater(telemetry["max_segment_feet"], 0.0)
        self.assertGreater(telemetry["estimated_rate_deg_s"], 0.0)
        self.assertAlmostEqual(
            telemetry["min_blur_segment_feet"],
            self.designer.SPIN_MAX_HEADING_DELTA_DEG * self.designer.SPEED_FT_PER_SEC / self.designer.MAX_ANGULAR_RATE_DEG_PER_SEC,
            places=2,
        )


    def test_normal_mode_headings_point_at_center(self):
        """Normal mode headings should face the POI (spiral center), not the path direction."""
        import math
        params = {"slices": 2, "N": 6, "r0": 100, "rHold": 1000}
        rows = self._parse_rows(self._generate_battery_csv(params, battery_index=0, spin_mode=False))

        center_lat, center_lon = 37.1972, -113.6187

        for row in rows:
            poi_lat = float(row["poi_latitude"])
            poi_lon = float(row["poi_longitude"])
            self.assertAlmostEqual(poi_lat, center_lat, places=3, msg="Normal mode POI lat should be center")
            self.assertAlmostEqual(poi_lon, center_lon, places=3, msg="Normal mode POI lon should be center")

        for row in rows:
            wp_lat = float(row["latitude"])
            wp_lon = float(row["longitude"])
            heading = float(row["heading(deg)"])
            dlon = math.radians(center_lon - wp_lon)
            lat1 = math.radians(wp_lat)
            lat2 = math.radians(center_lat)
            x = math.sin(dlon) * math.cos(lat2)
            y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
            bearing = (math.degrees(math.atan2(x, y)) + 360) % 360
            diff = abs(heading - bearing)
            if diff > 180:
                diff = 360 - diff
            self.assertLessEqual(diff, 1.0, f"Heading {heading} should match bearing to center {bearing:.1f}")

    def test_spin_mode_poi_zero_and_headings_rotate(self):
        """Spin mode must have POI=0 and headings that actually rotate."""
        params = {"slices": 2, "N": 6, "r0": 100, "rHold": 1000}
        rows = self._parse_rows(self._generate_battery_csv(params, battery_index=0, spin_mode=True))

        for row in rows:
            self.assertEqual(float(row["poi_latitude"]), 0.0, "Spin mode poi_latitude must be 0")
            self.assertEqual(float(row["poi_longitude"]), 0.0, "Spin mode poi_longitude must be 0")

        headings = [float(row["heading(deg)"]) for row in rows]
        self.assertGreaterEqual(len(set(headings)), len(rows) // 2, "Spin headings should have many unique values")

    def test_battery_export_part_validation(self):
        params = {"slices": 2, "N": 6, "r0": 100, "rHold": 1000}
        body = {
            **params,
            "center": self.center,
            "spinMode": False,
            "minHeight": 120.0,
        }

        invalid_response = drone_path_module.handle_battery_csv_download(
            self.designer,
            {**body, "exportPart": "invalid"},
            "1",
            {},
        )
        self.assertEqual(invalid_response["statusCode"], 400)

        for export_part in ("part1", "part2", "combined"):
            response = drone_path_module.handle_battery_csv_download(
                self.designer,
                {**body, "exportPart": export_part},
                "1",
                {},
            )
            self.assertEqual(response["statusCode"], 400)

    def test_battery_handler_exposes_split_spin_headers(self):
        params = {"slices": 2, "N": 6, "r0": 100, "rHold": 1000}
        body = {
            **params,
            "center": self.center,
            "spinMode": True,
            "exportPart": "part1",
            "minHeight": 120.0,
        }

        with patch.object(self.designer, "get_elevation_feet", return_value=1000.0), \
             patch.object(self.designer, "get_elevations_feet_optimized", side_effect=lambda locs: [1000.0] * len(locs)), \
             patch.object(self.designer, "adaptive_terrain_sampling", return_value=[]), \
             patch("builtins.print"):
            response = drone_path_module.handle_battery_csv_download(
                self.designer,
                body,
                "1",
                {"Access-Control-Allow-Origin": "*"},
            )

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["headers"]["X-Spin-Export-Part"], "part1")
        self.assertEqual(response["headers"]["X-Spin-Mode-Applied"], "true")
        self.assertEqual(response["headers"]["X-POI-Used"], "0,0")
        self.assertIn("X-Spin-Combined-Waypoints", response["headers"])
        self.assertIn("X-Spin-Max-Segment-Feet", response["headers"])
        self.assertIn("X-Spin-Estimated-Rate-Deg-S", response["headers"])
        self.assertIn("X-Spin-Min-Blur-Segment-Feet", response["headers"])


if __name__ == "__main__":
    unittest.main()
