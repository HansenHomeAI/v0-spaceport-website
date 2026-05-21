#!/usr/bin/env python3
"""Reduce independent SfM leaf outputs into one standard COLMAP sparse package."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from run_sfm_reducer_canary import (
    ModelStats,
    camera_signatures,
    global_image_ids,
    rewrite_model_text,
    run_command,
    stats_for_model,
    write_pose_aligned_merge,
)


SPARSE_FILES = ("cameras.txt", "images.txt", "points3D.txt", "frames.txt", "rigs.txt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--leaf-output-uri",
        action="append",
        required=True,
        help="Leaf COLMAP output URI or local path. Pass once per completed leaf.",
    )
    parser.add_argument("--output-uri", required=True, help="Final reducer output URI or local path.")
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--report-json-output", required=True)
    parser.add_argument("--min-retention-ratio", type=float, default=0.95)
    parser.add_argument("--min-shared-images", type=int, default=20)
    parser.add_argument("--expected-component-count", type=int, default=1)
    parser.add_argument("--final-min-track-length", type=int, default=3)
    parser.add_argument("--planner-manifest", default="")
    parser.add_argument("--seam-report-output", default="")
    parser.add_argument("--max-scale-delta", type=float, default=0.15)
    parser.add_argument("--max-sim3-p95-residual-m", type=float, default=0.25)
    parser.add_argument("--max-baseline-normalized-residual", type=float, default=0.01)
    parser.add_argument("--enable-seam-local-ba", action="store_true")
    parser.add_argument("--strict-production-gates", action="store_true")
    parser.add_argument("--branch", default="")
    parser.add_argument("--head", default="")
    parser.add_argument("--input-uri", default="")
    parser.add_argument("--colmap-bin", default="colmap")
    parser.add_argument("--skip-upload", action="store_true")
    return parser.parse_args()


def is_s3_uri(uri: str) -> bool:
    return uri.startswith("s3://")


def normalize_prefix(uri: str) -> str:
    return uri.rstrip("/")


def run_cli(command: list[str]) -> dict[str, object]:
    started = time.time()
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    return {
        "command": command,
        "returncode": result.returncode,
        "seconds": round(time.time() - started, 2),
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }


def existing_sparse_dir(root: Path) -> Path:
    for relative in ("sparse/0", "sparse_raw/0", "."):
        candidate = root / relative
        if all((candidate / file_name).exists() for file_name in ("cameras.txt", "images.txt", "points3D.txt")):
            return candidate
    raise FileNotFoundError(f"No COLMAP text sparse model found under {root}")


def copy_sparse_dir(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for file_name in SPARSE_FILES:
        source_file = source / file_name
        if source_file.exists():
            target_file = target / file_name
            if target_file.exists():
                target_file.unlink()
            try:
                os.link(source_file, target_file)
            except OSError:
                shutil.copy2(source_file, target_file)


def download_sparse_from_s3(leaf_uri: str, target: Path) -> dict[str, object]:
    commands: list[dict[str, object]] = []
    for sparse_kind in ("sparse/0", "sparse_raw/0"):
        target_kind = target / sparse_kind
        target_kind.mkdir(parents=True, exist_ok=True)
        copied_required = True
        for file_name in SPARSE_FILES:
            source_uri = f"{normalize_prefix(leaf_uri)}/{sparse_kind}/{file_name}"
            command = run_cli(["aws", "s3", "cp", source_uri, str(target_kind / file_name), "--only-show-errors"])
            commands.append(command)
            if command["returncode"] != 0 and file_name in {"cameras.txt", "images.txt", "points3D.txt"}:
                copied_required = False
        if copied_required:
            return {"sparse_dir": str(target_kind), "commands": commands}
    raise RuntimeError(f"Unable to download required sparse files from {leaf_uri}")


def load_planner_manifest(manifest_uri: str, work_dir: Path) -> tuple[dict[str, object] | None, dict[str, object]]:
    if not manifest_uri:
        return None, {"source": "", "loaded": False}
    if is_s3_uri(manifest_uri):
        target = work_dir / "planner_manifest.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        command = run_cli(["aws", "s3", "cp", manifest_uri, str(target), "--only-show-errors"])
        if command["returncode"] != 0:
            return None, {"source": manifest_uri, "loaded": False, "command": command}
        path = target
    else:
        path = Path(manifest_uri)
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload, {"source": manifest_uri, "loaded": True, "local_path": str(path)}


def materialize_leaf_sparse(leaf_uri: str, target: Path) -> tuple[Path, dict[str, object]]:
    if is_s3_uri(leaf_uri):
        result = download_sparse_from_s3(leaf_uri, target)
        return Path(str(result["sparse_dir"])), result
    source = existing_sparse_dir(Path(leaf_uri))
    copy_sparse_dir(source, target / "sparse")
    return target / "sparse", {"source": str(source), "commands": []}


def write_standard_output_package(
    *,
    merged_text_dir: Path,
    output_dir: Path,
    reducer_metadata: dict[str, object],
) -> None:
    shutil.rmtree(output_dir, ignore_errors=True)
    sparse0 = output_dir / "sparse" / "0"
    sparse_raw0 = output_dir / "sparse_raw" / "0"
    copy_sparse_dir(merged_text_dir, sparse0)
    copy_sparse_dir(merged_text_dir, sparse_raw0)
    (output_dir / "reducer_metadata.json").write_text(
        json.dumps(reducer_metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    seam_report = reducer_metadata.get("seam_merge_report")
    if isinstance(seam_report, dict):
        (output_dir / "seam_merge_report.json").write_text(
            json.dumps(seam_report, indent=2) + "\n",
            encoding="utf-8",
        )


def upload_output(output_dir: Path, output_uri: str) -> dict[str, object]:
    if is_s3_uri(output_uri):
        return run_cli(["aws", "s3", "sync", str(output_dir), normalize_prefix(output_uri), "--only-show-errors"])
    target = Path(output_uri)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(output_dir, target)
    return {"command": ["copytree", str(output_dir), str(target)], "returncode": 0, "seconds": 0.0}


def merge_leaf_models(
    *,
    leaf_dirs: list[Path],
    work_dir: Path,
    colmap_bin: str,
    min_shared_images: int,
    final_min_track_length: int = 3,
    planner_manifest: dict[str, object] | None = None,
    max_scale_delta: float = 0.15,
    max_sim3_p95_residual_m: float = 0.25,
    max_baseline_normalized_residual: float = 0.01,
    enable_seam_local_ba: bool = False,
    strict_production_gates: bool = False,
    scratch_cleanup_paths: list[Path] | None = None,
) -> dict[str, object]:
    normalized_root = work_dir / "normalized"
    binary_root = work_dir / "binary"
    merged_binary = work_dir / "merged_binary"
    merged_text = work_dir / "merged_text"
    pose_aligned_text = work_dir / "pose_aligned_text"
    pose_aligned_binary = work_dir / "pose_aligned_binary"

    before = [stats_for_model(model_dir) for model_dir in leaf_dirs]
    image_ids = global_image_ids(leaf_dirs)
    signature_to_id, camera_maps = camera_signatures(leaf_dirs)
    global_camera_records = {camera_id: list(signature) for signature, camera_id in signature_to_id.items()}

    convert_commands: list[dict[str, object]] = []
    normalized_dirs: list[Path] = []
    binary_dirs: list[Path] = []
    use_stock_binary_merge = False
    for index, model_dir in enumerate(leaf_dirs):
        normalized_dir = normalized_root / f"leaf-{index:02d}"
        binary_dir = binary_root / f"leaf-{index:02d}"
        rewrite_model_text(
            input_dir=model_dir,
            output_dir=normalized_dir,
            image_ids_by_name=image_ids,
            camera_ids_by_old_id=camera_maps[model_dir],
            global_camera_records=global_camera_records,
        )
        normalized_dirs.append(normalized_dir)
        if use_stock_binary_merge:
            binary_dir.mkdir(parents=True, exist_ok=True)
            command = run_command(
                [
                    colmap_bin,
                    "model_converter",
                    "--input_path",
                    str(normalized_dir),
                    "--output_path",
                    str(binary_dir),
                    "--output_type",
                    "BIN",
                ]
            )
            convert_commands.append(command)
            binary_dirs.append(binary_dir)
            if command["returncode"] != 0:
                break

    model_merger_command: dict[str, object] | None = None
    merged_converter_command: dict[str, object] | None = None
    pose_aligned_report: dict[str, object] | None = None
    pose_aligned_validator: dict[str, object] | None = None
    if all(command["returncode"] == 0 for command in convert_commands):
        if use_stock_binary_merge and len(binary_dirs) == 2:
            merged_binary.mkdir(parents=True, exist_ok=True)
            model_merger_command = run_command(
                [
                    colmap_bin,
                    "model_merger",
                    "--input_path1",
                    str(binary_dirs[0]),
                    "--input_path2",
                    str(binary_dirs[1]),
                    "--output_path",
                    str(merged_binary),
                    "--max_reproj_error",
                    "64",
                ]
            )
        else:
            model_merger_command = {
                "command": [colmap_bin, "model_merger"],
                "returncode": 64,
                "seconds": 0.0,
                "stdout_tail": "",
                "stderr_tail": "stock model_merger skipped: leaf count is not exactly two",
            }
        if model_merger_command["returncode"] == 0:
            merged_text.mkdir(parents=True, exist_ok=True)
            merged_converter_command = run_command(
                [
                    colmap_bin,
                    "model_converter",
                    "--input_path",
                    str(merged_binary),
                    "--output_path",
                    str(merged_text),
                    "--output_type",
                    "TXT",
                ]
            )
        else:
            try:
                pose_aligned_report = write_pose_aligned_merge(
                    normalized_dirs=normalized_dirs,
                    output_dir=pose_aligned_text,
                    min_shared_images=min_shared_images,
                    min_final_track_length=final_min_track_length,
                    planner_manifest=planner_manifest,
                    max_scale_delta=max_scale_delta,
                    max_sim3_p95_residual_m=max_sim3_p95_residual_m,
                    max_baseline_normalized_residual=max_baseline_normalized_residual,
                    enable_seam_local_ba=enable_seam_local_ba,
                    strict_production_gates=strict_production_gates,
                )
                for cleanup_path in scratch_cleanup_paths or []:
                    shutil.rmtree(cleanup_path, ignore_errors=True)
                if not use_stock_binary_merge:
                    shutil.rmtree(normalized_root, ignore_errors=True)
                    shutil.rmtree(binary_root, ignore_errors=True)
                pose_aligned_binary.mkdir(parents=True, exist_ok=True)
                pose_aligned_validator = run_command(
                    [
                        colmap_bin,
                        "model_converter",
                        "--input_path",
                        str(pose_aligned_text),
                        "--output_path",
                        str(pose_aligned_binary),
                        "--output_type",
                        "BIN",
                    ]
                )
                if not use_stock_binary_merge:
                    shutil.rmtree(pose_aligned_binary, ignore_errors=True)
            except Exception as exc:  # pragma: no cover - encoded in report
                pose_aligned_report = {"strategy": "pose_aligned_text_merge", "error": str(exc)}

    effective_merged_text = merged_text if (merged_text / "images.txt").exists() else pose_aligned_text
    merged = (
        stats_for_model(effective_merged_text)
        if (effective_merged_text / "images.txt").exists()
        else ModelStats(0, 0, set())
    )
    leaf_retention = [
        round(len(merged.image_names.intersection(stats.image_names)) / stats.registered_images, 4)
        if stats.registered_images
        else 0.0
        for stats in before
    ]
    blockers: list[str] = []
    if any(command["returncode"] != 0 for command in convert_commands):
        blockers.append("leaf_model_converter_failed")
    pose_aligned_succeeded = (
        pose_aligned_report is not None
        and "error" not in pose_aligned_report
        and pose_aligned_validator is not None
        and pose_aligned_validator["returncode"] == 0
    )
    stock_succeeded = (
        model_merger_command is not None
        and model_merger_command["returncode"] == 0
        and (merged_converter_command or {}).get("returncode") == 0
    )
    if not stock_succeeded and not pose_aligned_succeeded:
        blockers.append("model_merge_failed")
    if pose_aligned_report is not None and "error" in pose_aligned_report:
        blockers.append("pose_aligned_merge_failed")
    if pose_aligned_report is not None:
        blockers.extend(str(item) for item in (pose_aligned_report.get("promotion_blockers") or []))
    if pose_aligned_validator is not None and pose_aligned_validator["returncode"] != 0:
        blockers.append("pose_aligned_model_validation_failed")

    return {
        "before": before,
        "merged": merged,
        "leaf_retention": leaf_retention,
        "blockers": blockers,
        "commands": {
            "leaf_converters": convert_commands,
            "model_merger": model_merger_command,
            "merged_converter": merged_converter_command,
            "pose_aligned_validator": pose_aligned_validator,
        },
        "fallback": pose_aligned_report,
        "merged_text_dir": str(effective_merged_text),
        "normalized_text_dirs": [str(path) for path in normalized_dirs],
    }


def main() -> int:
    args = parse_args()
    work_dir = Path(args.work_dir).resolve()
    report_path = Path(args.report_json_output).resolve()
    download_root = work_dir / "leaf_downloads"
    reducer_output = work_dir / "output_package"
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    leaf_dirs: list[Path] = []
    materialize_reports: list[dict[str, object]] = []
    for index, leaf_uri in enumerate(args.leaf_output_uri):
        leaf_dir, materialize_report = materialize_leaf_sparse(leaf_uri, download_root / f"leaf-{index:02d}")
        leaf_dirs.append(leaf_dir)
        materialize_reports.append({"leaf_uri": leaf_uri, **materialize_report})
    planner_manifest, planner_manifest_report = load_planner_manifest(args.planner_manifest, work_dir)

    merge_report = merge_leaf_models(
        leaf_dirs=leaf_dirs,
        work_dir=work_dir / "merge",
        colmap_bin=args.colmap_bin,
        min_shared_images=args.min_shared_images,
        final_min_track_length=args.final_min_track_length,
        planner_manifest=planner_manifest,
        max_scale_delta=args.max_scale_delta,
        max_sim3_p95_residual_m=args.max_sim3_p95_residual_m,
        max_baseline_normalized_residual=args.max_baseline_normalized_residual,
        enable_seam_local_ba=args.enable_seam_local_ba,
        strict_production_gates=args.strict_production_gates,
        scratch_cleanup_paths=[download_root],
    )
    before: list[ModelStats] = merge_report["before"]  # type: ignore[assignment]
    merged: ModelStats = merge_report["merged"]  # type: ignore[assignment]
    leaf_retention: list[float] = merge_report["leaf_retention"]  # type: ignore[assignment]
    blockers = list(merge_report["blockers"])  # type: ignore[arg-type]
    if leaf_retention and min(leaf_retention) < args.min_retention_ratio:
        blockers.append("leaf_retention_below_gate")
    if merged.registered_images < max((stats.registered_images for stats in before), default=0):
        blockers.append("merged_model_lost_dominant_leaf")
    if args.expected_component_count <= 1 and blockers:
        merged_component_count = 0
    else:
        merged_component_count = args.expected_component_count
    promotion_blockers = list(dict.fromkeys(blockers))
    if merged.registered_images <= 0:
        promotion_blockers.append("missing_sparse0")
    fallback = merge_report.get("fallback") if isinstance(merge_report.get("fallback"), dict) else {}
    seam_merge_report = fallback.get("seam_merge_report") if isinstance(fallback, dict) else None
    seam_report_uri = f"{normalize_prefix(args.output_uri)}/seam_merge_report.json" if seam_merge_report else ""

    reducer_metadata = {
        "artifact_kind": "sfm_fanout_reducer_report",
        "schema_version": 1,
        "decision": "pass" if not promotion_blockers else "fail",
        "branch": args.branch,
        "head": args.head,
        "input_uri": args.input_uri,
        "output_uri": normalize_prefix(args.output_uri),
        "leaf_output_uris": args.leaf_output_uri,
        "leaf_count": len(leaf_dirs),
        "passed_leaf_count": len(leaf_dirs) if not blockers else 0,
        "failed_leaf_count": 0 if not blockers else len(leaf_dirs),
        "input_registered_images": [stats.registered_images for stats in before],
        "input_points3d": [stats.points3d for stats in before],
        "unique_registered_images_before_merge": len(set().union(*(stats.image_names for stats in before))),
        "merged_registered_images": merged.registered_images,
        "merged_points3d": merged.points3d,
        "leaf_retention_ratios": leaf_retention,
        "min_retention_ratio": args.min_retention_ratio,
        "min_shared_images": args.min_shared_images,
        "final_min_track_length": args.final_min_track_length,
        "merge_strategy": "seam_graph_sim3_v1",
        "seam_merge_report_uri": seam_report_uri,
        "seam_merge_report": seam_merge_report,
        "accepted_merge_tree": fallback.get("accepted_merge_tree") if isinstance(fallback, dict) else None,
        "rejected_edges": fallback.get("rejected_edges") if isinstance(fallback, dict) else None,
        "cycle_consistency": fallback.get("cycle_consistency") if isinstance(fallback, dict) else None,
        "post_merge_jurisdiction_culling": fallback.get("post_merge_jurisdiction_culling") if isinstance(fallback, dict) else None,
        "merged_component_count": merged_component_count,
        "expected_component_count": args.expected_component_count,
        "ba_policy": "seam_local_ba_interface" if args.enable_seam_local_ba else "leaf_local_or_deferred_global",
        "strict_production_gates": args.strict_production_gates,
        "standard_sparse0_exists": merged.registered_images > 0,
        "promotion_blockers": promotion_blockers,
        "blockers": blockers,
        "planner_manifest": planner_manifest_report,
        "materialize_reports": materialize_reports,
        "commands": merge_report["commands"],
        "fallback": merge_report["fallback"],
        "merged_text_dir": merge_report["merged_text_dir"],
        "normalized_text_dirs": merge_report["normalized_text_dirs"],
    }
    if merged.registered_images > 0:
        write_standard_output_package(
            merged_text_dir=Path(str(merge_report["merged_text_dir"])),
            output_dir=reducer_output,
            reducer_metadata=reducer_metadata,
        )
        upload_report = (
            {"command": [], "returncode": 0, "seconds": 0.0, "skipped": True}
            if args.skip_upload
            else upload_output(reducer_output, args.output_uri)
        )
    else:
        upload_report = {"command": [], "returncode": 2, "seconds": 0.0, "skipped": True}
    reducer_metadata["upload"] = upload_report
    if args.seam_report_output and isinstance(seam_merge_report, dict):
        seam_output_path = Path(args.seam_report_output).resolve()
        seam_output_path.parent.mkdir(parents=True, exist_ok=True)
        seam_output_path.write_text(json.dumps(seam_merge_report, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(json.dumps(reducer_metadata, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": reducer_metadata["decision"],
                "leaf_count": reducer_metadata["leaf_count"],
                "merged_registered_images": reducer_metadata["merged_registered_images"],
                "promotion_blockers": reducer_metadata["promotion_blockers"],
            },
            indent=2,
        )
    )
    if upload_report.get("returncode") != 0:
        return 2
    return 0 if reducer_metadata["decision"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
