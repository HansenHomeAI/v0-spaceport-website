# CV-HR Parallel Splat State

updated: 2026-05-19T23:59:09Z
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

## 2026-05-19T04:45Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T05:05Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T05:25Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress`.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T05:45Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T06:05Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- Latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`.
- Latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`.
- Latest observed log line: loaded `1893703` descriptors and started building the visual-word index.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T14:42Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- The long `vocab_tree_builder` silence resolved; CloudWatch resumed with `chunk_03_mapper_recovery`.
- Latest observed progress: `num_reg_frames=152`, then `Retriangulation and Global bundle adjustment` at `2026-05-19T14:43:05Z`.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T15:07Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- CloudWatch is actively advancing after the prior vocab-tree pause.
- Latest observed stage: `chunk_04_vocab_tree_matcher_recovery`.
- Latest observed progress: `Processing image [117/187]` at `2026-05-19T15:08:45Z`.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T15:28Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- CloudWatch continues to advance after the prior vocab-tree pause.
- Latest observed stage: `chunk_05_spatial_matcher`.
- Latest observed progress: `Processing image [67/177]` at `2026-05-19T15:29:50Z`.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T15:48Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- CloudWatch is still advancing: current observed stage is `chunk_05_mapper_recovery`.
- Latest positive mapper progress: `num_reg_frames=70` at `2026-05-19T15:52:10Z`, followed by bundle-adjustment warnings that have been nonfatal in this run.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T16:08Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- CloudWatch continues to advance in `chunk_05_mapper_recovery`.
- Latest mapper progress reached `num_reg_frames=171` at `2026-05-19T16:08:25Z`, then entered another retriangulation/global bundle-adjustment pass.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T16:28Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- CloudWatch advanced from chunk 05 into `chunk_06_mapper_recovery`.
- Latest mapper progress reached `num_reg_frames=14` in chunk 06 at `2026-05-19T16:30:05Z`, followed by retriangulation/global bundle adjustment.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T16:48Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- CloudWatch continues to advance in `chunk_06_mapper_recovery`.
- Latest mapper progress reached `num_reg_frames=184` at `2026-05-19T16:48:01Z`, then entered retriangulation/global bundle adjustment.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T17:08Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- CloudWatch advanced from chunk 06 into `chunk_07_mapper_initial`.
- Latest observed chunk 07 mapper state is repeatedly trying candidate images with `num_reg_frames=5`; this is active COLMAP work, not a SageMaker failure.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T17:29Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- CloudWatch advanced through later chunk work into `chunk_09_sequential_matcher`.
- Latest observed matcher progress: `Processing image [115/179]` at `2026-05-19T17:30:38Z`.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T17:49Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- CloudWatch advanced into `chunk_10_mapper_initial`.
- Latest mapper progress reached `num_reg_frames=126` at `2026-05-19T17:50:33Z`, followed by retriangulation/global bundle adjustment.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` and other external jobs were left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T18:11Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- CloudWatch is still active in the post-registration chunk 10 path.
- Latest observed progress: `chunk_10_mapper_initial` kept a successful reconstruction at `2026-05-19T17:55:50Z` after `12.724` minutes, then entered global bundle adjustment at `2026-05-19T17:57:00Z`.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` was directly checked, found `Stopped`, and left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T18:31Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- CloudWatch has no newer event after the chunk 10 global bundle adjustment line at `2026-05-19T17:57:00Z`.
- Latest positive mapper progress in the fetched window remains `num_reg_frames=172` before `chunk_10_mapper_initial` kept a successful reconstruction.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` was directly checked again, remains `Stopped`, and was left untouched.
- Separate external processing jobs `cvhr-viscell-c03-1779215211` and `cvhr-viscell-c04-1779215211` were observed and left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T18:51Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- CloudWatch still has no newer event after the `chunk_bundle_adjuster` global bundle adjustment line at `2026-05-19T17:57:00Z`.
- Latest positive mapper progress in the fetched window remains `num_reg_frames=172`, followed by `Keeping successful reconstruction` for chunk 10.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` remains `Stopped` and was left untouched.
- Separate external CV-HR processing and MD1 training jobs were observed and left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T19:11Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` remains `InProgress` by direct SageMaker describe.
- CloudWatch still has no newer event after `chunk_bundle_adjuster` global bundle adjustment at `2026-05-19T17:57:00Z`.
- Latest positive mapper progress remains chunk 10 `num_reg_frames=172`, followed by `Keeping successful reconstruction`.
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- No duplicate secondary CV-HR jobs were launched.
- Existing `cvhr-mtc-20260518T1729Z-sfm` remains `Stopped` and was left untouched.
- External CV-HR processing and MD1 training jobs were observed and left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T19:33Z Heartbeat Poll

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` still reports `InProgress` by direct SageMaker describe, so no secondary 3DGS launch was attempted from this state file.
- The EndOfJob S3 handoff has begun/landed: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap` now lists `1717` objects totaling `10379523417` bytes.
- Sparse COLMAP output is present under `sparse/0`: `cameras.txt`, `frames.txt`, `images.txt`, `points3D.txt`, and `rigs.txt`, totaling `877326466` bytes.
- CloudWatch still has no newer event after `chunk_bundle_adjuster` global bundle adjustment at `2026-05-19T17:57:00Z`.
- No duplicate secondary CV-HR jobs were launched by this branch/state.
- Existing `cvhr-mtc-20260518T1729Z-sfm` remains `Stopped` and was left untouched.
- An external CV-HR training job `cvhr-mtc-secondary-20260518t2113z-3dgs` is `InProgress`; it does not match this branch state run id and was left untouched.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T19:53Z SfM Complete And 3DGS Launch

- Secondary SfM job `cvhr-secondary-20260518t2113z-sfm` now reports `Completed`.
- CloudWatch terminal summary reports:
  - cameras registered: `1`
  - images registered: `1693`
  - images copied for 3DGS: `1710`
  - 3D points: `1329830`
  - processing time: `78924.24` seconds
  - completion time: `2026-05-19T19:19:06Z`
- S3 validation:
  - COLMAP handoff: `1717` objects, `10379523417` bytes
  - image objects: `1710`, `6930827064` bytes
  - sparse model: `sparse/0/cameras.txt`, `frames.txt`, `images.txt`, `points3D.txt`, `rigs.txt`
  - registered images counted from `sparse/0/images.txt`: `1693`
  - 3D points counted from `sparse/0/points3D.txt`: `1329830`
- Guarded launch command run exactly once after validation:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --run-id cvhr-secondary-20260518t2113z --state-file logs/cvhr-parallel/cv-hr-state.json --launch`
- Branch-owned 3DGS job:
  - name: `cvhr-secondary-20260518t2113z-3dgs`
  - status after launch: `InProgress`
  - secondary status: `Pending`
  - input: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - output: `s3://spaceport-ml-processing-staging/3dgs/cvhr-secondary-20260518t2113z/`
  - image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`
- Separate external job `cvhr-mtc-secondary-20260518t2113z-3dgs` remains `InProgress` and was not modified.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T20:13Z Heartbeat Poll

- Branch-owned 3DGS job `cvhr-secondary-20260518t2113z-3dgs` remains `InProgress`.
- Direct SageMaker state: `Training`, started `2026-05-19T13:59:27.439000-06:00`, no failure reason.
- CloudWatch stream `cvhr-secondary-20260518t2113z-3dgs/algo-1-1779220766` is live.
- Latest fetched 3DGS evidence: COLMAP conversion succeeded, Nerfstudio matched `1693` images / `99.01%`, validated `1693` frames, and started `ns-train splatfacto-w-light` for `30000` iterations at `2026-05-19T20:08:26Z`.
- No OOM, traceback, or SageMaker failure is visible in the fetched training logs.
- 3DGS S3 output remains empty, expected while the training job is still running.
- No duplicate secondary 3DGS or compression job was launched.
- Separate external job `cvhr-mtc-secondary-20260518t2113z-3dgs` remains `InProgress` and was not modified.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T20:33Z Heartbeat Poll

- Branch-owned 3DGS job `cvhr-secondary-20260518t2113z-3dgs` remains `InProgress`.
- Direct SageMaker state: `Training`, started `2026-05-19T13:59:27.439000-06:00`, no failure reason.
- CloudWatch stream is still `cvhr-secondary-20260518t2113z-3dgs/algo-1-1779220766`.
- Latest CloudWatch event remains `2026-05-19T20:08:26Z`, immediately after `ns-train splatfacto-w-light` started for `30000` iterations.
- No OOM, traceback, or SageMaker failure is visible in fetched logs.
- 3DGS S3 output remains empty, expected while the training job is still running.
- No duplicate secondary 3DGS or compression job was launched.
- Separate external job `cvhr-mtc-secondary-20260518t2113z-3dgs` remains `InProgress` and was not modified.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T20:53Z Heartbeat Poll

- Branch-owned 3DGS job `cvhr-secondary-20260518t2113z-3dgs` remains `InProgress`.
- Direct SageMaker state: `Training`, started `2026-05-19T13:59:27.439000-06:00`, no failure reason.
- CloudWatch stream remains `cvhr-secondary-20260518t2113z-3dgs/algo-1-1779220766`.
- Latest CloudWatch event remains `2026-05-19T20:08:26Z`, immediately after `ns-train splatfacto-w-light` started for `30000` iterations.
- No OOM, traceback, or SageMaker failure is visible in fetched logs.
- 3DGS S3 output remains empty, expected while the training job is still running.
- No duplicate secondary 3DGS or compression job was launched.
- Separate external job `cvhr-mtc-secondary-20260518t2113z-3dgs` remains `InProgress` and was not modified.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T21:13Z Heartbeat Poll

- Branch-owned 3DGS job `cvhr-secondary-20260518t2113z-3dgs` remains `InProgress`.
- Direct SageMaker state: `Training`, started `2026-05-19T13:59:27.439000-06:00`, no failure reason.
- CloudWatch stream remains `cvhr-secondary-20260518t2113z-3dgs/algo-1-1779220766`.
- Latest CloudWatch event remains `2026-05-19T20:08:26Z`, immediately after `ns-train splatfacto-w-light` started for `30000` iterations.
- No OOM, traceback, or SageMaker failure is visible in fetched logs.
- 3DGS S3 output remains empty, expected while the training job is still running.
- No duplicate secondary 3DGS or compression job was launched.
- Separate external job `cvhr-mtc-secondary-20260518t2113z-3dgs` remains `InProgress` and was not modified.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T21:33Z Heartbeat Poll

- Branch-owned 3DGS job `cvhr-secondary-20260518t2113z-3dgs` remains `InProgress`.
- Direct SageMaker state: `Training`, started `2026-05-19T13:59:27.439000-06:00`, no failure reason.
- CloudWatch stream remains `cvhr-secondary-20260518t2113z-3dgs/algo-1-1779220766`.
- Latest CloudWatch event remains `2026-05-19T20:08:26Z`, immediately after `ns-train splatfacto-w-light` started for `30000` iterations.
- No OOM, traceback, or SageMaker failure is visible in fetched logs.
- 3DGS S3 output remains empty, expected while the training job is still running.
- No duplicate secondary 3DGS or compression job was launched.
- Separate external job `cvhr-mtc-secondary-20260518t2113z-3dgs` remains `InProgress` and was not modified.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T21:53Z Heartbeat Poll

- Branch-owned 3DGS job `cvhr-secondary-20260518t2113z-3dgs` remains `InProgress`.
- Direct SageMaker state: `Training`, started `2026-05-19T13:59:27.439000-06:00`, no failure reason.
- CloudWatch stream remains `cvhr-secondary-20260518t2113z-3dgs/algo-1-1779220766`.
- Latest CloudWatch event remains `2026-05-19T20:08:26Z`, immediately after `ns-train splatfacto-w-light` started for `30000` iterations.
- No OOM, traceback, or SageMaker failure is visible in fetched logs.
- 3DGS S3 output remains empty, expected while the training job is still running.
- No duplicate secondary 3DGS or compression job was launched.
- Separate external job `cvhr-mtc-secondary-20260518t2113z-3dgs` remains `InProgress` and was not modified.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T22:13Z Heartbeat Poll

- Branch-owned 3DGS job `cvhr-secondary-20260518t2113z-3dgs` remains `InProgress`.
- Direct SageMaker state: `Training`, started `2026-05-19T13:59:27.439000-06:00`, no failure reason.
- CloudWatch stream remains `cvhr-secondary-20260518t2113z-3dgs/algo-1-1779220766`.
- Latest CloudWatch tail still ends at `2026-05-19T20:08:26Z`, immediately after `ns-train splatfacto-w-light` started for `30000` iterations.
- Same tail confirms COLMAP-to-Nerfstudio conversion stayed valid: `1693` matched images, `99.01%` pose coverage, and `1693` frames in `transforms.json`.
- No OOM, traceback, or SageMaker failure is visible in fetched logs.
- 3DGS S3 output remains empty, expected while the training job is still running.
- No duplicate secondary 3DGS or compression job was launched.
- Separate external job `cvhr-mtc-secondary-20260518t2113z-3dgs` remains `InProgress` and was not modified.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T22:33Z Heartbeat Poll

- Branch-owned 3DGS job `cvhr-secondary-20260518t2113z-3dgs` remains `InProgress`.
- Direct SageMaker state: `Training`, started `2026-05-19T13:59:27.439000-06:00`, no failure reason.
- CloudWatch stream remains `cvhr-secondary-20260518t2113z-3dgs/algo-1-1779220766`.
- Latest CloudWatch tail still ends at `2026-05-19T20:08:26Z`, immediately after `ns-train splatfacto-w-light` started for `30000` iterations.
- Same tail confirms COLMAP-to-Nerfstudio conversion stayed valid: `1693` matched images, `99.01%` pose coverage, and `1693` frames in `transforms.json`.
- No OOM, traceback, or SageMaker failure is visible in fetched logs.
- 3DGS S3 output remains empty, expected while the training job is still running.
- No duplicate secondary 3DGS or compression job was launched.
- Separate external job `cvhr-mtc-secondary-20260518t2113z-3dgs` remains `InProgress` and was not modified.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T22:53Z Heartbeat Poll

- Branch-owned 3DGS job `cvhr-secondary-20260518t2113z-3dgs` remains `InProgress`.
- Direct SageMaker state: `Training`, started `2026-05-19T13:59:27.439000-06:00`, no failure reason.
- CloudWatch stream remains `cvhr-secondary-20260518t2113z-3dgs/algo-1-1779220766`.
- Latest CloudWatch tail still ends at `2026-05-19T20:08:26Z`, immediately after `ns-train splatfacto-w-light` started for `30000` iterations.
- Same tail confirms COLMAP-to-Nerfstudio conversion stayed valid: `1693` matched images, `99.01%` pose coverage, and `1693` frames in `transforms.json`.
- No OOM, traceback, or SageMaker failure is visible in fetched logs.
- 3DGS S3 output remains empty, expected while the training job is still running.
- No duplicate secondary 3DGS or compression job was launched.
- Separate external job `cvhr-mtc-secondary-20260518t2113z-3dgs` completed independently and was not modified or used.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T23:13Z Heartbeat Poll

- Branch-owned 3DGS job `cvhr-secondary-20260518t2113z-3dgs` remains `InProgress`.
- Direct SageMaker state: `Training`, started `2026-05-19T13:59:27.439000-06:00`, no failure reason.
- CloudWatch stream remains `cvhr-secondary-20260518t2113z-3dgs/algo-1-1779220766`.
- Latest CloudWatch tail still ends at `2026-05-19T20:08:26Z`, immediately after `ns-train splatfacto-w-light` started for `30000` iterations.
- Same tail confirms COLMAP-to-Nerfstudio conversion stayed valid: `1693` matched images, `99.01%` pose coverage, and `1693` frames in `transforms.json`.
- No OOM, traceback, or SageMaker failure is visible in fetched logs.
- 3DGS S3 output remains empty, expected while the training job is still running.
- No duplicate secondary 3DGS or compression job was launched.
- Separate external job `cvhr-mtc-secondary-20260518t2113z-compression` is now visible as `InProgress`; it was not modified or used.
- Details and evidence are recorded in `logs/cvhr-parallel/STATE.md`.

## 2026-05-19T23:33Z 3DGS Complete, Compression Launched

- Branch/head/status before this poll:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `a265121f0743a6b2bb36ac94a7b24610bc3323ea` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- 3DGS completed and was validated before advancing:
  - job: `cvhr-secondary-20260518t2113z-3dgs`
  - model artifact: `s3://spaceport-ml-processing-staging/3dgs/cvhr-secondary-20260518t2113z/cvhr-secondary-20260518t2113z-3dgs/output/model.tar.gz`
  - S3 artifact size: `104412084` bytes
  - CloudWatch showed real training progress through `29999 (100.00%)`, `Training Finished`, export success, and no OOM/traceback/failure.
  - extracted tarball contains `splat.ply`, `training_metadata.json`, `export_manifest.json`, `background_skybox.webp`, `background_manifest.json`, and `floater_pruning_summary.json`
  - PLY header: binary little endian, `element vertex 463720`
  - metadata confirms `training_completed=true`, `sogs_compatible=true`, and `playcanvas_ready=true`
- Guarded compression launch command run exactly once after validation:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --run-id cvhr-secondary-20260518t2113z --state-file logs/cvhr-parallel/cv-hr-state.json --launch`
- Branch-owned compression job:
  - name: `cvhr-secondary-20260518t2113z-compression`
  - status at post-launch verification: `InProgress`
  - input: `s3://spaceport-ml-processing-staging/3dgs/cvhr-secondary-20260518t2113z/cvhr-secondary-20260518t2113z-3dgs/output/model.tar.gz`
  - output: `s3://spaceport-ml-processing-staging/compressed/cvhr-secondary-20260518t2113z/`
  - image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor@sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab`
  - compressed S3 output was empty at launch, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` reports `status=compression_started`, `last_action=launched_compression`, `3dgs_status=Completed`, `compression_job_name=cvhr-secondary-20260518t2113z-compression`, `updated_at=2026-05-19T23:35:56Z`
- External `cvhr-mtc-secondary-*` jobs were observed as read-only context only and were not modified or used.
- Next gate: monitor `cvhr-secondary-20260518t2113z-compression`; after it completes, validate compressed manifests/files, copy to the public processing bucket with non-KMS encryption, then run hosted viewer checks with skybox and `skybox=none`.

## 2026-05-19T23:55Z Compression Complete, Public Bundle Reachable

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head at start: `dbbded6eb92a6476e3d3a05955a6d721867f9959` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- Compression completed:
  - job: `cvhr-secondary-20260518t2113z-compression`
  - started: `2026-05-19T17:36:36.055000-06:00`
  - ended: `2026-05-19T17:45:57.186000-06:00`
  - no failure reason
  - CloudWatch confirms `PlayCanvas SOGS compression completed successfully`, `15.25x` compression, `7` WebP texture files, and no OOM/Traceback/ERROR/failed strings in fetched events.
- Private compressed output validation:
  - source: `s3://spaceport-ml-processing-staging/compressed/cvhr-secondary-20260518t2113z/`
  - private output: `22` objects / `15145510` bytes
  - `supersplat_bundle`: `13` required objects, no missing required files
  - `meta.json` means shape: `[462400, 3]`
  - compression ratio: `15.246227223278225`
- Public handoff:
  - copied `supersplat_bundle/` to `s3://spaceport-ml-processing/compressed/cvhr-secondary-20260518t2113z/supersplat_bundle/`
  - destination encryption is `AES256`, not KMS
  - explicit content types were set for JSON and WebP assets
  - public URL: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/cvhr-secondary-20260518t2113z/supersplat_bundle/meta.json`
  - public GET for `meta.json` returned `200 OK`
  - public GET for `background_skybox.webp` returned `200 OK`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` reports `status=completed`, `compression_status=Completed`, and records the public bundle S3/HTTPS URLs.
- Next gate: run hosted viewer checks against the public URL in skybox and `skybox=none` modes, capture screenshots, and only then call the CV-HR secondary splat visually accepted.
