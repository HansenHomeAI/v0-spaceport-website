#!/usr/bin/env python3
"""Monitor cost and stall signals for MD1 tiled 3DGS SageMaker runs."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping


INSTANCE_HOURLY_RATES_USD = {
    "ml.g5.2xlarge": 1.515,
    "ml.g5.xlarge": 1.408,
    "ml.g6.xlarge": 1.127,
    "ml.g4dn.xlarge": 0.736,
}


def run_aws_json(*args: str) -> dict[str, Any]:
    result = subprocess.run(
        ["aws", *args, "--output", "json"],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def estimate_training_spend(
    training_job: Mapping[str, Any],
    *,
    instance_hourly_rates: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    rates = dict(instance_hourly_rates or INSTANCE_HOURLY_RATES_USD)
    instance_type = str((training_job.get("ResourceConfig") or {}).get("InstanceType") or "ml.g5.2xlarge")
    seconds = training_job.get("BillableTimeInSeconds", training_job.get("TrainingTimeInSeconds", 0)) or 0
    billable_hours = float(seconds) / 3600.0
    hourly_rate = float(rates.get(instance_type, rates["ml.g5.2xlarge"]))
    return {
        "instance_type": instance_type,
        "hourly_rate_usd": hourly_rate,
        "billable_seconds": int(seconds),
        "billable_hours": round(billable_hours, 4),
        "estimated_usd": round(billable_hours * hourly_rate, 4),
    }


def evaluate_training_health(
    *,
    training_job: Mapping[str, Any],
    latest_log_age_seconds: int | None,
    gpu_average_percent: float | None,
    s3_output_object_count: int,
    max_estimated_usd: float,
    max_log_staleness_seconds: int = 1200,
    low_gpu_threshold_percent: float = 5.0,
    low_gpu_warmup_seconds: int = 900,
) -> dict[str, Any]:
    spend = estimate_training_spend(training_job)
    training_status = str(training_job.get("TrainingJobStatus") or "")
    secondary_status = str(training_job.get("SecondaryStatus") or "")
    elapsed_seconds = int(training_job.get("TrainingTimeInSeconds", 0) or 0)
    model_artifact = ((training_job.get("ModelArtifacts") or {}).get("S3ModelArtifacts") or "").strip()
    block_reasons: list[str] = []
    warnings: list[str] = []

    if training_status in {"Failed", "Stopped"}:
        block_reasons.append(f"training_job_{training_status.lower()}")
    if max_estimated_usd > 0 and float(spend["estimated_usd"]) > float(max_estimated_usd):
        block_reasons.append("estimated_spend_over_budget")
    if training_status == "InProgress" and latest_log_age_seconds is None and elapsed_seconds > low_gpu_warmup_seconds:
        block_reasons.append("cloudwatch_logs_missing_after_warmup")
    if (
        training_status == "InProgress"
        and latest_log_age_seconds is not None
        and latest_log_age_seconds > max_log_staleness_seconds
    ):
        block_reasons.append("cloudwatch_log_stale")
    if (
        training_status == "InProgress"
        and secondary_status == "Training"
        and gpu_average_percent is not None
        and elapsed_seconds > low_gpu_warmup_seconds
        and gpu_average_percent < low_gpu_threshold_percent
    ):
        block_reasons.append("gpu_low_after_warmup")
    if training_status == "Completed" and not model_artifact:
        block_reasons.append("completed_without_model_artifact")
    if training_status == "InProgress" and s3_output_object_count == 0 and elapsed_seconds > 6 * 3600:
        warnings.append("long_running_without_s3_outputs")

    return {
        "status": "blocked" if block_reasons else "ok",
        "training_job_name": training_job.get("TrainingJobName"),
        "training_status": training_status,
        "secondary_status": secondary_status,
        "elapsed_seconds": elapsed_seconds,
        "latest_log_age_seconds": latest_log_age_seconds,
        "gpu_average_percent": gpu_average_percent,
        "s3_output_object_count": s3_output_object_count,
        "spend": spend,
        "block_reasons": list(dict.fromkeys(block_reasons)),
        "warnings": list(dict.fromkeys(warnings)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-job-name", required=True)
    parser.add_argument("--max-estimated-usd", type=float, required=True)
    parser.add_argument("--latest-log-age-seconds", type=int, default=-1)
    parser.add_argument("--gpu-average-percent", type=float, default=-1.0)
    parser.add_argument("--s3-output-object-count", type=int, default=0)
    parser.add_argument("--max-log-staleness-seconds", type=int, default=1200)
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=0,
        help="Repeat checks at this cadence. Use 300-600 seconds for active training jobs.",
    )
    parser.add_argument("--max-polls", type=int, default=1, help="Maximum checks before exiting.")
    parser.add_argument("--output-json", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    max_polls = max(1, args.max_polls)
    checks: list[dict[str, Any]] = []
    exit_code = 0
    for poll_index in range(max_polls):
        training_job = run_aws_json(
            "sagemaker",
            "describe-training-job",
            "--training-job-name",
            args.training_job_name,
        )
        latest_log_age_seconds = None if args.latest_log_age_seconds < 0 else args.latest_log_age_seconds
        gpu_average_percent = None if args.gpu_average_percent < 0 else args.gpu_average_percent
        health = evaluate_training_health(
            training_job=training_job,
            latest_log_age_seconds=latest_log_age_seconds,
            gpu_average_percent=gpu_average_percent,
            s3_output_object_count=args.s3_output_object_count,
            max_estimated_usd=args.max_estimated_usd,
            max_log_staleness_seconds=args.max_log_staleness_seconds,
        )
        health["checked_at_epoch"] = int(time.time())
        health["poll_index"] = poll_index
        checks.append(health)
        payload = json.dumps(health, indent=2)
        print(payload)
        if args.output_json:
            Path(args.output_json).write_text(json.dumps({"checks": checks}, indent=2) + "\n", encoding="utf-8")
        if health["status"] == "blocked":
            exit_code = 2
            break
        if health["training_status"] != "InProgress":
            break
        if poll_index == max_polls - 1 or args.poll_seconds <= 0:
            break
        time.sleep(args.poll_seconds)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
