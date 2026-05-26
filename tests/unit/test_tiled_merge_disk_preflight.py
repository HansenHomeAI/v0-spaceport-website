import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "preflight_tiled_merge_disk.py"
SPEC = importlib.util.spec_from_file_location("preflight_tiled_merge_disk_test_module", MODULE_PATH)
preflight = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = preflight
SPEC.loader.exec_module(preflight)


class TiledMergeDiskPreflightTests(unittest.TestCase):
    def test_context_density_prefers_nested_tile_member(self):
        stage = {"stage_type": "context_density_tile", "tile_id": "tile_04"}

        self.assertEqual(
            preflight.stage_ply_candidates(stage),
            ["tiles/tile_04/splat.ply", "splat.ply"],
        )

    def test_build_disk_preflight_counts_extract_copy_and_merge_output(self):
        summary = {
            "stages": [
                {
                    "stage_name": "tile00",
                    "stage_type": "cached_tile",
                    "tile_id": "tile_00",
                    "source_artifact_uri": "s3://bucket/cache00.tar.gz",
                },
                {
                    "stage_name": "tile04",
                    "stage_type": "context_density_tile",
                    "tile_id": "tile_04",
                    "source_artifact_uri": "s3://bucket/v18.tar.gz",
                },
                {"stage_name": "merge", "stage_type": "merge"},
            ]
        }

        def fake_inventory(uri, wanted):
            if uri == "s3://bucket/cache00.tar.gz":
                return {"splat.ply": 100}
            if uri == "s3://bucket/v18.tar.gz":
                return {"tiles/tile_04/splat.ply": 200, "splat.ply": 999}
            return {}

        result = preflight.build_disk_preflight(
            summary,
            local_merge_output_dir=Path("/tmp/merge"),
            available_bytes=1000,
            inventory_loader=fake_inventory,
            safety_margin_bytes=100,
            metadata_overhead_bytes=0,
            merge_output_multiplier=1.0,
            tile_materialization_mode="copy",
        )

        self.assertTrue(result["safe_to_local_merge"])
        self.assertEqual(result["input_ply_bytes"], 300)
        self.assertEqual(result["estimated_required_bytes"], 900)
        self.assertEqual(result["required_with_safety_bytes"], 1000)
        self.assertEqual(result["stage_members"][1]["selected_member"], "tiles/tile_04/splat.ply")

    def test_build_disk_preflight_blocks_when_disk_is_too_low(self):
        summary = {
            "stages": [
                {
                    "stage_name": "tile00",
                    "stage_type": "cached_tile",
                    "tile_id": "tile_00",
                    "source_artifact_uri": "s3://bucket/cache00.tar.gz",
                }
            ]
        }

        result = preflight.build_disk_preflight(
            summary,
            local_merge_output_dir=Path("/tmp/merge"),
            available_bytes=299,
            inventory_loader=lambda _uri, _wanted: {"splat.ply": 100},
            safety_margin_bytes=0,
            metadata_overhead_bytes=0,
            merge_output_multiplier=1.0,
            tile_materialization_mode="copy",
        )

        self.assertFalse(result["safe_to_local_merge"])
        self.assertIn("insufficient_local_disk", result["block_reasons"])


if __name__ == "__main__":
    unittest.main()
