import importlib.util
import math
import sys
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


if __name__ == "__main__":
    unittest.main()
