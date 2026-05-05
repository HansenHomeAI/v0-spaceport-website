import argparse
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "3dgs"
    / "submit_md1_splat_transform_lod_processing.py"
)

SPEC = importlib.util.spec_from_file_location("submit_md1_splat_transform_lod_processing", MODULE_PATH)
lod_submit = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(lod_submit)


class MD1SplatTransformLODProcessingTests(unittest.TestCase):
    def test_direct_lod_payload_keeps_source_lineage_and_skybox_inputs(self):
        args = argparse.Namespace(
            branch="agent-90742618-md1-geometry-consistency",
            device="cpu",
            direct_lod_only=True,
            direct_script_path=str(lod_submit.DEFAULT_DIRECT_SCRIPT_PATH),
            direct_script_s3_prefix="",
            image_uri=lod_submit.DEFAULT_IMAGE_URI,
            input_prefix="s3://example/input/merged/",
            instance_type="ml.m5.4xlarge",
            job_name="md1-r4-t10rollback-lod-dryrun-20260505",
            lod_chunk_count=256,
            lod_chunk_extent=32,
            lod_decimation="30%,10%,3%",
            max_runtime_seconds=21600,
            output_prefix="s3://example/output/lod/",
            project_tag="md1-production-viewer",
            role_arn=lod_submit.DEFAULT_ROLE_ARN,
            source_label="md1-r4-tile10-rollback-v18-nonregression",
            source_ply="/opt/ml/processing/input/merged_splat.ply",
            source_skybox="/opt/ml/processing/input/background_skybox.webp",
            volume_size_gb=200,
        )

        payload = lod_submit.build_payload(args)

        self.assertEqual(
            payload["AppSpecification"]["ContainerEntrypoint"],
            [
                "/bin/bash",
                "/opt/ml/processing/script/md1_splat_transform_direct_lod.sh",
            ],
        )
        env = payload["Environment"]
        self.assertEqual(env["MD1_SOURCE_LINEAGE_LABEL"], args.source_label)
        self.assertEqual(env["MD1_SOURCE_PLY"], args.source_ply)
        self.assertEqual(env["MD1_SOURCE_SKYBOX"], args.source_skybox)
        self.assertIn(
            {"Key": "project", "Value": args.project_tag},
            payload["Tags"],
        )
        self.assertIn(
            {"Key": "source-lineage", "Value": args.source_label},
            payload["Tags"],
        )


if __name__ == "__main__":
    unittest.main()
