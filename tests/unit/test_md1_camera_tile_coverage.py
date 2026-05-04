import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "analyze_md1_camera_tile_coverage.py"
SPEC = importlib.util.spec_from_file_location("md1_camera_tile_coverage_test_module", MODULE_PATH)
coverage = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(coverage)


class MD1CameraTileCoverageTests(unittest.TestCase):
    def test_analyze_coverage_blocks_missing_full_tile_support(self):
        tile_manifest = {
            "tiles": [
                {
                    "tile_id": "tile_00",
                    "base_camera_ids": ["near_a.JPG"],
                    "border_camera_ids": ["boundary_a.JPG"],
                    "context_camera_ids": ["horizon_a.JPG"],
                    "image_names": [],
                },
                {
                    "tile_id": "tile_04",
                    "base_camera_ids": ["near_a.JPG"],
                    "border_camera_ids": ["boundary_a.JPG"],
                    "context_camera_ids": ["horizon_a.JPG"],
                    "image_names": [],
                },
                {
                    "tile_id": "tile_05",
                    "base_camera_ids": ["near_b.JPG"],
                    "border_camera_ids": [],
                    "context_camera_ids": [],
                    "image_names": [],
                },
            ]
        }
        review_manifest = {
            "review_image_names_by_bucket": {
                "near_detail_camera_ids": ["near_a.JPG", "near_b.JPG"],
                "boundary_camera_ids": ["boundary_a.JPG"],
                "horizon_camera_ids": ["horizon_a.JPG"],
            }
        }

        result = coverage.analyze_coverage(
            tile_manifest=tile_manifest,
            review_manifest=review_manifest,
            selected_tile_ids=["tile_00"],
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("review_cameras_missing_full_tile_support", result["block_reasons"])
        self.assertIn("review_cameras_missing_any_selected_tile_support", result["block_reasons"])
        self.assertEqual(result["missing_support_tile_frequency"], {"tile_04": 3, "tile_05": 1})
        self.assertEqual(result["minimum_any_support_tile_additions"], ["tile_05"])
        self.assertEqual(result["full_support_tile_additions"], ["tile_04", "tile_05"])
        self.assertEqual(result["matched_full_support_camera_subset"]["near_detail_camera_ids"], [])
        self.assertEqual(result["matched_any_support_camera_subset"]["boundary_camera_ids"], ["boundary_a.JPG"])

    def test_review_images_by_bucket_reads_frozen_smoke_manifest(self):
        review_manifest = {
            "buckets": {
                "near_detail": ["near_0.JPG", "near_1.JPG"],
                "boundary": ["boundary_0.JPG", "boundary_1.JPG"],
                "horizon": ["horizon_0.JPG", "horizon_1.JPG"],
            },
            "smoke_buckets": {
                "near_detail": ["near_0.JPG"],
                "boundary": ["boundary_0.JPG"],
                "horizon": ["horizon_0.JPG"],
            },
        }

        images = coverage.review_images_by_bucket(review_manifest, camera_set="smoke")

        self.assertEqual(images["near_detail_camera_ids"], ["near_0.JPG"])
        self.assertEqual(images["boundary_camera_ids"], ["boundary_0.JPG"])
        self.assertEqual(images["horizon_camera_ids"], ["horizon_0.JPG"])

    def test_cli_writes_output_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tile_manifest_path = root / "tile_manifest.json"
            review_manifest_path = root / "review_manifest.json"
            output_path = root / "coverage.json"
            coverage.write_json(
                tile_manifest_path,
                {
                    "tiles": [
                        {
                            "tile_id": "tile_00",
                            "base_camera_ids": ["near.JPG"],
                            "border_camera_ids": ["boundary.JPG"],
                            "context_camera_ids": ["horizon.JPG"],
                        }
                    ]
                },
            )
            coverage.write_json(
                review_manifest_path,
                {
                    "review_image_names_by_bucket": {
                        "near_detail_camera_ids": ["near.JPG"],
                        "boundary_camera_ids": ["boundary.JPG"],
                        "horizon_camera_ids": ["horizon.JPG"],
                    }
                },
            )
            result = coverage.analyze_coverage(
                tile_manifest=coverage.load_json(tile_manifest_path),
                review_manifest=coverage.load_json(review_manifest_path),
                selected_tile_ids=["tile_00"],
            )
            coverage.write_json(output_path, result)

            saved = coverage.load_json(output_path)

        self.assertEqual(saved["status"], "ok")
        self.assertEqual(saved["full_support_tile_additions"], [])


if __name__ == "__main__":
    unittest.main()
