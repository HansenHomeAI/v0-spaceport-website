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


class DronePathBoundaryPlannerTests(unittest.TestCase):
    def setUp(self):
        with patch("builtins.print"):
            self.designer = drone_path_module.SpiralDesigner()

        self.center = {"lat": 39.7392, "lon": -104.9903}
        self.circle_boundary = {
            "version": 1,
            "enabled": True,
            "centerLat": self.center["lat"],
            "centerLng": self.center["lon"],
            "majorRadiusFt": 2200.0,
            "minorRadiusFt": 2200.0,
            "rotationDeg": 0.0,
        }
        self.oblong_boundary = {
            "version": 1,
            "enabled": True,
            "centerLat": self.center["lat"],
            "centerLng": self.center["lon"],
            "majorRadiusFt": 5200.0,
            "minorRadiusFt": 1400.0,
            "rotationDeg": 18.0,
        }

    def _plan(self, boundary, *, battery_minutes=20, batteries=3, **extra_params):
        params = {"slices": batteries, "r0": 200.0, **extra_params}
        with patch("builtins.print"):
            return self.designer.plan_boundary_mission(battery_minutes, batteries, boundary, params)

    def _preview_paths(self, boundary, plan, *, batteries=3):
        params = {"slices": batteries, "r0": 200.0}
        with patch("builtins.print"):
            return self.designer.generate_boundary_preview_paths(params, boundary, plan)

    def _inside_boundary(self, lat, lon, boundary):
        local = self.designer.lat_lon_to_xy(lat, lon, boundary["centerLat"], boundary["centerLng"])
        theta = -drone_path_module.math.radians(boundary["rotationDeg"])
        x = local["x"] * drone_path_module.math.cos(theta) - local["y"] * drone_path_module.math.sin(theta)
        y = local["x"] * drone_path_module.math.sin(theta) + local["y"] * drone_path_module.math.cos(theta)
        value = (x * x) / (boundary["majorRadiusFt"] ** 2) + (y * y) / (boundary["minorRadiusFt"] ** 2)
        return value <= 1.0005

    def test_circle_boundary_returns_full_fit(self):
        plan = self._plan(self.circle_boundary, battery_minutes=24, batteries=4)

        self.assertEqual(plan["fitStatus"], "full")
        self.assertAlmostEqual(plan["coverageRatio"], 1.0, places=2)
        self.assertEqual(len(plan["batteries"]), 4)
        self.assertTrue(all(entry["sweepAngleDeg"] > 0 for entry in plan["batteries"]))

    def test_oblong_boundary_returns_unequal_sweeps(self):
        plan = self._plan(self.oblong_boundary, battery_minutes=18, batteries=4)
        sweeps = [round(entry["sweepAngleDeg"], 2) for entry in plan["batteries"]]

        self.assertGreater(len(set(sweeps)), 1)
        self.assertTrue(any(entry["bounceCount"] < max(item["bounceCount"] for item in plan["batteries"]) for entry in plan["batteries"]))

    def test_large_boundary_reduces_bounce_count(self):
        moderate = self._plan(self.circle_boundary, battery_minutes=18, batteries=3)
        stretched = self._plan({**self.oblong_boundary, "majorRadiusFt": 7600.0, "minorRadiusFt": 1100.0}, battery_minutes=18, batteries=3)

        self.assertGreaterEqual(max(entry["bounceCount"] for entry in moderate["batteries"]),
                                max(entry["bounceCount"] for entry in stretched["batteries"]))
        self.assertGreaterEqual(moderate["coverageRatio"], stretched["coverageRatio"])

    def test_extreme_boundary_can_drop_to_one_bounce(self):
        extreme = self._plan(
            {
                **self.oblong_boundary,
                "majorRadiusFt": 9800.0,
                "minorRadiusFt": 700.0,
            },
            battery_minutes=12,
            batteries=2,
        )

        self.assertTrue(any(entry["bounceCount"] == 1 for entry in extreme["batteries"]))

    def test_impossible_boundary_returns_best_effort(self):
        impossible = self._plan(
            {
                **self.oblong_boundary,
                "majorRadiusFt": 8000.0,
                "minorRadiusFt": 900.0,
            },
            battery_minutes=10,
            batteries=2,
        )

        self.assertEqual(impossible["fitStatus"], "best_effort")
        self.assertLess(impossible["coverageRatio"], 1.0)
        self.assertGreater(len(impossible["batteries"]), 0)

    def test_preview_and_csv_stay_inside_boundary_and_under_time_limit(self):
        plan = self._plan(self.oblong_boundary, battery_minutes=20, batteries=3)
        preview_paths = self._preview_paths(self.oblong_boundary, plan, batteries=3)
        self.assertEqual(len(preview_paths), len(plan["batteries"]))

        with patch.object(self.designer, "get_elevation_feet", return_value=5000.0), \
             patch.object(self.designer, "get_elevations_feet_optimized", side_effect=lambda locations: [5000.0] * len(locations)), \
             patch.object(self.designer, "adaptive_terrain_sampling", return_value=[]), \
             patch("builtins.print"):
            for entry in plan["batteries"]:
                csv_text = self.designer.generate_battery_csv(
                    {"slices": 3, "r0": 200.0},
                    f'{self.center["lat"]}, {self.center["lon"]}',
                    entry["batteryIndex"] - 1,
                    min_height=120.0,
                    max_height=300.0,
                    boundary=self.oblong_boundary,
                    boundary_plan=plan,
                )

                for line in csv_text.splitlines()[1:]:
                    parts = line.split(",")
                    lat = float(parts[0])
                    lon = float(parts[1])
                    self.assertTrue(self._inside_boundary(lat, lon, self.oblong_boundary))

                waypoints = self.designer.build_boundary_slice(
                    entry["batteryIndex"],
                    3,
                    self.oblong_boundary,
                    entry["startAngleDeg"],
                    entry["sweepAngleDeg"],
                    entry["bounceCount"],
                    {"slices": 3, "r0": 200.0},
                )
                self.assertLessEqual(
                    self.designer.estimate_generated_slice_time_minutes(waypoints),
                    20 * 0.98 + 0.01,
                )


if __name__ == "__main__":
    unittest.main()
