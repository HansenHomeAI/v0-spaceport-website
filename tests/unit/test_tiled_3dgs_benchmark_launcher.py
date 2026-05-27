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

    def test_input_image_coverage_gate_blocks_missing_leaf_images(self):
        manifest = {
            "tiles": [
                {
                    "tile_id": "tile_07",
                    "base_camera_ids": ["DJI_0001.JPG", "DJI_0002.JPG"],
                    "border_camera_ids": ["DJI_0003.JPG"],
                    "context_camera_ids": ["DJI_0004.JPG"],
                }
            ]
        }
        stage = benchmark.BenchmarkStage(
            stage_name="T0_tile_07",
            stage_type="train",
            training_mode="leaf_tile",
            tile_id="tile_07",
            output_s3_uri="s3://bucket/out",
        )

        gate = benchmark.build_input_image_coverage_gate(
            colmap_s3_uri="s3://bucket/colmap",
            tile_manifest=manifest,
            view_buckets={},
            stages=[stage],
            available_image_names={"DJI_0001.JPG", "DJI_0003.JPG"},
        )

        self.assertEqual(gate["status"], "blocked")
        self.assertEqual(gate["blocked_stage_count"], 1)
        self.assertEqual(gate["missing_image_count"], 2)
        self.assertEqual(
            gate["stages"][0]["missing_images_sample"],
            ["DJI_0002.JPG", "DJI_0004.JPG"],
        )

    def test_submit_guardrail_reports_input_image_coverage_blocker(self):
        args = type(
            "Args",
            (),
            {
                "submit": True,
                "max_estimated_usd": 1.0,
                "experiment_id": "coverage-test",
                "v18_review_manifest_s3_uri": "s3://bucket/v18.json",
                "enable_checkpoints": False,
                "enable_spot": False,
                "checkpoint_resume_s3_uri": "",
                "reuse_tile_cache": False,
                "orchestration_mode": "fanout",
                "skip_merge": True,
                "skip_review": True,
            },
        )()
        summary = {
            "visual_qa_plan": {"enabled": True},
            "viewer_smoke_plan": {"enabled": True},
            "early_visual_smoke_plan": {
                "abort_on_failure": True,
                "checkpoint_steps": [200],
                "sentinel_cameras": ["DJI_0001.JPG"],
                "checkpoint_s3_uris": {"tile_07": "s3://bucket/checkpoints"},
                "checkpoint_probe_command_template": "probe",
                "visual_gate_command_template": "gate",
                "stop_command_template": "stop",
            },
            "cost_estimate": {"estimated_usd": 0.1, "stage_estimates": []},
            "sagemaker_env_value_length_violations": [],
            "leaf_density_cap_preflight_violations": [],
            "input_image_coverage_gate": {
                "status": "blocked",
                "stages": [{"stage_name": "T0_tile_07", "missing_image_count": 2}],
            },
            "stages": [
                {
                    "stage_type": "train",
                    "training_mode": "leaf_tile",
                }
            ],
        }

        with self.assertRaisesRegex(RuntimeError, "input image coverage gate blocked submit"):
            benchmark.validate_submit_guardrails(args, summary)


if __name__ == "__main__":
    unittest.main()
