#!/usr/bin/env python3
"""Run the hybrid SfM proof frontier from representative subsets through full proof."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_SCRIPT = REPO_ROOT / "scripts" / "sfm" / "run_sfm_benchmark.py"
STATE_PATH = REPO_ROOT / "STATE.md"
LOG_PATH = REPO_ROOT / "logs" / "agent-loop.log"
FRONTIER_DIR = REPO_ROOT / "logs" / "sfm-proof-frontier"
FRONTIER_PATH = FRONTIER_DIR / "frontier.json"
RESULTS_DIR = FRONTIER_DIR / "results"
OPERATOR_CONTRACT_PATH = FRONTIER_DIR / "operator_contract.md"
AWS_CLI = shutil.which("aws") or (
    "/opt/homebrew/bin/aws" if Path("/opt/homebrew/bin/aws").exists() else "aws"
)

REGISTERED_RATIO_GATE = 0.98
POINTS_PER_IMAGE_GATE = 568.0
END_TO_END_SPEEDUP_GATE = 1.5
LEAF_SPEEDUP_GATE = 2.0
FULL_RUNTIME_GATE_SECONDS = 9008.46


@dataclass(frozen=True)
class Candidate:
    name: str
    scope: str
    input_s3_uri: str
    subset_strategy: str
    job_prefix: str
    mode: str = "chunked"
    chunk_leaf_mapper: str | None = None
    chunk_recovery_mapper: str | None = None
    chunk_merge_strategy: str | None = None
    chunk_merge_ba_policy: str | None = None
    chunk_hierarchical_merge_fanin: int | None = None
    matching_max_num_matches: int | None = None
    spatial_max_neighbors: int | None = None
    spatial_max_distance_meters: int | None = None
    sequential_overlap: int | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_command(command: list[str], *, capture_output: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        capture_output=capture_output,
        check=check,
    )


def aws_json(*args: str) -> dict[str, Any]:
    result = run_command([AWS_CLI, *args, "--output", "json"], capture_output=True)
    return json.loads(result.stdout)


def s3_uri_to_bucket_key(s3_uri: str) -> tuple[str, str]:
    parsed = urlparse(s3_uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path:
        raise ValueError(f"Unsupported S3 URI: {s3_uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def s3_exists(s3_uri: str) -> bool:
    bucket, key = s3_uri_to_bucket_key(s3_uri)
    result = run_command(
        [AWS_CLI, "s3api", "head-object", "--bucket", bucket, "--key", key],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def load_s3_json(s3_uri: str) -> dict[str, Any] | None:
    result = run_command([AWS_CLI, "s3", "cp", s3_uri, "-"], capture_output=True, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def get_current_branch() -> str:
    result = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True)
    return result.stdout.strip()


def get_current_head() -> str:
    result = run_command(["git", "rev-parse", "HEAD"], capture_output=True)
    return result.stdout.strip()


def ensure_runtime_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OPERATOR_CONTRACT_PATH.write_text(
        "\n".join(
            [
                "# Hybrid SfM Proof Frontier",
                "",
                "- Goal: prove the exact 2157-image baseline or close the current algorithm/resource frontier with evidence.",
                "- Never stop because one local frontier is exhausted if the task-level next frontier is clear.",
                "- Only promote a full run after a representative subset proof holds on dense and moderate connected subgraphs.",
                "- Only stop when the deliverable is achieved or the remaining next step changes algorithm class or resource class.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def append_agent_log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"[{now_iso()}] {message}\n")


def write_state(*, reason: str, last_step: str, next_unblocked_step: str, owner_action_needed: str = "none") -> None:
    STATE_PATH.write_text(
        "\n".join(
            [
                f"reason: {reason}",
                f"last_step: {last_step}",
                f"next_unblocked_step: {next_unblocked_step}",
                f"owner_action_needed: {owner_action_needed}",
                f"updated: {now_iso()}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def load_frontier() -> dict[str, Any]:
    if FRONTIER_PATH.exists():
        return json.loads(FRONTIER_PATH.read_text(encoding="utf-8"))
    return {}


def save_frontier(frontier: dict[str, Any]) -> None:
    frontier["updated_at"] = now_iso()
    FRONTIER_PATH.parent.mkdir(parents=True, exist_ok=True)
    FRONTIER_PATH.write_text(json.dumps(frontier, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def wait_for_s3_object(label: str, s3_uri: str, poll_seconds: int) -> None:
    append_agent_log(f"wait_s3:{label} -> {s3_uri}")
    while not s3_exists(s3_uri):
        time.sleep(max(poll_seconds, 30))


def load_summary(summary_path: Path) -> dict[str, Any] | None:
    if not summary_path.exists():
        return None
    return json.loads(summary_path.read_text(encoding="utf-8"))


def parse_job_bootstrap(log_path: Path) -> dict[str, Any]:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    extracted: dict[str, Any] = {}
    for field in ("job_name", "output_s3_uri", "image_uri", "selected_tag"):
        marker = f'"{field}": "'
        start = text.find(marker)
        if start == -1:
            continue
        value_start = start + len(marker)
        value_end = text.find('"', value_start)
        if value_end != -1:
            extracted[field] = text[value_start:value_end]
    return extracted


def registered_ratio(result: dict[str, Any]) -> float:
    images_registered = float(result.get("images_registered") or 0)
    dataset_image_count = float(result.get("dataset_image_count") or 0)
    if dataset_image_count <= 0:
        return 0.0
    return images_registered / dataset_image_count


def end_to_end_seconds(result: dict[str, Any]) -> float:
    return float(result.get("chunk_mapper_seconds") or 0) + float(result.get("chunk_merge_seconds") or 0)


def control_valid(result: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if registered_ratio(result) < REGISTERED_RATIO_GATE:
        reasons.append(
            f"registered_ratio={registered_ratio(result):.4f} < {REGISTERED_RATIO_GATE:.2f}"
        )
    if int(result.get("merged_component_count") or 0) != 1:
        reasons.append(f"merged_component_count={result.get('merged_component_count')} != 1")
    return not reasons, reasons


def candidate_valid(result: dict[str, Any], control: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    ratio = registered_ratio(result)
    if ratio < REGISTERED_RATIO_GATE:
        reasons.append(f"registered_ratio={ratio:.4f} < {REGISTERED_RATIO_GATE:.2f}")
    points = float(result.get("final_points_per_registered_image") or 0)
    if points < POINTS_PER_IMAGE_GATE:
        reasons.append(f"final_points_per_registered_image={points:.2f} < {POINTS_PER_IMAGE_GATE:.2f}")
    if int(result.get("merged_component_count") or 0) != 1:
        reasons.append(f"merged_component_count={result.get('merged_component_count')} != 1")

    candidate_leaf = float(result.get("chunk_mapper_seconds") or 0)
    control_leaf = float(control.get("chunk_mapper_seconds") or 0)
    candidate_total = end_to_end_seconds(result)
    control_total = end_to_end_seconds(control)
    leaf_win = control_leaf > 0 and candidate_leaf <= (control_leaf / LEAF_SPEEDUP_GATE)
    end_to_end_win = control_total > 0 and candidate_total <= (control_total / END_TO_END_SPEEDUP_GATE)
    if not leaf_win and not end_to_end_win:
        reasons.append(
            "speed_gate_failed:"
            f" leaf={candidate_leaf:.2f}s vs control={control_leaf:.2f}s,"
            f" total={candidate_total:.2f}s vs control={control_total:.2f}s"
        )
    return not reasons, reasons


def full_valid(result: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    ratio = registered_ratio(result)
    if ratio < REGISTERED_RATIO_GATE:
        reasons.append(f"registered_ratio={ratio:.4f} < {REGISTERED_RATIO_GATE:.2f}")
    points = float(result.get("final_points_per_registered_image") or 0)
    if points < POINTS_PER_IMAGE_GATE:
        reasons.append(f"final_points_per_registered_image={points:.2f} < {POINTS_PER_IMAGE_GATE:.2f}")
    runtime = float(result.get("processing_time_seconds") or 0)
    if runtime <= 0 or runtime > FULL_RUNTIME_GATE_SECONDS:
        reasons.append(f"processing_time_seconds={runtime:.2f} > {FULL_RUNTIME_GATE_SECONDS:.2f}")
    return not reasons, reasons


def close_on_quality(result: dict[str, Any]) -> bool:
    return float(result.get("final_points_per_registered_image") or 0) >= (POINTS_PER_IMAGE_GATE * 0.95)


def run_candidate(args: argparse.Namespace, frontier: dict[str, Any], candidate: Candidate) -> dict[str, Any]:
    existing = frontier.setdefault("candidates", {}).get(candidate.name)
    if existing and existing.get("status") == "completed":
        return existing

    run_id = f"{candidate.job_prefix}-{int(time.time())}"
    output_s3_uri = f"s3://{args.output_bucket}/manual-validations/{run_id}/colmap"
    summary_path = RESULTS_DIR / f"{run_id}.summary.json"
    log_path = RESULTS_DIR / f"{run_id}.log"
    command = [
        "python3",
        str(BENCHMARK_SCRIPT),
        "--branch",
        args.branch,
        "--input-s3-uri",
        candidate.input_s3_uri,
        "--output-s3-uri",
        output_s3_uri,
        "--job-prefix",
        candidate.job_prefix,
        "--mode",
        candidate.mode,
        "--subset-strategy",
        candidate.subset_strategy,
        "--wait",
        "--poll-seconds",
        str(args.poll_seconds),
        "--summary-json-output",
        str(summary_path),
    ]
    if candidate.chunk_leaf_mapper:
        command += ["--chunk-leaf-mapper", candidate.chunk_leaf_mapper]
    if candidate.chunk_recovery_mapper:
        command += ["--chunk-recovery-mapper", candidate.chunk_recovery_mapper]
    if candidate.chunk_merge_strategy:
        command += ["--chunk-merge-strategy", candidate.chunk_merge_strategy]
    if candidate.chunk_merge_ba_policy:
        command += ["--chunk-merge-ba-policy", candidate.chunk_merge_ba_policy]
    if candidate.chunk_hierarchical_merge_fanin is not None:
        command += ["--chunk-hierarchical-merge-fanin", str(candidate.chunk_hierarchical_merge_fanin)]
    if candidate.matching_max_num_matches is not None:
        command += ["--matching-max-num-matches", str(candidate.matching_max_num_matches)]
    if candidate.spatial_max_neighbors is not None:
        command += ["--spatial-max-neighbors", str(candidate.spatial_max_neighbors)]
    if candidate.spatial_max_distance_meters is not None:
        command += ["--spatial-max-distance-meters", str(candidate.spatial_max_distance_meters)]
    if candidate.sequential_overlap is not None:
        command += ["--sequential-overlap", str(candidate.sequential_overlap)]

    frontier["active_candidate"] = candidate.name
    frontier["last_run_id"] = run_id
    frontier["last_output_s3_uri"] = output_s3_uri
    frontier.setdefault("candidates", {})[candidate.name] = {
        "status": "running",
        "started_at": now_iso(),
        "candidate": asdict(candidate),
        "output_s3_uri": output_s3_uri,
        "run_id": run_id,
        "summary_path": str(summary_path),
        "log_path": str(log_path),
    }
    save_frontier(frontier)
    write_state(
        reason="running hybrid proof frontier",
        last_step=f"launching {candidate.name} -> {run_id}",
        next_unblocked_step=f"wait for {candidate.name} to finish and evaluate promotion gates",
    )
    append_agent_log(f"launch:{candidate.name} -> {run_id} -> {output_s3_uri}")

    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, text=True, stdout=handle, stderr=subprocess.STDOUT, check=False)

    summary = load_summary(summary_path) or {}
    metadata = load_s3_json(f"{output_s3_uri.rstrip('/')}/sfm_metadata.json") or {}
    bootstrap = parse_job_bootstrap(log_path)
    result: dict[str, Any] = {
        "status": "completed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "completed_at": now_iso(),
        "candidate": asdict(candidate),
        "output_s3_uri": output_s3_uri,
        "run_id": run_id,
        "summary_path": str(summary_path),
        "log_path": str(log_path),
        "job_name": summary.get("job_name") or bootstrap.get("job_name", ""),
        "image_uri": bootstrap.get("image_uri", ""),
        "selected_tag": bootstrap.get("selected_tag", ""),
        "summary": summary,
        "sfm_metadata": metadata,
    }
    result.update(summary)
    for key, value in metadata.items():
        result.setdefault(key, value)
    frontier["active_candidate"] = None
    frontier["candidates"][candidate.name] = result
    save_frontier(frontier)
    append_agent_log(
        f"complete:{candidate.name} -> status={result['status']} -> registered={result.get('images_registered')} -> next=evaluate"
    )
    return result


def decide_dense_candidate(control: dict[str, Any], results: dict[str, dict[str, Any]]) -> tuple[str | None, str]:
    serial = results["dense_hybrid_serial"]
    serial_ok, serial_reasons = candidate_valid(serial, control)
    if serial_ok:
        return "dense_hybrid_serial", "serial candidate cleared dense gate"

    hierarchical = results.get("dense_hybrid_hierarchical")
    if hierarchical is not None:
        hierarchical_ok, hierarchical_reasons = candidate_valid(hierarchical, control)
        if hierarchical_ok:
            return "dense_hybrid_hierarchical", "hierarchical candidate cleared dense gate"
        if close_on_quality(hierarchical):
            return None, "dense frontier needs relaxed leaf candidate"
        return None, f"dense frontier exhausted after hierarchical miss: {', '.join(hierarchical_reasons)}"

    if close_on_quality(serial):
        return None, "serial candidate close enough to justify hierarchical follow-up"
    return None, f"serial candidate failed dense gate: {', '.join(serial_reasons)}"


def candidate_ladder(scope: str, input_s3_uri: str) -> list[Candidate]:
    prefix = f"{scope}-"
    return [
        Candidate(
            name=f"{scope}_hybrid_serial",
            scope=scope,
            input_s3_uri=input_s3_uri,
            subset_strategy=f"{scope}_hybrid_serial_root_only",
            job_prefix=f"{prefix}hybser",
            chunk_leaf_mapper="global",
            chunk_recovery_mapper="incremental",
            chunk_merge_strategy="serial",
            chunk_merge_ba_policy="root_only",
            matching_max_num_matches=10240,
            spatial_max_neighbors=8,
        ),
        Candidate(
            name=f"{scope}_hybrid_hierarchical",
            scope=scope,
            input_s3_uri=input_s3_uri,
            subset_strategy=f"{scope}_hybrid_hierarchical_root_only",
            job_prefix=f"{prefix}hybhier",
            chunk_leaf_mapper="global",
            chunk_recovery_mapper="incremental",
            chunk_merge_strategy="hierarchical",
            chunk_hierarchical_merge_fanin=2,
            chunk_merge_ba_policy="root_only",
            matching_max_num_matches=10240,
            spatial_max_neighbors=8,
        ),
        Candidate(
            name=f"{scope}_hybrid_relaxed",
            scope=scope,
            input_s3_uri=input_s3_uri,
            subset_strategy=f"{scope}_hybrid_relaxed_root_only",
            job_prefix=f"{prefix}hybrel",
            chunk_leaf_mapper="global",
            chunk_recovery_mapper="incremental",
            chunk_merge_strategy="hierarchical",
            chunk_hierarchical_merge_fanin=2,
            chunk_merge_ba_policy="root_only",
            matching_max_num_matches=10752,
            spatial_max_neighbors=6,
        ),
    ]


def control_candidate(scope: str, input_s3_uri: str) -> Candidate:
    return Candidate(
        name=f"{scope}_control",
        scope=scope,
        input_s3_uri=input_s3_uri,
        subset_strategy=f"{scope}_control_incremental_serial",
        job_prefix=f"{scope}-ctl",
        chunk_leaf_mapper="incremental",
        chunk_merge_strategy="serial",
    )


def replay_promoted_candidate(name: str, scope: str, input_s3_uri: str, promoted: dict[str, Any]) -> Candidate:
    candidate = promoted["candidate"]
    return Candidate(
        name=name,
        scope=scope,
        input_s3_uri=input_s3_uri,
        subset_strategy=f"{scope}_{candidate['chunk_merge_strategy']}_proof",
        job_prefix=f"{scope}-hyb",
        chunk_leaf_mapper=candidate["chunk_leaf_mapper"],
        chunk_recovery_mapper=candidate["chunk_recovery_mapper"],
        chunk_merge_strategy=candidate["chunk_merge_strategy"],
        chunk_merge_ba_policy=candidate["chunk_merge_ba_policy"],
        chunk_hierarchical_merge_fanin=candidate["chunk_hierarchical_merge_fanin"],
        matching_max_num_matches=candidate["matching_max_num_matches"],
        spatial_max_neighbors=candidate["spatial_max_neighbors"],
        spatial_max_distance_meters=candidate["spatial_max_distance_meters"],
        sequential_overlap=candidate["sequential_overlap"],
    )


def run_scope(args: argparse.Namespace, frontier: dict[str, Any], scope: str, input_s3_uri: str) -> dict[str, Any] | None:
    control = run_candidate(args, frontier, control_candidate(scope, input_s3_uri))
    control_ok, control_reasons = control_valid(control)
    control["gate_passed"] = control_ok
    control["gate_reasons"] = control_reasons
    frontier["candidates"][control["candidate"]["name"]] = control
    save_frontier(frontier)
    if not control_ok:
        append_agent_log(f"{scope}:control_invalid -> {'; '.join(control_reasons)}")
        return None

    candidates = candidate_ladder(scope, input_s3_uri)
    serial = run_candidate(args, frontier, candidates[0])
    serial_ok, serial_reasons = candidate_valid(serial, control)
    serial["gate_passed"] = serial_ok
    serial["gate_reasons"] = serial_reasons
    frontier["candidates"][serial["candidate"]["name"]] = serial
    save_frontier(frontier)
    if serial_ok:
        append_agent_log(f"{scope}:promote -> {serial['candidate']['name']}")
        return serial

    hierarchical = run_candidate(args, frontier, candidates[1])
    hierarchical_ok, hierarchical_reasons = candidate_valid(hierarchical, control)
    hierarchical["gate_passed"] = hierarchical_ok
    hierarchical["gate_reasons"] = hierarchical_reasons
    frontier["candidates"][hierarchical["candidate"]["name"]] = hierarchical
    save_frontier(frontier)
    if hierarchical_ok:
        append_agent_log(f"{scope}:promote -> {hierarchical['candidate']['name']}")
        return hierarchical

    if not close_on_quality(serial) and not close_on_quality(hierarchical):
        append_agent_log(
            f"{scope}:frontier_exhausted -> serial={'; '.join(serial_reasons)} | hierarchical={'; '.join(hierarchical_reasons)}"
        )
        return None

    relaxed = run_candidate(args, frontier, candidates[2])
    relaxed_ok, relaxed_reasons = candidate_valid(relaxed, control)
    relaxed["gate_passed"] = relaxed_ok
    relaxed["gate_reasons"] = relaxed_reasons
    frontier["candidates"][relaxed["candidate"]["name"]] = relaxed
    save_frontier(frontier)
    if relaxed_ok:
        append_agent_log(f"{scope}:promote -> {relaxed['candidate']['name']}")
        return relaxed

    append_agent_log(
        f"{scope}:frontier_exhausted -> relaxed={'; '.join(relaxed_reasons)}"
    )
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch", default="", help="Branch to benchmark. Defaults to the current branch.")
    parser.add_argument("--output-bucket", default="spaceport-ml-processing-staging")
    parser.add_argument(
        "--dense-input-s3-uri",
        required=True,
        help="Exact connected dense subgraph ZIP built from the exact 2157-image baseline.",
    )
    parser.add_argument(
        "--moderate-input-s3-uri",
        required=True,
        help="Exact connected moderate subgraph ZIP built from the exact 2157-image baseline.",
    )
    parser.add_argument(
        "--full-input-s3-uri",
        default="s3://spaceport-ml-processing-staging/manual-validations/glomapfullexact-1776506913/prep/ladder_2157_exact.zip",
        help="Exact attributable 2157-image baseline ZIP.",
    )
    parser.add_argument("--poll-seconds", type=int, default=120)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.branch = args.branch or get_current_branch()
    ensure_runtime_dirs()

    frontier = load_frontier()
    frontier.setdefault(
        "goal",
        {
            "processing_time_seconds_lte": FULL_RUNTIME_GATE_SECONDS,
            "registered_ratio_gte": REGISTERED_RATIO_GATE,
            "final_points_per_registered_image_gte": POINTS_PER_IMAGE_GATE,
        },
    )
    frontier["branch"] = args.branch
    frontier["branch_head"] = get_current_head()
    frontier["dense_input_s3_uri"] = args.dense_input_s3_uri
    frontier["moderate_input_s3_uri"] = args.moderate_input_s3_uri
    frontier["full_input_s3_uri"] = args.full_input_s3_uri
    frontier["current_frontier"] = "representative_subgraphs"
    frontier.setdefault("exhausted_frontiers", [])
    frontier.setdefault("candidates", {})
    frontier["stop_allowed"] = False
    frontier["stop_reason"] = ""
    frontier["active_candidate"] = None
    frontier["next_frontier"] = "dense_control"
    save_frontier(frontier)

    write_state(
        reason="running hybrid proof frontier",
        last_step="initialized task-level frontier runner",
        next_unblocked_step="wait for dense subset object, run dense control, then promote the first winning candidate through moderate and full proof",
    )
    append_agent_log(
        f"frontier_init -> branch={args.branch} -> head={frontier['branch_head']} -> next=dense_control"
    )

    wait_for_s3_object("dense", args.dense_input_s3_uri, args.poll_seconds)
    dense_winner = run_scope(args, frontier, "dense", args.dense_input_s3_uri)
    if dense_winner is None:
        frontier["stop_allowed"] = True
        frontier["stop_reason"] = (
            "representative dense subgraph frontier exhausted; next justified task-level step is distributed leaf fan-out or a different algorithm class"
        )
        frontier["current_frontier"] = "dense_exhausted"
        frontier["next_frontier"] = "distributed_leaf_fanout_or_new_algorithm"
        frontier["exhausted_frontiers"].append("representative_subgraphs:dense")
        save_frontier(frontier)
        write_state(
            reason="hybrid proof frontier exhausted on dense representative subgraph",
            last_step="evaluated dense control and bounded candidate ladder without a promotable dense winner",
            next_unblocked_step="advance to distributed leaf fan-out or a different algorithmic frontier instead of more local single-job subset sweeps",
        )
        return 1

    frontier["promoted_dense_candidate"] = dense_winner["candidate"]["name"]
    frontier["next_frontier"] = "moderate_control"
    save_frontier(frontier)

    wait_for_s3_object("moderate", args.moderate_input_s3_uri, args.poll_seconds)
    moderate_control = run_candidate(args, frontier, control_candidate("moderate", args.moderate_input_s3_uri))
    moderate_control_ok, moderate_control_reasons = control_valid(moderate_control)
    moderate_control["gate_passed"] = moderate_control_ok
    moderate_control["gate_reasons"] = moderate_control_reasons
    frontier["candidates"][moderate_control["candidate"]["name"]] = moderate_control
    save_frontier(frontier)
    if not moderate_control_ok:
        frontier["stop_allowed"] = True
        frontier["stop_reason"] = "moderate representative control invalid"
        frontier["current_frontier"] = "moderate_control_invalid"
        frontier["next_frontier"] = "select_new_representative_subgraph_or_distributed_leaf_fanout"
        frontier["exhausted_frontiers"].append("representative_subgraphs:moderate_control_invalid")
        save_frontier(frontier)
        write_state(
            reason="moderate representative control invalid",
            last_step=f"moderate control failed gate: {', '.join(moderate_control_reasons)}",
            next_unblocked_step="select a new representative moderate connected subgraph or move to distributed leaf fan-out",
        )
        return 1

    promoted_candidate = replay_promoted_candidate(
        "moderate_promoted_candidate",
        "moderate",
        args.moderate_input_s3_uri,
        dense_winner,
    )
    moderate_candidate = run_candidate(args, frontier, promoted_candidate)
    moderate_ok, moderate_reasons = candidate_valid(moderate_candidate, moderate_control)
    moderate_candidate["gate_passed"] = moderate_ok
    moderate_candidate["gate_reasons"] = moderate_reasons
    frontier["candidates"][moderate_candidate["candidate"]["name"]] = moderate_candidate
    save_frontier(frontier)
    if not moderate_ok:
        frontier["stop_allowed"] = True
        frontier["stop_reason"] = "candidate failed moderate representative proof"
        frontier["current_frontier"] = "moderate_exhausted"
        frontier["next_frontier"] = "distributed_leaf_fanout_or_new_algorithm"
        frontier["exhausted_frontiers"].append("representative_subgraphs:moderate_failed")
        save_frontier(frontier)
        write_state(
            reason="representative moderate proof failed",
            last_step=f"{moderate_candidate['candidate']['name']} missed the moderate gate: {', '.join(moderate_reasons)}",
            next_unblocked_step="advance to distributed leaf fan-out or a different algorithmic frontier",
        )
        return 1

    frontier["promoted_candidate"] = dense_winner["candidate"]
    frontier["current_frontier"] = "full_exact_2157"
    frontier["next_frontier"] = "full_exact_2157"
    save_frontier(frontier)

    full_run = run_candidate(
        args,
        frontier,
        replay_promoted_candidate("full_exact_2157", "full_exact_2157", args.full_input_s3_uri, dense_winner),
    )
    full_ok, full_reasons = full_valid(full_run)
    full_run["gate_passed"] = full_ok
    full_run["gate_reasons"] = full_reasons
    frontier["candidates"][full_run["candidate"]["name"]] = full_run
    if full_ok:
        frontier["current_frontier"] = "complete"
        frontier["stop_allowed"] = True
        frontier["stop_reason"] = "deliverable achieved"
        frontier["next_frontier"] = ""
        frontier["deliverable_achieved"] = True
        save_frontier(frontier)
        write_state(
            reason="deliverable achieved",
            last_step=f"exact 2157-image full proof passed as {full_run.get('job_name', full_run['run_id'])}",
            next_unblocked_step="none",
        )
        append_agent_log(
            f"deliverable_achieved -> job={full_run.get('job_name', full_run['run_id'])} -> runtime={full_run.get('processing_time_seconds')}"
        )
        return 0

    runtime = float(full_run.get("processing_time_seconds") or 0)
    ratio = registered_ratio(full_run)
    points = float(full_run.get("final_points_per_registered_image") or 0)
    if ratio >= REGISTERED_RATIO_GATE and points >= POINTS_PER_IMAGE_GATE:
        frontier["stop_reason"] = "quality-safe full run missed runtime gate; next justified move is distributed leaf fan-out"
        frontier["next_frontier"] = "distributed_leaf_fanout"
    else:
        frontier["stop_reason"] = "full exact run failed quality or stability; next justified move is distributed incremental leaves with the same merge tree"
        frontier["next_frontier"] = "distributed_incremental_leaves"
    frontier["current_frontier"] = "full_exact_2157_failed"
    frontier["stop_allowed"] = True
    save_frontier(frontier)
    write_state(
        reason="full exact 2157 proof did not meet the final gate",
        last_step=f"full exact run missed gate: runtime={runtime:.2f}s ratio={ratio:.4f} points={points:.2f}",
        next_unblocked_step=frontier["next_frontier"],
    )
    append_agent_log(
        f"full_failed -> runtime={runtime:.2f} -> ratio={ratio:.4f} -> points={points:.2f} -> next={frontier['next_frontier']}"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
