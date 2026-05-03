import importlib.util
import json
import math
import sys
import tempfile
import types
import unittest
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "export_splatfacto_w_assets.py"


def load_module_with_stubs():
    torch_stub = types.SimpleNamespace()
    pil_stub = types.SimpleNamespace(Image=types.SimpleNamespace())
    gsplat_stub = types.SimpleNamespace(spherical_harmonics=lambda *args, **kwargs: None)
    eval_stub = types.SimpleNamespace(eval_setup=lambda *_args, **_kwargs: None)

    for name, module in {
        "numpy": np,
        "torch": torch_stub,
        "PIL": pil_stub,
        "PIL.Image": pil_stub.Image,
        "gsplat": types.SimpleNamespace(),
        "gsplat.cuda": types.SimpleNamespace(),
        "gsplat.cuda._wrapper": gsplat_stub,
        "nerfstudio": types.SimpleNamespace(),
        "nerfstudio.utils": types.SimpleNamespace(),
        "nerfstudio.utils.eval_utils": eval_stub,
    }.items():
        sys.modules[name] = module

    spec = importlib.util.spec_from_file_location("export_splatfacto_w_assets_test_module", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ExportSplatfactoWAssetsTests(unittest.TestCase):
    def test_positions_to_original_space_inverts_dataparser_transform_and_scale(self):
        module = load_module_with_stubs()
        pipeline = types.SimpleNamespace(
            datamanager=types.SimpleNamespace(
                train_dataparser_outputs=types.SimpleNamespace(
                    dataparser_transform=np.array(
                        [
                            [1.0, 0.0, 0.0, 10.0],
                            [0.0, 1.0, 0.0, -4.0],
                            [0.0, 0.0, 1.0, 2.0],
                        ],
                        dtype=np.float32,
                    ),
                    dataparser_scale=2.0,
                )
            )
        )
        positions = np.array([[24.0, -4.0, 10.0]], dtype=np.float32)

        transformed, metadata = module.positions_to_original_space(positions, pipeline)

        np.testing.assert_allclose(transformed, np.array([[2.0, 2.0, 3.0]], dtype=np.float32))
        self.assertTrue(metadata["applied"])
        self.assertEqual(metadata["coordinate_frame"], "original")
        self.assertEqual(metadata["dataparser_scale"], 2.0)
        self.assertTrue(metadata["position_transform_applied"])

    def test_original_space_scale_and_quaternion_adjustments(self):
        module = load_module_with_stubs()
        angle = math.pi / 2.0
        rotation_z = np.array(
            [
                [math.cos(angle), -math.sin(angle), 0.0, 0.0],
                [math.sin(angle), math.cos(angle), 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
            ],
            dtype=np.float32,
        )
        metadata = {
            "position_transform_applied": True,
            "dataparser_scale": 2.0,
            "dataparser_transform": rotation_z.tolist(),
        }

        raw_scales = np.array([[0.0, math.log(4.0), math.log(8.0)]], dtype=np.float32)
        transformed_scales = module.log_scales_to_original_space(raw_scales, metadata)
        np.testing.assert_allclose(
            transformed_scales,
            np.array([[math.log(0.5), math.log(2.0), math.log(4.0)]], dtype=np.float32),
            rtol=1e-6,
        )
        self.assertTrue(metadata["scale_transform_applied"])

        transformed_quats = module.quaternions_to_original_space(
            np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32),
            metadata,
        )
        transformed_matrix = module._quaternions_to_rotation_matrices(transformed_quats)[0]
        expected_matrix = rotation_z[:, :3].T
        np.testing.assert_allclose(transformed_matrix, expected_matrix, atol=1e-6)
        self.assertTrue(metadata["rotation_transform_applied"])

    def test_planner_space_applies_transforms_json_frame(self):
        module = load_module_with_stubs()
        with tempfile.TemporaryDirectory() as temp_dir:
            transforms_path = Path(temp_dir) / "transforms.json"
            transforms_path.write_text(
                json.dumps(
                    {
                        "applied_transform": [
                            [1.0, 0.0, 0.0, 0.0],
                            [0.0, 0.0, 1.0, 0.0],
                            [0.0, -1.0, 0.0, 0.0],
                        ],
                        "scale": 3.0,
                        "offset": [1.0, 2.0, 3.0],
                    }
                ),
                encoding="utf-8",
            )
            pipeline = types.SimpleNamespace(
                datamanager=types.SimpleNamespace(
                    dataparser=types.SimpleNamespace(
                        config=types.SimpleNamespace(data=Path(temp_dir)),
                    ),
                    train_dataparser_outputs=types.SimpleNamespace(
                        dataparser_transform=np.array(
                            [
                                [1.0, 0.0, 0.0, 10.0],
                                [0.0, 1.0, 0.0, -4.0],
                                [0.0, 0.0, 1.0, 2.0],
                            ],
                            dtype=np.float32,
                        ),
                        dataparser_scale=2.0,
                    ),
                )
            )

            positions = np.array([[24.0, -4.0, 10.0]], dtype=np.float32)
            transformed, metadata = module.positions_to_planner_space(positions, pipeline)

        np.testing.assert_allclose(transformed, np.array([[7.0, 11.0, -3.0]], dtype=np.float32))
        self.assertEqual(metadata["coordinate_frame"], "planner")
        self.assertTrue(metadata["position_transform_applied"])
        self.assertTrue(metadata["planner_transform_applied"])
        self.assertEqual(metadata["planner_scale"], 3.0)

    def test_planner_space_scale_and_quaternion_adjustments(self):
        module = load_module_with_stubs()
        angle = math.pi / 2.0
        rotation_z = np.array(
            [
                [math.cos(angle), -math.sin(angle), 0.0, 0.0],
                [math.sin(angle), math.cos(angle), 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
            ],
            dtype=np.float32,
        )
        planner_rotation = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0],
                [0.0, -1.0, 0.0],
            ],
            dtype=np.float32,
        )
        metadata = {
            "coordinate_frame": "planner",
            "position_transform_applied": True,
            "planner_transform_applied": True,
            "dataparser_scale": 2.0,
            "planner_scale": 3.0,
            "dataparser_transform": rotation_z.tolist(),
            "model_to_output_linear": (1.5 * planner_rotation @ rotation_z[:, :3].T).tolist(),
        }

        raw_scales = np.array([[0.0, math.log(4.0), math.log(8.0)]], dtype=np.float32)
        transformed_scales = module.log_scales_to_output_space(raw_scales, metadata)
        np.testing.assert_allclose(
            transformed_scales,
            np.array([[math.log(1.5), math.log(6.0), math.log(12.0)]], dtype=np.float32),
            rtol=1e-6,
        )
        self.assertTrue(metadata["planner_scale_transform_applied"])

        transformed_quats = module.quaternions_to_output_space(
            np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32),
            metadata,
        )
        transformed_matrix = module._quaternions_to_rotation_matrices(transformed_quats)[0]
        expected_matrix = planner_rotation @ rotation_z[:, :3].T
        np.testing.assert_allclose(transformed_matrix, expected_matrix, atol=1e-6)
        self.assertTrue(metadata["rotation_transform_applied"])

    def test_appearance_camera_index_clamps_to_embedding_table(self):
        module = load_module_with_stubs()
        model = types.SimpleNamespace(appearance_embeds=types.SimpleNamespace(num_embeddings=4))

        safe_idx, metadata = module.resolve_appearance_camera_idx(model, 9)

        self.assertEqual(safe_idx, 3)
        self.assertEqual(metadata["requested_camera_idx"], 9)
        self.assertEqual(metadata["appearance_camera_idx"], 3)
        self.assertEqual(metadata["appearance_num_embeddings"], 4)
        self.assertTrue(metadata["appearance_camera_clamped"])

    def test_foreground_export_uses_clamped_appearance_camera_index(self):
        module = load_module_with_stubs()

        class FakeTensor:
            def __init__(self, array):
                self.array = np.asarray(array, dtype=np.float32)

            def detach(self):
                return self

            def cpu(self):
                return self

            def numpy(self):
                return self.array

            def contiguous(self):
                return self

            def transpose(self, axis_a, axis_b):
                return FakeTensor(np.swapaxes(self.array, axis_a, axis_b))

            def reshape(self, shape):
                return FakeTensor(self.array.reshape(shape))

        class FakeModel:
            def __init__(self):
                self.appearance_embeds = types.SimpleNamespace(num_embeddings=2)
                self.camera_indices = []
                self.means = FakeTensor([[1.0, 2.0, 3.0]])
                self.opacities = FakeTensor([[0.5]])
                self.scales = FakeTensor([[0.0, 0.1, 0.2]])
                self.quats = FakeTensor([[1.0, 0.0, 0.0, 0.0]])

            def set_camera_idx(self, camera_idx):
                self.camera_indices.append(camera_idx)

            @property
            def shs_0(self):
                self.assert_safe_camera()
                return FakeTensor([[0.1, 0.2, 0.3]])

            @property
            def shs_rest(self):
                self.assert_safe_camera()
                return FakeTensor(np.zeros((1, 0, 3), dtype=np.float32))

            def assert_safe_camera(self):
                if self.camera_indices[-1] >= self.appearance_embeds.num_embeddings:
                    raise AssertionError("appearance camera index was not clamped")

        with tempfile.TemporaryDirectory() as temp_dir:
            _, metadata = module.build_foreground_ply(
                FakeModel(),
                Path(temp_dir),
                9,
            )

        self.assertEqual(metadata["appearance"]["requested_camera_idx"], 9)
        self.assertEqual(metadata["appearance"]["appearance_camera_idx"], 1)
        self.assertTrue(metadata["appearance"]["appearance_camera_clamped"])


if __name__ == "__main__":
    unittest.main()
