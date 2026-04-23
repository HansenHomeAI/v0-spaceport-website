import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "run_tiled_quality_review.py"


def load_module_with_stubs():
    torch_stub = types.ModuleType("torch")
    pil_stub = types.ModuleType("PIL")
    plyfile_stub = types.ModuleType("plyfile")
    skimage_stub = types.ModuleType("skimage")
    skimage_metrics_stub = types.ModuleType("skimage.metrics")
    gsplat_stub = types.ModuleType("gsplat")
    sky_quality_stub = types.ModuleType("sky_quality")
    tile_pipeline_stub = types.ModuleType("tile_pipeline")
    trainer_stub = types.ModuleType("train_nerfstudio_production")

    pil_stub.Image = types.SimpleNamespace()
    plyfile_stub.PlyData = type("PlyData", (), {})
    skimage_metrics_stub.structural_similarity = lambda *args, **kwargs: 1.0
    gsplat_stub.rasterization = types.SimpleNamespace()
    sky_quality_stub.compute_sky_image_metrics = lambda *_args, **_kwargs: {}
    tile_pipeline_stub.normalize_image_name = lambda value: value
    tile_pipeline_stub.ordered_unique = lambda values: list(dict.fromkeys(values))
    tile_pipeline_stub.resolve_tiled_input_manifests = lambda **_kwargs: ({}, {}, {})
    tile_pipeline_stub.select_pipeline_review_image_names_by_bucket = lambda *_args, **_kwargs: {}
    tile_pipeline_stub.subset_tile_manifest = lambda manifest, selected_tile_ids: manifest
    trainer_stub.NerfStudioTrainer = type("NerfStudioTrainer", (), {})

    for name, module in {
        "torch": torch_stub,
        "PIL": pil_stub,
        "plyfile": plyfile_stub,
        "skimage": skimage_stub,
        "skimage.metrics": skimage_metrics_stub,
        "gsplat": gsplat_stub,
        "sky_quality": sky_quality_stub,
        "tile_pipeline": tile_pipeline_stub,
        "train_nerfstudio_production": trainer_stub,
    }.items():
        sys.modules[name] = module

    spec = importlib.util.spec_from_file_location("run_tiled_quality_review_test_module", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_view(bucket: str, *, psnr: float = 30.0) -> dict:
    return {
        "bucket": bucket,
        "metrics": {"psnr": psnr, "ssim": 0.92, "lpips": 0.08},
        "metrics_no_background": {"psnr": psnr - 0.5, "ssim": 0.90, "lpips": 0.10},
        "sky_metrics": {
            "score": 0.81,
            "luminance": 0.74,
            "saturation": 0.11,
            "blue_dominance": 0.21,
            "edge_density": 0.06,
        },
        "merged_render_stats": {
            "source_gaussians": 3_600_000,
            "visible_gaussians": 3_100_000,
            "rendered_gaussians": 900_000,
            "limited": True,
        },
        "render_health": {
            "rgb_mean": 0.45,
            "rgb_std": 0.08,
            "rgb_min": 0.02,
            "rgb_max": 0.91,
            "dynamic_range": 0.89,
            "blank_or_flat": False,
        },
    }


class TiledQualityReviewManifestTests(unittest.TestCase):
    def test_build_review_manifest_marks_ready_for_manual_signoff(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            review_camera_manifest_path = root / "review_camera_manifest.json"
            review_camera_manifest_path.write_text("{}", encoding="utf-8")

            review_views = []
            review_images_by_bucket = {}
            for bucket_key, bucket_label in module.DEFAULT_BUCKET_ORDER:
                review_images_by_bucket[bucket_key] = [f"{bucket_label}_{index}.png" for index in range(4)]
                for index in range(4):
                    review_views.append(make_view(bucket_label, psnr=30.0 + index))

            manifest = module.build_review_manifest(
                model_tarball=root / "model.tar.gz",
                selected_tile_ids=["tile_04", "tile_05", "tile_06"],
                manifest_resolution={"source_mode": "native_3dgs_manifests"},
                merge_report={"retain_all_tile_count": 0, "fallback_tile_count": 0},
                review_images_by_bucket=review_images_by_bucket,
                review_camera_manifest_path=review_camera_manifest_path,
                review_views=review_views,
                max_images_per_bucket=4,
                merged_background_present=True,
                render_settings={"render_scale": 0.5, "max_gaussians_per_view": 900000},
            )

            self.assertEqual(manifest["promotion_readiness"]["status"], "ready_for_manual_signoff")
            self.assertTrue(manifest["promotion_readiness"]["review_buckets_complete"])
            self.assertEqual(
                manifest["actual_bucket_counts"],
                {"near_detail": 4, "boundary": 4, "horizon": 4},
            )
            self.assertEqual(
                manifest["requested_bucket_counts"],
                {"near_detail": 4, "boundary": 4, "horizon": 4},
            )
            self.assertEqual(manifest["bucket_medians"]["near_detail"]["psnr"], 31.5)
            self.assertEqual(manifest["no_background_bucket_medians"]["near_detail"]["psnr"], 31.0)
            self.assertEqual(manifest["render_settings"]["render_scale"], 0.5)
            self.assertEqual(manifest["render_stats_summary"]["merged_limited_view_count"], 12)
            self.assertEqual(manifest["render_stats_summary"]["merged_rendered_gaussian_min"], 900000.0)
            self.assertEqual(manifest["render_health_summary"]["blank_or_flat_count"], 0)
            self.assertIn(
                "merged review included promoted background skybox",
                manifest["promotion_readiness"]["notes"],
            )
            self.assertIn(
                "merged review used deterministic view-capped rendering on 12 views",
                manifest["promotion_readiness"]["notes"],
            )

    def test_build_review_manifest_blocks_on_incomplete_buckets_or_retain_all(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            review_camera_manifest_path = root / "review_camera_manifest.json"
            review_camera_manifest_path.write_text("{}", encoding="utf-8")

            manifest = module.build_review_manifest(
                model_tarball=root / "model.tar.gz",
                selected_tile_ids=["tile_00"],
                manifest_resolution={"source_mode": "native_3dgs_manifests"},
                merge_report={"retain_all_tile_count": 1, "fallback_tile_count": 2},
                review_images_by_bucket={
                    "near_detail_camera_ids": ["near_0.png"],
                    "boundary_camera_ids": [f"boundary_{index}.png" for index in range(4)],
                    "horizon_camera_ids": [f"horizon_{index}.png" for index in range(4)],
                },
                review_camera_manifest_path=review_camera_manifest_path,
                review_views=[
                    make_view("near_detail"),
                    *[make_view("boundary") for _ in range(4)],
                    *[make_view("horizon") for _ in range(4)],
                ],
                max_images_per_bucket=4,
                merged_background_present=False,
            )

            self.assertEqual(manifest["promotion_readiness"]["status"], "blocked")
            self.assertFalse(manifest["promotion_readiness"]["review_buckets_complete"])
            self.assertEqual(manifest["promotion_readiness"]["retain_all_tile_count"], 1)
            self.assertEqual(manifest["promotion_readiness"]["fallback_tile_count"], 2)
            self.assertIn(
                "review buckets did not produce the requested 4/4/4 coverage",
                manifest["promotion_readiness"]["notes"],
            )
            self.assertIn(
                "merge used retain_all fallback on at least one tile",
                manifest["promotion_readiness"]["notes"],
            )
            self.assertIn(
                "merged review had no promoted background skybox",
                manifest["promotion_readiness"]["notes"],
            )

    def test_build_review_manifest_blocks_blank_or_flat_renders(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            review_camera_manifest_path = root / "review_camera_manifest.json"
            review_camera_manifest_path.write_text("{}", encoding="utf-8")

            review_views = []
            review_images_by_bucket = {}
            for bucket_key, bucket_label in module.DEFAULT_BUCKET_ORDER:
                review_images_by_bucket[bucket_key] = [f"{bucket_label}_{index}.png" for index in range(4)]
                for index in range(4):
                    view = make_view(bucket_label, psnr=30.0 + index)
                    if bucket_label == "near_detail" and index == 0:
                        view["render_health"] = {
                            "rgb_mean": 0.0,
                            "rgb_std": 0.0,
                            "rgb_min": 0.0,
                            "rgb_max": 0.0,
                            "dynamic_range": 0.0,
                            "blank_or_flat": True,
                        }
                    review_views.append(view)

            manifest = module.build_review_manifest(
                model_tarball=root / "model.tar.gz",
                selected_tile_ids=["tile_02", "tile_05"],
                manifest_resolution={"source_mode": "native_3dgs_manifests"},
                merge_report={"retain_all_tile_count": 0, "fallback_tile_count": 0},
                review_images_by_bucket=review_images_by_bucket,
                review_camera_manifest_path=review_camera_manifest_path,
                review_views=review_views,
                max_images_per_bucket=4,
                merged_background_present=False,
            )

        self.assertEqual(manifest["promotion_readiness"]["status"], "blocked")
        self.assertEqual(manifest["render_health_summary"]["blank_or_flat_count"], 1)
        self.assertIn(
            "merged review produced blank or flat renders on 1 views",
            manifest["promotion_readiness"]["notes"],
        )

    def test_compare_review_manifests_blocks_metric_regressions_and_merge_fallbacks(self):
        module = load_module_with_stubs()

        baseline = {
            "model_artifact": "s3://baseline/model.tar.gz",
            "bucket_medians": {
                "near_detail": {"psnr": 30.0, "ssim": 0.90, "lpips": 0.10},
                "boundary": {"psnr": 25.0, "ssim": 0.85, "lpips": 0.20},
                "horizon": {"psnr": 28.0, "ssim": 0.88, "lpips": 0.12},
            },
            "sky_bucket_medians": {"horizon": {"score": 0.80}},
            "views": [
                {
                    "bucket": "boundary",
                    "image_name": "a.jpg",
                    "merged_render": "baseline.png",
                    "merged_no_background_render": "baseline_no_bg.png",
                }
            ],
        }
        candidate = {
            "model_artifact": "s3://candidate/model.tar.gz",
            "review_camera_manifest": "review_camera_manifest.json",
            "bucket_medians": {
                "near_detail": {"psnr": 28.5, "ssim": 0.86, "lpips": 0.16},
                "boundary": {"psnr": 25.1, "ssim": 0.851, "lpips": 0.19},
                "horizon": {"psnr": 27.0, "ssim": 0.87, "lpips": 0.16},
            },
            "sky_bucket_medians": {"horizon": {"score": 0.60}},
            "merge_report": {"fallback_tile_count": 1, "retain_all_tile_count": 0, "tiles": []},
            "views": [
                {
                    "bucket": "boundary",
                    "image_name": "a.jpg",
                    "merged_render": "candidate.png",
                    "merged_no_background_render": "candidate_no_bg.png",
                }
            ],
        }

        comparison = module.compare_review_manifests(
            baseline_manifest=baseline,
            candidate_manifest=candidate,
        )

        codes = {reason["code"] for reason in comparison["block_reasons"]}
        self.assertFalse(comparison["promotion_decision"]["promoted"])
        self.assertIn("near_detail_psnr_regression", codes)
        self.assertIn("boundary_no_required_improvement", codes)
        self.assertIn("horizon_sky_score_regression", codes)
        self.assertIn("merge_fallback_tile_count_nonzero", codes)
        self.assertEqual(comparison["side_by_side_render_paths"][0]["baseline_render"], "baseline.png")
        self.assertEqual(
            comparison["side_by_side_render_paths"][0]["candidate_no_background_render"],
            "candidate_no_bg.png",
        )

    def test_load_frozen_review_images_by_bucket_accepts_label_keys(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review_camera_manifest.json"
            path.write_text(
                '{"review_image_names_by_bucket":{"near_detail":["a.jpg","a2.jpg"],"boundary":["b.jpg","b2.jpg"],"horizon":["c.jpg","c2.jpg"]}}',
                encoding="utf-8",
            )

            frozen = module.load_frozen_review_images_by_bucket(path, max_images_per_bucket=1)

        self.assertEqual(frozen["near_detail_camera_ids"], ["a.jpg"])
        self.assertEqual(frozen["boundary_camera_ids"], ["b.jpg"])
        self.assertEqual(frozen["horizon_camera_ids"], ["c.jpg"])

    def test_sh_rest_coefficients_load_channel_major_ply_order(self):
        module = load_module_with_stubs()

        rest = np.array([[0.0, 1.0, 2.0, 3.0, 4.0, 5.0]], dtype=np.float32)
        reshaped = module.reshape_sh_rest_coefficients(rest)

        self.assertEqual(reshaped.shape, (1, 2, 3))
        np.testing.assert_array_equal(
            reshaped,
            np.array([[[0.0, 2.0, 4.0], [1.0, 3.0, 5.0]]], dtype=np.float32),
        )

    def test_camera_viewmat_candidates_include_opengl_to_opencv_flip(self):
        module = load_module_with_stubs()

        c2w = np.eye(4, dtype=np.float32)
        candidates = dict(module.camera_viewmat_candidates(c2w))

        np.testing.assert_array_equal(
            candidates["opengl_to_opencv_yz_flip"],
            np.diag([1.0, -1.0, -1.0, 1.0]).astype(np.float32),
        )
        np.testing.assert_array_equal(
            candidates["raw_world_to_camera"],
            np.eye(4, dtype=np.float32),
        )


if __name__ == "__main__":
    unittest.main()
