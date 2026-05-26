#!/usr/bin/env python3
"""Plan a SageMaker Processing no-training tiled merge from a benchmark summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence


MERGEABLE_STAGE_TYPES = {"train", "cached_tile", "context_density_tile"}
SUPPORTED_PROTECTED_OVERLAP_MODES = {"", "none", "off", "retain_all"}


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_s3_prefix(uri: str) -> str:
    return uri.rstrip("/")


def normalize_protected_overlap_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in SUPPORTED_PROTECTED_OVERLAP_MODES:
        raise ValueError(
            "unsupported --merge-protected-overlap-mode "
            f"{mode!r}; expected one of retain_all, none, off"
        )
    return "" if normalized in {"", "none", "off"} else normalized


def stage_artifact_uri(stage: dict) -> str:
    return str(stage.get("source_artifact_uri") or stage.get("model_artifact_s3_uri") or "").strip()


def stage_ply_candidates(stage: dict) -> list[str]:
    tile_id = str(stage.get("tile_id") or "").strip()
    if not tile_id:
        return []
    if stage.get("stage_type") == "context_density_tile":
        return [f"tiles/{tile_id}/splat.ply", "splat.ply"]
    return ["splat.ply"]


def build_merge_plan(summary: dict) -> dict:
    artifact_input_names: dict[str, str] = {}
    tiles: list[dict] = []
    for stage in summary.get("stages", []):
        if stage.get("stage_type") not in MERGEABLE_STAGE_TYPES:
            continue
        tile_id = str(stage.get("tile_id") or "").strip()
        artifact_uri = stage_artifact_uri(stage)
        candidates = stage_ply_candidates(stage)
        if not tile_id or not artifact_uri or not candidates:
            continue
        artifact_input_name = artifact_input_names.setdefault(artifact_uri, f"artifact-{len(artifact_input_names):02d}")
        tiles.append(
            {
                "tile_id": tile_id,
                "stage_name": stage.get("stage_name"),
                "stage_type": stage.get("stage_type"),
                "artifact_uri": artifact_uri,
                "artifact_input_name": artifact_input_name,
                "candidate_members": candidates,
                "cache_status": stage.get("cache_status"),
                "quality_gate_status": stage.get("quality_gate_status"),
            }
        )
    return {
        "source_summary_json": summary.get("source_summary_json"),
        "selected_tile_ids": [tile["tile_id"] for tile in tiles],
        "artifact_inputs": [
            {"artifact_input_name": name, "artifact_uri": uri}
            for uri, name in sorted(artifact_input_names.items(), key=lambda item: item[1])
        ],
        "tiles": tiles,
    }


def create_tiled_merge_processing_payload(
    *,
    branch_name: str,
    job_name: str,
    image_uri: str,
    role_arn: str,
    output_s3_uri: str,
    merge_plan_s3_uri: str,
    tile_selection_s3_uri: str,
    artifact_inputs: Sequence[dict],
    merge_mode: str,
    instance_type: str,
    volume_size_gb: int,
    max_runtime_seconds: int,
    background_source_tile_id: str = "",
    protected_overlap_tile_ids: str = "",
    protected_overlap_mode: str = "",
) -> dict:
    processing_inputs = [
        {
            "InputName": "merge-plan",
            "S3Input": {
                "S3Uri": merge_plan_s3_uri,
                "LocalPath": "/opt/ml/processing/input/merge-plan",
                "S3DataType": "S3Prefix",
                "S3InputMode": "File",
            },
        },
        {
            "InputName": "tile-selection",
            "S3Input": {
                "S3Uri": tile_selection_s3_uri,
                "LocalPath": "/opt/ml/processing/input/tile-selection",
                "S3DataType": "S3Prefix",
                "S3InputMode": "File",
            },
        },
    ]
    for artifact_input in artifact_inputs:
        input_name = str(artifact_input["artifact_input_name"])
        processing_inputs.append(
            {
                "InputName": input_name,
                "S3Input": {
                    "S3Uri": str(artifact_input["artifact_uri"]),
                    "LocalPath": f"/opt/ml/processing/input/artifacts/{input_name}",
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File",
                },
            }
        )

    environment = {
        "MERGE_MODE": merge_mode,
        "MERGE_PLAN_PATH": "/opt/ml/processing/input/merge-plan/merge_plan.json",
        "TILE_MANIFEST_PATH": "/opt/ml/processing/input/tile-selection/3dgs_tile_manifest.json",
        "VIEW_BUCKET_MANIFEST_PATH": "/opt/ml/processing/input/tile-selection/3dgs_view_buckets.json",
        "OUTPUT_DIR": "/opt/ml/processing/output/artifact",
    }
    if background_source_tile_id.strip():
        environment["BACKGROUND_SOURCE_TILE_ID"] = background_source_tile_id.strip()
    if protected_overlap_tile_ids.strip():
        environment["MERGE_PROTECTED_OVERLAP_TILE_IDS"] = protected_overlap_tile_ids.strip()
    normalized_protected_overlap_mode = normalize_protected_overlap_mode(protected_overlap_mode)
    if normalized_protected_overlap_mode:
        environment["MERGE_PROTECTED_OVERLAP_MODE"] = normalized_protected_overlap_mode

    return {
        "ProcessingJobName": job_name,
        "RoleArn": role_arn,
        "AppSpecification": {
            "ImageUri": image_uri,
            "ContainerEntrypoint": ["python3", "/opt/ml/code/run_tiled_merge_packaging.py"],
        },
        "Environment": environment,
        "ProcessingInputs": processing_inputs,
        "ProcessingOutputConfig": {
            "Outputs": [
                {
                    "OutputName": "artifact",
                    "S3Output": {
                        "S3Uri": output_s3_uri,
                        "LocalPath": "/opt/ml/processing/output/artifact",
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
        "StoppingCondition": {"MaxRuntimeInSeconds": max_runtime_seconds},
        "Tags": [
            {"Key": "Project", "Value": "Spaceport"},
            {"Key": "Component", "Value": "3DGS"},
            {"Key": "Benchmark", "Value": "true"},
            {"Key": "Branch", "Value": branch_name},
            {"Key": "Stage", "Value": "remote-tiled-merge"},
        ],
    }


def validate_background_source_tile_id(merge_plan: dict, background_source_tile_id: str) -> None:
    source_tile = background_source_tile_id.strip()
    if not source_tile:
        return
    selected_tile_ids = {str(tile_id) for tile_id in merge_plan.get("selected_tile_ids", [])}
    if source_tile not in selected_tile_ids:
        available = ", ".join(sorted(selected_tile_ids)) or "<none>"
        raise RuntimeError(
            "background source tile must be included in the merge plan before remote merge submit; "
            f"requested {source_tile!r}, available tiles: {available}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--merge-plan-output-json", required=True)
    parser.add_argument("--payload-output-json", default="")
    parser.add_argument("--merge-plan-s3-uri", default="")
    parser.add_argument("--tile-selection-s3-uri", default="")
    parser.add_argument("--output-s3-uri", default="")
    parser.add_argument("--job-name", default="")
    parser.add_argument("--role-arn", default="")
    parser.add_argument("--image-uri", default="")
    parser.add_argument("--branch", default="")
    parser.add_argument("--merge-mode", default="")
    parser.add_argument("--background-source-tile-id", default="")
    parser.add_argument("--merge-protected-overlap-tile-ids", default="")
    parser.add_argument("--merge-protected-overlap-mode", default="")
    parser.add_argument("--instance-type", default="ml.g5.2xlarge")
    parser.add_argument("--volume-size-gb", type=int, default=80)
    parser.add_argument("--max-runtime-seconds", type=int, default=3600)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = load_json(args.summary_json)
    summary["source_summary_json"] = args.summary_json
    merge_plan = build_merge_plan(summary)
    Path(args.merge_plan_output_json).write_text(json.dumps(merge_plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.payload_output_json:
        required = {
            "--merge-plan-s3-uri": args.merge_plan_s3_uri,
            "--tile-selection-s3-uri": args.tile_selection_s3_uri or summary.get("tile_selection_input_s3_uri", ""),
            "--output-s3-uri": args.output_s3_uri,
            "--job-name": args.job_name,
            "--role-arn": args.role_arn,
            "--image-uri": args.image_uri or summary.get("image_uri", ""),
        }
        missing = [name for name, value in required.items() if not str(value or "").strip()]
        if missing:
            raise RuntimeError(f"Missing required payload fields: {', '.join(missing)}")
        validate_background_source_tile_id(merge_plan, args.background_source_tile_id)
        payload = create_tiled_merge_processing_payload(
            branch_name=args.branch or str(summary.get("branch") or ""),
            job_name=args.job_name,
            image_uri=args.image_uri or str(summary.get("image_uri") or ""),
            role_arn=args.role_arn,
            output_s3_uri=args.output_s3_uri,
            merge_plan_s3_uri=args.merge_plan_s3_uri,
            tile_selection_s3_uri=args.tile_selection_s3_uri or str(summary.get("tile_selection_input_s3_uri") or ""),
            artifact_inputs=merge_plan["artifact_inputs"],
            merge_mode=args.merge_mode or str(summary.get("merge_mode") or "support_weighted_overlap"),
            background_source_tile_id=args.background_source_tile_id,
            protected_overlap_tile_ids=args.merge_protected_overlap_tile_ids,
            protected_overlap_mode=args.merge_protected_overlap_mode,
            instance_type=args.instance_type,
            volume_size_gb=args.volume_size_gb,
            max_runtime_seconds=args.max_runtime_seconds,
        )
        Path(args.payload_output_json).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(merge_plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
