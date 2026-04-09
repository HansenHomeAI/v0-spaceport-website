#!/usr/bin/env python3
"""Run the phase-1 MD1 probe validation ladder and write a compact comparison."""

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
    parser.add_argument("--manifest", required=True, help="Local path or s3:// URI for the MD1 probe manifest")
    parser.add_argument("--baseline-image-uri", required=True, help="Frozen control image URI by digest")
    parser.add_argument(
        "--candidate-image-uri",
        default="",
        help="Experimental image URI by digest. Defaults to the current branch tag via run_sfm_benchmark.py",
    )
    parser.add_argument("--branch", default="", help="Branch name override")
    parser.add_argument("--output-dir", required=True, help="Local directory for run summaries and comparison JSON")
    parser.add_argument("--job-prefix", default="md1phase1", help="Benchmark job prefix")
    parser.add_argument("--instance-type", default="ml.g4dn.xlarge")
    parser.add_argument("--volume-size-gb", default="100")
    parser.add_argument("--poll-seconds", type=int, default=60)
    return parser.parse_args()


def probe_input_uri(manifest_uri: str, probe_name: str) -> str:
    manifest_name = Path(manifest_uri).name
    probe_directory = "subsets" if manifest_name == "probe_manifest.json" else "probes"
    if manifest_uri.startswith("s3://"):
        return manifest_uri.rsplit("/", 1)[0] + f"/{probe_directory}/{probe_name}.zip"
    return str(Path(manifest_uri).expanduser().resolve().parent / probe_directory / f"{probe_name}.zip")


def probe_image_count(manifest: dict, probe_name: str) -> int:
    probe_value = manifest.get("probe_subsets", {}).get(probe_name)
    if isinstance(probe_value, dict):
        image_count = probe_value.get("image_count")
        if isinstance(image_count, int):
            return image_count
        images = probe_value.get("images")
        if isinstance(images, list):
            return len(images)
    if isinstance(probe_value, list):
        return len(probe_value)
    details = manifest.get("probe_subset_details", {}).get(probe_name, {})
    if isinstance(details, dict) and isinstance(details.get("image_count"), int):
        return int(details["image_count"])
    return 0


def run_benchmark(
    *,
    branch: str,
    input_s3_uri: str,
    image_uri: str,
    mode: str,
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
        mode,
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


def compare_rows(baseline: dict, candidate: dict, *, baseline_metadata: dict, candidate_metadata: dict) -> dict:
    baseline_registered = baseline.get("images_registered") or 0
    candidate_registered = candidate.get("images_registered") or 0
    baseline_pairs = baseline.get("chunk_role_counts") or {}
    candidate_pairs = candidate.get("chunk_role_counts") or {}
    return {
        "baseline_job_name": baseline.get("job_name"),
        "candidate_job_name": candidate.get("job_name"),
        "baseline_registered": baseline_registered,
        "candidate_registered": candidate_registered,
        "registered_delta": candidate_registered - baseline_registered,
        "baseline_dataset_image_count": baseline.get("dataset_image_count"),
        "candidate_dataset_image_count": candidate.get("dataset_image_count"),
        "baseline_mapper_seconds_per_registered_image": baseline.get("mapper_seconds_per_registered_image"),
        "candidate_mapper_seconds_per_registered_image": candidate.get("mapper_seconds_per_registered_image"),
        "baseline_chunk_count": baseline.get("chunk_count"),
        "candidate_chunk_count": candidate.get("chunk_count"),
        "baseline_chunk_matcher_strategy": baseline.get("chunk_matcher_strategy"),
        "candidate_chunk_matcher_strategy": candidate.get("chunk_matcher_strategy"),
        "baseline_role_counts": baseline_pairs,
        "candidate_role_counts": candidate_pairs,
        "baseline_verified_pairs_total": baseline_metadata.get("verified_pairs_total"),
        "candidate_verified_pairs_total": candidate_metadata.get("verified_pairs_total"),
        "baseline_chunk_merge_proof": baseline_metadata.get("chunk_merge_proof"),
        "candidate_chunk_merge_proof": candidate_metadata.get("chunk_merge_proof"),
    }


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_json(args.manifest)
    probes = manifest.get("probe_subsets", {})
    if not probes:
        raise RuntimeError("Probe manifest does not contain any probe_subsets")

    smallest_probe = min(
        probes.items(),
        key=lambda item: (probe_image_count(manifest, item[0]), item[0]),
    )[0]

    baseline_results: Dict[str, dict] = {}
    candidate_results: Dict[str, dict] = {}
    comparison: Dict[str, dict] = {
        "manifest": args.manifest,
        "baseline_image_uri": args.baseline_image_uri,
        "candidate_image_uri": args.candidate_image_uri,
        "smallest_probe": smallest_probe,
        "probes": {},
    }

    ordered_probe_names = ["geometry_mix", "cross_pass", "horizon_context"]
    ordered_probe_names = [name for name in ordered_probe_names if name in probes]

    for probe_name in ordered_probe_names:
        input_uri = probe_input_uri(args.manifest, probe_name)
        baseline_summary = run_benchmark(
            branch=args.branch,
            input_s3_uri=input_uri,
            image_uri=args.baseline_image_uri,
            mode="chunked",
            subset_strategy=f"md1_phase1_baseline_{probe_name}",
            summary_json_output=output_dir / f"baseline-{probe_name}-chunked-summary.json",
            job_prefix=f"{args.job_prefix}base{probe_name[:5]}",
            instance_type=args.instance_type,
            volume_size_gb=args.volume_size_gb,
            poll_seconds=args.poll_seconds,
        )
        baseline_results[probe_name] = baseline_summary
        baseline_metadata, baseline_output_s3_uri = fetch_job_metadata(
            baseline_summary["job_name"],
            output_dir / f"baseline-{probe_name}-sfm_metadata.json",
        )
        baseline_summary["output_s3_uri"] = baseline_output_s3_uri

        candidate_summary = run_benchmark(
            branch=args.branch,
            input_s3_uri=input_uri,
            image_uri=args.candidate_image_uri,
            mode="chunked",
            subset_strategy=f"md1_phase1_footprint_graph_{probe_name}",
            summary_json_output=output_dir / f"candidate-{probe_name}-chunked-summary.json",
            job_prefix=f"{args.job_prefix}cand{probe_name[:5]}",
            instance_type=args.instance_type,
            volume_size_gb=args.volume_size_gb,
            poll_seconds=args.poll_seconds,
            env={"COLMAP_CHUNK_PLANNER": "footprint_graph_v1"},
        )
        candidate_results[probe_name] = candidate_summary
        candidate_metadata, candidate_output_s3_uri = fetch_job_metadata(
            candidate_summary["job_name"],
            output_dir / f"candidate-{probe_name}-sfm_metadata.json",
        )
        candidate_summary["output_s3_uri"] = candidate_output_s3_uri

        comparison["probes"][probe_name] = compare_rows(
            baseline_summary,
            candidate_summary,
            baseline_metadata=baseline_metadata,
            candidate_metadata=candidate_metadata,
        )

    monolithic_probe_uri = probe_input_uri(args.manifest, smallest_probe)
    monolithic_summary = run_benchmark(
        branch=args.branch,
        input_s3_uri=monolithic_probe_uri,
        image_uri=args.baseline_image_uri,
        mode="monolithic",
        subset_strategy=f"md1_phase1_baseline_monolithic_{smallest_probe}",
        summary_json_output=output_dir / f"baseline-{smallest_probe}-monolithic-summary.json",
        job_prefix=f"{args.job_prefix}mono{smallest_probe[:5]}",
        instance_type=args.instance_type,
        volume_size_gb=args.volume_size_gb,
        poll_seconds=args.poll_seconds,
    )
    monolithic_metadata, monolithic_output_s3_uri = fetch_job_metadata(
        monolithic_summary["job_name"],
        output_dir / f"baseline-{smallest_probe}-monolithic-sfm_metadata.json",
    )
    monolithic_summary["output_s3_uri"] = monolithic_output_s3_uri
    comparison["baseline_monolithic_smallest_probe"] = monolithic_summary
    comparison["baseline_monolithic_smallest_probe_metadata"] = {
        "verified_pairs_total": monolithic_metadata.get("verified_pairs_total"),
        "images_registered": monolithic_metadata.get("images_registered"),
        "points_3d": monolithic_metadata.get("points_3d"),
    }

    comparison_path = output_dir / "phase1-comparison.json"
    comparison_path.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(comparison, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
