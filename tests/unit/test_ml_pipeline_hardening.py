import json
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(relative_path: str, module_name: str, extra_modules=None):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    injected = extra_modules or {}
    with mock.patch.dict(sys.modules, injected, clear=False):
        spec.loader.exec_module(module)
    return module


def fake_boto3_module():
    module = types.ModuleType("boto3")
    module.client = lambda *args, **kwargs: types.SimpleNamespace()
    return module


class StartMLJobContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(
            "infrastructure/spaceport_cdk/lambda/start_ml_job/lambda_function.py",
            "start_ml_job_lambda",
            {"boto3": fake_boto3_module()},
        )

    def test_state_machine_arn_prefers_primary_env_var(self):
        with mock.patch.dict(os.environ, {"STATE_MACHINE_ARN": "primary", "STEP_FUNCTION_ARN": "fallback"}, clear=True):
            self.assertEqual(self.module.get_state_machine_arn(), "primary")

    def test_state_machine_arn_falls_back_to_step_function_env_var(self):
        with mock.patch.dict(os.environ, {"STEP_FUNCTION_ARN": "fallback"}, clear=True):
            self.assertEqual(self.module.get_state_machine_arn(), "fallback")

    def test_validate_s3_url_accepts_supported_formats(self):
        self.assertTrue(self.module.validate_s3_url("s3://bucket-name/path/to/archive.zip"))
        self.assertTrue(self.module.validate_s3_url("https://bucket-name.s3.amazonaws.com/path/to/archive.zip"))
        self.assertTrue(self.module.validate_s3_url("https://s3.amazonaws.com/bucket-name/path/to/archive.zip"))

    def test_parse_s3_url_supports_https_and_s3_protocol(self):
        self.assertEqual(
            self.module.parse_s3_url("s3://bucket-name/path/to/archive.zip"),
            ("bucket-name", "path/to/archive.zip"),
        )
        self.assertEqual(
            self.module.parse_s3_url("https://bucket-name.s3.amazonaws.com/path/to/archive.zip"),
            ("bucket-name", "path/to/archive.zip"),
        )

    def test_lambda_continues_when_s3_preflight_access_is_forbidden(self):
        no_such_key = type("NoSuchKey", (Exception,), {})
        self.module.s3 = types.SimpleNamespace(
            head_object=mock.Mock(side_effect=Exception("403 forbidden")),
            put_object=mock.Mock(),
            exceptions=types.SimpleNamespace(NoSuchKey=no_such_key),
        )
        self.module.stepfunctions = types.SimpleNamespace(
            start_execution=mock.Mock(return_value={"executionArn": "arn:aws:states:region:acct:execution:test"})
        )
        self.module.boto3 = types.SimpleNamespace(
            client=lambda *args, **kwargs: types.SimpleNamespace(
                describe_repositories=lambda **repo_kwargs: {}
            )
        )

        event = {"body": json.dumps({"s3Url": "s3://bucket-name/path/to/archive.zip"})}
        context = types.SimpleNamespace(
            invoked_function_arn="arn:aws:lambda:us-west-2:123456789012:function:test"
        )

        with mock.patch.dict(
            os.environ,
            {
                "STATE_MACHINE_ARN": "arn:aws:states:us-west-2:123456789012:stateMachine:test",
                "ML_BUCKET": "spaceport-ml-processing-staging",
                "SFM_ECR_REPO": "spaceport/sfm",
                "GAUSSIAN_ECR_REPO": "spaceport/3dgs",
                "COMPRESSOR_ECR_REPO": "spaceport/compressor",
                "SFM_ECR_REPO_FALLBACK": "spaceport/sfm",
                "GAUSSIAN_ECR_REPO_FALLBACK": "spaceport/3dgs",
                "COMPRESSOR_ECR_REPO_FALLBACK": "spaceport/compressor",
            },
            clear=True,
        ):
            response = self.module.lambda_handler(event, context)

        self.assertEqual(response["statusCode"], 200)
        self.module.stepfunctions.start_execution.assert_called_once()


class MLStatusContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(
            "infrastructure/spaceport_cdk/lambda/ml_status/lambda_function.py",
            "ml_status_lambda",
            {"boto3": fake_boto3_module()},
        )

    def test_ml_status_arn_falls_back_to_step_function_env_var(self):
        with mock.patch.dict(os.environ, {"STEP_FUNCTION_ARN": "fallback"}, clear=True):
            self.assertEqual(self.module.get_state_machine_arn(), "fallback")


class SfmProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(
            "infrastructure/containers/sfm/profile_utils.py",
            "sfm_profile_utils",
        )

    def test_large_non_gps_dataset_selects_large_profile(self):
        profile = self.module.select_sfm_execution_profile(
            image_count=538,
            total_input_bytes=2311969858,
            has_gps_priors=False,
        )

        self.assertEqual(profile["name"], "large_no_gps")
        self.assertEqual(profile["overrides"]["matching_gps_neighbors"], 6)
        self.assertEqual(profile["timeouts"]["reconstruct"]["max_seconds"], 18000)
        self.assertEqual(profile["timeouts"]["reconstruct"]["stall_seconds"], 3600)

    def test_reconstruct_progress_signal_requires_real_progress_markers(self):
        self.assertTrue(self.module.line_indicates_progress("reconstruct", "Reconstruction now has 450 shots."))
        self.assertTrue(self.module.line_indicates_progress("reconstruct", "Ran GLOBAL bundle in 368.34 secs."))
        self.assertFalse(self.module.line_indicates_progress("reconstruct", "Some unrelated debug line"))


class SfmArtifactValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(
            "infrastructure/containers/sfm/run_opensfm_gps.py",
            "run_opensfm_gps",
            {
                "yaml": types.SimpleNamespace(safe_load=lambda stream: {}, dump=lambda data, stream: None),
                "gps_processor": types.SimpleNamespace(DroneFlightPathProcessor=object),
                "gps_processor_3d": types.SimpleNamespace(Advanced3DPathProcessor=object),
                "colmap_converter": types.SimpleNamespace(OpenSfMToCOLMAPConverter=object),
                "profile_utils": load_module(
                    "infrastructure/containers/sfm/profile_utils.py",
                    "sfm_profile_utils_for_pipeline_tests",
                ),
            },
        )

    def test_validate_output_artifacts_requires_complete_3dgs_handoff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            pipeline = self.module.OpenSfMGPSPipeline.__new__(self.module.OpenSfMGPSPipeline)
            pipeline.output_dir = output_dir

            sparse_dir = output_dir / "sparse" / "0"
            sparse_dir.mkdir(parents=True)
            (sparse_dir / "cameras.txt").write_text("1 PINHOLE 100 100 50 50 50\n", encoding="utf-8")
            (sparse_dir / "images.txt").write_text(
                "# Number of images: 1, mean observations per image: 24\n"
                "1 1 0 0 0 0 0 0 1 image.jpg\n"
                "0 0 1\n",
                encoding="utf-8",
            )
            (sparse_dir / "points3D.txt").write_text(
                "1 0 0 0 255 255 255 0.1 1 0 1 1\n",
                encoding="utf-8",
            )

            images_dir = output_dir / "images"
            images_dir.mkdir()
            (images_dir / "image.jpg").write_bytes(b"jpg")
            (output_dir / "database.db").write_bytes(b"sqlite")

            self.assertTrue(pipeline.validate_output_artifacts())

            (output_dir / "database.db").unlink()
            self.assertFalse(pipeline.validate_output_artifacts())


class TrainingArtifactValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake_torch = types.ModuleType("torch")
        fake_torch._dynamo = types.SimpleNamespace(config=types.SimpleNamespace(suppress_errors=False))
        cls.module = load_module(
            "infrastructure/containers/3dgs/train_nerfstudio_production.py",
            "train_nerfstudio_production",
            {
                "torch": fake_torch,
                "yaml": types.SimpleNamespace(safe_load=lambda stream: {}, dump=lambda data, stream: None),
            },
        )

    def test_validate_training_artifacts_requires_non_empty_ply(self):
        trainer = self.module.NerfStudioTrainer.__new__(self.module.NerfStudioTrainer)
        with tempfile.TemporaryDirectory() as tmpdir:
            trainer.output_dir = Path(tmpdir)
            self.assertFalse(trainer.validate_training_artifacts())

            ply_path = trainer.output_dir / "splat.ply"
            ply_path.write_bytes(b"ply\n")
            self.assertTrue(trainer.validate_training_artifacts())


class CompressionArtifactValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(
            "infrastructure/containers/compressor/compress.py",
            "compressor_module",
            {"boto3": fake_boto3_module()},
        )

    def test_validate_compression_outputs_requires_full_sogs_bundle(self):
        compressor = self.module.PlayCanvasSOGSCompressor.__new__(self.module.PlayCanvasSOGSCompressor)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            compressor.output_dir = str(output_dir)

            compressed_dir = output_dir / "compressed_splat"
            compressed_dir.mkdir()
            bundle_dir = output_dir / "supersplat_bundle"
            bundle_dir.mkdir()

            results = {"compressed_outputs": [{"output_dir": str(compressed_dir)}]}

            with self.assertRaises(RuntimeError):
                compressor._validate_compression_outputs(results)

            for directory in (compressed_dir, bundle_dir):
                for name in self.module.PlayCanvasSOGSCompressor.REQUIRED_SOGS_FILES:
                    (directory / name).write_bytes(b"data")
            (bundle_dir / "settings.json").write_text("{}", encoding="utf-8")

            compressor._validate_compression_outputs(results)


class StepFunctionDefinitionContractTests(unittest.TestCase):
    def test_failure_path_ends_in_fail_state_and_start_job_exports_both_env_vars(self):
        stack_source = (
            REPO_ROOT / "infrastructure/spaceport_cdk/spaceport_cdk/ml_pipeline_stack.py"
        ).read_text(encoding="utf-8")

        self.assertIn('pipeline_failed = sfn.Fail(', stack_source)
        self.assertIn('notify_error.next(pipeline_failed)', stack_source)
        self.assertIn('role=lambda_role,', stack_source)
        self.assertIn('role=notification_lambda_role,', stack_source)
        self.assertIn('start_job_lambda.add_environment("STATE_MACHINE_ARN"', stack_source)
        self.assertIn('"STATE_MACHINE_ARN": ml_pipeline.state_machine_arn', stack_source)

    def test_preview_ml_api_toggle_and_workflow_fallbacks_exist(self):
        stack_source = (
            REPO_ROOT / "infrastructure/spaceport_cdk/spaceport_cdk/ml_pipeline_stack.py"
        ).read_text(encoding="utf-8")
        app_source = (
            REPO_ROOT / "infrastructure/spaceport_cdk/app.py"
        ).read_text(encoding="utf-8")
        context_source = (
            REPO_ROOT / "infrastructure/spaceport_cdk/spaceport_cdk/deployment_context.py"
        ).read_text(encoding="utf-8")
        cdk_workflow_source = (
            REPO_ROOT / ".github/workflows/cdk-deploy.yml"
        ).read_text(encoding="utf-8")
        pages_workflow_source = (
            REPO_ROOT / ".github/workflows/deploy-cloudflare-pages.yml"
        ).read_text(encoding="utf-8")
        sfm_dockerfile_source = (
            REPO_ROOT / "infrastructure/containers/sfm/Dockerfile"
        ).read_text(encoding="utf-8")

        self.assertIn('self.deploy_ml_api = env_config.get("deployMlApi", True)', stack_source)
        self.assertIn('value=ml_api_url', stack_source)
        self.assertIn('self, "StartMLJobFunctionName"', stack_source)
        self.assertIn('self, "StopMLJobFunctionName"', stack_source)
        self.assertIn('if self.deployment_class == "branch-preview":', stack_source)
        self.assertIn('upload_bucket_name = "spaceport-uploads-staging"', stack_source)
        self.assertIn('app.node.try_get_context("deploy_ml_api")', app_source)
        self.assertIn('"deployMlApi": context.deploy_ml_api', context_source)
        self.assertIn('--context deploy_ml_api="${DEPLOY_ML_API}"', cdk_workflow_source)
        self.assertIn('infrastructure/spaceport_cdk/app\\.py|infrastructure/spaceport_cdk/spaceport_cdk/deployment_context\\.py', cdk_workflow_source.replace("\\\\", "\\"))
        self.assertNotIn('grep -Eq "^(infrastructure/spaceport_cdk/app\\.py|infrastructure/spaceport_cdk/spaceport_cdk/deployment_context\\.py', cdk_workflow_source.replace("\\\\", "\\"))
        self.assertIn('get_output_with_fallback "$ML_OUTPUT_STACK" "MLPipelineApiUrl" "SpaceportMLPipelineStagingStack"', cdk_workflow_source)
        self.assertIn('get_output_with_fallback "$ML_OUTPUT_STACK" "MLPipelineApiUrl" "SpaceportMLPipelineStagingStack"', pages_workflow_source)
        self.assertIn('resolve_stack_by_prefix() {', pages_workflow_source)
        self.assertIn('AUTH_FALLBACK_STACK="$(resolve_stack_by_prefix "SpaceportAuthStagingStack")"', pages_workflow_source)
        self.assertIn("grep -v '^NEXT_PUBLIC_EXPLORE_API_URL=$'", pages_workflow_source)
        self.assertIn('COPY profile_utils.py /opt/ml/code/profile_utils.py', sfm_dockerfile_source)


if __name__ == "__main__":
    unittest.main()
