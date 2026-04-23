import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
THREE_DGS_ROOT = REPO_ROOT / "infrastructure" / "containers" / "3dgs"
if str(THREE_DGS_ROOT) not in sys.path:
    sys.path.insert(0, str(THREE_DGS_ROOT))
if "tile_pipeline" in sys.modules and not hasattr(sys.modules["tile_pipeline"], "load_json"):
    del sys.modules["tile_pipeline"]

MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "run_geometry_consistency_audit.py"
SPEC = importlib.util.spec_from_file_location("geometry_consistency_audit_test_module", MODULE_PATH)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


def write_ply_header(path: Path, vertex_count: int = 3) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "ply",
                "format ascii 1.0",
                f"element vertex {vertex_count}",
                "property float x",
                "property float y",
                "property float z",
                "end_header",
                "0 0 0",
            ]
        ),
        encoding="utf-8",
    )


class GeometryConsistencyAuditTests(unittest.TestCase):
    def test_freeze_review_cameras_writes_promotion_and_smoke_sets(self):
        frozen = audit.freeze_review_cameras(
            view_buckets={
                "near_detail_camera_ids": ["a.jpg", "b.jpg", "c.jpg"],
                "boundary_camera_ids": ["d.jpg", "e.jpg"],
                "horizon_camera_ids": ["f.jpg"],
            },
            max_images_per_bucket=2,
            smoke_images_per_bucket=1,
        )

        self.assertEqual(frozen["review_image_names_by_bucket"]["near_detail_camera_ids"], ["a.jpg", "b.jpg"])
        self.assertEqual(frozen["smoke_image_names_by_bucket"]["near_detail_camera_ids"], ["a.jpg"])
        self.assertEqual(frozen["source_buckets"]["boundary_camera_ids"], 2)

    def test_artifact_inventory_fails_closed_until_required_artifacts_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inventory = audit.artifact_inventory(root, None, None)

        self.assertTrue(inventory["fail_closed"])
        self.assertFalse(inventory["required_artifacts"]["seven_tile_splats"])

    def test_artifact_inventory_and_root_cause_use_merge_fallbacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(7):
                write_ply_header(root / "tiles" / f"tile_{index:02d}" / "splat.ply", vertex_count=index + 1)
            write_ply_header(root / "merged" / "merged_splat.ply", vertex_count=10)
            (root / "merged" / "merge_report.json").write_text(
                json.dumps({"fallback_tile_count": 2, "retain_all_tile_count": 0}),
                encoding="utf-8",
            )
            (root / "tiled_pipeline" / "inputs" / "scaffold").mkdir(parents=True)
            (root / "tiled_pipeline" / "inputs" / "scaffold" / "3dgs_tile_manifest.json").write_text(
                json.dumps({"tiles": []}),
                encoding="utf-8",
            )
            (root / "tiled_pipeline" / "inputs" / "scaffold" / "3dgs_view_buckets.json").write_text(
                json.dumps({"boundary_camera_ids": []}),
                encoding="utf-8",
            )

            inventory = audit.artifact_inventory(root, None, None)
            root_cause = audit.classify_root_cause(
                inventory,
                {"fallback_tile_count": 2, "retain_all_tile_count": 0},
            )

        self.assertFalse(inventory["fail_closed"])
        self.assertEqual(inventory["tile_splat_count"], 7)
        self.assertEqual(inventory["tile_splats"][0]["vertex_count"], 1)
        self.assertEqual(root_cause, "merge_bad")


if __name__ == "__main__":
    unittest.main()
