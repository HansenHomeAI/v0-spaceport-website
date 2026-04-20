import importlib.util
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "run_sfm_benchmark.py"
SPEC = importlib.util.spec_from_file_location("run_sfm_benchmark_test_module", MODULE_PATH)
run_sfm_benchmark = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(run_sfm_benchmark)


class ParseArgsTests(unittest.TestCase):
    def test_parse_args_accepts_explicit_chunk_hybrid_flags(self) -> None:
        argv = [
            "run_sfm_benchmark.py",
            "--input-s3-uri",
            "s3://bucket/input.zip",
            "--mode",
            "chunked",
            "--chunk-leaf-mapper",
            "global",
            "--chunk-recovery-mapper",
            "incremental",
            "--chunk-merge-strategy",
            "hierarchical",
            "--chunk-hierarchical-merge-fanin",
            "2",
        ]
        with mock.patch("sys.argv", argv):
            args = run_sfm_benchmark.parse_args()

        self.assertEqual(args.mode, "chunked")
        self.assertEqual(args.chunk_leaf_mapper, "global")
        self.assertEqual(args.chunk_recovery_mapper, "incremental")
        self.assertEqual(args.chunk_merge_strategy, "hierarchical")
        self.assertEqual(args.chunk_hierarchical_merge_fanin, 2)


class BuildEnvironmentTests(unittest.TestCase):
    def test_build_environment_sets_chunk_hybrid_envs(self) -> None:
        args = run_sfm_benchmark.parse_args.__globals__["argparse"].Namespace(
            env=["EXTRA_FLAG=1"],
            mode="chunked",
            subset_strategy="geometry_mix",
            chunk_leaf_mapper="global",
            chunk_recovery_mapper="incremental",
            chunk_merge_strategy="hierarchical",
            chunk_hierarchical_merge_fanin=2,
        )

        environment = run_sfm_benchmark.build_environment(args)

        self.assertEqual(environment["COLMAP_ENABLE_SPATIAL_CHUNKING"], "1")
        self.assertEqual(environment["COLMAP_CHUNK_LEAF_MAPPER_MODE"], "global")
        self.assertEqual(environment["COLMAP_CHUNK_RECOVERY_MAPPER_MODE"], "incremental")
        self.assertEqual(environment["COLMAP_CHUNK_MERGE_STRATEGY"], "hierarchical")
        self.assertEqual(environment["COLMAP_CHUNK_HIERARCHICAL_MERGE_FANIN"], "2")
        self.assertEqual(environment["EXTRA_FLAG"], "1")

    def test_build_environment_defaults_chunking_off_for_monolithic(self) -> None:
        args = run_sfm_benchmark.parse_args.__globals__["argparse"].Namespace(
            env=[],
            mode="monolithic",
            subset_strategy="first_portion_by_exif_datetime_else_filename",
            chunk_leaf_mapper="",
            chunk_recovery_mapper="",
            chunk_merge_strategy="",
            chunk_hierarchical_merge_fanin=None,
        )

        environment = run_sfm_benchmark.build_environment(args)

        self.assertEqual(environment["COLMAP_ENABLE_SPATIAL_CHUNKING"], "0")
        self.assertNotIn("COLMAP_CHUNK_LEAF_MAPPER_MODE", environment)


if __name__ == "__main__":
    unittest.main()
