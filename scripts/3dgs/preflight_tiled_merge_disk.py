#!/usr/bin/env python3
"""Estimate local disk needs before extracting tile artifacts for a tiled merge."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tarfile
from pathlib import Path
from typing import Callable, Sequence


GIB = 1024**3
MIB = 1024**2
MERGEABLE_STAGE_TYPES = {"train", "cached_tile", "context_density_tile"}


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def stage_artifact_uri(stage: dict) -> str:
    return str(stage.get("source_artifact_uri") or stage.get("model_artifact_s3_uri") or "").strip()


def stage_ply_candidates(stage: dict) -> list[str]:
    tile_id = str(stage.get("tile_id") or "").strip()
    if not tile_id:
        return []
    if stage.get("stage_type") == "context_density_tile":
        return [f"tiles/{tile_id}/splat.ply", "splat.ply"]
    return ["splat.ply"]


def stage_member_requests(stages: Sequence[dict]) -> list[dict]:
    requests: list[dict] = []
    for stage in stages:
        if stage.get("stage_type") not in MERGEABLE_STAGE_TYPES:
            continue
        uri = stage_artifact_uri(stage)
        candidates = stage_ply_candidates(stage)
        if not uri or not candidates:
            continue
        requests.append(
            {
                "stage_name": stage.get("stage_name"),
                "stage_type": stage.get("stage_type"),
                "tile_id": stage.get("tile_id"),
                "artifact_uri": uri,
                "candidate_members": candidates,
            }
        )
    return requests


def inventory_s3_tar_members(s3_uri: str, wanted_members: Sequence[str]) -> dict[str, int]:
    wanted = set(wanted_members)
    process = subprocess.Popen(
        ["aws", "s3", "cp", s3_uri, "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if process.stdout is None:
        raise RuntimeError("Failed to open aws stdout pipe")
    found: dict[str, int] = {}
    try:
        with tarfile.open(fileobj=process.stdout, mode="r|gz") as archive:
            for member in archive:
                if wanted and member.name not in wanted:
                    continue
                if member.isfile():
                    found[member.name] = int(member.size)
    except Exception:
        process.kill()
        process.wait(timeout=30)
        raise
    stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    returncode = process.wait()
    if returncode != 0:
        raise RuntimeError(f"aws s3 cp failed for {s3_uri}: {stderr.strip()}")
    return found


def bytes_to_gib(value: int | float) -> float:
    return round(float(value) / GIB, 4)


def build_disk_preflight(
    summary: dict,
    *,
    local_merge_output_dir: Path,
    available_bytes: int,
    inventory_loader: Callable[[str, Sequence[str]], dict[str, int]] = inventory_s3_tar_members,
    safety_margin_bytes: int,
    metadata_overhead_bytes: int,
    merge_output_multiplier: float,
    tile_materialization_mode: str = "symlink",
) -> dict:
    if tile_materialization_mode not in {"copy", "symlink"}:
        raise ValueError("tile_materialization_mode must be copy or symlink")
    requests = stage_member_requests(summary.get("stages", []))
    wanted_by_uri: dict[str, set[str]] = {}
    for request in requests:
        wanted_by_uri.setdefault(str(request["artifact_uri"]), set()).update(request["candidate_members"])

    inventory_by_uri: dict[str, dict[str, int]] = {}
    for uri, wanted in sorted(wanted_by_uri.items()):
        inventory_by_uri[uri] = inventory_loader(uri, sorted(wanted))

    stage_members: list[dict] = []
    missing_members: list[dict] = []
    input_ply_bytes = 0
    for request in requests:
        uri = str(request["artifact_uri"])
        inventory = inventory_by_uri.get(uri, {})
        selected_member = ""
        selected_size = 0
        for member_name in request["candidate_members"]:
            if member_name in inventory:
                selected_member = member_name
                selected_size = int(inventory[member_name])
                break
        record = {
            **request,
            "selected_member": selected_member,
            "selected_size_bytes": selected_size,
            "selected_size_gib": bytes_to_gib(selected_size),
        }
        stage_members.append(record)
        if not selected_member:
            missing_members.append(record)
            continue
        input_ply_bytes += selected_size

    extracted_stage_bytes = input_ply_bytes
    merge_tile_copy_bytes = input_ply_bytes if tile_materialization_mode == "copy" else 0
    estimated_merge_output_bytes = int(input_ply_bytes * merge_output_multiplier)
    estimated_required_bytes = (
        extracted_stage_bytes
        + merge_tile_copy_bytes
        + estimated_merge_output_bytes
        + metadata_overhead_bytes
    )
    required_with_safety_bytes = estimated_required_bytes + safety_margin_bytes

    block_reasons: list[str] = []
    if missing_members:
        block_reasons.append("missing_required_splat_members")
    if available_bytes < required_with_safety_bytes:
        block_reasons.append("insufficient_local_disk")

    return {
        "source_summary_json": summary.get("source_summary_json"),
        "local_merge_output_dir": str(local_merge_output_dir),
        "safe_to_local_merge": not block_reasons,
        "block_reasons": block_reasons,
        "available_bytes": int(available_bytes),
        "available_gib": bytes_to_gib(available_bytes),
        "input_ply_bytes": int(input_ply_bytes),
        "input_ply_gib": bytes_to_gib(input_ply_bytes),
        "extracted_stage_bytes": int(extracted_stage_bytes),
        "merge_tile_copy_bytes": int(merge_tile_copy_bytes),
        "estimated_merge_output_bytes": int(estimated_merge_output_bytes),
        "metadata_overhead_bytes": int(metadata_overhead_bytes),
        "safety_margin_bytes": int(safety_margin_bytes),
        "estimated_required_bytes": int(estimated_required_bytes),
        "estimated_required_gib": bytes_to_gib(estimated_required_bytes),
        "required_with_safety_bytes": int(required_with_safety_bytes),
        "required_with_safety_gib": bytes_to_gib(required_with_safety_bytes),
        "merge_output_multiplier": merge_output_multiplier,
        "tile_materialization_mode": tile_materialization_mode,
        "stage_member_count": len(stage_members),
        "stage_members": stage_members,
        "artifact_member_sizes": inventory_by_uri,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-json", required=True, help="Planner dry-run or wait summary JSON.")
    parser.add_argument(
        "--local-merge-output-dir",
        required=True,
        help="Directory that would be used for --local-merge-output-dir.",
    )
    parser.add_argument("--output-json", default="", help="Optional path to write the preflight JSON.")
    parser.add_argument("--safety-margin-gb", type=float, default=2.0)
    parser.add_argument("--metadata-overhead-mb", type=float, default=512.0)
    parser.add_argument("--merge-output-multiplier", type=float, default=1.25)
    parser.add_argument(
        "--tile-materialization-mode",
        choices=["copy", "symlink"],
        default="symlink",
        help="How run_tiled_3dgs_benchmark.py will expose tile dirs under merged/tile_outputs.",
    )
    parser.add_argument(
        "--fail-if-unsafe",
        action="store_true",
        help="Exit non-zero when the estimated local merge is unsafe.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = load_json(args.summary_json)
    summary["source_summary_json"] = args.summary_json
    merge_dir = Path(args.local_merge_output_dir).expanduser()
    usage = shutil.disk_usage(merge_dir.parent if merge_dir.parent.exists() else Path.cwd())
    result = build_disk_preflight(
        summary,
        local_merge_output_dir=merge_dir,
        available_bytes=usage.free,
        safety_margin_bytes=int(args.safety_margin_gb * GIB),
        metadata_overhead_bytes=int(args.metadata_overhead_mb * MIB),
        merge_output_multiplier=args.merge_output_multiplier,
        tile_materialization_mode=args.tile_materialization_mode,
    )
    payload = json.dumps(result, indent=2, sort_keys=True)
    print(payload)
    if args.output_json:
        Path(args.output_json).write_text(payload + "\n", encoding="utf-8")
    if args.fail_if_unsafe and not result["safe_to_local_merge"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
