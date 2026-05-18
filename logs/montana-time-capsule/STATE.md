# Montana Time Capsule CV-HR State

## Branch

- Branch: `agent-40136728-montana-time-capsule`
- Purpose: preserve and run the exact Montana-era training stack for CV-HR without inheriting later pipeline/container changes.

## Runner

- Command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --launch`
- Idempotent state: `logs/montana-time-capsule/cv-hr-state.json`
- Dataset: `CV-HR`
- Required upload: one CV-HR zip with exactly `1710` image files.
- Upload search bucket: `s3://spaceport-uploads-staging/`
- Current archive: `s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
- Current archive proof: `1710` images, `6,931,098,350` bytes, ETag `3a18e20f13027204f59bd6f1df77b983-827`, VersionId `FwGuzoiTEKNT8SodLXu7Zrkg_b96qhOx`.
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

## 2026-05-18T17:29Z SfM Launch

- Archive validated by ZIP central-directory range reads: `1710` image entries, first `DJI_00001.JPG`, last `DJI_01710.JPG`.
- Command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
- Run id: `cvhr-mtc-20260518T1729Z`
- SfM job: `cvhr-mtc-20260518T1729Z-sfm`
- SfM ARN: `arn:aws:sagemaker:us-west-2:975050048887:processing-job/cvhr-mtc-20260518T1729Z-sfm`
- SfM status at launch verification: `InProgress`
- SfM input: `s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
- SfM output: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-mtc-20260518T1729Z/colmap`
- SfM image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`
- SfM instance: `ml.g4dn.xlarge`, volume `100` GB, max runtime `86400` seconds.
- SfM env: `COLMAP_ENABLE_SPATIAL_CHUNKING=1`, `COLMAP_CHUNK_MIN_CORE_REGISTERED_RATIO=0.90`.
- Log stream: `cvhr-mtc-20260518T1729Z-sfm/algo-1-1779125429`
- First live log proof: COLMAP feature extraction accepted the archive and was processing `4000 x 2250` images with GPS/gravity metadata; latest sampled progress at `2026-05-18T17:37Z` was `Processed file [56/1710]`.

## 2026-05-18T17:56Z Monitor Pass

- Branch/head/status command:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `31c5765c6227eaa6483f7e66758e9815c0d69ee1`, status clean (`## agent-40136728-montana-time-capsule...origin/agent-40136728-montana-time-capsule`).
- AWS identity command: `/opt/homebrew/bin/aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- SageMaker status command: `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress` for job `cvhr-mtc-20260518T1729Z-sfm` using pinned SfM image `sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`.
- CloudWatch stream command: `/opt/homebrew/bin/aws logs tail /aws/sagemaker/ProcessingJobs --since 20m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - Result: live COLMAP feature extraction progress observed through `Processed file [491/1710]`.
- Duplicate-job guard command: `/opt/homebrew/bin/aws sagemaker list-processing-jobs --name-contains cvhr-mtc-20260518T1729Z --max-results 10`
  - Result: only one matching processing job exists: `cvhr-mtc-20260518T1729Z-sfm` (`InProgress`).
- Advance-one-stage command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: state now reports `last_action=sfm_running`, `status=sfm_running`, `sfm_status=InProgress`; no new stage launched and no duplicate job created.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260518T1756Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T1756Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T1756Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T1756Z.log`
  - `logs/montana-time-capsule/launch-20260518T1755Z.log`
- Next unblocked step: wait for `cvhr-mtc-20260518T1729Z-sfm` to complete, then rerun `--launch` once to advance exactly one stage (3DGS launch).
