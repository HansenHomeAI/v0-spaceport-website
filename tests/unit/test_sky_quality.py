import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from plyfile import PlyData, PlyElement

try:
    from PIL import Image
except ModuleNotFoundError:  # pragma: no cover - optional local dev dependency
    Image = None

try:
    import cv2 as _cv2  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - optional local dev dependency
    _cv2 = None


REPO_ROOT = Path(__file__).resolve().parents[2]
THREE_DGS_ROOT = REPO_ROOT / "infrastructure" / "containers" / "3dgs"
if str(THREE_DGS_ROOT) not in sys.path:
    sys.path.insert(0, str(THREE_DGS_ROOT))

if Image is not None and _cv2 is not None:
    import sky_quality
else:  # pragma: no cover - exercised only when local optional deps are absent
    sky_quality = None


@unittest.skipIf(
    sky_quality is None or sky_quality.cv2 is None,
    "Pillow and opencv-python-headless are required for direct sky pruning tests",
)
class SkyQualityPruningTests(unittest.TestCase):
    def _write_fixture_data(self, root: Path) -> Path:
        data_dir = root / "data"
        images_dir = data_dir / "images"
        images_dir.mkdir(parents=True)
        Image.new("RGB", (16, 16), (51, 140, 255)).save(images_dir / "sky.png")
        transforms = {
            "fl_x": 8.0,
            "fl_y": 8.0,
            "cx": 8.0,
            "cy": 8.0,
            "w": 16,
            "h": 16,
            "frames": [
                {
                    "file_path": "images/sky.png",
                    "transform_matrix": [
                        [1.0, 0.0, 0.0, 0.0],
                        [0.0, 1.0, 0.0, 0.0],
                        [0.0, 0.0, 1.0, 0.0],
                        [0.0, 0.0, 0.0, 1.0],
                    ],
                }
            ],
        }
        (data_dir / "transforms.json").write_text(json.dumps(transforms), encoding="utf-8")
        return data_dir

    def _write_splat(self, path: Path) -> None:
        dtype = [
            ("x", "f4"),
            ("y", "f4"),
            ("z", "f4"),
            ("opacity", "f4"),
            ("f_dc_0", "f4"),
            ("f_dc_1", "f4"),
            ("f_dc_2", "f4"),
        ]
        vertices = np.zeros(2, dtype=dtype)
        vertices["x"] = [0.0, 0.0]
        vertices["y"] = [0.0, 0.0]
        vertices["z"] = [-1.0, -1.0]
        vertices["opacity"] = math.log(0.8 / 0.2)
        colors = np.asarray(
            [
                [51 / 255.0, 140 / 255.0, 1.0],
                [1.0, 0.0, 0.0],
            ],
            dtype=np.float32,
        )
        sh = (colors - 0.5) / sky_quality.SH_C0
        vertices["f_dc_0"] = sh[:, 0]
        vertices["f_dc_1"] = sh[:, 1]
        vertices["f_dc_2"] = sh[:, 2]
        PlyData([PlyElement.describe(vertices, "vertex")], text=False).write(str(path))

    def _write_scale_splat(self, path: Path) -> None:
        dtype = [
            ("x", "f4"),
            ("y", "f4"),
            ("z", "f4"),
            ("opacity", "f4"),
            ("scale_0", "f4"),
            ("scale_1", "f4"),
            ("scale_2", "f4"),
            ("f_dc_0", "f4"),
            ("f_dc_1", "f4"),
            ("f_dc_2", "f4"),
        ]
        vertices = np.zeros(3, dtype=dtype)
        vertices["x"] = [0.0, 1.0, 2.0]
        vertices["opacity"] = math.log(0.8 / 0.2)
        activated_scales = np.asarray(
            [
                [1.0, 1.0, 1.0],
                [4.0, 1.0, 1.0],
                [1.5, 1.5, 1.5],
            ],
            dtype=np.float32,
        )
        raw_scales = np.log(activated_scales)
        vertices["scale_0"] = raw_scales[:, 0]
        vertices["scale_1"] = raw_scales[:, 1]
        vertices["scale_2"] = raw_scales[:, 2]
        PlyData([PlyElement.describe(vertices, "vertex")], text=False).write(str(path))

    def test_sky_color_pruning_removes_sky_colored_splat_when_edge_rule_blocks_legacy_prune(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = self._write_fixture_data(root)
            ply_path = root / "splat.ply"
            self._write_splat(ply_path)

            result = sky_quality.prune_foreground_floaters(
                ply_path=ply_path,
                data_dir=data_dir,
                sampled_views=1,
                min_views=1,
                min_sky_views=1,
                max_opacity=1.01,
                max_color_distance=0.05,
                min_edge_support=0,
                patch_size=3,
                sky_color_pruning_enabled=True,
                sky_color_min_sky_views=1,
                sky_color_max_color_distance=0.05,
            )

            self.assertEqual(result.removed_gaussians, 1)
            self.assertEqual(result.sky_color_removed_gaussians, 1)
            self.assertEqual(result.diagnostics["legacy_removal_candidate_count"], 0)
            self.assertEqual(result.diagnostics["sky_color_removal_candidate_count"], 1)
            retained = PlyData.read(str(ply_path))["vertex"].data
            self.assertEqual(len(retained), 1)
            retained_rgb = sky_quality._gaussian_rgb_from_vertex_data(retained)[0]
            self.assertGreater(retained_rgb[0], 0.9)

    def test_sky_color_pruning_is_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = self._write_fixture_data(root)
            ply_path = root / "splat.ply"
            self._write_splat(ply_path)

            result = sky_quality.prune_foreground_floaters(
                ply_path=ply_path,
                data_dir=data_dir,
                sampled_views=1,
                min_views=1,
                min_sky_views=1,
                max_opacity=1.01,
                max_color_distance=0.05,
                min_edge_support=0,
                patch_size=3,
                sky_color_pruning_enabled=False,
            )

            self.assertEqual(result.removed_gaussians, 0)
            self.assertEqual(result.sky_color_removed_gaussians, 0)
            retained = PlyData.read(str(ply_path))["vertex"].data
            self.assertEqual(len(retained), 2)

    def test_horizon_coverage_pruning_removes_priority_sky_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = self._write_fixture_data(root)
            ply_path = root / "splat.ply"
            dtype = [
                ("x", "f4"),
                ("y", "f4"),
                ("z", "f4"),
                ("opacity", "f4"),
                ("f_dc_0", "f4"),
                ("f_dc_1", "f4"),
                ("f_dc_2", "f4"),
            ]
            vertices = np.zeros(2, dtype=dtype)
            vertices["x"] = [0.0, 1.0]
            vertices["y"] = [-0.8, 0.8]
            vertices["z"] = [-1.0, -1.0]
            vertices["opacity"] = math.log(0.8 / 0.2)
            colors = np.asarray([[1.0, 1.0, 1.0], [1.0, 0.0, 0.0]], dtype=np.float32)
            sh = (colors - 0.5) / sky_quality.SH_C0
            vertices["f_dc_0"] = sh[:, 0]
            vertices["f_dc_1"] = sh[:, 1]
            vertices["f_dc_2"] = sh[:, 2]
            PlyData([PlyElement.describe(vertices, "vertex")], text=False).write(str(ply_path))

            result = sky_quality.prune_foreground_floaters(
                ply_path=ply_path,
                data_dir=data_dir,
                sampled_views=1,
                priority_frame_names=["sky.png"],
                min_views=1,
                min_sky_views=1,
                max_opacity=1.01,
                max_color_distance=0.0,
                min_edge_support=1,
                patch_size=3,
                sky_color_pruning_enabled=False,
                horizon_coverage_pruning_enabled=True,
                horizon_coverage_min_priority_views=1,
                horizon_coverage_min_sky_views=1,
                horizon_coverage_min_top_fraction=0.5,
                horizon_coverage_max_color_distance=1.25,
            )

            self.assertEqual(result.removed_gaussians, 1)
            self.assertEqual(result.sky_color_removed_gaussians, 0)
            self.assertEqual(result.horizon_coverage_removed_gaussians, 1)
            self.assertEqual(result.diagnostics["horizon_coverage_priority_sample_count"], 1)
            self.assertEqual(result.diagnostics["horizon_coverage_removal_candidate_count"], 1)
            retained = PlyData.read(str(ply_path))["vertex"].data
            self.assertEqual(len(retained), 1)
            self.assertIn(1.0, set(float(value) for value in retained["x"]))

    def test_scale_pruning_removes_large_exported_gaussians(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ply_path = root / "splat.ply"
            self._write_scale_splat(ply_path)

            result = sky_quality.prune_gaussian_scale_outliers(
                ply_path=ply_path,
                max_scale=3.5,
                max_volume=0.0,
            )

            self.assertEqual(result.original_gaussians, 3)
            self.assertEqual(result.removed_gaussians, 1)
            self.assertEqual(result.removed_by_scale, 1)
            retained = PlyData.read(str(ply_path))["vertex"].data
            self.assertEqual(len(retained), 2)
            self.assertNotIn(1.0, set(float(value) for value in retained["x"]))


if __name__ == "__main__":
    unittest.main()
