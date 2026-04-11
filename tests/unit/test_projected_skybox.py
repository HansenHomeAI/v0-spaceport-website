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
    _apply_frame_alignment,
    _select_projected_elevation_mask,
    ProjectedSkyboxSettings,
    build_photo_guided_fill,
    build_projection_basis,
    build_projected_photo_skybox,
    derive_detail_sky_mask,
    derive_projection_sky_mask,
    derive_sky_mask_from_training_mask,
    world_dirs_to_equirectangular,
)


class ProjectedSkyboxTests(unittest.TestCase):
    @staticmethod
    def _rotation_x(angle_radians: float) -> np.ndarray:
        return np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, np.cos(angle_radians), -np.sin(angle_radians)],
                [0.0, np.sin(angle_radians), np.cos(angle_radians)],
            ],
            dtype=np.float32,
        )

    @staticmethod
    def _rotation_y(angle_radians: float) -> np.ndarray:
        return np.array(
            [
                [np.cos(angle_radians), 0.0, np.sin(angle_radians)],
                [0.0, 1.0, 0.0],
                [-np.sin(angle_radians), 0.0, np.cos(angle_radians)],
            ],
            dtype=np.float32,
        )

    def _make_pitched_ring_frames(self, pitch_degrees: float = 55.0) -> list[dict]:
        frames: list[dict] = []
        world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        pitch = np.deg2rad(pitch_degrees)
        base_rotation = self._rotation_x(pitch)
        radius = 3.0

        for yaw_degrees in (0.0, 90.0, 180.0, 270.0):
            yaw = np.deg2rad(yaw_degrees)
            yaw_rotation = self._rotation_y(yaw)
            c2w = np.eye(4, dtype=np.float32)
            c2w[:3, :3] = yaw_rotation @ base_rotation
            c2w[:3, 3] = np.array(
                [
                    radius * np.sin(yaw),
                    0.0,
                    radius * np.cos(yaw),
                ],
                dtype=np.float32,
            )
            frames.append({"transform_matrix": c2w.tolist()})

        self.assertLess(
            float(np.dot(np.asarray(frames[0]["transform_matrix"], dtype=np.float32)[:3, 1], world_up)),
            0.7,
        )
        return frames

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

    def test_build_projection_basis_uses_camera_ring_normal_for_world_up(self):
        frames = self._make_pitched_ring_frames()
        basis = build_projection_basis(frames)
        world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        self.assertGreater(float(np.dot(basis["up"], world_up)), 0.95)

        sky_proxy_dirs = []
        for frame in frames:
            c2w = np.asarray(frame["transform_matrix"], dtype=np.float32)
            proxy = (-c2w[:3, 2]) + (0.75 * c2w[:3, 1])
            proxy = proxy / np.linalg.norm(proxy)
            sky_proxy_dirs.append(proxy)

        xs, ys = world_dirs_to_equirectangular(
            world_directions=np.stack(sky_proxy_dirs, axis=0),
            world_to_sky=basis["world_to_sky"],
            width=400,
            height=200,
        )

        self.assertTrue(np.all(ys < 70.0), msg=f"Projected sky rows were not near the zenith: {ys.tolist()}")
        self.assertTrue(np.all((xs >= -0.5) & (xs <= 399.5)))

    def test_derive_projection_sky_mask_fills_above_horizon(self):
        sky_mask = np.array(
            [
                [0, 1, 0, 0, 1, 0],
                [0, 1, 1, 0, 1, 0],
                [0, 0, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0],
            ],
            dtype=bool,
        )
        confidence = np.array(
            [
                [0.0, 0.9, 0.8, 0.7, 0.9, 0.0],
                [0.0, 0.9, 0.8, 0.7, 0.9, 0.0],
                [0.0, 0.1, 0.7, 0.6, 0.1, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            ],
            dtype=np.float32,
        )

        projection_mask = derive_projection_sky_mask(
            sky_mask=sky_mask,
            confidence=confidence,
            confidence_threshold=0.6,
            horizon_smoothing_px=1,
            projection_mask_mode="semantic_horizon_fill",
        )

        self.assertGreater(float(projection_mask.mean()), float(sky_mask.mean()))
        self.assertTrue(np.all(projection_mask[:2, 1:5]))
        self.assertTrue(projection_mask[2, 2])
        self.assertTrue(projection_mask[2, 3])
        self.assertFalse(projection_mask[4, 2])

    def test_derive_detail_sky_mask_removes_horizon_band(self):
        sky_mask = np.array(
            [
                [0, 1, 1, 1, 1, 0],
                [0, 1, 1, 1, 1, 0],
                [0, 1, 1, 1, 1, 0],
                [0, 1, 1, 1, 1, 0],
                [0, 0, 0, 0, 0, 0],
            ],
            dtype=bool,
        )
        projection_mask = sky_mask.copy()
        confidence = np.ones_like(sky_mask, dtype=np.float32)

        detail_mask = derive_detail_sky_mask(
            sky_mask=sky_mask,
            projection_mask=projection_mask,
            confidence=confidence,
            confidence_threshold=0.5,
            horizon_margin_px=2,
            erosion_px=0,
        )

        self.assertTrue(np.all(detail_mask[0:2, 1:5]))
        self.assertFalse(np.any(detail_mask[2:, :]))

    def test_apply_frame_alignment_moves_frame_toward_target(self):
        rgb = np.full((4, 4, 3), [0.30, 0.60, 0.95], dtype=np.float32)
        mask = np.ones((4, 4), dtype=bool)
        target = np.array([0.45, 0.62, 0.88], dtype=np.float32)

        aligned, metadata = _apply_frame_alignment(
            rgb=rgb,
            reference_mask=mask,
            target_rgb=target,
            strength=0.8,
        )

        self.assertIsNotNone(metadata)
        before_error = float(np.abs(rgb[0, 0] - target).mean())
        after_error = float(np.abs(aligned[0, 0] - target).mean())
        self.assertLess(after_error, before_error)

    def test_select_projected_elevation_mask_flips_when_positive_gate_rejects_all(self):
        local_dirs = np.array(
            [
                [0.0, -0.35, 0.9],
                [0.1, -0.20, 0.97],
                [-0.1, -0.12, 0.98],
            ],
            dtype=np.float32,
        )

        elevation_mask, mode = _select_projected_elevation_mask(
            local_dirs=local_dirs,
            min_projected_elevation=0.0,
        )

        self.assertEqual(mode, "flipped")
        self.assertTrue(np.all(elevation_mask))

    def test_build_photo_guided_fill_prefers_projected_sky_over_dark_fallback(self):
        height = 128
        width = 256
        observed_rgb = np.zeros((height, width, 3), dtype=np.float32)
        observed_mask = np.zeros((height, width), dtype=bool)
        observed_mask[64:80, :] = True
        observed_rgb[observed_mask] = np.array([0.62, 0.81, 1.0], dtype=np.float32)
        weight_accum = observed_mask.astype(np.float32)
        fallback_fill_rgb = np.full((height, width, 3), [0.12, 0.04, 0.04], dtype=np.float32)

        fill_rgb, metadata = build_photo_guided_fill(
            observed_rgb=observed_rgb,
            observed_mask=observed_mask,
            weight_accum=weight_accum,
            fallback_fill_rgb=fallback_fill_rgb,
        )

        zenith = fill_rgb[: height // 10]
        self.assertTrue(metadata["fill_used_observed_projection"])
        self.assertEqual(metadata["fill_strategy"], "observed_projection_spherical_regression")
        self.assertGreater(float(zenith[..., 2].mean()), float(zenith[..., 0].mean()) + 0.2)
        self.assertGreater(float(zenith.mean()), float(fallback_fill_rgb[: height // 10].mean()) + 0.2)

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
            training_mask[1:, :] = 255
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
                    projection_mask_mode="semantic_horizon_fill",
                    projection_confidence_threshold=0.6,
                    projection_horizon_smoothing_px=1,
                    min_projected_elevation=-1.0,
                ),
            )

            self.assertEqual(manifest["contributing_frame_count"], 1)
            self.assertGreater(manifest["observed_coverage_ratio"], 0.0)
            self.assertGreater(manifest["mean_projection_mask_ratio"], manifest["mean_semantic_mask_ratio"])
            self.assertEqual(manifest["fill_strategy"], "observed_projection_spherical_regression")
            self.assertIn("detail_coverage_ratio", manifest)
            self.assertIn("base_saturation_scale", manifest)
            self.assertIn("projection_elevation_mode_counts", manifest)
            self.assertTrue((output_dir / "background_skybox_base.webp").exists())
            self.assertTrue((output_dir / "background_skybox_detail.webp").exists())
            self.assertTrue((output_dir / "background_skybox_detail_support.png").exists())
            observed_skybox = np.asarray(
                Image.open(output_dir / "background_skybox_observed.webp").convert("RGB"),
                dtype=np.uint8,
            )
            skybox = np.asarray(Image.open(output_dir / "background_skybox.webp").convert("RGB"), dtype=np.uint8)
            self.assertTrue(np.any(observed_skybox[..., 2] > observed_skybox[..., 0] + 20))
            zenith = skybox[: max(1, skybox.shape[0] // 10), :, :]
            self.assertGreater(float(zenith[..., 2].mean()), float(zenith[..., 0].mean()) + 20.0)
            self.assertFalse(np.array_equal(skybox, observed_skybox))


if __name__ == "__main__":
    unittest.main()
