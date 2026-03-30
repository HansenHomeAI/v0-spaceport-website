import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "prepare_sequential_benchmark_subset.py"
SPEC = importlib.util.spec_from_file_location("prepare_sequential_subset_test_module", MODULE_PATH)
prepare_subset = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = prepare_subset
SPEC.loader.exec_module(prepare_subset)


class SequentialBenchmarkSubsetTests(unittest.TestCase):
    def test_sort_capture_records_prefers_exif_time_then_filename(self):
        records = [
            {"file_name": "IMG_0004.JPG", "capture_time": "2026:03:30 09:00:03"},
            {"file_name": "IMG_0002.JPG", "capture_time": "2026:03:30 09:00:01"},
            {"file_name": "IMG_0003.JPG", "capture_time": "2026:03:30 09:00:02"},
            {"file_name": "IMG_0001.JPG", "capture_time": ""},
        ]

        ordered = prepare_subset.sort_capture_records(records)

        self.assertEqual(
            [record["file_name"] for record in ordered],
            ["IMG_0002.JPG", "IMG_0003.JPG", "IMG_0004.JPG", "IMG_0001.JPG"],
        )

    def test_sort_capture_records_falls_back_to_filename_when_exif_missing(self):
        records = [
            {"file_name": "DJI_0010.JPG", "capture_time": ""},
            {"file_name": "DJI_0002.JPG", "capture_time": ""},
            {"file_name": "DJI_0001.JPG", "capture_time": ""},
        ]

        ordered = prepare_subset.sort_capture_records(records)

        self.assertEqual(
            [record["file_name"] for record in ordered],
            ["DJI_0001.JPG", "DJI_0002.JPG", "DJI_0010.JPG"],
        )


if __name__ == "__main__":
    unittest.main()
