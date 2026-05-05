import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "plan_tiled_merge_processing.py"
SPEC = importlib.util.spec_from_file_location("plan_tiled_merge_processing_test_module", MODULE_PATH)
planner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = planner
SPEC.loader.exec_module(planner)


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


if __name__ == "__main__":
    unittest.main()
