import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "plan_md1_boundary_responsible_tiles.py"
SPEC = importlib.util.spec_from_file_location("plan_md1_boundary_responsible_tiles_test_module", MODULE_PATH)
planner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(planner)


def review_comparison() -> dict:
    return {
        "camera_manifest": {
            "review_image_names_by_bucket": {
                "near_detail_camera_ids": ["near.jpg"],
                "boundary_camera_ids": ["DJI_0067.JPG", "DJI_0068.JPG"],
                "horizon_camera_ids": ["horizon.jpg"],
            },
            "views": [
                {
                    "bucket": "boundary",
                    "image_name": "DJI_0067.JPG",
                    "boundary_context_tile_ids": ["tile_04", "tile_10"],
                },
                {
                    "bucket": "boundary",
                    "image_name": "DJI_0068.JPG",
                    "boundary_context_tile_ids": ["tile_04", "tile_10"],
                },
            ],
        },
        "promotion_decision": {
            "status": "blocked",
            "block_reasons": ["boundary_no_required_improvement"],
            "per_bucket": {
                "boundary": {
                    "delta": {
                        "psnr": 0.1,
                        "ssim": 0.002,
                        "lpips": -0.004,
                    }
                }
            },
            "thresholds": {
                "boundary": {
                    "required_improvement": {
                        "psnr": 0.5,
                        "ssim": 0.01,
                        "lpips": -0.025,
                    }
                }
            },
        },
    }


def tile_manifest() -> dict:
    return {
        "tiles": [
            {
                "tile_id": "tile_04",
                "base_camera_ids": ["DJI_0067.JPG", "DJI_0068.JPG"],
                "border_camera_ids": [],
                "context_camera_ids": [],
                "image_names": ["DJI_0067.JPG", "DJI_0068.JPG", "other_boundary.jpg"],
                "selected_image_count": 188,
                "neighbor_tile_ids": ["tile_06"],
            },
            {
                "tile_id": "tile_10",
                "base_camera_ids": ["DJI_0067.JPG", "DJI_0068.JPG"],
                "border_camera_ids": [],
                "context_camera_ids": [],
                "image_names": ["DJI_0067.JPG", "DJI_0068.JPG"],
                "selected_image_count": 188,
                "neighbor_tile_ids": ["tile_13"],
            },
            {
                "tile_id": "tile_13",
                "base_camera_ids": [],
                "border_camera_ids": [],
                "context_camera_ids": ["DJI_0067.JPG", "DJI_0068.JPG"],
                "image_names": [],
                "selected_image_count": 128,
                "neighbor_tile_ids": ["tile_10"],
            },
        ]
    }


def view_buckets() -> dict:
    return {
        "near_detail_camera_ids": [],
        "boundary_camera_ids": ["DJI_0067.JPG", "DJI_0068.JPG", "other_boundary.jpg"],
        "horizon_camera_ids": [],
    }


class PlanMd1BoundaryResponsibleTilesTests(unittest.TestCase):
    def test_lists_boundary_cameras_and_primary_tiles(self):
        report = planner.plan_boundary_responsible_tiles(
            review_comparison=review_comparison(),
            tile_manifest=tile_manifest(),
            view_buckets=view_buckets(),
            candidate_strategy=None,
        )

        self.assertEqual(report["boundary_frozen_cameras"], ["DJI_0067.JPG", "DJI_0068.JPG"])
        self.assertEqual(report["primary_responsible_tile_ids"], ["tile_04", "tile_10"])
        self.assertEqual(report["support_tile_ids"], ["tile_04", "tile_10", "tile_13"])
        self.assertEqual(report["recommendation"], "hold_paid_retry")

    def test_blocks_single_tile_candidate_that_omits_boundary_pair(self):
        candidate = {
            "targeted_quality_blockers": ["boundary_no_required_improvement"],
            "selected_tile_ids": ["tile_10"],
        }

        report = planner.plan_boundary_responsible_tiles(
            review_comparison=review_comparison(),
            tile_manifest=tile_manifest(),
            view_buckets=view_buckets(),
            candidate_strategy=candidate,
        )

        self.assertIn("candidate_strategy_omits_primary_boundary_tiles", report["candidate_strategy_block_reasons"])
        self.assertFalse(report["paid_retry_recommended"])

    def test_allows_candidate_only_when_boundary_blocker_and_primary_tiles_are_targeted(self):
        candidate = {
            "targeted_quality_blockers": ["boundary_no_required_improvement"],
            "selected_tile_ids": ["tile_04", "tile_10"],
        }

        report = planner.plan_boundary_responsible_tiles(
            review_comparison=review_comparison(),
            tile_manifest=tile_manifest(),
            view_buckets=view_buckets(),
            candidate_strategy=candidate,
        )

        self.assertEqual(report["candidate_strategy_block_reasons"], [])
        self.assertTrue(report["paid_retry_recommended"])

    def test_reports_boundary_improvement_gap(self):
        report = planner.plan_boundary_responsible_tiles(
            review_comparison=review_comparison(),
            tile_manifest=tile_manifest(),
        )

        self.assertEqual(report["boundary_improvement_gap"]["remaining_gap"]["psnr"], 0.4)
        self.assertEqual(report["boundary_improvement_gap"]["remaining_gap"]["ssim"], 0.008)
        self.assertAlmostEqual(report["boundary_improvement_gap"]["remaining_gap"]["lpips"], 0.021)


if __name__ == "__main__":
    unittest.main()
