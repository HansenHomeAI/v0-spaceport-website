import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTAINER_DIR = REPO_ROOT / "infrastructure" / "containers" / "3dgs"
if str(CONTAINER_DIR) not in sys.path:
    sys.path.insert(0, str(CONTAINER_DIR))

from projected_skybox import (  # noqa: E402
    ProjectedSkyboxSettings,
    build_projected_photo_skybox,
    derive_sky_mask_from_training_mask,
    world_dirs_to_equirectangular,
)


class ProjectedSkyboxTests(unittest.TestCase):
    def test_derive_sky_mask_from_training_mask_exclude_sky(self):
        training_mask = np.array([[0, 0], [255, 255]], dtype=np.uint8)
        sky_mask = derive_sky_mask_from_training_mask(training_mask, "exclude_sky")
        self.assertEqual(sky_mask.tolist(), [[True, True], [False, False]])

    def test_world_dirs_to_equirectangular_identity_basis(self):
        directions = np.array(
            [
                [0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0],
                [1.0, 0.0, 0.0],
            ],
            dtype=np.float32,
        )
        xs, ys = world_dirs_to_equirectangular(
            world_directions=directions,
            world_to_sky=np.eye(3, dtype=np.float32),
            width=400,
            height=200,
        )
        self.assertAlmostEqual(float(xs[0]), 199.5, delta=1.0)
        self.assertAlmostEqual(float(ys[0]), 99.5, delta=1.0)
        self.assertAlmostEqual(float(xs[1]), 199.5, delta=1.0)
        self.assertAlmostEqual(float(ys[1]), -0.5, delta=1.0)
        self.assertAlmostEqual(float(xs[2]), 299.5, delta=1.0)

    def test_build_projected_photo_skybox_uses_observed_sky_before_fill(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "converted_data"
            images_dir = data_dir / "images"
            masks_dir = data_dir / "masks"
            confidence_dir = data_dir / "semantic_sky_confidence"
            output_dir = Path(temp_dir) / "output"
            images_dir.mkdir(parents=True)
            masks_dir.mkdir(parents=True)
            confidence_dir.mkdir(parents=True)
            output_dir.mkdir(parents=True)

            rgb = np.zeros((4, 4, 3), dtype=np.uint8)
            rgb[:2, :, :] = np.array([70, 150, 255], dtype=np.uint8)
            rgb[2:, :, :] = np.array([20, 200, 40], dtype=np.uint8)
            Image.fromarray(rgb, mode="RGB").save(images_dir / "frame_00001.png")

            training_mask = np.zeros((4, 4), dtype=np.uint8)
            training_mask[2:, :] = 255
            Image.fromarray(training_mask, mode="L").save(masks_dir / "frame_00001.png")
            confidence = np.zeros((4, 4), dtype=np.uint8)
            confidence[:2, :] = 255
            Image.fromarray(confidence, mode="L").save(confidence_dir / "frame_00001.png")

            transforms = {
                "w": 4,
                "h": 4,
                "fl_x": 4.0,
                "fl_y": 4.0,
                "cx": 2.0,
                "cy": 2.0,
                "frames": [
                    {
                        "file_path": "images/frame_00001.png",
                        "mask_path": "masks/frame_00001.png",
                        "semantic_sky_confidence_path": "semantic_sky_confidence/frame_00001.png",
                        "transform_matrix": np.eye(4, dtype=np.float32).tolist(),
                    }
                ],
            }
            (data_dir / "transforms.json").write_text(json.dumps(transforms), encoding="utf-8")

            manifest = build_projected_photo_skybox(
                data_dir=data_dir,
                output_dir=output_dir,
                width=256,
                height=128,
                quality=90,
                fill_rgb=np.full((128, 256, 3), [0.7, 0.2, 0.2], dtype=np.float32),
                settings=ProjectedSkyboxSettings(
                    min_sky_mask_ratio=0.05,
                    projection_max_long_side=256,
                ),
            )

            self.assertEqual(manifest["contributing_frame_count"], 1)
            self.assertGreater(manifest["observed_coverage_ratio"], 0.0)
            observed_skybox = np.asarray(
                Image.open(output_dir / "background_skybox_observed.webp").convert("RGB"),
                dtype=np.uint8,
            )
            skybox = np.asarray(Image.open(output_dir / "background_skybox.webp").convert("RGB"), dtype=np.uint8)
            self.assertTrue(np.any(observed_skybox[..., 2] > observed_skybox[..., 0] + 20))
            self.assertTrue(np.any(skybox[..., 0] > skybox[..., 2] + 20))


if __name__ == "__main__":
    unittest.main()
