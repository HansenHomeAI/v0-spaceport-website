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

    def _generate_battery_csv(self, params, battery_index, spin_mode=False):
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

    def test_spin_mode_also_applies_to_battery_csv(self):
        params = {"slices": 2, "N": 6, "r0": 100, "rHold": 1000}

        base_rows = self._parse_rows(self._generate_battery_csv(params, battery_index=0, spin_mode=False))
        spin_rows = self._parse_rows(self._generate_battery_csv(params, battery_index=0, spin_mode=True))

        self.assertGreater(len(spin_rows), len(base_rows))
        self.assertLessEqual(len(spin_rows), self.designer.MAX_TOTAL_WAYPOINTS)

        photo_intervals = [float(row["photo_timeinterval"]) for row in spin_rows]
        self.assertTrue(all(abs(v - 2.0) < 1e-9 for v in photo_intervals[:-1]))
        self.assertEqual(photo_intervals[-1], 0.0)


if __name__ == "__main__":
    unittest.main()
