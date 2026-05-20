#!/usr/bin/env python3
"""Run the MD1-Shrunk production-readiness heartbeat (read-only; cost bounded).

This script automates the "heartbeat verify" loop captured in logs/md1-shrunk/STATE.md:
  - preflight: git/AWS identity, Step Functions + SageMaker in-progress checks, public meta.json HEADs, GH runs
  - bundle parity: compare S3 vs edge meta.json payload hashes
  - edge delivery validation: invoke ml_publish_bundle Lambda + verify browser-readable headers (CORS + caching + assets)
  - camera suite: multi-camera input-vs-render panels + deterministic sky/horizon diagnostics + pose drift checks
  - unit proof: run the small unit set that backs the above checks

It does NOT launch or stop any SageMaker / Step Functions jobs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
HOMEBREW_AWS = Path("/opt/homebrew/bin/aws")
HOMEBREW_PYTHON = Path("/opt/homebrew/bin/python3")


def resolve_aws() -> str:
    return str(HOMEBREW_AWS) if HOMEBREW_AWS.exists() else "aws"


def resolve_python() -> str:
    return str(HOMEBREW_PYTHON) if HOMEBREW_PYTHON.exists() else "python3"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.stdout


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def curl_head(url: str, *, origin: str | None = None) -> str:
    cmd = ["curl", "-sS", "-I"]
    if origin:
        cmd += ["-H", f"Origin: {origin}"]
    cmd.append(url)
    return run(cmd)


def curl_get(url: str) -> bytes:
    out = subprocess.run(["curl", "-sS", url], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return out.stdout


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--viewer-url", required=True, help="Deployed viewer base URL (e.g. https://...pages.dev)")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--compressed-output-s3-uri", required=True, help="s3://.../compressed/<job-id>/")
    parser.add_argument("--publish-function", default="Spaceport-MLPublishBundle-brc908ce627c")
    parser.add_argument(
        "--edge-meta-url",
        default="",
        help="Optional edge meta.json URL. If omitted, it is resolved from the publish Lambda response.",
    )
    parser.add_argument(
        "--s3-meta-url",
        default="",
        help="Optional public S3 meta.json URL for parity checks. If omitted, parity uses the edge URL only.",
    )
    parser.add_argument(
        "--colmap-images-txt",
        required=True,
        help="S3 URI or local path to COLMAP sparse/0/images.txt",
    )
    parser.add_argument(
        "--colmap-images-s3-prefix",
        required=True,
        help="S3 prefix to the source images directory (used for a small sample download).",
    )
    parser.add_argument("--baseline-suite-dir", default="", help="Optional prior camera-suite dir for pose drift checks.")
    parser.add_argument("--sample-count", type=int, default=6)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument(
        "--polls-root",
        default=str(REPO_ROOT / "logs" / "md1-shrunk" / "polls"),
        help="Root directory for timestamped poll outputs.",
    )
    parser.add_argument(
        "--staging-state-machine-arn",
        default="arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging",
    )
    parser.add_argument(
        "--branch-state-machine-arn",
        default="arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-br-8abcbd5662",
    )
    parser.add_argument(
        "--known-execution-arn",
        default="",
        help="Optional Step Functions execution ARN to describe (stored in preflight outputs).",
    )
    parser.add_argument("--gh-branch", default="", help="Branch name to use for `gh run list` (defaults to current).")
    return parser.parse_args()


def find_baseline_suite_dir(
    polls_root: Path,
    *,
    bundle_url: str,
    viewer_url: str,
    current_ts: str,
) -> str:
    """Pick a stable prior camera-suite directory for pose drift checks.

    When no explicit `--baseline-suite-dir` is passed, search earlier `*-camera-suite`
    directories under `polls_root` and pick the oldest passing run that matches the
    same bundle + viewer. This gives us a long-lived baseline without hardcoding a
    timestamp.
    """

    candidates: list[tuple[str, Path, dict[str, Any]]] = []
    for entry in polls_root.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if not name.endswith("-camera-suite"):
            continue
        ts = name.removesuffix("-camera-suite")
        if ts >= current_ts:
            continue

        summary_path = entry / "suite-summary.json"
        if not summary_path.exists():
            continue
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if summary.get("decision") != "pass":
            continue
        if str(summary.get("bundle_url") or "").strip() != bundle_url:
            continue
        if str(summary.get("viewer_url") or "").strip() != viewer_url:
            continue
        candidates.append((ts, entry, summary))

    if not candidates:
        return ""

    # Prefer the baseline suite dir referenced by the most recent passing run.
    candidates.sort(key=lambda pair: pair[0])  # chronological
    for ts, entry, summary in reversed(candidates):
        baseline = str(summary.get("baseline_suite_dir") or "").strip()
        if baseline and Path(baseline).exists():
            return str(Path(baseline).resolve())

    # Otherwise, default to using the most recent passing suite as the baseline.
    return str(candidates[-1][1].resolve())


def main() -> int:
    args = parse_args()
    ts = utc_timestamp()
    polls_root = Path(args.polls_root).resolve()

    pre_dir = polls_root / f"{ts}-preflight"
    bundle_dir = polls_root / f"{ts}-bundle"
    edge_dir = polls_root / f"{ts}-edge-validate"
    cam_dir = polls_root / f"{ts}-camera-suite"
    unit_dir = polls_root / f"{ts}-unit"
    ci_dir = polls_root / f"{ts}-ci"

    for directory in [pre_dir, bundle_dir, edge_dir, cam_dir, unit_dir, ci_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_ROOT).strip()
    head = run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).strip()
    status = run(["git", "status", "--porcelain=v1"], cwd=REPO_ROOT)
    gh_branch = args.gh_branch.strip() or branch

    aws = resolve_aws()
    py = resolve_python()

    # --- preflight (raw JSON) ---
    sts_json = json.loads(run([aws, "sts", "get-caller-identity", "--output", "json"]))
    staging_running = json.loads(
        run(
            [
                aws,
                "stepfunctions",
                "list-executions",
                "--state-machine-arn",
                args.staging_state_machine_arn,
                "--status-filter",
                "RUNNING",
                "--max-results",
                "20",
                "--region",
                "us-west-2",
                "--output",
                "json",
            ]
        )
    )
    branch_running = json.loads(
        run(
            [
                aws,
                "stepfunctions",
                "list-executions",
                "--state-machine-arn",
                args.branch_state_machine_arn,
                "--status-filter",
                "RUNNING",
                "--max-results",
                "20",
                "--region",
                "us-west-2",
                "--output",
                "json",
            ]
        )
    )
    processing_inprogress = json.loads(
        run(
            [
                aws,
                "sagemaker",
                "list-processing-jobs",
                "--status-equals",
                "InProgress",
                "--max-results",
                "20",
                "--region",
                "us-west-2",
                "--output",
                "json",
            ]
        )
    )
    training_inprogress = json.loads(
        run(
            [
                aws,
                "sagemaker",
                "list-training-jobs",
                "--status-equals",
                "InProgress",
                "--max-results",
                "20",
                "--region",
                "us-west-2",
                "--output",
                "json",
            ]
        )
    )
    gh_runs = json.loads(
        run(
            [
                "gh",
                "run",
                "list",
                "--branch",
                gh_branch,
                "--limit",
                "20",
                "--json",
                "databaseId,workflowName,status,conclusion,createdAt,updatedAt,headSha,event",
            ]
        )
    )

    write_json(pre_dir / "aws-sts-get-caller-identity.json", sts_json)
    write_json(pre_dir / "stepfunctions-running-staging.json", staging_running)
    write_json(pre_dir / "stepfunctions-running-branch.json", branch_running)
    write_json(pre_dir / "sagemaker-processing-inprogress.json", processing_inprogress)
    write_json(pre_dir / "sagemaker-training-inprogress.json", training_inprogress)
    write_json(pre_dir / "gh-run-list.json", gh_runs)

    if args.known_execution_arn.strip():
        known_exec = json.loads(
            run([aws, "stepfunctions", "describe-execution", "--execution-arn", args.known_execution_arn, "--region", "us-west-2", "--output", "json"])
        )
        write_json(pre_dir / "stepfunctions-describe-known.json", known_exec)

    s3_head = curl_head(args.s3_meta_url, origin=args.viewer_url) if args.s3_meta_url.strip() else ""
    edge_head = curl_head(args.edge_meta_url, origin=args.viewer_url) if args.edge_meta_url.strip() else ""

    # local listeners (best-effort)
    listeners = run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"])

    preflight_txt = [
        f"# preflight {ts}",
        "",
        "## git",
        f"branch={branch}",
        f"head={head}",
        "status_porcelain=" + ("clean" if not status.strip() else "dirty"),
        "",
        "## aws sts get-caller-identity",
        json.dumps(sts_json, indent=2),
        "",
        "## stepfunctions RUNNING (staging)",
        json.dumps(staging_running, indent=2),
        "",
        "## stepfunctions RUNNING (branch)",
        json.dumps(branch_running, indent=2),
        "",
        "## sagemaker processing InProgress",
        json.dumps(processing_inprogress, indent=2),
        "",
        "## sagemaker training InProgress",
        json.dumps(training_inprogress, indent=2),
        "",
        "## gh runs (branch)",
        json.dumps(gh_runs, indent=2),
    ]
    if s3_head:
        preflight_txt += ["", "## public S3 meta.json HEAD (with Origin)", s3_head.strip()]
    if edge_head:
        preflight_txt += ["", "## edge meta.json HEAD (with Origin)", edge_head.strip()]
    preflight_txt += ["", "## local tcp listeners", listeners.strip(), ""]
    write_text(pre_dir / "preflight.txt", "\n".join(preflight_txt))

    # --- bundle parity ---
    parity_lines: list[str] = [f"# bundle parity {ts}"]
    if args.s3_meta_url.strip() and args.edge_meta_url.strip():
        s3_payload = curl_get(args.s3_meta_url)
        edge_payload = curl_get(args.edge_meta_url)
        parity_lines += [
            "",
            f"S3_META={args.s3_meta_url}",
            f"EDGE_META={args.edge_meta_url}",
            "",
            "## shasum",
            f"s3 {sha256_bytes(s3_payload)}  -",
            f"edge {sha256_bytes(edge_payload)}  -",
        ]
    else:
        parity_lines += ["", "note: parity skipped (missing --s3-meta-url or --edge-meta-url)"]
    write_text(bundle_dir / "bundle.txt", "\n".join(parity_lines) + "\n")

    # --- edge publish/validate (also resolves edge url when missing) ---
    edge_output_json = edge_dir / "publish-edge.json"
    edge_report_html = edge_dir / "publish-edge.report.html"
    cmd_publish = [
        py,
        str(REPO_ROOT / "scripts" / "publish_ml_bundle_to_edge.py"),
        "--function-name",
        args.publish_function,
        "--job-id",
        args.job_id,
        "--compressed-output-s3-uri",
        args.compressed_output_s3_uri,
        "--output",
        str(edge_output_json),
        "--validate-http",
        "--require-browser-headers",
        "--origin",
        args.viewer_url,
        "--html-report",
        str(edge_report_html),
    ]
    write_text(edge_dir / "run.cmd.txt", " ".join(cmd_publish) + "\n")
    publish_log = run(cmd_publish, cwd=REPO_ROOT)
    write_text(edge_dir / "validate.txt", publish_log)

    publish_result = json.loads(edge_output_json.read_text(encoding="utf-8"))
    edge_url = str(publish_result.get("edgeBundleUrl") or "").strip()
    if not edge_url:
        raise RuntimeError(f"publish output missing edgeBundleUrl: {publish_result}")

    # If caller did not pass edge URL, use the resolved one for camera suite.
    bundle_url = args.edge_meta_url.strip() or edge_url

    baseline_suite_dir = args.baseline_suite_dir.strip()
    if not baseline_suite_dir:
        baseline_suite_dir = find_baseline_suite_dir(
            polls_root,
            bundle_url=bundle_url,
            viewer_url=args.viewer_url,
            current_ts=ts,
        )

    # --- camera suite ---
    cmd_camera = [
        py,
        str(REPO_ROOT / "scripts" / "sfm" / "run_md1_shrunk_camera_suite.py"),
        "--viewer-url",
        args.viewer_url,
        "--bundle-url",
        bundle_url,
        "--job-id",
        args.job_id,
        "--compressed-output-s3-uri",
        args.compressed_output_s3_uri,
        "--colmap-images-txt",
        args.colmap_images_txt,
        "--colmap-images-s3-prefix",
        args.colmap_images_s3_prefix,
        "--sample-count",
        str(args.sample_count),
        "--out-dir",
        str(cam_dir),
    ]
    if baseline_suite_dir:
        cmd_camera += ["--baseline-suite-dir", baseline_suite_dir]
    if args.strict:
        cmd_camera += ["--strict"]

    write_text(cam_dir / "run.cmd.txt", " ".join(cmd_camera) + "\n")
    cam_log = run(cmd_camera, cwd=REPO_ROOT)
    write_text(cam_dir / "suite.log", cam_log)

    # --- unit proof (verbose so output is non-empty on pass) ---
    cmd_unit = [
        py,
        "-m",
        "unittest",
        "-v",
        "tests.unit.test_sfm_heldout_panel_diagnostics",
        "tests.unit.test_viewer_camera_pose_derivation",
        "tests.unit.test_ml_publish_bundle",
    ]
    write_text(unit_dir / "run.cmd.txt", " ".join(cmd_unit) + "\n")
    unit_log = run(cmd_unit, cwd=REPO_ROOT)
    write_text(unit_dir / "unittest.txt", unit_log)

    # --- GH snapshot ---
    ci_summary = [f"# gh ci snapshot {ts}", "", "count=20"]
    for entry in gh_runs:
        ci_summary.append(
            f"- {entry.get('workflowName','')} id={entry.get('databaseId','')} status={entry.get('status','')} "
            f"conclusion={entry.get('conclusion','')} headSha={entry.get('headSha','')} createdAt={entry.get('createdAt','')}"
        )
    write_text(ci_dir / "summary.txt", "\n".join(ci_summary) + "\n")

    # --- final summary ---
    summary = {
        "timestamp_utc": ts,
        "branch": branch,
        "head": head,
        "viewer_url": args.viewer_url,
        "job_id": args.job_id,
        "compressed_output_s3_uri": args.compressed_output_s3_uri,
        "edge_meta_url": bundle_url,
        "poll_dirs": {
            "preflight": str(pre_dir),
            "bundle": str(bundle_dir),
            "edge_validate": str(edge_dir),
            "camera_suite": str(cam_dir),
            "unit": str(unit_dir),
            "ci": str(ci_dir),
        },
    }
    write_json(polls_root / f"{ts}-summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
