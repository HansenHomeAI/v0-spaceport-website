#!/usr/bin/env python3
"""Build a no-compute SfM fanout contract from a chunk planner manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Emit per-leaf SageMaker job specs and reducer inputs for a chunked "
            "COLMAP manifest without launching compute."
        )
    )
    parser.add_argument("--planner-manifest", required=True, help="Local chunk_planner_manifest.json")
    parser.add_argument(
        "--planner-manifest-uri",
        default="",
        help="Optional S3 URI for the immutable planner manifest each leaf should use.",
    )
    parser.add_argument("--input-s3-uri", required=True)
    parser.add_argument("--output-s3-uri", required=True, help="Base S3 prefix for the fanout proof")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--job-prefix", required=True)
    parser.add_argument(
        "--image-uri",
        default="975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:agent73948216sfmproductionspine",
    )
    parser.add_argument("--instance-type", default="ml.g4dn.xlarge")
    parser.add_argument("--volume-size-gb", type=int, default=120)
    parser.add_argument("--max-concurrency", type=int, default=0)
    parser.add_argument("--max-attempts-per-leaf", type=int, default=2)
    parser.add_argument("--summary-json-output", required=True)
    return parser.parse_args()


def normalize_s3_prefix(prefix: str) -> str:
    return prefix.rstrip("/")


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    chunks = manifest.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("planner manifest must contain a non-empty chunks array")
    return manifest


def build_leaf_job(
    *,
    args: argparse.Namespace,
    chunk: dict[str, Any],
    output_base: str,
) -> dict[str, Any]:
    index = int(chunk["index"])
    job_name = f"{args.job_prefix}-leaf-{index:02d}"
    output_uri = f"{output_base}/leaves/leaf-{index:02d}/colmap"
    planner = str(getattr(args, "planner", "") or chunk.get("planner") or "").strip()
    environment = {
        "AWS_DEFAULT_REGION": "us-west-2",
        "PYTHONUNBUFFERED": "1",
        "SFM_BRANCH_NAME": args.branch,
        "SFM_GIT_HEAD": args.head,
        "SFM_INPUT_URI": args.input_s3_uri,
        "SFM_OUTPUT_URI": output_uri,
        "SFM_JOB_NAME": job_name,
        "COLMAP_ENABLE_SPATIAL_CHUNKING": "1",
        "COLMAP_PIPELINE_MODE": "distributed_chunked_v1",
        "COLMAP_CHUNK_PLANNER": planner or "footprint_graph_v1",
        "COLMAP_ONLY_CHUNK_INDEXES": str(index),
        "COLMAP_LEAF_TARGET_IMAGES": "200",
        "COLMAP_LEAF_HARD_CAP": "320",
    }
    if args.planner_manifest_uri:
        environment["COLMAP_INPUT_CHUNK_PLANNER_MANIFEST_URI"] = args.planner_manifest_uri

    return {
        "chunk_index": index,
        "job_name": job_name,
        "output_uri": output_uri,
        "image_count": len(chunk.get("image_names") or []),
        "core_image_count": len(chunk.get("core_names") or []),
        "overlap_image_count": len(chunk.get("overlap_names") or []),
        "selected_chunk_indexes": [index],
        "processing_job_spec": {
            "ProcessingJobName": job_name,
            "AppSpecification": {
                "ImageUri": args.image_uri,
                "ContainerEntrypoint": ["/opt/ml/code/run_sfm.sh"],
            },
            "ProcessingResources": {
                "ClusterConfig": {
                    "InstanceCount": 1,
                    "InstanceType": args.instance_type,
                    "VolumeSizeInGB": args.volume_size_gb,
                }
            },
            "ProcessingInputs": [
                {
                    "InputName": "sfm-input",
                    "S3Input": {
                        "S3Uri": args.input_s3_uri,
                        "LocalPath": "/opt/ml/processing/input",
                        "S3DataType": "S3Prefix",
                        "S3InputMode": "File",
                        "S3DataDistributionType": "FullyReplicated",
                        "S3CompressionType": "None",
                    },
                }
            ],
            "ProcessingOutputConfig": {
                "Outputs": [
                    {
                        "OutputName": "colmap-output",
                        "S3Output": {
                            "S3Uri": output_uri,
                            "LocalPath": "/opt/ml/processing/output",
                            "S3UploadMode": "EndOfJob",
                        },
                        "AppManaged": False,
                    }
                ]
            },
            "Environment": environment,
            "Tags": [
                {"Key": "Project", "Value": "Spaceport"},
                {"Key": "Component", "Value": "SfM"},
                {"Key": "Benchmark", "Value": "true"},
                {"Key": "Branch", "Value": args.branch},
                {"Key": "FanoutProof", "Value": "true"},
            ],
        },
    }


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = Path(args.planner_manifest)
    manifest = load_manifest(manifest_path)
    output_base = normalize_s3_prefix(args.output_s3_uri)
    chunks = sorted(manifest["chunks"], key=lambda item: int(item["index"]))
    for chunk in chunks:
        chunk["planner"] = manifest.get("planner")
    leaf_jobs = [build_leaf_job(args=args, chunk=chunk, output_base=output_base) for chunk in chunks]
    indexes = [job["chunk_index"] for job in leaf_jobs]
    expected_indexes = list(range(len(chunks)))
    core_names = [name for chunk in chunks for name in (chunk.get("core_names") or [])]
    leaf_names = [name for chunk in chunks for name in (chunk.get("image_names") or [])]
    duplicate_core_count = len(core_names) - len(set(core_names))
    planner = manifest.get("planner", "footprint_graph_v1")
    max_concurrency = int(getattr(args, "max_concurrency", 0) or len(leaf_jobs))
    visibility_manifest = manifest.get("visibility_cell_manifest") or {}
    visibility_cells = visibility_manifest.get("cells", []) if isinstance(visibility_manifest, dict) else []
    chunk_jurisdictions = manifest.get("chunk_jurisdictions") or {}
    visibility_weak_adjacent_seams: list[dict[str, int]] = []
    visibility_adjacent_seams: list[dict[str, int]] = []
    if planner == "visibility_cell_v1" and isinstance(visibility_cells, list):
        cell_images: dict[int, set[str]] = {}
        cell_adjacency: dict[int, set[int]] = {}
        for raw_cell in visibility_cells:
            if not isinstance(raw_cell, dict):
                continue
            try:
                cell_index = int(raw_cell.get("index"))
            except (TypeError, ValueError):
                continue
            cell_images[cell_index] = {
                str(name)
                for name in (raw_cell.get("image_names") or [])
                if str(name).strip()
            }
            cell_adjacency[cell_index] = {
                int(index)
                for index in (raw_cell.get("adjacency") or [])
                if str(index).strip()
            }
        for first_index, neighbors in sorted(cell_adjacency.items()):
            for second_index in sorted(neighbors):
                if first_index >= second_index:
                    continue
                shared_count = len(cell_images.get(first_index, set()).intersection(cell_images.get(second_index, set())))
                seam = {
                    "first_chunk_index": first_index,
                    "second_chunk_index": second_index,
                    "shared_image_count": shared_count,
                }
                visibility_adjacent_seams.append(seam)
                if shared_count < 10:
                    visibility_weak_adjacent_seams.append(seam)

    gaps: list[str] = []
    warnings: list[str] = []
    if indexes != expected_indexes:
        gaps.append("selected chunk indexes do not exactly cover 0..chunk_count-1")
    if duplicate_core_count:
        warnings.append("core image ownership has duplicate images; reducer must de-duplicate overlap")
    if not args.planner_manifest_uri:
        gaps.append("immutable planner manifest must be uploaded to S3 before launching leaves")
    if planner == "visibility_cell_v1":
        if len(manifest.get("primary_cell_id_by_image") or {}) != len(set(core_names)):
            gaps.append("visibility_cell_v1 requires exactly one primary cell owner for every core image")
        if len(chunk_jurisdictions) != len(chunks):
            gaps.append("visibility_cell_v1 requires jurisdiction bounds for every leaf chunk")
        if not visibility_cells:
            gaps.append("visibility_cell_v1 requires a non-empty visibility cell manifest")
        if visibility_weak_adjacent_seams:
            gaps.append(
                "visibility_cell_v1 adjacent seams must have at least 10 shared images or an explicit targeted seam proof"
            )

    return {
        "status": "dry_run_contract_ready" if not gaps else "dry_run_contract_needs_fix",
        "no_compute_launched": True,
        "branch": args.branch,
        "head": args.head,
        "input_s3_uri": args.input_s3_uri,
        "output_s3_uri": output_base,
        "planner_manifest": str(manifest_path),
        "planner_manifest_uri": args.planner_manifest_uri,
        "planner": manifest.get("planner"),
        "pipeline_mode": manifest.get("pipeline_mode", "distributed_chunked_v1"),
        "max_concurrency": max_concurrency,
        "retry_policy": {
            "max_attempts_per_leaf": int(getattr(args, "max_attempts_per_leaf", 2)),
            "rerun_scope": "failed_leaf_or_smallest_bridge_only",
            "duplicate_full_md1_launch_allowed": False,
        },
        "chunk_count": len(chunks),
        "leaf_job_count": len(leaf_jobs),
        "visibility_cell_contract": {
            "enabled": planner == "visibility_cell_v1",
            "cell_count": len(visibility_cells) if isinstance(visibility_cells, list) else 0,
            "seam_overlap_percent": manifest.get("seam_overlap_percent"),
            "primary_cell_id_by_image_count": len(manifest.get("primary_cell_id_by_image") or {}),
            "overlap_cell_id_by_image_count": len(manifest.get("overlap_cell_ids_by_image") or {}),
            "chunk_jurisdiction_count": len(chunk_jurisdictions),
            "min_required_adjacent_shared_images": 10,
            "min_adjacent_shared_images": min(
                (seam["shared_image_count"] for seam in visibility_adjacent_seams),
                default=0,
            ),
            "weak_adjacent_seams_under_10": visibility_weak_adjacent_seams,
            "adjacent_seam_shared_images": visibility_adjacent_seams,
        },
        "coverage": {
            "selected_chunk_indexes": indexes,
            "expected_chunk_indexes": expected_indexes,
            "unique_core_images": len(set(core_names)),
            "unique_leaf_images": len(set(leaf_names)),
            "duplicate_core_images": duplicate_core_count,
            "max_leaf_image_count": max(job["image_count"] for job in leaf_jobs),
            "max_core_image_count": max(job["core_image_count"] for job in leaf_jobs),
        },
        "leaf_jobs": leaf_jobs,
        "reducer_contract": {
            "expected_leaf_count": len(leaf_jobs),
            "leaf_output_uris": [job["output_uri"] for job in leaf_jobs],
            "final_output_uri": f"{output_base}/merged/colmap",
            "required_leaf_artifacts": [
                "chunk_planner_manifest.json",
                "leaf_metadata.json",
                "sfm_metadata.json",
                "sparse/0/cameras.txt",
                "sparse/0/images.txt",
                "sparse/0/points3D.txt",
                "sparse_raw/0/cameras.txt",
                "sparse_raw/0/images.txt",
                "sparse_raw/0/points3D.txt",
            ],
            "promotion_gates": [
                "all leaf jobs Completed",
                "failed_leaf_count == 0 after bounded retries",
                "merged_component_count == expected_component_count",
                "standard sparse/0 exists",
                "visibility_cell_v1 jurisdiction coverage exists when enabled",
                "no weak seam has <10 shared registered images without targeted seam proof",
                "registration and speed gates compare against md1p24e752k-1776314974",
            ],
        },
        "gaps": gaps,
        "warnings": warnings,
        "unresolved_after_dry_run": [
            "actual multi-instance SageMaker leaf execution is not yet proven",
            "reducer merge from independently uploaded leaf outputs is not yet proven",
        ],
        "next_validation_step": (
            "Upload the immutable planner manifest, launch a two-leaf canary with this contract, "
            "then run the reducer against the two independent leaf prefixes before any repeat full MD1 fanout."
        ),
    }


def main() -> int:
    args = parse_args()
    contract = build_contract(args)
    output_path = Path(args.summary_json_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: contract[k] for k in ("status", "chunk_count", "leaf_job_count", "gaps")}, indent=2))
    return 0 if contract["status"] == "dry_run_contract_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
