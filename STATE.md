# CV-HR Parallel Splat State

updated: 2026-05-18T21:14:00Z
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
