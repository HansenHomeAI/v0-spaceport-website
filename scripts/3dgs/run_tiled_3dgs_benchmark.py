#!/usr/bin/env python3
"""Launch cheap, resumable tiled 3DGS benchmark ladders against the current branch stack."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
THREE_DGS_ROOT = REPO_ROOT / "infrastructure" / "containers" / "3dgs"
if str(THREE_DGS_ROOT) not in sys.path:
    sys.path.insert(0, str(THREE_DGS_ROOT))

from tile_pipeline import resolve_tiled_input_manifests

MERGE_SCRIPT_PATH = REPO_ROOT / "infrastructure" / "containers" / "3dgs" / "merge_gaussian_tiles.py"
DEFAULT_SCAFFOLD_MAX_ITERATIONS = 4000
DEFAULT_TILE_MAX_ITERATIONS = 12000
DEFAULT_INSTANCE_TYPE = "ml.g5.2xlarge"
DEFAULT_VOLUME_SIZE_GB = 100
DEFAULT_TRAINING_MAX_RUNTIME_SECONDS = 14400
DEFAULT_REVIEW_MAX_RUNTIME_SECONDS = 7200
DEFAULT_CHECKPOINT_SAVE_STEPS = 1000
MAX_SPOT_EXTRA_WAIT_SECONDS = 1800
MD1_PRODUCTION_TILE_ENV_DEFAULTS = {
    "GLOBAL_SCAFFOLD_INIT_MAX_POINTS": "300000",
    "GLOBAL_SCAFFOLD_REQUIRE_FILTERED_INIT": "true",
    "TRAINING_STOP_SPLIT_AT": "3500",
    "TRAINING_MAX_GAUSS_RATIO": "3.0",
    "SH_DEGREE": "1",
    "BG_SH_DEGREE": "1",
}
TILE_INPUT_HASH_ENV_KEYS = (
    "MODEL_VARIANT",
    "BILATERAL_PROCESSING",
    "ENABLE_BG_MODEL",
    "ENABLE_ALPHA_LOSS",
    "ENABLE_ROBUST_MASK",
    "GLOBAL_SCAFFOLD_INIT_MAX_POINTS",
    "GLOBAL_SCAFFOLD_REQUIRE_FILTERED_INIT",
    "TRAINING_STOP_SPLIT_AT",
    "TRAINING_MAX_GAUSS_RATIO",
    "SH_DEGREE",
    "BG_SH_DEGREE",
)
SCAFFOLD_CHANNEL_DIR = "/opt/ml/input/data/scaffold"
TILE_SELECTION_CHANNEL_NAME = "tile-selection"
TILE_SELECTION_CHANNEL_DIR = f"/opt/ml/input/data/{TILE_SELECTION_CHANNEL_NAME}"
TILE_SELECTION_TRAINING_MODES = {"global_scaffold", "leaf_tile", "tiled_pipeline"}
UNSUPPORTED_BILATERAL_VARIANTS = {"splatfacto-w-light", "splatfacto-w"}
PROOF_PROFILE_NONE = "none"
PROOF_PROFILE_QUALITY_GATE_LOW_MEMORY = "quality_gate_low_memory"
QUALITY_GATE_LOW_MEMORY_STOP_SPLIT_AT = 8500
QUALITY_GATE_MULTI_TILE_STOP_SPLIT_AT = 7000
QUALITY_GATE_MULTI_TILE_MAX_GAUSS_RATIO = "8.0"
INSTANCE_HOURLY_RATES_USD = {
    "ml.g5.2xlarge": 1.515,
    "ml.g5.xlarge": 1.408,
    "ml.g6.xlarge": 1.127,
    "ml.g4dn.xlarge": 0.736,
}
DEFAULT_V18_NON_REGRESSION_THRESHOLDS = {
    "median_psnr_min_delta": -0.25,
    "median_ssim_min_delta": -0.005,
    "median_lpips_max_delta": 0.010,
    "single_camera_psnr_min_delta": -0.75,
    "single_camera_lpips_max_delta": 0.025,
    "horizon_sky_score_min_ratio": 0.98,
}
BUDGET_CLASS_RANK = {
    "skip": 0,
    "tiny": 1,
    "standard": 2,
    "hard": 3,
}
PASSING_GATE_STATUSES = {"passed", "pass", "ok", "promoted", "accepted", "quality_passed"}
PASSING_RUNG_STATUSES = PASSING_GATE_STATUSES
REQUIRED_PRODUCTION_RUNG_STATUS_FIELDS = ("r0_status", "r1_status", "r2_status", "r3_status")
REQUIRED_PRODUCTION_RUNG_EVIDENCE_KEYS = ("r0", "r1", "r2", "r3")
PRODUCTION_RUNG_EVIDENCE_REFERENCE_KEYS = (
    "artifact_s3_uri",
    "dry_run_summary",
    "manifest_json",
    "review_manifest_s3_uri",
    "summary_json",
    "test_log",
)


def run_command(command: Sequence[str], *, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        check=True,
        text=True,
        capture_output=capture_output,
    )


def aws_json(*args: str) -> dict:
    command = ["aws", *args, "--output", "json"]
    last_error: subprocess.CalledProcessError | None = None
    for attempt in range(3):
        try:
            result = run_command(command, capture_output=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as exc:
            last_error = exc
            if attempt == 2:
                break
            time.sleep(5 * (attempt + 1))
    assert last_error is not None
    raise last_error


def parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Expected s3:// URI, got: {uri}")
    bucket, _, key = uri[5:].partition("/")
    if not bucket:
        raise ValueError(f"Invalid S3 URI missing bucket: {uri}")
    return bucket, key


def load_s3_json(s3_uri: str) -> dict:
    result = run_command(["aws", "s3", "cp", s3_uri, "-"], capture_output=True)
    return json.loads(result.stdout)


def load_json_path_or_s3(uri_or_path: str) -> dict:
    value = uri_or_path.strip()
    if not value:
        return {}
    if value.startswith("s3://"):
        return load_s3_json(value)
    return json.loads(Path(value).read_text(encoding="utf-8"))


def load_production_rung_gate(path_or_s3: str) -> dict:
    if not path_or_s3:
        return {}
    gate = load_json_path_or_s3(path_or_s3)
    if not isinstance(gate, dict):
        raise RuntimeError("--production-rung-gate-json must resolve to a JSON object")
    return gate


def s3_json_or_none(s3_uri: str) -> dict | None:
    result = subprocess.run(
        ["aws", "s3", "cp", s3_uri, "-"],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def checkpoint_step_from_path(path: str) -> int | None:
    match = re.search(r"(?:^|/)step-(\d+)\.ckpt$", str(path))
    if not match:
        return None
    return int(match.group(1))


def checkpoint_step_from_manifest(manifest: dict) -> int | None:
    latest_step = checkpoint_step_from_path(str(manifest.get("latest_checkpoint") or ""))
    if latest_step is not None:
        return latest_step
    candidate_steps = [
        step
        for step in (
            checkpoint_step_from_path(str(entry.get("path") or ""))
            for entry in manifest.get("checkpoint_files", [])
            if isinstance(entry, dict)
        )
        if step is not None
    ]
    return max(candidate_steps) if candidate_steps else None


def checkpoint_resume_manifest_s3_uri(checkpoint_resume_s3_uri: str) -> str:
    return f"{normalize_s3_prefix(checkpoint_resume_s3_uri)}/checkpoint_manifest.json"


def resolve_checkpoint_resume_step(checkpoint_resume_s3_uri: str) -> tuple[int | None, str]:
    if not checkpoint_resume_s3_uri:
        return None, ""
    manifest_s3_uri = checkpoint_resume_manifest_s3_uri(checkpoint_resume_s3_uri)
    manifest = s3_json_or_none(manifest_s3_uri)
    if manifest is None:
        return None, manifest_s3_uri
    return checkpoint_step_from_manifest(manifest), manifest_s3_uri


def _int_env_value(env: Dict[str, str], key: str) -> int | None:
    try:
        return int(str(env.get(key) or "").strip())
    except ValueError:
        return None


def _int_or_none(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def derive_checkpoint_resume_input_hash(
    *,
    base_input_hash: str,
    checkpoint_resume_s3_uri: str,
    checkpoint_resume_step: int,
    max_iterations: int,
    extra_iterations: int,
) -> str:
    payload = {
        "base_input_hash": base_input_hash,
        "checkpoint_resume_s3_uri": checkpoint_resume_s3_uri,
        "checkpoint_resume_step": checkpoint_resume_step,
        "checkpoint_resume_extra_iterations": extra_iterations,
        "max_iterations": max_iterations,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def extend_checkpoint_resume_stage_iterations(
    stages: Sequence["BenchmarkStage"],
    *,
    checkpoint_resume_step: int | None,
    extra_iterations: int,
) -> list[dict]:
    if checkpoint_resume_step is None:
        return []
    if extra_iterations < 0:
        raise RuntimeError("--checkpoint-resume-extra-iterations must be >= 0")

    changes: list[dict] = []
    target_iterations = checkpoint_resume_step + extra_iterations + 1
    for stage in stages:
        if stage.stage_type != "train":
            continue
        env = dict(stage.environment or {})
        if not env.get("TRAINING_CHECKPOINT_RESUME_S3_URI"):
            continue
        current_iterations = _int_env_value(env, "MAX_ITERATIONS")
        if current_iterations is None:
            raise RuntimeError(f"{stage.stage_name} has non-integer MAX_ITERATIONS for checkpoint resume")
        if current_iterations <= checkpoint_resume_step + 1 and extra_iterations <= 0:
            raise RuntimeError(
                f"{stage.stage_name} resumes from checkpoint step {checkpoint_resume_step} "
                f"but MAX_ITERATIONS={current_iterations}; pass --checkpoint-resume-extra-iterations "
                "so the restart proof runs real additional training steps."
            )
        if current_iterations >= target_iterations:
            continue

        env["MAX_ITERATIONS"] = str(target_iterations)
        suppressed_step = str(target_iterations + 1)
        for key in ("TRAINING_STEPS_PER_EVAL_IMAGE", "TRAINING_STEPS_PER_EVAL_ALL_IMAGES"):
            current_eval_step = _int_env_value(env, key)
            if current_eval_step is not None and current_eval_step <= target_iterations:
                env[key] = suppressed_step
        previous_input_hash = str(env.get("TILE_INPUT_HASH") or stage.input_hash or "")
        input_hash = ""
        if previous_input_hash:
            input_hash = derive_checkpoint_resume_input_hash(
                base_input_hash=previous_input_hash,
                checkpoint_resume_s3_uri=str(env.get("TRAINING_CHECKPOINT_RESUME_S3_URI") or ""),
                checkpoint_resume_step=checkpoint_resume_step,
                max_iterations=target_iterations,
                extra_iterations=extra_iterations,
            )
            env["TILE_INPUT_HASH"] = input_hash
            stage.input_hash = input_hash
        stage.environment = env
        if stage.max_iterations is not None and stage.max_iterations < target_iterations:
            stage.max_iterations = target_iterations
        change = {
            "stage_name": stage.stage_name,
            "tile_id": stage.tile_id,
            "resume_step": checkpoint_resume_step,
            "previous_max_iterations": current_iterations,
            "max_iterations": target_iterations,
            "extra_iterations": extra_iterations,
        }
        if input_hash:
            change["previous_input_hash"] = previous_input_hash
            change["input_hash"] = input_hash
        changes.append(change)
    return changes


def download_sparse_support_dir(colmap_s3_uri: str, *, scratch_dir: Path) -> Path | None:
    sparse_dir = scratch_dir / "sparse" / "0"
    sparse_dir.mkdir(parents=True, exist_ok=True)
    copy_results: dict[str, subprocess.CompletedProcess[str]] = {}
    for file_name in ("images.txt", "points3D.txt"):
        source_uri = f"{normalize_s3_prefix(colmap_s3_uri)}/sparse/0/{file_name}"
        target_path = sparse_dir / file_name
        result = subprocess.run(
            ["aws", "s3", "cp", source_uri, str(target_path)],
            check=False,
            text=True,
            capture_output=True,
        )
        copy_results[file_name] = result

    copied_files = [
        file_name
        for file_name, result in copy_results.items()
        if result.returncode == 0 and (sparse_dir / file_name).exists() and (sparse_dir / file_name).stat().st_size > 0
    ]
    if len(copied_files) == len(copy_results):
        return sparse_dir
    if copied_files:
        missing = sorted(set(copy_results) - set(copied_files))
        raise RuntimeError(
            "Incomplete sparse support download; refusing to synthesize ownership bounds "
            f"from partial COLMAP sparse files. copied={copied_files} missing={missing}"
        )
    return None


def get_current_branch() -> str:
    result = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True)
    return result.stdout.strip()


def get_branch_ecr_tag(branch_name: str) -> str:
    result = run_command(
        [
            "python3",
            str(REPO_ROOT / "scripts" / "get_branch_suffix.py"),
            branch_name,
            "--mode",
            "ecr",
        ],
        capture_output=True,
    )
    return result.stdout.strip()


def stack_outputs(stack: dict) -> Dict[str, str]:
    outputs: Dict[str, str] = {}
    for entry in stack.get("Outputs", []):
        outputs[entry["OutputKey"]] = entry["OutputValue"]
    return outputs


def find_branch_ml_stack(branch_name: str) -> tuple[str, Dict[str, str]]:
    response = aws_json("cloudformation", "describe-stacks")
    for stack in response.get("Stacks", []):
        outputs = stack_outputs(stack)
        if outputs.get("BranchName") != branch_name:
            continue
        if "MLBucketName" not in outputs or "GaussianRepositoryUri" not in outputs:
            continue
        return stack["StackName"], outputs
    raise RuntimeError(f"Could not find an ML stack deployment for branch {branch_name}")


def get_stack_outputs(stack_name: str) -> tuple[str, Dict[str, str]]:
    response = aws_json("cloudformation", "describe-stacks", "--stack-name", stack_name)
    stacks = response.get("Stacks", [])
    if not stacks:
        raise RuntimeError(f"Could not describe stack {stack_name}")
    stack = stacks[0]
    return stack["StackName"], stack_outputs(stack)


def get_sagemaker_role_arn(stack_name: str) -> str:
    resources = aws_json("cloudformation", "list-stack-resources", "--stack-name", stack_name)
    for resource in resources.get("StackResourceSummaries", []):
        logical_id = resource.get("LogicalResourceId", "")
        physical_id = resource.get("PhysicalResourceId", "")
        if not (
            logical_id.startswith("SageMakerExecutionRole")
            or physical_id.startswith("Spaceport-SageMaker-Role-")
        ):
            continue
        role_name = physical_id
        role = aws_json("iam", "get-role", "--role-name", role_name)
        return role["Role"]["Arn"]
    raise RuntimeError(f"Could not resolve SageMakerExecutionRole from stack {stack_name}")


def parse_env(values: Sequence[str]) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Environment override must look like KEY=VALUE: {value}")
        key, raw_value = value.split("=", 1)
        env[key] = raw_value
    return env


def parse_tile_int_map(values: Sequence[str], *, label: str) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"{label} must look like tile_id=count: {value}")
        tile_id, raw_count = value.split("=", 1)
        tile_id = tile_id.strip()
        if not tile_id:
            raise ValueError(f"{label} has an empty tile_id: {value}")
        try:
            count = int(raw_count)
        except ValueError as exc:
            raise ValueError(f"{label} count must be an integer: {value}") from exc
        if count <= 0:
            raise ValueError(f"{label} count must be positive: {value}")
        mapping[tile_id] = count
    return mapping


def normalize_s3_prefix(uri: str) -> str:
    return uri.rstrip("/")


def upload_tile_selection_manifests(tile_manifest: dict, view_buckets: dict, s3_uri: str) -> None:
    """Publish the exact resolved tile-selection inputs that SageMaker should mount."""
    output_prefix = normalize_s3_prefix(s3_uri)
    with tempfile.TemporaryDirectory(prefix="3dgs-tile-selection-") as tmp:
        tmpdir = Path(tmp)
        manifest_path = tmpdir / "3dgs_tile_manifest.json"
        view_buckets_path = tmpdir / "3dgs_view_buckets.json"
        manifest_path.write_text(json.dumps(tile_manifest, indent=2, sort_keys=True), encoding="utf-8")
        view_buckets_path.write_text(json.dumps(view_buckets, indent=2, sort_keys=True), encoding="utf-8")
        run_command(["aws", "s3", "cp", str(manifest_path), f"{output_prefix}/3dgs_tile_manifest.json"])
        run_command(["aws", "s3", "cp", str(view_buckets_path), f"{output_prefix}/3dgs_view_buckets.json"])


def supports_bilateral_processing(model_variant: str) -> bool:
    return model_variant not in UNSUPPORTED_BILATERAL_VARIANTS


def select_tile_ids(
    manifest: dict,
    *,
    explicit_tile_ids: Sequence[str] | None = None,
    max_tiles: int | None = None,
) -> list[str]:
    tile_ids = [str(tile["tile_id"]) for tile in manifest.get("tiles", [])]
    if explicit_tile_ids:
        requested = [tile_id.strip() for tile_id in explicit_tile_ids if tile_id.strip()]
        missing = [tile_id for tile_id in requested if tile_id not in tile_ids]
        if missing:
            raise ValueError(f"Unknown tile ids requested: {', '.join(missing)}")
        tile_ids = requested
    if max_tiles is not None and max_tiles > 0:
        tile_ids = tile_ids[:max_tiles]
    return tile_ids


def ordered_unique(values: Iterable[object]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = str(raw_value).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def tile_selected_image_names(tile_entry: dict) -> list[str]:
    return ordered_unique(
        [
            *tile_entry.get("selected_image_names", []),
            *tile_entry.get("image_names", []),
            *tile_entry.get("camera_ids", []),
            *tile_entry.get("assigned_camera_ids", []),
            *tile_entry.get("base_camera_ids", []),
            *tile_entry.get("border_camera_ids", []),
            *tile_entry.get("context_camera_ids", []),
        ]
    )


def tile_role_count(tile_entry: dict, role_name: str) -> int:
    selected_by_role = tile_entry.get("selected_cameras_by_role") or {}
    if isinstance(selected_by_role, dict):
        if role_name in selected_by_role or f"{role_name}_camera_ids" in selected_by_role:
            values = selected_by_role.get(role_name) or selected_by_role.get(f"{role_name}_camera_ids") or []
            return len(ordered_unique(values))
    view_bucket_counts = tile_entry.get("view_bucket_counts") or {}
    if isinstance(view_bucket_counts, dict):
        return int(view_bucket_counts.get(role_name, 0) or view_bucket_counts.get(f"{role_name}_camera_ids", 0) or 0)
    return 0


def tile_prior_retained_gaussians(tile_entry: dict) -> int | None:
    for key in ("prior_retained_gaussians", "retained_gaussians", "previous_retained_gaussians"):
        value = tile_entry.get(key)
        if value in (None, ""):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def tile_prior_duration_hours(tile_entry: dict) -> float | None:
    for key in ("prior_duration_hours", "duration_hours", "wall_time_hours"):
        value = tile_entry.get(key)
        if value in (None, ""):
            continue
        try:
            duration = float(value)
        except (TypeError, ValueError):
            continue
        if duration > 0:
            return duration
    return None


def tile_prior_fanout_duration_hours(tile_entry: dict, budget_class: str | None = None) -> float | None:
    required_budget_class = normalized_budget_class(tile_entry.get("prior_fanout_budget_class"))
    if required_budget_class is not None and budget_class is not None and required_budget_class != budget_class:
        return None
    for key in (
        "prior_fanout_duration_hours",
        "fanout_duration_hours",
        "observed_fanout_duration_hours",
        "observed_leaf_duration_hours",
    ):
        value = tile_entry.get(key)
        if value in (None, ""):
            continue
        try:
            duration = float(value)
        except (TypeError, ValueError):
            continue
        if duration > 0:
            return duration
    for key in (
        "prior_fanout_billable_time_seconds",
        "fanout_billable_time_seconds",
        "observed_fanout_billable_time_seconds",
        "observed_leaf_billable_time_seconds",
    ):
        value = tile_entry.get(key)
        if value in (None, ""):
            continue
        try:
            seconds = float(value)
        except (TypeError, ValueError):
            continue
        if seconds > 0:
            return seconds / 3600.0
    by_budget = tile_entry.get("prior_fanout_duration_hours_by_budget") or {}
    if budget_class and isinstance(by_budget, dict):
        value = by_budget.get(budget_class)
        try:
            duration = float(value)
        except (TypeError, ValueError):
            duration = 0.0
        if duration > 0:
            return duration
    return None


def normalize_prior_tile_stats(payload: dict) -> dict[str, dict]:
    raw_tiles = payload.get("tiles", payload)
    if isinstance(raw_tiles, list):
        iterable = raw_tiles
    elif isinstance(raw_tiles, dict):
        iterable = [
            {"tile_id": tile_id, **tile_payload}
            for tile_id, tile_payload in raw_tiles.items()
            if isinstance(tile_payload, dict)
        ]
    else:
        iterable = []

    stats: dict[str, dict] = {}
    for raw_tile in iterable:
        if not isinstance(raw_tile, dict):
            continue
        tile_id = str(raw_tile.get("tile_id", "")).strip()
        if not tile_id:
            continue
        tile_stats: dict[str, object] = {}
        for source_key, target_key in (
            ("retained_gaussians", "prior_retained_gaussians"),
            ("prior_retained_gaussians", "prior_retained_gaussians"),
            ("selected_image_count", "prior_selected_image_count"),
            ("duration_hours", "prior_duration_hours"),
            ("wall_time_hours", "prior_duration_hours"),
            ("billable_time_seconds", "prior_billable_time_seconds"),
            ("fanout_duration_hours", "prior_fanout_duration_hours"),
            ("observed_fanout_duration_hours", "prior_fanout_duration_hours"),
            ("observed_leaf_duration_hours", "prior_fanout_duration_hours"),
            ("fanout_billable_time_seconds", "prior_fanout_billable_time_seconds"),
            ("observed_fanout_billable_time_seconds", "prior_fanout_billable_time_seconds"),
            ("observed_leaf_billable_time_seconds", "prior_fanout_billable_time_seconds"),
            ("fanout_budget_class", "prior_fanout_budget_class"),
            ("observed_fanout_budget_class", "prior_fanout_budget_class"),
            ("fanout_duration_hours_by_budget", "prior_fanout_duration_hours_by_budget"),
            ("observed_fanout_duration_hours_by_budget", "prior_fanout_duration_hours_by_budget"),
            ("budget_class_fanout_duration_hours", "prior_fanout_duration_hours_by_budget"),
            ("force_budget_class", "prior_force_budget_class"),
            ("forced_budget_class", "prior_force_budget_class"),
            ("min_budget_class", "prior_min_budget_class"),
            ("force_max_iterations", "prior_max_iterations"),
            ("force_max_selected_images", "prior_max_selected_images"),
            ("budget_override_reason", "prior_budget_override_reason"),
        ):
            value = raw_tile.get(source_key)
            if value not in (None, ""):
                tile_stats[target_key] = value
        if tile_stats:
            stats[tile_id] = tile_stats
    return stats


def apply_prior_tile_stats(tile_manifest: dict, prior_stats: dict[str, dict]) -> dict:
    if not prior_stats:
        return tile_manifest
    resolved_manifest = dict(tile_manifest)
    resolved_tiles: list[dict] = []
    for tile in tile_manifest.get("tiles", []):
        tile_entry = dict(tile)
        stats = prior_stats.get(str(tile_entry.get("tile_id")))
        if stats:
            for key, value in stats.items():
                tile_entry.setdefault(key, value)
        resolved_tiles.append(tile_entry)
    resolved_manifest["tiles"] = resolved_tiles
    return resolved_manifest


def normalize_tile_cache_manifest(payload: dict) -> dict[str, dict]:
    raw_entries = payload.get("tiles") or payload.get("cache_entries") or payload.get("tile_cache") or payload
    if isinstance(raw_entries, list):
        iterable = raw_entries
    elif isinstance(raw_entries, dict):
        iterable = [
            {"tile_id": tile_id, **tile_payload}
            for tile_id, tile_payload in raw_entries.items()
            if isinstance(tile_payload, dict)
        ]
    else:
        iterable = []

    cache: dict[str, dict] = {}
    for raw_entry in iterable:
        if not isinstance(raw_entry, dict):
            continue
        tile_id = str(raw_entry.get("tile_id", "")).strip()
        if not tile_id:
            continue
        cache[tile_id] = dict(raw_entry)
    return cache


def normalize_context_density_manifest(payload: dict) -> dict[str, dict]:
    raw_entries = (
        payload.get("context_density_tiles")
        or payload.get("context_density_entries")
        or payload.get("dense_context_tiles")
        or payload.get("tiles")
        or payload
    )
    if isinstance(raw_entries, list):
        iterable = raw_entries
    elif isinstance(raw_entries, dict):
        iterable = [
            {"tile_id": tile_id, **tile_payload}
            for tile_id, tile_payload in raw_entries.items()
            if isinstance(tile_payload, dict)
        ]
    else:
        iterable = []

    manifest: dict[str, dict] = {}
    for raw_entry in iterable:
        if not isinstance(raw_entry, dict):
            continue
        tile_id = str(raw_entry.get("tile_id", "")).strip()
        if not tile_id:
            continue
        manifest[tile_id] = dict(raw_entry)
    return manifest


def tile_cache_artifact_uri(cache_entry: dict) -> str:
    return str(
        cache_entry.get("artifact_s3_uri")
        or cache_entry.get("model_artifacts_s3_uri")
        or cache_entry.get("source_artifact_uri")
        or cache_entry.get("cache_artifact_s3_uri")
        or ""
    ).strip()


def tile_cache_status(cache_entry: dict) -> str:
    return str(
        cache_entry.get("quality_gate_status")
        or cache_entry.get("quality_status")
        or cache_entry.get("preflight_status")
        or cache_entry.get("promotion_readiness")
        or cache_entry.get("status")
        or ""
    ).strip().lower()


def tile_cache_ownership_rejection_reasons(cache_entry: dict) -> list[str]:
    reasons: list[str] = []
    blocked_statuses = {
        "blocked",
        "fail",
        "failed",
        "merge_ownership_blocked",
        "ownership_blocked",
        "preflight_blocked",
        "quality_blocked",
    }
    pass_statuses = {"passed", "pass", "ok", "promoted", "accepted", "quality_passed", "ownership_passed"}

    status = str(
        cache_entry.get("ownership_gate_status")
        or cache_entry.get("merge_ownership_status")
        or ""
    ).strip().lower()
    if status in blocked_statuses:
        reasons.append("ownership_status_blocked")
    elif status and status not in pass_statuses:
        reasons.append("ownership_status_not_passing")

    if cache_entry.get("merge_ownership_blocked") is True:
        reasons.append("merge_ownership_blocked")

    ratio = cache_entry.get("source_tile_core_ratio")
    if ratio is None:
        ownership_distribution = cache_entry.get("ownership_distribution")
        if isinstance(ownership_distribution, dict):
            for key in ("source_tile_core_ratio", "source_tile_core_retention_ratio", "tile_core_ratio"):
                if ownership_distribution.get(key) is not None:
                    ratio = ownership_distribution.get(key)
                    break
    min_ratio = None
    for key in ("min_source_tile_core_ratio", "v18_reference_merge_retention_ratio", "reference_merge_retention_ratio"):
        if cache_entry.get(key) is not None:
            min_ratio = cache_entry.get(key)
            break
    try:
        ratio_value = None if ratio is None else float(ratio)
        min_ratio_value = None if min_ratio is None else float(min_ratio)
    except (TypeError, ValueError):
        reasons.append("ownership_distribution_unparseable")
    else:
        if ratio_value is not None and min_ratio_value is not None and ratio_value < min_ratio_value:
            reasons.append("ownership_distribution_below_minimum")

    return sorted(set(reasons))


def resolve_tile_cache_hit(tile_budget: "TileBudgetPlan", cache_entry: dict | None) -> tuple[dict | None, list[str]]:
    if not cache_entry:
        return None, ["no_cache_entry"]
    reasons: list[str] = []
    artifact_uri = tile_cache_artifact_uri(cache_entry)
    if not artifact_uri:
        reasons.append("missing_artifact_s3_uri")
    cached_hash = str(cache_entry.get("input_hash", "")).strip()
    if cached_hash != tile_budget.input_hash:
        reasons.append("input_hash_mismatch")
    status = tile_cache_status(cache_entry)
    if status not in PASSING_GATE_STATUSES:
        reasons.append("quality_status_not_passing")
    reasons.extend(tile_cache_ownership_rejection_reasons(cache_entry))
    if reasons:
        return None, reasons
    return {**cache_entry, "artifact_s3_uri": artifact_uri, "quality_gate_status": status}, []


def first_present_value(payload: dict, keys: Sequence[str]) -> object | None:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return None


def context_density_status(context_entry: dict) -> str:
    return str(
        context_entry.get("context_density_status")
        or context_entry.get("quality_gate_status")
        or context_entry.get("quality_status")
        or context_entry.get("promotion_readiness")
        or context_entry.get("status")
        or ""
    ).strip().lower()


def context_density_has_lineage(context_entry: dict) -> bool:
    if context_entry.get("context_preserve_enabled") is True:
        return True
    if context_entry.get("preserve_context_gaussians") is True:
        return True
    if context_entry.get("teacher_context_preserved") is True:
        return True
    lineage = context_entry.get("context_density_lineage") or context_entry.get("lineage")
    return bool(lineage)


def resolve_context_density_reuse(
    tile_budget: "TileBudgetPlan",
    context_entry: dict | None,
) -> tuple[dict | None, list[str]]:
    del tile_budget
    if not context_entry:
        return None, ["no_context_density_entry"]
    reasons: list[str] = []
    artifact_uri = tile_cache_artifact_uri(context_entry)
    if not artifact_uri:
        reasons.append("missing_context_density_artifact_s3_uri")

    status = context_density_status(context_entry)
    if status not in PASSING_GATE_STATUSES:
        reasons.append("context_density_status_not_passing")

    if not context_density_has_lineage(context_entry):
        reasons.append("missing_context_density_lineage")

    retained = first_present_value(
        context_entry,
        ("retained_gaussians", "context_retained_gaussians", "dense_retained_gaussians"),
    )
    reference = first_present_value(
        context_entry,
        ("reference_retained_gaussians", "v18_retained_gaussians", "target_retained_gaussians"),
    )
    min_ratio = first_present_value(
        context_entry,
        ("min_retained_ratio_vs_reference", "min_context_density_ratio", "min_density_ratio"),
    )
    try:
        retained_value = None if retained is None else float(retained)
        reference_value = None if reference is None else float(reference)
        min_ratio_value = 0.95 if min_ratio is None else float(min_ratio)
    except (TypeError, ValueError):
        reasons.append("context_density_ratio_unparseable")
    else:
        if retained_value is None or reference_value is None or reference_value <= 0:
            reasons.append("missing_context_density_reference")
        elif retained_value / reference_value < min_ratio_value:
            reasons.append("context_density_ratio_below_minimum")

    if reasons:
        return None, reasons
    return {
        **context_entry,
        "artifact_s3_uri": artifact_uri,
        "quality_gate_status": status,
        "context_density_ratio": retained_value / reference_value,
    }, []


@dataclass(frozen=True)
class TileBudgetPlan:
    tile_id: str
    budget_class: str
    selected_image_count: int
    max_iterations: int
    max_selected_images: int
    input_hash: str
    reasons: list[str]
    instance_type: str | None = None
    spot_enabled: bool = False
    checkpoint_uri: str | None = None
    source_artifact_uri: str | None = None
    prior_duration_hours: float | None = None
    prior_fanout_duration_hours: float | None = None
    quality_gate_status: str = "planned"

    def to_dict(self) -> dict:
        return asdict(self)


def build_tile_input_hash(
    *,
    tile_entry: dict,
    budget_class: str,
    max_iterations: int,
    max_selected_images: int,
    input_colmap_s3_uri: str = "",
    image_uri: str = "",
    scaffold_artifact_s3_uri: str = "",
    training_env_fingerprint: dict[str, str] | None = None,
) -> str:
    ignored_tile_entry_fields = {
        "source_artifact_uri",
        "cache_artifact_s3_uri",
        "model_artifact_s3_uri",
        "prior_retained_gaussians",
        "prior_selected_image_count",
        "prior_duration_hours",
        "prior_billable_time_seconds",
        "prior_fanout_duration_hours",
        "prior_fanout_billable_time_seconds",
        "prior_fanout_budget_class",
        "prior_fanout_duration_hours_by_budget",
        "fanout_duration_hours",
        "observed_fanout_duration_hours",
        "observed_leaf_duration_hours",
        "fanout_billable_time_seconds",
        "observed_fanout_billable_time_seconds",
        "observed_leaf_billable_time_seconds",
        "fanout_budget_class",
        "observed_fanout_budget_class",
        "fanout_duration_hours_by_budget",
        "observed_fanout_duration_hours_by_budget",
        "budget_class_fanout_duration_hours",
        "prior_force_budget_class",
        "prior_min_budget_class",
        "prior_max_iterations",
        "prior_max_selected_images",
        "prior_budget_override_reason",
    }
    stable_tile_entry = {
        key: value
        for key, value in tile_entry.items()
        if key not in ignored_tile_entry_fields
    }
    payload = {
        "tile_id": tile_entry.get("tile_id"),
        "selected_image_names": tile_selected_image_names(tile_entry),
        "tile_entry": stable_tile_entry,
        "budget_class": budget_class,
        "max_iterations": max_iterations,
        "max_selected_images": max_selected_images,
        "input_colmap_s3_uri": normalize_s3_prefix(input_colmap_s3_uri) if input_colmap_s3_uri else "",
        "image_uri": image_uri,
        "scaffold_artifact_s3_uri": normalize_s3_prefix(scaffold_artifact_s3_uri) if scaffold_artifact_s3_uri else "",
        "training_env_fingerprint": training_env_fingerprint or {},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def apply_md1_production_tile_defaults(env: Dict[str, str]) -> None:
    for key, value in MD1_PRODUCTION_TILE_ENV_DEFAULTS.items():
        env.setdefault(key, value)


def tile_input_hash_env_fingerprint(env: Dict[str, str]) -> dict[str, str]:
    return {
        key: str(env[key])
        for key in TILE_INPUT_HASH_ENV_KEYS
        if key in env and str(env[key]).strip()
    }


def budget_image_cap(*, default_cap: int, max_images_per_tile: int) -> int:
    if max_images_per_tile > 0:
        return min(default_cap, max_images_per_tile)
    return default_cap


def normalized_budget_class(value: object) -> str | None:
    budget_class = str(value or "").strip().lower()
    return budget_class if budget_class in BUDGET_CLASS_RANK else None


def adaptive_budget_defaults(
    budget_class: str,
    *,
    tile_max_iterations: int,
    max_images_per_tile: int,
) -> tuple[int, int]:
    if budget_class == "skip":
        return 0, 0
    if budget_class == "tiny":
        return (
            min(tile_max_iterations, 3000),
            budget_image_cap(default_cap=96, max_images_per_tile=max_images_per_tile),
        )
    if budget_class == "standard":
        return (
            min(tile_max_iterations, 8000),
            budget_image_cap(default_cap=128, max_images_per_tile=max_images_per_tile),
        )
    if budget_class == "hard":
        return (
            min(tile_max_iterations, 12000),
            budget_image_cap(default_cap=188, max_images_per_tile=max_images_per_tile),
        )
    raise ValueError(f"Unsupported budget class: {budget_class}")


def build_tile_budget_plan(
    tile_entry: dict,
    *,
    mode: str,
    tile_max_iterations: int,
    max_images_per_tile: int = 0,
    input_colmap_s3_uri: str = "",
    image_uri: str = "",
    scaffold_artifact_s3_uri: str = "",
    training_env_fingerprint: dict[str, str] | None = None,
    instance_type: str | None = None,
    spot_enabled: bool = False,
    checkpoint_uri: str | None = None,
) -> TileBudgetPlan:
    tile_id = str(tile_entry.get("tile_id", "")).strip()
    selected_count = int(tile_entry.get("selected_image_count") or len(tile_selected_image_names(tile_entry)))
    prior_retained = tile_prior_retained_gaussians(tile_entry)
    prior_duration_hours = tile_prior_duration_hours(tile_entry)
    horizon_count = tile_role_count(tile_entry, "horizon")
    boundary_count = tile_role_count(tile_entry, "boundary")
    near_detail_count = tile_role_count(tile_entry, "near_detail")
    source_artifact_uri = str(
        tile_entry.get("source_artifact_uri")
        or tile_entry.get("cache_artifact_s3_uri")
        or tile_entry.get("model_artifact_s3_uri")
        or ""
    ).strip() or None

    reasons: list[str] = []
    if mode != "adaptive":
        budget_class = "hard"
        max_iterations = tile_max_iterations
        max_selected_images = max_images_per_tile if max_images_per_tile > 0 else 0
        reasons.append("fixed_budget")
    elif source_artifact_uri:
        budget_class = "skip"
        max_iterations = 0
        max_selected_images = 0
        reasons.append("source_artifact_reuse")
    elif selected_count <= 0:
        budget_class = "skip"
        max_iterations = 0
        max_selected_images = 0
        reasons.append("zero_selected_images")
    elif prior_retained is not None and prior_retained <= 100:
        budget_class = "tiny"
        max_iterations, max_selected_images = adaptive_budget_defaults(
            budget_class,
            tile_max_iterations=tile_max_iterations,
            max_images_per_tile=max_images_per_tile,
        )
        reasons.append("low_prior_retained_gaussians")
    elif selected_count <= 24:
        budget_class = "tiny"
        max_iterations, max_selected_images = adaptive_budget_defaults(
            budget_class,
            tile_max_iterations=tile_max_iterations,
            max_images_per_tile=max_images_per_tile,
        )
        reasons.append("low_selected_image_count")
    elif horizon_count >= 12:
        budget_class = "hard"
        max_iterations, max_selected_images = adaptive_budget_defaults(
            budget_class,
            tile_max_iterations=tile_max_iterations,
            max_images_per_tile=max_images_per_tile,
        )
        reasons.append("horizon_support")
    elif boundary_count >= 48 or near_detail_count >= 48:
        budget_class = "hard"
        max_iterations, max_selected_images = adaptive_budget_defaults(
            budget_class,
            tile_max_iterations=tile_max_iterations,
            max_images_per_tile=max_images_per_tile,
        )
        reasons.append("dense_detail_or_boundary_support")
    else:
        budget_class = "standard"
        max_iterations, max_selected_images = adaptive_budget_defaults(
            budget_class,
            tile_max_iterations=tile_max_iterations,
            max_images_per_tile=max_images_per_tile,
        )
        reasons.append("standard_visibility")

    if mode == "adaptive" and budget_class not in {"skip"}:
        force_budget_class = normalized_budget_class(tile_entry.get("prior_force_budget_class"))
        min_budget_class = normalized_budget_class(tile_entry.get("prior_min_budget_class"))
        if force_budget_class is not None:
            budget_class = force_budget_class
            max_iterations, max_selected_images = adaptive_budget_defaults(
                budget_class,
                tile_max_iterations=tile_max_iterations,
                max_images_per_tile=max_images_per_tile,
            )
            reasons.append(f"prior_force_budget_class_{budget_class}")
        elif (
            min_budget_class is not None
            and BUDGET_CLASS_RANK[min_budget_class] > BUDGET_CLASS_RANK.get(budget_class, -1)
        ):
            budget_class = min_budget_class
            max_iterations, max_selected_images = adaptive_budget_defaults(
                budget_class,
                tile_max_iterations=tile_max_iterations,
                max_images_per_tile=max_images_per_tile,
            )
            reasons.append(f"prior_min_budget_class_{budget_class}")

        forced_iterations = _int_or_none(tile_entry.get("prior_max_iterations"))
        if forced_iterations is not None and forced_iterations >= 0:
            max_iterations = min(tile_max_iterations, forced_iterations)
            reasons.append("prior_max_iterations")
        forced_max_images = _int_or_none(tile_entry.get("prior_max_selected_images"))
        if forced_max_images is not None and forced_max_images >= 0:
            max_selected_images = forced_max_images
            reasons.append("prior_max_selected_images")

    prior_fanout_duration_hours = tile_prior_fanout_duration_hours(tile_entry, budget_class=budget_class)

    input_hash = build_tile_input_hash(
        tile_entry=tile_entry,
        budget_class=budget_class,
        max_iterations=max_iterations,
        max_selected_images=max_selected_images,
        input_colmap_s3_uri=input_colmap_s3_uri,
        image_uri=image_uri,
        scaffold_artifact_s3_uri=scaffold_artifact_s3_uri,
        training_env_fingerprint=training_env_fingerprint,
    )
    return TileBudgetPlan(
        tile_id=tile_id,
        budget_class=budget_class,
        selected_image_count=selected_count,
        max_iterations=max_iterations,
        max_selected_images=max_selected_images,
        input_hash=input_hash,
        reasons=reasons,
        instance_type=instance_type,
        spot_enabled=spot_enabled,
        checkpoint_uri=checkpoint_uri,
        source_artifact_uri=source_artifact_uri,
        prior_duration_hours=prior_duration_hours,
        prior_fanout_duration_hours=prior_fanout_duration_hours,
    )


def estimate_training_cost(
    stages: Sequence["BenchmarkStage"],
    *,
    instance_type: str,
    max_runtime_seconds: int,
    baseline_iterations: int,
    instance_hourly_rates: dict[str, float] | None = None,
) -> dict:
    rates = instance_hourly_rates or INSTANCE_HOURLY_RATES_USD
    hourly_rate = float(rates.get(instance_type, rates[DEFAULT_INSTANCE_TYPE]))
    max_hours_per_stage = max_runtime_seconds / 3600.0
    estimated_hours = 0.0
    worst_case_hours = 0.0
    train_stage_count = 0
    stage_estimates: list[dict] = []
    for stage in stages:
        if stage.stage_type != "train":
            continue
        train_stage_count += 1
        env = stage.environment or {}
        try:
            stage_iterations = int(env.get("MAX_ITERATIONS", baseline_iterations) or baseline_iterations)
        except (TypeError, ValueError):
            stage_iterations = baseline_iterations
        fraction = 0.0 if stage_iterations <= 0 else min(1.0, max(0.05, stage_iterations / max(1, baseline_iterations)))
        stage_multiplier = 1
        if stage.training_mode == "tiled_pipeline":
            try:
                stage_multiplier = max(1, int(env.get("TILED_MAX_TILES", 1) or 1))
            except (TypeError, ValueError):
                stage_multiplier = 1
        stage_hours = max_hours_per_stage * fraction * stage_multiplier
        cost_basis = "iteration_fraction_of_runtime_cap"
        runtime_risk = None
        runtime_cap_shortfall_hours = 0.0
        prior_duration_hours = stage.prior_duration_hours
        prior_fanout_duration_hours = stage.prior_fanout_duration_hours
        if (
            prior_fanout_duration_hours is not None
            and prior_fanout_duration_hours > 0
            and stage.training_mode == "leaf_tile"
        ):
            stage_hours = prior_fanout_duration_hours
            cost_basis = "observed_fanout_leaf_duration"
        elif (
            prior_duration_hours is not None
            and prior_duration_hours > 0
            and stage.budget_class == "hard"
            and stage.training_mode == "leaf_tile"
        ):
            stage_hours = max(stage_hours, prior_duration_hours)
            cost_basis = "historical_prior_duration"
        runtime_cap_hours = max_hours_per_stage * stage_multiplier
        if stage_hours > runtime_cap_hours:
            runtime_risk = "prior_duration_exceeds_max_runtime"
            runtime_cap_shortfall_hours = stage_hours - runtime_cap_hours
        estimated_hours += stage_hours
        worst_case_hours += max_hours_per_stage * stage_multiplier
        stage_estimates.append(
            {
                "stage_name": stage.stage_name,
                "training_mode": stage.training_mode,
                "tile_id": stage.tile_id,
                "max_iterations": stage_iterations,
                "stage_multiplier": stage_multiplier,
                "estimated_billable_hours": round(stage_hours, 4),
                "estimated_usd": round(stage_hours * hourly_rate, 4),
                "budget_class": stage.budget_class,
                "prior_duration_hours": prior_duration_hours,
                "prior_fanout_duration_hours": prior_fanout_duration_hours,
                "cost_basis": cost_basis,
                "runtime_risk": runtime_risk,
                "runtime_cap_shortfall_hours": round(runtime_cap_shortfall_hours, 4),
            }
        )
    return {
        "instance_type": instance_type,
        "hourly_rate_usd": hourly_rate,
        "train_stage_count": train_stage_count,
        "estimated_billable_hours": round(estimated_hours, 4),
        "estimated_usd": round(estimated_hours * hourly_rate, 4),
        "worst_case_billable_hours": round(worst_case_hours, 4),
        "worst_case_usd": round(worst_case_hours * hourly_rate, 4),
        "baseline_iterations": baseline_iterations,
        "stage_estimates": stage_estimates,
        "pricing_source": "static_us-west-2-rates-verified-2026-04-30",
    }


def fanout_execution_batches(
    stages: Sequence["BenchmarkStage"],
    *,
    max_tile_concurrency: int,
) -> list[list["BenchmarkStage"]]:
    if max_tile_concurrency < 1:
        raise ValueError("max_tile_concurrency must be >= 1")
    batches: list[list[BenchmarkStage]] = []
    leaf_batch: list[BenchmarkStage] = []

    def flush_leaf_batch() -> None:
        nonlocal leaf_batch
        if leaf_batch:
            batches.append(leaf_batch)
            leaf_batch = []

    for stage in stages:
        if stage.stage_type != "train":
            continue
        if stage.training_mode == "leaf_tile":
            leaf_batch.append(stage)
            if len(leaf_batch) >= max_tile_concurrency:
                flush_leaf_batch()
            continue
        flush_leaf_batch()
        batches.append([stage])
    flush_leaf_batch()
    return batches


def selected_tile_count_for_submit(summary: dict) -> int:
    selected_tile_ids = summary.get("selected_tile_ids") or []
    if isinstance(selected_tile_ids, list) and selected_tile_ids:
        return len(selected_tile_ids)
    stage_tile_ids = {
        str(stage.get("tile_id"))
        for stage in summary.get("stages") or []
        if isinstance(stage, dict) and stage.get("tile_id")
    }
    return len(stage_tile_ids)


def production_rung_evidence_for(rung_gate: dict, rung_name: str) -> dict:
    evidence_by_rung = rung_gate.get("rung_evidence")
    evidence = evidence_by_rung.get(rung_name) if isinstance(evidence_by_rung, dict) else None
    if evidence is None:
        evidence = rung_gate.get(f"{rung_name}_evidence")
    return evidence if isinstance(evidence, dict) else {}


def production_rung_evidence_has_reference(evidence: dict) -> bool:
    for key in PRODUCTION_RUNG_EVIDENCE_REFERENCE_KEYS:
        value = evidence.get(key)
        if isinstance(value, str) and value.strip():
            return True
        if isinstance(value, list) and any(str(item).strip() for item in value):
            return True
    return False


def validate_submit_guardrails(args: argparse.Namespace, summary: dict) -> None:
    if not getattr(args, "submit", False):
        return
    errors: list[str] = []
    max_estimated_usd = float(getattr(args, "max_estimated_usd", 0.0) or 0.0)
    experiment_id = str(getattr(args, "experiment_id", "") or "").strip()
    v18_review_manifest_s3_uri = str(getattr(args, "v18_review_manifest_s3_uri", "") or "").strip()
    if max_estimated_usd <= 0:
        errors.append("--max-estimated-usd is required for submitted training runs")
    if not experiment_id:
        errors.append("--experiment-id is required for submitted training runs")
    if not v18_review_manifest_s3_uri:
        errors.append("--v18-review-manifest-s3-uri is required so every paid run has a V18 comparison plan")
    estimate = (summary.get("cost_estimate") or {}).get("estimated_usd")
    if estimate is not None and max_estimated_usd > 0 and float(estimate) > max_estimated_usd:
        errors.append(f"estimated cost ${float(estimate):.2f} exceeds --max-estimated-usd ${max_estimated_usd:.2f}")
    for stage_estimate in (summary.get("cost_estimate") or {}).get("stage_estimates") or []:
        runtime_risk = str(stage_estimate.get("runtime_risk") or "").strip()
        if runtime_risk:
            stage_name = str(stage_estimate.get("stage_name") or stage_estimate.get("tile_id") or "unknown")
            errors.append(
                f"{stage_name} has runtime risk {runtime_risk}; increase --training-max-runtime-seconds "
                "or reduce the stage budget before submit"
            )
    checkpoints_requested = bool(
        getattr(args, "enable_checkpoints", False) or getattr(args, "enable_spot", False)
    )
    if checkpoints_requested and not str(getattr(args, "checkpoint_s3_prefix", "") or "").strip():
        errors.append("--checkpoint-s3-prefix is required when checkpoints or Spot are enabled")
    checkpoint_resume_s3_uri = str(getattr(args, "checkpoint_resume_s3_uri", "") or "").strip()
    if checkpoint_resume_s3_uri and not checkpoints_requested:
        errors.append("--checkpoint-resume-s3-uri requires --enable-checkpoints or --enable-spot")
    if checkpoint_resume_s3_uri and not checkpoint_resume_s3_uri.startswith("s3://"):
        errors.append("--checkpoint-resume-s3-uri must be an s3:// prefix")
    selected_tile_count = selected_tile_count_for_submit(summary)
    if selected_tile_count >= 14:
        rung_gate_json = str(getattr(args, "production_rung_gate_json", "") or "").strip()
        rung_gate = summary.get("production_rung_gate") or {}
        if not rung_gate_json:
            errors.append(
                "full 14-tile submits require --production-rung-gate-json documenting "
                "R0/R1/R2/R3 acceptance before spend"
            )
        else:
            missing_or_blocked = [
                rung
                for rung in REQUIRED_PRODUCTION_RUNG_STATUS_FIELDS
                if str(rung_gate.get(rung) or "").strip().lower() not in PASSING_RUNG_STATUSES
            ]
            if missing_or_blocked:
                errors.append(
                    "--production-rung-gate-json does not pass required rungs: "
                    + ", ".join(missing_or_blocked)
                )
            missing_evidence = [
                rung
                for rung in REQUIRED_PRODUCTION_RUNG_EVIDENCE_KEYS
                if not production_rung_evidence_has_reference(production_rung_evidence_for(rung_gate, rung))
            ]
            if missing_evidence:
                errors.append(
                    "--production-rung-gate-json missing evidence for required rungs: "
                    + ", ".join(missing_evidence)
                )
            if rung_gate.get("allow_full_14tile_submit") is not True:
                errors.append("--production-rung-gate-json must set allow_full_14tile_submit=true")
            try:
                gate_max_usd = float(rung_gate.get("max_estimated_usd") or 0.0)
            except (TypeError, ValueError):
                gate_max_usd = 0.0
                errors.append("--production-rung-gate-json max_estimated_usd must be numeric")
            if gate_max_usd <= 0:
                errors.append("--production-rung-gate-json must set max_estimated_usd > 0")
            elif max_estimated_usd > gate_max_usd:
                errors.append(
                    f"--max-estimated-usd ${max_estimated_usd:.2f} exceeds "
                    f"production rung gate cap ${gate_max_usd:.2f}"
                )
    if getattr(args, "enable_spot", False):
        if not getattr(args, "spot_restart_proof_passed", False):
            errors.append("--spot-restart-proof-passed is required before submitting spot training")
        spot_max_wait_seconds = int(getattr(args, "spot_max_wait_seconds", 0) or 0)
        training_max_runtime_seconds = int(
            getattr(args, "training_max_runtime_seconds", DEFAULT_TRAINING_MAX_RUNTIME_SECONDS)
            or DEFAULT_TRAINING_MAX_RUNTIME_SECONDS
        )
        if spot_max_wait_seconds <= 0:
            errors.append("--spot-max-wait-seconds is required for submitted Spot training")
        elif spot_max_wait_seconds < training_max_runtime_seconds:
            errors.append("--spot-max-wait-seconds must be >= --training-max-runtime-seconds")
        elif spot_max_wait_seconds - training_max_runtime_seconds > MAX_SPOT_EXTRA_WAIT_SECONDS:
            errors.append(
                "--spot-max-wait-seconds may exceed --training-max-runtime-seconds by at most "
                f"{MAX_SPOT_EXTRA_WAIT_SECONDS}s for bounded Spot capacity waits"
            )
    if getattr(args, "reuse_tile_cache", False):
        stages = summary.get("stages") or []
        scaffold_train_planned = any(
            stage.get("stage_type") == "train" and stage.get("training_mode") == "global_scaffold"
            for stage in stages
        )
        leaf_train_planned = any(
            stage.get("stage_type") == "train" and stage.get("training_mode") == "leaf_tile"
            for stage in stages
        )
        if scaffold_train_planned and not leaf_train_planned:
            errors.append("all selected leaf tiles are cache hits, but scaffold training is still planned; pass --skip-scaffold")
    if str(getattr(args, "orchestration_mode", "") or "") == "fanout":
        stages = summary.get("stages") or []
        leaf_train_planned = any(
            stage.get("stage_type") == "train" and stage.get("training_mode") == "leaf_tile"
            for stage in stages
        )
        if leaf_train_planned and (
            not bool(getattr(args, "skip_merge", False)) or not bool(getattr(args, "skip_review", False))
        ):
            errors.append(
                "submitted fanout leaf-tile runs must use --skip-merge and --skip-review; "
                "run post_leaf_preflight_gates before merge/review spend"
            )
    if errors:
        raise RuntimeError("; ".join(errors))


def validate_manifest_override_args(*, tile_manifest_json: str, view_bucket_json: str) -> None:
    if bool(tile_manifest_json) != bool(view_bucket_json):
        raise RuntimeError("--tile-manifest-json and --view-bucket-json must be provided together")


def sanitize_sagemaker_job_name(raw_name: str, *, max_length: int = 63) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9-]+", "-", raw_name).strip("-")
    sanitized = re.sub(r"-{2,}", "-", sanitized)
    if not sanitized:
        sanitized = "spaceport-3dgs-job"
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip("-")
    return sanitized or "spaceport-3dgs-job"


def resolve_proof_profile(
    requested_profile: str | None,
    *,
    orchestration_mode: str,
    include_review: bool,
) -> str:
    if requested_profile:
        return requested_profile
    if orchestration_mode == "single_job" and include_review:
        return PROOF_PROFILE_QUALITY_GATE_LOW_MEMORY
    return PROOF_PROFILE_NONE


def apply_proof_profile(
    env: Dict[str, str],
    *,
    proof_profile: str,
    max_iterations: int,
    training_mode: str,
    include_review: bool,
    tile_count: int,
) -> None:
    if proof_profile != PROOF_PROFILE_QUALITY_GATE_LOW_MEMORY:
        return
    env.setdefault("TRAINING_PROOF_PROFILE", proof_profile)
    env.setdefault("TRAINING_VIS_MODE", "viewer")
    env.setdefault("TRAINING_CACHE_IMAGES", "disk")
    env.setdefault("TRAINING_CACHE_IMAGES_TYPE", "uint8")
    env.setdefault("TRAINING_DATALOADER_NUM_WORKERS", "0")
    stop_split_at = QUALITY_GATE_LOW_MEMORY_STOP_SPLIT_AT
    if training_mode == "tiled_pipeline" and include_review and tile_count >= 3:
        env.setdefault("TRAINING_MAX_GAUSS_RATIO", QUALITY_GATE_MULTI_TILE_MAX_GAUSS_RATIO)
        stop_split_at = QUALITY_GATE_MULTI_TILE_STOP_SPLIT_AT
    env.setdefault("TRAINING_STOP_SPLIT_AT", str(min(max_iterations, stop_split_at)))
    apply_training_eval_suppression(env, max_iterations=max_iterations)


def apply_training_eval_suppression(env: Dict[str, str], *, max_iterations: int) -> None:
    suppressed_step = str(max_iterations + 1)
    env.setdefault("TRAINING_STEPS_PER_EVAL_IMAGE", suppressed_step)
    env.setdefault("TRAINING_STEPS_PER_EVAL_ALL_IMAGES", suppressed_step)
    env.setdefault("TRAINING_STEPS_PER_SAVE", suppressed_step)


@dataclass
class BenchmarkStage:
    stage_name: str
    stage_type: str
    training_mode: str
    output_s3_uri: str
    job_name: str | None = None
    tile_id: str | None = None
    depends_on: list[str] | None = None
    environment: Dict[str, str] | None = None
    budget_class: str | None = None
    selected_image_count: int | None = None
    max_iterations: int | None = None
    max_selected_images: int | None = None
    input_hash: str | None = None
    source_artifact_uri: str | None = None
    checkpoint_uri: str | None = None
    spot_enabled: bool = False
    prior_duration_hours: float | None = None
    prior_fanout_duration_hours: float | None = None
    quality_gate_status: str | None = None
    cache_status: str | None = None
    cache_rejection_reasons: list[str] | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["depends_on"] = self.depends_on or []
        payload["environment"] = self.environment or {}
        payload["cache_rejection_reasons"] = self.cache_rejection_reasons or []
        return payload


def training_stage_requires_tile_selection(stage: BenchmarkStage) -> bool:
    return stage.stage_type == "train" and stage.training_mode in TILE_SELECTION_TRAINING_MODES


def attach_tile_selection_channel_to_stages(stages: Sequence[BenchmarkStage]) -> None:
    """Use a small mounted manifest channel for tiled stages so planning and training match."""
    for stage in stages:
        if not training_stage_requires_tile_selection(stage):
            continue
        environment = dict(stage.environment or {})
        environment["TILE_MANIFEST_PATH"] = f"{TILE_SELECTION_CHANNEL_DIR}/3dgs_tile_manifest.json"
        environment["VIEW_BUCKET_MANIFEST_PATH"] = f"{TILE_SELECTION_CHANNEL_DIR}/3dgs_view_buckets.json"
        stage.environment = environment


def safe_log_stem(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    sanitized = re.sub(r"-{2,}", "-", sanitized)
    return sanitized or "3dgs-leaf-gate"


def leaf_artifact_uri_for_stage(stage: BenchmarkStage) -> str:
    if not stage.job_name:
        return ""
    return f"{normalize_s3_prefix(stage.output_s3_uri)}/{stage.job_name}/output/model.tar.gz"


def build_post_leaf_preflight_gates(
    stages: Sequence[BenchmarkStage],
    *,
    reference_splat_counts: Dict[str, int],
    max_reference_splat_ratio: float,
    experiment_id: str,
    gate_json_path: str,
) -> list[dict]:
    if not reference_splat_counts:
        return []
    if max_reference_splat_ratio <= 0:
        raise RuntimeError("--leaf-max-reference-splat-ratio must be > 0 with --leaf-reference-splat-count")

    gates: list[dict] = []
    for stage in stages:
        if stage.stage_type != "train" or stage.training_mode != "leaf_tile" or not stage.tile_id:
            continue
        reference_count = reference_splat_counts.get(stage.tile_id)
        if reference_count is None:
            continue
        artifact_uri = leaf_artifact_uri_for_stage(stage)
        if not artifact_uri:
            continue
        hard_max = int(reference_count * max_reference_splat_ratio)
        log_stem = safe_log_stem(f"{experiment_id or stage.job_name or '3dgs'}-{stage.tile_id}")
        preflight_json = f"logs/{log_stem}-leaf-preflight.json"
        gate_output_json = f"logs/{log_stem}-leaf-gate.json"
        preflight_command = [
            "python3",
            "scripts/3dgs/preflight_leaf_model_artifact.py",
            "--artifact-uri",
            artifact_uri,
            "--tile-id",
            stage.tile_id,
            "--job-name",
            stage.job_name or "",
            "--output-dir",
            f"logs/{log_stem}-leaf-preflight",
            "--summary-json-output",
            preflight_json,
            "--reference-splat-count",
            str(reference_count),
            "--max-reference-splat-ratio",
            str(max_reference_splat_ratio),
        ]
        enforce_command = [
            "python3",
            "scripts/3dgs/enforce_leaf_preflight_gate.py",
            "--preflight-json",
            preflight_json,
            "--gate-json",
            gate_json_path or "<benchmark-summary-json>",
            "--expected-tile-id",
            stage.tile_id,
            "--expected-selected-image-count",
            str(stage.selected_image_count or 0),
            "--require-filtered-scaffold",
            "--summary-json-output",
            gate_output_json,
        ]
        gates.append(
            {
                "tile_id": stage.tile_id,
                "stage_name": stage.stage_name,
                "job_name": stage.job_name,
                "artifact_uri": artifact_uri,
                "reference_splat_count": reference_count,
                "max_reference_splat_ratio": max_reference_splat_ratio,
                "hard_max_splat_count": hard_max,
                "expected_selected_image_count": stage.selected_image_count,
                "required_leaf_preflight_gate": {
                    "pass_decision": "leaf_preflight_passed_cache_candidate",
                    "reference_splat_count": reference_count,
                    "max_reference_splat_ratio": max_reference_splat_ratio,
                    "hard_max_splat_count": hard_max,
                    "require_filtered_scaffold": True,
                    "expected_selected_image_count": stage.selected_image_count,
                },
                "preflight_summary_json": preflight_json,
                "gate_summary_json": gate_output_json,
                "preflight_command": preflight_command,
                "enforce_gate_command": enforce_command,
                "merge_review_allowed_only_if": "enforce_gate_command exits 0",
            }
        )
    return gates


def resolve_stage_scaffold_artifact_s3_uri(
    stage: BenchmarkStage,
    *,
    explicit_scaffold_artifact_s3_uri: str = "",
    completed_stage_outputs: Dict[str, dict] | None = None,
) -> str:
    """Resolve the scaffold artifact that must be mounted for a training stage."""
    if stage.training_mode == "tiled_pipeline":
        return explicit_scaffold_artifact_s3_uri.strip()
    if stage.training_mode != "leaf_tile":
        return ""
    explicit_uri = explicit_scaffold_artifact_s3_uri.strip()
    if explicit_uri:
        return explicit_uri

    completed = completed_stage_outputs or {}
    for dependency in stage.depends_on or []:
        scaffold_uri = str(completed.get(dependency, {}).get("model_artifacts_s3_uri", "") or "").strip()
        if scaffold_uri:
            return scaffold_uri
    return ""


@dataclass
class ExecutionContext:
    stack_name: str | None
    outputs: Dict[str, str]
    role_arn: str
    image_uri: str
    output_root_s3_uri: str


def build_training_environment(
    *,
    training_mode: str,
    tile_manifest_name: str,
    view_bucket_manifest_name: str,
    tile_id: str | None,
    max_iterations: int,
    extra_env: Dict[str, str],
    training_timeout_seconds: int | None = None,
    scaffold_max_iterations: int | None = None,
    max_tiles: int | None = None,
    selected_tile_ids: Sequence[str] | None = None,
    include_scaffold: bool = True,
    include_merge: bool = True,
    include_review: bool = False,
    downscale_factor: int = 1,
    proof_profile: str = PROOF_PROFILE_NONE,
) -> Dict[str, str]:
    env = {
        "AWS_DEFAULT_REGION": "us-west-2",
        "PYTHONUNBUFFERED": "1",
        "SAGEMAKER_PROGRAM": "train.py",
        "TORCH_CUDA_ARCH_LIST": "8.0 8.6",
        "CUDA_HOME": "/usr/local/cuda",
        "LD_LIBRARY_PATH": "/usr/local/cuda/lib64:/usr/local/cuda/lib",
        "LIBRARY_PATH": "/usr/local/cuda/lib64:/usr/local/cuda/lib",
        "MAX_ITERATIONS": str(max_iterations),
        "TRAINING_MODE": training_mode,
        "TILE_MANIFEST_PATH": tile_manifest_name,
        "VIEW_BUCKET_MANIFEST_PATH": view_bucket_manifest_name,
        "MODEL_VARIANT": "splatfacto-w-light",
        "BILATERAL_PROCESSING": "false",
        "ENABLE_BG_MODEL": "true",
        "ENABLE_ALPHA_LOSS": "true",
        "ENABLE_ROBUST_MASK": "true",
        "OUTPUT_FORMAT": "ply",
        "SOGS_COMPATIBLE": "true",
        "COMMERCIAL_LICENSE": "true",
        "FRAMEWORK": "nerfstudio",
        "METHODOLOGY": "spaceport_splatfacto_w_light_skybox",
    }
    if training_timeout_seconds is not None and training_timeout_seconds > 0:
        env["TRAINING_TIMEOUT_SECONDS"] = str(training_timeout_seconds)
    if max_iterations <= 50:
        env["TRAINING_VIS_MODE"] = "viewer"
        env["TRAINING_CACHE_IMAGES"] = "disk"
        env["TRAINING_CACHE_IMAGES_TYPE"] = "uint8"
        env["TRAINING_DATALOADER_NUM_WORKERS"] = "0"
    if training_mode == "global_scaffold":
        env["GLOBAL_SCAFFOLD_MAX_ITERATIONS"] = str(max_iterations)
    if downscale_factor > 1:
        env["TRAINING_DOWNSCALE_FACTOR"] = str(downscale_factor)
    if training_mode == "tiled_pipeline":
        if scaffold_max_iterations is not None and scaffold_max_iterations > 0:
            env["GLOBAL_SCAFFOLD_MAX_ITERATIONS"] = str(scaffold_max_iterations)
        if max_tiles is not None and max_tiles > 0:
            env["TILED_MAX_TILES"] = str(max_tiles)
        if selected_tile_ids:
            env["TILED_TILE_IDS"] = ",".join(selected_tile_ids)
        env["TILED_INCLUDE_SCAFFOLD"] = "true" if include_scaffold else "false"
        env["TILED_INCLUDE_MERGE"] = "true" if include_merge else "false"
        apply_proof_profile(
            env,
            proof_profile=proof_profile,
            max_iterations=max_iterations,
            training_mode=training_mode,
            include_review=include_review,
            tile_count=len(selected_tile_ids or []),
        )
    if tile_id:
        env["TILE_ID"] = tile_id
    env.update(extra_env)
    model_variant = env.get("MODEL_VARIANT", "splatfacto-w-light")
    bilateral_requested = env.get("BILATERAL_PROCESSING", "false").lower() in {"1", "true", "yes", "on"}
    if bilateral_requested and not supports_bilateral_processing(model_variant):
        env["BILATERAL_PROCESSING"] = "false"
    return env


def build_benchmark_stages(
    *,
    manifest: dict,
    branch_name: str,
    output_root_s3_uri: str,
    job_prefix: str,
    include_monolithic: bool,
    include_scaffold: bool,
    include_merge: bool,
    orchestration_mode: str,
    tile_ids: Sequence[str],
    monolithic_max_iterations: int,
    scaffold_max_iterations: int,
    tile_max_iterations: int,
    training_max_runtime_seconds: int,
    extra_env: Dict[str, str],
    timestamp: int,
    downscale_factor: int,
    include_review: bool,
    proof_profile: str = PROOF_PROFILE_NONE,
    tile_budget_mode: str = "fixed",
    max_images_per_tile: int = 0,
    input_colmap_s3_uri: str = "",
    image_uri: str = "",
    scaffold_artifact_s3_uri: str = "",
    instance_type: str | None = None,
    enable_spot: bool = False,
    enable_checkpoints: bool = False,
    checkpoint_s3_prefix: str = "",
    reuse_tile_cache: bool = False,
    tile_cache_manifest: dict[str, dict] | None = None,
    enable_context_density_reuse: bool = False,
    context_density_manifest: dict[str, dict] | None = None,
) -> list[BenchmarkStage]:
    output_root = normalize_s3_prefix(output_root_s3_uri)
    tile_manifest_name = "3dgs_tile_manifest.json"
    view_bucket_manifest_name = "3dgs_view_buckets.json"
    stages: list[BenchmarkStage] = []

    if include_monolithic:
        stages.append(
            BenchmarkStage(
                stage_name="M0_monolithic",
                stage_type="train",
                training_mode="monolithic",
                job_name=sanitize_sagemaker_job_name(f"{job_prefix}-{timestamp}-m0"),
                output_s3_uri=f"{output_root}/M0_monolithic",
                environment=build_training_environment(
                    training_mode="monolithic",
                    tile_manifest_name=tile_manifest_name,
                    view_bucket_manifest_name=view_bucket_manifest_name,
                    tile_id=None,
                    max_iterations=monolithic_max_iterations,
                    extra_env=extra_env,
                    training_timeout_seconds=training_max_runtime_seconds,
                    downscale_factor=downscale_factor,
                ),
            )
        )

    if orchestration_mode == "single_job":
        stages.append(
            BenchmarkStage(
                stage_name="T2_tiled_pipeline",
                stage_type="train",
                training_mode="tiled_pipeline",
                job_name=sanitize_sagemaker_job_name(f"{job_prefix}-{timestamp}-tiled"),
                output_s3_uri=f"{output_root}/T2_tiled_pipeline",
                environment=build_training_environment(
                    training_mode="tiled_pipeline",
                    tile_manifest_name=tile_manifest_name,
                    view_bucket_manifest_name=view_bucket_manifest_name,
                    tile_id=None,
                    max_iterations=tile_max_iterations,
                    extra_env=extra_env,
                    training_timeout_seconds=training_max_runtime_seconds,
                    scaffold_max_iterations=scaffold_max_iterations,
                    max_tiles=len(tile_ids),
                    selected_tile_ids=tile_ids,
                    include_scaffold=include_scaffold,
                    include_merge=include_merge,
                    include_review=include_review,
                    downscale_factor=downscale_factor,
                    proof_profile=proof_profile,
                ),
            )
        )
        if include_review and include_merge:
            stages.append(
                BenchmarkStage(
                    stage_name="R0_quality_review",
                    stage_type="review",
                    training_mode="quality_review",
                    output_s3_uri=f"{output_root}/quality_review",
                    depends_on=["T2_tiled_pipeline"],
                    environment={
                        "QUALITY_REVIEW_MAX_IMAGES_PER_BUCKET": "4",
                        "QUALITY_REVIEW_TILE_IDS": ",".join(tile_ids),
                    },
                )
            )
        return stages

    scaffold_stage_name = "S0_scaffold"
    if include_scaffold:
        stages.append(
            BenchmarkStage(
                stage_name=scaffold_stage_name,
                stage_type="train",
                training_mode="global_scaffold",
                job_name=sanitize_sagemaker_job_name(f"{job_prefix}-{timestamp}-scaffold"),
                output_s3_uri=f"{output_root}/{scaffold_stage_name}",
                environment=build_training_environment(
                    training_mode="global_scaffold",
                    tile_manifest_name=tile_manifest_name,
                    view_bucket_manifest_name=view_bucket_manifest_name,
                    tile_id=None,
                    max_iterations=scaffold_max_iterations,
                    extra_env=extra_env,
                    training_timeout_seconds=training_max_runtime_seconds,
                    downscale_factor=downscale_factor,
                ),
            )
        )

    tiles_by_id = {str(tile.get("tile_id")): dict(tile) for tile in manifest.get("tiles", [])}
    selected_tiles = list(tile_ids)
    for tile_id in selected_tiles:
        tile_entry = tiles_by_id.get(str(tile_id), {"tile_id": tile_id})
        stage_env = dict(extra_env)
        if tile_budget_mode == "adaptive":
            apply_md1_production_tile_defaults(stage_env)
        checkpoint_uri = (
            f"{normalize_s3_prefix(checkpoint_s3_prefix)}/{sanitize_sagemaker_job_name(f'{job_prefix}-{timestamp}-{tile_id}')}"
            if checkpoint_s3_prefix and (enable_spot or enable_checkpoints)
            else None
        )
        tile_budget = build_tile_budget_plan(
            tile_entry,
            mode=tile_budget_mode,
            tile_max_iterations=tile_max_iterations,
            max_images_per_tile=max_images_per_tile,
            input_colmap_s3_uri=input_colmap_s3_uri,
            image_uri=image_uri,
            scaffold_artifact_s3_uri=scaffold_artifact_s3_uri,
            training_env_fingerprint=tile_input_hash_env_fingerprint(stage_env),
            instance_type=instance_type,
            spot_enabled=enable_spot,
            checkpoint_uri=checkpoint_uri,
        )
        stage_max_iterations = tile_max_iterations
        if tile_budget_mode == "adaptive" or max_images_per_tile > 0:
            stage_max_iterations = tile_budget.max_iterations
            stage_env.setdefault("TILE_BUDGET_CLASS", tile_budget.budget_class)
            stage_env.setdefault("TILE_INPUT_HASH", tile_budget.input_hash)
            if tile_budget.max_selected_images > 0:
                stage_env.setdefault("TRAINING_MAX_SELECTED_IMAGES", str(tile_budget.max_selected_images))
        if checkpoint_uri:
            stage_env.setdefault("TRAINING_CHECKPOINT_S3_URI", checkpoint_uri)
        if scaffold_artifact_s3_uri:
            stage_env.setdefault("GLOBAL_SCAFFOLD_SOURCE_DIR", SCAFFOLD_CHANNEL_DIR)
            stage_env.setdefault("GLOBAL_SCAFFOLD_REQUIRE_FILTERED_INIT", "true")
        cache_rejection_reasons: list[str] = []
        context_density_hit, context_density_rejection_reasons = resolve_context_density_reuse(
            tile_budget,
            (context_density_manifest or {}).get(tile_id) if enable_context_density_reuse else None,
        )
        if enable_context_density_reuse and context_density_hit is not None:
            context_stage_env = dict(stage_env)
            context_stage_env.setdefault("CONTEXT_DENSITY_REUSE", "true")
            context_stage_env.setdefault("CONTEXT_DENSITY_SOURCE_ARTIFACT_URI", str(context_density_hit.get("artifact_s3_uri")))
            stages.append(
                BenchmarkStage(
                    stage_name=f"T0_{tile_id}",
                    stage_type="context_density_tile",
                    training_mode="leaf_tile",
                    job_name=None,
                    tile_id=tile_id,
                    output_s3_uri=f"{output_root}/tiles/{tile_id}",
                    depends_on=[],
                    environment=build_training_environment(
                        training_mode="leaf_tile",
                        tile_manifest_name=tile_manifest_name,
                        view_bucket_manifest_name=view_bucket_manifest_name,
                        tile_id=tile_id,
                        max_iterations=0,
                        extra_env=context_stage_env,
                        training_timeout_seconds=training_max_runtime_seconds,
                        downscale_factor=downscale_factor,
                    ),
                    budget_class=tile_budget.budget_class if tile_budget_mode == "adaptive" else None,
                    selected_image_count=tile_budget.selected_image_count if tile_budget_mode == "adaptive" else None,
                    max_iterations=0,
                    max_selected_images=tile_budget.max_selected_images if tile_budget_mode == "adaptive" else None,
                    input_hash=tile_budget.input_hash if tile_budget_mode == "adaptive" else None,
                    source_artifact_uri=str(context_density_hit.get("artifact_s3_uri")),
                    checkpoint_uri=None,
                    spot_enabled=False,
                    prior_duration_hours=tile_budget.prior_duration_hours if tile_budget_mode == "adaptive" else None,
                    prior_fanout_duration_hours=tile_budget.prior_fanout_duration_hours if tile_budget_mode == "adaptive" else None,
                    quality_gate_status=str(context_density_hit.get("quality_gate_status") or "passed"),
                    cache_status="context_density_hit",
                    cache_rejection_reasons=[],
                )
            )
            continue
        if enable_context_density_reuse:
            cache_rejection_reasons.extend(context_density_rejection_reasons)

        cache_hit, tile_cache_rejection_reasons = resolve_tile_cache_hit(
            tile_budget,
            (tile_cache_manifest or {}).get(tile_id) if reuse_tile_cache else None,
        )
        if reuse_tile_cache and cache_hit is not None:
            stages.append(
                BenchmarkStage(
                    stage_name=f"T0_{tile_id}",
                    stage_type="cached_tile",
                    training_mode="leaf_tile",
                    job_name=None,
                    tile_id=tile_id,
                    output_s3_uri=f"{output_root}/tiles/{tile_id}",
                    depends_on=[],
                    environment=build_training_environment(
                        training_mode="leaf_tile",
                        tile_manifest_name=tile_manifest_name,
                        view_bucket_manifest_name=view_bucket_manifest_name,
                        tile_id=tile_id,
                        max_iterations=0,
                        extra_env=stage_env,
                        training_timeout_seconds=training_max_runtime_seconds,
                        downscale_factor=downscale_factor,
                    ),
                    budget_class=tile_budget.budget_class if tile_budget_mode == "adaptive" else None,
                    selected_image_count=tile_budget.selected_image_count if tile_budget_mode == "adaptive" else None,
                    max_iterations=0,
                    max_selected_images=tile_budget.max_selected_images if tile_budget_mode == "adaptive" else None,
                    input_hash=tile_budget.input_hash if tile_budget_mode == "adaptive" else None,
                    source_artifact_uri=str(cache_hit.get("artifact_s3_uri")),
                    checkpoint_uri=None,
                    spot_enabled=False,
                    prior_duration_hours=tile_budget.prior_duration_hours if tile_budget_mode == "adaptive" else None,
                    prior_fanout_duration_hours=tile_budget.prior_fanout_duration_hours if tile_budget_mode == "adaptive" else None,
                    quality_gate_status=str(cache_hit.get("quality_gate_status") or "passed"),
                    cache_status="hit",
                    cache_rejection_reasons=[],
                )
            )
            continue
        if reuse_tile_cache:
            cache_rejection_reasons.extend(tile_cache_rejection_reasons)
        stages.append(
            BenchmarkStage(
                stage_name=f"T0_{tile_id}",
                stage_type="train",
                training_mode="leaf_tile",
                job_name=sanitize_sagemaker_job_name(f"{job_prefix}-{timestamp}-{tile_id}"),
                tile_id=tile_id,
                output_s3_uri=f"{output_root}/tiles/{tile_id}",
                depends_on=[scaffold_stage_name] if include_scaffold else [],
                environment=build_training_environment(
                    training_mode="leaf_tile",
                    tile_manifest_name=tile_manifest_name,
                    view_bucket_manifest_name=view_bucket_manifest_name,
                    tile_id=tile_id,
                    max_iterations=stage_max_iterations,
                    extra_env=stage_env,
                    training_timeout_seconds=training_max_runtime_seconds,
                    downscale_factor=downscale_factor,
                ),
                budget_class=tile_budget.budget_class if tile_budget_mode == "adaptive" else None,
                selected_image_count=tile_budget.selected_image_count if tile_budget_mode == "adaptive" else None,
                max_iterations=tile_budget.max_iterations if tile_budget_mode == "adaptive" else None,
                max_selected_images=tile_budget.max_selected_images if tile_budget_mode == "adaptive" else None,
                input_hash=tile_budget.input_hash if tile_budget_mode == "adaptive" else None,
                source_artifact_uri=tile_budget.source_artifact_uri,
                checkpoint_uri=tile_budget.checkpoint_uri,
                spot_enabled=tile_budget.spot_enabled,
                prior_duration_hours=tile_budget.prior_duration_hours if tile_budget_mode == "adaptive" else None,
                prior_fanout_duration_hours=tile_budget.prior_fanout_duration_hours if tile_budget_mode == "adaptive" else None,
                quality_gate_status=tile_budget.quality_gate_status if tile_budget_mode == "adaptive" else None,
                cache_status="miss" if (reuse_tile_cache or enable_context_density_reuse) else None,
                cache_rejection_reasons=cache_rejection_reasons if (reuse_tile_cache or enable_context_density_reuse) else None,
            )
        )

    if include_merge and selected_tiles:
        merge_mode = extra_env.get("MERGE_MODE", "strict_core")
        stages.append(
            BenchmarkStage(
                stage_name=f"MERGE_{merge_mode}",
                stage_type="merge",
                training_mode=merge_mode,
                output_s3_uri=f"{output_root}/merged",
                depends_on=[f"T0_{tile_id}" for tile_id in selected_tiles],
            )
        )

    return stages


def create_training_job_payload(
    *,
    branch_name: str,
    job_name: str,
    image_uri: str,
    role_arn: str,
    input_s3_uri: str,
    output_s3_uri: str,
    environment: Dict[str, str],
    instance_type: str,
    volume_size_gb: int,
    max_runtime_seconds: int,
    scaffold_artifact_s3_uri: str = "",
    tile_selection_s3_uri: str = "",
    enable_spot: bool = False,
    enable_checkpoints: bool = False,
    checkpoint_s3_uri: str = "",
    max_wait_seconds: int | None = None,
    experiment_id: str = "",
) -> dict:
    input_channels = [
        {
            "ChannelName": "training",
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": "S3Prefix",
                    "S3Uri": input_s3_uri,
                    "S3DataDistributionType": "FullyReplicated",
                }
            },
            "CompressionType": "None",
            "RecordWrapperType": "None",
        }
    ]
    if tile_selection_s3_uri:
        input_channels.append(
            {
                "ChannelName": TILE_SELECTION_CHANNEL_NAME,
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": tile_selection_s3_uri,
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
                "CompressionType": "None",
                "RecordWrapperType": "None",
            }
        )
    if scaffold_artifact_s3_uri:
        input_channels.append(
            {
                "ChannelName": "scaffold",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": scaffold_artifact_s3_uri,
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
                "CompressionType": "None",
                "RecordWrapperType": "None",
            }
        )

    tags = [
        {"Key": "Project", "Value": "Spaceport"},
        {"Key": "Component", "Value": "3DGS"},
        {"Key": "Benchmark", "Value": "true"},
        {"Key": "Branch", "Value": branch_name},
    ]
    if experiment_id:
        tags.append({"Key": "ExperimentId", "Value": experiment_id})
    payload = {
        "TrainingJobName": job_name,
        "AlgorithmSpecification": {
            "TrainingImage": image_uri,
            "TrainingInputMode": "File",
        },
        "RoleArn": role_arn,
        "InputDataConfig": input_channels,
        "OutputDataConfig": {
            "S3OutputPath": output_s3_uri,
        },
        "ResourceConfig": {
            "InstanceType": instance_type,
            "InstanceCount": 1,
            "VolumeSizeInGB": volume_size_gb,
        },
        "StoppingCondition": {
            "MaxRuntimeInSeconds": max_runtime_seconds,
        },
        "Environment": environment,
        "Tags": tags,
    }
    if enable_spot or enable_checkpoints:
        if not checkpoint_s3_uri:
            raise ValueError("checkpoint_s3_uri is required when checkpointing is enabled")
        payload["CheckpointConfig"] = {
            "S3Uri": checkpoint_s3_uri,
            "LocalPath": "/opt/ml/checkpoints",
        }
    if enable_spot:
        payload["EnableManagedSpotTraining"] = True
        payload["StoppingCondition"]["MaxWaitTimeInSeconds"] = int(max_wait_seconds or max_runtime_seconds)
    return payload


def create_quality_review_processing_payload(
    *,
    branch_name: str,
    job_name: str,
    image_uri: str,
    role_arn: str,
    model_artifact_s3_uri: str,
    colmap_s3_uri: str,
    output_s3_uri: str,
    environment: Dict[str, str],
    instance_type: str,
    volume_size_gb: int,
    max_runtime_seconds: int,
    review_camera_manifest_s3_uri: str = "",
    baseline_review_manifest_s3_uri: str = "",
) -> dict:
    resolved_environment = dict(environment)
    processing_inputs = [
        {
            "InputName": "model",
            "S3Input": {
                "S3Uri": model_artifact_s3_uri,
                "LocalPath": "/opt/ml/processing/input/model",
                "S3DataType": "S3Prefix",
                "S3InputMode": "File",
            },
        },
        {
            "InputName": "colmap",
            "S3Input": {
                "S3Uri": colmap_s3_uri,
                "LocalPath": "/opt/ml/processing/input/colmap",
                "S3DataType": "S3Prefix",
                "S3InputMode": "File",
            },
        },
    ]
    if review_camera_manifest_s3_uri:
        processing_inputs.append(
            {
                "InputName": "review-manifest",
                "S3Input": {
                    "S3Uri": review_camera_manifest_s3_uri,
                    "LocalPath": "/opt/ml/processing/input/review",
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File",
                },
            }
        )
        resolved_environment.setdefault(
            "FROZEN_REVIEW_CAMERA_MANIFEST",
            "/opt/ml/processing/input/review/review_camera_manifest.json",
        )
    if baseline_review_manifest_s3_uri:
        processing_inputs.append(
            {
                "InputName": "baseline-review",
                "S3Input": {
                    "S3Uri": baseline_review_manifest_s3_uri,
                    "LocalPath": "/opt/ml/processing/input/baseline-review",
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File",
                },
            }
        )
        resolved_environment.setdefault(
            "BASELINE_REVIEW_MANIFEST",
            "/opt/ml/processing/input/baseline-review/quality_review_manifest.json",
        )

    return {
        "ProcessingJobName": job_name,
        "RoleArn": role_arn,
        "AppSpecification": {
            "ImageUri": image_uri,
            "ContainerEntrypoint": ["python3", "/opt/ml/code/run_tiled_quality_review.py"],
        },
        "Environment": resolved_environment,
        "ProcessingInputs": processing_inputs,
        "ProcessingOutputConfig": {
            "Outputs": [
                {
                    "OutputName": "quality-review",
                    "S3Output": {
                        "S3Uri": output_s3_uri,
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    },
                }
            ]
        },
        "ProcessingResources": {
            "ClusterConfig": {
                "InstanceType": instance_type,
                "InstanceCount": 1,
                "VolumeSizeInGB": volume_size_gb,
            }
        },
        "StoppingCondition": {
            "MaxRuntimeInSeconds": max_runtime_seconds,
        },
        "Tags": [
            {"Key": "Project", "Value": "Spaceport"},
            {"Key": "Component", "Value": "3DGS"},
            {"Key": "Benchmark", "Value": "true"},
            {"Key": "Branch", "Value": branch_name},
            {"Key": "Stage", "Value": "quality-review"},
        ],
    }


def create_quality_review_training_payload(
    *,
    branch_name: str,
    job_name: str,
    image_uri: str,
    role_arn: str,
    model_artifact_s3_uri: str,
    colmap_s3_uri: str,
    output_s3_uri: str,
    environment: Dict[str, str],
    instance_type: str,
    volume_size_gb: int,
    max_runtime_seconds: int,
    review_camera_manifest_s3_uri: str = "",
    baseline_review_manifest_s3_uri: str = "",
) -> dict:
    resolved_environment = {
        "MODEL_INPUT_DIR": "/opt/ml/input/data/model",
        "COLMAP_INPUT_DIR": "/opt/ml/input/data/colmap",
        "OUTPUT_DIR": "/opt/ml/model",
        **environment,
    }
    input_channels = [
        {
            "ChannelName": "model",
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": "S3Prefix",
                    "S3Uri": model_artifact_s3_uri,
                    "S3DataDistributionType": "FullyReplicated",
                }
            },
            "CompressionType": "None",
            "RecordWrapperType": "None",
        },
        {
            "ChannelName": "colmap",
            "DataSource": {
                "S3DataSource": {
                    "S3DataType": "S3Prefix",
                    "S3Uri": colmap_s3_uri,
                    "S3DataDistributionType": "FullyReplicated",
                }
            },
            "CompressionType": "None",
            "RecordWrapperType": "None",
        },
    ]
    if review_camera_manifest_s3_uri:
        input_channels.append(
            {
                "ChannelName": "review-manifest",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": review_camera_manifest_s3_uri,
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
                "CompressionType": "None",
                "RecordWrapperType": "None",
            }
        )
        resolved_environment.setdefault(
            "FROZEN_REVIEW_CAMERA_MANIFEST",
            "/opt/ml/input/data/review-manifest/review_camera_manifest.json",
        )
    if baseline_review_manifest_s3_uri:
        input_channels.append(
            {
                "ChannelName": "baseline-review",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": baseline_review_manifest_s3_uri,
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
                "CompressionType": "None",
                "RecordWrapperType": "None",
            }
        )
        resolved_environment.setdefault(
            "BASELINE_REVIEW_MANIFEST",
            "/opt/ml/input/data/baseline-review/quality_review_manifest.json",
        )

    return {
        "TrainingJobName": job_name,
        "RoleArn": role_arn,
        "AlgorithmSpecification": {
            "TrainingImage": image_uri,
            "TrainingInputMode": "File",
            "ContainerEntrypoint": ["python3", "/opt/ml/code/run_tiled_quality_review.py"],
        },
        "InputDataConfig": input_channels,
        "OutputDataConfig": {
            "S3OutputPath": output_s3_uri,
        },
        "ResourceConfig": {
            "InstanceType": instance_type,
            "InstanceCount": 1,
            "VolumeSizeInGB": volume_size_gb,
        },
        "StoppingCondition": {
            "MaxRuntimeInSeconds": max_runtime_seconds,
        },
        "Environment": resolved_environment,
        "Tags": [
            {"Key": "Project", "Value": "Spaceport"},
            {"Key": "Component", "Value": "3DGS"},
            {"Key": "Benchmark", "Value": "true"},
            {"Key": "Branch", "Value": branch_name},
            {"Key": "Stage", "Value": "quality-review"},
        ],
    }


def wait_for_training_job(job_name: str, *, poll_seconds: int) -> dict:
    while True:
        status = aws_json("sagemaker", "describe-training-job", "--training-job-name", job_name)
        current_status = status["TrainingJobStatus"]
        if current_status == "Completed":
            return status
        if current_status in {"Failed", "Stopped"}:
            reason = status.get("FailureReason", current_status)
            raise RuntimeError(f"Training job {job_name} ended with {current_status}: {reason}")
        time.sleep(max(15, poll_seconds))


def wait_for_processing_job(job_name: str, *, poll_seconds: int) -> dict:
    while True:
        status = aws_json("sagemaker", "describe-processing-job", "--processing-job-name", job_name)
        current_status = status["ProcessingJobStatus"]
        if current_status == "Completed":
            return status
        if current_status in {"Failed", "Stopped"}:
            reason = status.get("FailureReason", current_status)
            raise RuntimeError(f"Processing job {job_name} ended with {current_status}: {reason}")
        time.sleep(max(15, poll_seconds))


def download_and_extract_model_artifact(
    *,
    s3_uri: str,
    target_dir: Path,
    members: Sequence[str] | None = None,
) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    tar_path = target_dir / "model.tar.gz"
    run_command(["aws", "s3", "cp", s3_uri, str(tar_path)])
    try:
        with tarfile.open(tar_path, "r:gz") as archive:
            if members:
                for member_name in members:
                    try:
                        member = archive.getmember(member_name)
                    except KeyError:
                        continue
                    archive.extract(member, target_dir)
            else:
                archive.extractall(target_dir)
    finally:
        tar_path.unlink(missing_ok=True)
    return target_dir


def assert_s3_object_exists(s3_uri: str) -> None:
    if not s3_uri.startswith("s3://"):
        raise RuntimeError(f"Expected an s3:// artifact URI, got {s3_uri}")
    run_command(["aws", "s3", "ls", s3_uri], capture_output=True)


def summarize_training_metadata(stage_name: str, extracted_dir: Path, describe_payload: dict) -> dict:
    metadata_path = extracted_dir / "training_metadata.json"
    selection_path = extracted_dir / "training_selection.json"
    tiled_summary_path = extracted_dir / "tiled_pipeline_summary.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    selection = json.loads(selection_path.read_text(encoding="utf-8")) if selection_path.exists() else {}
    tiled_summary = json.loads(tiled_summary_path.read_text(encoding="utf-8")) if tiled_summary_path.exists() else {}
    return {
        "stage_name": stage_name,
        "training_mode": metadata.get("training_mode") or selection.get("training_mode"),
        "billable_time_seconds": describe_payload.get("BillableTimeInSeconds"),
        "training_time_seconds": describe_payload.get("TrainingTimeInSeconds"),
        "model_artifacts_s3_uri": describe_payload.get("ModelArtifacts", {}).get("S3ModelArtifacts"),
        "output_file": metadata.get("output_file"),
        "file_size_mb": metadata.get("file_size_mb"),
        "background_skybox": metadata.get("background_skybox"),
        "training_selection": selection or metadata.get("training_selection"),
        "tiled_pipeline_summary": tiled_summary or metadata.get("stages"),
    }


def artifact_members_for_stage(stage: BenchmarkStage) -> list[str]:
    members = [
        "training_metadata.json",
        "training_selection.json",
        "tiled_pipeline_summary.json",
        "merged/merge_report.json",
    ]
    if stage.tile_id:
        members.append("splat.ply")
    if stage.stage_type == "context_density_tile" and stage.tile_id:
        members.extend(
            [
                f"tiles/{stage.tile_id}/splat.ply",
                f"tiles/{stage.tile_id}/training_metadata.json",
                f"tiles/{stage.tile_id}/training_selection.json",
            ]
        )
    return members


def materialize_context_density_tile(stage: BenchmarkStage, extracted_dir: Path) -> None:
    if stage.stage_type != "context_density_tile" or not stage.tile_id:
        return
    tile_dir = extracted_dir / "tiles" / stage.tile_id
    for filename in ("splat.ply", "training_metadata.json", "training_selection.json"):
        target = extracted_dir / filename
        source = tile_dir / filename
        if not target.exists() and source.exists():
            shutil.copy2(source, target)


def materialize_merge_tile_dir(source_dir: Path, stage_link: Path) -> str:
    if stage_link.exists() or stage_link.is_symlink():
        if stage_link.is_symlink() or stage_link.is_file():
            stage_link.unlink()
        else:
            shutil.rmtree(stage_link)
    try:
        stage_link.symlink_to(source_dir.resolve(), target_is_directory=True)
        return "symlink"
    except OSError:
        shutil.copytree(source_dir, stage_link)
        return "copy"


def run_merge_stage(
    *,
    tile_manifest: dict[str, object],
    tile_stage_dirs: Dict[str, Path],
    output_dir: Path,
    merge_mode: str = "strict_core",
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    tile_manifest_path = output_dir / "selected_tile_manifest.json"
    tile_manifest_path.write_text(json.dumps(tile_manifest, indent=2), encoding="utf-8")
    command = [
        "python3",
        str(MERGE_SCRIPT_PATH),
        "--tile-manifest",
        str(tile_manifest_path),
        "--tiles-root",
        str(output_dir / "tile_outputs"),
        "--output-dir",
        str(output_dir),
        "--merge-mode",
        merge_mode,
    ]
    tile_root = output_dir / "tile_outputs"
    tile_root.mkdir(parents=True, exist_ok=True)
    materialization_modes: dict[str, str] = {}
    for tile_id, extracted_dir in tile_stage_dirs.items():
        stage_link = tile_root / tile_id
        materialization_modes[tile_id] = materialize_merge_tile_dir(extracted_dir, stage_link)
    result = run_command(command, capture_output=True)
    payload = json.loads(result.stdout)
    payload["tile_materialization_modes"] = materialization_modes
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch", default="", help="Git branch to benchmark. Defaults to current branch.")
    parser.add_argument(
        "--stack-name",
        default="",
        help="Optional CloudFormation ML stack name override. Use this when the current branch has no deployed ML stack.",
    )
    parser.add_argument(
        "--role-arn",
        default="",
        help="Optional SageMaker execution role ARN. Requires --image-uri and --output-root-s3-uri when no ML stack is available.",
    )
    parser.add_argument("--colmap-s3-uri", required=True, help="S3 prefix for SfM/colmap output.")
    parser.add_argument(
        "--output-root-s3-uri",
        default="",
        help="S3 prefix for benchmark outputs. Defaults to the branch ML bucket manual-validations prefix.",
    )
    parser.add_argument("--job-prefix", default="3dgs-tiled", help="Training job name prefix.")
    parser.add_argument("--instance-type", default=DEFAULT_INSTANCE_TYPE)
    parser.add_argument("--volume-size-gb", type=int, default=DEFAULT_VOLUME_SIZE_GB)
    parser.add_argument("--training-max-runtime-seconds", type=int, default=DEFAULT_TRAINING_MAX_RUNTIME_SECONDS)
    parser.add_argument(
        "--max-estimated-usd",
        type=float,
        default=0.0,
        help="Required with --submit. Blocks paid runs whose estimated training cost exceeds this cap.",
    )
    parser.add_argument(
        "--production-rung-gate-json",
        default="",
        help="Local or s3:// JSON proving R0/R1/R2/R3 gates passed before full 14-tile submits.",
    )
    parser.add_argument(
        "--experiment-id",
        default="",
        help="Required with --submit. Stable ID written to summaries and SageMaker tags.",
    )
    parser.add_argument("--monolithic-max-iterations", type=int, default=DEFAULT_TILE_MAX_ITERATIONS)
    parser.add_argument("--scaffold-max-iterations", type=int, default=DEFAULT_SCAFFOLD_MAX_ITERATIONS)
    parser.add_argument("--tile-max-iterations", type=int, default=DEFAULT_TILE_MAX_ITERATIONS)
    parser.add_argument(
        "--tile-budget-mode",
        choices=["fixed", "adaptive"],
        default="fixed",
        help="Use adaptive per-tile iteration/image budgets for fanout leaf jobs.",
    )
    parser.add_argument(
        "--max-images-per-tile",
        type=int,
        default=0,
        help="Upper bound for per-tile selected images; adaptive class defaults still apply below this cap.",
    )
    parser.add_argument(
        "--max-tile-concurrency",
        type=int,
        default=1,
        help="Maximum concurrently active leaf-tile jobs in fanout mode when --wait is used.",
    )
    parser.add_argument(
        "--reuse-tile-cache",
        action="store_true",
        help="Reuse validated per-tile artifacts from --tile-cache-manifest-json when input hashes match.",
    )
    parser.add_argument(
        "--tile-cache-manifest-json",
        default="",
        help="Optional local path or s3:// JSON with validated per-tile cache records for --reuse-tile-cache.",
    )
    parser.add_argument(
        "--enable-context-density-reuse",
        action="store_true",
        help="Reuse dense teacher/context tile artifacts from --context-density-manifest-json before training.",
    )
    parser.add_argument(
        "--context-density-manifest-json",
        default="",
        help="Optional local path or s3:// JSON with dense teacher/context tile reuse records.",
    )
    parser.add_argument(
        "--prior-tile-stats-json",
        default="",
        help="Optional local path or s3:// JSON with prior retained gaussians/durations for adaptive tile budgets.",
    )
    parser.add_argument(
        "--tile-manifest-json",
        default="",
        help="Optional local path or s3:// 3dgs_tile_manifest.json override for no-spend production-shaped planning.",
    )
    parser.add_argument(
        "--view-bucket-json",
        default="",
        help="Optional local path or s3:// 3dgs_view_buckets.json override for no-spend production-shaped planning.",
    )
    parser.add_argument("--enable-spot", action="store_true", help="Use SageMaker Managed Spot Training.")
    parser.add_argument(
        "--enable-checkpoints",
        action="store_true",
        help="Attach SageMaker CheckpointConfig and checkpoint env without enabling Managed Spot.",
    )
    parser.add_argument(
        "--checkpoint-s3-prefix",
        default="",
        help="S3 prefix for SageMaker training checkpoints when checkpoints or Spot are enabled.",
    )
    parser.add_argument(
        "--checkpoint-resume-s3-uri",
        default="",
        help=(
            "Optional prior checkpoint prefix to download before training. "
            "Use with a separate --checkpoint-s3-prefix for restart proofs."
        ),
    )
    parser.add_argument(
        "--checkpoint-resume-extra-iterations",
        type=int,
        default=0,
        help=(
            "When --checkpoint-resume-s3-uri has a compact checkpoint manifest, extend resumed train stages "
            "to checkpoint_step + this value + 1 so restart proofs run real additional iterations."
        ),
    )
    parser.add_argument(
        "--checkpoint-save-steps",
        type=int,
        default=DEFAULT_CHECKPOINT_SAVE_STEPS,
        help="Default TRAINING_STEPS_PER_SAVE for checkpointed runs unless --env overrides it.",
    )
    parser.add_argument(
        "--spot-max-wait-seconds",
        type=int,
        default=0,
        help=(
            "MaxWaitTimeInSeconds for Managed Spot jobs. Required with --submit --enable-spot; "
            f"may exceed runtime by at most {MAX_SPOT_EXTRA_WAIT_SECONDS}s."
        ),
    )
    parser.add_argument(
        "--spot-restart-proof-passed",
        action="store_true",
        help="Required before --submit with --enable-spot; documents the one-tile checkpoint restart proof gate.",
    )
    parser.add_argument("--downscale-factor", type=int, default=1, help="Optional per-stage image downscale factor for cheap proof runs.")
    parser.add_argument("--max-tiles", type=int, default=4, help="Cap leaf-tile jobs for cheap ladder runs.")
    parser.add_argument("--tile-id", action="append", default=[], help="Repeatable tile_id filter.")
    parser.add_argument("--env", action="append", default=[], help="Repeatable KEY=VALUE environment overrides.")
    parser.add_argument(
        "--leaf-reference-splat-count",
        action="append",
        default=[],
        help="Repeatable tile_id=count guard used to emit post-leaf preflight/enforcement commands.",
    )
    parser.add_argument(
        "--leaf-max-reference-splat-ratio",
        type=float,
        default=0.0,
        help="Maximum allowed leaf splat ratio versus --leaf-reference-splat-count before merge/review spend.",
    )
    parser.add_argument("--image-tag", default="", help="Override the ECR image tag. Defaults to current branch tag.")
    parser.add_argument("--image-uri", default="", help="Fully qualified training image URI override.")
    parser.add_argument(
        "--scaffold-artifact-s3-uri",
        default="",
        help="Optional S3 prefix containing a prior scaffold model.tar.gz or splat.ply for tiled or fanout leaf reuse.",
    )
    parser.add_argument("--wait", action="store_true", help="Wait for submitted jobs and collect summaries.")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--submit", action="store_true", help="Submit the generated training jobs.")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved benchmark plan without submitting jobs.")
    parser.add_argument("--include-monolithic", action="store_true", help="Include the monolithic baseline rung.")
    parser.add_argument(
        "--orchestration-mode",
        choices=["single_job", "fanout"],
        default="single_job",
        help="Run one tiled job that orchestrates scaffold+tiles locally, or fan out one SageMaker job per stage.",
    )
    parser.add_argument("--skip-scaffold", action="store_true", help="Skip the scaffold rung.")
    parser.add_argument("--skip-merge", action="store_true", help="Skip the local merge stage.")
    parser.add_argument(
        "--merge-mode",
        choices=["strict_core", "support_weighted_overlap"],
        default="strict_core",
        help="Merge strategy for tiled pipeline and fanout local merge.",
    )
    parser.add_argument("--skip-review", action="store_true", help="Skip the post-run merged quality review job.")
    parser.add_argument(
        "--proof-profile",
        choices=[PROOF_PROFILE_NONE, PROOF_PROFILE_QUALITY_GATE_LOW_MEMORY],
        default=None,
        help="Optional proof-run environment profile. Defaults to quality_gate_low_memory for single-job runs with review.",
    )
    parser.add_argument(
        "--suppress-training-eval",
        action="store_true",
        help=(
            "Set train-time eval/save intervals to max_iterations+1 without enabling the low-memory proof profile. "
            "Explicit --env values for the same keys still win."
        ),
    )
    parser.add_argument("--review-instance-type", default=DEFAULT_INSTANCE_TYPE)
    parser.add_argument("--review-volume-size-gb", type=int, default=DEFAULT_VOLUME_SIZE_GB)
    parser.add_argument("--review-max-runtime-seconds", type=int, default=DEFAULT_REVIEW_MAX_RUNTIME_SECONDS)
    parser.add_argument(
        "--review-camera-manifest-s3-uri",
        default="",
        help="Optional frozen camera manifest prefix for quality review.",
    )
    parser.add_argument(
        "--baseline-review-manifest-s3-uri",
        default="",
        help="Optional baseline quality_review_manifest.json prefix for quality review.",
    )
    parser.add_argument(
        "--v18-review-manifest-s3-uri",
        default="",
        help="Required with --submit. V18 quality_review_manifest.json prefix used for non-regression comparison.",
    )
    parser.add_argument(
        "--compatibility-gate",
        action="store_true",
        help="Mark the run as a future large-artifact compatibility gate; summaries stop on manual hold.",
    )
    parser.add_argument("--summary-json-output", default="", help="Optional local path for the benchmark summary JSON.")
    parser.add_argument(
        "--local-merge-output-dir",
        default="",
        help="Optional local directory for downloaded tile artifacts and merged output when --wait is used.",
    )
    return parser.parse_args()


def resolve_execution_context(
    *,
    branch_name: str,
    timestamp: int,
    args: argparse.Namespace,
) -> ExecutionContext:
    branch_tag = get_branch_ecr_tag(branch_name) or "latest"
    resolved_stack_name: str | None = None
    outputs: Dict[str, str] = {}

    if args.stack_name:
        resolved_stack_name, outputs = get_stack_outputs(args.stack_name)
    else:
        try:
            resolved_stack_name, outputs = find_branch_ml_stack(branch_name)
        except RuntimeError:
            if not (args.role_arn and args.image_uri and args.output_root_s3_uri):
                raise RuntimeError(
                    "Could not find a branch ML stack. Provide --stack-name, or provide "
                    "--role-arn, --image-uri, and --output-root-s3-uri explicitly."
                ) from None

    role_arn = args.role_arn or (get_sagemaker_role_arn(resolved_stack_name) if resolved_stack_name else "")
    if not role_arn:
        raise RuntimeError("Could not resolve a SageMaker role ARN for the benchmark run")

    if args.image_uri:
        image_uri = args.image_uri
    else:
        gaussian_repo_uri = outputs.get("GaussianRepositoryUri")
        if not gaussian_repo_uri:
            raise RuntimeError("Missing GaussianRepositoryUri; provide --image-uri explicitly")
        selected_tag = args.image_tag or branch_tag
        image_uri = f"{gaussian_repo_uri}:{selected_tag}"

    if args.output_root_s3_uri:
        output_root_s3_uri = args.output_root_s3_uri
    else:
        bucket_name = outputs.get("MLBucketName")
        if not bucket_name:
            raise RuntimeError("Missing MLBucketName; provide --output-root-s3-uri explicitly")
        output_root_s3_uri = f"s3://{bucket_name}/manual-validations/{args.job_prefix}-{timestamp}/3dgs"

    return ExecutionContext(
        stack_name=resolved_stack_name,
        outputs=outputs,
        role_arn=role_arn,
        image_uri=image_uri,
        output_root_s3_uri=output_root_s3_uri,
    )


def main() -> int:
    args = parse_args()
    branch_name = args.branch or get_current_branch()
    timestamp = int(time.time())
    include_review = not args.skip_review
    if args.max_tile_concurrency < 1:
        raise RuntimeError("--max-tile-concurrency must be >= 1")
    resolved_proof_profile = resolve_proof_profile(
        args.proof_profile,
        orchestration_mode=args.orchestration_mode,
        include_review=include_review,
    )
    if args.scaffold_artifact_s3_uri and args.orchestration_mode == "fanout" and not args.skip_scaffold:
        raise RuntimeError("--scaffold-artifact-s3-uri with fanout requires --skip-scaffold to avoid retraining scaffold")
    production_rung_gate = load_production_rung_gate(args.production_rung_gate_json)
    context = resolve_execution_context(
        branch_name=branch_name,
        timestamp=timestamp,
        args=args,
    )

    colmap_s3_uri = normalize_s3_prefix(args.colmap_s3_uri)
    tile_manifest_s3_uri = f"{colmap_s3_uri}/3dgs_tile_manifest.json"
    view_bucket_s3_uri = f"{colmap_s3_uri}/3dgs_view_buckets.json"
    chunk_planner_s3_uri = f"{colmap_s3_uri}/chunk_planner_manifest.json"
    sfm_metadata_s3_uri = f"{colmap_s3_uri}/sfm_metadata.json"
    tile_selection_input_s3_uri = f"{normalize_s3_prefix(context.output_root_s3_uri)}/inputs/tile-selection"

    validate_manifest_override_args(
        tile_manifest_json=args.tile_manifest_json,
        view_bucket_json=args.view_bucket_json,
    )

    tile_manifest_payload = (
        load_json_path_or_s3(args.tile_manifest_json)
        if args.tile_manifest_json
        else s3_json_or_none(tile_manifest_s3_uri)
    )
    view_bucket_payload = (
        load_json_path_or_s3(args.view_bucket_json)
        if args.view_bucket_json
        else s3_json_or_none(view_bucket_s3_uri)
    )
    chunk_planner_payload = s3_json_or_none(chunk_planner_s3_uri)
    sfm_metadata_payload = s3_json_or_none(sfm_metadata_s3_uri)
    sparse_support_dir = None
    if chunk_planner_payload is not None and (tile_manifest_payload is None or view_bucket_payload is None):
        sparse_support_dir = download_sparse_support_dir(
            colmap_s3_uri,
            scratch_dir=Path(tempfile.mkdtemp(prefix="3dgs-benchmark-sparse-")),
        )
    tile_manifest, view_buckets, manifest_resolution = resolve_tiled_input_manifests(
        tile_manifest_payload=tile_manifest_payload,
        view_bucket_payload=view_bucket_payload,
        chunk_planner_manifest=chunk_planner_payload,
        sfm_metadata=sfm_metadata_payload,
        colmap_sparse_dir=sparse_support_dir,
    )
    prior_tile_stats = normalize_prior_tile_stats(load_json_path_or_s3(args.prior_tile_stats_json))
    tile_manifest = apply_prior_tile_stats(tile_manifest, prior_tile_stats)
    tile_cache_manifest = normalize_tile_cache_manifest(load_json_path_or_s3(args.tile_cache_manifest_json))
    context_density_manifest = normalize_context_density_manifest(
        load_json_path_or_s3(args.context_density_manifest_json)
    )

    selected_tiles = select_tile_ids(
        tile_manifest,
        explicit_tile_ids=args.tile_id,
        max_tiles=args.max_tiles,
    )
    explicit_env = parse_env(args.env)
    leaf_reference_splat_counts = parse_tile_int_map(
        args.leaf_reference_splat_count,
        label="--leaf-reference-splat-count",
    )
    training_env_overrides = {"MERGE_MODE": args.merge_mode, **explicit_env}
    if args.suppress_training_eval:
        apply_training_eval_suppression(training_env_overrides, max_iterations=args.tile_max_iterations)
    checkpoints_requested = bool(args.enable_checkpoints or args.enable_spot)
    if checkpoints_requested:
        training_env_overrides.setdefault("TRAINING_CHECKPOINT_DIR", "/opt/ml/checkpoints")
        training_env_overrides.setdefault("TRAINING_ENABLE_CHECKPOINTS", "true")
        if "TRAINING_STEPS_PER_SAVE" not in explicit_env:
            training_env_overrides["TRAINING_STEPS_PER_SAVE"] = str(args.checkpoint_save_steps)
    if args.checkpoint_resume_s3_uri:
        training_env_overrides.setdefault(
            "TRAINING_CHECKPOINT_RESUME_S3_URI",
            args.checkpoint_resume_s3_uri,
        )
    if args.scaffold_artifact_s3_uri:
        training_env_overrides.setdefault("GLOBAL_SCAFFOLD_SOURCE_DIR", "/opt/ml/input/data/scaffold")

    stages = build_benchmark_stages(
        manifest=tile_manifest,
        branch_name=branch_name,
        output_root_s3_uri=context.output_root_s3_uri,
        job_prefix=args.job_prefix,
        include_monolithic=args.include_monolithic,
        include_scaffold=not args.skip_scaffold,
        include_merge=not args.skip_merge,
        orchestration_mode=args.orchestration_mode,
        tile_ids=selected_tiles,
        monolithic_max_iterations=args.monolithic_max_iterations,
        scaffold_max_iterations=args.scaffold_max_iterations,
        tile_max_iterations=args.tile_max_iterations,
        training_max_runtime_seconds=args.training_max_runtime_seconds,
        extra_env=training_env_overrides,
        timestamp=timestamp,
        downscale_factor=args.downscale_factor,
        include_review=include_review,
        proof_profile=resolved_proof_profile,
        tile_budget_mode=args.tile_budget_mode,
        max_images_per_tile=args.max_images_per_tile,
        input_colmap_s3_uri=colmap_s3_uri,
        image_uri=context.image_uri,
        scaffold_artifact_s3_uri=args.scaffold_artifact_s3_uri,
        instance_type=args.instance_type,
        enable_spot=args.enable_spot,
        enable_checkpoints=args.enable_checkpoints,
        checkpoint_s3_prefix=args.checkpoint_s3_prefix,
        reuse_tile_cache=args.reuse_tile_cache,
        tile_cache_manifest=tile_cache_manifest,
        enable_context_density_reuse=args.enable_context_density_reuse,
        context_density_manifest=context_density_manifest,
    )
    checkpoint_resume_step, checkpoint_resume_manifest_uri = resolve_checkpoint_resume_step(args.checkpoint_resume_s3_uri)
    if args.checkpoint_resume_extra_iterations > 0 and checkpoint_resume_step is None:
        raise RuntimeError(
            "Could not resolve checkpoint step from "
            f"{checkpoint_resume_manifest_uri}; cannot apply --checkpoint-resume-extra-iterations"
        )
    checkpoint_resume_iteration_extensions = extend_checkpoint_resume_stage_iterations(
        stages,
        checkpoint_resume_step=checkpoint_resume_step,
        extra_iterations=args.checkpoint_resume_extra_iterations,
    )
    attach_tile_selection_channel_to_stages(stages)
    post_leaf_preflight_gates = build_post_leaf_preflight_gates(
        stages,
        reference_splat_counts=leaf_reference_splat_counts,
        max_reference_splat_ratio=args.leaf_max_reference_splat_ratio,
        experiment_id=args.experiment_id,
        gate_json_path=args.summary_json_output,
    )
    gated_tile_ids = {str(gate.get("tile_id")) for gate in post_leaf_preflight_gates}
    unused_leaf_reference_splat_counts = {
        tile_id: count
        for tile_id, count in leaf_reference_splat_counts.items()
        if tile_id not in gated_tile_ids
    }
    cost_estimate = estimate_training_cost(
        stages,
        instance_type=args.instance_type,
        max_runtime_seconds=args.training_max_runtime_seconds,
        baseline_iterations=args.tile_max_iterations,
    )

    summary: dict = {
        "branch": branch_name,
        "experiment_id": args.experiment_id,
        "stack_name": context.stack_name,
        "image_uri": context.image_uri,
        "input_colmap_s3_uri": colmap_s3_uri,
        "tile_manifest_s3_uri": tile_manifest_s3_uri,
        "view_bucket_s3_uri": view_bucket_s3_uri,
        "tile_manifest_json_override": args.tile_manifest_json,
        "view_bucket_json_override": args.view_bucket_json,
        "tile_selection_input_s3_uri": tile_selection_input_s3_uri,
        "tile_selection_channel_dir": TILE_SELECTION_CHANNEL_DIR,
        "chunk_planner_s3_uri": chunk_planner_s3_uri,
        "sfm_metadata_s3_uri": sfm_metadata_s3_uri,
        "manifest_resolution": manifest_resolution,
        "prior_tile_stats_json": args.prior_tile_stats_json,
        "prior_tile_stats_tile_count": len(prior_tile_stats),
        "selected_tile_ids": selected_tiles,
        "downscale_factor": args.downscale_factor,
        "proof_profile": resolved_proof_profile,
        "training_max_runtime_seconds": args.training_max_runtime_seconds,
        "leaf_reference_splat_counts": leaf_reference_splat_counts,
        "leaf_max_reference_splat_ratio": args.leaf_max_reference_splat_ratio,
        "unused_leaf_reference_splat_counts": unused_leaf_reference_splat_counts,
        "post_leaf_preflight_gates": post_leaf_preflight_gates,
        "compatibility_gate": bool(args.compatibility_gate),
        "suppress_training_eval": bool(args.suppress_training_eval),
        "merge_mode": args.merge_mode,
        "scaffold_artifact_s3_uri": args.scaffold_artifact_s3_uri,
        "tile_budget_mode": args.tile_budget_mode,
        "max_images_per_tile": args.max_images_per_tile,
        "max_tile_concurrency": args.max_tile_concurrency,
        "reuse_tile_cache": bool(args.reuse_tile_cache),
        "tile_cache_manifest_json": args.tile_cache_manifest_json,
        "tile_cache_entry_count": len(tile_cache_manifest),
        "enable_context_density_reuse": bool(args.enable_context_density_reuse),
        "context_density_manifest_json": args.context_density_manifest_json,
        "context_density_entry_count": len(context_density_manifest),
        "enable_spot": bool(args.enable_spot),
        "spot_max_wait_seconds": args.spot_max_wait_seconds,
        "max_spot_extra_wait_seconds": MAX_SPOT_EXTRA_WAIT_SECONDS,
        "enable_checkpoints": bool(args.enable_checkpoints or args.enable_spot),
        "checkpoint_s3_prefix": args.checkpoint_s3_prefix,
        "checkpoint_resume_s3_uri": args.checkpoint_resume_s3_uri,
        "checkpoint_resume_manifest_s3_uri": checkpoint_resume_manifest_uri,
        "checkpoint_resume_start_step": checkpoint_resume_step,
        "checkpoint_resume_extra_iterations": args.checkpoint_resume_extra_iterations,
        "checkpoint_resume_iteration_extensions": checkpoint_resume_iteration_extensions,
        "checkpoint_save_steps": args.checkpoint_save_steps,
        "max_estimated_usd": args.max_estimated_usd,
        "production_rung_gate_json": args.production_rung_gate_json,
        "production_rung_gate": production_rung_gate,
        "review_camera_manifest_s3_uri": args.review_camera_manifest_s3_uri,
        "baseline_review_manifest_s3_uri": args.baseline_review_manifest_s3_uri,
        "v18_review_manifest_s3_uri": args.v18_review_manifest_s3_uri,
        "v18_non_regression_thresholds": DEFAULT_V18_NON_REGRESSION_THRESHOLDS,
        "cost_estimate": cost_estimate,
        "manual_hold": (
            {
                "required": True,
                "reason": "compatibility gate passed; hold before launching the future largest tiled 3DGS run",
            }
            if args.compatibility_gate
            else None
        ),
        "stages": [stage.to_dict() for stage in stages],
        "submitted_jobs": [],
        "completed_jobs": [],
    }

    if args.submit and post_leaf_preflight_gates and (not args.skip_merge or not args.skip_review):
        raise RuntimeError(
            "--leaf-reference-splat-count requires --skip-merge and --skip-review on submitted runs; "
            "run the emitted post_leaf_preflight_gates before any merge/review spend"
        )

    if args.dry_run or not args.submit:
        print(json.dumps(summary, indent=2))
        if args.summary_json_output:
            Path(args.summary_json_output).write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return 0

    validate_submit_guardrails(args, summary)

    if args.orchestration_mode == "fanout" and not args.wait:
        raise RuntimeError("Fanout submission requires --wait so scaffold and tile dependencies can be enforced safely")

    if any(training_stage_requires_tile_selection(stage) for stage in stages):
        upload_tile_selection_manifests(tile_manifest, view_buckets, tile_selection_input_s3_uri)

    sagemaker = aws_json  # alias for consistency with lambda/test patterns
    submitted_stage_to_job: Dict[str, str] = {}
    completed_stage_outputs: Dict[str, dict] = {}

    merge_summary = None
    merge_root = Path(args.local_merge_output_dir) if args.local_merge_output_dir else None
    extracted_stage_dirs: Dict[str, Path] = {}

    def submit_training_stage(stage: BenchmarkStage) -> None:
        scaffold_artifact_s3_uri = resolve_stage_scaffold_artifact_s3_uri(
            stage,
            explicit_scaffold_artifact_s3_uri=args.scaffold_artifact_s3_uri,
            completed_stage_outputs=completed_stage_outputs,
        )
        stage_environment = dict(stage.environment or {})
        if scaffold_artifact_s3_uri and stage.training_mode in {"leaf_tile", "tiled_pipeline"}:
            stage_environment.setdefault("GLOBAL_SCAFFOLD_SOURCE_DIR", SCAFFOLD_CHANNEL_DIR)
            stage_environment.setdefault("GLOBAL_SCAFFOLD_REQUIRE_FILTERED_INIT", "true")
        stage_checkpoint_s3_uri = stage.checkpoint_uri or (
            f"{normalize_s3_prefix(args.checkpoint_s3_prefix)}/{stage.job_name or stage.stage_name}"
            if checkpoints_requested and args.checkpoint_s3_prefix
            else ""
        )
        if stage_checkpoint_s3_uri:
            stage_environment.setdefault("TRAINING_CHECKPOINT_S3_URI", stage_checkpoint_s3_uri)
        payload = create_training_job_payload(
            branch_name=branch_name,
            job_name=stage.job_name or stage.stage_name,
            image_uri=context.image_uri,
            role_arn=context.role_arn,
            input_s3_uri=colmap_s3_uri,
            output_s3_uri=stage.output_s3_uri,
            environment=stage_environment,
            instance_type=args.instance_type,
            volume_size_gb=args.volume_size_gb,
            max_runtime_seconds=args.training_max_runtime_seconds,
            scaffold_artifact_s3_uri=scaffold_artifact_s3_uri,
            tile_selection_s3_uri=(
                tile_selection_input_s3_uri
                if training_stage_requires_tile_selection(stage)
                else ""
            ),
            enable_spot=args.enable_spot,
            enable_checkpoints=args.enable_checkpoints,
            checkpoint_s3_uri=stage_checkpoint_s3_uri,
            max_wait_seconds=args.spot_max_wait_seconds or (args.training_max_runtime_seconds + 3600),
            experiment_id=args.experiment_id,
        )
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(payload, handle, indent=2)
            handle.flush()
            payload_path = Path(handle.name)
        try:
            run_command(["aws", "sagemaker", "create-training-job", "--cli-input-json", f"file://{payload_path}"])
        finally:
            payload_path.unlink(missing_ok=True)
        submitted_stage_to_job[stage.stage_name] = stage.job_name or stage.stage_name
        summary["submitted_jobs"].append(
            {
                "stage_name": stage.stage_name,
                "job_name": stage.job_name,
                "output_s3_uri": stage.output_s3_uri,
            }
        )

    def collect_completed_training_stage(stage: BenchmarkStage) -> None:
        describe_payload = wait_for_training_job(submitted_stage_to_job[stage.stage_name], poll_seconds=args.poll_seconds)
        model_artifacts_s3_uri = describe_payload.get("ModelArtifacts", {}).get("S3ModelArtifacts")
        if not model_artifacts_s3_uri:
            raise RuntimeError(f"Training job {stage.job_name} completed without model artifacts")
        extracted_dir = None
        if merge_root is not None:
            stage_dir = merge_root / stage.stage_name
            extracted_dir = download_and_extract_model_artifact(
                s3_uri=model_artifacts_s3_uri,
                target_dir=stage_dir,
                members=artifact_members_for_stage(stage),
            )
            materialize_context_density_tile(stage, extracted_dir)
        if stage.tile_id and extracted_dir is not None:
            extracted_stage_dirs[stage.tile_id] = extracted_dir
        completed = summarize_training_metadata(stage.stage_name, extracted_dir or Path("/nonexistent"), describe_payload)
        summary["completed_jobs"].append(completed)
        completed_stage_outputs[stage.stage_name] = completed

    def collect_cached_tile_stage(stage: BenchmarkStage) -> None:
        model_artifacts_s3_uri = str(stage.source_artifact_uri or "").strip()
        if not model_artifacts_s3_uri:
            raise RuntimeError(f"Cached stage {stage.stage_name} is missing source_artifact_uri")
        assert_s3_object_exists(model_artifacts_s3_uri)
        extracted_dir = None
        if merge_root is not None:
            stage_dir = merge_root / stage.stage_name
            extracted_dir = download_and_extract_model_artifact(
                s3_uri=model_artifacts_s3_uri,
                target_dir=stage_dir,
                members=artifact_members_for_stage(stage),
            )
            materialize_context_density_tile(stage, extracted_dir)
        if stage.tile_id and extracted_dir is not None:
            extracted_stage_dirs[stage.tile_id] = extracted_dir
        completed = summarize_training_metadata(
            stage.stage_name,
            extracted_dir or Path("/nonexistent"),
            {
                "BillableTimeInSeconds": 0,
                "TrainingTimeInSeconds": 0,
                "ModelArtifacts": {"S3ModelArtifacts": model_artifacts_s3_uri},
            },
        )
        completed["cache_hit"] = True
        completed["cache_status"] = stage.cache_status
        completed["tile_id"] = stage.tile_id
        summary["completed_jobs"].append(completed)
        completed_stage_outputs[stage.stage_name] = completed

    for stage in stages:
        if stage.stage_type in {"cached_tile", "context_density_tile"}:
            collect_cached_tile_stage(stage)

    train_stages = [stage for stage in stages if stage.stage_type == "train"]
    if args.orchestration_mode == "fanout" and args.wait:
        for batch in fanout_execution_batches(train_stages, max_tile_concurrency=args.max_tile_concurrency):
            for stage in batch:
                submit_training_stage(stage)
            for stage in batch:
                collect_completed_training_stage(stage)
    else:
        for stage in train_stages:
            submit_training_stage(stage)

    review_stage = next((stage for stage in stages if stage.stage_type == "review"), None)
    if args.wait and args.orchestration_mode != "fanout":
        merge_root = Path(args.local_merge_output_dir) if args.local_merge_output_dir else None
        for stage in stages:
            if stage.stage_type != "train":
                continue
            collect_completed_training_stage(stage)

        if review_stage is not None:
            tiled_stage_output = completed_stage_outputs.get("T2_tiled_pipeline")
            if tiled_stage_output is None:
                raise RuntimeError("Quality review requires completed output for T2_tiled_pipeline")
            model_artifacts_s3_uri = str(tiled_stage_output.get("model_artifacts_s3_uri", "")).strip()
            if not model_artifacts_s3_uri:
                raise RuntimeError("Quality review requires the tiled pipeline model artifact S3 URI")

            review_job_name = sanitize_sagemaker_job_name(f"{args.job_prefix}-{timestamp}-quality")
            review_payload = create_quality_review_processing_payload(
                branch_name=branch_name,
                job_name=review_job_name,
                image_uri=context.image_uri,
                role_arn=context.role_arn,
                model_artifact_s3_uri=model_artifacts_s3_uri,
                colmap_s3_uri=colmap_s3_uri,
                output_s3_uri=review_stage.output_s3_uri,
                environment=review_stage.environment or {},
                instance_type=args.review_instance_type,
                volume_size_gb=args.review_volume_size_gb,
                max_runtime_seconds=args.review_max_runtime_seconds,
                review_camera_manifest_s3_uri=args.review_camera_manifest_s3_uri,
                baseline_review_manifest_s3_uri=args.v18_review_manifest_s3_uri
                or args.baseline_review_manifest_s3_uri,
            )
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
                json.dump(review_payload, handle, indent=2)
                handle.flush()
                payload_path = Path(handle.name)
            try:
                run_command(["aws", "sagemaker", "create-processing-job", "--cli-input-json", f"file://{payload_path}"])
            finally:
                payload_path.unlink(missing_ok=True)

            processing_status = wait_for_processing_job(review_job_name, poll_seconds=args.poll_seconds)
            review_manifest_s3_uri = f"{normalize_s3_prefix(review_stage.output_s3_uri)}/quality_review_manifest.json"
            review_manifest = load_s3_json(review_manifest_s3_uri)
            summary["quality_review"] = {
                "stage_name": review_stage.stage_name,
                "processing_job_name": review_job_name,
                "output_s3_uri": review_stage.output_s3_uri,
                "manifest_s3_uri": review_manifest_s3_uri,
                "processing_status": processing_status.get("ProcessingJobStatus"),
                "processing_start_time": processing_status.get("ProcessingStartTime"),
                "processing_end_time": processing_status.get("ProcessingEndTime"),
                "manifest": review_manifest,
            }
            summary["promotion_readiness"] = review_manifest.get("promotion_readiness")

        if merge_root is not None and not args.skip_merge and extracted_stage_dirs:
            local_tile_manifest_path = merge_root / "3dgs_tile_manifest.json"
            local_tile_manifest_path.write_text(json.dumps(tile_manifest, indent=2), encoding="utf-8")
            merge_summary = run_merge_stage(
                tile_manifest={
                    **tile_manifest,
                    "tiles": [
                        dict(tile)
                        for tile in tile_manifest.get("tiles", [])
                        if str(tile.get("tile_id")) in set(selected_tiles)
                    ],
                },
                tile_stage_dirs=extracted_stage_dirs,
                output_dir=merge_root / "merged",
                merge_mode=args.merge_mode,
            )
            summary["merge"] = merge_summary
    elif args.wait and merge_root is not None and not args.skip_merge and extracted_stage_dirs:
        local_tile_manifest_path = merge_root / "3dgs_tile_manifest.json"
        local_tile_manifest_path.write_text(json.dumps(tile_manifest, indent=2), encoding="utf-8")
        merge_summary = run_merge_stage(
            tile_manifest={
                **tile_manifest,
                "tiles": [
                    dict(tile)
                    for tile in tile_manifest.get("tiles", [])
                    if str(tile.get("tile_id")) in set(selected_tiles)
                ],
            },
            tile_stage_dirs=extracted_stage_dirs,
            output_dir=merge_root / "merged",
            merge_mode=args.merge_mode,
        )
        summary["merge"] = merge_summary
    elif review_stage is not None:
        summary["quality_review"] = {
            "stage_name": review_stage.stage_name,
            "planned_output_s3_uri": review_stage.output_s3_uri,
            "planned_environment": review_stage.environment or {},
            "requires_wait": True,
        }

    print(json.dumps(summary, indent=2))
    if args.summary_json_output:
        Path(args.summary_json_output).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
