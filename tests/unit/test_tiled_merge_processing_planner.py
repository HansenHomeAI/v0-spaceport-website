import importlib.util
import json
import sys
import tarfile
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
            background_source_tile_id="tile_10",
            protected_overlap_tile_ids="tile_04,tile_10",
            protected_overlap_mode="retain_all",
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
        self.assertEqual(payload["Environment"]["BACKGROUND_SOURCE_TILE_ID"], "tile_10")
        self.assertEqual(payload["Environment"]["MERGE_PROTECTED_OVERLAP_TILE_IDS"], "tile_04,tile_10")
        self.assertEqual(payload["Environment"]["MERGE_PROTECTED_OVERLAP_MODE"], "retain_all")

    def test_packager_resets_output_mount_contents_without_removing_mount(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "artifact"
            (output_root / "nested").mkdir(parents=True)
            (output_root / "nested" / "old.txt").write_text("old", encoding="utf-8")
            (output_root / "old-root.txt").write_text("old", encoding="utf-8")

            packager.reset_directory_contents(output_root)

            self.assertTrue(output_root.exists())
            self.assertEqual(list(output_root.iterdir()), [])

    def test_packager_writes_required_tile_input_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "artifact"
            packager.write_required_tile_inputs(
                output_root=output_root,
                tile_plan={
                    "tile_id": "tile_04",
                    "artifact_uri": "s3://bucket/v18/model.tar.gz",
                    "candidate_members": ["tiles/tile_04/splat.ply", "splat.ply"],
                },
                tile_manifest={"tiles": [{"tile_id": "tile_04"}, {"tile_id": "tile_05"}]},
                view_buckets={"tile_04": {"boundary": ["DJI_0001.JPG"]}},
            )

            input_dir = output_root / "tiled_pipeline" / "inputs" / "tile_04"
            manifest = json.loads((input_dir / "3dgs_tile_manifest.json").read_text(encoding="utf-8"))
            scaffold = json.loads((input_dir / "scaffold_init_metadata.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["tiles"], [{"tile_id": "tile_04"}])
            self.assertEqual(scaffold["scaffold_inheritance_mode"], "remote_no_training_reuse")

    def test_packager_extracts_background_sidecars_for_merge_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "splat.ply").write_text("ply\n", encoding="utf-8")
            (source / "background_skybox.webp").write_bytes(b"webp")
            (source / "background_manifest.json").write_text(
                json.dumps({"background_selection": {"score": 0.8}}),
                encoding="utf-8",
            )
            tarball = root / "model.tar.gz"
            with tarfile.open(tarball, "w:gz") as archive:
                archive.add(source / "splat.ply", arcname="tiles/tile_04/splat.ply")
                archive.add(source / "background_skybox.webp", arcname="tiles/tile_04/background_skybox.webp")
                archive.add(source / "background_manifest.json", arcname="tiles/tile_04/background_manifest.json")

            output_tile_dir = root / "out" / "tile_04"
            record = packager.extract_tile_from_artifact(
                {
                    "tile_id": "tile_04",
                    "artifact_uri": "s3://bucket/model.tar.gz",
                    "artifact_input_name": "artifact-00",
                    "candidate_members": ["tiles/tile_04/splat.ply"],
                },
                root,
                output_tile_dir,
            )

            self.assertEqual(record["selected_member"], "tiles/tile_04/splat.ply")
            self.assertTrue((output_tile_dir / "background_skybox.webp").exists())
            self.assertTrue((output_tile_dir / "background_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
