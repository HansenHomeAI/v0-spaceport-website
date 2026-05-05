import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "plan_tiled_merge_processing.py"
CONTAINER_DIR = REPO_ROOT / "infrastructure" / "containers" / "3dgs"
PACKAGER_PATH = CONTAINER_DIR / "run_tiled_merge_packaging.py"
SPEC = importlib.util.spec_from_file_location("plan_tiled_merge_processing_test_module", MODULE_PATH)
planner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = planner
SPEC.loader.exec_module(planner)
sys.path.insert(0, str(CONTAINER_DIR))
PACKAGER_SPEC = importlib.util.spec_from_file_location("run_tiled_merge_packaging_test_module", PACKAGER_PATH)
packager = importlib.util.module_from_spec(PACKAGER_SPEC)
assert PACKAGER_SPEC and PACKAGER_SPEC.loader
sys.modules[PACKAGER_SPEC.name] = packager
PACKAGER_SPEC.loader.exec_module(packager)


class TiledMergeProcessingPlannerTests(unittest.TestCase):
    def test_build_merge_plan_dedupes_artifacts_and_uses_nested_context_members(self):
        summary = {
            "stages": [
                {
                    "stage_name": "T0_tile_00",
                    "stage_type": "cached_tile",
                    "tile_id": "tile_00",
                    "source_artifact_uri": "s3://bucket/cache00/model.tar.gz",
                },
                {
                    "stage_name": "T0_tile_04",
                    "stage_type": "context_density_tile",
                    "tile_id": "tile_04",
                    "source_artifact_uri": "s3://bucket/v18/model.tar.gz",
                },
                {
                    "stage_name": "T0_tile_05",
                    "stage_type": "context_density_tile",
                    "tile_id": "tile_05",
                    "source_artifact_uri": "s3://bucket/v18/model.tar.gz",
                },
            ]
        }

        plan = planner.build_merge_plan(summary)

        self.assertEqual(len(plan["artifact_inputs"]), 2)
        self.assertEqual(plan["tiles"][1]["artifact_input_name"], plan["tiles"][2]["artifact_input_name"])
        self.assertEqual(plan["tiles"][1]["candidate_members"][0], "tiles/tile_04/splat.ply")

    def test_create_tiled_merge_processing_payload_mounts_merge_plan_tile_selection_and_artifacts(self):
        payload = planner.create_tiled_merge_processing_payload(
            branch_name="agent-branch",
            job_name="merge-job",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest",
            role_arn="arn:aws:iam::123:role/test",
            output_s3_uri="s3://bucket/output",
            merge_plan_s3_uri="s3://bucket/merge-plan",
            tile_selection_s3_uri="s3://bucket/tile-selection",
            artifact_inputs=[
                {"artifact_input_name": "artifact-00", "artifact_uri": "s3://bucket/a/model.tar.gz"}
            ],
            merge_mode="support_weighted_overlap",
            instance_type="ml.g5.2xlarge",
            volume_size_gb=80,
            max_runtime_seconds=3600,
        )

        self.assertEqual(payload["ProcessingJobName"], "merge-job")
        self.assertEqual(
            payload["AppSpecification"]["ContainerEntrypoint"],
            ["python3", "/opt/ml/code/run_tiled_merge_packaging.py"],
        )
        self.assertEqual(
            [processing_input["InputName"] for processing_input in payload["ProcessingInputs"]],
            ["merge-plan", "tile-selection", "artifact-00"],
        )
        self.assertEqual(payload["Environment"]["MERGE_MODE"], "support_weighted_overlap")

    def test_packager_resets_output_mount_contents_without_removing_mount(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "artifact"
            (output_root / "nested").mkdir(parents=True)
            (output_root / "nested" / "old.txt").write_text("old", encoding="utf-8")
            (output_root / "old-root.txt").write_text("old", encoding="utf-8")

            packager.reset_directory_contents(output_root)

            self.assertTrue(output_root.exists())
            self.assertEqual(list(output_root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
