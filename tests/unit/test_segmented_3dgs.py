import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "infrastructure/containers/3dgs"))

from train_nerfstudio_production import NerfStudioTrainer
from utils.ply_ops import clip_ply_to_bounds, merge_clipped_tiles, write_mock_gaussian_ply
from utils.segmented_training import SegmentedProfile, SparseScene, build_tiles, write_tile_dataset


class Segmented3DGSTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.training_root = self.root / "training"
        self._write_fixture(self.training_root)
        self.scene = SparseScene.from_training_root(self.training_root)
        self.profile = SegmentedProfile(
            max_tiles=3,
            max_cameras_per_tile=5,
            max_points_per_tile=50,
            min_cameras_per_tile=2,
            min_points_per_tile=20,
            overlap_ratio=0.1,
            min_observation_fraction=0.1,
            default_iterations=6000,
            heavy_tile_iterations=8000,
            heavy_camera_threshold=4,
            heavy_point_threshold=45,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_build_tiles_assigns_all_cameras(self) -> None:
        projector, tiles, summary = build_tiles(self.scene, self.profile)
        self.assertLessEqual(len(tiles), self.profile.max_tiles)
        self.assertEqual(summary["tile_count"], len(tiles))
        assigned_images = sorted({image_id for tile in tiles for image_id in tile.image_ids})
        self.assertEqual(assigned_images, self.scene.image_ids)
        self.assertTrue(all(tile.expanded_point_ids for tile in tiles))
        self.assertTrue(any(tile.iterations == self.profile.heavy_tile_iterations for tile in tiles))
        self.assertEqual(projector.project_points(self.scene.point_xyz).shape[1], 2)

    def test_write_tile_dataset_and_merge_prunes_to_target(self) -> None:
        projector, tiles, _ = build_tiles(self.scene, self.profile)
        clipped_tiles = []

        for tile in tiles[:2]:
            dataset_root = self.root / tile.tile_id / "dataset"
            tile_paths = write_tile_dataset(self.scene, tile, dataset_root)
            self.assertTrue((tile_paths.sparse_dir / "cameras.txt").exists())
            self.assertTrue((tile_paths.sparse_dir / "images.txt").exists())
            self.assertTrue((tile_paths.sparse_dir / "points3D.txt").exists())
            self.assertTrue((tile_paths.images_dir / self.scene.images[tile.image_ids[0]].name).exists())

            point_indices = [self.scene.point_id_to_index[point_id] for point_id in tile.expanded_point_ids]
            centers = self.scene.point_xyz[point_indices]
            raw_ply = self.root / tile.tile_id / "raw.ply"
            write_mock_gaussian_ply(raw_ply, centers_xyz=centers, count=70, seed=len(tile.tile_id))

            clipped_path = self.root / tile.tile_id / "clipped.ply"
            clipped = clip_ply_to_bounds(raw_ply, projector, tile.core_bounds, clipped_path, tile.tile_id)
            self.assertGreater(clipped.clipped_count, 0)
            self.assertLessEqual(clipped.clipped_count, clipped.input_count)
            clipped_tiles.append(clipped)

        merged_path = self.root / "merged.ply"
        merge_result = merge_clipped_tiles(clipped_tiles, target_total_gaussians=80, output_path=merged_path)
        self.assertEqual(merge_result.merged_count, 80)
        self.assertLessEqual(merge_result.seam_density_ratio, 2.5)
        self.assertTrue(merged_path.exists())

    def test_tile_manifest_is_json_serializable(self) -> None:
        _, tiles, summary = build_tiles(self.scene, self.profile)
        payload = {
            "summary": summary,
            "tiles": [tile.to_manifest_entry() for tile in tiles],
        }
        rendered = json.dumps(payload)
        self.assertIn("tile_00", rendered)

    def test_segmented_trainer_dry_run_writes_artifacts(self) -> None:
        model_dir = self.root / "model"
        config_path = Path(__file__).resolve().parents[2] / "infrastructure/containers/3dgs/nerfstudio_config.yaml"
        env = {
            "SM_CHANNEL_TRAINING": str(self.training_root),
            "SM_MODEL_DIR": str(model_dir),
            "TRAINING_MODE": "segmented",
            "SEGMENTED_DRY_RUN": "true",
            "SEG_TARGET_TOTAL_GAUSSIANS": "200",
            "SEG_MAX_TILES": "3",
            "SEG_TILE_MAX_ITERATIONS": "200",
            "WRITE_PROOF_ARTIFACTS": "false",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            trainer = NerfStudioTrainer(str(config_path))
            self.assertTrue(trainer.run_full_training_pipeline())

        self.assertTrue((model_dir / "splat.ply").exists())
        self.assertTrue((model_dir / "training_metadata.json").exists())
        self.assertTrue((model_dir / "segmentation_manifest.json").exists())
        self.assertTrue((model_dir / "proof" / "proof_links.json").exists())

    def _write_fixture(self, training_root: Path) -> None:
        sparse_dir = training_root / "sparse" / "0"
        images_dir = training_root / "images"
        sparse_dir.mkdir(parents=True, exist_ok=True)
        images_dir.mkdir(parents=True, exist_ok=True)

        with open(sparse_dir / "cameras.txt", "w", encoding="utf-8") as handle:
            handle.write("# CAMERA_ID MODEL WIDTH HEIGHT PARAMS[]\n")
            handle.write("1 PINHOLE 1024 768 800 800 512 384\n")

        image_observations = {image_id: [] for image_id in range(1, 13)}
        points = []
        for point_id in range(1, 121):
            cluster = (point_id - 1) // 10
            center_x = float(cluster)
            x = center_x + ((point_id % 5) - 2) * 0.05
            y = float(cluster % 2) * 0.8 + ((point_id % 3) - 1) * 0.03
            z = ((point_id % 7) - 3) * 0.02

            image_ids = []
            for image_id in range(1, 13):
                if abs((image_id - 1) - cluster) <= 1:
                    image_ids.append(image_id)
            if len(image_ids) < 2:
                image_ids = [max(1, cluster), min(12, cluster + 2)]

            track = []
            for observation_index, image_id in enumerate(image_ids):
                point2d_id = len(image_observations[image_id])
                x2d = 100.0 + point_id + observation_index
                y2d = 200.0 + point_id - observation_index
                image_observations[image_id].append((x2d, y2d, point_id))
                track.append((image_id, point2d_id))
            points.append((point_id, x, y, z, track))

        with open(sparse_dir / "images.txt", "w", encoding="utf-8") as handle:
            handle.write("# IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID NAME\n")
            handle.write("# POINTS2D[] as X Y POINT3D_ID\n")
            for image_id in range(1, 13):
                center_x = float(image_id - 1)
                center_y = float((image_id - 1) % 2) * 0.8
                center_z = 2.0
                tx, ty, tz = -center_x, -center_y, -center_z
                image_name = f"frame_{image_id:04d}.jpg"
                handle.write(f"{image_id} 1 0 0 0 {tx} {ty} {tz} 1 {image_name}\n")
                points_line = " ".join(
                    f"{x:.3f} {y:.3f} {point_id}"
                    for x, y, point_id in image_observations[image_id]
                )
                handle.write(points_line + "\n")
                (images_dir / image_name).write_bytes(b"fixture")

        with open(sparse_dir / "points3D.txt", "w", encoding="utf-8") as handle:
            handle.write("# POINT3D_ID X Y Z R G B ERROR TRACK[]\n")
            for point_id, x, y, z, track in points:
                track_str = " ".join(f"{image_id} {point2d_id}" for image_id, point2d_id in track)
                handle.write(f"{point_id} {x:.4f} {y:.4f} {z:.4f} 255 255 255 0.1 {track_str}\n")


if __name__ == "__main__":
    unittest.main()
