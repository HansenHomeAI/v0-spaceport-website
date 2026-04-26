import importlib.util
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "preflight_tiled_model_artifact.py"
SPEC = importlib.util.spec_from_file_location("preflight_tiled_model_artifact_test_module", MODULE_PATH)
preflight = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(preflight)


def add_json(archive: tarfile.TarFile, name: str, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8")
    info = tarfile.TarInfo(name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def add_bytes(archive: tarfile.TarFile, name: str, payload: bytes = b"ply\n") -> None:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    archive.addfile(info, io.BytesIO(payload))


def write_artifact(path: Path, *, fallback_tile_count: int = 0, omit: set[str] | None = None) -> None:
    omitted = omit or set()
    tile_ids = ["tile_00", "tile_01"]
    with tarfile.open(path, "w:gz") as archive:
        members = {
            "merged/merge_report.json": {
                "merge_mode": "support_weighted_overlap",
                "tile_count": 2,
                "source_gaussians": 100,
                "retained_gaussians": 90,
                "dropped_gaussians": 10,
                "fallback_tile_count": fallback_tile_count,
                "retain_all_tile_count": 0,
                "fallback_reasons": ([{"tile_id": "tile_01", "reason": "test"}] if fallback_tile_count else []),
                "tile_reports": {
                    "tile_00": {"fallback_used": False, "retained_gaussians": 50, "dropped_gaussians": 5},
                    "tile_01": {"fallback_used": bool(fallback_tile_count), "fallback_reason": "test"},
                },
            },
            "tiled_pipeline_summary.json": {
                "mode": "tiled_pipeline",
                "selected_tile_ids": tile_ids,
                "include_scaffold": True,
                "include_merge": True,
            },
            "training_metadata.json": {"training_completed": True, "training_mode": "tiled_pipeline"},
        }
        for name, payload in members.items():
            if name not in omitted:
                add_json(archive, name, payload)
        if "merged/merged_splat.ply" not in omitted:
            add_bytes(archive, "merged/merged_splat.ply")
        for tile_id in tile_ids:
            json_members = {
                f"tiles/{tile_id}/export_manifest.json": {
                    "foreground_coordinate_frame": "planner",
                    "planner_transform_applied": True,
                },
                f"tiles/{tile_id}/stage_summary.json": {"remaining_gaussians": 10},
                f"tiles/{tile_id}/training_metadata.json": {
                    "training_completed": True,
                    "training_mode": "leaf_tile",
                    "model_variant": "splatfacto-w-light",
                    "max_iterations": 12000,
                    "sh_degree": 1,
                },
                f"tiles/{tile_id}/training_selection.json": {
                    "selected_image_count": 12,
                    "view_bucket_counts": {"near_detail": 4, "boundary": 4, "horizon": 4},
                },
                f"tiled_pipeline/inputs/{tile_id}/3dgs_tile_manifest.json": {"tile_id": tile_id},
                f"tiled_pipeline/inputs/{tile_id}/3dgs_view_buckets.json": {"near_detail_camera_ids": []},
                f"tiled_pipeline/inputs/{tile_id}/scaffold_init_metadata.json": {
                    "scaffold_source_artifact": "scaffold/splat.ply",
                    "scaffold_inheritance_mode": "global_scaffold_ply_filtered_point_cloud",
                    "inherited_gaussian_count": 100,
                },
            }
            for name, payload in json_members.items():
                if name not in omitted:
                    add_json(archive, name, payload)
            splat_name = f"tiles/{tile_id}/splat.ply"
            if splat_name not in omitted:
                add_bytes(archive, splat_name, b"ply\n" + tile_id.encode("utf-8"))


class PreflightTiledModelArtifactTests(unittest.TestCase):
    def test_complete_artifact_passes_without_extracting_large_ply_members(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "model.tar.gz"
            output = root / "out"
            write_artifact(artifact)

            summary = preflight.build_summary(
                artifact_uri=str(artifact),
                output_dir=output,
                tile_ids=["tile_00", "tile_01"],
                rung="R4",
                candidate_label="candidate",
                job_name="job",
            )

            self.assertEqual(summary["decision"], "preflight_passed_run_frozen_smoke_review")
            self.assertEqual(summary["block_reasons"], [])
            self.assertFalse((output / "tiles" / "tile_00" / "splat.ply").exists())
            self.assertTrue((output / "tiles" / "tile_00" / "training_metadata.json").exists())
            self.assertEqual(summary["tiles"]["tile_00"]["file_size_mb"], 11 / (1024 * 1024))

    def test_fallback_tile_blocks_promotion_preflight(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "model.tar.gz"
            write_artifact(artifact, fallback_tile_count=1)

            summary = preflight.build_summary(
                artifact_uri=str(artifact),
                output_dir=root / "out",
                tile_ids=["tile_00", "tile_01"],
                rung="R4",
                candidate_label="candidate",
                job_name="job",
            )

            self.assertEqual(summary["decision"], "preflight_blocked")
            self.assertIn("merge_fallback_tile_count_gt_zero", summary["block_reasons"])

    def test_missing_required_path_blocks_preflight(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "model.tar.gz"
            write_artifact(artifact, omit={"tiled_pipeline/inputs/tile_01/scaffold_init_metadata.json"})

            summary = preflight.build_summary(
                artifact_uri=str(artifact),
                output_dir=root / "out",
                tile_ids=["tile_00", "tile_01"],
                rung="R4",
                candidate_label="candidate",
                job_name="job",
            )

            self.assertEqual(summary["decision"], "preflight_blocked")
            self.assertIn("artifact_required_paths_missing", summary["block_reasons"])
            self.assertIn(
                "tiled_pipeline/inputs/tile_01/scaffold_init_metadata.json",
                summary["artifact_required_paths"]["missing"],
            )


if __name__ == "__main__":
    unittest.main()
