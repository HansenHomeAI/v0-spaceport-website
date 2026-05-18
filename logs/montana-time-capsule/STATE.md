# Montana Time Capsule CV-HR State

## Branch

- Branch: `agent-40136728-montana-time-capsule`
- Purpose: preserve and run the exact Montana-era training stack for CV-HR without inheriting later pipeline/container changes.

## Runner

- Command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --launch`
- Idempotent state: `logs/montana-time-capsule/cv-hr-state.json`
- Dataset: `CV-HR`
- Required upload: one CV-HR zip with exactly `1710` image files.
- Upload search bucket: `s3://spaceport-uploads/`
- Output bucket: `s3://spaceport-ml-processing-staging/`

## Default Time Capsule Stack

Default profile: `brass-chunked`

- SfM image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`
- SfM env: `COLMAP_ENABLE_SPATIAL_CHUNKING=1`, `COLMAP_CHUNK_MIN_CORE_REGISTERED_RATIO=0.90`
- 3DGS image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`
- Compression image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor@sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab`

Fallback profile: `horsetail-gps`, only after a proven default-profile failure.

## Resume Rules

1. Verify git branch/head/status and AWS identity first.
2. Do not launch duplicate CV-HR jobs. Read `cv-hr-state.json` before `--launch`.
3. Let the runner advance exactly one stage at a time: upload check, SfM, 3DGS, compression.
4. On a SageMaker failure, capture describe output, CloudWatch logs, S3 listings, and exact failure reason before patching.
5. Patch only a proven blocker and rerun the smallest failed stage.
6. Final acceptance requires the compressed bundle to load in the viewer with skybox and no-sky modes, plus visual quality evidence.
