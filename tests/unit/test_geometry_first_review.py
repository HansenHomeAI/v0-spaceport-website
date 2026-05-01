import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "geometry_review.py"
SPEC = importlib.util.spec_from_file_location("geometry_review_test_module", MODULE_PATH)
geometry_review = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(geometry_review)


class GeometryFirstReviewTests(unittest.TestCase):
    def test_freeze_review_camera_manifest_selects_promotion_and_smoke_sets(self):
        frozen = geometry_review.freeze_review_camera_manifest(
            {
                "near_detail_camera_ids": [f"near_{index}.jpg" for index in range(20)],
                "boundary_camera_ids": [f"boundary_{index}.jpg" for index in range(20)],
                "horizon_camera_ids": [f"horizon_{index}.jpg" for index in range(20)],
            },
            images_per_bucket=12,
            smoke_images_per_bucket=4,
        )

        self.assertEqual(len(frozen["buckets"]["near_detail"]), 12)
        self.assertEqual(frozen["smoke_buckets"]["boundary"], [f"boundary_{index}.jpg" for index in range(4)])

    def test_evaluate_promotion_decision_blocks_fallback_and_metric_regressions(self):
        baseline = {
            "bucket_medians": {
                "near_detail": {"psnr": 30.0, "ssim": 0.9, "lpips": 0.1},
                "boundary": {"psnr": 28.0, "ssim": 0.88, "lpips": 0.12},
                "horizon": {"psnr": 27.0, "ssim": 0.86, "lpips": 0.14},
            },
            "sky_bucket_medians": {"horizon": {"score": 0.8}},
        }
        candidate = {
            "bucket_medians": {
                "near_detail": {"psnr": 28.5, "ssim": 0.88, "lpips": 0.2},
                "boundary": {"psnr": 28.1, "ssim": 0.881, "lpips": 0.119},
                "horizon": {"psnr": 27.0, "ssim": 0.86, "lpips": 0.14},
            },
            "sky_bucket_medians": {"horizon": {"score": 0.8}},
            "merge_report": {"fallback_tile_count": 1, "retain_all_tile_count": 0},
        }

        decision = geometry_review.evaluate_promotion_decision(
            baseline_manifest=baseline,
            candidate_manifest=candidate,
        )

        self.assertEqual(decision["status"], "blocked")
        self.assertIn("merge_fallback_tile_count_gt_zero", decision["block_reasons"])
        self.assertIn("near_detail_psnr_regression", decision["block_reasons"])
        self.assertIn("boundary_no_required_improvement", decision["block_reasons"])

    def test_build_review_comparison_includes_fallback_breakdown(self):
        comparison = geometry_review.build_review_comparison(
            baseline_manifest={
                "bucket_medians": {},
                "merge_report": {
                    "fallback_tile_count": 1,
                    "retain_all_tile_count": 0,
                    "fallback_reasons": [{"tile_id": "tile_05", "reason": "baseline_fallback"}],
                },
            },
            candidate_manifest={
                "bucket_medians": {},
                "merge_report": {
                    "fallback_tile_count": 2,
                    "retain_all_tile_count": 0,
                    "fallback_reasons": [{"tile_id": "tile_06", "reason": "candidate_fallback"}],
                },
            },
        )

        self.assertEqual(comparison["fallback_breakdown"]["baseline"]["fallback_tile_count"], 1)
        self.assertEqual(comparison["fallback_breakdown"]["candidate"]["fallback_tile_count"], 2)
        self.assertIn(
            "merge_fallback_tile_count_gt_zero",
            comparison["promotion_decision"]["block_reasons"],
        )

    def test_build_review_comparison_blocks_camera_coverage_mismatch(self):
        bucket_medians = {
            "near_detail": {"psnr": 30.0, "ssim": 0.9, "lpips": 0.1},
            "boundary": {"psnr": 28.0, "ssim": 0.88, "lpips": 0.12},
            "horizon": {"psnr": 27.0, "ssim": 0.86, "lpips": 0.14},
        }
        baseline = {
            "actual_bucket_counts": {"near_detail": 4, "boundary": 4, "horizon": 4},
            "review_image_names_by_bucket": {
                "near_detail_camera_ids": ["near_0.JPG", "near_1.JPG", "near_2.JPG", "near_3.JPG"],
                "boundary_camera_ids": ["boundary_0.JPG", "boundary_1.JPG", "boundary_2.JPG", "boundary_3.JPG"],
                "horizon_camera_ids": ["horizon_0.JPG", "horizon_1.JPG", "horizon_2.JPG", "horizon_3.JPG"],
            },
            "bucket_medians": bucket_medians,
        }
        candidate = {
            "actual_bucket_counts": {"near_detail": 12, "boundary": 12, "horizon": 12},
            "review_image_names_by_bucket": {
                "near_detail_camera_ids": [f"near_{index}.JPG" for index in range(12)],
                "boundary_camera_ids": [f"boundary_{index}.JPG" for index in range(12)],
                "horizon_camera_ids": [f"horizon_{index}.JPG" for index in range(12)],
            },
            "bucket_medians": {
                "near_detail": {"psnr": 10.0, "ssim": 0.5, "lpips": 0.5},
                "boundary": {"psnr": 10.0, "ssim": 0.5, "lpips": 0.5},
                "horizon": {"psnr": 10.0, "ssim": 0.5, "lpips": 0.5},
            },
            "merge_report": {"fallback_tile_count": 0, "retain_all_tile_count": 0},
            "render_sanity": {"status": "ok", "blank_view_count": 0},
        }

        comparison = geometry_review.build_review_comparison(
            baseline_manifest=baseline,
            candidate_manifest=candidate,
        )

        decision = comparison["promotion_decision"]
        self.assertEqual(decision["status"], "blocked")
        self.assertEqual(comparison["camera_coverage"]["status"], "blocked")
        self.assertIn("near_detail_camera_set_mismatch", decision["block_reasons"])
        self.assertIn("boundary_camera_set_mismatch", decision["block_reasons"])
        self.assertIn("horizon_camera_set_mismatch", decision["block_reasons"])
        self.assertNotIn("horizon_psnr_regression", decision["block_reasons"])

    def test_evaluate_v18_non_regression_accepts_small_bucket_deltas(self):
        v18 = {
            "bucket_medians": {
                "near_detail": {"psnr": 30.0, "ssim": 0.9, "lpips": 0.1},
                "boundary": {"psnr": 28.0, "ssim": 0.88, "lpips": 0.12},
                "horizon": {"psnr": 27.0, "ssim": 0.86, "lpips": 0.14},
            },
            "sky_bucket_medians": {"horizon": {"score": 0.8}},
        }
        candidate = {
            "bucket_medians": {
                "near_detail": {"psnr": 29.9, "ssim": 0.897, "lpips": 0.105},
                "boundary": {"psnr": 27.9, "ssim": 0.878, "lpips": 0.125},
                "horizon": {"psnr": 26.9, "ssim": 0.857, "lpips": 0.145},
            },
            "sky_bucket_medians": {"horizon": {"score": 0.79}},
        }

        decision = geometry_review.evaluate_v18_non_regression_decision(
            v18_manifest=v18,
            candidate_manifest=candidate,
        )

        self.assertEqual(decision["status"], "promoted")
        self.assertEqual(decision["block_reasons"], [])

    def test_evaluate_v18_non_regression_blocks_bucket_sky_and_single_camera_regressions(self):
        v18 = {
            "bucket_medians": {
                "near_detail": {"psnr": 30.0, "ssim": 0.9, "lpips": 0.1},
                "boundary": {"psnr": 28.0, "ssim": 0.88, "lpips": 0.12},
                "horizon": {"psnr": 27.0, "ssim": 0.86, "lpips": 0.14},
            },
            "sky_bucket_medians": {"horizon": {"score": 0.8}},
            "views": [
                {
                    "bucket": "near_detail",
                    "image_name": "near_0.jpg",
                    "metrics": {"psnr": 30.0, "ssim": 0.9, "lpips": 0.1},
                }
            ],
        }
        candidate = {
            "bucket_medians": {
                "near_detail": {"psnr": 29.9, "ssim": 0.897, "lpips": 0.105},
                "boundary": {"psnr": 27.7, "ssim": 0.878, "lpips": 0.125},
                "horizon": {"psnr": 26.9, "ssim": 0.857, "lpips": 0.145},
            },
            "sky_bucket_medians": {"horizon": {"score": 0.77}},
            "views": [
                {
                    "bucket": "near_detail",
                    "image_name": "near_0.jpg",
                    "metrics": {"psnr": 29.0, "ssim": 0.9, "lpips": 0.13},
                }
            ],
        }

        decision = geometry_review.evaluate_v18_non_regression_decision(
            v18_manifest=v18,
            candidate_manifest=candidate,
        )

        self.assertEqual(decision["status"], "blocked")
        self.assertIn("boundary_v18_median_psnr_regression", decision["block_reasons"])
        self.assertIn("horizon_v18_sky_score_regression", decision["block_reasons"])
        self.assertIn("near_detail_v18_single_camera_psnr_regression", decision["block_reasons"])
        self.assertIn("near_detail_v18_single_camera_lpips_regression", decision["block_reasons"])

    def test_build_review_comparison_includes_v18_non_regression_decision(self):
        manifest = {
            "bucket_medians": {
                "near_detail": {"psnr": 30.0, "ssim": 0.9, "lpips": 0.1},
                "boundary": {"psnr": 28.0, "ssim": 0.88, "lpips": 0.12},
                "horizon": {"psnr": 27.0, "ssim": 0.86, "lpips": 0.14},
            },
            "sky_bucket_medians": {"horizon": {"score": 0.8}},
        }

        comparison = geometry_review.build_review_comparison(
            baseline_manifest=manifest,
            candidate_manifest=manifest,
        )

        self.assertEqual(comparison["v18_non_regression_decision"]["status"], "promoted")

    def test_evaluate_promotion_decision_blocks_blank_render_sanity(self):
        baseline = {
            "bucket_medians": {
                "near_detail": {"psnr": 30.0, "ssim": 0.9, "lpips": 0.1},
                "boundary": {"psnr": 28.0, "ssim": 0.88, "lpips": 0.12},
                "horizon": {"psnr": 27.0, "ssim": 0.86, "lpips": 0.14},
            },
            "sky_bucket_medians": {"horizon": {"score": 0.8}},
        }
        candidate = {
            "bucket_medians": {
                "near_detail": {"psnr": 30.0, "ssim": 0.9, "lpips": 0.1},
                "boundary": {"psnr": 28.6, "ssim": 0.89, "lpips": 0.09},
                "horizon": {"psnr": 27.0, "ssim": 0.86, "lpips": 0.14},
            },
            "sky_bucket_medians": {"horizon": {"score": 0.8}},
            "merge_report": {"fallback_tile_count": 0, "retain_all_tile_count": 0},
            "render_sanity": {"status": "blocked", "blank_view_count": 12},
        }

        decision = geometry_review.evaluate_promotion_decision(
            baseline_manifest=baseline,
            candidate_manifest=candidate,
        )

        self.assertEqual(decision["status"], "blocked")
        self.assertIn("candidate_render_sanity_blocked", decision["block_reasons"])

    def test_evaluate_promotion_decision_blocks_raw_union_as_diagnostic(self):
        baseline = {
            "bucket_medians": {
                "near_detail": {"psnr": 30.0, "ssim": 0.9, "lpips": 0.1},
                "boundary": {"psnr": 28.0, "ssim": 0.88, "lpips": 0.12},
                "horizon": {"psnr": 27.0, "ssim": 0.86, "lpips": 0.14},
            },
            "sky_bucket_medians": {"horizon": {"score": 0.8}},
        }
        candidate = {
            "bucket_medians": {
                "near_detail": {"psnr": 30.4, "ssim": 0.91, "lpips": 0.09},
                "boundary": {"psnr": 28.7, "ssim": 0.89, "lpips": 0.09},
                "horizon": {"psnr": 27.2, "ssim": 0.87, "lpips": 0.13},
            },
            "sky_bucket_medians": {"horizon": {"score": 0.8}},
            "merge_report": {
                "merge_mode": "raw_union",
                "fallback_tile_count": 0,
                "retain_all_tile_count": 0,
            },
            "render_sanity": {"status": "ok", "blank_view_count": 0},
        }

        decision = geometry_review.evaluate_promotion_decision(
            baseline_manifest=baseline,
            candidate_manifest=candidate,
        )

        self.assertEqual(decision["status"], "blocked")
        self.assertEqual(decision["merge_mode"], "raw_union")
        self.assertIn("diagnostic_raw_union_not_promotable", decision["block_reasons"])

    def test_classify_root_cause_prefers_merge_bad_on_fallbacks(self):
        root_cause = geometry_review.classify_root_cause(
            inventory={"complete": True, "required": {"seven_tile_splats": True}},
            merge_report={"fallback_tile_count": 2, "retain_all_tile_count": 0},
            candidate_pairs=[{"eligible": True}],
        )

        self.assertEqual(root_cause, "merge_bad")

    def test_inventory_extracted_model_requires_tiles_merge_and_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(7):
                tile_dir = root / "tiles" / f"tile_{index:02d}"
                tile_dir.mkdir(parents=True)
                (tile_dir / "splat.ply").write_bytes(b"ply")
            (root / "merged").mkdir()
            (root / "merged" / "merged_splat.ply").write_bytes(b"ply")
            (root / "merged" / "merge_report.json").write_text("{}", encoding="utf-8")
            (root / "3dgs_tile_manifest.json").write_text("{}", encoding="utf-8")
            (root / "3dgs_view_buckets.json").write_text("{}", encoding="utf-8")

            inventory = geometry_review.inventory_extracted_model(root)

            self.assertTrue(inventory["complete"])
            self.assertEqual(inventory["tile_splat_count"], 7)


if __name__ == "__main__":
    unittest.main()
