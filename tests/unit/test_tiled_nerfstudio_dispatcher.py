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


if __name__ == "__main__":
    unittest.main()
