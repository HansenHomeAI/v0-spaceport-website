import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "run_sfm_benchmark.py"
SPEC = importlib.util.spec_from_file_location("run_sfm_benchmark_test_module", MODULE_PATH)
run_sfm_benchmark = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = run_sfm_benchmark
SPEC.loader.exec_module(run_sfm_benchmark)


class RunSfmBenchmarkTests(unittest.TestCase):
    def test_parse_args_accepts_hierarchical_stock_mode(self):
        with mock.patch.object(
            sys,
            "argv",
            [
                "run_sfm_benchmark.py",
                "--input-s3-uri",
                "s3://bucket/input.zip",
                "--mode",
                "hierarchical-stock",
            ],
        ):
            args = run_sfm_benchmark.parse_args()

        self.assertEqual(args.mode, "hierarchical-stock")
        self.assertEqual(args.input_s3_uri, "s3://bucket/input.zip")

    def test_build_summary_row_includes_hierarchical_metrics(self):
        summary = run_sfm_benchmark.build_summary_row(
            job_name="bench-123",
            mode="hierarchical-stock",
            input_s3_uri="s3://bucket/input.zip",
            metadata={
                "colmap_pipeline_mode": "hierarchical_stock",
                "processing_time_seconds": 123.4,
                "hierarchical_mapper_seconds": 77.7,
                "hierarchical_partition_seconds": 10.0,
                "hierarchical_leaf_reconstruction_seconds": 50.0,
                "hierarchical_merge_seconds": 17.7,
                "images_registered": 42,
                "dataset_image_count": 50,
                "points_3d": 1000,
                "final_points_per_registered_image": 23.81,
            },
        )

        self.assertEqual(summary["colmap_pipeline_mode"], "hierarchical_stock")
        self.assertEqual(summary["hierarchical_mapper_seconds"], 77.7)
        self.assertEqual(summary["hierarchical_partition_seconds"], 10.0)
        self.assertEqual(summary["hierarchical_leaf_reconstruction_seconds"], 50.0)
        self.assertEqual(summary["hierarchical_merge_seconds"], 17.7)


if __name__ == "__main__":
    unittest.main()
