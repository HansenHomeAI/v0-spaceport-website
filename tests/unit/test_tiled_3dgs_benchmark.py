import importlib.util
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "run_tiled_3dgs_benchmark.py"
SPEC = importlib.util.spec_from_file_location("run_tiled_3dgs_benchmark_test_module", MODULE_PATH)
benchmark = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = benchmark
SPEC.loader.exec_module(benchmark)


class Tiled3DGSBenchmarkTests(unittest.TestCase):
    def test_build_benchmark_stages_defaults_to_single_tiled_job(self):
        manifest = {
            "tiles": [
                {"tile_id": "tile_00"},
                {"tile_id": "tile_01"},
            ]
        }

        stages = benchmark.build_benchmark_stages(
            manifest=manifest,
            branch_name="agent-branch",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="bench",
            include_monolithic=True,
            include_scaffold=True,
            include_merge=True,
            orchestration_mode="single_job",
            tile_ids=["tile_00", "tile_01"],
            monolithic_max_iterations=8000,
            scaffold_max_iterations=2000,
            tile_max_iterations=12000,
            extra_env={"LOG_INTERVAL": "50"},
            timestamp=123,
            downscale_factor=1,
        )

        self.assertEqual([stage.stage_name for stage in stages], ["M0_monolithic", "T2_tiled_pipeline"])
        tiled_env = stages[1].environment
        self.assertEqual(tiled_env["TRAINING_MODE"], "tiled_pipeline")
        self.assertEqual(tiled_env["TILED_TILE_IDS"], "tile_00,tile_01")
        self.assertEqual(tiled_env["TILED_MAX_TILES"], "2")
        self.assertEqual(tiled_env["TILED_INCLUDE_MERGE"], "true")
        self.assertEqual(tiled_env["GLOBAL_SCAFFOLD_MAX_ITERATIONS"], "2000")
        self.assertEqual(tiled_env["BILATERAL_PROCESSING"], "false")

    def test_build_training_environment_disables_bilateral_for_w_light_even_if_requested(self):
        env = benchmark.build_training_environment(
            training_mode="monolithic",
            tile_manifest_name="3dgs_tile_manifest.json",
            view_bucket_manifest_name="3dgs_view_buckets.json",
            tile_id=None,
            max_iterations=1000,
            extra_env={
                "MODEL_VARIANT": "splatfacto-w-light",
                "BILATERAL_PROCESSING": "true",
            },
        )

        self.assertEqual(env["MODEL_VARIANT"], "splatfacto-w-light")
        self.assertEqual(env["BILATERAL_PROCESSING"], "false")

    def test_build_training_environment_includes_downscale_factor_when_requested(self):
        env = benchmark.build_training_environment(
            training_mode="monolithic",
            tile_manifest_name="3dgs_tile_manifest.json",
            view_bucket_manifest_name="3dgs_view_buckets.json",
            tile_id=None,
            max_iterations=1000,
            extra_env={},
            downscale_factor=8,
        )

        self.assertEqual(env["TRAINING_DOWNSCALE_FACTOR"], "8")

    def test_build_training_environment_defaults_tiny_proof_runs_to_viewer_mode(self):
        env = benchmark.build_training_environment(
            training_mode="leaf_tile",
            tile_manifest_name="3dgs_tile_manifest.json",
            view_bucket_manifest_name="3dgs_view_buckets.json",
            tile_id="tile_00",
            max_iterations=10,
            extra_env={},
        )

        self.assertEqual(env["TRAINING_VIS_MODE"], "viewer")
        self.assertEqual(env["TRAINING_CACHE_IMAGES"], "disk")
        self.assertEqual(env["TRAINING_CACHE_IMAGES_TYPE"], "uint8")
        self.assertEqual(env["TRAINING_DATALOADER_NUM_WORKERS"], "0")

    def test_build_training_environment_allows_explicit_vis_override_for_tiny_runs(self):
        env = benchmark.build_training_environment(
            training_mode="leaf_tile",
            tile_manifest_name="3dgs_tile_manifest.json",
            view_bucket_manifest_name="3dgs_view_buckets.json",
            tile_id="tile_00",
            max_iterations=10,
            extra_env={"TRAINING_VIS_MODE": "tensorboard"},
        )

        self.assertEqual(env["TRAINING_VIS_MODE"], "tensorboard")

    def test_build_benchmark_stages_fanout_emits_leaf_tiles_and_merge(self):
        manifest = {
            "tiles": [
                {"tile_id": "tile_00"},
                {"tile_id": "tile_01"},
            ]
        }

        stages = benchmark.build_benchmark_stages(
            manifest=manifest,
            branch_name="agent-branch",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="bench",
            include_monolithic=False,
            include_scaffold=True,
            include_merge=True,
            orchestration_mode="fanout",
            tile_ids=["tile_00", "tile_01"],
            monolithic_max_iterations=8000,
            scaffold_max_iterations=2000,
            tile_max_iterations=12000,
            extra_env={},
            timestamp=456,
            downscale_factor=1,
        )

        self.assertEqual(
            [stage.stage_name for stage in stages],
            ["S0_scaffold", "T0_tile_00", "T0_tile_01", "MERGE_strict_core"],
        )
        self.assertEqual(stages[1].depends_on, ["S0_scaffold"])
        self.assertEqual(stages[3].stage_type, "merge")
        self.assertEqual(stages[1].job_name, "bench-456-tile-00")

    def test_create_training_job_payload_includes_branch_tag(self):
        payload = benchmark.create_training_job_payload(
            branch_name="agent-branch",
            job_name="bench-123",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest",
            role_arn="arn:aws:iam::123:role/test",
            input_s3_uri="s3://bucket/input",
            output_s3_uri="s3://bucket/output",
            environment={"TRAINING_MODE": "tiled_pipeline"},
            instance_type="ml.g5.2xlarge",
            volume_size_gb=100,
        )

        self.assertEqual(payload["TrainingJobName"], "bench-123")
        self.assertEqual(payload["Environment"]["TRAINING_MODE"], "tiled_pipeline")
        self.assertIn({"Key": "Branch", "Value": "agent-branch"}, payload["Tags"])

    def test_resolve_execution_context_accepts_explicit_role_image_and_output_without_branch_stack(self):
        original_find = benchmark.find_branch_ml_stack
        original_tag = benchmark.get_branch_ecr_tag
        try:
            def fail_find(_branch_name):
                raise RuntimeError("missing stack")

            benchmark.find_branch_ml_stack = fail_find
            benchmark.get_branch_ecr_tag = lambda _branch_name: "branch-tag"
            args = types.SimpleNamespace(
                stack_name="",
                role_arn="arn:aws:iam::123456789012:role/test",
                image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:test",
                output_root_s3_uri="s3://bucket/manual-validations/test/3dgs",
                image_tag="",
                job_prefix="bench",
            )

            context = benchmark.resolve_execution_context(
                branch_name="agent-branch",
                timestamp=123,
                args=args,
            )

            self.assertIsNone(context.stack_name)
            self.assertEqual(context.role_arn, args.role_arn)
            self.assertEqual(context.image_uri, args.image_uri)
            self.assertEqual(context.output_root_s3_uri, args.output_root_s3_uri)
        finally:
            benchmark.find_branch_ml_stack = original_find
            benchmark.get_branch_ecr_tag = original_tag

    def test_resolve_execution_context_uses_named_stack_when_provided(self):
        original_get_stack_outputs = benchmark.get_stack_outputs
        original_get_role = benchmark.get_sagemaker_role_arn
        original_tag = benchmark.get_branch_ecr_tag
        try:
            benchmark.get_stack_outputs = lambda stack_name: (
                stack_name,
                {
                    "GaussianRepositoryUri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs",
                    "MLBucketName": "spaceport-ml-processing-staging",
                },
            )
            benchmark.get_sagemaker_role_arn = lambda stack_name: f"arn:aws:iam::123456789012:role/{stack_name}"
            benchmark.get_branch_ecr_tag = lambda _branch_name: "branch-tag"
            args = types.SimpleNamespace(
                stack_name="SpaceportMLPipelineStagingStack",
                role_arn="",
                image_uri="",
                output_root_s3_uri="",
                image_tag="",
                job_prefix="bench",
            )

            context = benchmark.resolve_execution_context(
                branch_name="agent-branch",
                timestamp=123,
                args=args,
            )

            self.assertEqual(context.stack_name, "SpaceportMLPipelineStagingStack")
            self.assertEqual(
                context.image_uri,
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:branch-tag",
            )
            self.assertEqual(context.role_arn, "arn:aws:iam::123456789012:role/SpaceportMLPipelineStagingStack")
            self.assertEqual(
                context.output_root_s3_uri,
                "s3://spaceport-ml-processing-staging/manual-validations/bench-123/3dgs",
            )
        finally:
            benchmark.get_stack_outputs = original_get_stack_outputs
            benchmark.get_sagemaker_role_arn = original_get_role
            benchmark.get_branch_ecr_tag = original_tag


if __name__ == "__main__":
    unittest.main()
