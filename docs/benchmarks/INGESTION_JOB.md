# Benchmark Ingestion Job Stub

This stub defines a Phase 2 job contract for dataset ingestion into the benchmark S3 layout.

## Job Type

Preferred default: AWS Batch (container job).
Alternative: SageMaker Processing (same container and entrypoint).

## Container Entrypoint

- Entrypoint command: `python3 scripts/bench/ingest_to_s3.py`
- Default mode: dry-run (`--dry-run` implied unless `--upload` is set)

Example args:

```bash
python3 scripts/bench/ingest_to_s3.py \
  --dataset mipnerf360 \
  --scene garden \
  --source-url https://example.com/garden.zip \
  --license-url https://example.com/license \
  --bucket spaceport-ml-benchmarks \
  --prefix benchmarks/dev \
  --region us-east-1 \
  --profile default \
  --output-dir /tmp/bench_ingest \
  --upload
```

## Required Env / Args

Required runtime args:

- `--dataset`
- `--scene`
- `--bucket`
- `--output-dir`

Required when generating new local manifest:

- `--source-url`

Optional args:

- `--prefix`
- `--region`
- `--profile`
- `--license-url`
- `--expected-image-dirs`
- `--upload` (disabled by default)

Suggested environment variables (placeholders):

- `BENCHMARK_BUCKET` (maps to `--bucket`)
- `BENCHMARK_PREFIX` (maps to `--prefix`)
- `AWS_REGION` (maps to `--region`)
- `BENCH_DATASET`, `BENCH_SCENE`

## IAM / ECR Notes

IAM (placeholder policy scope):

- `s3:PutObject` on:
  - `arn:aws:s3:::<benchmark-bucket>/<prefix>/raw/*`
  - `arn:aws:s3:::<benchmark-bucket>/<prefix>/manifests/*`
- Optional: `s3:ListBucket` on `arn:aws:s3:::<benchmark-bucket>` (for preflight/list checks)
- CloudWatch logs write permissions
- If using SageMaker Processing, execution role trust + processing job permissions

ECR:

- Store ingestion image in project ECR repository (placeholder: `<account>.dkr.ecr.<region>.amazonaws.com/spaceport-bench-ingest:<tag>`)
- Image should include Python runtime and `scripts/bench/` files

Local upload run example (using AWS CLI profile):

```bash
python3 scripts/bench/ingest_to_s3.py \
  --dataset mipnerf360 \
  --scene garden \
  --output-dir /tmp/bench_ingest \
  --bucket spaceport-ml-benchmarks \
  --prefix benchmarks/dev \
  --region us-east-1 \
  --profile my-profile \
  --upload
```

## Compute Sizing (Placeholders)

Batch starter placeholder:

- vCPU: `2`
- Memory: `8 GiB`
- Ephemeral storage: `20-50 GiB` (depends on source archive size)

SageMaker starter placeholder:

- Instance: `ml.m5.large` (or equivalent)
- Volume size: `50 GiB`

Tune based on largest scene archive and unpacked footprint.

## Retries / Timeouts

Batch placeholder:

- Retries: `2`
- Attempt timeout: `3600s`

SageMaker Processing placeholder:

- `max_runtime_in_seconds: 3600`
- Retry behavior handled by orchestration layer

## Logs

Primary logs:

- CloudWatch Logs group (placeholder): `/aws/batch/job/spaceport-bench-ingest`
- Stream name: by job id / attempt

Optional exported logs:

- `s3://<benchmark-bucket>/<prefix>/results/<run_id>/<dataset>/<scene>/logs/...`

## Artifact Paths

Canonical write targets:

- Raw source payload: `s3://<benchmark-bucket>/<prefix>/raw/<dataset>/<scene>/...`
- Scene manifest: `s3://<benchmark-bucket>/<prefix>/manifests/<dataset>/<scene>.manifest.json`

Local job outputs before upload:

- `<output-dir>/downloads/<dataset>/<scene>/...`
- `<output-dir>/manifests/<dataset>/<scene>.manifest.json`
- `<output-dir>/s3_dry_run/<prefix>/manifests/<dataset>/<scene>.manifest.json`
