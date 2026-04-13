import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path

import numpy as np

try:
    from plyfile import PlyData, PlyElement
except ModuleNotFoundError:
    class PlyElement:
        def __init__(self, data, name: str):
            self.data = data
            self.name = name

        @classmethod
        def describe(cls, data, name: str):
            return cls(data, name)

    class PlyData:
        def __init__(self, elements, text: bool = False):
            self._elements = {element.name: element for element in elements}

        def __getitem__(self, key: str):
            return self._elements[key]

        def write(self, path: str) -> None:
            with open(path, "wb") as handle:
                np.save(handle, self._elements["vertex"].data, allow_pickle=False)

        @classmethod
        def read(cls, path: str):
            with open(path, "rb") as handle:
                vertex_data = np.load(handle, allow_pickle=False)
            return cls([PlyElement(vertex_data, "vertex")])

    sys.modules["plyfile"] = types.SimpleNamespace(PlyData=PlyData, PlyElement=PlyElement)


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "tile_pipeline.py"
SPEC = importlib.util.spec_from_file_location("tile_pipeline_test_module", MODULE_PATH)
tile_pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = tile_pipeline
SPEC.loader.exec_module(tile_pipeline)


def write_test_ply(path: Path, vertices: list[tuple[float, float, float, float]]) -> None:
    vertex_array = np.array(
        vertices,
        dtype=[
            ("x", "f4"),
            ("y", "f4"),
            ("z", "f4"),
            ("opacity", "f4"),
        ],
    )
    PlyData([PlyElement.describe(vertex_array, "vertex")], text=False).write(str(path))


class GaussianTilePipelineTests(unittest.TestCase):
    def test_select_training_image_names_scaffold_and_leaf_tile(self):
        manifest = {
            "all_image_names": ["a.jpg", "b.jpg", "c.jpg", "d.jpg"],
            "global_scaffold_camera_ids": ["a.jpg", "b.jpg", "c.jpg", "d.jpg"],
            "tiles": [
                {
                    "tile_id": "tile_00",
                    "base_camera_ids": ["a.jpg"],
                    "border_camera_ids": ["b.jpg"],
                    "context_camera_ids": ["c.jpg"],
                }
            ],
        }

        scaffold = tile_pipeline.select_training_image_names(
            training_mode="global_scaffold",
            tile_manifest=manifest,
            max_images=2,
            stride=2,
        )
        leaf = tile_pipeline.select_training_image_names(
            training_mode="leaf_tile",
            tile_manifest=manifest,
            tile_id="tile_00",
        )

        self.assertEqual(scaffold, ["a.jpg", "c.jpg"])
        self.assertEqual(leaf, ["a.jpg", "b.jpg", "c.jpg"])

    def test_filter_transforms_frames_filters_split_filename_lists(self):
        transforms = {
            "frames": [
                {"file_path": "./images/a.jpg"},
                {"file_path": "images/b.jpg"},
                {"file_path": "images/c.jpg"},
            ],
            "train_filenames": ["./images/a.jpg", "images/b.jpg"],
            "val_filenames": ["images/c.jpg"],
            "test_filenames": ["images/b.jpg", "images/c.jpg"],
        }

        filtered = tile_pipeline.filter_transforms_frames(transforms, ["b.jpg", "c.jpg"])

        self.assertEqual(
            [Path(frame["file_path"]).name for frame in filtered["frames"]],
            ["b.jpg", "c.jpg"],
        )
        self.assertEqual(filtered["train_filenames"], ["images/b.jpg"])
        self.assertEqual(filtered["val_filenames"], ["images/c.jpg"])
        self.assertEqual(filtered["test_filenames"], ["images/b.jpg", "images/c.jpg"])

    def test_merge_tile_outputs_uses_overlap_fallback_when_core_retains_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tile_dir = root / "tiles" / "tile_00"
            tile_dir.mkdir(parents=True)
            write_test_ply(
                tile_dir / "splat.ply",
                [
                    (1.0, 0.0, 0.0, 0.8),
                    (1.5, 0.0, 0.0, 0.6),
                ],
            )

            report = tile_pipeline.merge_tile_outputs(
                tile_manifest={
                    "tiles": [
                        {
                            "tile_id": "tile_00",
                            "core_bounds": {
                                "min_x": 0.0,
                                "max_x": 0.5,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                            "overlap_bounds": {
                                "min_x": 0.0,
                                "max_x": 2.0,
                                "min_y": -1.0,
                                "max_y": 1.0,
                                "min_z": -1.0,
                                "max_z": 1.0,
                            },
                        }
                    ]
                },
                tile_output_dirs={"tile_00": tile_dir},
                output_dir=root / "merged",
            )

            self.assertEqual(report["retained_gaussians"], 2)
            self.assertEqual(report["tiles"][0]["retention_strategy"], "overlap_bounds_fallback")
            self.assertTrue((root / "merged" / "merged_splat.ply").exists())

    def test_merge_tile_outputs_retains_all_when_bounds_are_degenerate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tile_dir = root / "tiles" / "tile_00"
            tile_dir.mkdir(parents=True)
            write_test_ply(tile_dir / "splat.ply", [(10.0, 0.0, 0.0, 0.9)])

            report = tile_pipeline.merge_tile_outputs(
                tile_manifest={
                    "tiles": [
                        {
                            "tile_id": "tile_00",
                            "core_bounds": {
                                "min_x": 0.0,
                                "max_x": 0.0,
                                "min_y": 0.0,
                                "max_y": 0.0,
                                "min_z": 0.0,
                                "max_z": 0.0,
                            },
                            "overlap_bounds": {
                                "min_x": 0.0,
                                "max_x": 0.0,
                                "min_y": 0.0,
                                "max_y": 0.0,
                                "min_z": 0.0,
                                "max_z": 0.0,
                            },
                        }
                    ]
                },
                tile_output_dirs={"tile_00": tile_dir},
                output_dir=root / "merged",
            )

            self.assertEqual(report["retained_gaussians"], 1)
            self.assertEqual(report["tiles"][0]["retention_strategy"], "retain_all")


if __name__ == "__main__":
    unittest.main()
