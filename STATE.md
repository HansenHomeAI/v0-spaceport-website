# CV-HR Parallel Splat State

updated: 2026-05-18T21:20:00Z
branch: agent-73910482-cvhr-parallel-splat
base: origin/development @ b2b451ae6dc46a25c7547162b6f8d037437f2950
repo: HansenHomeAI/v0-spaceport-website

## Goal

Run a secondary, isolated CV-HR E2E splat pipeline in parallel with the existing
Montana time capsule run, without touching or advancing the existing
`cvhr-mtc-20260518T1729Z` jobs.

## Isolation

- Worktree: `/Users/gabrielhansen/worktrees/agent-73910482-cvhr-parallel-splat`
- Durable state: `logs/cvhr-parallel/cv-hr-state.json`
- Durable ledger: `logs/cvhr-parallel/STATE.md`
- Run id namespace: `cvhr-secondary-*`
- Source archive: `s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`

## Current Step

- Tooling commits have been cherry-picked from the Montana time capsule branch.
- Runner supports explicit isolated run ids.
- Local static checks passed:
  - `python3 -m py_compile scripts/montana_time_capsule/cv_hr_time_capsule.py`
  - `python3 -m unittest tests.unit.test_montana_time_capsule`
  - `git diff --check`
- CV-HR archive was validated into `logs/cvhr-parallel/cv-hr-state.json`:
  - run id: `cvhr-secondary-20260518t2113z`
  - status: `upload_ready`
  - image count: `1710`
  - size: `6931098350`
  - ETag: `3a18e20f13027204f59bd6f1df77b983-827`
- Prelaunch AWS state:
  - account: `975050048887`
  - Step Functions running executions: `0`
  - SageMaker training jobs in progress: `0`
  - SageMaker processing jobs in progress: `md1-viscell-leaf-08-1779136078`, `md1-viscell-leaf-01-1779136049`, `md1-shrunk-prodspine-sfm-1779128752`, `cvhr-mtc-20260518T1729Z-sfm`
- No secondary SageMaker job has been launched yet.

## 2026-05-18T21:20Z Secondary SfM Launch

- Commit/push before launch:
  - commit: `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`
  - branch: `agent-73910482-cvhr-parallel-splat`
  - exact-head `CDK Deploy` run `26060892234` succeeded.
- Launch command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --run-id cvhr-secondary-20260518t2113z --state-file logs/cvhr-parallel/cv-hr-state.json --launch`
- Secondary SfM job:
  - name: `cvhr-secondary-20260518t2113z-sfm`
  - ARN: `arn:aws:sagemaker:us-west-2:975050048887:processing-job/cvhr-secondary-20260518t2113z-sfm`
  - status at startup verification: `InProgress`
  - input: `s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
  - output: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - instance: `ml.g4dn.xlarge`
  - image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`
  - `SFM_GIT_HEAD`: `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`
- Startup evidence:
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T2120Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-list-cvhr-secondary-20260518t2113z-20260518T2120Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260518T2120Z.txt`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260518T2120Z.json`
- S3 output is currently empty, expected before `S3UploadMode=EndOfJob`.
- Heartbeat automation created:
  - id: `cv-hr-parallel-splat-monitor`
  - cadence: every 20 minutes
  - target: this thread

## 2026-05-18T21:44Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch progress reached feature extraction `Processed file [508/1710]`.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-18T22:04Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch progress reached feature extraction `Processed file [1024/1710]`.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-18T22:25Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch progress reached feature extraction `Processed file [1570/1710]`.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-18T22:52Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Feature extraction completed before this poll; COLMAP mapper is active.
- Latest CloudWatch mapper progress: `chunk_01_mapper_initial` reached `num_reg_frames=117`.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-18T23:12Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch mapper progress: `chunk_02_mapper_initial` reached `num_reg_frames=185`.
- `chunk_02_mapper_initial` logged `Keeping successful reconstruction` and started `model_converter`.
- Nonfatal COLMAP linear-solver warnings were observed, but the job continued and SageMaker reports no failure, OOM, or timeout.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-18T23:32Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch stage: `chunk_03_spatial_matcher_recovery`.
- Latest matching progress: processed `187/187` images and added `682` verified image pairs.
- `vocab_tree_builder` retried after rejecting `--max_num_images`; the fallback continued with older COLMAP-compatible flags.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-18T23:52Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T00:12Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:41Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T00:39Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:41Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T00:59Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T01:19Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T01:39Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T02:05Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T02:25Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T02:45Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T03:05Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T03:25Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T03:45Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T04:05Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T04:25Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.
