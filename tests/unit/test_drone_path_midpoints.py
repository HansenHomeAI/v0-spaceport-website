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
    # The unit tests don't exercise network calls; stub requests so the module imports
    # cleanly in environments without that dependency.
    fake_requests = types.SimpleNamespace(get=lambda *args, **kwargs: None)
    sys.modules["requests"] = fake_requests

SPEC = importlib.util.spec_from_file_location("drone_path_lambda", MODULE_PATH)
drone_path_module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(drone_path_module)


class DronePathMidpointSamplingTests(unittest.TestCase):
    def setUp(self):
        # SpiralDesigner prints API key info during init; silence to avoid leaking env details in CI logs.
        with patch("builtins.print"):
            self.designer = drone_path_module.SpiralDesigner()

    def _build(self, slices: int, N: int = 6):
        params = {"slices": slices, "N": N, "r0": 100, "rHold": 1000}
        with patch("builtins.print"):
            return self.designer.build_slice(0, params)

    def test_waypoint_counts_match_expected_for_low_slices(self):
        # Derived expected totals:
        # start(1)
        # outbound: N * (midpoints_per_segment + bounce(1))
        # hold: midpoints_per_segment + hold_end(1)
        # first inbound: midpoints_per_segment
        # inbound: N * bounce(1) + (N-1) * midpoints_per_segment
        cases = [
            # slices, midpoints_per_segment, expected_total
            (1, 5, 79),
            (2, 2, 40),
            (4, 1, 27),
        ]

        for slices, midpoints, expected_total in cases:
            with self.subTest(slices=slices):
                waypoints = self._build(slices=slices, N=6)
                self.assertEqual(len(waypoints), expected_total)

                outbound_mids = [wp for wp in waypoints if str(wp.get("phase", "")).startswith("outbound_mid_")]
                inbound_mids = [wp for wp in waypoints if str(wp.get("phase", "")).startswith("inbound_mid_")]
                hold_mids = [wp for wp in waypoints if str(wp.get("phase", "")) .startswith("hold_mid")]

                self.assertEqual(len(outbound_mids), 6 * midpoints)
                # inbound mids include "inbound_mid_0_..." for the initial segment and then
                # (N-1) segments each with midpoints_per_segment.
                self.assertEqual(len(inbound_mids), midpoints + (6 - 1) * midpoints)
                self.assertEqual(len(hold_mids), midpoints)

    def test_single_slice_optimizer_respects_waypoint_budget(self):
        with patch("builtins.print"):
            optimized = self.designer.optimize_spiral_for_battery(
                target_battery_minutes=20,
                num_batteries=1,
                center_lat=37.1972,
                center_lon=-113.6187,
            )

        waypoint_budget = self.designer.MAX_TOTAL_WAYPOINTS - self.designer.RESERVED_SAFETY_WAYPOINTS
        estimated_waypoints = self.designer.estimate_slice_waypoint_count(1, int(optimized["N"]))

        self.assertLessEqual(int(optimized["N"]), self.designer.max_bounces_for_waypoint_budget(1))
        self.assertLessEqual(estimated_waypoints, waypoint_budget)
        self.assertGreater(float(optimized["rHold"]), float(optimized["r0"]))


if __name__ == "__main__":
    unittest.main()
