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
    def _single_leaf_stages(self, *, extra_env=None, downscale_factor=1):
        manifest = {
            "tiles": [
                {
                    "tile_id": "tile_00",
                    "base_camera_ids": ["DJI_0001.JPG", "DJI_0002.JPG"],
                    "border_camera_ids": ["DJI_0003.JPG"],
                    "context_camera_ids": ["DJI_0004.JPG"],
                }
            ]
        }
        return benchmark.build_benchmark_stages(
            manifest=manifest,
            branch_name="agent-test",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="hash-test",
            include_monolithic=False,
            include_scaffold=False,
            include_merge=False,
            orchestration_mode="fanout",
            tile_ids=["tile_00"],
            monolithic_max_iterations=0,
            scaffold_max_iterations=0,
            tile_max_iterations=6000,
            training_max_runtime_seconds=7200,
            extra_env=extra_env or {},
            timestamp=1234567890,
            downscale_factor=downscale_factor,
            include_review=False,
            tile_budget_mode="fixed",
            max_images_per_tile=240,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="111111111111.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:test",
            scaffold_artifact_s3_uri="s3://bucket/scaffold/model.tar.gz",
            instance_type="ml.g4dn.xlarge",
        )

    def test_tile_input_hash_changes_for_effective_downscale_factor(self):
        downscale_1 = self._single_leaf_stages(downscale_factor=1)[0]
        downscale_2 = self._single_leaf_stages(downscale_factor=2)[0]

        self.assertNotEqual(downscale_1.input_hash, downscale_2.input_hash)
        self.assertNotIn("TRAINING_DOWNSCALE_FACTOR", downscale_1.environment)
        self.assertEqual(downscale_2.environment["TRAINING_DOWNSCALE_FACTOR"], "2")

    def test_tile_input_hash_changes_for_floater_pruning_settings(self):
        conservative = self._single_leaf_stages(
            extra_env={
                "FLOATER_PRUNING_MAX_OPACITY": "0.98",
                "FLOATER_PRUNING_MAX_COLOR_DISTANCE": "0.24",
            }
        )[0]
        aggressive = self._single_leaf_stages(
            extra_env={
                "FLOATER_PRUNING_MAX_OPACITY": "1.01",
                "FLOATER_PRUNING_MAX_COLOR_DISTANCE": "0.65",
            }
        )[0]

        self.assertNotEqual(conservative.input_hash, aggressive.input_hash)

    def test_tile_input_hash_uses_effective_default_training_environment(self):
        stage = self._single_leaf_stages()[0]
        fingerprint = benchmark.tile_input_hash_env_fingerprint(stage.environment)

        self.assertEqual(fingerprint["MODEL_VARIANT"], "splatfacto-w-light")
        self.assertEqual(fingerprint["ENABLE_BG_MODEL"], "true")
        self.assertEqual(fingerprint["ENABLE_ALPHA_LOSS"], "true")
        self.assertEqual(fingerprint["ENABLE_ROBUST_MASK"], "true")
        self.assertEqual(fingerprint["GLOBAL_SCAFFOLD_REQUIRE_FILTERED_INIT"], "true")

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
                "baseline_review_manifest_s3_uri": "",
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

    def test_submit_guardrail_accepts_dataset_baseline_without_v18(self):
        args = type(
            "Args",
            (),
            {
                "submit": True,
                "max_estimated_usd": 1.0,
                "experiment_id": "cvhr-baseline-test",
                "v18_review_manifest_s3_uri": "",
                "baseline_review_manifest_s3_uri": "s3://bucket/cvhr-baseline.json",
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
            "input_image_coverage_gate": {"status": "passed", "stages": []},
            "stages": [
                {
                    "stage_type": "train",
                    "training_mode": "leaf_tile",
                }
            ],
        }

        benchmark.validate_submit_guardrails(args, summary)

    def test_submit_guardrail_allows_cached_only_merge_without_checkpoint_targets(self):
        args = type(
            "Args",
            (),
            {
                "submit": True,
                "max_estimated_usd": 1.0,
                "experiment_id": "cached-merge-test",
                "v18_review_manifest_s3_uri": "",
                "baseline_review_manifest_s3_uri": "s3://bucket/cvhr-baseline.json",
                "enable_checkpoints": False,
                "enable_spot": False,
                "checkpoint_resume_s3_uri": "",
                "reuse_tile_cache": True,
                "orchestration_mode": "fanout",
                "skip_merge": False,
                "skip_review": True,
            },
        )()
        summary = {
            "visual_qa_plan": {"enabled": True},
            "viewer_smoke_plan": {"enabled": True},
            "early_visual_smoke_plan": {
                "abort_on_failure": True,
                "checkpoint_steps": [],
                "sentinel_cameras": [],
                "checkpoint_s3_uris": {},
                "checkpoint_probe_command_template": "probe",
                "visual_gate_command_template": "gate",
                "stop_command_template": "stop",
            },
            "cost_estimate": {"estimated_usd": 0.0, "stage_estimates": []},
            "sagemaker_env_value_length_violations": [],
            "leaf_density_cap_preflight_violations": [],
            "input_image_coverage_gate": {"status": "passed", "stages": []},
            "stages": [
                {
                    "stage_type": "cached_tile",
                    "training_mode": "leaf_tile",
                },
                {
                    "stage_type": "merge",
                    "training_mode": "strict_core",
                },
            ],
        }

        benchmark.validate_submit_guardrails(args, summary)


if __name__ == "__main__":
    unittest.main()
