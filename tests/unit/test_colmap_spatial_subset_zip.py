import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "sfm" / "prepare_colmap_spatial_subset_zip.py"
SPEC = importlib.util.spec_from_file_location("prepare_colmap_spatial_subset_zip", MODULE_PATH)
subset_zip = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = subset_zip
SPEC.loader.exec_module(subset_zip)


class ColmapSpatialSubsetZipTests(unittest.TestCase):
    def make_pose(self, name: str, x: float, y: float) -> object:
        return subset_zip.ImagePose(
            image_id=len(name),
            name=name,
            qvec=(1.0, 0.0, 0.0, 0.0),
            tvec=(-x, -y, 0.0),
            center=(x, y, 0.0),
        )

    def test_choose_densest_spatial_subset_returns_contiguous_cluster(self):
        records = [
            self.make_pose("a.jpg", 0.0, 0.0),
            self.make_pose("b.jpg", 1.0, 0.0),
            self.make_pose("c.jpg", 2.0, 0.0),
            self.make_pose("far.jpg", 100.0, 0.0),
        ]

        seed, selected = subset_zip.choose_densest_spatial_subset(records, 3)

        self.assertEqual(seed.name, "b.jpg")
        self.assertEqual([record.name for record in selected], ["a.jpg", "b.jpg", "c.jpg"])

    def test_camera_center_from_colmap_identity_rotation(self):
        center = subset_zip.camera_center_from_colmap(
            (1.0, 0.0, 0.0, 0.0),
            (-10.0, 4.0, -2.5),
        )

        self.assertEqual(center, (10.0, -4.0, 2.5))

    def test_build_subset_summary_keeps_exact_selected_count_and_names(self):
        records = [
            self.make_pose("a.jpg", 0.0, 0.0),
            self.make_pose("b.jpg", 1.0, 0.0),
            self.make_pose("c.jpg", 2.0, 0.0),
        ]
        seed = records[1]
        selected = records[:2]

        summary = subset_zip.build_subset_summary(
            source_colmap_uri="s3://bucket/source/colmap",
            source_images_uri="s3://bucket/source/colmap/images",
            output_zip_uri="s3://bucket/out/md1-shrunk.zip",
            target_count=2,
            records=records,
            selected=selected,
            seed=seed,
        )

        self.assertEqual(summary["dataset"], "MD1-Shrunk")
        self.assertEqual(summary["source_registered_images"], 3)
        self.assertEqual(summary["selected_count"], 2)
        self.assertEqual(summary["selected_names"], ["a.jpg", "b.jpg"])


if __name__ == "__main__":
    unittest.main()
