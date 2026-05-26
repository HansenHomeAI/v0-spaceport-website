import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "run_tiled_3dgs_benchmark.py"
SPEC = importlib.util.spec_from_file_location("run_tiled_3dgs_benchmark_test_module", MODULE_PATH)
benchmark = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = benchmark
SPEC.loader.exec_module(benchmark)


class Tiled3DGSBenchmarkLauncherTests(unittest.TestCase):
    def test_nested_string_reads_metadata_paths(self):
        payload = {"planner_manifest": {"source": "s3://bucket/planner.json"}}

        self.assertEqual(
            benchmark.nested_string(payload, ("planner_manifest", "source")),
            "s3://bucket/planner.json",
        )
        self.assertEqual(benchmark.nested_string(payload, ("planner_manifest", "missing")), "")
        self.assertEqual(benchmark.nested_string(payload, ("planner_manifest", "source", "bad")), "")

    def test_s3_json_from_metadata_uri_follows_first_existing_reference(self):
        calls = []
        original = benchmark.s3_json_or_none

        def fake_s3_json_or_none(uri):
            calls.append(uri)
            if uri.endswith("missing.json"):
                return None
            return {"loaded_from": uri}

        try:
            benchmark.s3_json_or_none = fake_s3_json_or_none
            payload = {
                "planner_manifest": {"source": "s3://bucket/missing.json"},
                "chunk_planner_manifest_uri": "s3://bucket/planner.json",
            }

            self.assertEqual(
                benchmark.s3_json_from_metadata_uri(
                    payload,
                    ("planner_manifest", "source"),
                    ("chunk_planner_manifest_uri",),
                ),
                {"loaded_from": "s3://bucket/planner.json"},
            )
            self.assertEqual(calls, ["s3://bucket/missing.json", "s3://bucket/planner.json"])
        finally:
            benchmark.s3_json_or_none = original


if __name__ == "__main__":
    unittest.main()
