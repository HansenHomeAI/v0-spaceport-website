import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "prepare_spatial_heading_benchmark_subset.py"
SPEC = importlib.util.spec_from_file_location("prepare_spatial_heading_subset_test_module", MODULE_PATH)
prepare_subset = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = prepare_subset
SPEC.loader.exec_module(prepare_subset)


class SpatialHeadingBenchmarkSubsetTests(unittest.TestCase):
    def test_select_spatial_heading_subset_prefers_spatial_neighborhood_over_capture_time(self):
        records = [
            {
                "file_name": "seed.jpg",
                "capture_time": "2026:04:01 10:00:00",
                "local_x_m": 0.0,
                "local_y_m": 0.0,
                "heading_deg": 0.0,
            },
            {
                "file_name": "near_same_heading.jpg",
                "capture_time": "2026:04:01 10:05:00",
                "local_x_m": 10.0,
                "local_y_m": 0.0,
                "heading_deg": 2.0,
            },
            {
                "file_name": "far_earlier.jpg",
                "capture_time": "2026:04:01 09:00:00",
                "local_x_m": 400.0,
                "local_y_m": 0.0,
                "heading_deg": 0.0,
            },
        ]

        selected = prepare_subset.select_spatial_heading_subset(
            records,
            count=2,
            seed_image="seed.jpg",
            heading_weight=0.6,
        )

        self.assertEqual(
            [record["file_name"] for record in selected],
            ["seed.jpg", "near_same_heading.jpg"],
        )

    def test_select_spatial_heading_subset_penalizes_heading_mismatch(self):
        records = [
            {
                "file_name": "seed.jpg",
                "capture_time": "2026:04:01 10:00:00",
                "local_x_m": 0.0,
                "local_y_m": 0.0,
                "heading_deg": 0.0,
            },
            {
                "file_name": "closer_wrong_heading.jpg",
                "capture_time": "2026:04:01 10:00:01",
                "local_x_m": 20.0,
                "local_y_m": 0.0,
                "heading_deg": 180.0,
            },
            {
                "file_name": "slightly_farther_right_heading.jpg",
                "capture_time": "2026:04:01 10:00:02",
                "local_x_m": 25.0,
                "local_y_m": 0.0,
                "heading_deg": 5.0,
            },
        ]

        selected = prepare_subset.select_spatial_heading_subset(
            records,
            count=2,
            seed_image="seed.jpg",
            heading_weight=1.0,
        )

        self.assertEqual(
            [record["file_name"] for record in selected],
            ["seed.jpg", "slightly_farther_right_heading.jpg"],
        )


if __name__ == "__main__":
    unittest.main()
