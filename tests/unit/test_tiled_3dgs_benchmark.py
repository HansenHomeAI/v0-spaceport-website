import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

tile_pipeline_stub = types.SimpleNamespace(
    resolve_tiled_input_manifests=lambda **kwargs: (
        kwargs.get("tile_manifest_payload") or {
            "tiles": [{"tile_id": "tile_00"}, {"tile_id": "tile_01"}],
            "global_scaffold_camera_ids": [],
            "all_image_names": [],
        },
        kwargs.get("view_bucket_payload") or {"boundary_camera_ids": []},
        {"source_mode": "native_3dgs_manifests"},
    )
)
sys.modules.setdefault("tile_pipeline", tile_pipeline_stub)

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "3dgs" / "run_tiled_3dgs_benchmark.py"
SPEC = importlib.util.spec_from_file_location("run_tiled_3dgs_benchmark_test_module", MODULE_PATH)
benchmark = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = benchmark
SPEC.loader.exec_module(benchmark)


class Tiled3DGSBenchmarkTests(unittest.TestCase):
    def test_load_json_path_or_s3_reads_local_override(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            payload_path = Path(tmpdir) / "manifest.json"
            payload_path.write_text('{"tiles": [{"tile_id": "tile_00"}]}', encoding="utf-8")

            payload = benchmark.load_json_path_or_s3(str(payload_path))

        self.assertEqual(payload["tiles"][0]["tile_id"], "tile_00")

    def test_parse_tile_int_map_requires_positive_counts(self):
        parsed = benchmark.parse_tile_int_map(["tile_10=387192"], label="leaf refs")

        self.assertEqual(parsed, {"tile_10": 387192})
        with self.assertRaises(ValueError):
            benchmark.parse_tile_int_map(["tile_10=0"], label="leaf refs")
        with self.assertRaises(ValueError):
            benchmark.parse_tile_int_map(["tile_10"], label="leaf refs")

    def test_build_post_leaf_preflight_gates_emits_commands(self):
        stage = benchmark.BenchmarkStage(
            stage_name="T0_tile_10",
            stage_type="train",
            training_mode="leaf_tile",
            output_s3_uri="s3://bucket/run/tiles/tile_10",
            job_name="tile10-proof",
            tile_id="tile_10",
            selected_image_count=188,
        )

        gates = benchmark.build_post_leaf_preflight_gates(
            [stage],
            reference_splat_counts={"tile_10": 387192},
            max_reference_splat_ratio=1.5,
            min_reference_splat_ratio=0.8,
            experiment_id="exp",
            gate_json_path="logs/summary.json",
        )

        self.assertEqual(len(gates), 1)
        gate = gates[0]
        self.assertEqual(gate["artifact_uri"], "s3://bucket/run/tiles/tile_10/tile10-proof/output/model.tar.gz")
        self.assertEqual(gate["hard_max_splat_count"], 580788)
        self.assertEqual(gate["hard_min_splat_count"], 309753)
        self.assertIn("--reference-splat-count", gate["preflight_command"])
        self.assertIn("--min-reference-splat-ratio", gate["preflight_command"])
        self.assertIn("--gate-json", gate["enforce_gate_command"])
        self.assertIn("logs/summary.json", gate["enforce_gate_command"])

    def test_resolve_proof_profile_defaults_to_quality_gate_low_memory_for_single_job_review(self):
        resolved = benchmark.resolve_proof_profile(
            None,
            orchestration_mode="single_job",
            include_review=True,
        )

        self.assertEqual(resolved, benchmark.PROOF_PROFILE_QUALITY_GATE_LOW_MEMORY)

    def test_resolve_proof_profile_defaults_to_none_for_non_review_or_fanout_runs(self):
        self.assertEqual(
            benchmark.resolve_proof_profile(
                None,
                orchestration_mode="single_job",
                include_review=False,
            ),
            benchmark.PROOF_PROFILE_NONE,
        )
        self.assertEqual(
            benchmark.resolve_proof_profile(
                None,
                orchestration_mode="fanout",
                include_review=True,
            ),
            benchmark.PROOF_PROFILE_NONE,
        )

    def test_s3_json_or_none_returns_none_on_missing_object(self):
        original_run = benchmark.subprocess.run
        try:
            benchmark.subprocess.run = lambda *args, **kwargs: types.SimpleNamespace(
                returncode=1,
                stdout="",
                stderr="missing",
            )
            self.assertIsNone(benchmark.s3_json_or_none("s3://bucket/missing.json"))
        finally:
            benchmark.subprocess.run = original_run

    def test_checkpoint_step_from_manifest_uses_latest_checkpoint(self):
        step = benchmark.checkpoint_step_from_manifest(
            {
                "latest_checkpoint": "nerfstudio_models/step-000002999.ckpt",
                "checkpoint_files": [
                    {"path": "nerfstudio_models/step-000001000.ckpt"},
                ],
            }
        )

        self.assertEqual(step, 2999)

    def test_checkpoint_step_from_manifest_falls_back_to_max_checkpoint_file(self):
        step = benchmark.checkpoint_step_from_manifest(
            {
                "checkpoint_files": [
                    {"path": "nerfstudio_models/step-000001000.ckpt"},
                    {"path": "nerfstudio_models/step-000002500.ckpt"},
                ],
            }
        )

        self.assertEqual(step, 2500)

    def test_download_sparse_support_dir_requires_complete_sparse_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []

            def fake_run(args, **_kwargs):
                calls.append(args)
                target = Path(args[-1])
                if args[3].endswith("images.txt"):
                    target.write_text("# images\n", encoding="utf-8")
                    return types.SimpleNamespace(returncode=0, stdout="", stderr="")
                return types.SimpleNamespace(returncode=1, stdout="", stderr="missing")

            original_run = benchmark.subprocess.run
            try:
                benchmark.subprocess.run = fake_run
                with self.assertRaises(RuntimeError) as raised:
                    benchmark.download_sparse_support_dir("s3://bucket/colmap", scratch_dir=Path(tmp))
            finally:
                benchmark.subprocess.run = original_run

            self.assertIn("Incomplete sparse support download", str(raised.exception))
            self.assertEqual(len(calls), 2)

    def test_download_sparse_support_dir_returns_sparse_dir_when_complete(self):
        with tempfile.TemporaryDirectory() as tmp:

            def fake_run(args, **_kwargs):
                target = Path(args[-1])
                target.write_text("# sparse\n", encoding="utf-8")
                return types.SimpleNamespace(returncode=0, stdout="", stderr="")

            original_run = benchmark.subprocess.run
            try:
                benchmark.subprocess.run = fake_run
                sparse_dir = benchmark.download_sparse_support_dir("s3://bucket/colmap", scratch_dir=Path(tmp))
            finally:
                benchmark.subprocess.run = original_run

            self.assertEqual(sparse_dir, Path(tmp) / "sparse" / "0")
            self.assertTrue((sparse_dir / "images.txt").exists())
            self.assertTrue((sparse_dir / "points3D.txt").exists())

    def test_materialize_merge_tile_dir_prefers_symlink_without_copying(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "splat.ply").write_text("ply\n", encoding="utf-8")
            target = Path(tmp) / "target"

            mode = benchmark.materialize_merge_tile_dir(source, target)

            self.assertIn(mode, {"symlink", "copy"})
            self.assertTrue((target / "splat.ply").exists())
            if mode == "symlink":
                self.assertTrue(target.is_symlink())

    def test_build_benchmark_stages_defaults_to_single_tiled_job(self):
        manifest = {
            "tiles": [
                {"tile_id": "tile_00"},
                {"tile_id": "tile_01"},
            ]
        }

        stages = benchmark.build_benchmark_stages(
            manifest=manifest,
            branch_name="agent-branch",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="bench",
            include_monolithic=True,
            include_scaffold=True,
            include_merge=True,
            orchestration_mode="single_job",
            tile_ids=["tile_00", "tile_01"],
            monolithic_max_iterations=8000,
            scaffold_max_iterations=2000,
            tile_max_iterations=12000,
            training_max_runtime_seconds=21600,
            extra_env={"LOG_INTERVAL": "50"},
            timestamp=123,
            downscale_factor=1,
            include_review=True,
            proof_profile=benchmark.PROOF_PROFILE_QUALITY_GATE_LOW_MEMORY,
        )

        self.assertEqual(
            [stage.stage_name for stage in stages],
            ["M0_monolithic", "T2_tiled_pipeline", "R0_quality_review"],
        )
        tiled_env = stages[1].environment
        self.assertEqual(tiled_env["TRAINING_MODE"], "tiled_pipeline")
        self.assertEqual(tiled_env["TILED_TILE_IDS"], "tile_00,tile_01")
        self.assertEqual(tiled_env["TILED_MAX_TILES"], "2")
        self.assertEqual(tiled_env["TILED_INCLUDE_MERGE"], "true")
        self.assertEqual(tiled_env["GLOBAL_SCAFFOLD_MAX_ITERATIONS"], "2000")
        self.assertEqual(tiled_env["BILATERAL_PROCESSING"], "false")
        self.assertEqual(tiled_env["TRAINING_VIS_MODE"], "viewer")
        self.assertEqual(tiled_env["TRAINING_TIMEOUT_SECONDS"], "21600")
        self.assertEqual(tiled_env["TRAINING_STEPS_PER_EVAL_IMAGE"], "12001")
        self.assertEqual(tiled_env["TRAINING_STEPS_PER_EVAL_ALL_IMAGES"], "12001")
        self.assertEqual(tiled_env["TRAINING_STEPS_PER_SAVE"], "12001")
        self.assertEqual(stages[2].stage_type, "review")
        self.assertEqual(stages[2].depends_on, ["T2_tiled_pipeline"])

    def test_build_training_environment_disables_bilateral_for_w_light_even_if_requested(self):
        env = benchmark.build_training_environment(
            training_mode="monolithic",
            tile_manifest_name="3dgs_tile_manifest.json",
            view_bucket_manifest_name="3dgs_view_buckets.json",
            tile_id=None,
            max_iterations=1000,
            extra_env={
                "MODEL_VARIANT": "splatfacto-w-light",
                "BILATERAL_PROCESSING": "true",
            },
        )

        self.assertEqual(env["MODEL_VARIANT"], "splatfacto-w-light")
        self.assertEqual(env["BILATERAL_PROCESSING"], "false")

    def test_build_training_environment_includes_downscale_factor_when_requested(self):
        env = benchmark.build_training_environment(
            training_mode="monolithic",
            tile_manifest_name="3dgs_tile_manifest.json",
            view_bucket_manifest_name="3dgs_view_buckets.json",
            tile_id=None,
            max_iterations=1000,
            extra_env={},
            downscale_factor=8,
        )

        self.assertEqual(env["TRAINING_DOWNSCALE_FACTOR"], "8")

    def test_build_training_environment_defaults_tiny_proof_runs_to_viewer_mode(self):
        env = benchmark.build_training_environment(
            training_mode="leaf_tile",
            tile_manifest_name="3dgs_tile_manifest.json",
            view_bucket_manifest_name="3dgs_view_buckets.json",
            tile_id="tile_00",
            max_iterations=10,
            extra_env={},
        )

        self.assertEqual(env["TRAINING_VIS_MODE"], "viewer")
        self.assertEqual(env["TRAINING_CACHE_IMAGES"], "disk")
        self.assertEqual(env["TRAINING_CACHE_IMAGES_TYPE"], "uint8")
        self.assertEqual(env["TRAINING_DATALOADER_NUM_WORKERS"], "0")

    def test_build_training_environment_quality_gate_profile_injects_low_memory_defaults(self):
        env = benchmark.build_training_environment(
            training_mode="tiled_pipeline",
            tile_manifest_name="3dgs_tile_manifest.json",
            view_bucket_manifest_name="3dgs_view_buckets.json",
            tile_id=None,
            max_iterations=12000,
            extra_env={},
            training_timeout_seconds=21600,
            proof_profile=benchmark.PROOF_PROFILE_QUALITY_GATE_LOW_MEMORY,
        )

        self.assertEqual(env["TRAINING_VIS_MODE"], "viewer")
        self.assertEqual(env["TRAINING_PROOF_PROFILE"], "quality_gate_low_memory")
        self.assertEqual(env["TRAINING_TIMEOUT_SECONDS"], "21600")
        self.assertEqual(env["TRAINING_CACHE_IMAGES"], "disk")
        self.assertEqual(env["TRAINING_CACHE_IMAGES_TYPE"], "uint8")
        self.assertEqual(env["TRAINING_DATALOADER_NUM_WORKERS"], "0")
        self.assertEqual(env["TRAINING_STOP_SPLIT_AT"], "8500")
        self.assertEqual(env["TRAINING_STEPS_PER_EVAL_IMAGE"], "12001")
        self.assertEqual(env["TRAINING_STEPS_PER_EVAL_ALL_IMAGES"], "12001")
        self.assertEqual(env["TRAINING_STEPS_PER_SAVE"], "12001")

    def test_build_training_environment_quality_gate_profile_tightens_multi_tile_review_runs(self):
        env = benchmark.build_training_environment(
            training_mode="tiled_pipeline",
            tile_manifest_name="3dgs_tile_manifest.json",
            view_bucket_manifest_name="3dgs_view_buckets.json",
            tile_id=None,
            max_iterations=12000,
            extra_env={},
            include_review=True,
            selected_tile_ids=["tile_04", "tile_05", "tile_06"],
            proof_profile=benchmark.PROOF_PROFILE_QUALITY_GATE_LOW_MEMORY,
        )

        self.assertEqual(env["TRAINING_PROOF_PROFILE"], "quality_gate_low_memory")
        self.assertEqual(env["TRAINING_MAX_GAUSS_RATIO"], "8.0")
        self.assertEqual(env["TRAINING_STOP_SPLIT_AT"], "7000")

    def test_build_training_environment_quality_gate_profile_keeps_single_tile_behavior(self):
        env = benchmark.build_training_environment(
            training_mode="tiled_pipeline",
            tile_manifest_name="3dgs_tile_manifest.json",
            view_bucket_manifest_name="3dgs_view_buckets.json",
            tile_id=None,
            max_iterations=12000,
            extra_env={},
            include_review=True,
            selected_tile_ids=["tile_00"],
            proof_profile=benchmark.PROOF_PROFILE_QUALITY_GATE_LOW_MEMORY,
        )

        self.assertNotIn("TRAINING_MAX_GAUSS_RATIO", env)
        self.assertEqual(env["TRAINING_STOP_SPLIT_AT"], "8500")

    def test_build_training_environment_preserves_explicit_timeout_override(self):
        env = benchmark.build_training_environment(
            training_mode="tiled_pipeline",
            tile_manifest_name="3dgs_tile_manifest.json",
            view_bucket_manifest_name="3dgs_view_buckets.json",
            tile_id=None,
            max_iterations=12000,
            extra_env={"TRAINING_TIMEOUT_SECONDS": "28800"},
            training_timeout_seconds=21600,
            proof_profile=benchmark.PROOF_PROFILE_QUALITY_GATE_LOW_MEMORY,
        )

        self.assertEqual(env["TRAINING_TIMEOUT_SECONDS"], "28800")

    def test_build_training_environment_quality_gate_profile_preserves_explicit_overrides(self):
        env = benchmark.build_training_environment(
            training_mode="tiled_pipeline",
            tile_manifest_name="3dgs_tile_manifest.json",
            view_bucket_manifest_name="3dgs_view_buckets.json",
            tile_id=None,
            max_iterations=12000,
            extra_env={
                "TRAINING_VIS_MODE": "tensorboard",
                "TRAINING_STEPS_PER_EVAL_IMAGE": "300",
                "TRAINING_STEPS_PER_EVAL_ALL_IMAGES": "900",
                "TRAINING_STEPS_PER_SAVE": "1200",
                "TRAINING_STOP_SPLIT_AT": "7000",
                "TRAINING_MAX_GAUSS_RATIO": "7.5",
            },
            include_review=True,
            selected_tile_ids=["tile_04", "tile_05", "tile_06"],
            proof_profile=benchmark.PROOF_PROFILE_QUALITY_GATE_LOW_MEMORY,
        )

        self.assertEqual(env["TRAINING_VIS_MODE"], "tensorboard")
        self.assertEqual(env["TRAINING_STEPS_PER_EVAL_IMAGE"], "300")
        self.assertEqual(env["TRAINING_STEPS_PER_EVAL_ALL_IMAGES"], "900")
        self.assertEqual(env["TRAINING_STEPS_PER_SAVE"], "1200")
        self.assertEqual(env["TRAINING_STOP_SPLIT_AT"], "7000")
        self.assertEqual(env["TRAINING_MAX_GAUSS_RATIO"], "7.5")

    def test_build_training_environment_quality_gate_profile_preserves_explicit_profile_override(self):
        env = benchmark.build_training_environment(
            training_mode="tiled_pipeline",
            tile_manifest_name="3dgs_tile_manifest.json",
            view_bucket_manifest_name="3dgs_view_buckets.json",
            tile_id=None,
            max_iterations=12000,
            extra_env={"TRAINING_PROOF_PROFILE": "custom_profile"},
            proof_profile=benchmark.PROOF_PROFILE_QUALITY_GATE_LOW_MEMORY,
        )

        self.assertEqual(env["TRAINING_PROOF_PROFILE"], "custom_profile")

    def test_apply_training_eval_suppression_preserves_explicit_overrides(self):
        env = {"TRAINING_STEPS_PER_EVAL_IMAGE": "300"}

        benchmark.apply_training_eval_suppression(env, max_iterations=12000)

        self.assertEqual(env["TRAINING_STEPS_PER_EVAL_IMAGE"], "300")
        self.assertEqual(env["TRAINING_STEPS_PER_EVAL_ALL_IMAGES"], "12001")
        self.assertEqual(env["TRAINING_STEPS_PER_SAVE"], "12001")

    def test_build_training_environment_allows_explicit_vis_override_for_tiny_runs(self):
        env = benchmark.build_training_environment(
            training_mode="leaf_tile",
            tile_manifest_name="3dgs_tile_manifest.json",
            view_bucket_manifest_name="3dgs_view_buckets.json",
            tile_id="tile_00",
            max_iterations=10,
            extra_env={"TRAINING_VIS_MODE": "tensorboard"},
        )

        self.assertEqual(env["TRAINING_VIS_MODE"], "tensorboard")

    def test_build_benchmark_stages_fanout_emits_leaf_tiles_and_merge(self):
        manifest = {
            "tiles": [
                {"tile_id": "tile_00"},
                {"tile_id": "tile_01"},
            ]
        }

        stages = benchmark.build_benchmark_stages(
            manifest=manifest,
            branch_name="agent-branch",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="bench",
            include_monolithic=False,
            include_scaffold=True,
            include_merge=True,
            orchestration_mode="fanout",
            tile_ids=["tile_00", "tile_01"],
            monolithic_max_iterations=8000,
            scaffold_max_iterations=2000,
            tile_max_iterations=12000,
            training_max_runtime_seconds=21600,
            extra_env={},
            timestamp=456,
            downscale_factor=1,
            include_review=True,
            proof_profile=benchmark.PROOF_PROFILE_NONE,
        )

        self.assertEqual(
            [stage.stage_name for stage in stages],
            ["S0_scaffold", "T0_tile_00", "T0_tile_01", "MERGE_strict_core"],
        )
        self.assertEqual(stages[0].environment["TRAINING_TIMEOUT_SECONDS"], "21600")
        self.assertEqual(stages[1].environment["TRAINING_TIMEOUT_SECONDS"], "21600")
        self.assertEqual(stages[1].depends_on, ["S0_scaffold"])
        self.assertEqual(stages[3].stage_type, "merge")
        self.assertEqual(stages[1].job_name, "bench-456-tile-00")

    def test_fanout_leaf_tiles_can_mount_external_scaffold(self):
        manifest = {"tiles": [{"tile_id": "tile_00"}]}

        stages = benchmark.build_benchmark_stages(
            manifest=manifest,
            branch_name="agent-branch",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="bench",
            include_monolithic=False,
            include_scaffold=False,
            include_merge=True,
            orchestration_mode="fanout",
            tile_ids=["tile_00"],
            monolithic_max_iterations=8000,
            scaffold_max_iterations=2000,
            tile_max_iterations=12000,
            training_max_runtime_seconds=21600,
            extra_env={},
            timestamp=456,
            downscale_factor=1,
            include_review=False,
            proof_profile=benchmark.PROOF_PROFILE_NONE,
            scaffold_artifact_s3_uri="s3://bucket/reusable-scaffold/model.tar.gz",
        )

        self.assertEqual([stage.stage_name for stage in stages], ["T0_tile_00", "MERGE_strict_core"])
        tile_stage = stages[0]
        self.assertEqual(tile_stage.depends_on, [])
        self.assertEqual(tile_stage.environment["GLOBAL_SCAFFOLD_SOURCE_DIR"], benchmark.SCAFFOLD_CHANNEL_DIR)
        self.assertEqual(tile_stage.environment["GLOBAL_SCAFFOLD_REQUIRE_FILTERED_INIT"], "true")

    def test_resolve_stage_scaffold_artifact_supports_fanout_leaf_dependencies(self):
        leaf_stage = benchmark.BenchmarkStage(
            stage_name="T0_tile_00",
            stage_type="train",
            training_mode="leaf_tile",
            output_s3_uri="s3://bucket/out/tiles/tile_00",
            depends_on=["S0_scaffold"],
        )

        self.assertEqual(
            benchmark.resolve_stage_scaffold_artifact_s3_uri(
                leaf_stage,
                explicit_scaffold_artifact_s3_uri="s3://bucket/external-scaffold/model.tar.gz",
                completed_stage_outputs={},
            ),
            "s3://bucket/external-scaffold/model.tar.gz",
        )
        self.assertEqual(
            benchmark.resolve_stage_scaffold_artifact_s3_uri(
                leaf_stage,
                completed_stage_outputs={
                    "S0_scaffold": {"model_artifacts_s3_uri": "s3://bucket/generated-scaffold/model.tar.gz"}
                },
            ),
            "s3://bucket/generated-scaffold/model.tar.gz",
        )

    def test_build_adaptive_tile_budget_plan_downshifts_low_retained_tile(self):
        tile = {
            "tile_id": "tile_11",
            "base_camera_ids": [f"frame_{index:03d}.jpg" for index in range(188)],
            "prior_retained_gaussians": 68,
        }

        budget = benchmark.build_tile_budget_plan(
            tile,
            mode="adaptive",
            tile_max_iterations=12000,
            max_images_per_tile=188,
        )

        self.assertEqual(budget.budget_class, "tiny")
        self.assertEqual(budget.max_iterations, 3000)
        self.assertEqual(budget.max_selected_images, 96)
        self.assertIn("low_prior_retained_gaussians", budget.reasons)

    def test_apply_prior_tile_stats_enables_low_value_tile_classification(self):
        manifest = {
            "tiles": [
                {
                    "tile_id": "tile_11",
                    "base_camera_ids": [f"frame_{index:03d}.jpg" for index in range(188)],
                }
            ]
        }
        prior_stats = benchmark.normalize_prior_tile_stats(
            {"tiles": {"tile_11": {"retained_gaussians": 68, "duration_hours": 3.99}}}
        )

        resolved_manifest = benchmark.apply_prior_tile_stats(manifest, prior_stats)
        budget = benchmark.build_tile_budget_plan(
            resolved_manifest["tiles"][0],
            mode="adaptive",
            tile_max_iterations=12000,
            max_images_per_tile=188,
        )

        self.assertEqual(resolved_manifest["tiles"][0]["prior_retained_gaussians"], 68)
        self.assertEqual(resolved_manifest["tiles"][0]["prior_duration_hours"], 3.99)
        self.assertEqual(budget.budget_class, "tiny")
        self.assertEqual(budget.max_iterations, 3000)

    def test_prior_tile_stats_can_force_horizon_repair_tile_to_hard_budget(self):
        manifest = {
            "tiles": [
                {
                    "tile_id": "tile_13",
                    "base_camera_ids": [f"frame_{index:03d}.jpg" for index in range(188)],
                }
            ]
        }
        prior_stats = benchmark.normalize_prior_tile_stats(
            {
                "tiles": {
                    "tile_13": {
                        "retained_gaussians": 311000,
                        "selected_image_count": 188,
                        "min_budget_class": "hard",
                        "force_max_iterations": 12000,
                        "force_max_selected_images": 188,
                    }
                }
            }
        )

        resolved_manifest = benchmark.apply_prior_tile_stats(manifest, prior_stats)
        budget = benchmark.build_tile_budget_plan(
            resolved_manifest["tiles"][0],
            mode="adaptive",
            tile_max_iterations=12000,
            max_images_per_tile=128,
        )

        self.assertEqual(resolved_manifest["tiles"][0]["prior_min_budget_class"], "hard")
        self.assertEqual(resolved_manifest["tiles"][0]["prior_max_iterations"], 12000)
        self.assertEqual(resolved_manifest["tiles"][0]["prior_max_selected_images"], 188)
        self.assertEqual(budget.budget_class, "hard")
        self.assertEqual(budget.max_iterations, 12000)
        self.assertEqual(budget.max_selected_images, 188)
        self.assertIn("prior_min_budget_class_hard", budget.reasons)

    def test_tile_input_hash_changes_when_geometry_changes(self):
        base_tile = {
            "tile_id": "tile_00",
            "base_camera_ids": ["DJI_0001.JPG", "DJI_0002.JPG"],
            "ownership_bounds": {"min_x": 0, "max_x": 10, "min_y": 0, "max_y": 10},
        }
        moved_tile = {
            **base_tile,
            "ownership_bounds": {"min_x": 5, "max_x": 15, "min_y": 0, "max_y": 10},
        }

        base_hash = benchmark.build_tile_input_hash(
            tile_entry=base_tile,
            budget_class="standard",
            max_iterations=8000,
            max_selected_images=96,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="image",
            scaffold_artifact_s3_uri="s3://bucket/scaffold/model.tar.gz",
        )
        moved_hash = benchmark.build_tile_input_hash(
            tile_entry=moved_tile,
            budget_class="standard",
            max_iterations=8000,
            max_selected_images=96,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="image",
            scaffold_artifact_s3_uri="s3://bucket/scaffold/model.tar.gz",
        )

        self.assertNotEqual(base_hash, moved_hash)

    def test_tile_input_hash_changes_when_training_fingerprint_changes(self):
        tile = {
            "tile_id": "tile_00",
            "base_camera_ids": ["DJI_0001.JPG", "DJI_0002.JPG"],
            "ownership_bounds": {"min_x": 0, "max_x": 10, "min_y": 0, "max_y": 10},
        }

        md1_hash = benchmark.build_tile_input_hash(
            tile_entry=tile,
            budget_class="standard",
            max_iterations=8000,
            max_selected_images=96,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="image",
            scaffold_artifact_s3_uri="s3://bucket/scaffold/model.tar.gz",
            training_env_fingerprint={"SH_DEGREE": "1", "BG_SH_DEGREE": "1"},
        )
        sh3_hash = benchmark.build_tile_input_hash(
            tile_entry=tile,
            budget_class="standard",
            max_iterations=8000,
            max_selected_images=96,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="image",
            scaffold_artifact_s3_uri="s3://bucket/scaffold/model.tar.gz",
            training_env_fingerprint={"SH_DEGREE": "3", "BG_SH_DEGREE": "8"},
        )

        self.assertNotEqual(md1_hash, sh3_hash)

    def test_reuse_tile_cache_turns_matching_tile_into_non_training_stage(self):
        tile_entry = {
            "tile_id": "tile_11",
            "base_camera_ids": [f"frame_{index:03d}.jpg" for index in range(188)],
            "prior_retained_gaussians": 68,
        }
        training_env = {}
        benchmark.apply_md1_production_tile_defaults(training_env)
        budget = benchmark.build_tile_budget_plan(
            tile_entry,
            mode="adaptive",
            tile_max_iterations=12000,
            max_images_per_tile=96,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:test",
            scaffold_artifact_s3_uri="s3://bucket/scaffold/model.tar.gz",
            training_env_fingerprint=benchmark.tile_input_hash_env_fingerprint(training_env),
        )

        stages = benchmark.build_benchmark_stages(
            manifest={"tiles": [tile_entry]},
            branch_name="agent-branch",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="bench",
            include_monolithic=False,
            include_scaffold=False,
            include_merge=True,
            orchestration_mode="fanout",
            tile_ids=["tile_11"],
            monolithic_max_iterations=8000,
            scaffold_max_iterations=2000,
            tile_max_iterations=12000,
            training_max_runtime_seconds=3600,
            extra_env={},
            timestamp=456,
            downscale_factor=1,
            include_review=False,
            proof_profile=benchmark.PROOF_PROFILE_NONE,
            tile_budget_mode="adaptive",
            max_images_per_tile=96,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:test",
            scaffold_artifact_s3_uri="s3://bucket/scaffold/model.tar.gz",
            reuse_tile_cache=True,
            tile_cache_manifest={
                "tile_11": {
                    "input_hash": budget.input_hash,
                    "artifact_s3_uri": "s3://bucket/cache/tile_11/model.tar.gz",
                    "quality_gate_status": "passed",
                }
            },
        )

        self.assertEqual(stages[0].stage_type, "cached_tile")
        self.assertEqual(stages[0].cache_status, "hit")
        self.assertEqual(stages[0].source_artifact_uri, "s3://bucket/cache/tile_11/model.tar.gz")
        self.assertEqual(stages[1].depends_on, ["T0_tile_11"])
        cost = benchmark.estimate_training_cost(
            stages,
            instance_type="ml.g5.2xlarge",
            max_runtime_seconds=3600,
            baseline_iterations=12000,
        )
        self.assertEqual(cost["train_stage_count"], 0)
        self.assertEqual(cost["estimated_usd"], 0.0)

    def test_reuse_tile_cache_rejects_stale_hash_and_keeps_training_stage(self):
        tile_entry = {
            "tile_id": "tile_11",
            "base_camera_ids": [f"frame_{index:03d}.jpg" for index in range(188)],
            "prior_retained_gaussians": 68,
        }

        stages = benchmark.build_benchmark_stages(
            manifest={"tiles": [tile_entry]},
            branch_name="agent-branch",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="bench",
            include_monolithic=False,
            include_scaffold=False,
            include_merge=False,
            orchestration_mode="fanout",
            tile_ids=["tile_11"],
            monolithic_max_iterations=8000,
            scaffold_max_iterations=2000,
            tile_max_iterations=12000,
            training_max_runtime_seconds=3600,
            extra_env={},
            timestamp=456,
            downscale_factor=1,
            include_review=False,
            proof_profile=benchmark.PROOF_PROFILE_NONE,
            tile_budget_mode="adaptive",
            max_images_per_tile=96,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:test",
            scaffold_artifact_s3_uri="s3://bucket/scaffold/model.tar.gz",
            reuse_tile_cache=True,
            tile_cache_manifest={
                "tile_11": {
                    "input_hash": "stale",
                    "artifact_s3_uri": "s3://bucket/cache/tile_11/model.tar.gz",
                    "quality_gate_status": "passed",
                }
            },
        )

        self.assertEqual(stages[0].stage_type, "train")
        self.assertEqual(stages[0].cache_status, "miss")
        self.assertIn("input_hash_mismatch", stages[0].cache_rejection_reasons)

    def test_reuse_tile_cache_rejects_preflight_only_status(self):
        tile_entry = {
            "tile_id": "tile_13",
            "base_camera_ids": [f"frame_{index:03d}.jpg" for index in range(188)],
            "prior_min_budget_class": "hard",
        }
        training_env = {}
        benchmark.apply_md1_production_tile_defaults(training_env)
        budget = benchmark.build_tile_budget_plan(
            tile_entry,
            mode="adaptive",
            tile_max_iterations=12000,
            max_images_per_tile=188,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:test",
            scaffold_artifact_s3_uri="s3://bucket/scaffold/model.tar.gz",
            training_env_fingerprint=benchmark.tile_input_hash_env_fingerprint(training_env),
        )

        stages = benchmark.build_benchmark_stages(
            manifest={"tiles": [tile_entry]},
            branch_name="agent-branch",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="bench",
            include_monolithic=False,
            include_scaffold=False,
            include_merge=False,
            orchestration_mode="fanout",
            tile_ids=["tile_13"],
            monolithic_max_iterations=8000,
            scaffold_max_iterations=2000,
            tile_max_iterations=12000,
            training_max_runtime_seconds=18000,
            extra_env={},
            timestamp=456,
            downscale_factor=1,
            include_review=False,
            proof_profile=benchmark.PROOF_PROFILE_NONE,
            tile_budget_mode="adaptive",
            max_images_per_tile=188,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:test",
            scaffold_artifact_s3_uri="s3://bucket/scaffold/model.tar.gz",
            reuse_tile_cache=True,
            tile_cache_manifest={
                "tile_13": {
                    "input_hash": budget.input_hash,
                    "artifact_s3_uri": "s3://bucket/cache/tile_13/model.tar.gz",
                    "quality_gate_status": "preflight_passed",
                }
            },
        )

        self.assertEqual(stages[0].stage_type, "train")
        self.assertEqual(stages[0].cache_status, "miss")
        self.assertIn("quality_status_not_passing", stages[0].cache_rejection_reasons)

    def test_reuse_tile_cache_rejects_ownership_blocked_artifact(self):
        tile_entry = {
            "tile_id": "tile_13",
            "base_camera_ids": [f"frame_{index:03d}.jpg" for index in range(188)],
            "prior_min_budget_class": "hard",
        }
        training_env = {}
        benchmark.apply_md1_production_tile_defaults(training_env)
        budget = benchmark.build_tile_budget_plan(
            tile_entry,
            mode="adaptive",
            tile_max_iterations=12000,
            max_images_per_tile=188,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:test",
            scaffold_artifact_s3_uri="s3://bucket/scaffold/model.tar.gz",
            training_env_fingerprint=benchmark.tile_input_hash_env_fingerprint(training_env),
        )

        stages = benchmark.build_benchmark_stages(
            manifest={"tiles": [tile_entry]},
            branch_name="agent-branch",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="bench",
            include_monolithic=False,
            include_scaffold=False,
            include_merge=False,
            orchestration_mode="fanout",
            tile_ids=["tile_13"],
            monolithic_max_iterations=8000,
            scaffold_max_iterations=2000,
            tile_max_iterations=12000,
            training_max_runtime_seconds=18000,
            extra_env={},
            timestamp=456,
            downscale_factor=1,
            include_review=False,
            proof_profile=benchmark.PROOF_PROFILE_NONE,
            tile_budget_mode="adaptive",
            max_images_per_tile=188,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:test",
            scaffold_artifact_s3_uri="s3://bucket/scaffold/model.tar.gz",
            reuse_tile_cache=True,
            tile_cache_manifest={
                "tile_13": {
                    "input_hash": budget.input_hash,
                    "artifact_s3_uri": "s3://bucket/cache/tile_13/model.tar.gz",
                    "quality_gate_status": "passed",
                    "ownership_gate_status": "merge_ownership_blocked",
                    "source_tile_core_ratio": 0.025578,
                    "v18_reference_merge_retention_ratio": 0.732865,
                }
            },
        )

        self.assertEqual(stages[0].stage_type, "train")
        self.assertEqual(stages[0].cache_status, "miss")
        self.assertIn("ownership_status_blocked", stages[0].cache_rejection_reasons)
        self.assertIn("ownership_distribution_below_minimum", stages[0].cache_rejection_reasons)

    def test_context_density_reuse_turns_dense_teacher_tile_into_non_training_stage(self):
        tile_entry = {
            "tile_id": "tile_04",
            "base_camera_ids": [f"frame_{index:03d}.jpg" for index in range(188)],
            "prior_min_budget_class": "hard",
        }

        stages = benchmark.build_benchmark_stages(
            manifest={"tiles": [tile_entry]},
            branch_name="agent-branch",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="bench",
            include_monolithic=False,
            include_scaffold=False,
            include_merge=True,
            orchestration_mode="fanout",
            tile_ids=["tile_04"],
            monolithic_max_iterations=8000,
            scaffold_max_iterations=2000,
            tile_max_iterations=12000,
            training_max_runtime_seconds=18000,
            extra_env={},
            timestamp=456,
            downscale_factor=1,
            include_review=False,
            proof_profile=benchmark.PROOF_PROFILE_NONE,
            tile_budget_mode="adaptive",
            max_images_per_tile=188,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:test",
            scaffold_artifact_s3_uri="s3://bucket/scaffold/model.tar.gz",
            enable_context_density_reuse=True,
            context_density_manifest={
                "tile_04": {
                    "artifact_s3_uri": "s3://bucket/v18/context/model.tar.gz",
                    "context_density_status": "passed",
                    "retained_gaussians": 956277,
                    "reference_retained_gaussians": 956277,
                    "min_retained_ratio_vs_reference": 0.95,
                    "context_preserve_enabled": True,
                }
            },
        )

        self.assertEqual(stages[0].stage_type, "context_density_tile")
        self.assertEqual(stages[0].cache_status, "context_density_hit")
        self.assertEqual(stages[0].source_artifact_uri, "s3://bucket/v18/context/model.tar.gz")
        self.assertEqual(stages[1].depends_on, ["T0_tile_04"])
        cost = benchmark.estimate_training_cost(
            stages,
            instance_type="ml.g5.2xlarge",
            max_runtime_seconds=18000,
            baseline_iterations=12000,
        )
        self.assertEqual(cost["train_stage_count"], 0)
        self.assertEqual(cost["estimated_usd"], 0.0)

    def test_context_density_reuse_rejects_low_density_ratio(self):
        tile_entry = {
            "tile_id": "tile_06",
            "base_camera_ids": [f"frame_{index:03d}.jpg" for index in range(188)],
            "prior_min_budget_class": "hard",
        }

        stages = benchmark.build_benchmark_stages(
            manifest={"tiles": [tile_entry]},
            branch_name="agent-branch",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="bench",
            include_monolithic=False,
            include_scaffold=False,
            include_merge=False,
            orchestration_mode="fanout",
            tile_ids=["tile_06"],
            monolithic_max_iterations=8000,
            scaffold_max_iterations=2000,
            tile_max_iterations=12000,
            training_max_runtime_seconds=18000,
            extra_env={},
            timestamp=456,
            downscale_factor=1,
            include_review=False,
            proof_profile=benchmark.PROOF_PROFILE_NONE,
            tile_budget_mode="adaptive",
            max_images_per_tile=188,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:test",
            scaffold_artifact_s3_uri="s3://bucket/scaffold/model.tar.gz",
            enable_context_density_reuse=True,
            context_density_manifest={
                "tile_06": {
                    "artifact_s3_uri": "s3://bucket/v18/context/model.tar.gz",
                    "context_density_status": "passed",
                    "retained_gaussians": 278178,
                    "reference_retained_gaussians": 1188805,
                    "min_retained_ratio_vs_reference": 0.95,
                    "context_preserve_enabled": True,
                }
            },
        )

        self.assertEqual(stages[0].stage_type, "train")
        self.assertEqual(stages[0].cache_status, "miss")
        self.assertIn("context_density_ratio_below_minimum", stages[0].cache_rejection_reasons)

    def test_context_density_stage_can_materialize_tile_from_full_tiled_artifact(self):
        stage = benchmark.BenchmarkStage(
            stage_name="T0_tile_04",
            stage_type="context_density_tile",
            training_mode="leaf_tile",
            output_s3_uri="s3://bucket/out/tiles/tile_04",
            tile_id="tile_04",
        )

        members = benchmark.artifact_members_for_stage(stage)
        self.assertIn("splat.ply", members)
        self.assertIn("tiles/tile_04/splat.ply", members)

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tile_dir = root / "tiles" / "tile_04"
            tile_dir.mkdir(parents=True)
            (tile_dir / "splat.ply").write_text("ply\n", encoding="utf-8")
            (tile_dir / "training_metadata.json").write_text('{"training_mode":"leaf_tile"}', encoding="utf-8")

            benchmark.materialize_context_density_tile(stage, root)

            self.assertEqual((root / "splat.ply").read_text(encoding="utf-8"), "ply\n")
            self.assertEqual(
                json.loads((root / "training_metadata.json").read_text(encoding="utf-8"))["training_mode"],
                "leaf_tile",
            )

    def test_manifest_overrides_must_be_provided_as_a_pair(self):
        with self.assertRaises(RuntimeError) as raised:
            benchmark.validate_manifest_override_args(
                tile_manifest_json="local/3dgs_tile_manifest.json",
                view_bucket_json="",
            )

        self.assertIn("--tile-manifest-json and --view-bucket-json", str(raised.exception))

    def test_build_adaptive_tile_budget_plan_keeps_horizon_tile_hard(self):
        tile = {
            "tile_id": "tile_08",
            "base_camera_ids": [f"frame_{index:03d}.jpg" for index in range(160)],
            "selected_cameras_by_role": {
                "horizon": [f"horizon_{index:03d}.jpg" for index in range(24)],
                "boundary": [f"boundary_{index:03d}.jpg" for index in range(12)],
            },
        }

        budget = benchmark.build_tile_budget_plan(
            tile,
            mode="adaptive",
            tile_max_iterations=12000,
            max_images_per_tile=128,
        )

        self.assertEqual(budget.budget_class, "hard")
        self.assertEqual(budget.max_iterations, 12000)
        self.assertEqual(budget.max_selected_images, 128)
        self.assertIn("horizon_support", budget.reasons)

    def test_build_benchmark_stages_applies_adaptive_leaf_budgets(self):
        manifest = {
            "tiles": [
                {
                    "tile_id": "tile_11",
                    "base_camera_ids": [f"frame_{index:03d}.jpg" for index in range(188)],
                    "prior_retained_gaussians": 68,
                },
                {
                    "tile_id": "tile_08",
                    "base_camera_ids": [f"frame_{index:03d}.jpg" for index in range(188)],
                    "selected_cameras_by_role": {"horizon": [f"horizon_{index:03d}.jpg" for index in range(24)]},
                },
            ]
        }

        stages = benchmark.build_benchmark_stages(
            manifest=manifest,
            branch_name="agent-branch",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="bench",
            include_monolithic=False,
            include_scaffold=False,
            include_merge=True,
            orchestration_mode="fanout",
            tile_ids=["tile_11", "tile_08"],
            monolithic_max_iterations=8000,
            scaffold_max_iterations=2000,
            tile_max_iterations=12000,
            training_max_runtime_seconds=21600,
            extra_env={},
            timestamp=456,
            downscale_factor=1,
            include_review=False,
            proof_profile=benchmark.PROOF_PROFILE_NONE,
            tile_budget_mode="adaptive",
            max_images_per_tile=188,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:test",
        )

        tile_11 = next(stage for stage in stages if stage.tile_id == "tile_11")
        tile_08 = next(stage for stage in stages if stage.tile_id == "tile_08")
        self.assertEqual(tile_11.environment["MAX_ITERATIONS"], "3000")
        self.assertEqual(tile_11.environment["TRAINING_MAX_SELECTED_IMAGES"], "96")
        self.assertEqual(tile_11.environment["TILE_BUDGET_CLASS"], "tiny")
        self.assertEqual(tile_11.environment["GLOBAL_SCAFFOLD_INIT_MAX_POINTS"], "300000")
        self.assertEqual(tile_11.environment["TRAINING_STOP_SPLIT_AT"], "3500")
        self.assertEqual(tile_11.environment["TRAINING_MAX_GAUSS_RATIO"], "3.0")
        self.assertEqual(tile_11.environment["SH_DEGREE"], "1")
        self.assertEqual(tile_11.environment["BG_SH_DEGREE"], "1")
        self.assertEqual(tile_08.environment["MAX_ITERATIONS"], "12000")
        self.assertEqual(tile_08.environment["TRAINING_MAX_SELECTED_IMAGES"], "188")
        self.assertEqual(tile_08.environment["TILE_BUDGET_CLASS"], "hard")
        self.assertRegex(tile_08.environment["TILE_INPUT_HASH"], r"^[0-9a-f]{64}$")

    def test_adaptive_leaf_budget_preserves_explicit_md1_hyperparameter_overrides(self):
        stages = benchmark.build_benchmark_stages(
            manifest={"tiles": [{"tile_id": "tile_02", "base_camera_ids": [f"frame_{index:03d}.jpg" for index in range(128)]}]},
            branch_name="agent-branch",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="bench",
            include_monolithic=False,
            include_scaffold=False,
            include_merge=False,
            orchestration_mode="fanout",
            tile_ids=["tile_02"],
            monolithic_max_iterations=8000,
            scaffold_max_iterations=2000,
            tile_max_iterations=12000,
            training_max_runtime_seconds=21600,
            extra_env={"SH_DEGREE": "2", "TRAINING_MAX_GAUSS_RATIO": "4.0"},
            timestamp=456,
            downscale_factor=1,
            include_review=False,
            proof_profile=benchmark.PROOF_PROFILE_NONE,
            tile_budget_mode="adaptive",
            max_images_per_tile=128,
            input_colmap_s3_uri="s3://bucket/colmap",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:test",
        )

        tile_stage = stages[0]
        self.assertEqual(tile_stage.environment["SH_DEGREE"], "2")
        self.assertEqual(tile_stage.environment["BG_SH_DEGREE"], "1")
        self.assertEqual(tile_stage.environment["TRAINING_MAX_GAUSS_RATIO"], "4.0")
        self.assertEqual(tile_stage.environment["TRAINING_STOP_SPLIT_AT"], "3500")

    def test_estimate_training_cost_uses_stage_iteration_budgets(self):
        stages = [
            benchmark.BenchmarkStage(
                stage_name="T0_tile_11",
                stage_type="train",
                training_mode="leaf_tile",
                output_s3_uri="s3://bucket/out/tile_11",
                environment={"MAX_ITERATIONS": "3000"},
            ),
            benchmark.BenchmarkStage(
                stage_name="T0_tile_08",
                stage_type="train",
                training_mode="leaf_tile",
                output_s3_uri="s3://bucket/out/tile_08",
                environment={"MAX_ITERATIONS": "12000"},
            ),
        ]

        estimate = benchmark.estimate_training_cost(
            stages,
            instance_type="ml.g5.2xlarge",
            max_runtime_seconds=14400,
            baseline_iterations=12000,
        )

        self.assertAlmostEqual(estimate["estimated_usd"], 7.575, places=3)
        self.assertEqual(estimate["train_stage_count"], 2)
        self.assertAlmostEqual(estimate["estimated_billable_hours"], 5.0, places=3)

    def test_estimate_training_cost_uses_prior_duration_for_hard_full_cover_tiles(self):
        stages = [
            benchmark.BenchmarkStage(
                stage_name="T0_tile_13",
                stage_type="train",
                training_mode="leaf_tile",
                output_s3_uri="s3://bucket/out/tile_13",
                tile_id="tile_13",
                budget_class="hard",
                environment={"MAX_ITERATIONS": "12000"},
                prior_duration_hours=4.73,
            )
        ]

        estimate = benchmark.estimate_training_cost(
            stages,
            instance_type="ml.g5.2xlarge",
            max_runtime_seconds=3600,
            baseline_iterations=12000,
        )

        self.assertAlmostEqual(estimate["estimated_billable_hours"], 4.73, places=3)
        self.assertAlmostEqual(estimate["estimated_usd"], 7.166, places=3)
        stage_estimate = estimate["stage_estimates"][0]
        self.assertEqual(stage_estimate["cost_basis"], "historical_prior_duration")
        self.assertEqual(stage_estimate["runtime_risk"], "prior_duration_exceeds_max_runtime")
        self.assertAlmostEqual(stage_estimate["runtime_cap_shortfall_hours"], 3.73, places=3)

    def test_estimate_training_cost_prefers_observed_fanout_leaf_duration(self):
        stages = [
            benchmark.BenchmarkStage(
                stage_name="T0_tile_13",
                stage_type="train",
                training_mode="leaf_tile",
                output_s3_uri="s3://bucket/out/tile_13",
                tile_id="tile_13",
                budget_class="hard",
                environment={"MAX_ITERATIONS": "12000"},
                prior_duration_hours=4.73,
                prior_fanout_duration_hours=0.982,
            )
        ]

        estimate = benchmark.estimate_training_cost(
            stages,
            instance_type="ml.g5.2xlarge",
            max_runtime_seconds=18000,
            baseline_iterations=12000,
        )

        self.assertAlmostEqual(estimate["estimated_billable_hours"], 0.982, places=3)
        self.assertAlmostEqual(estimate["estimated_usd"], 1.488, places=3)
        stage_estimate = estimate["stage_estimates"][0]
        self.assertEqual(stage_estimate["cost_basis"], "observed_fanout_leaf_duration")
        self.assertEqual(stage_estimate["runtime_risk"], None)
        self.assertAlmostEqual(stage_estimate["prior_fanout_duration_hours"], 0.982, places=3)

    def test_normalize_prior_tile_stats_keeps_observed_fanout_duration(self):
        stats = benchmark.normalize_prior_tile_stats(
            {
                "tiles": [
                    {
                        "tile_id": "tile_13",
                        "duration_hours": 4.73,
                        "observed_fanout_duration_hours": 0.982,
                        "observed_fanout_billable_time_seconds": 3535,
                    }
                ]
            }
        )

        self.assertEqual(stats["tile_13"]["prior_duration_hours"], 4.73)
        self.assertEqual(stats["tile_13"]["prior_fanout_duration_hours"], 0.982)
        self.assertEqual(stats["tile_13"]["prior_fanout_billable_time_seconds"], 3535)

    def test_adaptive_budget_can_use_budget_class_fanout_prior(self):
        tile_entry = {
            "tile_id": "tile_08",
            "selected_image_count": 188,
            "view_bucket_counts": {"near_detail": 52},
            "prior_fanout_duration_hours_by_budget": {"standard": 0.72, "hard": 1.08},
        }

        budget = benchmark.build_tile_budget_plan(
            tile_entry,
            mode="adaptive",
            tile_max_iterations=12000,
            max_images_per_tile=128,
        )

        self.assertEqual(budget.budget_class, "hard")
        self.assertAlmostEqual(budget.prior_fanout_duration_hours, 1.08, places=3)

    def test_estimate_training_cost_accounts_for_serial_tiled_pipeline_tiles(self):
        stages = [
            benchmark.BenchmarkStage(
                stage_name="T2_tiled_pipeline",
                stage_type="train",
                training_mode="tiled_pipeline",
                output_s3_uri="s3://bucket/out/tiled",
                environment={"MAX_ITERATIONS": "12000", "TILED_MAX_TILES": "14"},
            ),
        ]

        estimate = benchmark.estimate_training_cost(
            stages,
            instance_type="ml.g5.2xlarge",
            max_runtime_seconds=14400,
            baseline_iterations=12000,
        )

        self.assertAlmostEqual(estimate["estimated_billable_hours"], 56.0, places=3)
        self.assertAlmostEqual(estimate["estimated_usd"], 84.84, places=2)

    def test_fanout_execution_batches_group_leaf_tiles_by_concurrency(self):
        stages = [
            benchmark.BenchmarkStage("S0_scaffold", "train", "global_scaffold", "s3://bucket/scaffold"),
            benchmark.BenchmarkStage("T0_tile_00", "train", "leaf_tile", "s3://bucket/tile_00", tile_id="tile_00"),
            benchmark.BenchmarkStage("T0_tile_01", "train", "leaf_tile", "s3://bucket/tile_01", tile_id="tile_01"),
            benchmark.BenchmarkStage("T0_tile_02", "train", "leaf_tile", "s3://bucket/tile_02", tile_id="tile_02"),
            benchmark.BenchmarkStage("MERGE", "merge", "strict_core", "s3://bucket/merge"),
        ]

        batches = benchmark.fanout_execution_batches(stages, max_tile_concurrency=2)

        self.assertEqual(
            [[stage.stage_name for stage in batch] for batch in batches],
            [["S0_scaffold"], ["T0_tile_00", "T0_tile_01"], ["T0_tile_02"]],
        )

    def test_validate_submit_guardrails_requires_cost_experiment_and_v18_plan(self):
        args = types.SimpleNamespace(
            submit=True,
            max_estimated_usd=0.0,
            experiment_id="",
            v18_review_manifest_s3_uri="",
            baseline_review_manifest_s3_uri="",
            enable_spot=False,
            enable_checkpoints=False,
            checkpoint_s3_prefix="",
            spot_restart_proof_passed=False,
        )

        with self.assertRaises(RuntimeError) as raised:
            benchmark.validate_submit_guardrails(args, {"cost_estimate": {"estimated_usd": 1.0}})

        message = str(raised.exception)
        self.assertIn("--max-estimated-usd", message)
        self.assertIn("--experiment-id", message)
        self.assertIn("--v18-review-manifest-s3-uri", message)

    def test_validate_submit_guardrails_blocks_over_budget_and_unsafe_spot(self):
        args = types.SimpleNamespace(
            submit=True,
            max_estimated_usd=2.0,
            experiment_id="r2-smoke",
            v18_review_manifest_s3_uri="s3://bucket/v18-review",
            baseline_review_manifest_s3_uri="",
            enable_spot=True,
            enable_checkpoints=False,
            checkpoint_s3_prefix="s3://bucket/checkpoints",
            spot_restart_proof_passed=False,
            spot_max_wait_seconds=0,
            training_max_runtime_seconds=3600,
        )

        with self.assertRaises(RuntimeError) as raised:
            benchmark.validate_submit_guardrails(args, {"cost_estimate": {"estimated_usd": 3.0}})

        message = str(raised.exception)
        self.assertIn("estimated cost", message)
        self.assertIn("--spot-restart-proof-passed", message)
        self.assertIn("--spot-max-wait-seconds", message)

    def test_validate_submit_guardrails_blocks_unbounded_spot_wait(self):
        args = types.SimpleNamespace(
            submit=True,
            max_estimated_usd=2.0,
            experiment_id="r3-spot-smoke",
            v18_review_manifest_s3_uri="s3://bucket/v18-review",
            baseline_review_manifest_s3_uri="",
            enable_spot=True,
            enable_checkpoints=False,
            checkpoint_s3_prefix="s3://bucket/checkpoints",
            spot_restart_proof_passed=True,
            spot_max_wait_seconds=7200,
            training_max_runtime_seconds=3600,
            reuse_tile_cache=False,
        )

        with self.assertRaises(RuntimeError) as raised:
            benchmark.validate_submit_guardrails(args, {"cost_estimate": {"estimated_usd": 1.0}})

        self.assertIn("bounded Spot capacity waits", str(raised.exception))

    def test_validate_submit_guardrails_blocks_runtime_risk_stage_estimates(self):
        args = types.SimpleNamespace(
            submit=True,
            max_estimated_usd=20.0,
            experiment_id="r4-hardbudget",
            v18_review_manifest_s3_uri="s3://bucket/v18-review",
            baseline_review_manifest_s3_uri="",
            enable_spot=False,
            enable_checkpoints=True,
            checkpoint_s3_prefix="s3://bucket/checkpoints",
            spot_restart_proof_passed=False,
            reuse_tile_cache=False,
        )

        with self.assertRaises(RuntimeError) as raised:
            benchmark.validate_submit_guardrails(
                args,
                {
                    "cost_estimate": {
                        "estimated_usd": 7.17,
                        "stage_estimates": [
                            {
                                "stage_name": "T0_tile_13",
                                "tile_id": "tile_13",
                                "runtime_risk": "prior_duration_exceeds_max_runtime",
                            }
                        ],
                    }
                },
            )

        message = str(raised.exception)
        self.assertIn("runtime risk", message)
        self.assertIn("T0_tile_13", message)
        self.assertIn("prior_duration_exceeds_max_runtime", message)

    def test_validate_submit_guardrails_blocks_all_cache_hit_scaffold_spend(self):
        args = types.SimpleNamespace(
            submit=True,
            max_estimated_usd=1.0,
            experiment_id="cache-proof",
            v18_review_manifest_s3_uri="s3://bucket/v18-review",
            baseline_review_manifest_s3_uri="",
            enable_spot=False,
            enable_checkpoints=False,
            checkpoint_s3_prefix="",
            spot_restart_proof_passed=False,
            reuse_tile_cache=True,
        )

        with self.assertRaises(RuntimeError) as raised:
            benchmark.validate_submit_guardrails(
                args,
                {
                    "cost_estimate": {"estimated_usd": 0.25},
                    "stages": [
                        {"stage_type": "train", "training_mode": "global_scaffold"},
                        {"stage_type": "cached_tile", "training_mode": "leaf_tile"},
                    ],
                },
            )

        self.assertIn("scaffold training is still planned", str(raised.exception))

    def test_validate_submit_guardrails_requires_checkpoint_prefix_without_spot(self):
        args = types.SimpleNamespace(
            submit=True,
            max_estimated_usd=1.0,
            experiment_id="r2-checkpoint",
            v18_review_manifest_s3_uri="s3://bucket/v18-review",
            baseline_review_manifest_s3_uri="",
            enable_spot=False,
            enable_checkpoints=True,
            checkpoint_s3_prefix="",
            spot_restart_proof_passed=False,
            reuse_tile_cache=False,
        )

        with self.assertRaises(RuntimeError) as raised:
            benchmark.validate_submit_guardrails(args, {"cost_estimate": {"estimated_usd": 0.25}})

        self.assertIn("--checkpoint-s3-prefix", str(raised.exception))

    def test_validate_submit_guardrails_requires_checkpointing_for_resume_uri(self):
        args = types.SimpleNamespace(
            submit=True,
            max_estimated_usd=1.0,
            experiment_id="r2-checkpoint-restart",
            v18_review_manifest_s3_uri="s3://bucket/v18-review",
            baseline_review_manifest_s3_uri="",
            enable_spot=False,
            enable_checkpoints=False,
            checkpoint_s3_prefix="",
            checkpoint_resume_s3_uri="s3://bucket/prior-checkpoint",
            spot_restart_proof_passed=False,
            reuse_tile_cache=False,
        )

        with self.assertRaises(RuntimeError) as raised:
            benchmark.validate_submit_guardrails(args, {"cost_estimate": {"estimated_usd": 0.25}})

        self.assertIn("--checkpoint-resume-s3-uri requires", str(raised.exception))

    def test_validate_submit_guardrails_blocks_fanout_leaf_merge_review_spend(self):
        args = types.SimpleNamespace(
            submit=True,
            max_estimated_usd=2.0,
            experiment_id="r4-leaf-proof",
            v18_review_manifest_s3_uri="s3://bucket/v18-review",
            baseline_review_manifest_s3_uri="",
            enable_spot=False,
            enable_checkpoints=True,
            checkpoint_s3_prefix="s3://bucket/checkpoints",
            checkpoint_resume_s3_uri="",
            spot_restart_proof_passed=False,
            reuse_tile_cache=False,
            orchestration_mode="fanout",
            skip_merge=False,
            skip_review=False,
        )

        with self.assertRaises(RuntimeError) as raised:
            benchmark.validate_submit_guardrails(
                args,
                {
                    "cost_estimate": {"estimated_usd": 1.0},
                    "stages": [
                        {"stage_type": "train", "training_mode": "leaf_tile", "tile_id": "tile_10"},
                        {"stage_type": "merge", "training_mode": "strict_core"},
                        {"stage_type": "review", "training_mode": "quality_review"},
                    ],
                },
            )

        message = str(raised.exception)
        self.assertIn("--skip-merge", message)
        self.assertIn("post_leaf_preflight_gates", message)

    def test_validate_submit_guardrails_allows_fanout_leaf_proof_when_merge_review_skipped(self):
        args = types.SimpleNamespace(
            submit=True,
            max_estimated_usd=2.0,
            experiment_id="r4-leaf-proof",
            v18_review_manifest_s3_uri="s3://bucket/v18-review",
            baseline_review_manifest_s3_uri="",
            enable_spot=False,
            enable_checkpoints=True,
            checkpoint_s3_prefix="s3://bucket/checkpoints",
            checkpoint_resume_s3_uri="",
            spot_restart_proof_passed=False,
            reuse_tile_cache=False,
            orchestration_mode="fanout",
            skip_merge=True,
            skip_review=True,
        )

        benchmark.validate_submit_guardrails(
            args,
            {
                "cost_estimate": {"estimated_usd": 1.0},
                "stages": [
                    {"stage_type": "train", "training_mode": "leaf_tile", "tile_id": "tile_10"},
                ],
            },
        )

    def test_validate_submit_guardrails_blocks_full_14tile_without_rung_gate(self):
        args = types.SimpleNamespace(
            submit=True,
            max_estimated_usd=20.0,
            experiment_id="r6-full",
            v18_review_manifest_s3_uri="s3://bucket/v18-review",
            baseline_review_manifest_s3_uri="",
            enable_spot=False,
            enable_checkpoints=True,
            checkpoint_s3_prefix="s3://bucket/checkpoints",
            checkpoint_resume_s3_uri="",
            spot_restart_proof_passed=False,
            reuse_tile_cache=False,
            orchestration_mode="fanout",
            skip_merge=True,
            skip_review=True,
            production_rung_gate_json="",
        )

        with self.assertRaises(RuntimeError) as raised:
            benchmark.validate_submit_guardrails(
                args,
                {
                    "cost_estimate": {"estimated_usd": 18.0},
                    "selected_tile_ids": [f"tile_{tile_index:02d}" for tile_index in range(14)],
                },
            )

        self.assertIn("--production-rung-gate-json", str(raised.exception))

    def test_validate_submit_guardrails_blocks_full_14tile_when_rung_gate_is_incomplete(self):
        args = types.SimpleNamespace(
            submit=True,
            max_estimated_usd=20.0,
            experiment_id="r6-full",
            v18_review_manifest_s3_uri="s3://bucket/v18-review",
            baseline_review_manifest_s3_uri="",
            enable_spot=False,
            enable_checkpoints=True,
            checkpoint_s3_prefix="s3://bucket/checkpoints",
            checkpoint_resume_s3_uri="",
            spot_restart_proof_passed=False,
            reuse_tile_cache=False,
            orchestration_mode="fanout",
            skip_merge=True,
            skip_review=True,
            production_rung_gate_json="logs/rung-gate.json",
        )

        with self.assertRaises(RuntimeError) as raised:
            benchmark.validate_submit_guardrails(
                args,
                {
                    "cost_estimate": {"estimated_usd": 18.0},
                    "selected_tile_ids": [f"tile_{tile_index:02d}" for tile_index in range(14)],
                    "production_rung_gate": {
                        "r0_status": "passed",
                        "r1_status": "passed",
                        "r2_status": "blocked",
                        "r3_status": "passed",
                        "allow_full_14tile_submit": False,
                        "max_estimated_usd": 12.0,
                    },
                },
            )

        message = str(raised.exception)
        self.assertIn("r2_status", message)
        self.assertIn("allow_full_14tile_submit", message)
        self.assertIn("production rung gate cap", message)

    def test_validate_submit_guardrails_blocks_full_14tile_when_rung_gate_has_no_budget(self):
        args = types.SimpleNamespace(
            submit=True,
            max_estimated_usd=20.0,
            experiment_id="r6-full",
            v18_review_manifest_s3_uri="s3://bucket/v18-review",
            baseline_review_manifest_s3_uri="",
            enable_spot=False,
            enable_checkpoints=True,
            checkpoint_s3_prefix="s3://bucket/checkpoints",
            checkpoint_resume_s3_uri="",
            spot_restart_proof_passed=False,
            reuse_tile_cache=False,
            orchestration_mode="fanout",
            skip_merge=True,
            skip_review=True,
            production_rung_gate_json="logs/rung-gate.json",
        )

        with self.assertRaises(RuntimeError) as raised:
            benchmark.validate_submit_guardrails(
                args,
                {
                    "cost_estimate": {"estimated_usd": 18.0},
                    "selected_tile_ids": [f"tile_{tile_index:02d}" for tile_index in range(14)],
                    "production_rung_gate": {
                        "r0_status": "passed",
                        "r1_status": "accepted",
                        "r2_status": "quality_passed",
                        "r3_status": "ok",
                        "allow_full_14tile_submit": True,
                    },
                },
            )

        self.assertIn("max_estimated_usd > 0", str(raised.exception))

    def test_validate_submit_guardrails_blocks_full_14tile_when_rung_gate_has_no_evidence(self):
        args = types.SimpleNamespace(
            submit=True,
            max_estimated_usd=20.0,
            experiment_id="r6-full",
            v18_review_manifest_s3_uri="s3://bucket/v18-review",
            baseline_review_manifest_s3_uri="",
            enable_spot=False,
            enable_checkpoints=True,
            checkpoint_s3_prefix="s3://bucket/checkpoints",
            checkpoint_resume_s3_uri="",
            spot_restart_proof_passed=False,
            reuse_tile_cache=False,
            orchestration_mode="fanout",
            skip_merge=True,
            skip_review=True,
            production_rung_gate_json="logs/rung-gate.json",
        )

        with self.assertRaises(RuntimeError) as raised:
            benchmark.validate_submit_guardrails(
                args,
                {
                    "cost_estimate": {"estimated_usd": 18.0},
                    "selected_tile_ids": [f"tile_{tile_index:02d}" for tile_index in range(14)],
                    "production_rung_gate": {
                        "r0_status": "passed",
                        "r1_status": "accepted",
                        "r2_status": "quality_passed",
                        "r3_status": "ok",
                        "allow_full_14tile_submit": True,
                        "max_estimated_usd": 25.0,
                    },
                },
            )

        message = str(raised.exception)
        self.assertIn("missing evidence", message)
        self.assertIn("r0", message)
        self.assertIn("r3", message)

    def test_validate_submit_guardrails_allows_full_14tile_with_passing_rung_gate(self):
        args = types.SimpleNamespace(
            submit=True,
            max_estimated_usd=20.0,
            experiment_id="r6-full",
            v18_review_manifest_s3_uri="s3://bucket/v18-review",
            baseline_review_manifest_s3_uri="",
            enable_spot=False,
            enable_checkpoints=True,
            checkpoint_s3_prefix="s3://bucket/checkpoints",
            checkpoint_resume_s3_uri="",
            spot_restart_proof_passed=False,
            reuse_tile_cache=False,
            orchestration_mode="fanout",
            skip_merge=True,
            skip_review=True,
            production_rung_gate_json="logs/rung-gate.json",
        )

        benchmark.validate_submit_guardrails(
            args,
            {
                "cost_estimate": {"estimated_usd": 18.0},
                "selected_tile_ids": [f"tile_{tile_index:02d}" for tile_index in range(14)],
                "production_rung_gate": {
                    "r0_status": "passed",
                    "r1_status": "accepted",
                    "r2_status": "quality_passed",
                    "r3_status": "ok",
                    "allow_full_14tile_submit": True,
                    "max_estimated_usd": 25.0,
                    "rung_evidence": {
                        "r0": {"summary_json": "logs/r0-no-spend.json"},
                        "r1": {"dry_run_summary": "logs/r1-dry-run.json"},
                        "r2": {"test_log": "logs/r2-checkpoint-proof.log"},
                        "r3": {"review_manifest_s3_uri": "s3://bucket/r3-review/quality_review_manifest.json"},
                    },
                },
            },
        )

    def test_assert_s3_object_exists_probes_cache_artifact_uri(self):
        with mock.patch.object(benchmark, "run_command") as run_command:
            benchmark.assert_s3_object_exists("s3://bucket/cache/tile_00/model.tar.gz")

        run_command.assert_called_once_with(
            ["aws", "s3", "ls", "s3://bucket/cache/tile_00/model.tar.gz"],
            capture_output=True,
        )

    def test_create_training_job_payload_can_enable_spot_checkpointing(self):
        payload = benchmark.create_training_job_payload(
            branch_name="agent-branch",
            job_name="bench-spot",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest",
            role_arn="arn:aws:iam::123:role/test",
            input_s3_uri="s3://bucket/input",
            output_s3_uri="s3://bucket/output",
            environment={"TRAINING_MODE": "leaf_tile"},
            instance_type="ml.g5.2xlarge",
            volume_size_gb=100,
            max_runtime_seconds=18000,
            enable_spot=True,
            checkpoint_s3_uri="s3://bucket/checkpoints/bench-spot",
            max_wait_seconds=24000,
            experiment_id="r2-smoke",
        )

        self.assertTrue(payload["EnableManagedSpotTraining"])
        self.assertEqual(payload["CheckpointConfig"]["S3Uri"], "s3://bucket/checkpoints/bench-spot")
        self.assertEqual(payload["CheckpointConfig"]["LocalPath"], "/opt/ml/checkpoints")
        self.assertEqual(payload["StoppingCondition"]["MaxWaitTimeInSeconds"], 24000)
        self.assertIn({"Key": "ExperimentId", "Value": "r2-smoke"}, payload["Tags"])

    def test_create_training_job_payload_can_checkpoint_without_spot(self):
        payload = benchmark.create_training_job_payload(
            branch_name="agent-branch",
            job_name="bench-checkpoint",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest",
            role_arn="arn:aws:iam::123:role/test",
            input_s3_uri="s3://bucket/input",
            output_s3_uri="s3://bucket/output",
            environment={"TRAINING_MODE": "leaf_tile"},
            instance_type="ml.g5.2xlarge",
            volume_size_gb=100,
            max_runtime_seconds=3600,
            enable_checkpoints=True,
            checkpoint_s3_uri="s3://bucket/checkpoints/bench-checkpoint",
            experiment_id="r2-checkpoint",
        )

        self.assertNotIn("EnableManagedSpotTraining", payload)
        self.assertEqual(payload["CheckpointConfig"]["S3Uri"], "s3://bucket/checkpoints/bench-checkpoint")
        self.assertEqual(payload["CheckpointConfig"]["LocalPath"], "/opt/ml/checkpoints")

    def test_build_benchmark_stages_can_plan_checkpoint_uri_without_spot(self):
        stages = benchmark.build_benchmark_stages(
            manifest={"tiles": [{"tile_id": "tile_11"}]},
            branch_name="agent-branch",
            output_root_s3_uri="s3://bucket/out",
            job_prefix="bench",
            include_monolithic=False,
            include_scaffold=False,
            include_merge=False,
            orchestration_mode="fanout",
            tile_ids=["tile_11"],
            monolithic_max_iterations=8000,
            scaffold_max_iterations=2000,
            tile_max_iterations=3000,
            training_max_runtime_seconds=3600,
            extra_env={"TRAINING_ENABLE_CHECKPOINTS": "true"},
            timestamp=456,
            downscale_factor=1,
            include_review=False,
            proof_profile=benchmark.PROOF_PROFILE_NONE,
            enable_checkpoints=True,
            checkpoint_s3_prefix="s3://bucket/checkpoints",
        )

        self.assertEqual(stages[0].checkpoint_uri, "s3://bucket/checkpoints/bench-456-tile-11")
        self.assertFalse(stages[0].spot_enabled)
        self.assertEqual(
            stages[0].environment["TRAINING_CHECKPOINT_S3_URI"],
            "s3://bucket/checkpoints/bench-456-tile-11",
        )

    def test_extend_checkpoint_resume_stage_iterations_adds_real_restart_steps(self):
        stage = benchmark.BenchmarkStage(
            stage_name="T0_tile_11",
            stage_type="train",
            training_mode="leaf_tile",
            output_s3_uri="s3://bucket/out/tile_11",
            tile_id="tile_11",
            environment={
                "MAX_ITERATIONS": "3000",
                "TRAINING_CHECKPOINT_RESUME_S3_URI": "s3://bucket/prior/resume_checkpoint",
                "TRAINING_STEPS_PER_EVAL_IMAGE": "3001",
                "TRAINING_STEPS_PER_EVAL_ALL_IMAGES": "12001",
                "TRAINING_STEPS_PER_SAVE": "250",
                "TILE_INPUT_HASH": "basehash",
            },
            max_iterations=3000,
        )
        expected_hash = benchmark.derive_checkpoint_resume_input_hash(
            base_input_hash="basehash",
            checkpoint_resume_s3_uri="s3://bucket/prior/resume_checkpoint",
            checkpoint_resume_step=2999,
            max_iterations=3250,
            extra_iterations=250,
        )

        changes = benchmark.extend_checkpoint_resume_stage_iterations(
            [stage],
            checkpoint_resume_step=2999,
            extra_iterations=250,
        )

        self.assertEqual(stage.environment["MAX_ITERATIONS"], "3250")
        self.assertEqual(stage.max_iterations, 3250)
        self.assertEqual(stage.environment["TRAINING_STEPS_PER_EVAL_IMAGE"], "3251")
        self.assertEqual(stage.environment["TRAINING_STEPS_PER_EVAL_ALL_IMAGES"], "12001")
        self.assertEqual(stage.environment["TRAINING_STEPS_PER_SAVE"], "250")
        self.assertEqual(stage.environment["TILE_INPUT_HASH"], expected_hash)
        self.assertEqual(stage.input_hash, expected_hash)
        self.assertEqual(
            changes,
            [
                {
                    "stage_name": "T0_tile_11",
                    "tile_id": "tile_11",
                    "resume_step": 2999,
                    "previous_max_iterations": 3000,
                    "max_iterations": 3250,
                    "extra_iterations": 250,
                    "previous_input_hash": "basehash",
                    "input_hash": expected_hash,
                }
            ],
        )

    def test_extend_checkpoint_resume_stage_iterations_blocks_noop_restart(self):
        stage = benchmark.BenchmarkStage(
            stage_name="T0_tile_11",
            stage_type="train",
            training_mode="leaf_tile",
            output_s3_uri="s3://bucket/out/tile_11",
            environment={
                "MAX_ITERATIONS": "3000",
                "TRAINING_CHECKPOINT_RESUME_S3_URI": "s3://bucket/prior/resume_checkpoint",
            },
        )

        with self.assertRaises(RuntimeError) as raised:
            benchmark.extend_checkpoint_resume_stage_iterations(
                [stage],
                checkpoint_resume_step=2999,
                extra_iterations=0,
            )

        self.assertIn("--checkpoint-resume-extra-iterations", str(raised.exception))

    def test_create_training_job_payload_includes_branch_tag(self):
        payload = benchmark.create_training_job_payload(
            branch_name="agent-branch",
            job_name="bench-123",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest",
            role_arn="arn:aws:iam::123:role/test",
            input_s3_uri="s3://bucket/input",
            output_s3_uri="s3://bucket/output",
            environment={"TRAINING_MODE": "tiled_pipeline"},
            instance_type="ml.g5.2xlarge",
            volume_size_gb=100,
            max_runtime_seconds=18000,
        )

        self.assertEqual(payload["TrainingJobName"], "bench-123")
        self.assertEqual(payload["Environment"]["TRAINING_MODE"], "tiled_pipeline")
        self.assertEqual(payload["StoppingCondition"]["MaxRuntimeInSeconds"], 18000)
        self.assertIn({"Key": "Branch", "Value": "agent-branch"}, payload["Tags"])

    def test_create_training_job_payload_can_mount_reusable_scaffold_channel(self):
        payload = benchmark.create_training_job_payload(
            branch_name="agent-branch",
            job_name="bench-123",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest",
            role_arn="arn:aws:iam::123:role/test",
            input_s3_uri="s3://bucket/input",
            output_s3_uri="s3://bucket/output",
            environment={"TRAINING_MODE": "tiled_pipeline"},
            instance_type="ml.g5.2xlarge",
            volume_size_gb=100,
            max_runtime_seconds=18000,
            scaffold_artifact_s3_uri="s3://bucket/scaffold-output",
        )

        channels = {channel["ChannelName"]: channel for channel in payload["InputDataConfig"]}
        self.assertEqual(channels["training"]["DataSource"]["S3DataSource"]["S3Uri"], "s3://bucket/input")
        self.assertEqual(channels["scaffold"]["DataSource"]["S3DataSource"]["S3Uri"], "s3://bucket/scaffold-output")

    def test_create_training_job_payload_can_mount_tile_selection_channel(self):
        payload = benchmark.create_training_job_payload(
            branch_name="agent-branch",
            job_name="bench-123",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest",
            role_arn="arn:aws:iam::123:role/test",
            input_s3_uri="s3://bucket/input",
            output_s3_uri="s3://bucket/output",
            environment={"TRAINING_MODE": "leaf_tile"},
            instance_type="ml.g5.2xlarge",
            volume_size_gb=100,
            max_runtime_seconds=18000,
            tile_selection_s3_uri="s3://bucket/out/inputs/tile-selection",
        )

        channels = {channel["ChannelName"]: channel for channel in payload["InputDataConfig"]}
        self.assertEqual(
            channels["tile-selection"]["DataSource"]["S3DataSource"]["S3Uri"],
            "s3://bucket/out/inputs/tile-selection",
        )

    def test_attach_tile_selection_channel_uses_absolute_paths_for_tiled_train_stages(self):
        stages = [
            benchmark.BenchmarkStage("M0_monolithic", "train", "monolithic", "s3://bucket/mono"),
            benchmark.BenchmarkStage("T0_tile_11", "train", "leaf_tile", "s3://bucket/tile"),
            benchmark.BenchmarkStage("MERGE", "merge", "strict_core", "s3://bucket/merge"),
        ]

        benchmark.attach_tile_selection_channel_to_stages(stages)

        self.assertNotIn("TILE_MANIFEST_PATH", stages[0].environment or {})
        self.assertEqual(
            stages[1].environment["TILE_MANIFEST_PATH"],
            "/opt/ml/input/data/tile-selection/3dgs_tile_manifest.json",
        )
        self.assertEqual(
            stages[1].environment["VIEW_BUCKET_MANIFEST_PATH"],
            "/opt/ml/input/data/tile-selection/3dgs_view_buckets.json",
        )
        self.assertIsNone(stages[2].environment)

    def test_upload_tile_selection_manifests_copies_resolved_inputs(self):
        calls = []

        def fake_run(command, *, capture_output=False):
            calls.append(command)
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        with mock.patch.object(benchmark, "run_command", side_effect=fake_run):
            benchmark.upload_tile_selection_manifests(
                {"tiles": [{"tile_id": "tile_11"}]},
                {"boundary_camera_ids": ["DJI_0001.JPG"]},
                "s3://bucket/out/inputs/tile-selection/",
            )

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][:3], ["aws", "s3", "cp"])
        self.assertEqual(calls[0][-1], "s3://bucket/out/inputs/tile-selection/3dgs_tile_manifest.json")
        self.assertEqual(calls[1][-1], "s3://bucket/out/inputs/tile-selection/3dgs_view_buckets.json")

    def test_create_quality_review_processing_payload_includes_model_and_colmap_inputs(self):
        payload = benchmark.create_quality_review_processing_payload(
            branch_name="agent-branch",
            job_name="bench-123-quality",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest",
            role_arn="arn:aws:iam::123:role/test",
            model_artifact_s3_uri="s3://bucket/model.tar.gz",
            colmap_s3_uri="s3://bucket/colmap",
            output_s3_uri="s3://bucket/review",
            environment={"QUALITY_REVIEW_MAX_IMAGES_PER_BUCKET": "4"},
            instance_type="ml.g5.2xlarge",
            volume_size_gb=100,
            max_runtime_seconds=7200,
        )

        self.assertEqual(payload["ProcessingJobName"], "bench-123-quality")
        self.assertEqual(payload["AppSpecification"]["ContainerEntrypoint"], ["python3", "/opt/ml/code/run_tiled_quality_review.py"])
        self.assertEqual(payload["ProcessingInputs"][0]["S3Input"]["S3Uri"], "s3://bucket/model.tar.gz")
        self.assertEqual(payload["ProcessingInputs"][1]["S3Input"]["S3Uri"], "s3://bucket/colmap")
        self.assertEqual(payload["Environment"]["QUALITY_REVIEW_MAX_IMAGES_PER_BUCKET"], "4")

    def test_create_quality_review_processing_payload_can_mount_frozen_and_baseline_manifests(self):
        payload = benchmark.create_quality_review_processing_payload(
            branch_name="agent-branch",
            job_name="bench-123-quality",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest",
            role_arn="arn:aws:iam::123:role/test",
            model_artifact_s3_uri="s3://bucket/model.tar.gz",
            colmap_s3_uri="s3://bucket/colmap",
            output_s3_uri="s3://bucket/review",
            environment={},
            instance_type="ml.g5.2xlarge",
            volume_size_gb=100,
            max_runtime_seconds=7200,
            review_camera_manifest_s3_uri="s3://bucket/review-input",
            baseline_review_manifest_s3_uri="s3://bucket/baseline-review",
        )

        self.assertEqual(
            [processing_input["InputName"] for processing_input in payload["ProcessingInputs"]],
            ["model", "colmap", "review-manifest", "baseline-review"],
        )
        self.assertEqual(
            payload["Environment"]["FROZEN_REVIEW_CAMERA_MANIFEST"],
            "/opt/ml/processing/input/review/review_camera_manifest.json",
        )
        self.assertEqual(
            payload["Environment"]["BASELINE_REVIEW_MANIFEST"],
            "/opt/ml/processing/input/baseline-review/quality_review_manifest.json",
        )

    def test_create_quality_review_training_payload_uses_multi_channel_inputs(self):
        payload = benchmark.create_quality_review_training_payload(
            branch_name="agent-branch",
            job_name="bench-123-quality",
            image_uri="123.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest",
            role_arn="arn:aws:iam::123:role/test",
            model_artifact_s3_uri="s3://bucket/model.tar.gz",
            colmap_s3_uri="s3://bucket/colmap",
            output_s3_uri="s3://bucket/review-output",
            environment={"QUALITY_REVIEW_RENDER_SCALE": "0.25"},
            instance_type="ml.g5.2xlarge",
            volume_size_gb=100,
            max_runtime_seconds=7200,
            review_camera_manifest_s3_uri="s3://bucket/review-input",
            baseline_review_manifest_s3_uri="s3://bucket/baseline-review",
        )

        self.assertEqual(payload["TrainingJobName"], "bench-123-quality")
        self.assertEqual(payload["AlgorithmSpecification"]["ContainerEntrypoint"], ["python3", "/opt/ml/code/run_tiled_quality_review.py"])
        self.assertEqual(
            [channel["ChannelName"] for channel in payload["InputDataConfig"]],
            ["model", "colmap", "review-manifest", "baseline-review"],
        )
        self.assertEqual(payload["Environment"]["MODEL_INPUT_DIR"], "/opt/ml/input/data/model")
        self.assertEqual(payload["Environment"]["OUTPUT_DIR"], "/opt/ml/model")
        self.assertEqual(payload["Environment"]["QUALITY_REVIEW_RENDER_SCALE"], "0.25")
        self.assertEqual(
            payload["Environment"]["FROZEN_REVIEW_CAMERA_MANIFEST"],
            "/opt/ml/input/data/review-manifest/review_camera_manifest.json",
        )

    def test_resolve_execution_context_accepts_explicit_role_image_and_output_without_branch_stack(self):
        original_find = benchmark.find_branch_ml_stack
        original_tag = benchmark.get_branch_ecr_tag
        try:
            def fail_find(_branch_name):
                raise RuntimeError("missing stack")

            benchmark.find_branch_ml_stack = fail_find
            benchmark.get_branch_ecr_tag = lambda _branch_name: "branch-tag"
            args = types.SimpleNamespace(
                stack_name="",
                role_arn="arn:aws:iam::123456789012:role/test",
                image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:test",
                output_root_s3_uri="s3://bucket/manual-validations/test/3dgs",
                image_tag="",
                job_prefix="bench",
            )

            context = benchmark.resolve_execution_context(
                branch_name="agent-branch",
                timestamp=123,
                args=args,
            )

            self.assertIsNone(context.stack_name)
            self.assertEqual(context.role_arn, args.role_arn)
            self.assertEqual(context.image_uri, args.image_uri)
            self.assertEqual(context.output_root_s3_uri, args.output_root_s3_uri)
        finally:
            benchmark.find_branch_ml_stack = original_find
            benchmark.get_branch_ecr_tag = original_tag

    def test_resolve_execution_context_uses_named_stack_when_provided(self):
        original_get_stack_outputs = benchmark.get_stack_outputs
        original_get_role = benchmark.get_sagemaker_role_arn
        original_tag = benchmark.get_branch_ecr_tag
        try:
            benchmark.get_stack_outputs = lambda stack_name: (
                stack_name,
                {
                    "GaussianRepositoryUri": "123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs",
                    "MLBucketName": "spaceport-ml-processing-staging",
                },
            )
            benchmark.get_sagemaker_role_arn = lambda stack_name: f"arn:aws:iam::123456789012:role/{stack_name}"
            benchmark.get_branch_ecr_tag = lambda _branch_name: "branch-tag"
            args = types.SimpleNamespace(
                stack_name="SpaceportMLPipelineStagingStack",
                role_arn="",
                image_uri="",
                output_root_s3_uri="",
                image_tag="",
                job_prefix="bench",
            )

            context = benchmark.resolve_execution_context(
                branch_name="agent-branch",
                timestamp=123,
                args=args,
            )

            self.assertEqual(context.stack_name, "SpaceportMLPipelineStagingStack")
            self.assertEqual(
                context.image_uri,
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:branch-tag",
            )
            self.assertEqual(context.role_arn, "arn:aws:iam::123456789012:role/SpaceportMLPipelineStagingStack")
            self.assertEqual(
                context.output_root_s3_uri,
                "s3://spaceport-ml-processing-staging/manual-validations/bench-123/3dgs",
            )
        finally:
            benchmark.get_stack_outputs = original_get_stack_outputs
            benchmark.get_sagemaker_role_arn = original_get_role
            benchmark.get_branch_ecr_tag = original_tag


if __name__ == "__main__":
    unittest.main()
