"""Regression for Catmull–Rom scalar used by Canyon-Vista path (ported to TS)."""
import unittest


def catmull_rom_scalar(p0, p1, p2, p3, t):
    t2 = t * t
    t3 = t2 * t
    return 0.5 * (
        (2 * p1)
        + (-p0 + p2) * t
        + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
        + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
    )


class TestCatmullRom(unittest.TestCase):
    def test_endpoints(self):
        self.assertAlmostEqual(catmull_rom_scalar(0, 1, 2, 3, 0.0), 1.0)
        self.assertAlmostEqual(catmull_rom_scalar(0, 1, 2, 3, 1.0), 2.0)

    def test_midpoint_in_range(self):
        v = catmull_rom_scalar(0, 0.5, 1.0, 1.5, 0.5)
        self.assertGreaterEqual(v, 0.0)
        self.assertLessEqual(v, 1.5)


if __name__ == "__main__":
    unittest.main()
