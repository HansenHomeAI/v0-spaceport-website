import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = REPO_ROOT / "infrastructure" / "containers" / "3dgs"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

MODULE_PATH = MODULE_DIR / "run_tiled_merge_packaging.py"
SPEC = importlib.util.spec_from_file_location("run_tiled_merge_packaging_test_module", MODULE_PATH)
merge_packaging = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = merge_packaging
SPEC.loader.exec_module(merge_packaging)


class TiledMergePackagingTests(unittest.TestCase):
    def test_apply_sidecar_merge_bounds_uses_refreshed_leaf_scaffold_bounds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            tile_dir = root / "tile_07"
            tile_dir.mkdir()
            sidecar_bounds = {
                "min_x": -10.0,
                "max_x": 10.0,
                "min_y": -5.0,
                "max_y": 5.0,
                "min_z": -2.0,
                "max_z": 12.0,
            }
            (tile_dir / "training_selection.json").write_text(
                json.dumps(
                    {
                        "tile_id": "tile_07",
                        "scaffold_initialization": {
                            "scaffold_filter_bounds": sidecar_bounds,
                            "source_filter_retention_ratio": 0.25,
                            "source_filtered_gaussian_count": 25,
                            "source_gaussian_count": 100,
                        },
                        "tile_manifest_resolution": {
                            "ownership_bounds_refresh": {
                                "status": "refreshed",
                                "strategy_counts": {"transformed_camera_centers": 1},
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            manifest = {
                "tiles": [
                    {
                        "tile_id": "tile_07",
                        "core_bounds": {
                            "min_x": -1000,
                            "max_x": 1000,
                            "min_y": -1000,
                            "max_y": 1000,
                            "min_z": -1000,
                            "max_z": 1000,
                        },
                        "overlap_bounds": {
                            "min_x": -1100,
                            "max_x": 1100,
                            "min_y": -1100,
                            "max_y": 1100,
                            "min_z": -1100,
                            "max_z": 1100,
                        },
                        "bounds_strategy": {"core": "observed_points", "overlap": "observed_points"},
                    }
                ]
            }

            updated, summary = merge_packaging.apply_sidecar_merge_bounds(
                manifest,
                {"tile_07": tile_dir},
            )

            tile = updated["tiles"][0]
            self.assertEqual(summary["applied_tile_count"], 1)
            self.assertEqual(tile["core_bounds"], sidecar_bounds)
            self.assertEqual(tile["overlap_bounds"], manifest["tiles"][0]["overlap_bounds"])
            self.assertEqual(tile["bounds_strategy"]["core"], "resolved_scaffold_filter_bounds")
            self.assertEqual(
                tile["merge_sidecar_bounds"]["original_core_bounds"],
                manifest["tiles"][0]["core_bounds"],
            )

    def test_apply_sidecar_merge_bounds_ignores_unrefreshed_sidecar(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            tile_dir = root / "tile_00"
            tile_dir.mkdir()
            (tile_dir / "training_selection.json").write_text(
                json.dumps(
                    {
                        "scaffold_initialization": {
                            "scaffold_filter_bounds": {
                                "min_x": -1,
                                "max_x": 1,
                                "min_y": -1,
                                "max_y": 1,
                                "min_z": -1,
                                "max_z": 1,
                            }
                        },
                        "tile_manifest_resolution": {"ownership_bounds_refresh": {"status": "unchanged"}},
                    }
                ),
                encoding="utf-8",
            )
            original_bounds = {
                "min_x": -100,
                "max_x": 100,
                "min_y": -100,
                "max_y": 100,
                "min_z": -100,
                "max_z": 100,
            }
            manifest = {"tiles": [{"tile_id": "tile_00", "core_bounds": original_bounds}]}

            updated, summary = merge_packaging.apply_sidecar_merge_bounds(
                manifest,
                {"tile_00": tile_dir},
            )

            self.assertEqual(summary["applied_tile_count"], 0)
            self.assertEqual(updated["tiles"][0]["core_bounds"], original_bounds)
            self.assertEqual(summary["tiles"][0]["reason"], "tile_manifest_bounds_not_refreshed")


if __name__ == "__main__":
    unittest.main()
