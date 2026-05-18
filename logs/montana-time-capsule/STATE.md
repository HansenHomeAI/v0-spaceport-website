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

## 2026-05-18T18:00Z Ledger Commit + Push

- Commit: `dfd66f0591b45bf2881c72ea27b098edcf828a0a`
- Commit message: `chore: record cv-hr montana sfm monitor evidence [skip ci]`
- Push command: `git push origin agent-40136728-montana-time-capsule`
- Push result: branch updated on origin (`31c5765c..dfd66f05`).
- Exact-head workflow check command:
  - `/opt/homebrew/bin/gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` (no exact-head workflows, expected for `[skip ci]` ledger-only commit).
- Branch workflow evidence (latest on branch): `logs/montana-time-capsule/gh-run-list-agent-40136728-20260518T1800Z.json`
- Exact-head workflow evidence: `logs/montana-time-capsule/gh-run-list-exact-head-20260518T1800Z.json`
- Next unblocked step: continue polling SfM `cvhr-mtc-20260518T1729Z-sfm`; when it reaches `Completed`, run `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch` exactly once to launch 3DGS.

## 2026-05-18T18:13Z Monitor Pass

- Branch/head/status command:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short --branch`
  - Result before this pass: branch `agent-40136728-montana-time-capsule`, head `f30edce52753ad59709711d5dbbdc6f9a430af18`, status clean (`## agent-40136728-montana-time-capsule...origin/agent-40136728-montana-time-capsule`).
- AWS identity command: `/opt/homebrew/bin/aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- SageMaker status command: `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress` for `cvhr-mtc-20260518T1729Z-sfm`; pinned SfM image unchanged (`sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`).
- CloudWatch stream command: `/opt/homebrew/bin/aws logs tail /aws/sagemaker/ProcessingJobs --since 20m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - Result: live COLMAP feature extraction observed through `Processed file [1011/1710]` at `2026-05-18T18:13:58Z`.
- Duplicate-job guard command: `/opt/homebrew/bin/aws sagemaker list-processing-jobs --name-contains cvhr-mtc-20260518T1729Z --max-results 20`
  - Result: still only one matching job (`cvhr-mtc-20260518T1729Z-sfm`, `InProgress`).
- Advance-one-stage command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: state remains `status=sfm_running`, `sfm_status=InProgress`; no new stage launched and no duplicate job created.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260518T181357Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T181357Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T181357Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T181357Z.log`
  - `logs/montana-time-capsule/launch-20260518T181357Z.log`
- Next unblocked step: wait for `cvhr-mtc-20260518T1729Z-sfm` to complete, then run the same `--launch` command exactly once to launch 3DGS with the pinned Montana 3DGS image.

## 2026-05-18T18:17Z Monitor Pass

- SageMaker status command: `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress`.
- CloudWatch stream command: `/opt/homebrew/bin/aws logs tail /aws/sagemaker/ProcessingJobs --since 20m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - Result: latest observed feature extraction progress `Processed file [1099/1710]`.
- Duplicate-job guard command: `/opt/homebrew/bin/aws sagemaker list-processing-jobs --name-contains cvhr-mtc-20260518T1729Z --max-results 20`
  - Result: still one matching processing job (`cvhr-mtc-20260518T1729Z-sfm`), no duplicates.
- Advance-one-stage command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: `status=sfm_running`; runner held position correctly and did not launch 3DGS early.
- Evidence files:
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T181722Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T181722Z.json`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T181722Z.log`
  - `logs/montana-time-capsule/launch-20260518T181722Z.log`
- Next unblocked step: continue polling until SfM reaches `Completed`, then run `--launch` once to start 3DGS.

## 2026-05-18T18:18Z Ledger Commit + Push

- Commit: `483efaeb3c05d1f8647da38f73e98584d43b0807`
- Commit message: `chore: record cv-hr montana monitor poll [skip ci]`
- Push command: `git push origin agent-40136728-montana-time-capsule`
- Push result: branch updated on origin (`eed8727c..483efaeb`).
- Exact-head workflow check command:
  - `/opt/homebrew/bin/gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url`
  - Exact-head selection result for `483efaeb3c05d1f8647da38f73e98584d43b0807`: `[]` (no exact-head workflows, expected for `[skip ci]`).
- Branch workflow evidence: `logs/montana-time-capsule/gh-run-list-agent-40136728-20260518T181809Z.json`
- Exact-head workflow evidence: `logs/montana-time-capsule/gh-run-list-exact-head-20260518T181809Z.json`
- Next unblocked step: keep polling SfM until `Completed`, then run `--launch` exactly once to advance to 3DGS.

## 2026-05-18T18:33Z Monitor Pass

- Branch/head/status command:
  - `git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git status --short --branch`
  - Result: branch `agent-40136728-montana-time-capsule`, head `1281188169eed19054fcb6ae370c9e102e28b560`, status clean before this pass.
- AWS identity command: `/opt/homebrew/bin/aws sts get-caller-identity`
  - Result: account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- SageMaker status command: `/opt/homebrew/bin/aws sagemaker describe-processing-job --processing-job-name cvhr-mtc-20260518T1729Z-sfm`
  - Result: `ProcessingJobStatus=InProgress` for `cvhr-mtc-20260518T1729Z-sfm`; pinned SfM image unchanged (`sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`).
- Duplicate-job guard command: `/opt/homebrew/bin/aws sagemaker list-processing-jobs --name-contains cvhr-mtc-20260518T1729Z --max-results 20`
  - Result: one matching processing job (`cvhr-mtc-20260518T1729Z-sfm`, `InProgress`); no duplicate jobs launched.
- Advance-one-stage command: `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --launch`
  - Result: state held at `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`; runner did not launch 3DGS early.
- CloudWatch proof command: `/opt/homebrew/bin/aws logs tail /aws/sagemaker/ProcessingJobs --since 20m --log-stream-name-prefix cvhr-mtc-20260518T1729Z-sfm --format short`
  - Result: live SfM feature extraction progressed through `Processed file [1522/1710]` at `2026-05-18T18:33:44Z`.
- Evidence files:
  - `logs/montana-time-capsule/aws-sts-20260518T183327Z.json`
  - `logs/montana-time-capsule/sagemaker-describe-cvhr-mtc-20260518T1729Z-sfm-20260518T183327Z.json`
  - `logs/montana-time-capsule/sagemaker-list-cvhr-mtc-20260518T1729Z-20260518T183327Z.json`
  - `logs/montana-time-capsule/launch-20260518T183334Z.log`
  - `logs/montana-time-capsule/cloudwatch-tail-cvhr-mtc-20260518T1729Z-sfm-20260518T183346Z.log`
- Next unblocked step: continue polling until `cvhr-mtc-20260518T1729Z-sfm` reaches `Completed`, then run the same `--launch` command exactly once to launch 3DGS with the pinned Montana 3DGS image.

## 2026-05-18T18:34Z Ledger Commit + Push

- Commit: `ec78016b85165431f7487738ff00f39f5479aa56`
- Commit message: `chore: record montana sfm monitor pass [skip ci]`
- Push command: `git push origin agent-40136728-montana-time-capsule`
- Push result: branch updated on origin (`12811881..ec78016b`).
- Exact-head workflow check command:
  - `/opt/homebrew/bin/gh run list --branch agent-40136728-montana-time-capsule --limit 50 --json databaseId,headSha,workflowName,status,conclusion,createdAt,updatedAt,url | jq --arg sha "$(git rev-parse HEAD)" '[.[] | select(.headSha==$sha)]'`
  - Result: `[]` (no exact-head workflows, expected for `[skip ci]` ledger-only commit).
- Branch workflow evidence (latest on branch):
  - `logs/montana-time-capsule/gh-run-list-agent-40136728-20260518T183450Z.json`
- Exact-head workflow evidence:
  - `logs/montana-time-capsule/gh-run-list-exact-head-20260518T183450Z.json`
- Last meaningful non-skip workflow proof retained:
  - `CDK Deploy` success on head `1b264bc2ac6be3bf34ca06582895f7f750e9a442` run `26049509375`.
- Next unblocked step: continue polling SfM job `cvhr-mtc-20260518T1729Z-sfm` until `Completed`; immediately run the same `--launch` command once to advance to pinned Montana 3DGS.
