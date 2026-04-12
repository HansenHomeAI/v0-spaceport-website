#!/usr/bin/env python3
"""Run the phase-2 MD1 hierarchy validation ladder and write a compact comparison."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_SCRIPT = REPO_ROOT / "scripts" / "sfm" / "run_sfm_benchmark.py"


def run_command(command: List[str], *, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        capture_output=capture_output,
    )


def load_json(path_or_s3_uri: str) -> dict:
    if path_or_s3_uri.startswith("s3://"):
        result = run_command(["aws", "s3", "cp", path_or_s3_uri, "-"], capture_output=True)
        return json.loads(result.stdout)
    return json.loads(Path(path_or_s3_uri).expanduser().resolve().read_text(encoding="utf-8"))


def aws_json(*args: str) -> dict:
    result = run_command(["aws", *args, "--output", "json"], capture_output=True)
    return json.loads(result.stdout)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Local path or s3:// URI for the MD1 manifest")
    parser.add_argument("--baseline-image-uri", required=True, help="Control image URI by digest")
    parser.add_argument("--candidate-image-uri", default="", help="Experimental image URI by digest")
    parser.add_argument("--branch", default="", help="Branch name override")
    parser.add_argument("--output-dir", required=True, help="Local directory for run summaries and comparison JSON")
    parser.add_argument("--job-prefix", default="md1phase2", help="Benchmark job prefix")
    parser.add_argument("--instance-type", default="ml.g4dn.xlarge")
    parser.add_argument("--volume-size-gb", default="120")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument(
        "--subset-name",
        action="append",
        default=[],
        help="Optional subset filter. Repeat to run only selected subsets.",
    )
    return parser.parse_args()


def subset_input_uri(manifest_uri: str, subset_name: str) -> str:
    manifest_name = Path(manifest_uri).name
    subset_directory = "subsets" if manifest_name == "probe_manifest.json" else "probes"
    if manifest_uri.startswith("s3://"):
        return manifest_uri.rsplit("/", 1)[0] + f"/{subset_directory}/{subset_name}.zip"
    return str(Path(manifest_uri).expanduser().resolve().parent / subset_directory / f"{subset_name}.zip")


def subset_image_count(manifest_section: dict, subset_name: str) -> int:
    subset_value = manifest_section.get(subset_name)
    if isinstance(subset_value, dict):
        image_count = subset_value.get("image_count")
        if isinstance(image_count, int):
            return image_count
        images = subset_value.get("images")
        if isinstance(images, list):
            return len(images)
    if isinstance(subset_value, list):
        return len(subset_value)
    return 0


def run_benchmark(
    *,
    branch: str,
    input_s3_uri: str,
    image_uri: str,
    subset_strategy: str,
    summary_json_output: Path,
    job_prefix: str,
    instance_type: str,
    volume_size_gb: str,
    poll_seconds: int,
    env: Dict[str, str] | None = None,
) -> dict:
    command = [
        "python3",
        str(BENCHMARK_SCRIPT),
        "--input-s3-uri",
        input_s3_uri,
        "--job-prefix",
        job_prefix,
        "--instance-type",
        instance_type,
        "--volume-size-gb",
        volume_size_gb,
        "--mode",
        "chunked",
        "--subset-strategy",
        subset_strategy,
        "--summary-json-output",
        str(summary_json_output),
        "--wait",
        "--poll-seconds",
        str(poll_seconds),
    ]
    if branch:
        command.extend(["--branch", branch])
    if image_uri:
        command.extend(["--image-uri", image_uri])
    for key, value in (env or {}).items():
        command.extend(["--env", f"{key}={value}"])
    run_command(command)
    return json.loads(summary_json_output.read_text(encoding="utf-8"))


def fetch_job_metadata(job_name: str, metadata_output_path: Path) -> Tuple[dict, str]:
    job = aws_json("sagemaker", "describe-processing-job", "--processing-job-name", job_name)
    output_s3_uri = job["ProcessingOutputConfig"]["Outputs"][0]["S3Output"]["S3Uri"].rstrip("/")
    metadata = load_json(f"{output_s3_uri}/sfm_metadata.json")
    metadata_output_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata, output_s3_uri


def summarize_row(summary: dict, metadata: dict) -> dict:
    filtered_sparse = metadata.get("filtered_sparse_summary", {})
    return {
        "job_name": summary.get("job_name"),
        "processing_time_seconds": metadata.get("processing_time_seconds"),
        "images_registered": metadata.get("images_registered"),
        "points_3d": metadata.get("points_3d"),
        "verified_pairs_total": metadata.get("verified_pairs_total"),
        "mapper_seconds_per_registered_image": metadata.get("mapper_seconds_per_registered_image"),
        "chunk_count": metadata.get("chunk_count"),
        "bundle_adjusted_node_count": metadata.get("bundle_adjusted_node_count"),
        "max_bundle_adjusted_image_count": metadata.get("max_bundle_adjusted_image_count"),
        "skipped_seam_merge_count": metadata.get("skipped_seam_merge_count"),
        "top_level_ba_ran": metadata.get("chunk_merge_proof", {}).get("top_level_ba_ran"),
        "weak_far_context_points_rejected": filtered_sparse.get("weak_far_context_points_rejected"),
        "core_filtered_points_3d": filtered_sparse.get("core_filtered_points_3d"),
        "far_context_points_3d": filtered_sparse.get("far_context_points_3d"),
        "filtered_points_3d": filtered_sparse.get("filtered_points_3d"),
    }


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_json(args.manifest)
    probe_subsets = manifest.get("probe_subsets", {})
    ladder_subsets = manifest.get("ladder_subsets", {})
    ordered_subset_names = [
        name
        for name in ("geometry_mix", "cross_pass", "horizon_context", "ladder_1000", "ladder_2000")
        if name in probe_subsets or name in ladder_subsets
    ]
    if args.subset_name:
        requested = {name.strip() for name in args.subset_name if name.strip()}
        ordered_subset_names = [name for name in ordered_subset_names if name in requested]
    if not ordered_subset_names:
        raise RuntimeError("Manifest does not contain any probe_subsets or ladder_subsets")

    candidate_env = {
        "COLMAP_CHUNK_PLANNER": "footprint_graph_v1",
        "COLMAP_PARENT_MERGE_MODE": "seam_only_v1",
        "COLMAP_HIERARCHY_MODE": "balanced_tree_v1",
        "COLMAP_SEAM_FRONTIER_MODE": "frontier_only",
        "COLMAP_TOP_LEVEL_BA_MODE": "below_threshold",
        "COLMAP_TOP_LEVEL_BA_IMAGE_THRESHOLD": "900",
        "COLMAP_LEAF_TARGET_IMAGES": "144",
        "COLMAP_LEAF_HARD_CAP": "176",
        "COLMAP_PAIR_CAP_LOCAL": "8",
        "COLMAP_PAIR_CAP_REVISIT": "3",
        "COLMAP_PAIR_CAP_SEAM": "3",
    }
    full_input_uri = str(manifest.get("input") or "").strip()

    comparison: Dict[str, object] = {
        "manifest": args.manifest,
        "baseline_image_uri": args.baseline_image_uri,
        "candidate_image_uri": args.candidate_image_uri,
        "subsets": {},
    }
    for subset_name in ordered_subset_names:
        baseline_env: Dict[str, str] | None = None
        candidate_subset_env = dict(candidate_env)
        if full_input_uri:
            input_uri = full_input_uri
            baseline_env = {
                "COLMAP_INPUT_SUBSET_MANIFEST_URI": args.manifest,
                "COLMAP_INPUT_SUBSET_NAME": subset_name,
            }
            candidate_subset_env.update(baseline_env)
        else:
            input_uri = subset_input_uri(args.manifest, subset_name)
        baseline_summary = run_benchmark(
            branch=args.branch,
            input_s3_uri=input_uri,
            image_uri=args.baseline_image_uri,
            subset_strategy=f"md1_phase2_baseline_{subset_name}",
            summary_json_output=output_dir / f"baseline-{subset_name}-summary.json",
            job_prefix=f"{args.job_prefix}base{subset_name[:5]}",
            instance_type=args.instance_type,
            volume_size_gb=args.volume_size_gb,
            poll_seconds=args.poll_seconds,
            env=baseline_env,
        )
        baseline_metadata, baseline_output_s3_uri = fetch_job_metadata(
            baseline_summary["job_name"],
            output_dir / f"baseline-{subset_name}-sfm_metadata.json",
        )
        baseline_summary["output_s3_uri"] = baseline_output_s3_uri

        candidate_summary = run_benchmark(
            branch=args.branch,
            input_s3_uri=input_uri,
            image_uri=args.candidate_image_uri,
            subset_strategy=f"md1_phase2_candidate_{subset_name}",
            summary_json_output=output_dir / f"candidate-{subset_name}-summary.json",
            job_prefix=f"{args.job_prefix}cand{subset_name[:5]}",
            instance_type=args.instance_type,
            volume_size_gb=args.volume_size_gb,
            poll_seconds=args.poll_seconds,
            env=candidate_subset_env,
        )
        candidate_metadata, candidate_output_s3_uri = fetch_job_metadata(
            candidate_summary["job_name"],
            output_dir / f"candidate-{subset_name}-sfm_metadata.json",
        )
        candidate_summary["output_s3_uri"] = candidate_output_s3_uri

        baseline_row = summarize_row(baseline_summary, baseline_metadata)
        candidate_row = summarize_row(candidate_summary, candidate_metadata)
        subset_size = subset_image_count(probe_subsets if subset_name in probe_subsets else ladder_subsets, subset_name)
        comparison["subsets"][subset_name] = {
            "image_count": subset_size,
            "baseline": baseline_row,
            "candidate": candidate_row,
            "runtime_delta_seconds": (
                (candidate_row["processing_time_seconds"] or 0) - (baseline_row["processing_time_seconds"] or 0)
            ),
            "registration_delta": (
                (candidate_row["images_registered"] or 0) - (baseline_row["images_registered"] or 0)
            ),
        }

    comparison_path = output_dir / "phase2-comparison.json"
    comparison_path.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(comparison, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
