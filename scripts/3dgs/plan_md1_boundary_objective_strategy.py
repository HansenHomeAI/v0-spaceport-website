#!/usr/bin/env python3
"""Plan and gate the next MD1 boundary-objective retry."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


BOUNDARY_BLOCKER = "boundary_no_required_improvement"
HORIZON_SSIM_BLOCKER = "horizon_ssim_regression"
APPROVED_OBJECTIVE_TERMS = (
    "boundary_camera_weighting",
    "boundary_loss_weighting",
    "camera_weighting",
    "frozen_camera_weighting",
    "visibility_weighted_camera_sampling",
    "tile04_tile10_joint_objective",
    "tile_04_tile_10_joint_objective",
    "boundary_visibility_weighting",
    "perceptual_loss_weighting",
    "lpips_loss_weighting",
    "appearance_consistency",
    "color_consistency",
    "horizon_appearance_protection",
)
FAILED_DENSITY_OR_MERGE_TERMS = (
    "density_only",
    "more_density",
    "more_splats",
    "tile10_density",
    "tile_10_density",
    "protected_overlap",
    "retain_overlap",
    "merge_only",
    "retention_only",
)
FAILED_DENSITY_CAP_TERMS = (
    "density_cap",
    "density_capped",
    "hard_cap",
    "output_cap",
)
QUALITY_PRESERVING_DENSITY_TERMS = (
    "density_preserving",
    "density_restoring",
    "density_recovery",
    "soft_density_control",
    "horizon_preserving",
    "quality_preserving",
)
FAILED_SOFT_DENSITY_TERMS = (
    "soft_density",
    "soft_density_control",
    "global_ssim_loss_weighting",
    "ssim_lambda_0_28",
)
FAILED_HARD_OUTPUT_CAP_VISUAL_FIDELITY_TERMS = (
    "hard_output_cap",
    "hard_output_density_cap",
    "output_cap",
    "opacity_topk",
)
QUALITY_REPAIR_AFTER_HARDCAP_TERMS = (
    "anti_magenta",
    "color_calibration",
    "exposure_calibration",
    "geometry_alignment_loss",
    "per_camera_color",
    "perceptual_color_loss",
    "photometric_calibration",
    "render_color_normalization",
    "sky_mask",
    "white_balance",
)
QUALITY_REPAIR_AFTER_HARDCAP_ENV_KEYS = (
    "BILATERAL_PROCESSING",
    "FLOATER_PRUNING_MAX_COLOR_DISTANCE",
)
QUALITY_REPAIR_AFTER_HARDCAP_CONFIG_KEYS = (
    "bilateral_processing",
    "floater_pruning_max_color_distance",
)
VISUAL_FIDELITY_OBJECTIVE_TERMS = (
    "appearance",
    "color",
    "exposure",
    "geometry",
    "perceptual",
    "lpips",
    "sky",
    "horizon_continuity",
    "texture",
)
FAILED_FRAME_REPEAT_TERMS = (
    "boundary_frame_repeat",
    "camera_repeat",
    "repeat_weighting",
    "repeat_factor",
)
LOSS_WEIGHTING_TERMS = (
    "loss_weight",
    "loss_weighting",
    "boundary_loss",
    "photometric_loss",
    "ssim_loss",
    "lpips_loss",
)
LOSS_WEIGHTING_ENV_KEYS = (
    "SSIM_LAMBDA",
)
LOSS_WEIGHTING_CONFIG_KEYS = (
    "ssim_lambda",
)
VISUAL_FIDELITY_ENV_KEYS = (
    "APPEARANCE_EMBED_DIM",
    "BG_SH_DEGREE",
    "SH_DEGREE",
    "ENABLE_BG_MODEL",
    "ENABLE_ALPHA_LOSS",
    "ENABLE_ROBUST_MASK",
    "BILATERAL_PROCESSING",
    "MODEL_VARIANT",
)
VISUAL_FIDELITY_CONFIG_KEYS = (
    "appearance_embed_dim",
    "bg_sh_degree",
    "sh_degree",
    "enable_bg_model",
    "enable_alpha_loss",
    "enable_robust_mask",
    "bilateral_processing",
    "model_variant",
)
DENSITY_CONTROL_ENV_KEYS = (
    "TRAINING_MAX_GAUSS_RATIO",
    "TRAINING_STOP_SPLIT_AT",
    "CULL_ALPHA_THRESH",
    "CULL_SCALE_THRESH",
    "TRAINING_DENSITY_CAP_ENABLED",
    "TRAINING_MAX_OUTPUT_GAUSSIANS",
    "TRAINING_DENSITY_CAP_POLICY",
)
DENSITY_CONTROL_CONFIG_KEYS = (
    "training_max_gauss_ratio",
    "training_stop_split_at",
    "cull_alpha_thresh",
    "cull_scale_thresh",
    "density_cap_enabled",
    "max_output_gaussians",
    "density_cap_policy",
)
UNDERDENSE_REPAIR_ENV_KEYS = (
    "MAX_ITERATIONS",
    "TRAINING_MAX_SELECTED_IMAGES",
    "TRAINING_STOP_SPLIT_AT",
)
UNDERDENSE_REPAIR_CONFIG_KEYS = (
    "max_iterations",
    "training_max_selected_images",
    "training_stop_split_at",
)
SCAFFOLD_REPAIR_ENV_KEYS = (
    "GLOBAL_SCAFFOLD_SOURCE_DIR",
    "GLOBAL_SCAFFOLD_INIT_MAX_POINTS",
    "GLOBAL_SCAFFOLD_REQUIRE_FILTERED_INIT",
    "TILED_INCLUDE_SCAFFOLD",
)
SCAFFOLD_REPAIR_CONFIG_KEYS = (
    "global_scaffold_source_dir",
    "global_scaffold_init_max_points",
    "tiled_include_scaffold",
    "scaffold_artifact_s3_uri",
)
OVERDENSE_LEAF_REASONS = (
    "splat_vertex_count_above_reference_ratio",
    "splat_vertex_count_above_hard_max",
)
UNDERDENSE_LEAF_REASONS = (
    "splat_vertex_count_below_reference_ratio",
    "splat_vertex_count_below_hard_min",
)
LEAF_ARTIFACT_STRUCTURE_REASONS = (
    "leaf_required_paths_missing",
)
LEAF_DENSITY_REASONS = OVERDENSE_LEAF_REASONS + UNDERDENSE_LEAF_REASONS
LEAF_GATE_REASONS = LEAF_DENSITY_REASONS + LEAF_ARTIFACT_STRUCTURE_REASONS
REQUIRED_LEAF_SIDECARS = (
    "export_manifest.json",
    "background_manifest.json",
    "background_skybox.webp",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def list_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def split_label_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return list_strings(value)
    if not isinstance(value, str):
        return []
    result: list[str] = []
    for item in value.replace(";", ",").split(","):
        cleaned = item.strip()
        if cleaned:
            result.append(cleaned)
    return result


def ordered_unique(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = str(item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def sorted_unique(items: Sequence[str]) -> list[str]:
    return sorted(set(item for item in items if item))


def strategy_values(
    strategy: Mapping[str, Any] | None,
    direct_keys: tuple[str, ...],
    env_keys: tuple[str, ...] = (),
) -> list[str]:
    if not strategy:
        return []
    values: list[str] = []
    for key in direct_keys:
        values.extend(split_label_list(strategy.get(key)))
    nested = strategy.get("quality_strategy")
    if isinstance(nested, Mapping):
        for key in direct_keys:
            values.extend(split_label_list(nested.get(key)))
    stages = strategy.get("stages")
    if isinstance(stages, list):
        for stage in stages:
            if not isinstance(stage, Mapping):
                continue
            if stage.get("tile_id"):
                if "tile_id" in direct_keys:
                    values.append(str(stage["tile_id"]))
            env = stage.get("environment")
            if not isinstance(env, Mapping):
                continue
            for key in env_keys:
                values.extend(split_label_list(env.get(key)))
    return sorted_unique(values)


def selected_tile_ids(strategy: Mapping[str, Any] | None) -> list[str]:
    values = strategy_values(strategy, ("selected_tile_ids", "tile_ids", "tile_id"), ("TILE_IDS", "TILE_ID"))
    if strategy and isinstance(strategy.get("planned_tiles"), list):
        for tile in strategy["planned_tiles"]:
            if isinstance(tile, Mapping) and tile.get("tile_id"):
                values.append(str(tile["tile_id"]))
    return sorted_unique(values)


def context_tile_ids(strategy: Mapping[str, Any] | None) -> list[str]:
    return strategy_values(
        strategy,
        (
            "context_support_tile_ids",
            "reuse_context_tile_ids",
            "source_context_tile_ids",
            "protected_context_tile_ids",
        ),
        (
            "CONTEXT_SUPPORT_TILE_IDS",
            "REUSE_CONTEXT_TILE_IDS",
            "SOURCE_CONTEXT_TILE_IDS",
            "PROTECTED_CONTEXT_TILE_IDS",
        ),
    )


def targeted_blockers(strategy: Mapping[str, Any] | None) -> list[str]:
    return strategy_values(
        strategy,
        ("targeted_quality_blockers", "targeted_quality_block_reasons"),
        ("TARGETED_QUALITY_BLOCKERS", "TARGETED_QUALITY_BLOCK_REASONS"),
    )


def boundary_cameras(strategy: Mapping[str, Any] | None) -> list[str]:
    return strategy_values(
        strategy,
        ("boundary_camera_ids", "boundary_frozen_cameras"),
        ("BOUNDARY_CAMERA_IDS", "BOUNDARY_FROZEN_CAMERAS"),
    )


def horizon_cameras(strategy: Mapping[str, Any] | None) -> list[str]:
    return strategy_values(
        strategy,
        ("horizon_camera_ids", "horizon_frozen_cameras"),
        ("HORIZON_CAMERA_IDS", "HORIZON_FROZEN_CAMERAS"),
    )


def expected_metric_axes(strategy: Mapping[str, Any] | None) -> list[str]:
    return strategy_values(
        strategy,
        ("expected_metric_axes", "expected_metric_axis"),
        ("EXPECTED_METRIC_AXES", "EXPECTED_METRIC_AXIS"),
    )


def objective_changes(strategy: Mapping[str, Any] | None) -> list[str]:
    return strategy_values(
        strategy,
        (
            "objective_changes",
            "training_objective_changes",
            "camera_weighting_strategy",
            "loss_weighting_strategy",
            "sampling_strategy",
            "hypothesis",
        ),
        (
            "OBJECTIVE_CHANGES",
            "TRAINING_OBJECTIVE_CHANGES",
            "CAMERA_WEIGHTING_STRATEGY",
            "LOSS_WEIGHTING_STRATEGY",
            "SAMPLING_STRATEGY",
            "HYPOTHESIS",
        ),
    )


def objective_implementation(strategy: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(strategy, Mapping):
        return {"environment": {}, "training_config": {}}

    environment: dict[str, str] = {}
    training_config: dict[str, Any] = {}
    direct_environment = strategy.get("environment")
    if isinstance(direct_environment, Mapping):
        environment.update({str(key): str(value) for key, value in direct_environment.items()})
    direct_training_config = strategy.get("training_config")
    if isinstance(direct_training_config, Mapping):
        training_config.update(dict(direct_training_config))

    nested = strategy.get("objective_implementation")
    if isinstance(nested, Mapping):
        nested_environment = nested.get("environment")
        if isinstance(nested_environment, Mapping):
            environment.update({str(key): str(value) for key, value in nested_environment.items()})
        nested_training_config = nested.get("training_config")
        if isinstance(nested_training_config, Mapping):
            training_config.update(dict(nested_training_config))

    stages = strategy.get("stages")
    if isinstance(stages, list):
        for stage in stages:
            if not isinstance(stage, Mapping):
                continue
            stage_environment = stage.get("environment")
            if isinstance(stage_environment, Mapping):
                environment.update({str(key): str(value) for key, value in stage_environment.items()})

    return {"environment": environment, "training_config": training_config}


def stage_environments(strategy: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not isinstance(strategy, Mapping):
        return []
    environments: list[dict[str, str]] = []
    direct_environment = strategy.get("environment")
    if isinstance(direct_environment, Mapping):
        environments.append({str(key): str(value) for key, value in direct_environment.items()})
    nested = strategy.get("objective_implementation")
    if isinstance(nested, Mapping):
        nested_environment = nested.get("environment")
        if isinstance(nested_environment, Mapping):
            environments.append({str(key): str(value) for key, value in nested_environment.items()})
    stages = strategy.get("stages")
    if isinstance(stages, list):
        for stage in stages:
            if not isinstance(stage, Mapping):
                continue
            stage_environment = stage.get("environment")
            if isinstance(stage_environment, Mapping):
                environments.append({str(key): str(value) for key, value in stage_environment.items()})
    return environments


def sagemaker_env_value_length_violations(strategy: Mapping[str, Any] | None, *, max_length: int = 512) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for index, environment in enumerate(stage_environments(strategy)):
        for key, value in environment.items():
            if len(value) > max_length:
                violations.append({"environment_index": index, "key": key, "length": len(value), "max_length": max_length})
    return violations


def has_leaf_sidecar_export_implementation(strategy: Mapping[str, Any] | None) -> bool:
    if not isinstance(strategy, Mapping):
        return False
    implementation = objective_implementation(strategy)
    environment = implementation["environment"]
    training_config = implementation["training_config"]
    model_variant = str(environment.get("MODEL_VARIANT") or training_config.get("model_variant") or "").lower()
    if model_variant.startswith("splatfacto-w"):
        return True
    artifact_plan = strategy.get("leaf_artifact_plan")
    if isinstance(artifact_plan, Mapping):
        required_paths = list_strings(artifact_plan.get("required_paths"))
        if all(path in required_paths for path in REQUIRED_LEAF_SIDECARS):
            return True
        if all(artifact_plan.get(key) is True for key in ("export_manifest", "background_manifest", "background_skybox")):
            return True
    return False


def hard_output_cap_below_failed_minimums(
    density_control_knobs: Mapping[str, Any],
    failed_hypotheses: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    env = density_control_knobs.get("environment")
    if not isinstance(env, Mapping):
        env = {}
    config = density_control_knobs.get("training_config")
    if not isinstance(config, Mapping):
        config = {}
    candidate_output_cap = float_value(env.get("TRAINING_MAX_OUTPUT_GAUSSIANS") or config.get("max_output_gaussians"))
    if candidate_output_cap is None:
        return []
    violations: list[dict[str, Any]] = []
    for failure in underdense_output_cap_failures(failed_hypotheses):
        hard_min = float_value(failure.get("hard_min_splat_count"))
        if hard_min is not None and candidate_output_cap < hard_min:
            violations.append(
                {
                    "tile_id": failure.get("tile_id"),
                    "candidate_output_cap": int(candidate_output_cap),
                    "hard_min_splat_count": int(hard_min),
                }
            )
    return violations


def has_loss_weighting_change(changes: Sequence[str]) -> bool:
    normalized = " ".join(changes).lower()
    return any(term in normalized for term in LOSS_WEIGHTING_TERMS)


def implemented_loss_weighting_knobs(strategy: Mapping[str, Any] | None) -> dict[str, Any]:
    implementation = objective_implementation(strategy)
    environment = implementation["environment"]
    training_config = implementation["training_config"]
    env_knobs = {key: environment[key] for key in LOSS_WEIGHTING_ENV_KEYS if key in environment}
    config_knobs = {key: training_config[key] for key in LOSS_WEIGHTING_CONFIG_KEYS if key in training_config}
    return {"environment": env_knobs, "training_config": config_knobs}


def implemented_density_control_knobs(strategy: Mapping[str, Any] | None) -> dict[str, Any]:
    implementation = objective_implementation(strategy)
    environment = implementation["environment"]
    training_config = implementation["training_config"]
    env_knobs = {key: environment[key] for key in DENSITY_CONTROL_ENV_KEYS if key in environment}
    config_knobs = {key: training_config[key] for key in DENSITY_CONTROL_CONFIG_KEYS if key in training_config}
    return {"environment": env_knobs, "training_config": config_knobs}


def implemented_visual_fidelity_knobs(strategy: Mapping[str, Any] | None) -> dict[str, Any]:
    implementation = objective_implementation(strategy)
    environment = implementation["environment"]
    training_config = implementation["training_config"]
    env_knobs = {key: environment[key] for key in VISUAL_FIDELITY_ENV_KEYS if key in environment}
    config_knobs = {key: training_config[key] for key in VISUAL_FIDELITY_CONFIG_KEYS if key in training_config}
    return {"environment": env_knobs, "training_config": config_knobs}


def implemented_hardcap_quality_repair_knobs(strategy: Mapping[str, Any] | None) -> dict[str, Any]:
    implementation = objective_implementation(strategy)
    environment = implementation["environment"]
    training_config = implementation["training_config"]
    env_knobs = {key: environment[key] for key in QUALITY_REPAIR_AFTER_HARDCAP_ENV_KEYS if key in environment}
    config_knobs = {key: training_config[key] for key in QUALITY_REPAIR_AFTER_HARDCAP_CONFIG_KEYS if key in training_config}
    return {"environment": env_knobs, "training_config": config_knobs}


def float_value(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def estimated_usd(strategy: Mapping[str, Any] | None) -> float | None:
    if not strategy:
        return None
    cost = strategy.get("planned_cost_estimate")
    if not isinstance(cost, Mapping):
        cost = strategy.get("cost_estimate")
    if not isinstance(cost, Mapping):
        return None
    for key in ("estimated_usd", "worst_case_usd"):
        if cost.get(key) is not None:
            try:
                return float(cost[key])
            except (TypeError, ValueError):
                return None
    return None


def no_full_14tile_training_confirmed(strategy: Mapping[str, Any] | None) -> bool:
    if not strategy:
        return False
    if strategy.get("no_full_14tile_training") is True:
        return True
    if strategy.get("full_14tile_training_launched") is False:
        return True
    tiles = selected_tile_ids(strategy)
    return 0 < len(tiles) < 14


def current_quality_blockers(
    quality_strategy: Mapping[str, Any],
    responsible_tiles: Mapping[str, Any],
    attribution: Mapping[str, Any],
) -> list[str]:
    values = list_strings(quality_strategy.get("current_quality_blockers"))
    values.extend(list_strings(responsible_tiles.get("current_quality_blockers")))
    values.extend(list_strings(attribution.get("promotion_block_reasons")))
    tested_candidate = attribution.get("tested_candidate")
    if isinstance(tested_candidate, Mapping):
        values.extend(list_strings(tested_candidate.get("promotion_block_reasons")))
        values.extend(list_strings(tested_candidate.get("visual_qa_block_reasons")))
    block_reasons = attribution.get("block_reasons")
    if isinstance(block_reasons, Mapping):
        values.extend(list_strings(block_reasons.get("protected")))
        values.extend(reason for reason in list_strings(block_reasons.get("leaf_gate")) if reason in LEAF_GATE_REASONS)
    values.extend(reason for reason in list_strings(attribution.get("leaf_gate_block_reasons")) if reason in LEAF_GATE_REASONS)
    values.extend(reason for reason in list_strings(attribution.get("merge_review_block_reasons")) if reason in LEAF_GATE_REASONS)
    paid_jobs = attribution.get("paid_jobs")
    if isinstance(paid_jobs, list):
        for job in paid_jobs:
            if not isinstance(job, Mapping):
                continue
            values.extend(reason for reason in list_strings(job.get("block_reasons")) if reason in LEAF_GATE_REASONS)
    values.extend(list_strings(attribution.get("visual_qa_gate_block_reasons")))
    values.extend(list_strings(attribution.get("ai_visual_defect_blockers")))
    return sorted_unique(values)


def overdense_leaf_records(attribution: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    leaf_gate_block_reasons = list_strings(attribution.get("leaf_gate_block_reasons"))
    block_reasons = attribution.get("block_reasons")
    failed_density_env = attribution.get("failed_density_control_environment")
    if not isinstance(failed_density_env, Mapping):
        failed_density_env = {}
    failed_density_config = attribution.get("failed_density_control_training_config")
    if not isinstance(failed_density_config, Mapping):
        failed_density_config = {}
    if isinstance(block_reasons, Mapping):
        leaf_gate_block_reasons.extend(list_strings(block_reasons.get("leaf_gate")))
    if any(reason in leaf_gate_block_reasons for reason in OVERDENSE_LEAF_REASONS):
        records.append(
            {
                "tile_id": attribution.get("tile_id"),
                "leaf_gate_block_reasons": sorted_unique(leaf_gate_block_reasons),
                "splat_vertex_count": attribution.get("splat_vertex_count"),
                "reference_splat_count": attribution.get("reference_splat_count"),
                "observed_reference_ratio": attribution.get("observed_reference_ratio"),
                "hard_max_splat_count": attribution.get("hard_max_splat_count"),
                "density_control_environment": dict(failed_density_env),
                "density_control_training_config": dict(failed_density_config),
            }
        )
    paid_jobs = attribution.get("paid_jobs")
    if isinstance(paid_jobs, list):
        for job in paid_jobs:
            if not isinstance(job, Mapping):
                continue
            job_reasons = list_strings(job.get("block_reasons"))
            if any(reason in job_reasons for reason in OVERDENSE_LEAF_REASONS):
                job_density_env = job.get("density_control_environment")
                if not isinstance(job_density_env, Mapping):
                    job_density_env = failed_density_env
                job_density_config = job.get("density_control_training_config")
                if not isinstance(job_density_config, Mapping):
                    job_density_config = failed_density_config
                records.append(
                    {
                        "tile_id": job.get("tile_id"),
                        "leaf_gate_block_reasons": sorted_unique(job_reasons),
                        "splat_vertex_count": job.get("splat_vertex_count"),
                        "reference_splat_count": job.get("reference_splat_count"),
                        "observed_reference_ratio": job.get("observed_reference_ratio"),
                        "hard_max_splat_count": job.get("hard_max_splat_count"),
                        "density_control_environment": dict(job_density_env),
                        "density_control_training_config": dict(job_density_config),
                    }
                )
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for record in records:
        key = (
            record.get("tile_id"),
            tuple(record.get("leaf_gate_block_reasons", [])),
            record.get("splat_vertex_count"),
            record.get("reference_splat_count"),
            record.get("hard_max_splat_count"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def underdense_leaf_records(attribution: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    leaf_gate_block_reasons = list_strings(attribution.get("leaf_gate_block_reasons"))
    block_reasons = attribution.get("block_reasons")
    failed_density_env = attribution.get("failed_density_control_environment")
    if not isinstance(failed_density_env, Mapping):
        failed_density_env = {}
    failed_density_config = attribution.get("failed_density_control_training_config")
    if not isinstance(failed_density_config, Mapping):
        failed_density_config = {}
    if isinstance(block_reasons, Mapping):
        leaf_gate_block_reasons.extend(list_strings(block_reasons.get("leaf_gate")))
    if any(reason in leaf_gate_block_reasons for reason in UNDERDENSE_LEAF_REASONS):
        records.append(
            {
                "tile_id": attribution.get("tile_id"),
                "leaf_gate_block_reasons": sorted_unique(leaf_gate_block_reasons),
                "splat_vertex_count": attribution.get("splat_vertex_count"),
                "reference_splat_count": attribution.get("reference_splat_count"),
                "observed_reference_ratio": attribution.get("observed_reference_ratio"),
                "hard_min_splat_count": attribution.get("hard_min_splat_count"),
                "density_control_environment": dict(failed_density_env),
                "density_control_training_config": dict(failed_density_config),
            }
        )
    paid_jobs = attribution.get("paid_jobs")
    if isinstance(paid_jobs, list):
        for job in paid_jobs:
            if not isinstance(job, Mapping):
                continue
            job_reasons = list_strings(job.get("block_reasons"))
            if any(reason in job_reasons for reason in UNDERDENSE_LEAF_REASONS):
                job_density_env = job.get("density_control_environment")
                if not isinstance(job_density_env, Mapping):
                    job_density_env = failed_density_env
                job_density_config = job.get("density_control_training_config")
                if not isinstance(job_density_config, Mapping):
                    job_density_config = failed_density_config
                records.append(
                    {
                        "tile_id": job.get("tile_id"),
                        "leaf_gate_block_reasons": sorted_unique(job_reasons),
                        "splat_vertex_count": job.get("splat_vertex_count"),
                        "reference_splat_count": job.get("reference_splat_count"),
                        "observed_reference_ratio": job.get("observed_reference_ratio"),
                        "hard_min_splat_count": job.get("hard_min_splat_count"),
                        "density_control_environment": dict(job_density_env),
                        "density_control_training_config": dict(job_density_config),
                    }
                )
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for record in records:
        key = (
            record.get("tile_id"),
            tuple(record.get("leaf_gate_block_reasons", [])),
            record.get("splat_vertex_count"),
            record.get("reference_splat_count"),
            record.get("hard_min_splat_count"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def extract_failed_hypotheses(attribution: Mapping[str, Any]) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    density_delta = attribution.get("density_v2_minus_baseline_bucket_delta")
    if isinstance(density_delta, Mapping):
        failed.append(
            {
                "hypothesis": "tile10_density_v2",
                "status": "failed",
                "evidence": "Increasing tile_10 retained density did not fix boundary quality.",
                "metric_delta_vs_rollback_bg10": density_delta,
            }
        )
    protected_merge_delta = attribution.get("protected_minus_baseline_merge_delta")
    protected_bucket_delta = attribution.get("protected_minus_baseline_bucket_delta")
    if isinstance(protected_merge_delta, Mapping) or isinstance(protected_bucket_delta, Mapping):
        failed.append(
            {
                "hypothesis": "protected_overlap_retention",
                "status": "failed",
                "evidence": "Retaining extra overlap splats changed merge counts but not frozen rendered metrics.",
                "merge_delta_vs_rollback_bg10": protected_merge_delta if isinstance(protected_merge_delta, Mapping) else {},
                "bucket_delta_vs_rollback_bg10": protected_bucket_delta if isinstance(protected_bucket_delta, Mapping) else {},
            }
        )
    camera_weighting_delta = (
        attribution.get("camera_weighting_minus_reference_bucket_delta")
        or attribution.get("camera_weighting_minus_baseline_bucket_delta")
        or attribution.get("camera_repeat_minus_reference_bucket_delta")
    )
    if isinstance(camera_weighting_delta, Mapping):
        failed.append(
            {
                "hypothesis": "boundary_frame_repeat_weighting",
                "status": "failed",
                "evidence": "Repeating frozen boundary cameras changed the tile_04 leaf but did not improve the frozen boundary gate and introduced horizon PSNR regression.",
                "metric_delta_vs_reference_bg10": camera_weighting_delta,
            }
        )
    density_capped_delta = attribution.get("density_capped_minus_reference_bucket_delta")
    if isinstance(density_capped_delta, Mapping):
        tested_candidate = attribution.get("tested_candidate")
        if not isinstance(tested_candidate, Mapping):
            tested_candidate = {}
        failed.append(
            {
                "hypothesis": "density_capped_loss_weighting_quality_regression",
                "status": "failed",
                "evidence": "The density-capped/loss-weighted tile_04 leaf passed density guards but worsened horizon, boundary LPIPS, and near-detail LPIPS versus the tile04 boundary+horizon bg10 reference.",
                "metric_delta_vs_reference_bg10": density_capped_delta,
                "promotion_block_reasons": list_strings(tested_candidate.get("promotion_block_reasons")),
                "v18_non_regression_block_reasons": list_strings(
                    tested_candidate.get("v18_non_regression_block_reasons")
                ),
            }
        )
    soft_density_delta = attribution.get("soft_density_minus_reference_bucket_delta") or attribution.get(
        "soft_density_minus_v18_bucket_delta"
    )
    if isinstance(soft_density_delta, Mapping):
        tested_candidate = attribution.get("tested_candidate")
        if not isinstance(tested_candidate, Mapping):
            tested_candidate = {}
        failed.append(
            {
                "hypothesis": "soft_density_quality_regression",
                "status": "failed",
                "evidence": "The soft-density tile_04 leaf passed density guards and structural merge/review gates, but V18 metrics and AI visual QA showed horizon/geometry/texture/color regressions.",
                "metric_delta_vs_reference_bg10": soft_density_delta,
                "promotion_block_reasons": list_strings(tested_candidate.get("promotion_block_reasons")),
                "v18_non_regression_block_reasons": list_strings(
                    tested_candidate.get("v18_non_regression_block_reasons")
                ),
                "visual_qa_gate_block_reasons": list_strings(attribution.get("visual_qa_gate_block_reasons")),
                "ai_visual_defect_blockers": list_strings(attribution.get("ai_visual_defect_blockers")),
            }
        )
    hard_output_cap_visual_delta = attribution.get("hard_output_cap_visual_fidelity_minus_v18_bucket_delta") or attribution.get(
        "hard_output_cap_visual_fidelity_minus_reference_bucket_delta"
    )
    if isinstance(hard_output_cap_visual_delta, Mapping):
        tested_candidate = attribution.get("tested_candidate")
        if not isinstance(tested_candidate, Mapping):
            tested_candidate = {}
        failed.append(
            {
                "hypothesis": "hard_output_cap_visual_fidelity_quality_regression",
                "status": "failed",
                "evidence": "The hard-output-cap tile_10 plus visual-fidelity tile_04 bg10 merge passed density and structural preflight, but V18 metrics and AI visual QA blocked it for false color, horizon, near-detail, and perceptual regressions.",
                "metric_delta_vs_v18": hard_output_cap_visual_delta,
                "promotion_block_reasons": list_strings(tested_candidate.get("promotion_block_reasons")),
                "v18_non_regression_block_reasons": list_strings(
                    tested_candidate.get("v18_non_regression_block_reasons")
                ),
                "visual_qa_gate_block_reasons": list_strings(attribution.get("visual_qa_gate_block_reasons")),
                "ai_visual_defect_blockers": list_strings(attribution.get("ai_visual_defect_blockers")),
            }
        )
    hypothesis_context = str(attribution.get("hypothesis", "")).lower()
    visual_fidelity_context = "visual_fidelity" in hypothesis_context
    stronger_density_context = (
        "stronger_density" in hypothesis_context
        or "stronger-density" in hypothesis_context
        or "hard_output_cap" in hypothesis_context
        or "vfdc3" in hypothesis_context
    )
    density_controlled_context = (
        "density_controlled" in hypothesis_context
        or "density-controlled" in hypothesis_context
        or stronger_density_context
        or "vfdc" in hypothesis_context
        or isinstance(attribution.get("failed_density_control_environment"), Mapping)
    )
    for overdense_record in overdense_leaf_records(attribution):
        hypothesis = "loss_weighting_overdense_leaf"
        evidence = "The previous loss-weighted tile_04 leaf completed but was rejected before merge/review because retained splats exceeded the reference-ratio hard max."
        if visual_fidelity_context or overdense_record.get("tile_id") == "tile_10":
            hypothesis = "visual_fidelity_tile10_overdense_leaf"
            evidence = "The visual-fidelity paired leaf proof improved the objective surface but tile_10 was rejected before merge/review because retained splats exceeded the density guard."
        if density_controlled_context and overdense_record.get("tile_id") == "tile_10":
            hypothesis = "density_controlled_visual_fidelity_tile10_overdense_leaf"
            evidence = "The density-controlled visual-fidelity tile_10 leaf reduced splat count but still exceeded the hard density guard, so the same density controls cannot be repeated."
        if stronger_density_context and overdense_record.get("tile_id") == "tile_10":
            hypothesis = "stronger_density_visual_fidelity_tile10_overdense_leaf"
            evidence = "The stronger split/culling visual-fidelity tile_10 leaf only made a small density improvement and still exceeded the hard density guard, so the next retry needs a hard exported-output cap."
        failed.append(
            {
                "hypothesis": hypothesis,
                "status": "failed",
                "evidence": evidence,
                "tile_id": overdense_record.get("tile_id"),
                "leaf_gate_block_reasons": overdense_record["leaf_gate_block_reasons"],
                "splat_vertex_count": overdense_record.get("splat_vertex_count"),
                "reference_splat_count": overdense_record.get("reference_splat_count"),
                "observed_reference_ratio": overdense_record.get("observed_reference_ratio"),
                "hard_max_splat_count": overdense_record.get("hard_max_splat_count"),
                "density_control_environment": overdense_record.get("density_control_environment", {}),
                "density_control_training_config": overdense_record.get("density_control_training_config", {}),
            }
        )
    for underdense_record in underdense_leaf_records(attribution):
        hypothesis = "leaf_output_cap_underdense_leaf"
        evidence = "The previous leaf proof was rejected before merge/review because retained splats fell below the post-leaf density guard."
        tile_id = underdense_record.get("tile_id")
        if tile_id == "tile_04" and "visual_sentinel" in hypothesis_context:
            failed_env = underdense_record.get("density_control_environment")
            if not isinstance(failed_env, Mapping):
                failed_env = {}
            failed_config = underdense_record.get("density_control_training_config")
            if not isinstance(failed_config, Mapping):
                failed_config = {}
            failed_output_cap = float_value(
                failed_env.get("TRAINING_MAX_OUTPUT_GAUSSIANS") or failed_config.get("max_output_gaussians")
            )
            if failed_output_cap is not None:
                hypothesis = "visual_sentinel_tile04_output_cap_underdense_leaf"
                evidence = "The R0 visual-sentinel tile_04 leaf inherited an output cap that forced retained splats below the tile_04 hard minimum before any merge/review."
            elif "filtered_scaffold_initialization_missing" in list_strings(underdense_record.get("leaf_gate_block_reasons")):
                hypothesis = "visual_sentinel_tile04_density_restored_underdense_leaf"
                evidence = "The R0 visual-sentinel tile_04 density-restored leaf increased iterations/images but still produced too few retained splats and lacked filtered scaffold initialization."
            else:
                hypothesis = "visual_sentinel_tile04_budget_underdense_leaf"
                evidence = "The R0 visual-sentinel tile_04 leaf removed the hard output cap and exported required sidecars, but the bounded training budget still produced too few retained splats before any merge/review."
        failed.append(
            {
                "hypothesis": hypothesis,
                "status": "failed",
                "evidence": evidence,
                "tile_id": tile_id,
                "leaf_gate_block_reasons": underdense_record["leaf_gate_block_reasons"],
                "splat_vertex_count": underdense_record.get("splat_vertex_count"),
                "reference_splat_count": underdense_record.get("reference_splat_count"),
                "observed_reference_ratio": underdense_record.get("observed_reference_ratio"),
                "hard_min_splat_count": underdense_record.get("hard_min_splat_count"),
                "density_control_environment": underdense_record.get("density_control_environment", {}),
                "density_control_training_config": underdense_record.get("density_control_training_config", {}),
            }
        )
    return failed


def has_approved_objective(changes: Sequence[str]) -> bool:
    normalized = " ".join(changes).lower()
    return any(term in normalized for term in APPROVED_OBJECTIVE_TERMS)


def repeats_failed_density_or_merge_only(changes: Sequence[str]) -> bool:
    if not changes:
        return False
    normalized = " ".join(changes).lower()
    return any(term in normalized for term in FAILED_DENSITY_OR_MERGE_TERMS) and not has_approved_objective(changes)


def repeats_failed_frame_repeat_without_loss(changes: Sequence[str]) -> bool:
    if not changes:
        return False
    normalized = " ".join(changes).lower()
    has_frame_repeat = any(term in normalized for term in FAILED_FRAME_REPEAT_TERMS)
    has_loss_weighting = any(term in normalized for term in LOSS_WEIGHTING_TERMS)
    return has_frame_repeat and not has_loss_weighting


def repeats_failed_density_cap(changes: Sequence[str], failed_hypotheses: Sequence[Mapping[str, Any]]) -> bool:
    if not changes:
        return False
    if not any(item.get("hypothesis") == "density_capped_loss_weighting_quality_regression" for item in failed_hypotheses):
        return False
    normalized = " ".join(changes).lower()
    has_hard_cap = any(term in normalized for term in FAILED_DENSITY_CAP_TERMS)
    has_quality_preserving_density = any(term in normalized for term in QUALITY_PRESERVING_DENSITY_TERMS)
    return has_hard_cap and not has_quality_preserving_density


def repeats_failed_soft_density(changes: Sequence[str], failed_hypotheses: Sequence[Mapping[str, Any]]) -> bool:
    if not changes:
        return False
    if not any(item.get("hypothesis") == "soft_density_quality_regression" for item in failed_hypotheses):
        return False
    normalized = " ".join(changes).lower()
    repeats_soft_density = any(term in normalized for term in FAILED_SOFT_DENSITY_TERMS)
    adds_visual_fidelity_objective = any(term in normalized for term in VISUAL_FIDELITY_OBJECTIVE_TERMS)
    return repeats_soft_density and not adds_visual_fidelity_objective


def has_soft_density_failed(failed_hypotheses: Sequence[Mapping[str, Any]]) -> bool:
    return any(item.get("hypothesis") == "soft_density_quality_regression" for item in failed_hypotheses)


def has_hardcap_visual_quality_failed(failed_hypotheses: Sequence[Mapping[str, Any]]) -> bool:
    return any(item.get("hypothesis") == "hard_output_cap_visual_fidelity_quality_regression" for item in failed_hypotheses)


def underdense_output_cap_failures(failed_hypotheses: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [
        item
        for item in failed_hypotheses
        if item.get("hypothesis")
        in (
            "leaf_output_cap_underdense_leaf",
            "visual_sentinel_tile04_output_cap_underdense_leaf",
        )
    ]


def visual_sentinel_budget_underdense_failures(
    failed_hypotheses: Sequence[Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    return [
        item
        for item in failed_hypotheses
        if item.get("hypothesis") == "visual_sentinel_tile04_budget_underdense_leaf"
    ]


def visual_sentinel_density_restored_underdense_failures(
    failed_hypotheses: Sequence[Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    return [
        item
        for item in failed_hypotheses
        if item.get("hypothesis") == "visual_sentinel_tile04_density_restored_underdense_leaf"
    ]


def underdense_density_restoration_implementation(
    strategy: Mapping[str, Any] | None,
    failed_hypotheses: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    implementation = objective_implementation(strategy)
    environment = implementation["environment"]
    training_config = implementation["training_config"]
    env_knobs = {key: environment[key] for key in UNDERDENSE_REPAIR_ENV_KEYS if key in environment}
    config_knobs = {key: training_config[key] for key in UNDERDENSE_REPAIR_CONFIG_KEYS if key in training_config}
    comparisons: list[dict[str, Any]] = []
    stronger_budget = False
    for failure in visual_sentinel_budget_underdense_failures(failed_hypotheses):
        failed_env = failure.get("density_control_environment")
        if not isinstance(failed_env, Mapping):
            failed_env = {}
        failed_config = failure.get("density_control_training_config")
        if not isinstance(failed_config, Mapping):
            failed_config = {}
        candidate_iterations = float_value(environment.get("MAX_ITERATIONS") or training_config.get("max_iterations"))
        failed_iterations = float_value(failed_env.get("MAX_ITERATIONS") or failed_config.get("max_iterations"))
        candidate_images = float_value(
            environment.get("TRAINING_MAX_SELECTED_IMAGES") or training_config.get("training_max_selected_images")
        )
        failed_images = float_value(
            failed_env.get("TRAINING_MAX_SELECTED_IMAGES") or failed_config.get("training_max_selected_images")
        )
        candidate_stop_split = float_value(
            environment.get("TRAINING_STOP_SPLIT_AT") or training_config.get("training_stop_split_at")
        )
        failed_stop_split = float_value(
            failed_env.get("TRAINING_STOP_SPLIT_AT") or failed_config.get("training_stop_split_at")
        )
        improved = {
            "max_iterations_increased": (
                candidate_iterations is not None
                and failed_iterations is not None
                and candidate_iterations > failed_iterations
            ),
            "selected_images_increased": (
                candidate_images is not None and failed_images is not None and candidate_images > failed_images
            ),
            "split_stop_delayed": (
                candidate_stop_split is not None
                and failed_stop_split is not None
                and candidate_stop_split > failed_stop_split
            ),
        }
        stronger_budget = stronger_budget or any(improved.values())
        comparisons.append(
            {
                "tile_id": failure.get("tile_id"),
                "failed": {
                    "max_iterations": failed_iterations,
                    "training_max_selected_images": failed_images,
                    "training_stop_split_at": failed_stop_split,
                },
                "candidate": {
                    "max_iterations": candidate_iterations,
                    "training_max_selected_images": candidate_images,
                    "training_stop_split_at": candidate_stop_split,
                },
                "improved": improved,
            }
        )
    return {
        "environment": env_knobs,
        "training_config": config_knobs,
        "has_stronger_density_budget": stronger_budget,
        "comparisons": comparisons,
    }


def scaffold_density_restoration_implementation(strategy: Mapping[str, Any] | None) -> dict[str, Any]:
    implementation = objective_implementation(strategy)
    environment = implementation["environment"]
    training_config = implementation["training_config"]
    env_knobs = {key: environment[key] for key in SCAFFOLD_REPAIR_ENV_KEYS if key in environment}
    config_knobs = {key: training_config[key] for key in SCAFFOLD_REPAIR_CONFIG_KEYS if key in training_config}
    top_level_artifact = ""
    if isinstance(strategy, Mapping):
        top_level_artifact = str(strategy.get("scaffold_artifact_s3_uri") or "").strip()
    source_dir = str(environment.get("GLOBAL_SCAFFOLD_SOURCE_DIR") or training_config.get("global_scaffold_source_dir") or "").strip()
    artifact = str(training_config.get("scaffold_artifact_s3_uri") or top_level_artifact).strip()
    include_scaffold = str(
        environment.get("TILED_INCLUDE_SCAFFOLD")
        or training_config.get("tiled_include_scaffold")
        or ("true" if source_dir or artifact else "")
    ).lower() in ("1", "true", "yes")
    return {
        "environment": env_knobs,
        "training_config": config_knobs,
        "scaffold_artifact_s3_uri": artifact,
        "has_scaffold_restoration": include_scaffold and bool(source_dir or artifact),
    }


def has_underdense_leaf_blocker(blockers: Sequence[str]) -> bool:
    return any(reason in blockers for reason in UNDERDENSE_LEAF_REASONS)


def has_leaf_artifact_structure_blocker(blockers: Sequence[str]) -> bool:
    return any(reason in blockers for reason in LEAF_ARTIFACT_STRUCTURE_REASONS)


def repeats_failed_hardcap_visual_without_quality_repair(
    changes: Sequence[str],
    failed_hypotheses: Sequence[Mapping[str, Any]],
) -> bool:
    if not changes or not has_hardcap_visual_quality_failed(failed_hypotheses):
        return False
    normalized = " ".join(changes).lower()
    repeats_hardcap_visual = any(term in normalized for term in FAILED_HARD_OUTPUT_CAP_VISUAL_FIDELITY_TERMS) and any(
        term in normalized for term in VISUAL_FIDELITY_OBJECTIVE_TERMS
    )
    adds_new_quality_repair = any(term in normalized for term in QUALITY_REPAIR_AFTER_HARDCAP_TERMS)
    return repeats_hardcap_visual and not adds_new_quality_repair


def repeats_failed_hardcap_visual(changes: Sequence[str], failed_hypotheses: Sequence[Mapping[str, Any]]) -> bool:
    if not changes or not has_hardcap_visual_quality_failed(failed_hypotheses):
        return False
    normalized = " ".join(changes).lower()
    return any(term in normalized for term in FAILED_HARD_OUTPUT_CAP_VISUAL_FIDELITY_TERMS) and any(
        term in normalized for term in VISUAL_FIDELITY_OBJECTIVE_TERMS
    )


def has_visual_fidelity_overdense_failed(failed_hypotheses: Sequence[Mapping[str, Any]]) -> bool:
    return any(
        item.get("hypothesis")
        in (
            "visual_fidelity_tile10_overdense_leaf",
            "density_controlled_visual_fidelity_tile10_overdense_leaf",
            "stronger_density_visual_fidelity_tile10_overdense_leaf",
        )
        for item in failed_hypotheses
    )


def density_controlled_visual_fidelity_failures(
    failed_hypotheses: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    return [
        item
        for item in failed_hypotheses
        if item.get("hypothesis") == "density_controlled_visual_fidelity_tile10_overdense_leaf"
    ]


def stronger_density_visual_fidelity_failures(
    failed_hypotheses: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    return [
        item
        for item in failed_hypotheses
        if item.get("hypothesis") == "stronger_density_visual_fidelity_tile10_overdense_leaf"
    ]


def has_hard_output_density_cap(
    density_control_knobs: Mapping[str, Any],
    failed_hypotheses: Sequence[Mapping[str, Any]],
) -> bool:
    env = density_control_knobs.get("environment")
    if not isinstance(env, Mapping):
        env = {}
    config = density_control_knobs.get("training_config")
    if not isinstance(config, Mapping):
        config = {}
    candidate_output_cap = float_value(env.get("TRAINING_MAX_OUTPUT_GAUSSIANS") or config.get("max_output_gaussians"))
    if candidate_output_cap is None:
        return False
    hard_maxes = [
        hard_max
        for hard_max in (float_value(failure.get("hard_max_splat_count")) for failure in failed_hypotheses)
        if hard_max is not None
    ]
    return not hard_maxes or any(candidate_output_cap <= hard_max for hard_max in hard_maxes)


def has_stronger_density_control(
    density_control_knobs: Mapping[str, Any],
    failed_hypotheses: Sequence[Mapping[str, Any]],
) -> bool:
    env = density_control_knobs.get("environment")
    if not isinstance(env, Mapping):
        env = {}
    config = density_control_knobs.get("training_config")
    if not isinstance(config, Mapping):
        config = {}
    candidate_max_ratio = float_value(env.get("TRAINING_MAX_GAUSS_RATIO") or config.get("training_max_gauss_ratio"))
    candidate_stop_split = float_value(env.get("TRAINING_STOP_SPLIT_AT") or config.get("training_stop_split_at"))
    candidate_alpha = float_value(env.get("CULL_ALPHA_THRESH") or config.get("cull_alpha_thresh"))
    candidate_scale = float_value(env.get("CULL_SCALE_THRESH") or config.get("cull_scale_thresh"))
    candidate_output_cap = float_value(env.get("TRAINING_MAX_OUTPUT_GAUSSIANS") or config.get("max_output_gaussians"))
    candidate_density_cap_enabled = str(
        env.get("TRAINING_DENSITY_CAP_ENABLED") or config.get("density_cap_enabled") or ""
    ).lower() in ("1", "true", "yes")

    for failure in density_controlled_visual_fidelity_failures(failed_hypotheses):
        failed_env = failure.get("density_control_environment")
        if not isinstance(failed_env, Mapping):
            failed_env = {}
        failed_config = failure.get("density_control_training_config")
        if not isinstance(failed_config, Mapping):
            failed_config = {}
        failed_max_ratio = float_value(failed_env.get("TRAINING_MAX_GAUSS_RATIO") or failed_config.get("training_max_gauss_ratio"))
        failed_stop_split = float_value(failed_env.get("TRAINING_STOP_SPLIT_AT") or failed_config.get("training_stop_split_at"))
        failed_alpha = float_value(failed_env.get("CULL_ALPHA_THRESH") or failed_config.get("cull_alpha_thresh"))
        failed_scale = float_value(failed_env.get("CULL_SCALE_THRESH") or failed_config.get("cull_scale_thresh"))
        hard_max = float_value(failure.get("hard_max_splat_count"))

        if failed_max_ratio is not None and candidate_max_ratio is not None and candidate_max_ratio < failed_max_ratio:
            return True
        if failed_stop_split is not None and candidate_stop_split is not None and candidate_stop_split < failed_stop_split:
            return True
        if failed_alpha is not None and candidate_alpha is not None and candidate_alpha > failed_alpha:
            return True
        if failed_scale is not None and candidate_scale is not None and candidate_scale < failed_scale:
            return True
        if candidate_output_cap is not None and (hard_max is None or candidate_output_cap <= hard_max):
            return True
        if candidate_density_cap_enabled and candidate_output_cap is not None:
            return True
    return False


def has_ai_visual_blocker(blockers: Sequence[str]) -> bool:
    return any(str(reason).startswith("ai_visual_") or str(reason).startswith("visual_qa_") for reason in blockers)


def has_v18_comparison_plan(strategy: Mapping[str, Any] | None) -> bool:
    if not isinstance(strategy, Mapping):
        return False
    if strategy.get("v18_review_manifest_s3_uri") or strategy.get("v18_comparison_plan"):
        return True
    plan = strategy.get("v18_non_regression_plan")
    return isinstance(plan, Mapping) and bool(plan)


def has_visual_qa_plan(strategy: Mapping[str, Any] | None) -> bool:
    if not isinstance(strategy, Mapping):
        return False
    if strategy.get("visual_qa_required") is True or strategy.get("visual_qa_plan"):
        return True
    plan = strategy.get("ai_visual_review_plan")
    return isinstance(plan, Mapping) and bool(plan)


def has_early_visual_smoke_plan(strategy: Mapping[str, Any] | None) -> bool:
    if not isinstance(strategy, Mapping):
        return False
    plan = strategy.get("early_visual_smoke_plan")
    if not isinstance(plan, Mapping):
        plan = strategy.get("early_checkpoint_visual_qa_plan")
    if not isinstance(plan, Mapping) or not plan:
        return False
    checkpoint_steps = plan.get("checkpoint_steps")
    frozen_cameras = plan.get("frozen_cameras") or plan.get("sentinel_cameras")
    abort_on_failure = plan.get("abort_on_failure") is True
    if not isinstance(checkpoint_steps, list) or not checkpoint_steps:
        return False
    if not isinstance(frozen_cameras, list) or not frozen_cameras:
        return False
    return abort_on_failure


def has_horizon_blocker(blockers: Sequence[str]) -> bool:
    return any(str(reason).startswith("horizon_") for reason in blockers)


def required_bucket_axes(blockers: Sequence[str], *, bucket: str) -> list[str]:
    required: list[str] = []
    prefix = f"{bucket}_"
    for reason in blockers:
        normalized = str(reason).lower()
        if not normalized.startswith(prefix):
            continue
        if "psnr" in normalized:
            required.append(f"{bucket}.psnr")
        if "ssim" in normalized:
            required.append(f"{bucket}.ssim")
        if "lpips" in normalized:
            required.append(f"{bucket}.lpips")
        if "sky" in normalized:
            required.append(f"{bucket}.sky_score")
    return ordered_unique(required)


def required_horizon_axes(blockers: Sequence[str]) -> list[str]:
    return required_bucket_axes(blockers, bucket="horizon")


def required_boundary_axes(blockers: Sequence[str]) -> list[str]:
    required = required_bucket_axes(blockers, bucket="boundary")
    if BOUNDARY_BLOCKER in blockers:
        required.append("boundary.required_improvement")
    return ordered_unique(required)


def has_overdense_leaf_blocker(blockers: Sequence[str]) -> bool:
    return any(reason in blockers for reason in OVERDENSE_LEAF_REASONS)


def evaluate_candidate_objective(
    *,
    candidate_objective: Mapping[str, Any] | None,
    current_blockers: Sequence[str],
    responsible_tiles: Mapping[str, Any],
    failed_hypotheses: Sequence[Mapping[str, Any]] = (),
    max_estimated_usd: float,
) -> dict[str, Any]:
    block_reasons: list[str] = []
    warnings: list[str] = []
    horizon_blocked = has_horizon_blocker(current_blockers)

    if not candidate_objective:
        return {
            "present": False,
            "decision": "paid_retry_blocked",
            "block_reasons": ["candidate_objective_missing"],
            "warnings": [],
            "targeted_quality_blockers": [],
            "selected_tile_ids": [],
            "context_support_tile_ids": [],
            "covered_tile_ids": [],
            "boundary_camera_ids": [],
            "horizon_camera_ids": [],
            "expected_metric_axes": [],
            "objective_changes": [],
            "loss_weighting_implementation": {"environment": {}, "training_config": {}},
            "density_control_implementation": {"environment": {}, "training_config": {}},
            "visual_fidelity_implementation": {"environment": {}, "training_config": {}},
            "hardcap_quality_repair_implementation": {"environment": {}, "training_config": {}},
            "scaffold_density_restoration_implementation": {
                "environment": {},
                "training_config": {},
                "scaffold_artifact_s3_uri": "",
                "has_scaffold_restoration": False,
            },
            "leaf_sidecar_export_implementation_present": False,
            "hard_output_cap_below_leaf_min_violations": [],
            "sagemaker_env_value_length_violations": [],
            "estimated_usd": None,
            "max_estimated_usd": max_estimated_usd or None,
        }

    targets = targeted_blockers(candidate_objective)
    missing_targets = [reason for reason in current_blockers if reason not in targets]
    if not targets:
        block_reasons.append("objective_missing_targeted_quality_blockers")
    elif missing_targets:
        block_reasons.append("objective_does_not_target_current_blockers")

    tiles = selected_tile_ids(candidate_objective)
    contexts = context_tile_ids(candidate_objective)
    covered = sorted_unique(tiles + contexts)
    primary_boundary_tiles = list_strings(responsible_tiles.get("primary_responsible_tile_ids"))
    missing_primary_boundary_tiles = [tile_id for tile_id in primary_boundary_tiles if tile_id not in covered]
    if BOUNDARY_BLOCKER in current_blockers and missing_primary_boundary_tiles:
        block_reasons.append("objective_omits_primary_boundary_tiles")

    horizon_primary_tiles = list_strings(responsible_tiles.get("horizon_primary_responsible_tile_ids"))
    missing_horizon_tiles = [tile_id for tile_id in horizon_primary_tiles if tile_id not in covered]
    if horizon_blocked and missing_horizon_tiles:
        block_reasons.append("objective_omits_primary_horizon_tiles")
    elif missing_horizon_tiles:
        warnings.append("objective_does_not_cover_all_horizon_context_tiles")

    expected_boundary_cameras = list_strings(responsible_tiles.get("boundary_frozen_cameras"))
    candidate_boundary_cameras = boundary_cameras(candidate_objective)
    missing_boundary_cameras = [
        camera_id for camera_id in expected_boundary_cameras if camera_id not in candidate_boundary_cameras
    ]
    if BOUNDARY_BLOCKER in current_blockers and missing_boundary_cameras:
        block_reasons.append("objective_missing_boundary_frozen_cameras")

    expected_horizon_cameras = list_strings(responsible_tiles.get("horizon_frozen_cameras"))
    candidate_horizon_cameras = horizon_cameras(candidate_objective)
    missing_horizon_cameras = [
        camera_id for camera_id in expected_horizon_cameras if camera_id not in candidate_horizon_cameras
    ]
    if horizon_blocked and missing_horizon_cameras:
        block_reasons.append("objective_missing_horizon_frozen_cameras")
    elif missing_horizon_cameras:
        warnings.append("objective_does_not_name_all_horizon_frozen_cameras")

    axes = expected_metric_axes(candidate_objective)
    missing_boundary_axes = [axis for axis in required_boundary_axes(current_blockers) if axis not in axes]
    for axis in missing_boundary_axes:
        suffix = axis.rsplit(".", 1)[-1]
        block_reasons.append(f"objective_missing_boundary_{suffix}_axis")
    missing_horizon_axes = [axis for axis in required_horizon_axes(current_blockers) if axis not in axes]
    for axis in missing_horizon_axes:
        suffix = axis.rsplit(".", 1)[-1]
        block_reasons.append(f"objective_missing_horizon_{suffix}_axis")

    changes = objective_changes(candidate_objective)
    if not has_approved_objective(changes):
        block_reasons.append("objective_lacks_camera_or_loss_weighting_change")
    if repeats_failed_density_or_merge_only(changes):
        block_reasons.append("objective_repeats_failed_density_or_merge_only_hypothesis")
    if repeats_failed_frame_repeat_without_loss(changes):
        block_reasons.append("objective_repeats_failed_frame_repeat_without_loss_weighting")
    if repeats_failed_density_cap(changes, failed_hypotheses):
        block_reasons.append("objective_repeats_failed_density_cap_loss_weighting_hypothesis")
    if repeats_failed_soft_density(changes, failed_hypotheses):
        block_reasons.append("objective_repeats_failed_soft_density_hypothesis")
    if repeats_failed_hardcap_visual_without_quality_repair(changes, failed_hypotheses):
        block_reasons.append("objective_repeats_failed_hard_output_cap_visual_fidelity_without_new_quality_repair")
    hardcap_quality_repair_knobs = implemented_hardcap_quality_repair_knobs(candidate_objective)
    if (
        repeats_failed_hardcap_visual(changes, failed_hypotheses)
        and not repeats_failed_hardcap_visual_without_quality_repair(changes, failed_hypotheses)
        and not any(hardcap_quality_repair_knobs.values())
    ):
        block_reasons.append("objective_missing_hard_output_cap_quality_repair_implementation")
    if has_hardcap_visual_quality_failed(failed_hypotheses) and not has_early_visual_smoke_plan(candidate_objective):
        block_reasons.append("objective_missing_early_visual_smoke_abort_plan_after_hardcap_visual_failure")
    loss_weighting_knobs = implemented_loss_weighting_knobs(candidate_objective)
    if has_loss_weighting_change(changes) and not any(loss_weighting_knobs.values()):
        block_reasons.append("objective_missing_loss_weighting_implementation")
    density_control_knobs = implemented_density_control_knobs(candidate_objective)
    if has_overdense_leaf_blocker(current_blockers) and not any(density_control_knobs.values()):
        block_reasons.append("objective_missing_density_control_after_overdense_leaf")
    if has_underdense_leaf_blocker(current_blockers):
        cap_violations = hard_output_cap_below_failed_minimums(density_control_knobs, failed_hypotheses)
        if cap_violations:
            block_reasons.append("objective_repeats_impossible_hard_output_cap_below_leaf_min")
    else:
        cap_violations = []
    underdense_density_restoration = underdense_density_restoration_implementation(
        candidate_objective, failed_hypotheses
    )
    scaffold_density_restoration = scaffold_density_restoration_implementation(candidate_objective)
    if (
        visual_sentinel_budget_underdense_failures(failed_hypotheses)
        and not underdense_density_restoration["has_stronger_density_budget"]
    ):
        block_reasons.append("objective_missing_density_restoration_after_visual_sentinel_underdense_leaf")
    if (
        visual_sentinel_density_restored_underdense_failures(failed_hypotheses)
        and not scaffold_density_restoration["has_scaffold_restoration"]
    ):
        block_reasons.append("objective_missing_scaffold_restoration_after_density_restored_underdense_leaf")
    normalized_changes = " ".join(changes).lower()
    if (
        has_visual_fidelity_overdense_failed(failed_hypotheses)
        and any(term in normalized_changes for term in VISUAL_FIDELITY_OBJECTIVE_TERMS)
        and not any(density_control_knobs.values())
    ):
        block_reasons.append("objective_repeats_failed_visual_fidelity_without_density_control")
    if (
        density_controlled_visual_fidelity_failures(failed_hypotheses)
        and any(term in normalized_changes for term in VISUAL_FIDELITY_OBJECTIVE_TERMS)
        and not has_stronger_density_control(density_control_knobs, failed_hypotheses)
    ):
        block_reasons.append("objective_repeats_failed_density_control_without_stronger_cap")
    if (
        stronger_density_visual_fidelity_failures(failed_hypotheses)
        and any(term in normalized_changes for term in VISUAL_FIDELITY_OBJECTIVE_TERMS)
        and not has_hard_output_density_cap(density_control_knobs, failed_hypotheses)
    ):
        block_reasons.append("objective_repeats_failed_incremental_density_control_without_hard_output_cap")
    visual_fidelity_knobs = implemented_visual_fidelity_knobs(candidate_objective)
    if has_ai_visual_blocker(current_blockers) and not any(visual_fidelity_knobs.values()):
        block_reasons.append("objective_missing_visual_fidelity_implementation_after_ai_block")
    sidecar_export_present = has_leaf_sidecar_export_implementation(candidate_objective)
    if has_leaf_artifact_structure_blocker(current_blockers) and not sidecar_export_present:
        block_reasons.append("objective_missing_leaf_export_background_sidecar_plan")
    env_value_length_violations = sagemaker_env_value_length_violations(candidate_objective)
    if env_value_length_violations:
        block_reasons.append("objective_has_sagemaker_env_value_over_512_chars")
    if has_soft_density_failed(failed_hypotheses) and not has_v18_comparison_plan(candidate_objective):
        block_reasons.append("objective_missing_v18_non_regression_plan_after_soft_density_failure")
    if has_ai_visual_blocker(current_blockers) and not has_visual_qa_plan(candidate_objective):
        block_reasons.append("objective_missing_visual_qa_plan_after_ai_block")

    submitted_jobs = candidate_objective.get("submitted_jobs")
    if submitted_jobs not in ([], None):
        block_reasons.append("objective_already_submitted_jobs")

    if not no_full_14tile_training_confirmed(candidate_objective):
        block_reasons.append("no_full_14tile_training_not_confirmed")

    cost = estimated_usd(candidate_objective)
    if max_estimated_usd > 0:
        if cost is None:
            block_reasons.append("objective_missing_cost_estimate")
        elif cost > max_estimated_usd:
            block_reasons.append("objective_estimated_cost_above_cap")
    elif cost is None:
        warnings.append("objective_missing_cost_estimate")

    return {
        "present": True,
        "decision": "paid_retry_allowed" if not block_reasons else "paid_retry_blocked",
        "block_reasons": block_reasons,
        "warnings": warnings,
        "targeted_quality_blockers": targets,
        "missing_targeted_quality_blockers": missing_targets,
        "selected_tile_ids": tiles,
        "context_support_tile_ids": contexts,
        "covered_tile_ids": covered,
        "missing_primary_boundary_tile_ids": missing_primary_boundary_tiles,
        "missing_primary_horizon_tile_ids": missing_horizon_tiles,
        "boundary_camera_ids": candidate_boundary_cameras,
        "missing_boundary_frozen_cameras": missing_boundary_cameras,
        "horizon_camera_ids": candidate_horizon_cameras,
        "missing_horizon_frozen_cameras": missing_horizon_cameras,
        "expected_metric_axes": axes,
        "missing_boundary_metric_axes": missing_boundary_axes,
        "missing_horizon_metric_axes": missing_horizon_axes,
        "objective_changes": changes,
        "loss_weighting_implementation": loss_weighting_knobs,
        "density_control_implementation": density_control_knobs,
        "visual_fidelity_implementation": visual_fidelity_knobs,
        "hardcap_quality_repair_implementation": hardcap_quality_repair_knobs,
        "underdense_density_restoration_implementation": underdense_density_restoration,
        "scaffold_density_restoration_implementation": scaffold_density_restoration,
        "leaf_sidecar_export_implementation_present": sidecar_export_present,
        "hard_output_cap_below_leaf_min_violations": cap_violations,
        "sagemaker_env_value_length_violations": env_value_length_violations,
        "estimated_usd": cost,
        "max_estimated_usd": max_estimated_usd or None,
        "submitted_jobs": submitted_jobs,
        "no_full_14tile_training": no_full_14tile_training_confirmed(candidate_objective),
        "early_visual_smoke_plan_present": has_early_visual_smoke_plan(candidate_objective),
    }


def plan_boundary_objective_strategy(
    *,
    quality_strategy: Mapping[str, Any],
    responsible_tiles: Mapping[str, Any],
    attribution: Mapping[str, Any],
    candidate_objective: Mapping[str, Any] | None = None,
    max_estimated_usd: float = 0.0,
) -> dict[str, Any]:
    blockers = current_quality_blockers(quality_strategy, responsible_tiles, attribution)
    failed_hypotheses = extract_failed_hypotheses(attribution)
    candidate_gate = evaluate_candidate_objective(
        candidate_objective=candidate_objective,
        current_blockers=blockers,
        responsible_tiles=responsible_tiles,
        failed_hypotheses=failed_hypotheses,
        max_estimated_usd=max_estimated_usd,
    )
    primary_boundary_tiles = list_strings(responsible_tiles.get("primary_responsible_tile_ids"))
    horizon_primary_tiles = list_strings(responsible_tiles.get("horizon_primary_responsible_tile_ids"))
    support_tiles = [
        tile_id
        for tile_id in list_strings(responsible_tiles.get("combined_support_tile_ids"))
        if tile_id not in primary_boundary_tiles and tile_id not in horizon_primary_tiles
    ]
    protected_v18_status = attribution.get("v18_non_regression_status")
    if not isinstance(protected_v18_status, Mapping):
        protected_v18_status = {}

    paid_allowed = candidate_gate["decision"] == "paid_retry_allowed"
    recommendation = "candidate_objective_can_enter_leaf_only_gate" if paid_allowed else "no_paid_retry_until_objective_redesign"
    required_axes = ordered_unique(
        required_boundary_axes(blockers) + required_horizon_axes(blockers) + ["boundary.psnr", "boundary.ssim", "boundary.lpips"]
    )

    return {
        "checked_at": now_iso(),
        "recommendation": recommendation,
        "paid_retry_allowed": paid_allowed,
        "paid_retry_recommended": paid_allowed,
        "current_quality_blockers": blockers,
        "boundary_improvement_gap": quality_strategy.get("boundary_improvement_gap"),
        "horizon_regression_gap": quality_strategy.get("horizon_regression_gap"),
        "protected_v18_non_regression_status": protected_v18_status,
        "boundary_frozen_cameras": list_strings(responsible_tiles.get("boundary_frozen_cameras")),
        "horizon_frozen_cameras": list_strings(responsible_tiles.get("horizon_frozen_cameras")),
        "primary_boundary_tile_ids": primary_boundary_tiles,
        "primary_horizon_tile_ids": horizon_primary_tiles,
        "context_support_tile_ids": support_tiles,
        "failed_hypotheses": failed_hypotheses,
        "required_next_hypothesis": {
            "must_change": [
                "camera/objective weighting during leaf training or selection",
                "explicit boundary frozen-camera emphasis for DJI_0067.JPG-DJI_0070.JPG",
                "tile_04/tile_10 boundary context coverage before merge/review",
            ],
            "must_not_repeat": [
                "tile_10 density-only repair",
                "merge-only protected overlap retention",
                "frame-repeat-only camera weighting without loss/objective redesign",
                "hard density-cap/loss-weighting retry that does not explicitly preserve horizon and LPIPS quality",
                "soft-density/global-SSIM retry without a new appearance, geometry, color, or perceptual objective",
                "visual-fidelity tile_10 retry without concrete density control after over-dense leaf rejection",
                "density-controlled visual-fidelity tile_10 retry without a stronger cap/split/culling change after the latest over-dense leaf rejection",
                "incremental tile_10 split/culling density retry without an exported-output hard cap at or below the post-leaf hard max",
                "hard-output-cap visual-fidelity retry without a new color, exposure, geometry, or perceptual repair after AI visual QA blocks",
                "long leaf proofs after visual QA failure unless a cheap early visual-smoke abort plan is present",
                "full 14-tile training before staged R0/R1/R2/R3 gates",
            ],
            "expected_metric_axes": required_axes,
        },
        "candidate_objective_gate": candidate_gate,
        "next_no_spend_actions": [
            "write a concrete candidate objective JSON that names the frozen cameras, primary tiles, metric axis, cost cap, and no-full14 guard",
            "run this planner against that candidate objective and require candidate_objective_gate.decision=paid_retry_allowed",
            "only then run leaf-only submit readiness; merge/review spend remains blocked until leaf gates pass",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quality-strategy-json", required=True)
    parser.add_argument("--responsible-tiles-json", required=True)
    parser.add_argument("--attribution-json", required=True)
    parser.add_argument("--candidate-objective-json", default="")
    parser.add_argument("--max-estimated-usd", type=float, default=0.0)
    parser.add_argument("--output-json", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = plan_boundary_objective_strategy(
        quality_strategy=load_json(args.quality_strategy_json),
        responsible_tiles=load_json(args.responsible_tiles_json),
        attribution=load_json(args.attribution_json),
        candidate_objective=load_json(args.candidate_objective_json) if args.candidate_objective_json else None,
        max_estimated_usd=args.max_estimated_usd,
    )
    write_json(args.output_json, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["candidate_objective_gate"]["decision"] == "paid_retry_allowed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
