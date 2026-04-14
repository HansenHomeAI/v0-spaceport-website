import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "train_nerfstudio_production.py"


def load_module_with_stubs():
    class FakeImageFile:
        def __init__(self, size):
            self.width, self.height = size
            self.size = size

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def resize(self, size, _resampling):
            return FakeImageFile(size)

        def save(self, path):
            Path(path).write_text(json.dumps({"size": list(self.size)}), encoding="utf-8")

    def fake_open(path):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return FakeImageFile(tuple(payload["size"]))

    def fake_new(_mode, size, color=None):
        return FakeImageFile(size)

    pil_stub = types.SimpleNamespace(
        Image=types.SimpleNamespace(
            open=fake_open,
            new=fake_new,
            Resampling=types.SimpleNamespace(LANCZOS="lanczos"),
            LANCZOS="lanczos",
        )
    )
    torch_stub = types.SimpleNamespace(
        _dynamo=types.SimpleNamespace(
            config=types.SimpleNamespace(suppress_errors=False)
        )
    )
    yaml_stub = types.SimpleNamespace(safe_load=lambda _stream: {})
    sky_quality_stub = types.SimpleNamespace(
        BackgroundSelectionResult=object,
        FloaterPruningResult=object,
        prune_foreground_floaters=lambda *args, **kwargs: None,
        select_background_camera=lambda *args, **kwargs: None,
    )

    def load_json(path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    tile_pipeline_stub = types.SimpleNamespace(
        filter_transforms_frames=lambda transforms, _selected, image_name_map=None: transforms,
        load_json=load_json,
        merge_tile_outputs=lambda **kwargs: {
            "merge_mode": kwargs["merge_mode"],
            "tile_count": len(kwargs["tile_output_dirs"]),
        },
        selection_counts_for_buckets=lambda *_args, **_kwargs: {},
        select_manifest_tile_ids=lambda manifest, explicit_tile_ids=None, max_tiles=None: [
            tile["tile_id"] for tile in manifest["tiles"]
        ][: max_tiles or None],
        select_training_image_names=lambda **_kwargs: [],
        subset_tile_manifest=lambda manifest, selected_tile_ids: {
            **manifest,
            "tiles": [
                dict(tile)
                for tile in manifest.get("tiles", [])
                if tile.get("tile_id") in set(selected_tile_ids)
            ],
        },
    )

    for name, module in {
        "PIL": pil_stub,
        "torch": torch_stub,
        "yaml": yaml_stub,
        "sky_quality": sky_quality_stub,
        "tile_pipeline": tile_pipeline_stub,
    }.items():
        sys.modules[name] = module

    spec = importlib.util.spec_from_file_location("train_nerfstudio_tiled_test_module", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TiledNerfStudioDispatcherTests(unittest.TestCase):
    def test_limit_selected_image_names_preserves_boundary_and_horizon_coverage(self):
        module = load_module_with_stubs()

        limited = module.limit_selected_image_names(
            [
                "frame_00001.JPG",
                "frame_00002.JPG",
                "frame_00003.JPG",
                "frame_00004.JPG",
                "frame_00005.JPG",
                "frame_00006.JPG",
            ],
            view_buckets={
                "boundary_camera_ids": ["frame_00002.JPG", "frame_00004.JPG"],
                "horizon_camera_ids": ["frame_00006.JPG"],
                "near_detail_camera_ids": ["frame_00001.JPG", "frame_00003.JPG"],
            },
            max_images=4,
            selection_stride=1,
        )

        self.assertEqual(limited[:3], ["frame_00002.JPG", "frame_00004.JPG", "frame_00006.JPG"])
        self.assertEqual(len(limited), 4)
        self.assertIn(limited[3], {"frame_00001.JPG", "frame_00003.JPG"})

    def test_run_tiled_training_pipeline_writes_root_summary(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_input = root / "source"
            output_dir = root / "output"
            canonical_dir = root / "canonical"
            source_input.mkdir()
            output_dir.mkdir()
            (canonical_dir / "images").mkdir(parents=True)
            (canonical_dir / "transforms.json").write_text(json.dumps({"frames": []}), encoding="utf-8")
            (source_input / "3dgs_tile_manifest.json").write_text(
                json.dumps(
                    {
                        "tiles": [
                            {"tile_id": "tile_00"},
                            {"tile_id": "tile_01"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (source_input / "3dgs_view_buckets.json").write_text(
                json.dumps({"boundary_camera_ids": []}),
                encoding="utf-8",
            )

            trainer = module.NerfStudioTrainer.__new__(module.NerfStudioTrainer)
            trainer.config = {
                "tiling": {
                    "training_mode": "tiled_pipeline",
                    "tile_manifest_path": "3dgs_tile_manifest.json",
                    "view_bucket_manifest_path": "3dgs_view_buckets.json",
                    "merge": {"mode": "strict_core"},
                    "pipeline": {
                        "max_tiles": 1,
                        "tile_ids": "",
                        "include_scaffold": True,
                        "include_merge": True,
                        "resume_existing": True,
                    },
                }
            }
            trainer.config_path = str(REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "nerfstudio_config.yaml")
            trainer.input_dir = source_input
            trainer.output_dir = output_dir
            trainer.temp_dir = root / "tmp"
            trainer.background_selection_result = None
            trainer.floater_pruning_result = None
            trainer.training_selection_result = None

            def fake_validate():
                trainer.input_dir = canonical_dir
                return True

            def fake_prepare(**kwargs):
                stage_input_dir = kwargs["stage_input_dir"]
                stage_input_dir.mkdir(parents=True, exist_ok=True)

            def fake_stage(**kwargs):
                stage_output_dir = kwargs["stage_output_dir"]
                stage_output_dir.mkdir(parents=True, exist_ok=True)
                return {
                    "stage_name": kwargs["stage_name"],
                    "training_mode": kwargs["training_mode"],
                    "tile_id": kwargs.get("tile_id"),
                }

            trainer.validate_input_data = fake_validate
            trainer.prepare_tiled_stage_dataset = fake_prepare
            trainer.run_prepared_training_stage = fake_stage

            success = trainer.run_tiled_training_pipeline()

            self.assertTrue(success)
            root_metadata = json.loads((output_dir / "training_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(root_metadata["training_mode"], "tiled_pipeline")
            self.assertEqual(root_metadata["selected_tile_ids"], ["tile_00"])
            self.assertEqual(root_metadata["merge"]["tile_count"], 1)

    def test_run_nerfstudio_training_retries_with_explicit_dataparser_on_tyro_order_error(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trainer = module.NerfStudioTrainer.__new__(module.NerfStudioTrainer)
            trainer.config = {
                "model": {
                    "variant": "splatfacto-w-light",
                    "sh_degree": 3,
                    "bilateral_processing": True,
                    "rasterize_mode": "classic",
                    "use_scale_regularization": True,
                    "cull_alpha_thresh": 0.12,
                    "cull_scale_thresh": 0.35,
                    "enable_bg_model": True,
                    "enable_alpha_loss": True,
                    "enable_robust_mask": True,
                    "bg_sh_degree": 8,
                    "appearance_embed_dim": 64,
                    "never_mask_upper": 0.4,
                },
                "training": {
                    "max_iterations": 100,
                    "log_interval": 10,
                },
                "tiling": {
                    "training_mode": "monolithic",
                    "global_scaffold": {},
                },
            }
            trainer.input_dir = root / "input"
            trainer.output_dir = root / "output"
            trainer.temp_dir = root / "tmp"
            trainer.training_selection_result = None
            trainer.background_selection_result = None
            trainer.floater_pruning_result = None
            trainer.resolve_training_mode = lambda: "monolithic"

            calls: list[list[str]] = []

            def fake_run(cmd, **kwargs):
                calls.append(list(cmd))
                if len(calls) == 1:
                    return types.SimpleNamespace(
                        returncode=2,
                        stdout="",
                        stderr=(
                            "Unrecognized or misplaced options\n"
                            "Arguments are applied to the directly preceding subcommand\n"
                        ),
                    )
                return types.SimpleNamespace(returncode=0, stdout="done\n", stderr="")

            original_run = module.subprocess.run
            module.subprocess.run = fake_run
            try:
                success = trainer.run_nerfstudio_training()
            finally:
                module.subprocess.run = original_run

            self.assertTrue(success)
            self.assertEqual(len(calls), 2)
            self.assertIn("--data", calls[0])
            self.assertNotIn("nerfstudio-data", calls[0])
            self.assertIn("nerfstudio-data", calls[1])
            self.assertEqual(calls[1][-2:], ["--data", str(trainer.input_dir)])
            self.assertNotIn("--pipeline.model.use-bilateral-grid", calls[0])
            self.assertNotIn("--pipeline.model.use-bilateral-grid", calls[1])

    def test_run_nerfstudio_training_small_proof_run_suppresses_eval_and_save_cadence(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trainer = module.NerfStudioTrainer.__new__(module.NerfStudioTrainer)
            trainer.config = {
                "model": {
                    "variant": "splatfacto-w-light",
                    "sh_degree": 3,
                    "bilateral_processing": False,
                    "rasterize_mode": "classic",
                    "use_scale_regularization": True,
                    "cull_alpha_thresh": 0.12,
                    "cull_scale_thresh": 0.35,
                    "enable_bg_model": True,
                    "enable_alpha_loss": True,
                    "enable_robust_mask": True,
                    "bg_sh_degree": 8,
                    "appearance_embed_dim": 64,
                    "never_mask_upper": 0.4,
                },
                "training": {
                    "max_iterations": 50,
                    "log_interval": 10,
                    "steps_per_eval_image": 100,
                    "steps_per_eval_all_images": 1000,
                    "steps_per_save": 2000,
                },
                "tiling": {
                    "training_mode": "leaf_tile",
                    "global_scaffold": {},
                },
            }
            trainer.input_dir = root / "input"
            trainer.output_dir = root / "output"
            trainer.temp_dir = root / "tmp"
            trainer.training_selection_result = None
            trainer.background_selection_result = None
            trainer.floater_pruning_result = None
            trainer.resolve_training_mode = lambda: "leaf_tile"

            calls: list[list[str]] = []

            def fake_run(cmd, **kwargs):
                calls.append(list(cmd))
                return types.SimpleNamespace(returncode=0, stdout="done\n", stderr="")

            original_run = module.subprocess.run
            module.subprocess.run = fake_run
            try:
                success = trainer.run_nerfstudio_training()
            finally:
                module.subprocess.run = original_run

            self.assertTrue(success)
            self.assertEqual(len(calls), 1)
            self.assertIn("--viewer.quit_on_train_completion", calls[0])
            self.assertIn("True", calls[0])
            self.assertIn("--steps_per_eval_image", calls[0])
            self.assertIn("--steps_per_eval_all_images", calls[0])
            self.assertIn("--steps_per_save", calls[0])
            self.assertIn("51", calls[0])

    def test_run_nerfstudio_training_honors_vis_mode_override(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trainer = module.NerfStudioTrainer.__new__(module.NerfStudioTrainer)
            trainer.config = {
                "model": {
                    "variant": "splatfacto-w-light",
                    "sh_degree": 3,
                    "bilateral_processing": False,
                    "rasterize_mode": "classic",
                    "use_scale_regularization": True,
                    "cull_alpha_thresh": 0.12,
                    "cull_scale_thresh": 0.35,
                    "enable_bg_model": True,
                    "enable_alpha_loss": True,
                    "enable_robust_mask": True,
                    "bg_sh_degree": 8,
                    "appearance_embed_dim": 64,
                    "never_mask_upper": 0.4,
                },
                "training": {
                    "max_iterations": 10,
                    "log_interval": 1,
                    "vis_mode": "viewer",
                },
                "tiling": {
                    "training_mode": "leaf_tile",
                    "global_scaffold": {},
                },
            }
            trainer.input_dir = root / "input"
            trainer.output_dir = root / "output"
            trainer.temp_dir = root / "tmp"
            trainer.training_selection_result = None
            trainer.background_selection_result = None
            trainer.floater_pruning_result = None
            trainer.resolve_training_mode = lambda: "leaf_tile"

            calls: list[list[str]] = []

            def fake_run(cmd, **kwargs):
                calls.append(list(cmd))
                return types.SimpleNamespace(returncode=0, stdout="done\n", stderr="")

            original_run = module.subprocess.run
            module.subprocess.run = fake_run
            try:
                success = trainer.run_nerfstudio_training()
            finally:
                module.subprocess.run = original_run

            self.assertTrue(success)
            self.assertEqual(len(calls), 1)
            self.assertIn("--vis", calls[0])
            self.assertEqual(calls[0][calls[0].index("--vis") + 1], "viewer")

    def test_run_nerfstudio_training_honors_datamanager_cache_overrides(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trainer = module.NerfStudioTrainer.__new__(module.NerfStudioTrainer)
            trainer.config = {
                "model": {
                    "variant": "splatfacto-w-light",
                    "sh_degree": 3,
                    "bilateral_processing": False,
                    "rasterize_mode": "classic",
                    "use_scale_regularization": True,
                    "cull_alpha_thresh": 0.12,
                    "cull_scale_thresh": 0.35,
                    "enable_bg_model": True,
                    "enable_alpha_loss": True,
                    "enable_robust_mask": True,
                    "bg_sh_degree": 8,
                    "appearance_embed_dim": 64,
                    "never_mask_upper": 0.4,
                },
                "training": {
                    "max_iterations": 10,
                    "log_interval": 1,
                    "cache_images": "cpu",
                    "cache_images_type": "uint8",
                    "dataloader_num_workers": 0,
                },
                "tiling": {
                    "training_mode": "leaf_tile",
                    "global_scaffold": {},
                },
            }
            trainer.input_dir = root / "input"
            trainer.output_dir = root / "output"
            trainer.temp_dir = root / "tmp"
            trainer.training_selection_result = None
            trainer.background_selection_result = None
            trainer.floater_pruning_result = None
            trainer.resolve_training_mode = lambda: "leaf_tile"

            calls: list[list[str]] = []

            def fake_run(cmd, **kwargs):
                calls.append(list(cmd))
                return types.SimpleNamespace(returncode=0, stdout="done\n", stderr="")

            original_run = module.subprocess.run
            module.subprocess.run = fake_run
            try:
                success = trainer.run_nerfstudio_training()
            finally:
                module.subprocess.run = original_run

            self.assertTrue(success)
            self.assertEqual(len(calls), 1)
            self.assertIn("--pipeline.datamanager.cache-images", calls[0])
            self.assertIn("cpu", calls[0])
            self.assertIn("--pipeline.datamanager.cache-images-type", calls[0])
            self.assertIn("uint8", calls[0])
            self.assertIn("--pipeline.datamanager.dataloader-num-workers", calls[0])
            self.assertIn("0", calls[0])

    def test_build_sparse_point_cloud_ply_writes_ascii_vertices(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            points_txt = root / "points3D.txt"
            points_txt.write_text(
                "\n".join(
                    [
                        "# comment",
                        "1 1.0 2.0 3.0 255 128 64 0.1 1 1",
                        "2 4.0 5.0 6.0 10 20 30 0.2 2 3",
                    ]
                ),
                encoding="utf-8",
            )
            output_ply = root / "sparse_pc.ply"

            written = module.NerfStudioTrainer.build_sparse_point_cloud_ply(points_txt, output_ply)

            self.assertTrue(written)
            contents = output_ply.read_text(encoding="utf-8")
            self.assertIn("element vertex 2", contents)
            self.assertIn("1.0 2.0 3.0 255 128 64", contents)
            self.assertIn("4.0 5.0 6.0 10 20 30", contents)

    def test_downscale_selected_training_data_if_requested_resizes_images_and_intrinsics(self):
        module = load_module_with_stubs()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical_images = root / "canonical_images"
            canonical_images.mkdir()
            image_path = canonical_images / "frame_00001.JPG"
            module.Image.new("RGB", (800, 400), color=(64, 128, 192)).save(image_path)

            stage_input = root / "stage_input"
            stage_input.mkdir()
            (stage_input / "images").symlink_to(canonical_images, target_is_directory=True)
            transforms = {
                "fl_x": 800.0,
                "fl_y": 800.0,
                "cx": 400.0,
                "cy": 200.0,
                "w": 800,
                "h": 400,
                "frames": [
                    {
                        "file_path": "images/frame_00001.JPG",
                        "fl_x": 800.0,
                        "fl_y": 800.0,
                        "cx": 400.0,
                        "cy": 200.0,
                        "w": 800,
                        "h": 400,
                    }
                ],
            }
            (stage_input / "transforms.json").write_text(json.dumps(transforms), encoding="utf-8")

            trainer = module.NerfStudioTrainer.__new__(module.NerfStudioTrainer)
            trainer.config = {"training": {"downscale_factor": 4}}
            trainer.input_dir = stage_input
            trainer.training_selection_result = {}

            trainer.downscale_selected_training_data_if_requested()

            updated = json.loads((stage_input / "transforms.json").read_text(encoding="utf-8"))
            self.assertEqual(updated["stage_downscale_factor"], 4)
            self.assertEqual(updated["w"], 200)
            self.assertEqual(updated["h"], 100)
            self.assertEqual(updated["frames"][0]["w"], 200)
            self.assertEqual(updated["frames"][0]["h"], 100)
            self.assertEqual(updated["frames"][0]["cx"], 100.0)
            self.assertEqual(trainer.training_selection_result["downscale_factor"], 4)
            downscaled_image = stage_input / "images" / "frame_00001.JPG"
            self.assertTrue(downscaled_image.exists())
            with module.Image.open(downscaled_image) as image:
                self.assertEqual(image.size, (200, 100))
            self.assertTrue((stage_input / "transforms.pre_downscale.json").exists())


if __name__ == "__main__":
    unittest.main()
