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
    import numpy as numpy_stub
    stubbed_modules = {
        "numpy",
        "torch",
        "PIL",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "plyfile",
        "skimage",
        "skimage.metrics",
        "gsplat",
        "geometry_review",
        "sky_quality",
        "tile_pipeline",
        "train_nerfstudio_production",
    }
    original_modules = {name: sys.modules.get(name) for name in stubbed_modules}
    torch_stub = types.ModuleType("torch")
    pil_stub = types.ModuleType("PIL")
    pil_image_draw_stub = types.ModuleType("PIL.ImageDraw")
    pil_image_font_stub = types.ModuleType("PIL.ImageFont")
    plyfile_stub = types.ModuleType("plyfile")
    skimage_stub = types.ModuleType("skimage")
    skimage_metrics_stub = types.ModuleType("skimage.metrics")
    gsplat_stub = types.ModuleType("gsplat")
    geometry_review_stub = types.ModuleType("geometry_review")
    sky_quality_stub = types.ModuleType("sky_quality")
    tile_pipeline_stub = types.ModuleType("tile_pipeline")
    trainer_stub = types.ModuleType("train_nerfstudio_production")

    pil_stub.Image = types.SimpleNamespace()
    pil_image_draw_stub.Draw = lambda *_args, **_kwargs: types.SimpleNamespace(text=lambda *_a, **_k: None)
    pil_image_font_stub.load_default = lambda: None
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
    trainer_stub.prepare_colmap_subset_for_image_names = lambda *_args, **_kwargs: {"enabled": False}

    for name, module in {
        "numpy": numpy_stub,
        "torch": torch_stub,
        "PIL": pil_stub,
        "PIL.ImageDraw": pil_image_draw_stub,
        "PIL.ImageFont": pil_image_font_stub,
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
    try:
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    finally:
        for name, original_module in original_modules.items():
            if original_module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original_module
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
    def test_parse_tile_render_buckets_supports_default_and_horizon(self):
        module = load_module_with_stubs()

        self.assertEqual(module.parse_tile_render_buckets(""), {"boundary"})
        self.assertEqual(module.parse_tile_render_buckets("horizon,boundary"), {"boundary", "horizon"})
        self.assertEqual(module.parse_tile_render_buckets("all"), {"near_detail", "boundary", "horizon"})
        with self.assertRaises(ValueError):
            module.parse_tile_render_buckets("bad_bucket")

    def test_resolve_tile_render_ids_uses_all_selected_for_horizon(self):
        module = load_module_with_stubs()

        manifest = {
            "tiles": [
                {
                    "tile_id": "tile_00",
                    "base_camera_ids": ["a.JPG"],
                    "neighbor_tile_ids": ["tile_07"],
                },
                {
                    "tile_id": "tile_07",
                    "base_camera_ids": ["b.JPG"],
                    "neighbor_tile_ids": ["tile_00"],
                },
            ]
        }

        self.assertEqual(
            module.resolve_tile_render_ids(
                manifest,
                ["tile_00", "tile_07"],
                "DJI_00809.JPG",
                "horizon",
                2,
            ),
            ["tile_00", "tile_07"],
        )
        self.assertEqual(
            module.resolve_tile_render_ids(manifest, ["tile_00", "tile_07"], "a.JPG", "boundary", 2),
            ["tile_00", "tile_07"],
        )

    def test_decode_ply_sh_rest_converts_channel_major_to_basis_major_rgb(self):
        module = load_module_with_stubs()

        sh_rest = module.decode_ply_sh_rest(
            module.np.array([[10.0, 11.0, 20.0, 21.0, 30.0, 31.0]], dtype=module.np.float32),
            source="unit-test.ply",
        )

        self.assertEqual(sh_rest.shape, (1, 2, 3))
        self.assertEqual(sh_rest.tolist(), [[[10.0, 20.0, 30.0], [11.0, 21.0, 31.0]]])

    def test_decode_ply_sh_rest_rejects_invalid_width(self):
        module = load_module_with_stubs()

        with self.assertRaisesRegex(RuntimeError, "Unexpected SH payload width"):
            module.decode_ply_sh_rest(
                module.np.array([[1.0, 2.0, 3.0, 4.0]], dtype=module.np.float32),
                source="bad-width.ply",
            )

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

    def test_backfill_review_manifests_from_model_copies_missing_manifests(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_dir = root / "model"
            review_dir = root / "review"
            model_dir.mkdir()
            review_dir.mkdir()
            (model_dir / "3dgs_tile_manifest.json").write_text('{"tiles":[]}', encoding="utf-8")
            (model_dir / "3dgs_view_buckets.json").write_text('{"near_detail_camera_ids":[]}', encoding="utf-8")
            (review_dir / "sfm_metadata.json").write_text('{"source":"colmap"}', encoding="utf-8")

            summary = module.backfill_review_manifests_from_model(model_dir, review_dir)

            self.assertIn("3dgs_tile_manifest.json", summary["copied"])
            self.assertIn("3dgs_view_buckets.json", summary["copied"])
            self.assertIn("sfm_metadata.json", summary["already_present"])
            self.assertTrue((review_dir / "3dgs_tile_manifest.json").exists())
            self.assertTrue((review_dir / "3dgs_view_buckets.json").exists())
            self.assertEqual(
                json.loads((review_dir / "sfm_metadata.json").read_text(encoding="utf-8")),
                {"source": "colmap"},
            )

    def test_planner_frame_review_camera_uses_colmap_pose(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_dir = root / "model"
            tile_dir = model_dir / "tiles" / "tile_00"
            sparse_dir = root / "review" / "sparse" / "0"
            tile_dir.mkdir(parents=True)
            sparse_dir.mkdir(parents=True)
            (tile_dir / "export_manifest.json").write_text(
                json.dumps(
                    {
                        "foreground_coordinate_frame": "planner",
                        "foreground_transform": {
                            "planner_transform_applied": True,
                            "planner_transform": [
                                [1.0, 0.0, 0.0, 0.0],
                                [0.0, 1.0, 0.0, 0.0],
                                [0.0, 0.0, 1.0, 0.0],
                            ],
                            "planner_scale": 1.0,
                            "planner_offset": [0.0, 0.0, 0.0],
                        },
                    }
                ),
                encoding="utf-8",
            )
            (sparse_dir / "images.txt").write_text(
                "1 1 0 0 0 10 20 30 1 DJI_0001.JPG\n\n",
                encoding="utf-8",
            )

            planner_frame = module.load_planner_frame_transform(model_dir)
            poses = module.load_colmap_world_to_camera_by_name(sparse_dir / "images.txt")
            world_to_camera, source = module.foreground_world_to_camera_for_image(
                image_name="DJI_0001.JPG",
                frame={"transform_matrix": [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]},
                planner_frame=planner_frame,
                colmap_world_to_camera_by_name=poses,
            )

            self.assertEqual(source, "colmap_planner_frame")
            self.assertEqual(world_to_camera[:3, 3].tolist(), [10.0, 20.0, 30.0])

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

    def test_load_frozen_review_images_treats_named_frozen_sets_as_auto(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "review_camera_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "buckets": {
                            "near_detail": ["near_full_0", "near_full_1", "near_full_2", "near_full_3", "near_full_4"],
                            "boundary": [
                                "boundary_full_0",
                                "boundary_full_1",
                                "boundary_full_2",
                                "boundary_full_3",
                                "boundary_full_4",
                            ],
                            "horizon": [
                                "horizon_full_0",
                                "horizon_full_1",
                                "horizon_full_2",
                                "horizon_full_3",
                                "horizon_full_4",
                            ],
                        },
                        "smoke_buckets": {
                            "near_detail": ["near_smoke_0", "near_smoke_1"],
                            "boundary": ["boundary_smoke_0"],
                            "horizon": ["horizon_smoke_0"],
                        },
                    }
                ),
                encoding="utf-8",
            )

            selected = module.load_frozen_review_images_by_bucket(
                manifest_path,
                max_images_per_bucket=4,
                camera_set="frozen-promotion-p24",
            )

            self.assertEqual(
                selected,
                {
                    "near_detail_camera_ids": ["near_smoke_0", "near_smoke_1"],
                    "boundary_camera_ids": ["boundary_smoke_0"],
                    "horizon_camera_ids": ["horizon_smoke_0"],
                },
            )

    def test_review_images_for_preconversion_flattens_frozen_camera_set(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "review_camera_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "smoke_buckets": {
                            "near_detail": ["near_0.JPG", "shared.JPG"],
                            "boundary": ["boundary_0.JPG", "shared.JPG"],
                            "horizon": ["horizon_0.JPG", "horizon_1.JPG"],
                        },
                    }
                ),
                encoding="utf-8",
            )

            selected = module.review_images_for_preconversion(
                manifest_path,
                max_images_per_bucket=4,
                review_camera_set="smoke",
            )

            self.assertEqual(
                selected,
                ["near_0.JPG", "shared.JPG", "boundary_0.JPG", "horizon_0.JPG", "horizon_1.JPG"],
            )

    def test_prepare_review_preconversion_input_uses_subset_summary(self):
        module = load_module_with_stubs()
        calls = []

        def fake_subset(source_input_dir, subset_input_dir, selected_image_names):
            calls.append((source_input_dir, subset_input_dir, list(selected_image_names)))
            return {
                "enabled": True,
                "subset_input_dir": str(subset_input_dir),
                "selected_image_count": len(selected_image_names),
                "missing_image_count": 0,
            }

        module.prepare_colmap_subset_for_image_names = fake_subset

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            selected_dir, summary = module.prepare_review_preconversion_input_dir(
                root / "source",
                root / "tmp",
                ["a.JPG", "b.JPG"],
            )

            self.assertEqual(selected_dir, root / "tmp" / "review_preconversion_selected_input")
            self.assertTrue(summary["enabled"])
            self.assertEqual(summary["selected_image_count"], 2)
            self.assertEqual(calls[0][2], ["a.JPG", "b.JPG"])

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

    def test_build_visual_qa_manifest_lists_panels_and_ai_schema(self):
        module = load_module_with_stubs()

        manifest = module.build_visual_qa_manifest(
            model_tarball=Path("/tmp/model.tar.gz"),
            selected_tile_ids=["tile_04", "tile_10"],
            output_dir=Path("/tmp/review-output"),
            quality_review_manifest_path=Path("/tmp/review-output/quality_review_manifest.json"),
            review_views=[
                {
                    "bucket": "boundary",
                    "image_name": "DJI_0068.JPG",
                    "reference_image": "/tmp/review-output/quality_review/reference/boundary/DJI_0068.JPG",
                    "merged_render": "/tmp/review-output/quality_review/merged/boundary/DJI_0068.png",
                    "merged_no_background_render": "/tmp/review-output/quality_review/merged_no_background/boundary/DJI_0068.png",
                    "visual_diff_heatmap": "/tmp/review-output/quality_review/diff_heatmaps/boundary/DJI_0068.png",
                    "visual_side_by_side_panel": "/tmp/review-output/quality_review/visual_panels/boundary/DJI_0068.png",
                    "boundary_composite": "/tmp/review-output/quality_review/boundary_composites/DJI_0068.png",
                    "metrics": {"psnr": 29.0, "ssim": 0.91, "lpips": 0.07},
                    "difference_stats": {"mean_abs_rgb_error": 0.04},
                    "boundary_context_tile_ids": ["tile_04", "tile_10"],
                }
            ],
        )

        self.assertEqual(manifest["view_count"], 1)
        self.assertEqual(manifest["panel_count"], 1)
        self.assertTrue(manifest["ai_review_required"])
        self.assertEqual(manifest["bucket_counts"], {"boundary": 1})
        self.assertEqual(
            manifest["views"][0]["assets"]["side_by_side_panel"]["artifact_relative_path"],
            "quality_review/visual_panels/boundary/DJI_0068.png",
        )
        self.assertIn("blocking_defects", manifest["ai_review_response_schema"]["required"])

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

    def test_build_review_manifest_blocks_horizon_foreground_saturation(self):
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
                        "mean": 0.997 if bucket_label == "horizon" else 0.35,
                        "max": 1.0,
                        "coverage_gt_001": 1.0,
                        "coverage_gt_005": 1.0 if bucket_label == "horizon" else 0.42,
                    }
                    view["merged_foreground_stats"] = {
                        "mean_luminance": 0.72,
                        "max_luminance": 0.95,
                        "mean_rgb": 0.70,
                        "max_rgb": 0.99,
                    }
                    if bucket_label == "horizon":
                        view["sky_metrics_no_background"] = {
                            "luminance": 0.73,
                            "saturation": 0.18,
                            "blue_dominance": 0.64,
                        }
                    review_views.append(view)

            manifest = module.build_review_manifest(
                model_tarball=root / "model.tar.gz",
                selected_tile_ids=["tile_00", "tile_07"],
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
            self.assertEqual(manifest["render_sanity"]["horizon_foreground_saturation_count"], 4)
            self.assertIn(
                "horizon review has opaque sky-like foreground splats",
                manifest["promotion_readiness"]["notes"],
            )


if __name__ == "__main__":
    unittest.main()
