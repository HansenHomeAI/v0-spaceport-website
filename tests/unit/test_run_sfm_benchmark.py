import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "run_sfm_benchmark.py"
SPEC = importlib.util.spec_from_file_location("run_sfm_benchmark_test_module", MODULE_PATH)
run_sfm_benchmark = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(run_sfm_benchmark)


class ProcessingJobElapsedSecondsTests(unittest.TestCase):
    def test_elapsed_seconds_from_iso_timestamp(self) -> None:
        status = {"ProcessingStartTime": "2026-04-17T15:25:58.329000-06:00"}
        now = datetime.fromisoformat("2026-04-17T15:27:58.329000-06:00")

        elapsed = run_sfm_benchmark.processing_job_elapsed_seconds(status, now=now)

        self.assertEqual(elapsed, 120.0)

    def test_elapsed_seconds_from_datetime(self) -> None:
        status = {
            "ProcessingStartTime": datetime(2026, 4, 17, 21, 25, 58, tzinfo=timezone.utc),
        }
        now = datetime(2026, 4, 17, 21, 26, 13, tzinfo=timezone.utc)

        elapsed = run_sfm_benchmark.processing_job_elapsed_seconds(status, now=now)

        self.assertEqual(elapsed, 15.0)

    def test_elapsed_seconds_missing_start_time(self) -> None:
        self.assertIsNone(run_sfm_benchmark.processing_job_elapsed_seconds({}))


class ParseArgsTests(unittest.TestCase):
    def test_stop_after_seconds_flag(self) -> None:
        argv = [
            "run_sfm_benchmark.py",
            "--input-s3-uri",
            "s3://bucket/input.zip",
            "--stop-after-seconds",
            "2112",
        ]
        with mock.patch("sys.argv", argv):
            args = run_sfm_benchmark.parse_args()

        self.assertEqual(args.input_s3_uri, "s3://bucket/input.zip")
        self.assertEqual(args.stop_after_seconds, 2112.0)


class FindBranchMlStackTests(unittest.TestCase):
    def test_returns_exact_branch_stack_when_present(self) -> None:
        with mock.patch.object(
            run_sfm_benchmark,
            "aws_json",
            return_value={
                "Stacks": [
                    {
                        "StackName": "SpaceportMLPreviewStack",
                        "Outputs": [
                            {"OutputKey": "BranchName", "OutputValue": "feature-branch"},
                            {"OutputKey": "MLBucketName", "OutputValue": "preview-bucket"},
                            {"OutputKey": "SfMRepositoryUri", "OutputValue": "123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm"},
                        ],
                    }
                ]
            },
        ):
            stack_name, outputs = run_sfm_benchmark.find_branch_ml_stack("feature-branch")

        self.assertEqual(stack_name, "SpaceportMLPreviewStack")
        self.assertEqual(outputs["MLBucketName"], "preview-bucket")

    def test_falls_back_to_shared_staging_stack_for_branch_preview(self) -> None:
        with mock.patch.object(
            run_sfm_benchmark,
            "aws_json",
            side_effect=[
                {
                    "Stacks": [
                        {
                            "StackName": "SpaceportPreviewStack",
                            "Outputs": [
                                {"OutputKey": "BranchName", "OutputValue": "feature-branch"},
                            ],
                        }
                    ]
                },
                {
                    "Stacks": [
                        {
                            "StackName": "SpaceportMLPipelineStagingStack",
                            "Outputs": [
                                {"OutputKey": "BranchName", "OutputValue": "development"},
                                {"OutputKey": "MLBucketName", "OutputValue": "staging-bucket"},
                                {"OutputKey": "SfMRepositoryUri", "OutputValue": "975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm"},
                            ],
                        }
                    ]
                },
            ],
        ):
            stack_name, outputs = run_sfm_benchmark.find_branch_ml_stack("feature-branch")

        self.assertEqual(stack_name, "SpaceportMLPipelineStagingStack")
        self.assertEqual(outputs["MLBucketName"], "staging-bucket")

    def test_raises_when_no_ml_stack_has_required_outputs(self) -> None:
        with mock.patch.object(
            run_sfm_benchmark,
            "aws_json",
            side_effect=[
                {"Stacks": []},
                {
                    "Stacks": [
                        {
                            "StackName": "SpaceportMLPipelineStagingStack",
                            "Outputs": [
                                {"OutputKey": "BranchName", "OutputValue": "development"},
                            ],
                        }
                    ]
                },
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_sfm_benchmark.find_branch_ml_stack("feature-branch")


if __name__ == "__main__":
    unittest.main()
