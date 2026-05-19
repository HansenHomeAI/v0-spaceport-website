# CV-HR Parallel Splat Ledger

updated: 2026-05-18T21:20:00Z
branch: agent-73910482-cvhr-parallel-splat
base: origin/development @ b2b451ae6dc46a25c7547162b6f8d037437f2950

## Goal

Train a fully functioning, high-quality CV-HR splat with an isolated secondary
pipeline run. This run is intentionally parallel to the existing
`cvhr-mtc-20260518T1729Z` job family and must not touch that job family except
as read-only context.

## Inputs

- Dataset: CV-HR
- Source archive: `s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip`
- Expected images: `1710`
- Default profile: `brass-chunked`
- SfM image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`
- 3DGS image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:482c1789b2d885beccf351b68d50e4b8135c43d5921c2379b0ba5fb152ed15db`
- Compression image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor@sha256:a0784727da1870ce9caa4774dc831a32fb96cd1574df389cf9093fbf18f4f4ab`

## Guardrails

- Do not stop, modify, or advance `cvhr-mtc-20260518T1729Z-*`.
- Launch at most one secondary SfM job until it reaches a terminal state.
- Advance exactly one stage per runner invocation after a stage completes.
- Patch only failures proven by this secondary run.
- Final acceptance requires public bundle reachability plus hosted viewer proof
  with skybox and no-sky modes.

## Current State

- Runner tooling has been cherry-picked from the Montana time capsule branch.
- The runner now supports explicit `--run-id` for isolated job names and S3 prefixes.
- Local static checks passed:
  - `python3 -m py_compile scripts/montana_time_capsule/cv_hr_time_capsule.py`
  - `python3 -m unittest tests.unit.test_montana_time_capsule`
  - `git diff --check`
- Archive validation created `logs/cvhr-parallel/cv-hr-state.json`:
  - run id: `cvhr-secondary-20260518t2113z`
  - status: `upload_ready`
  - image count: `1710`
  - size: `6931098350`
  - ETag: `3a18e20f13027204f59bd6f1df77b983-827`
- Prelaunch evidence files:
  - `logs/cvhr-parallel/evidence/aws-sts-prelaunch-20260518T2114Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-prelaunch-20260518T2114Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-prelaunch-20260518T2114Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-prelaunch-20260518T2114Z.json`
  - `logs/cvhr-parallel/evidence/cvhr-archive-head-20260518T2114Z.json`
  - `logs/cvhr-parallel/evidence/gh-runs-prepush-20260518T2114Z.json`

## 2026-05-18T21:20Z Secondary SfM Launch

- Commit/push before launch:
  - commit: `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`
  - exact-head `CDK Deploy` run `26060892234` succeeded.
  - evidence: `logs/cvhr-parallel/evidence/gh-runs-exact-head-0b60d8bf-20260518T2120Z.json`
- Launch command:
  - `python3 scripts/montana_time_capsule/cv_hr_time_capsule.py --input-s3-uri s3://spaceport-uploads-staging/1779123600000-cvhr-Archive.zip --run-id cvhr-secondary-20260518t2113z --state-file logs/cvhr-parallel/cv-hr-state.json --launch`
- Secondary SfM job:
  - name: `cvhr-secondary-20260518t2113z-sfm`
  - ARN: `arn:aws:sagemaker:us-west-2:975050048887:processing-job/cvhr-secondary-20260518t2113z-sfm`
  - startup status: `InProgress`
  - output: `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm@sha256:8fe38e3413e09954dcad77b8436c2a04defd20a39bdae1b3df573c504ef98811`
  - `SFM_GIT_HEAD`: `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`
- Startup evidence:
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T2120Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-list-cvhr-secondary-20260518t2113z-20260518T2120Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260518T2120Z.txt`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260518T2120Z.json`
- S3 output remains empty, expected before `S3UploadMode=EndOfJob`.
- Heartbeat automation:
  - id: `cv-hr-parallel-splat-monitor`
  - kind: thread heartbeat
  - cadence: every 20 minutes

## 2026-05-18T21:44Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `0d1c8c40749ab0386a29e4ca7c7eda92ffdfa61a` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-shrunk-prodspine-sfm-1779128752`, `cvhr-mtc-20260518T1729Z-sfm`
  - in-progress training jobs: `0`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest observed feature extraction: `Processed file [508/1710]`
  - images are `4000 x 2250` with GPS/gravity metadata and SIFT features
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` now reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260518T2143Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T2143Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260518T2143Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260518T2143Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260518T2143Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260518T2143Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260518T2143Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260518T2143Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260518T2143Z.log`
  - `logs/cvhr-parallel/evidence/runner-status-20260518T2144Z.json`

## 2026-05-18T22:04Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `ec38a0f4a6cc5f9a73b69610bb64e993058fc256` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-shrunk-prodspine-sfm-1779128752`, `cvhr-mtc-20260518T1729Z-sfm`
  - in-progress training jobs: `0`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest observed feature extraction: `Processed file [1024/1710]`
  - images are `4000 x 2250` with GPS/gravity metadata and SIFT features
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` still reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260518T2203Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T2203Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260518T2203Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260518T2203Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260518T2203Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260518T2203Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260518T2203Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260518T2203Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260518T2203Z.log`
  - `logs/cvhr-parallel/evidence/runner-status-20260518T2203Z.json`

## 2026-05-18T22:25Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `521d93a639ccf19c9ecf7c8c26e5a23431bfd922` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l01-1779141986`, `md1-viscell-full-l00-1779141981`, `md1-shrunk-prodspine-sfm-1779128752`, `cvhr-mtc-20260518T1729Z-sfm`
  - in-progress training jobs: `0`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest observed feature extraction: `Processed file [1570/1710]`
  - images are `4000 x 2250` with GPS/gravity metadata and SIFT features
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` still reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260518T2224Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T2224Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260518T2224Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260518T2224Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260518T2224Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260518T2224Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260518T2224Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260518T2224Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260518T2224Z.log`
  - `logs/cvhr-parallel/evidence/runner-status-20260518T2224Z.json`

## 2026-05-18T22:52Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `16d8e90278d1f157d9986061690b51befc3fd151` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l02-1779143476`, `md1-viscell-full-l01-1779141986`, `md1-shrunk-prodspine-sfm-1779128752`, `cvhr-mtc-20260518T1729Z-sfm`
  - in-progress training jobs: `0`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - feature extraction completed before this poll; mapper is active
  - latest observed mapper progress: `chunk_01_mapper_initial` reached `num_reg_frames=117`
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` still reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260518T2252Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T2252Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260518T2252Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260518T2252Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260518T2252Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260518T2252Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260518T2252Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260518T2252Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260518T2252Z.log`
  - `logs/cvhr-parallel/evidence/runner-status-20260518T2252Z.json`

## 2026-05-18T23:12Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `ceeab743d3b8d85c7db02290f70cab0023967885` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l03-1779145861`, `md1-viscell-full-l02-1779143476`, `md1-shrunk-prodspine-sfm-1779128752`, `cvhr-mtc-20260518T1729Z-sfm`
  - in-progress training jobs: `0`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest observed mapper progress: `chunk_02_mapper_initial` reached `num_reg_frames=185`
  - `chunk_02_mapper_initial` then logged `Keeping successful reconstruction` and started `model_converter`
  - nonfatal COLMAP dense Cholesky linear-solver warnings appeared during bundle adjustment, followed by successful reconstruction; no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` still reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260518T2312Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T2312Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260518T2312Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260518T2312Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260518T2312Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260518T2312Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260518T2312Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260518T2312Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260518T2312Z.log`
  - `logs/cvhr-parallel/evidence/runner-status-20260518T2312Z.json`

## 2026-05-18T23:32Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `cb8e9cc2c8ee19d2c108e0b418c302e53dd91e89` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l04-1779146968`, `md1-viscell-full-l03-1779145861`, `md1-shrunk-prodspine-sfm-1779128752`, `cvhr-mtc-20260518T1729Z-sfm`
  - in-progress training jobs: `0`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest observed stage: `chunk_03_spatial_matcher_recovery`
  - latest observed matching progress: processed `187/187` images and added `682` verified image pairs
  - `vocab_tree_builder` rejected `--max_num_images`, then the runner retried with older COLMAP-compatible flags and continued building the vocab tree
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260518T2332Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T2332Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260518T2332Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260518T2332Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260518T2332Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260518T2332Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260518T2332Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260518T2332Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260518T2332Z.log`
  - `logs/cvhr-parallel/evidence/runner-status-20260518T2332Z.json`

## 2026-05-18T23:52Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `346652bf511f97d516ed51842a9761f5101fbc87` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l05-1779147527`, `md1-viscell-full-l04-1779146968`, `md1-shrunk-prodspine-sfm-1779128752`, `cvhr-mtc-20260518T1729Z-sfm`
  - in-progress training jobs: `0`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`
  - latest observed log line: `vocab_tree_builder` loaded `1893703` descriptors and started building the visual-word index
  - `vocab_tree_builder` had already retried after rejecting `--max_num_images`; the fallback path continued with older COLMAP-compatible flags
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260518T2352Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260518T2352Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260518T2352Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260518T2352Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260518T2352Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260518T2352Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260518T2352Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260518T2352Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260518T2352Z.log`
  - `logs/cvhr-parallel/evidence/runner-status-20260518T2352Z.json`

## 2026-05-19T00:12Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `7b4e69de93dbf66f31ca546d3a011c18d08e34e6` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l05-1779147527`, `md1-viscell-full-l04-1779146968`, `md1-shrunk-prodspine-sfm-1779128752`, `cvhr-mtc-20260518T1729Z-sfm`
  - in-progress training jobs: `0`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest CloudWatch event timestamp remains `2026-05-18T23:31:41Z`
  - latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`
  - latest observed log line: `vocab_tree_builder` loaded `1893703` descriptors and started building the visual-word index
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260519T0012Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0012Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260519T0012Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260519T0012Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260519T0012Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0012Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260519T0012Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0012Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0012Z.log`
  - `logs/cvhr-parallel/evidence/runner-status-20260519T0012Z.json`

## 2026-05-19T00:39Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `40655411227f6cd939b10f64f3d0cc7139c2e29c` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l06-1779150311`, `md1-viscell-full-l05-1779147527`, `cvhr-mtc-20260518T1729Z-sfm`
  - external training jobs observed and left untouched: `md1-shrunk-prodspine-wlight-202605190027-3dgs`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest CloudWatch event timestamp remains `2026-05-18T23:31:41Z`
  - latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`
  - latest observed log line: `vocab_tree_builder` loaded `1893703` descriptors and started building the visual-word index
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260519T0039Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0039Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260519T0039Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260519T0039Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260519T0039Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0039Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260519T0039Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0039Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0039Z.log`
  - `logs/cvhr-parallel/evidence/runner-status-20260519T0039Z.json`

## 2026-05-19T00:59Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `d10509949d8f4ccd0a4c325179eb05116e0238ed` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l07-1779151432`, `md1-viscell-full-l06-1779150311`, `cvhr-mtc-20260518T1729Z-sfm`
  - external training jobs observed and left untouched: `md1-shrunk-prodspine-wlight-202605190027-3dgs`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`
  - latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`
  - latest observed log line: `vocab_tree_builder` loaded `1893703` descriptors and started building the visual-word index
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260519T0059Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0059Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260519T0059Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260519T0059Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260519T0059Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0059Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260519T0059Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0059Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0059Z.log`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-json-cvhr-secondary-20260518t2113z-sfm-20260519T0059Z.json`
  - `logs/cvhr-parallel/evidence/runner-status-20260519T0059Z.json`

## 2026-05-19T01:19Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `98be57b03b5f1d1582ba93885cac0a049f94983b` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l07-1779151432`, `cvhr-mtc-20260518T1729Z-sfm`
  - external training jobs observed and left untouched: `md1-shrunk-prodspine-wlight-202605190027-3dgs`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`
  - latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`
  - latest observed log line: `vocab_tree_builder` loaded `1893703` descriptors and started building the visual-word index
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260519T0119Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0119Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260519T0119Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260519T0119Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260519T0119Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0119Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260519T0119Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0119Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0119Z.log`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-json-cvhr-secondary-20260518t2113z-sfm-20260519T0119Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-cvhr-secondary-20260518t2113z-sfm-20260519T0119Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-late-cvhr-secondary-20260518t2113z-sfm-20260519T0119Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-final-cvhr-secondary-20260518t2113z-sfm-20260519T0119Z.json`
  - `logs/cvhr-parallel/evidence/runner-status-20260519T0119Z.json`

## 2026-05-19T01:39Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `db52b3c6d72ea8a1c592ad2a7b1b2da32777d601` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l06r2-1779154798`, `md1-viscell-full-l07-1779151432`, `cvhr-mtc-20260518T1729Z-sfm`
  - external training jobs observed and left untouched: `md1-shrunk-prodspine-wlight-202605190027-3dgs`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest CloudWatch event timestamp remains `2026-05-18T23:31:39Z`
  - latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`
  - latest observed log line: `vocab_tree_builder` loaded `1893703` descriptors and started building the visual-word index
  - nonfatal `--max_num_images` option warning is still the only captured warning, followed by fallback execution
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260519T0139Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0139Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260519T0139Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260519T0139Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260519T0139Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0139Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260519T0139Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0139Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0139Z.log`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-final-cvhr-secondary-20260518t2113z-sfm-20260519T0139Z.json`
  - `logs/cvhr-parallel/evidence/runner-status-20260519T0139Z.json`

## 2026-05-19T02:05Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `228ef7f26ab6870b9da0a75cb87ecef9c3fa60f3` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l08-1779155211`, `md1-viscell-full-l06r2-1779154798`, `cvhr-mtc-20260518T1729Z-sfm`
  - external training jobs observed and left untouched: `md1-shrunk-prodspine-wlight-202605190027-3dgs`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest CloudWatch event timestamp: `2026-05-18T23:31:39.156Z`
  - latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`
  - latest observed log line: `vocab_tree_builder` loaded `1893703` descriptors and started building the visual-word index
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260519T0205Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0205Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260519T0205Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260519T0205Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260519T0205Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0205Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260519T0205Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0205Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-tail-cvhr-secondary-20260518t2113z-sfm-20260519T0205Z.log`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-cvhr-secondary-20260518t2113z-sfm-20260519T0205Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-cvhr-secondary-20260518t2113z-sfm-20260519T0205Z.log`
  - `logs/cvhr-parallel/evidence/runner-status-20260519T0205Z.json`

## 2026-05-19T02:25Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `bf427fd8f1fa7dabe062e2a6e26f730fa5a74bcd` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l08-1779155211`, `md1-viscell-full-l06r2-1779154798`, `cvhr-mtc-20260518T1729Z-sfm`
  - external training jobs observed and left untouched: `md1-shrunk-prodspine-wlight-202605190027-3dgs`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest CloudWatch event timestamp: `2026-05-18T23:31:39.156Z`
  - latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`
  - latest observed log line: `vocab_tree_builder` loaded `1893703` descriptors and started building the visual-word index
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260519T0225Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0225Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260519T0225Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260519T0225Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260519T0225Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0225Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260519T0225Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0225Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-final-cvhr-secondary-20260518t2113z-sfm-20260519T0225Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-final-cvhr-secondary-20260518t2113z-sfm-20260519T0225Z.log`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-last-cvhr-secondary-20260518t2113z-sfm-20260519T0225Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-last-cvhr-secondary-20260518t2113z-sfm-20260519T0225Z.log`
  - `logs/cvhr-parallel/evidence/runner-status-20260519T0225Z.json`

## 2026-05-19T02:45Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `58c0ac99c18d4147a10ecd91969fdf60da74314d` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l10-1779158398`, `md1-viscell-full-l09-1779157902`, `cvhr-mtc-20260518T1729Z-sfm`
  - external training jobs observed and left untouched: `md1-shrunk-prodspine-wlight-202605190027-3dgs`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest CloudWatch event timestamp: `2026-05-18T23:31:39.156Z`
  - latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`
  - latest observed log line: `vocab_tree_builder` loaded `1893703` descriptors and started building the visual-word index
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260519T0245Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0245Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260519T0245Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260519T0245Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260519T0245Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0245Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260519T0245Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0245Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-last-cvhr-secondary-20260518t2113z-sfm-20260519T0245Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-last-cvhr-secondary-20260518t2113z-sfm-20260519T0245Z.log`
  - `logs/cvhr-parallel/evidence/runner-status-20260519T0245Z.json`

## 2026-05-19T03:05Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `8eff5cbd6b33eb9fef96a23fea08b215169e500e` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l10-1779158398`, `md1-viscell-full-l09-1779157902`, `cvhr-mtc-20260518T1729Z-sfm`
  - external training jobs observed: `0`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest CloudWatch event timestamp: `2026-05-18T23:31:39.156Z`
  - latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`
  - latest observed log line: `vocab_tree_builder` loaded `1893703` descriptors and started building the visual-word index
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260519T0305Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0305Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260519T0305Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260519T0305Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260519T0305Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0305Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260519T0305Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0305Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-last-cvhr-secondary-20260518t2113z-sfm-20260519T0305Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-last-cvhr-secondary-20260518t2113z-sfm-20260519T0305Z.log`
  - `logs/cvhr-parallel/evidence/runner-status-20260519T0305Z.json`

## 2026-05-19T03:25Z Heartbeat Poll

- Branch/head/status:
  - branch: `agent-73910482-cvhr-parallel-splat`
  - head: `e9b11311486c94b15491e2ae78bb14070f13009e` (`[skip ci]` ledger commit)
  - status before this poll: clean
  - last meaningful exact-head workflow remains `CDK Deploy` run `26060892234` for code head `0b60d8bf9e7e4355bd46001dcd61387b327a8e5a`, conclusion `success`
- AWS identity:
  - account: `975050048887`
  - ARN: `arn:aws:iam::975050048887:root`
- Active SageMaker / Step Functions:
  - secondary SfM: `cvhr-secondary-20260518t2113z-sfm` -> `InProgress`
  - external processing jobs observed and left untouched: `md1-viscell-full-l11-1779161085`, `cvhr-mtc-20260518T1729Z-sfm`
  - external training jobs observed: `0`
  - running `SpaceportMLPipeline-staging` Step Functions executions: `0`
- Secondary SfM progress:
  - CloudWatch stream: `cvhr-secondary-20260518t2113z-sfm/algo-1-1779139231`
  - latest CloudWatch event timestamp: `2026-05-18T23:31:39.156Z`
  - latest observed stage remains `chunk_03_spatial_matcher_recovery` / `vocab_tree_builder`
  - latest observed log line: `vocab_tree_builder` loaded `1893703` descriptors and started building the visual-word index
  - no SageMaker failure, OOM, or timeout visible
- S3 output:
  - `s3://spaceport-ml-processing-staging/manual-validations/cvhr-secondary-20260518t2113z/colmap`
  - `Total Objects: 0`, expected before `S3UploadMode=EndOfJob`
- State update:
  - `logs/cvhr-parallel/cv-hr-state.json` reports `status=sfm_running`, `sfm_status=InProgress`, `last_action=sfm_running`
- Evidence:
  - `logs/cvhr-parallel/evidence/aws-sts-20260519T0325Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-describe-cvhr-secondary-20260518t2113z-sfm-20260519T0325Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-processing-inprogress-20260519T0325Z.json`
  - `logs/cvhr-parallel/evidence/sagemaker-training-inprogress-20260519T0325Z.json`
  - `logs/cvhr-parallel/evidence/stepfunctions-running-20260519T0325Z.json`
  - `logs/cvhr-parallel/evidence/s3-colmap-cvhr-secondary-20260518t2113z-20260519T0325Z.txt`
  - `logs/cvhr-parallel/evidence/gh-runs-agent-73910482-20260519T0325Z.json`
  - `logs/cvhr-parallel/evidence/logstreams-cvhr-secondary-20260518t2113z-sfm-20260519T0325Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-last-cvhr-secondary-20260518t2113z-sfm-20260519T0325Z.json`
  - `logs/cvhr-parallel/evidence/cloudwatch-filter-last-cvhr-secondary-20260518t2113z-sfm-20260519T0325Z.log`
  - `logs/cvhr-parallel/evidence/runner-status-20260519T0325Z.json`
