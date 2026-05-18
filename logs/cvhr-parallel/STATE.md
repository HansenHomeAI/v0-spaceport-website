# CV-HR Parallel Splat Ledger

updated: 2026-05-18T21:14:00Z
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
- No secondary SageMaker job has been launched yet.
