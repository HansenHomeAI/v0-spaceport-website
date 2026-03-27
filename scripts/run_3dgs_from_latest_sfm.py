#!/usr/bin/env python3
"""Start and monitor a 3DGS -> compression pipeline from the latest completed SfM output."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PipelineRunner:
    def __init__(self, region: str, lookback_hours: int, max_retries: int, poll_seconds: int) -> None:
        self.region = region
        self.lookback_hours = lookback_hours
        self.max_retries = max_retries
        self.poll_seconds = poll_seconds

        self.lambda_client = boto3.client("lambda", region_name=region)
        self.sfn_client = boto3.client("stepfunctions", region_name=region)
        self.sagemaker_client = boto3.client("sagemaker", region_name=region)

    def find_start_lambda(self) -> str:
        paginator = self.lambda_client.get_paginator("list_functions")
        candidates: List[str] = []
        for page in paginator.paginate():
            for fn in page.get("Functions", []):
                name = fn.get("FunctionName", "")
                if name.startswith("Spaceport-StartMLJob"):
                    candidates.append(name)

        if not candidates:
            raise RuntimeError("Could not find Lambda function with prefix 'Spaceport-StartMLJob'.")

        # Prefer exact name, then staging, then shortest name.
        if "Spaceport-StartMLJob" in candidates:
            return "Spaceport-StartMLJob"
        for preferred in ("Spaceport-StartMLJob-staging", "Spaceport-StartMLJob-development"):
            if preferred in candidates:
                return preferred

        return sorted(candidates, key=len)[0]

    def find_state_machine_arn(self) -> str:
        paginator = self.sfn_client.get_paginator("list_state_machines")
        candidates: List[Dict[str, str]] = []
        for page in paginator.paginate():
            for sm in page.get("stateMachines", []):
                name = sm.get("name", "")
                arn = sm.get("stateMachineArn", "")
                if name.startswith("SpaceportMLPipeline"):
                    candidates.append({"name": name, "arn": arn})

        if not candidates:
            raise RuntimeError("Could not find state machine with prefix 'SpaceportMLPipeline'.")

        # Prefer staging first (aligns with StartMLJob-staging input/output buckets), then unsuffixed.
        for preferred in ("SpaceportMLPipeline-staging", "SpaceportMLPipeline"):
            match = next((c for c in candidates if c["name"] == preferred), None)
            if match:
                return match["arn"]

        return sorted(candidates, key=lambda c: len(c["name"]))[0]["arn"]

    def find_latest_completed_sfm_output(self) -> Tuple[str, str, datetime]:
        cutoff = utc_now() - timedelta(hours=self.lookback_hours)

        paginator = self.sagemaker_client.get_paginator("list_processing_jobs")
        newest: Optional[Dict[str, Any]] = None

        for page in paginator.paginate(
            StatusEquals="Completed",
            SortBy="CreationTime",
            SortOrder="Descending",
        ):
            jobs = page.get("ProcessingJobSummaries", [])
            if not jobs:
                continue

            for summary in jobs:
                job_name = summary.get("ProcessingJobName", "")
                ctime = summary.get("CreationTime")
                if not ctime or ctime < cutoff:
                    # Since sorted descending by creation time, we're done scanning.
                    return self._extract_sfm_job_output(newest)

                if not job_name.endswith("-sfm"):
                    continue

                details = self.sagemaker_client.describe_processing_job(ProcessingJobName=job_name)
                end_time = details.get("ProcessingEndTime")
                if not end_time or end_time < cutoff:
                    continue

                outputs = details.get("ProcessingOutputConfig", {}).get("Outputs", [])
                if not outputs:
                    continue

                s3_uri = outputs[0].get("S3Output", {}).get("S3Uri")
                if not s3_uri:
                    continue

                newest = {
                    "job_name": job_name,
                    "s3_uri": s3_uri,
                    "end_time": end_time,
                }
                return self._extract_sfm_job_output(newest)

        return self._extract_sfm_job_output(newest)

    @staticmethod
    def _extract_sfm_job_output(candidate: Optional[Dict[str, Any]]) -> Tuple[str, str, datetime]:
        if not candidate:
            raise RuntimeError("No completed SfM SageMaker processing job found in the lookback window.")
        return candidate["job_name"], candidate["s3_uri"], candidate["end_time"]

    def start_execution(self, lambda_name: str, existing_colmap_uri: str, email: str) -> Tuple[str, str]:
        payload = {
            "body": {
                "s3Url": "s3://spaceport-ml-pipeline/test-data/dummy-file.zip",
                "email": email,
                "pipelineStep": "3dgs",
                "existingColmapUri": existing_colmap_uri,
            }
        }

        response = self.lambda_client.invoke(
            FunctionName=lambda_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )
        raw_payload = response["Payload"].read().decode("utf-8")
        parsed = json.loads(raw_payload)

        if parsed.get("statusCode") != 200:
            body = parsed.get("body", "")
            if isinstance(body, str) and "STATE_MACHINE_ARN" in body:
                print("⚠️ Start lambda missing STATE_MACHINE_ARN. Falling back to direct Step Functions start.")
                return self.start_execution_direct(existing_colmap_uri=existing_colmap_uri, email=email)
            raise RuntimeError(f"Start lambda returned non-200: {parsed}")

        body = json.loads(parsed.get("body", "{}"))
        execution_arn = body.get("executionArn")
        job_id = body.get("jobId")
        if not execution_arn or not job_id:
            raise RuntimeError(f"Could not parse executionArn/jobId from response body: {body}")

        return job_id, execution_arn

    def start_execution_direct(self, existing_colmap_uri: str, email: str) -> Tuple[str, str]:
        sm_arn = self.find_state_machine_arn()
        account_id = boto3.client("sts", region_name=self.region).get_caller_identity()["Account"]
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        unix_ts = int(time.time())
        job_id = f"manual-3dgs-{unix_ts}"
        job_name = f"ml-job-{ts}-{job_id[:8]}"

        step_input = {
            "jobId": job_id,
            "jobName": job_name,
            "s3Url": "s3://spaceport-ml-pipeline/test-data/dummy-file.zip",
            "email": email,
            "pipelineStep": "3dgs",
            "inputS3Uri": "s3://spaceport-ml-pipeline/test-data/dummy-file.zip",
            "colmapOutputS3Uri": existing_colmap_uri,
            "gaussianOutputS3Uri": f"s3://spaceport-ml-processing/3dgs/{job_id}/",
            "compressedOutputS3Uri": f"s3://spaceport-ml-processing/compressed/{job_id}/",
            "sfmImageUri": f"{account_id}.dkr.ecr.{self.region}.amazonaws.com/spaceport/sfm:latest",
            "gaussianImageUri": f"{account_id}.dkr.ecr.{self.region}.amazonaws.com/spaceport/3dgs:latest",
            "compressorImageUri": f"{account_id}.dkr.ecr.{self.region}.amazonaws.com/spaceport/compressor:latest",
            "MAX_ITERATIONS": "30000",
            "TARGET_PSNR": "35.0",
            "MODEL_VARIANT": "splatfacto-big",
            "SH_DEGREE": "3",
            "BILATERAL_PROCESSING": "true",
            "LOG_INTERVAL": "100",
            "FRAMEWORK": "nerfstudio",
            "METHODOLOGY": "vincent_woo_sutro_tower",
            "LICENSE": "apache_2_0",
            "COMMERCIAL_LICENSE": "true",
            "OUTPUT_FORMAT": "ply",
            "SOGS_COMPATIBLE": "true",
            "MAX_NUM_GAUSSIANS": "1500000",
            "MEMORY_OPTIMIZATION": "true",
            "max_iterations": 30000,
            "target_psnr": 35.0,
            "sh_degree": 3,
            "log_interval": 100,
            "TORCH_CUDA_ARCH_LIST": "8.0 8.6",
        }

        resp = self.sfn_client.start_execution(
            stateMachineArn=sm_arn,
            name=f"execution-{job_id}",
            input=json.dumps(step_input),
        )
        return job_id, resp["executionArn"]

    def monitor_execution(self, execution_arn: str, timeout_hours: int) -> Tuple[str, Dict[str, Any]]:
        deadline = utc_now() + timedelta(hours=timeout_hours)
        while utc_now() < deadline:
            desc = self.sfn_client.describe_execution(executionArn=execution_arn)
            status = desc.get("status", "UNKNOWN")
            start_dt = desc.get("startDate")
            elapsed = (utc_now() - start_dt).total_seconds() if start_dt else 0
            print(f"[{datetime.now().isoformat()}] execution={status} elapsed={elapsed/60:.1f}m")

            if status in {"SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"}:
                return status, desc

            time.sleep(self.poll_seconds)

        raise TimeoutError(f"Execution did not complete within {timeout_hours} hour(s): {execution_arn}")

    def get_execution_history(self, execution_arn: str) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        next_token: Optional[str] = None
        while True:
            kwargs: Dict[str, Any] = {"executionArn": execution_arn, "maxResults": 1000}
            if next_token:
                kwargs["nextToken"] = next_token
            resp = self.sfn_client.get_execution_history(**kwargs)
            events.extend(resp.get("events", []))
            next_token = resp.get("nextToken")
            if not next_token:
                break
        return events

    @staticmethod
    def execution_has_task_failures(events: List[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        for event in events:
            if event.get("type") == "TaskFailed":
                return True, event.get("taskFailedEventDetails")
        return False, None

    def wait_for_training_capacity(self, instance_type: str = "ml.g5.2xlarge", timeout_minutes: int = 180) -> bool:
        deadline = utc_now() + timedelta(minutes=timeout_minutes)
        print(f"Waiting for {instance_type} training capacity to free up...")
        while utc_now() < deadline:
            resp = self.sagemaker_client.list_training_jobs(
                StatusEquals="InProgress",
                SortBy="CreationTime",
                SortOrder="Descending",
                MaxResults=50,
            )
            in_use = []
            for summary in resp.get("TrainingJobSummaries", []):
                job_name = summary.get("TrainingJobName")
                if not job_name:
                    continue
                details = self.sagemaker_client.describe_training_job(TrainingJobName=job_name)
                cfg = details.get("ResourceConfig", {})
                if cfg.get("InstanceType") == instance_type:
                    in_use.append(job_name)
            if not in_use:
                print(f"{instance_type} capacity appears available.")
                return True
            print(f"{instance_type} still in use by: {', '.join(in_use[:3])}. Rechecking in {self.poll_seconds}s.")
            time.sleep(self.poll_seconds)
        return False

    def collect_failure_context(self, execution_arn: str) -> Dict[str, Any]:
        history = self.sfn_client.get_execution_history(
            executionArn=execution_arn,
            reverseOrder=True,
            maxResults=30,
        )
        events = history.get("events", [])

        context: Dict[str, Any] = {"recent_events": []}
        for event in events[:10]:
            entry: Dict[str, Any] = {
                "timestamp": event.get("timestamp").isoformat() if event.get("timestamp") else None,
                "type": event.get("type"),
            }
            for key in (
                "executionFailedEventDetails",
                "taskFailedEventDetails",
                "lambdaFunctionFailedEventDetails",
            ):
                if key in event:
                    entry[key] = event[key]
            context["recent_events"].append(entry)

        # Attempt to identify failed SageMaker jobs created recently.
        failed_jobs: List[Dict[str, Any]] = []
        now = utc_now()
        lookback = now - timedelta(hours=6)
        paginator = self.sagemaker_client.get_paginator("list_processing_jobs")
        for page in paginator.paginate(StatusEquals="Failed", SortBy="CreationTime", SortOrder="Descending"):
            for summary in page.get("ProcessingJobSummaries", []):
                ctime = summary.get("CreationTime")
                if ctime and ctime < lookback:
                    break
                job_name = summary.get("ProcessingJobName")
                if not job_name:
                    continue
                details = self.sagemaker_client.describe_processing_job(ProcessingJobName=job_name)
                failed_jobs.append(
                    {
                        "job_name": job_name,
                        "failure_reason": details.get("FailureReason"),
                        "creation_time": ctime.isoformat() if ctime else None,
                    }
                )
            if failed_jobs:
                break

        if failed_jobs:
            context["recent_failed_processing_jobs"] = failed_jobs[:3]
        return context

    def run(self, timeout_hours: int, email: str) -> int:
        lambda_name = self.find_start_lambda()
        print(f"Using start lambda: {lambda_name}")

        sfm_job_name, sfm_output_uri, sfm_end_time = self.find_latest_completed_sfm_output()
        print(f"Using latest completed SfM job: {sfm_job_name}")
        print(f"SfM completed at (UTC): {sfm_end_time.isoformat()}")
        print(f"SfM output URI: {sfm_output_uri}")

        attempts = 0
        while attempts < self.max_retries:
            attempts += 1
            print(f"\n=== Attempt {attempts}/{self.max_retries} ===")
            job_id, execution_arn = self.start_execution(lambda_name, sfm_output_uri, email)
            print(f"Triggered job_id={job_id}")
            print(f"Execution ARN: {execution_arn}")

            try:
                status, desc = self.monitor_execution(execution_arn, timeout_hours=timeout_hours)
            except TimeoutError as exc:
                print(f"Timeout: {exc}")
                return 2

            events = self.get_execution_history(execution_arn)
            has_task_failures, task_failure_details = self.execution_has_task_failures(events)

            if status == "SUCCEEDED" and not has_task_failures:
                output = desc.get("output")
                print("✅ Pipeline completed successfully without task failures.")
                if output:
                    print(f"Execution output: {output}")
                return 0

            print(f"❌ Execution ended with status: {status} (task failures: {has_task_failures})")
            if task_failure_details:
                print(f"Task failure details: {json.dumps(task_failure_details, default=str)}")
            context = self.collect_failure_context(execution_arn)
            print("Failure context:")
            print(json.dumps(context, indent=2, default=str))

            if task_failure_details and task_failure_details.get("error") == "SageMaker.ResourceLimitExceededException":
                if not self.wait_for_training_capacity():
                    print("❌ Timed out waiting for training capacity.")
                    return 1

        print(f"❌ Exhausted retries ({self.max_retries}) without successful completion.")
        return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--lookback-hours", type=int, default=24)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--timeout-hours", type=int, default=4)
    parser.add_argument("--email", default="pipeline-monitor@spaceport.dev")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runner = PipelineRunner(
        region=args.region,
        lookback_hours=args.lookback_hours,
        max_retries=args.max_retries,
        poll_seconds=args.poll_seconds,
    )

    try:
        return runner.run(timeout_hours=args.timeout_hours, email=args.email)
    except ClientError as exc:
        print(f"AWS error: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
