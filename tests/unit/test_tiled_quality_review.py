import importlib.util
import json
import sys
import tarfile
import tempfile
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "run_tiled_quality_review.py"


def load_module_with_stubs():
    numpy_stub = types.ModuleType("numpy")
    torch_stub = types.ModuleType("torch")
    pil_stub = types.ModuleType("PIL")
    plyfile_stub = types.ModuleType("plyfile")
    skimage_stub = types.ModuleType("skimage")
    skimage_metrics_stub = types.ModuleType("skimage.metrics")
    gsplat_stub = types.ModuleType("gsplat")
    geometry_review_stub = types.ModuleType("geometry_review")
    sky_quality_stub = types.ModuleType("sky_quality")
    tile_pipeline_stub = types.ModuleType("tile_pipeline")
    trainer_stub = types.ModuleType("train_nerfstudio_production")

    pil_stub.Image = types.SimpleNamespace()
    plyfile_stub.PlyData = type("PlyData", (), {})
    skimage_metrics_stub.structural_similarity = lambda *args, **kwargs: 1.0
    gsplat_stub.rasterization = types.SimpleNamespace()
    geometry_review_stub.REVIEW_BUCKETS = [
        ("near_detail_camera_ids", "near_detail"),
        ("boundary_camera_ids", "boundary"),
        ("horizon_camera_ids", "horizon"),
    ]
    geometry_review_stub.build_review_comparison = lambda **kwargs: {"promotion_decision": {"status": "blocked"}}
    sky_quality_stub.compute_sky_image_metrics = lambda *_args, **_kwargs: {}
    tile_pipeline_stub.normalize_image_name = lambda value: value
    tile_pipeline_stub.ordered_unique = lambda values: list(dict.fromkeys(values))
    tile_pipeline_stub.resolve_tiled_input_manifests = lambda **_kwargs: ({}, {}, {})
    tile_pipeline_stub.select_pipeline_review_image_names_by_bucket = lambda *_args, **_kwargs: {}
    tile_pipeline_stub.subset_tile_manifest = lambda manifest, selected_tile_ids: manifest
    trainer_stub.NerfStudioTrainer = type("NerfStudioTrainer", (), {})

    for name, module in {
        "numpy": numpy_stub,
        "torch": torch_stub,
        "PIL": pil_stub,
        "plyfile": plyfile_stub,
        "skimage": skimage_stub,
        "skimage.metrics": skimage_metrics_stub,
        "gsplat": gsplat_stub,
        "geometry_review": geometry_review_stub,
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
        "sky_metrics": {
            "score": 0.81,
            "luminance": 0.74,
            "saturation": 0.11,
            "blue_dominance": 0.21,
            "edge_density": 0.06,
        },
    }


class TiledQualityReviewManifestTests(unittest.TestCase):
    def test_extract_model_artifact_rejects_unsafe_members(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "unsafe.tar.gz"
            payload = root / "payload.txt"
            payload.write_text("unsafe", encoding="utf-8")
            with tarfile.open(archive_path, "w:gz") as archive:
                archive.add(payload, arcname="../payload.txt")

            with self.assertRaisesRegex(RuntimeError, "Refusing unsafe tar member"):
                module.extract_model_artifact(archive_path, root / "extract")

    def test_load_frozen_review_images_uses_smoke_bucket_keys(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "review_camera_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "buckets": {
                            "near_detail": ["near_0", "near_1", "near_2"],
                            "boundary": ["boundary_0", "boundary_1", "boundary_2"],
                            "horizon": ["horizon_0", "horizon_1", "horizon_2"],
                        },
                        "smoke_buckets": {
                            "near_detail": ["near_0"],
                            "boundary": ["boundary_0"],
                            "horizon": ["horizon_0"],
                        },
                    }
                ),
                encoding="utf-8",
            )

            selected = module.load_frozen_review_images_by_bucket(
                manifest_path,
                max_images_per_bucket=4,
                camera_set="auto",
            )

            self.assertEqual(
                selected,
                {
                    "near_detail_camera_ids": ["near_0"],
                    "boundary_camera_ids": ["boundary_0"],
                    "horizon_camera_ids": ["horizon_0"],
                },
            )

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
                render_settings=module.RenderSettings(render_scale=0.5, max_gaussians_per_view=500_000),
            )

            self.assertEqual(manifest["promotion_readiness"]["status"], "ready_for_comparison")
            self.assertEqual(manifest["render_settings"]["render_scale"], 0.5)
            self.assertEqual(manifest["render_settings"]["max_gaussians_per_view"], 500_000)
            self.assertTrue(manifest["promotion_readiness"]["review_buckets_complete"])
            self.assertEqual(
                manifest["actual_bucket_counts"],
                {"near_detail": 4, "boundary": 4, "horizon": 4},
            )
            self.assertEqual(manifest["bucket_medians"]["near_detail"]["psnr"], 31.5)
            self.assertIn(
                "merged review included promoted background skybox",
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
                render_settings=module.RenderSettings(),
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

    def test_build_review_manifest_blocks_blank_gaussian_foreground(self):
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
                    view["image_name"] = f"{bucket_label}_{index}.png"
                    view["merged_alpha_stats"] = {
                        "mean": 0.0,
                        "max": 0.0,
                        "coverage_gt_001": 0.0,
                        "coverage_gt_005": 0.0,
                    }
                    view["merged_foreground_stats"] = {
                        "mean_luminance": 0.0,
                        "max_luminance": 0.0,
                        "mean_rgb": 0.0,
                        "max_rgb": 0.0,
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
                merged_background_present=True,
                render_settings=module.RenderSettings(),
            )

            self.assertEqual(manifest["promotion_readiness"]["status"], "blocked")
            self.assertEqual(manifest["render_sanity"]["status"], "blocked")
            self.assertEqual(manifest["render_sanity"]["blank_view_count"], 12)
            self.assertIn(
                "merged gaussian foreground rendered blank for at least one review view",
                manifest["promotion_readiness"]["notes"],
            )


if __name__ == "__main__":
    unittest.main()
