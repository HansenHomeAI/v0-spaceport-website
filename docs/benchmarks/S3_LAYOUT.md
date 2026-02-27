# Benchmark S3 Layout Contract

This document defines canonical S3 key prefixes for benchmark ingestion artifacts.

## Canonical Prefixes

- `raw/`: unmodified source downloads per dataset and scene
- `processed/`: normalized scene trees prepared for training/eval
- `manifests/`: scene-level reproducibility and provenance manifests
- `results/`: run-scoped metrics and artifacts

## Path Contract

Base bucket:

- `s3://<benchmark-bucket>/`

Per dataset + scene:

- `s3://<benchmark-bucket>/raw/<dataset>/<scene>/...`
- `s3://<benchmark-bucket>/processed/<dataset>/<scene>/...`
- `s3://<benchmark-bucket>/manifests/<dataset>/<scene>.manifest.json`

Per run:

- `s3://<benchmark-bucket>/results/<run_id>/<dataset>/<scene>/metrics.json`
- `s3://<benchmark-bucket>/results/<run_id>/<dataset>/<scene>/artifacts/...`

## Example Paths

- `s3://spaceport-ml-benchmarks/raw/mipnerf360/garden/source.zip`
- `s3://spaceport-ml-benchmarks/processed/mipnerf360/garden/images_4/0001.png`
- `s3://spaceport-ml-benchmarks/manifests/mipnerf360/garden.manifest.json`
- `s3://spaceport-ml-benchmarks/results/2026-02-27T15-00-00Z/mipnerf360/garden/metrics.json`

## Naming Convention

- Dataset keys are lowercase and stable (for example: `mipnerf360`, `tanksandtemples`, `deepblending`, `zipnerf`).
- Scene keys are lowercase and use original canonical names where possible.
- Manifest files are named `<scene>.manifest.json` under `manifests/<dataset>/`.
- Run IDs should be globally unique and sortable by time (UTC timestamp or timestamp + commit suffix).
