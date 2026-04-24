import importlib.util
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "run_md1_geometry_r1_review.py"

benchmark_stub = types.ModuleType("run_tiled_3dgs_benchmark")
benchmark_stub.create_quality_review_processing_payload = lambda **kwargs: dict(kwargs)
benchmark_stub.create_quality_review_training_payload = lambda **kwargs: dict(kwargs)
benchmark_stub.find_branch_ml_stack = lambda branch: ("Stack", {})
benchmark_stub.get_branch_ecr_tag = lambda branch: "branch-tag"
benchmark_stub.get_current_branch = lambda: "agent-test"
benchmark_stub.get_sagemaker_role_arn = lambda stack_name: "arn:aws:iam::123:role/test"
benchmark_stub.get_stack_outputs = lambda stack_name: (stack_name, {})
benchmark_stub.normalize_s3_prefix = lambda value: value.rstrip("/")
benchmark_stub.run_command = lambda *args, **kwargs: None
benchmark_stub.sanitize_sagemaker_job_name = lambda value: value.replace("_", "-")
benchmark_stub.wait_for_processing_job = lambda *args, **kwargs: {}
benchmark_stub.wait_for_training_job = lambda *args, **kwargs: {}
sys.modules.setdefault("run_tiled_3dgs_benchmark", benchmark_stub)

SPEC = importlib.util.spec_from_file_location("md1_geometry_r1_review_test_module", MODULE_PATH)
md1_review = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(md1_review)


class MD1GeometryR1ReviewTests(unittest.TestCase):
    def test_candidate_only_reviews_reuse_explicit_strict_baseline(self):
        jobs = md1_review.run_review_jobs(
            branch_name="agent-branch",
            image_uri="repo:tag",
            role_arn="arn:aws:iam::123:role/test",
            colmap_s3_uri="s3://bucket/colmap",
            output_root_s3_uri="s3://bucket/out",
            review_camera_manifest_s3_uri="s3://bucket/review-input",
            staged_variants={
                "support_weighted_overlap": {"model_s3_uri": "s3://bucket/support/model.tar.gz"},
                "raw_union": {"model_s3_uri": "s3://bucket/raw/model.tar.gz"},
            },
            variants=["support_weighted_overlap", "raw_union"],
            max_images_per_bucket=4,
            camera_set="smoke",
            instance_type="ml.g5.2xlarge",
            volume_size_gb=100,
            max_runtime_seconds=7200,
            poll_seconds=60,
            submit=False,
            wait=False,
            execution_mode="training",
            render_scale=0.25,
            max_gaussians_per_view=500000,
            cull_margin=0.5,
            min_gaussians_on_oom=75000,
            tile_ids="tile_02,tile_05",
            baseline_review_manifest_s3_uri="s3://bucket/baselines/strict_core",
        )

        for variant in ("support_weighted_overlap", "raw_union"):
            self.assertEqual(
                jobs[variant]["baseline_review_manifest_s3_uri"],
                "s3://bucket/baselines/strict_core",
            )
            self.assertEqual(
                jobs[variant]["payload"]["baseline_review_manifest_s3_uri"],
                "s3://bucket/baselines/strict_core",
            )

    def test_strict_review_does_not_compare_against_itself(self):
        jobs = md1_review.run_review_jobs(
            branch_name="agent-branch",
            image_uri="repo:tag",
            role_arn="arn:aws:iam::123:role/test",
            colmap_s3_uri="s3://bucket/colmap",
            output_root_s3_uri="s3://bucket/out",
            review_camera_manifest_s3_uri="s3://bucket/review-input",
            staged_variants={"strict_core": {"model_s3_uri": "s3://bucket/strict/model.tar.gz"}},
            variants=["strict_core"],
            max_images_per_bucket=4,
            camera_set="smoke",
            instance_type="ml.g5.2xlarge",
            volume_size_gb=100,
            max_runtime_seconds=7200,
            poll_seconds=60,
            submit=False,
            wait=False,
            execution_mode="training",
            render_scale=0.25,
            max_gaussians_per_view=500000,
            cull_margin=0.5,
            min_gaussians_on_oom=75000,
            tile_ids="tile_02,tile_05",
            baseline_review_manifest_s3_uri="s3://bucket/baselines/strict_core",
        )

        self.assertEqual(jobs["strict_core"]["baseline_review_manifest_s3_uri"], "")
        self.assertEqual(jobs["strict_core"]["payload"]["baseline_review_manifest_s3_uri"], "")


if __name__ == "__main__":
    unittest.main()
