# MD1 Baseline E2E State

updated: 2026-05-14T12:47:11-0600
branch: agent-113647-md1-baseline-e2e
base: origin/development @ b2b451ae6dc46a25c7547162b6f8d037437f2950
repo: HansenHomeAI/v0-spaceport-website

## Goal

Produce a development-based MD1 baseline with:

- an end-to-end MD1 pipeline run from the canonical MD1 image zip
- gated SfM, 3DGS, compression, and viewer verification
- a functioning MD1 viewer route in this worktree
- exact AWS job names, S3 outputs, screenshots, and final URL proof

## Canonical Inputs

- MD1 input zip: `s3://spaceport-uploads/1775750905123-vg76vr-md1-dji-images.zip`
- Existing validated SfM reference: `s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap`
- Existing validated V18 LOD viewer manifest: `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-r5-v18-splattransform-lod-nosingle-public-1777575472/supersplat_bundle/lod-meta.json`

## Current AWS State

- Account: `975050048887`
- Development ML stack: `SpaceportMLPipelineStagingStack`
- Development ML bucket: `spaceport-ml-processing-staging`
- Active external canary at setup: `md1-sample5-cpu-r8-1778692401`; still `InProgress` with `TrainingTimeInSeconds=1938` at 2026-05-13T11:47:00-06:00.
- That canary is owned by the separate SFM reality-check lineage (`CODE_HEAD=e0ed962f...`) and must not be stopped or counted as this run.
- Automation correction: `md1-baseline-e2e-monitor` is now a `heartbeat` automation targeting this thread (`019e2268-9fed-7593-9318-a4e8d1045849`) instead of a standalone `cron`, so follow-up monitor runs should continue here rather than opening new chat cards.
- Branch preview uses shared staging ML outputs from `SpaceportMLPipelineStagingStack`; Pages output resolution now allows that fallback stack when it is in `UPDATE_ROLLBACK_COMPLETE` but still serving required outputs.

## Completed In This Branch

- Created isolated worktree branch `agent-113647-md1-baseline-e2e` from `origin/development`.
- Added MD1 viewer route `/md1-viewer`, SfM point cloud route `/sfm-output-viewer`, LOD SuperSplat runtime assets, S3/SOGS proxy support, and `web/scripts/test-md1-production-viewer.mjs`.
- Updated compressor path to the current `@playcanvas/splat-transform` SuperSplat bundle implementation with skybox manifest support.
- Verified canonical MD1 input object exists: `ContentLength=12827403903`, ETag `"2069941b24d23c98190798ffa14c5f86-1530"`.
- Verified V18 LOD manifest exists: `ContentLength=271219`, ETag `"42d56f638f962cada54441f0b8144e25"`.
- Verified `spaceport_bundle.json` exists: `ContentLength=161`, ETag `"d63cbe95b7295d3ff13911cd680d8c4f"`.
- `npm run build` passed for the web app; route table includes `/md1-viewer` and `/sfm-output-viewer`.
- `MD1_VIEWER_URL=http://127.0.0.1:3031 node scripts/test-md1-production-viewer.mjs` passed.
- Viewer proof JSON: `logs/md1-production-viewer-results.json`.
- Desktop screenshot: `logs/md1-production-viewer-desktop.png`.
- Mobile screenshot: `logs/md1-production-viewer-mobile.png`.
- `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` passed.
- `python3 -m py_compile ...` passed for compressor, SfM, and existing 3DGS entrypoints.
- `git diff --check` passed.
- First branch Pages deploy failed at CloudFormation output resolution because the fallback staging ML stack was `UPDATE_ROLLBACK_COMPLETE`; patched the Pages workflow gate and pushed a rerun fix.
- Full MD1 baseline run launched once:
  - execution: `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260513115645`
  - job id/name: `md1-baseline-e2e-20260513115645`
  - payload: `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-payload.json`
  - start proof: `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-start.json`
  - current stage at launch verification: `WaitForSfM`; SageMaker processing job `md1-baseline-e2e-20260513115645-sfm` is `InProgress` on `ml.g4dn.xlarge`.
- Public branch preview is live:
  - alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev/md1-viewer`
  - hash: `https://830ad77b.v0-spaceport-website-preview2.pages.dev/md1-viewer`
  - public Playwright smoke passed against the alias; desktop first frame `90.4ms`, mobile first frame `130.3ms`, LOD levels `4`, chunk files `44`.

## Gated Execution Plan

1. Verify the MD1 viewer locally against the existing validated V18 LOD bundle.
2. Run static/local checks for the viewer branch.
3. Wait for AWS to be idle except for explicitly external canaries.
4. Launch the smallest development-based proof that can verify SfM-to-3DGS handoff without duplicating stale jobs.
5. If the handoff is clean, launch the bounded full MD1 baseline E2E run once.
6. Monitor each stage for OOM, timeout, missing artifact, and stale output handoff failures.
7. Patch this branch only for failures proven by the current run, rebuild/relaunch the smallest failed stage, then continue.
8. Publish or serve the final compressed bundle through the MD1 viewer and capture desktop/mobile visual proof.

## Cost Guardrails

- Do not launch duplicate full MD1 jobs.
- Do not stop jobs owned by another active automation unless they are confirmed orphaned and ineligible.
- Prefer no-spend/static checks and existing SfM references before full retraining.
- Use one canonical full run after preflight, then bounded retries for isolated failed stages only.

## Live Monitor Updates

### 2026-05-13T12:45:30-06:00

- Git: `agent-113647-md1-baseline-e2e` clean (`git status -sb` shows no changes).
- AWS identity: `aws sts get-caller-identity` -> `Account=975050048887`.
- Step Functions execution: `RUNNING`
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260513115645`
- Active SageMaker jobs (no duplicate MD1 E2E runs launched):
  - Processing (ours): `md1-baseline-e2e-20260513115645-sfm` -> `InProgress` on `ml.g4dn.xlarge`
  - Training (external, not ours): `md1-sample5-cachectl-r10-1778696805` -> `InProgress` (leave running)
- SfM progress proof (CloudWatch tail, last 30m, last 200 lines):
  - `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-sfm-cloudwatch-tail-20260513T184500Z.log`
  - Latest observed progress: `Processed file [1061/3076]` at `2026-05-13T18:46:21Z`
  - Short poll log: `logs/md1-baseline-e2e/monitor-md1-baseline-e2e-20260513115645-20260513T184704Z.txt` (1077 -> 1136 / 3076 over ~2m)

### 2026-05-13T12:56:00-06:00

- CI: `CDK Deploy` run `25819707178` -> `success` after pushing `ec9926be` (log-only update; no workflow changes).
- SfM progress (from `logs/md1-baseline-e2e/monitor-md1-baseline-e2e-20260513115645-20260513T184704Z.txt`):
  - `Processed file [1136/3076]` at `2026-05-13T18:49:04Z` (still `InProgress`).
- Expected S3 outputs are still empty until job end (`S3UploadMode=EndOfJob`):
  - `aws s3 ls s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260513115645/ --summarize` -> `Total Objects: 0`

### 2026-05-13T13:52:21-06:00

- Git: `agent-113647-md1-baseline-e2e` clean on `e4d77b1b` (`git status -sb`).
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
- Step Functions execution: still `RUNNING`
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260513115645`
- Active SageMaker jobs (no duplicate MD1 E2E runs launched):
  - Processing (ours): `md1-baseline-e2e-20260513115645-sfm` -> `InProgress`
  - Training (external; do not stop): `md1-sample5-ds1000-r12-1778700562` -> `InProgress`
  - Training (external; do not stop): `md1-sample40-ds1000-r13-1778701888` -> `InProgress`
- SfM progress proof (CloudWatch tail, last 10m):
  - tail json: `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-sfm-cloudwatch-tail-20260513T195138Z.json`
  - tail log: `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-sfm-cloudwatch-tail-20260513T195138Z.log`
  - Latest observed progress: `Processed file [2828/3076]` at `2026-05-13T19:51:26Z`
- S3 outputs still empty (expected until job end): `Total Objects: 0` under `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260513115645/`
- No-spend regression check: `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` -> `OK`

## Latest Monitor Snapshot (2026-05-13T13:52:21-06:00)

### Repo / local (no-spend)

- `git status -sb` clean on `agent-113647-md1-baseline-e2e` @ `e4d77b1b`
- `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` OK

### AWS identity

- `aws sts get-caller-identity`: Account `975050048887` (region `us-west-2`)

### Canonical E2E execution (do not duplicate)

- Step Functions execution is still `RUNNING`:
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260513115645`
- Current state remains `WaitForSfM` / `WaitForSfMCompletion` (polling loop)

### SageMaker jobs (active)

- This run SfM processing job is still `InProgress`:
  - `md1-baseline-e2e-20260513115645-sfm` (`ml.g4dn.xlarge`)
  - output target: `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260513115645/`
- External training jobs observed (do not stop; not owned by this automation):
  - `md1-sample5-ds1000-r12-1778700562` is `InProgress`
  - `md1-sample40-ds1000-r13-1778701888` is `InProgress`

### SfM CloudWatch progress proof

- Log stream: `/aws/sagemaker/ProcessingJobs` / `md1-baseline-e2e-20260513115645-sfm/algo-1-1778695048`
- Tail captured (latest):
  - `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-sfm-cloudwatch-tail-20260513T195138Z.json`
- Most recent observed progress (from the captured tail):
  - `COLMAP[feature_extractor] ... Processed file [2828/3076]` (feature extraction ongoing)

### 2026-05-13T15:01:20-06:00

- Git: on `agent-113647-md1-baseline-e2e` @ `2806e54c` (logs updated locally; no new AWS runs launched).
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
- Step Functions execution: still `RUNNING`
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260513115645`
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260513115645-sfm` -> `InProgress` (`S3UploadMode=EndOfJob`)
  - Output prefix: `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260513115645/` (still empty)
- SageMaker (external; do not stop; not owned by this automation):
  - `md1-sample5-ds1000-r12-1778700562` -> `Stopped` (`MaxRuntimeExceeded`)
  - `md1-sample40-ds1000-r13-1778701888` -> `Completed`
  - `md1-sample40-ds1000-r14-1778705722` -> `InProgress` (`Downloading`)
- Snapshot:
  - `logs/md1-baseline-e2e/monitor-md1-baseline-e2e-20260513115645-20260513T210120Z.txt`
- SfM CloudWatch tail (mapping stage; latest 20m):
  - `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-sfm-cloudwatch-tail-20260513T205956Z.log`
  - Most recent observed line: `COLMAP[mapper_spatial_sequential_only] ... Registering image #1369` at `2026-05-13T20:59:56Z`
- Follow-up poll: `2026-05-13T15:05:51-06:00` -> SfM still `InProgress`, Step Functions still `RUNNING`, S3 outputs still empty.

### 2026-05-13T16:00:45-06:00

- Git: on `agent-113647-md1-baseline-e2e` @ `1e8301b1` (monitor artifacts captured locally; no new AWS runs launched).
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
- Step Functions execution: still `RUNNING`
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260513115645`
  - Latest history snapshot (reverse order): `logs/md1-baseline-e2e/stepfunctions-execution-md1-baseline-e2e-20260513115645-history-reverse-20260513T220011Z.json`
  - Latest state observed: `WaitForSfM` / `WaitForSfMCompletion` at `2026-05-13T15:59:40-06:00`
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260513115645-sfm` -> `InProgress` (`S3UploadMode=EndOfJob`)
  - Output prefix: `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260513115645/` -> `Total Objects: 0`
- SageMaker (external; do not stop; not owned by this automation):
  - Training job observed: `md1-sample40-ds1000-r15-1778709400` -> `InProgress` (`Downloading`)
- SfM CloudWatch tail (latest ~30m):
  - tail json: `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-sfm-cloudwatch-tail-20260513T215950Z.json`
  - tail txt: `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-sfm-cloudwatch-tail-20260513T215950Z.txt`
  - Most recent observed transition: `Retriangulation and Global bundle adjustment` at `2026-05-13T21:55:00Z`, then `HEARTBEAT idle=240s` at `2026-05-13T21:59:02Z`
- Snapshot:
  - `logs/md1-baseline-e2e/monitor-md1-baseline-e2e-20260513115645-20260513T220031Z.txt`
- No-spend regression check: `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` -> `OK`

### 2026-05-13T16:04:30-06:00

- Git: committed + pushed monitor snapshot `4d8b3997` (no code-path changes; logs/state only).
- CI:
  - `CDK Deploy` run `25829028805` -> `success` (head `4d8b3997`)
  - No new `Deploy Next.js to Cloudflare Pages` run was triggered by this logs-only commit; latest Pages run on this branch remains `25816779815` -> `success` (workflow_dispatch)

### 2026-05-13T16:12:30-06:00

- Git: on `agent-113647-md1-baseline-e2e` @ `81cb1205` (latest push was CI-log only).
- CI:
  - `CDK Deploy` run `25829233748` -> `success` (head `81cb1205`)
- Step Functions execution: still `RUNNING`
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260513115645`
  - Latest history snapshot (reverse order): `logs/md1-baseline-e2e/stepfunctions-execution-md1-baseline-e2e-20260513115645-history-reverse-20260513T221209Z.json`
  - Latest state observed: `WaitForSfM` at `2026-05-13T16:11:43-06:00`
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260513115645-sfm` -> `InProgress`
  - Output prefix: `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260513115645/` -> `Total Objects: 0` (still empty; `S3UploadMode=EndOfJob`)
- SfM CloudWatch tail (latest ~30m):
  - tail json: `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-sfm-cloudwatch-tail-20260513T221150Z.json`
  - tail txt: `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-sfm-cloudwatch-tail-20260513T221150Z.txt`
  - Most recent observed progress: mapper remains in `Global bundle adjustment` with heartbeats increasing to `idle=960s` at `2026-05-13T22:11:02Z`
- Snapshot:
  - `logs/md1-baseline-e2e/monitor-md1-baseline-e2e-20260513115645-20260513T221209Z.txt`

### 2026-05-13T16:16:30-06:00

- Git: pushed monitor progress commit `6691d8c3`.
- CI:
  - `CDK Deploy` run `25829447798` -> `success` (head `6691d8c3`)

### 2026-05-13T17:05:58-06:00

- Git: on `agent-113647-md1-baseline-e2e` @ `d5ad81b9957d46920f563eea817dba26431901f3` (no new commits; logs captured locally).
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
- Step Functions execution: still `RUNNING`
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260513115645`
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-20260513T230503Z.json`
  - history snapshot (reverse order): `logs/md1-baseline-e2e/stepfunctions-history-reverse-20260513T230133Z.json`
  - latest observed state: `WaitForSfM` (still waiting on SfM completion)
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260513115645-sfm` -> `InProgress` (`S3UploadMode=EndOfJob`)
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260513115645-sfm-20260513T230503Z.json`
  - Output prefix: `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260513115645/` -> `Total Objects: 0` (still empty)
  - S3 listing snapshot: `logs/md1-baseline-e2e/s3-colmap-md1-baseline-e2e-20260513115645-20260513T230527Z.txt`

### 2026-05-13T20:08:06-06:00

- Git: on `agent-113647-md1-baseline-e2e` @ `edf0fe0d` (dirty; infra patch pending commit).
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
- Step Functions execution: `TIMED_OUT` at `2026-05-13T19:56:49-06:00` (8h execution timeout tripped).
  - `aws stepfunctions describe-execution ...` snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-20260514T020707Z.json`
  - history snapshot: `logs/md1-baseline-e2e/stepfunctions-history-reverse-20260514T020707Z.json`
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260513115645-sfm` -> `InProgress` (`MaxRuntimeInSeconds=86400`, `S3UploadMode=EndOfJob`)
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260513115645-sfm-20260514T020707Z.json`
  - Output prefix listing snapshot: `logs/md1-baseline-e2e/s3api-colmap-md1-baseline-e2e-20260513115645-20260514T020707Z.json` (still empty)
- SageMaker (external; do not stop; not owned by this automation):
  - Training jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-training-inprogress-20260514T020707Z.json`
  - Processing jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-processing-inprogress-20260514T020707Z.json`
- SfM CloudWatch tail (~last 30m):
  - `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-sfm-cloudwatch-tail-20260514T020718Z.txt`
  - most recent observed progress: only `HEARTBEAT` lines with `idle` increasing to `4200s` at `2026-05-14T02:06:59Z`
- Fix (proven by this run): bump Step Functions execution timeout from `8h` -> `24h` (prevents orchestration timeout while SfM is still running).
  - IaC patch committed: `timeout=Duration.hours(24)` in `infrastructure/spaceport_cdk/spaceport_cdk/ml_pipeline_stack.py` (but CloudFormation `SpaceportMLPipelineStagingStack` is currently `UPDATE_ROLLBACK_COMPLETE`, so CDK deploy does not update this stack).
  - Live workaround applied (authoritative until the stack can be recovered):
    - definition patched via `aws stepfunctions update-state-machine ...` to set top-level `TimeoutSeconds=86400`
    - patched definition: `logs/md1-baseline-e2e/stepfunctions-definition-SpaceportMLPipeline-staging-20260514T021842Z.json`
    - update response: `logs/md1-baseline-e2e/stepfunctions-update-state-machine-20260514T021901Z.json`
    - verification: `aws stepfunctions describe-state-machine ... --query definition` now returns `TimeoutSeconds=86400`
- SfM CloudWatch tail (latest):
  - Log stream: `/aws/sagemaker/ProcessingJobs` / `md1-baseline-e2e-20260513115645-sfm/algo-1-1778695048`
  - Tail json: `logs/md1-baseline-e2e/cloudwatch-tail-md1-baseline-e2e-20260513115645-sfm-20260513T230503Z.json`
  - Most recent observed lines: `COLMAP[mapper_spatial_sequential_only] HEARTBEAT elapsed=10001s idle=4140s` (mapper still alive; long idle suggests global BA/cleanup phase)
- SageMaker (external; do not stop; not owned by this automation):
  - Training job observed: `md1-sample120-ds1000-r16-1778713144` -> `InProgress` (`Downloading`)
  - snapshot: `logs/md1-baseline-e2e/sagemaker-training-inprogress-20260513T230204Z.json`

### 2026-05-13T18:14:17-06:00

- Git: on `agent-113647-md1-baseline-e2e` @ `b6c7ed95` (committed refreshed monitor state; not pushed).
- No-spend static checks:
  - `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` -> `OK`
  - `cd web && npm run build` -> `success` (warnings only; no failures)
  - `cd web && MD1_VIEWER_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev node scripts/test-md1-production-viewer.mjs` -> `passed`
    - results: `logs/md1-production-viewer-results.json`
    - screenshot: `logs/md1-production-viewer-desktop.png`
    - screenshot: `logs/md1-production-viewer-mobile.png`
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
- Step Functions execution: still `RUNNING`
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260513115645`
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-20260514T000206Z.json`
  - history snapshot (reverse order): `logs/md1-baseline-e2e/stepfunctions-history-reverse-20260514T000207Z.json`
  - latest observed state: `WaitForSfM` (wait loop continues)
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260513115645-sfm` -> `InProgress` (`S3UploadMode=EndOfJob`)
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260513115645-sfm-20260514T000207Z.json`
  - Output prefix: `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260513115645/` -> `Total Objects: 0` (still empty; upload at end of job)
  - S3 listing snapshot: `logs/md1-baseline-e2e/s3-colmap-md1-baseline-e2e-20260513115645-20260514T000207Z.txt`
- SfM CloudWatch progress:
  - Stream: `/aws/sagemaker/ProcessingJobs` / `md1-baseline-e2e-20260513115645-sfm/algo-1-1778695048`
  - Non-heartbeat tail: `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-sfm-cloudwatch-tail-non-heartbeat-20260514T000333Z.log`
  - Most recent observed transition: `Retriangulation and Global bundle adjustment` at `2026-05-13T23:19:09Z`
  - Heartbeat tail: `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-sfm-cloudwatch-tail-20260514T000207Z.log`
  - Most recent observed heartbeat: `HEARTBEAT elapsed=13669s idle=2760s` at `2026-05-14T00:05:11Z` (global BA still running; long idle expected but monitor for excessive stalls)
- Snapshot:
  - `logs/md1-baseline-e2e/monitor-md1-baseline-e2e-20260513115645-20260514T000358Z.txt`

### 2026-05-13T19:06:42-0600

- Git: on `agent-113647-md1-baseline-e2e` @ `3278c1fd` (local monitor snapshots captured; not pushed).
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
- Step Functions execution: still `RUNNING`
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260513115645`
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-20260514T010553Z.json`
  - history snapshot (reverse order): `logs/md1-baseline-e2e/stepfunctions-history-reverse-20260514T010553Z.json`
  - latest observed state: `WaitForSfM` (wait loop continues)
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260513115645-sfm` -> `InProgress` (`S3UploadMode=EndOfJob`)
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260513115645-sfm-20260514T010553Z.json`
  - Output prefix: `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260513115645/` -> `Total Objects: 0` (still empty; upload at end of job)
  - S3 listing snapshot: `logs/md1-baseline-e2e/s3-colmap-md1-baseline-e2e-20260513115645-20260514T010553Z.txt`
- SageMaker (active job inventory; do not stop unrelated jobs):
  - processing InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-processing-inprogress-20260514T010553Z.json` (includes this run's SfM job)
  - training InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-training-inprogress-20260514T010553Z.json` (empty at this poll)
- SfM CloudWatch progress:
  - Stream: `/aws/sagemaker/ProcessingJobs` / `md1-baseline-e2e-20260513115645-sfm/algo-1-1778695048`
  - Tail: `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-sfm-cloudwatch-tail-20260514T010553Z.txt`
  - Most recent observed heartbeat: `HEARTBEAT elapsed=17317s idle=540s` at `2026-05-14T01:05:59Z` (still in global BA / retriangulation phase)
- Snapshot:
  - `logs/md1-baseline-e2e/monitor-md1-baseline-e2e-20260513115645-20260514T010553Z.txt`

### 2026-05-13T21:12:50-0600

- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
- Step Functions execution (this run): `TIMED_OUT`
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260513115645`
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-20260514T031250Z.json`
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260513115645-sfm` -> `Failed` (`AlgorithmError`, exit code 1)
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260513115645-sfm-20260514T031250Z.json`
  - Root cause (from CloudWatch tail): internal mapper timeout: `RuntimeError: mapper_spatial_sequential_only timed out after 21600s`
    - streams: `logs/md1-baseline-e2e/cloudwatch-logstreams-md1-baseline-e2e-20260513115645-sfm-20260514T000000Z.json`
    - tail json: `logs/md1-baseline-e2e/cloudwatch-tail-md1-baseline-e2e-20260513115645-sfm-20260514T000000Z.json`
    - tail txt: `logs/md1-baseline-e2e/md1-baseline-e2e-20260513115645-sfm-cloudwatch-tail-20260514T000000Z.txt`
- SageMaker (external; do not stop; not owned by this automation):
  - Training jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-training-inprogress-20260514T031250Z.json`
  - Processing jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-processing-inprogress-20260514T031250Z.json`
- Fix queued (proven by this run): raise SfM container timeout environment for future runs:
  - set `COLMAP_MONOLITHIC_MAPPER_TIMEOUT_SECONDS=43200` and `COLMAP_BUNDLE_ADJUSTER_TIMEOUT_SECONDS=43200` on the SfM Processing Job in `infrastructure/spaceport_cdk/spaceport_cdk/ml_pipeline_stack.py`
  - next: commit + push + wait for `CDK Deploy` green, then relaunch a single SfM-only execution (`pipelineStep=sfm`) with a new `jobName`.

### 2026-05-13T21:25:52-0600

- Git: on `agent-113647-md1-baseline-e2e` @ `5b1efa21` (pushed).
- CI:
  - `CDK Deploy` run `25839478938` -> `success`
  - `Deploy Next.js to Cloudflare Pages` run `25839635220` -> `success`
  - Preview URLs proof: `logs/md1-baseline-e2e/pages-preview-urls-25839635220.txt`
- Step Functions (workaround; required because CF stack may not be updatable):
  - Patched definition to include SfM env timeouts:
    - definition: `logs/md1-baseline-e2e/stepfunctions-definition-SpaceportMLPipeline-staging-20260514T032351Z.json`
    - update response: `logs/md1-baseline-e2e/stepfunctions-update-state-machine-20260514T032351Z.json`
    - verification: `logs/md1-baseline-e2e/stepfunctions-describe-state-machine-20260514T032351Z.json` (definition contains both timeout env keys)
- New canonical MD1 baseline execution launched (single retry after proven SfM timeout):
  - execution: `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260514032448`
  - job id/name: `md1-baseline-e2e-20260514032448`
  - payload: `logs/md1-baseline-e2e/md1-baseline-e2e-20260514032448-payload.json`
  - start proof: `logs/md1-baseline-e2e/md1-baseline-e2e-20260514032448-start.json`
  - current stage: `SfMProcessingJob` / `WaitForSfM` (`StepFunctions=RUNNING`)
  - SageMaker job: `md1-baseline-e2e-20260514032448-sfm` -> `InProgress` (env includes `COLMAP_*_TIMEOUT_SECONDS=43200`)
  - monitor snapshot: `logs/md1-baseline-e2e/monitor-md1-baseline-e2e-20260514032448-20260514T032552Z.txt`

### 2026-05-13T22:19:26-0600

- Git: still on `agent-113647-md1-baseline-e2e` @ `1c9b3cf2` (no code changes in this poll; new logs only).
- No-spend static checks:
  - `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` -> `OK`
  - `cd web && npx next lint` -> `0` (warnings only)
  - `cd web && npm run build` -> `success` (warnings only)
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
- Step Functions execution: still `RUNNING`
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260514032448`
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-md1-baseline-e2e-20260514032448-20260514T041906Z.json`
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260514032448-sfm` -> `InProgress`
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260514032448-sfm-20260514T041906Z.json`
  - Output prefix: `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260514032448/` -> `Total Objects: 0` (still `S3UploadMode=EndOfJob`)
  - S3 listing snapshot: `logs/md1-baseline-e2e/s3-colmap-md1-baseline-e2e-20260514032448-20260514T041906Z.txt`
- SageMaker (active job inventory; do not stop unrelated jobs):
  - `aws sagemaker list-processing-jobs --status-equals InProgress --query 'ProcessingJobSummaries[].ProcessingJobName'` -> only `md1-baseline-e2e-20260514032448-sfm`
  - `aws sagemaker list-training-jobs --status-equals InProgress --query 'TrainingJobSummaries[].TrainingJobName'` -> empty
- SfM CloudWatch progress:
  - Stream: `/aws/sagemaker/ProcessingJobs` / `md1-baseline-e2e-20260514032448-sfm/algo-1-1778729134`
  - Tail json: `logs/md1-baseline-e2e/cloudwatch-tail-md1-baseline-e2e-20260514032448-sfm-20260514T041906Z.json`
  - Tail txt: `logs/md1-baseline-e2e/md1-baseline-e2e-20260514032448-sfm-cloudwatch-tail-20260514T041906Z.txt`
  - Most recent parsed progress: `processed=825/3076` (feature extraction still underway)
- Snapshot:
  - `logs/md1-baseline-e2e/monitor-md1-baseline-e2e-20260514032448-20260514T041906Z.txt`

### 2026-05-13T23:20:18-0600

- Git: on `agent-113647-md1-baseline-e2e` @ `31f5fb37` (poll evidence commit; working tree clean).
- No-spend static checks:
  - `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` -> `OK`
  - `cd web && npx next lint` -> `0` (warnings only)
  - `cd web && npm run build` -> `success` (warnings only)
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
- Step Functions:
  - state machine arn: `arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging`
  - execution: `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260514032448` -> still `RUNNING` (latest state `WaitForSfM`)
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-md1-baseline-e2e-20260514032448-20260514T051731Z.json`
  - history snapshot (reverse): `logs/md1-baseline-e2e/stepfunctions-history-reverse-md1-baseline-e2e-20260514032448-20260514T051731Z.json`
  - list snapshot (RUNNING): `logs/md1-baseline-e2e/stepfunctions-list-running-20260514T051731Z.json`
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260514032448-sfm` -> `InProgress` (instance `ml.g4dn.xlarge`, volume `100GB`, `MaxRuntimeInSeconds=86400`)
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260514032448-sfm-20260514T032511Z.json`
  - Output prefix (S3UploadMode=EndOfJob): `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260514032448/` -> still empty
  - S3 listing snapshot: `logs/md1-baseline-e2e/s3-colmap-md1-baseline-e2e-20260514032448-20260514T051731Z.txt`
- SageMaker (other in-progress; do not stop unless proven orphaned):
  - Training job observed: `md1-sample120-ds1500-r21-1778733520` -> `InProgress` (`Training`)
- SfM CloudWatch progress:
  - Stream: `/aws/sagemaker/ProcessingJobs` / `md1-baseline-e2e-20260514032448-sfm/algo-1-1778729134`
  - Streams snapshot: `logs/md1-baseline-e2e/cloudwatch-streams-md1-baseline-e2e-20260514032448-sfm-20260514T051731Z.json`
  - Tail txt: `logs/md1-baseline-e2e/md1-baseline-e2e-20260514032448-sfm-cloudwatch-tail-20260514T051815Z.txt`
  - Most recent parsed progress in that tail: `processed=2691/3076` (feature_extractor) at ~`2026-05-14T05:18:15Z`

### 2026-05-13T23:31:36-0600

- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260514032448-sfm` -> still `InProgress`
- SfM CloudWatch progress:
  - `aws logs tail ... --since 15m | rg 'Processed file [' | tail -n 1` -> `Processed file [3025/3076]` at `2026-05-14T05:31:11Z` (feature_extractor; nearing completion)
  - excerpt: `logs/md1-baseline-e2e/sfm-progress-md1-baseline-e2e-20260514032448-20260514T053130Z.txt`

### 2026-05-14T00:20:20-0600

- Git: on `agent-113647-md1-baseline-e2e` @ `62140158` (working tree clean).
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
- Step Functions execution: still `RUNNING`
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260514032448`
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-md1-baseline-e2e-20260514032448-20260514T061906Z.json`
  - history snapshot (reverse): `logs/md1-baseline-e2e/stepfunctions-history-reverse-md1-baseline-e2e-20260514032448-20260514T061912Z.json`
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260514032448-sfm` -> `InProgress`
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260514032448-sfm-20260514T061917Z.json`
  - Output prefix (S3UploadMode=EndOfJob): `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260514032448/` -> still empty
  - S3 listing snapshot: `logs/md1-baseline-e2e/s3-colmap-md1-baseline-e2e-20260514032448-20260514T061932Z.txt` (empty; `aws s3 ls` returns exit code 1 when prefix has 0 objects)
- SageMaker (active job inventory; do not stop unrelated jobs):
  - Processing jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-processing-inprogress-20260514T061954Z.json`
  - Training jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-training-inprogress-20260514T061954Z.json` (empty)
- SfM CloudWatch progress:
  - Stream: `/aws/sagemaker/ProcessingJobs` / `md1-baseline-e2e-20260514032448-sfm/algo-1-1778729134`
  - Streams snapshot: `logs/md1-baseline-e2e/cloudwatch-streams-md1-baseline-e2e-20260514032448-sfm-20260514T061954Z.json`
  - Progress excerpt (filtered; safe to commit): `logs/md1-baseline-e2e/sfm-progress-md1-baseline-e2e-20260514032448-20260514T062120Z.txt`
  - Most recent observed stage transition: `Retriangulation and Global bundle adjustment` at `2026-05-14T06:18:40Z` (mapper running; feature extraction completed earlier).

### 2026-05-14T01:19:56-0600

- Git: on `agent-113647-md1-baseline-e2e` @ `25e686b1` (working tree clean; no code-path changes).
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
  - snapshot: `logs/md1-baseline-e2e/aws-sts-20260514T071833Z.json`
- Step Functions execution: still `RUNNING`
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260514032448`
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-md1-baseline-e2e-20260514032448-20260514T071833Z.json`
  - history snapshot (reverse): `logs/md1-baseline-e2e/stepfunctions-history-reverse-md1-baseline-e2e-20260514032448-20260514T071833Z.json`
  - latest state observed in history: `WaitForSfMCompletion` (poll loop calling `describeProcessingJob`)
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260514032448-sfm` -> `InProgress`
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260514032448-sfm-20260514T071833Z.json`
  - Output prefix (S3UploadMode=EndOfJob): `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260514032448/` -> still empty
  - S3 listing snapshot: `logs/md1-baseline-e2e/s3-colmap-md1-baseline-e2e-20260514032448-20260514T071833Z.txt`
- SageMaker (active job inventory; do not stop unrelated jobs):
  - Processing jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-processing-inprogress-20260514T071833Z.json` (only the SfM job)
  - Training jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-training-inprogress-20260514T071833Z.json` (external job observed)
- SfM CloudWatch progress (most recent ~45m; mapper still active):
  - Stream snapshot: `logs/md1-baseline-e2e/cloudwatch-streams-md1-baseline-e2e-20260514032448-sfm-20260514T071956Z.json`
  - Tail snapshot: `logs/md1-baseline-e2e/cloudwatch-tail-md1-baseline-e2e-20260514032448-sfm-20260514T071956Z.log`
  - Progress excerpt (filtered; safe to commit): `logs/md1-baseline-e2e/sfm-progress-md1-baseline-e2e-20260514032448-20260514T071956Z.txt`
  - Most recent observed activity in excerpt: `Registering image` lines through `num_reg_frames=939` at `2026-05-14T07:19:53Z`, with intervening `HEARTBEAT` lines (no stall signal).

### 2026-05-14T02:31:42-0600

- Git: on `agent-113647-md1-baseline-e2e` @ `9e192d9c` (working tree clean; no code-path changes).
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
  - snapshot: `logs/md1-baseline-e2e/aws-sts-20260514T082946Z.json`
- Step Functions execution: still `RUNNING` (poll loop still waiting on SfM)
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260514032448`
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-md1-baseline-e2e-20260514032448-20260514T082946Z.json`
  - history snapshot (reverse): `logs/md1-baseline-e2e/stepfunctions-history-reverse-md1-baseline-e2e-20260514032448-20260514T082946Z.json`
  - latest state observed in history: `WaitForSfM` at `2026-05-14T02:30:55-0600`
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260514032448-sfm` -> `InProgress` (`MaxRuntimeInSeconds=86400`, `S3UploadMode=EndOfJob`)
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260514032448-sfm-20260514T082946Z.json`
  - Output prefix (S3UploadMode=EndOfJob): `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260514032448/` -> still empty
  - S3 listing snapshot: `logs/md1-baseline-e2e/s3-colmap-md1-baseline-e2e-20260514032448-20260514T082946Z.txt`
- SageMaker (active job inventory; do not stop unrelated jobs):
  - Processing jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-processing-inprogress-20260514T082946Z.json` (only the SfM job)
  - Training jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-training-inprogress-20260514T082946Z.json` (none)
- SfM CloudWatch progress (most recent ~90m; mapper alive in global BA):
  - Stream: `/aws/sagemaker/ProcessingJobs` / `md1-baseline-e2e-20260514032448-sfm/algo-1-1778729134`
  - Streams snapshot: `logs/md1-baseline-e2e/cloudwatch-streams-md1-baseline-e2e-20260514032448-sfm-20260514T083037Z.json`
  - Tail snapshot: `logs/md1-baseline-e2e/cloudwatch-tail-md1-baseline-e2e-20260514032448-sfm-20260514T083037Z.log`
  - Progress excerpt (filtered; safe to commit): `logs/md1-baseline-e2e/sfm-progress-md1-baseline-e2e-20260514032448-20260514T083037Z.txt`
  - Most recent observed activity in excerpt: `Retriangulation and Global bundle adjustment` at `2026-05-14T07:37:41Z`, then `HEARTBEAT ... idle=3120s` at `2026-05-14T08:29:44Z` (no error lines observed).

### 2026-05-14T03:32:15-0600

- Git: on `agent-113647-md1-baseline-e2e` (local poll artifacts captured; not pushed).
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
  - snapshot: `logs/md1-baseline-e2e/aws-sts-20260514T093215Z.json`
- Step Functions execution: still `RUNNING` (poll loop still waiting on SfM)
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260514032448`
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-md1-baseline-e2e-20260514032448-20260514T093215Z.json`
  - history snapshot (reverse): `logs/md1-baseline-e2e/stepfunctions-history-reverse-md1-baseline-e2e-20260514032448-20260514T093215Z.json`
  - latest observed states in history: `WaitForSfMCompletion` -> `WaitForSfM` at `2026-05-14T03:32:07-0600`
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260514032448-sfm` -> `InProgress` (`S3UploadMode=EndOfJob`)
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260514032448-sfm-20260514T093215Z.json`
  - Output prefix (S3UploadMode=EndOfJob): `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260514032448/` -> still empty
  - S3 listing snapshot: `logs/md1-baseline-e2e/s3-colmap-md1-baseline-e2e-20260514032448-20260514T093215Z.txt`
- SageMaker (active job inventory; do not stop unrelated jobs):
  - Processing jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-processing-inprogress-20260514T093215Z.json` (includes unrelated `md1-full-fanout-r23-1778748500-leaf-*`)
  - Training jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-training-inprogress-20260514T093215Z.json` (none)
- SfM CloudWatch progress (recent ~3h; mapper still alive):
  - Streams snapshot: `logs/md1-baseline-e2e/cloudwatch-streams-md1-baseline-e2e-20260514032448-sfm-20260514T093215Z.json`
  - Tail snapshot: `logs/md1-baseline-e2e/cloudwatch-tail-md1-baseline-e2e-20260514032448-sfm-20260514T093215Z.log`
  - Progress excerpt (filtered; safe to commit): `logs/md1-baseline-e2e/sfm-progress-md1-baseline-e2e-20260514032448-20260514T093215Z.txt`
  - Most recent observed activity in excerpt: `Registering image` through `num_reg_frames=1195` at `2026-05-14T09:15:20Z`, then `Retriangulation and Global bundle adjustment` at `2026-05-14T09:15:23Z`, then `HEARTBEAT ... idle=1080s` at `2026-05-14T09:33:25Z` (no error lines observed).

### 2026-05-14T04:34:05-0600

- Git: on `agent-113647-md1-baseline-e2e` (local poll artifacts captured; not pushed).
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
  - snapshot: `logs/md1-baseline-e2e/aws-sts-20260514T103405Z.json`
- Step Functions execution: still `RUNNING` (poll loop still waiting on SfM)
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260514032448`
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-md1-baseline-e2e-20260514032448-20260514T103405Z.json`
  - history snapshot (reverse): `logs/md1-baseline-e2e/stepfunctions-history-reverse-md1-baseline-e2e-20260514032448-20260514T103405Z.json`
  - latest observed state in history: `WaitForSfM` at `2026-05-14T04:33:19-0600`
- SageMaker (this run):
  - Processing job: `md1-baseline-e2e-20260514032448-sfm` -> `InProgress` (`S3UploadMode=EndOfJob`)
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260514032448-sfm-20260514T103405Z.json`
  - Output prefix (S3UploadMode=EndOfJob): `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260514032448/` -> still empty
  - S3 listing snapshot: `logs/md1-baseline-e2e/s3-colmap-md1-baseline-e2e-20260514032448-20260514T103405Z.txt`
- SageMaker (active job inventory; do not stop unrelated jobs):
  - Processing jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-processing-inprogress-20260514T103405Z.json` (includes unrelated `md1-full-fanout-r23-1778748500-leaf-*`)
  - Training jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-training-inprogress-20260514T103405Z.json` (none)
- SfM CloudWatch progress (recent ~30m; mapper still alive, currently idle in global BA):
  - Stream: `/aws/sagemaker/ProcessingJobs` / `md1-baseline-e2e-20260514032448-sfm/algo-1-1778729134`
  - Streams snapshot: `logs/md1-baseline-e2e/cloudwatch-streams-md1-baseline-e2e-20260514032448-sfm-20260514T103405Z.json`
  - Tail snapshot: `logs/md1-baseline-e2e/cloudwatch-tail-md1-baseline-e2e-20260514032448-sfm-20260514T103405Z.log`
  - Progress excerpt (filtered; safe to commit): `logs/md1-baseline-e2e/sfm-progress-md1-baseline-e2e-20260514032448-20260514T103405Z.txt`
  - Most recent observed activity in excerpt: `HEARTBEAT ... idle=4740s` at `2026-05-14T10:34:25Z` (no error lines observed).
- No-spend regression check:
  - `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` -> `OK`
  - output: `logs/md1-baseline-e2e/no-spend-unittest-test_sogs_supersplat_bundle-20260514T103405Z.txt`

### 2026-05-14T06:40:06-0600

- Git: on `agent-113647-md1-baseline-e2e` @ `d72f5523` (local poll artifacts captured; not pushed).
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
- Step Functions (previous run) is now terminal:
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260513115645` -> `TIMED_OUT`
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-20260514T123539Z.json`
- SageMaker (previous run) terminal:
  - Processing job: `md1-baseline-e2e-20260513115645-sfm` -> `Failed` (`AlgorithmError: , exit code: 1`)
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260513115645-sfm-20260514T123539Z.json`
- Step Functions (current run):
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260514032448` -> `RUNNING`
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-20260514032448-20260514T123609Z.json`
  - history snapshot (reverse): `logs/md1-baseline-e2e/stepfunctions-history-reverse-20260514032448-20260514T123609Z.json` (wait loop `WaitForSfM`)
  - executions inventory snapshots: `logs/md1-baseline-e2e/stepfunctions-list-executions-RUNNING-20260514T123557Z.json`, `logs/md1-baseline-e2e/stepfunctions-list-executions-TIMED_OUT-20260514T123557Z.json`
- SageMaker (current run):
  - Processing job: `md1-baseline-e2e-20260514032448-sfm` -> `InProgress` (`S3UploadMode=EndOfJob`)
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260514032448-sfm-20260514T123637Z.json`
  - Output prefix (S3UploadMode=EndOfJob): `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260514032448/` -> still empty
  - S3 listing snapshot: `logs/md1-baseline-e2e/s3-colmap-md1-baseline-e2e-20260514032448-20260514T123637Z.txt`
- SageMaker (active job inventory; do not stop unrelated jobs):
  - Processing jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-processing-InProgress-20260514T123904Z.json` (1 job)
  - Training jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-training-InProgress-20260514T123846Z.json` (none)
- SfM CloudWatch progress (recent ~12h; mapper reached global BA and is now quiet):
  - Stream: `/aws/sagemaker/ProcessingJobs` / `md1-baseline-e2e-20260514032448-sfm/algo-1-1778729134`
  - Streams snapshot: `logs/md1-baseline-e2e/cloudwatch-describe-log-streams-20260514T123646Z.json`
  - Tail snapshot (recent ~1h): `logs/md1-baseline-e2e/md1-baseline-e2e-20260514032448-sfm-cloudwatch-tail-20260514T123706Z.txt`
  - Progress excerpt (filtered; safe to commit): `logs/md1-baseline-e2e/sfm-progress-md1-baseline-e2e-20260514032448-20260514T123952Z.txt`
  - Most recent observed activity:
    - `Retriangulation and Global bundle adjustment` at `2026-05-14T11:05:52Z`
    - `HEARTBEAT ... idle=5460s` at `2026-05-14T12:36:54Z` (no error lines observed)

### 2026-05-14T07:39:27-0600

- Git: on `agent-113647-md1-baseline-e2e` @ `750b7e9d` (working tree clean; no code-path changes).
- Follow-up: committed + pushed poll artifacts as `4f85b3ba`.
  - CI: `CDK Deploy` run `25863420474` -> `success` (no new Pages deploy triggered by this logs-only push).
- AWS identity: `aws sts get-caller-identity` -> Account `975050048887` (region `us-west-2`).
  - snapshot: `logs/md1-baseline-e2e/aws-sts-20260514T133927Z.json`
- Step Functions (current run):
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260514032448` -> `RUNNING`
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-md1-baseline-e2e-20260514032448-20260514T133927Z.json`
  - history snapshot (reverse): `logs/md1-baseline-e2e/stepfunctions-history-reverse-md1-baseline-e2e-20260514032448-20260514T133927Z.json`
  - list snapshot (RUNNING): `logs/md1-baseline-e2e/stepfunctions-list-executions-RUNNING-20260514T133927Z.json`
- SageMaker (current run):
  - Processing job: `md1-baseline-e2e-20260514032448-sfm` -> `InProgress` (`S3UploadMode=EndOfJob`)
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260514032448-sfm-20260514T133927Z.json`
  - Output prefix (S3UploadMode=EndOfJob): `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260514032448/` -> still empty
  - S3 listing snapshot: `logs/md1-baseline-e2e/s3api-colmap-md1-baseline-e2e-20260514032448-20260514T133927Z.json` (`KeyCount=0`)
- SageMaker (active job inventory; do not stop unrelated jobs):
  - Processing jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-processing-InProgress-20260514T133927Z.json`
  - Training jobs InProgress snapshot: `logs/md1-baseline-e2e/sagemaker-list-training-InProgress-20260514T133927Z.json` (empty)
- SfM CloudWatch progress (recent ~2h; mapper is alive but only emitting heartbeats):
  - Stream: `/aws/sagemaker/ProcessingJobs` / `md1-baseline-e2e-20260514032448-sfm/algo-1-1778729134`
  - Streams snapshot: `logs/md1-baseline-e2e/cloudwatch-describe-log-streams-20260514T133927Z.json`
  - Tail snapshot: `logs/md1-baseline-e2e/md1-baseline-e2e-20260514032448-sfm-cloudwatch-tail-20260514T133927Z.txt`
  - Progress excerpt (filtered; safe to commit): `logs/md1-baseline-e2e/sfm-progress-md1-baseline-e2e-20260514032448-20260514T133927Z.txt`
  - Most recent observed activity in excerpt: `HEARTBEAT ... idle=9181s` at `2026-05-14T13:38:55Z` (no error lines observed).
- No-spend regression check:
  - `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` -> `OK`
  - output: `logs/md1-baseline-e2e/no-spend-unittest-test_sogs_supersplat_bundle-20260514T134020Z.txt`

### 2026-05-14T08:24:23-0600

- Automation correction:
  - Paused `/Users/gabrielhansen/.codex/automations/md1-baseline-e2e-monitor/automation.toml`.
  - Confirmed `status = "PAUSED"` and `kind = "cron"`.
  - Root cause of new chat cards: the cron automation has no `target_thread_id`; the current thread id is `019e2268-9fed-7593-9318-a4e8d1045849`, but the available automation tool for this session only exposes standalone cron automation fields.
  - Next automation policy: do not re-enable the standalone cron; use this chat plus `STATE.md`/`logs/agent-loop.log` as the durable resume surface unless a thread-bound heartbeat automation becomes available.
- Git: on `agent-113647-md1-baseline-e2e` @ `84efb4ed` before this ledger update.
- Step Functions (current run):
  - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260514032448` -> `RUNNING`
  - describe snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-md1-baseline-e2e-20260514032448-20260514T142423Z.json`
  - history snapshot (reverse): `logs/md1-baseline-e2e/stepfunctions-history-reverse-md1-baseline-e2e-20260514032448-20260514T142423Z.json`
- SageMaker (current run):
  - Processing job: `md1-baseline-e2e-20260514032448-sfm` -> `InProgress`
  - Output prefix (still empty because `S3UploadMode=EndOfJob`): `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260514032448/`
  - describe snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-baseline-e2e-20260514032448-sfm-20260514T142423Z.json`
  - S3 listing snapshot: `logs/md1-baseline-e2e/s3api-colmap-md1-baseline-e2e-20260514032448-20260514T142423Z.json` (`Contents` absent/empty)
- SageMaker active inventory:
  - Processing jobs InProgress: `md1-baseline-e2e-20260514032448-sfm` only.
  - Training jobs InProgress: none.
  - snapshots: `logs/md1-baseline-e2e/sagemaker-list-processing-InProgress-20260514T142423Z.json`, `logs/md1-baseline-e2e/sagemaker-list-training-InProgress-20260514T142423Z.json`
- SfM CloudWatch progress:
  - Stream: `/aws/sagemaker/ProcessingJobs` / `md1-baseline-e2e-20260514032448-sfm/algo-1-1778729134`
  - Tail snapshots: `logs/md1-baseline-e2e/md1-baseline-e2e-20260514032448-sfm-cloudwatch-tail-20260514T142423Z.json`, `logs/md1-baseline-e2e/md1-baseline-e2e-20260514032448-sfm-cloudwatch-tail-20260514T142423Z.txt`
  - Most recent evidence: mapper resumed after the earlier long idle stretch, registered images through `num_reg_frames=1420` at `2026-05-14T13:47:37Z`, then entered `Retriangulation and Global bundle adjustment` at `2026-05-14T13:47:40Z`; latest heartbeat in this tail is `elapsed=30759s idle=2160s` (no error lines observed).
- No-spend regression check:
  - `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` -> `OK`
  - output: `logs/md1-baseline-e2e/no-spend-unittest-test_sogs_supersplat_bundle-20260514T142423Z.txt`

### 2026-05-14T08:43:29-0600

- Viewer visual gate found a real issue:
  - Fresh public smoke initially passed telemetry, but manual screenshot inspection showed `/md1-viewer` rendered the global header/footer feedback panel over the splat.
  - This made the old viewer smoke too permissive: it verified pixels and telemetry, but did not verify that the viewer surface was actually unobstructed.
- Fix applied:
  - `web/components/SiteChrome.tsx`: treat `/md1-viewer` and `/sfm-output-viewer` as standalone routes, matching the existing SOGS viewer behavior.
  - `web/scripts/test-md1-production-viewer.mjs`: fail if `/md1-viewer` renders `header`, `footer`, or `#footer-stats`.
- Local verification:
  - `npm run build` -> passed (existing lint warnings only).
  - `MD1_VIEWER_URL=http://127.0.0.1:3032 node scripts/test-md1-production-viewer.mjs` -> passed with the stricter chrome assertions.
  - local desktop first frame `213.2ms`, mobile first frame `199.3ms`.
  - updated screenshots: `logs/md1-production-viewer-desktop.png`, `logs/md1-production-viewer-mobile.png` now show the MD1 panel only, no global header/footer feedback overlay.
  - one-off Playwright check for `http://127.0.0.1:3032/sfm-output-viewer` -> `{"header":0,"footer":0,"feedback":0,"canvas":1}`.

### 2026-05-14T08:52:41-0600

- Preview deploy after viewer fix:
  - Pages run `25866557369` -> `success`.
  - CDK run `25866557372` -> `success`.
  - Exact preview URLs from the Pages run log:
    - alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`
    - hash: `https://42fc5824.v0-spaceport-website-preview2.pages.dev`
- Deployed-preview viewer verification:
  - `MD1_VIEWER_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev node scripts/test-md1-production-viewer.mjs` -> passed with standalone chrome assertions.
  - desktop first frame `474.1ms`, chunk meta requests `5`.
  - mobile first frame `827.7ms`, chunk meta requests `17`.
  - screenshots: `logs/md1-production-viewer-desktop.png`, `logs/md1-production-viewer-mobile.png`.
  - manual visual inspection: screenshots show only the MD1 viewer panel and splat canvas; the previous global header/footer feedback overlay is gone.

### 2026-05-14T09:14:00-0600

- Automation correction completed:
  - `/Users/gabrielhansen/.codex/automations/md1-baseline-e2e-monitor/automation.toml` changed from `kind = "cron"` to `kind = "heartbeat"`.
  - `status = "ACTIVE"`, `rrule = "FREQ=MINUTELY;INTERVAL=30"`, `target_thread_id = "019e2268-9fed-7593-9318-a4e8d1045849"`.
  - `codex_app.automation_update` `mode=view` rendered the automation card after the change.
  - Expected behavior: future automation runs append into this thread instead of making new chat cards.
- Latest canonical SfM status before this ledger update:
  - Step Functions execution `execution-md1-baseline-e2e-20260514032448` -> `RUNNING`.
  - SageMaker processing job `md1-baseline-e2e-20260514032448-sfm` -> `InProgress`.
  - S3 output prefix still empty (`S3UploadMode=EndOfJob`).
  - Latest observed heartbeat at 2026-05-14T09:08:08-0600: `elapsed=33399s idle=4800s`.
  - External active training job observed: `md1-full2157-ds4-r24-1778769804`; do not stop or count as this run.

### 2026-05-14T09:14:55-0600

- User concern addressed:
  - Confirmed root cause of new chat cards: the previous `md1-baseline-e2e-monitor` automation was `kind = "cron"` with no thread target.
  - Current monitor file: `/Users/gabrielhansen/.codex/automations/md1-baseline-e2e-monitor/automation.toml`.
  - Current monitor state: `kind = "heartbeat"`, `status = "ACTIVE"`, `rrule = "FREQ=MINUTELY;INTERVAL=30"`, `target_thread_id = "019e2268-9fed-7593-9318-a4e8d1045849"`.
  - Intended behavior: future monitor runs append to the current MD1 thread instead of creating new chat cards.
- GitHub workflow gate:
  - Branch: `agent-113647-md1-baseline-e2e`.
  - Latest head after automation ledger commit: `d3392a47`.
  - `gh run list --branch agent-113647-md1-baseline-e2e --limit 6` showed latest runs green.
  - Latest run: `25867928726` / `CDK Deploy` / `success` / `3m52s` / triggered by `chore: record md1 heartbeat automation`.
  - Prior viewer deploy proof remains green: Pages run `25866557369` and CDK run `25866557372`.
- Current canonical SfM run:
  - Step Functions execution: `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260514032448` -> `RUNNING`.
  - SageMaker processing job: `md1-baseline-e2e-20260514032448-sfm` -> `InProgress`.
  - Processing instance: `ml.g4dn.xlarge`, max runtime `86400`.
  - Runtime env verified: `COLMAP_MONOLITHIC_MAPPER_TIMEOUT_SECONDS=43200`, `COLMAP_BUNDLE_ADJUSTER_TIMEOUT_SECONDS=43200`.
  - Output prefix: `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260514032448/` still empty; expected while running because `S3UploadMode=EndOfJob`.
  - CloudWatch stream: `/aws/sagemaker/ProcessingJobs` / `md1-baseline-e2e-20260514032448-sfm/algo-1-1778729134`.
  - Latest observed heartbeat: `COLMAP[mapper_spatial_sequential_only] HEARTBEAT elapsed=33819s idle=5220s`.
  - No error lines were observed in the latest log tail.
- Active job inventory:
  - Processing jobs InProgress: `md1-baseline-e2e-20260514032448-sfm` only.
  - Training jobs InProgress: `md1-full2157-ds4-r24-1778769804`; external to this canonical run, leave untouched.
- Next step:
  - Continue conservative polling until SfM either finishes and uploads COLMAP output, or fails with a concrete timeout/error.
  - On SfM success: validate COLMAP S3 contents, then monitor the downstream `3dgs` and compression stages.
  - On SfM failure: capture the exact failure and prefer a bounded continuation from the known validated SfM reference over launching another full SfM job.

### 2026-05-14T11:39:59-0600

- Heartbeat progress check:
  - Git branch/head clean: `agent-113647-md1-baseline-e2e` @ `eb7b643d315dd9b7faba5ed1f1eb142c1e36a36a`.
  - AWS identity verified: account `975050048887`.
  - GitHub workflows remain green; latest exact-head run is `25868226962` / `CDK Deploy` / `success`.
- Current canonical SfM run:
  - Step Functions execution: `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260514032448` -> `RUNNING`.
  - SageMaker processing job: `md1-baseline-e2e-20260514032448-sfm` -> `InProgress`.
  - Output prefix remains empty as expected before EndOfJob upload: `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260514032448/`.
  - `COLMAP_MONOLITHIC_MAPPER_TIMEOUT_SECONDS=43200`, `COLMAP_BUNDLE_ADJUSTER_TIMEOUT_SECONDS=43200`, processing max runtime `86400`.
- Important progress:
  - Mapper resumed after the earlier heartbeat-only stretch.
  - Latest CloudWatch tail shows active registrations through `num_reg_frames=1560`.
  - Latest registration before bundle adjustment: image `#2876` at `2026-05-14T17:32:44Z`.
  - Then `Retriangulation and Global bundle adjustment` at `2026-05-14T17:32:47Z`.
  - Latest heartbeat after that activity: `COLMAP[mapper_spatial_sequential_only] HEARTBEAT elapsed=42524s idle=420s`.
  - This is close to the `43200s` mapper timeout, but the idle timer reset after real registration progress, so the run is still worth monitoring rather than interrupting.
- Active job inventory:
  - Processing jobs InProgress: `md1-baseline-e2e-20260514032448-sfm`.
  - Training jobs InProgress: none at this poll.
- Next step:
  - Poll again soon for either mapper completion/S3 EndOfJob upload or a concrete timeout/failure.

### 2026-05-14T12:11:56-0600

- Canonical SfM retry ended without usable COLMAP output:
  - Step Functions execution `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-baseline-e2e-20260514032448` ended `SUCCEEDED` only because the pipeline notified failure via `NotifyError`; this is not a successful training pipeline completion.
  - SageMaker processing job `md1-baseline-e2e-20260514032448-sfm` -> `Failed`.
  - Processing end time: `2026-05-14T11:51:18-0600`.
  - SageMaker failure reason: `AlgorithmError: , exit code: 1`.
  - S3 output prefix contains only `sfm_metadata.json`, not trainable COLMAP sparse output:
    - `s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260514032448/sfm_metadata.json`
  - Metadata failure stage: `mapper_spatial_sequential_only`.
  - Metadata failure detail: `GPS-first mapper failed: mapper_spatial_sequential_only timed out after 43200s`.
  - Last useful mapper progress before timeout: `num_reg_frames=1560`, then `Retriangulation and Global bundle adjustment`.
  - Command evidence:
    - `aws sagemaker describe-processing-job --processing-job-name md1-baseline-e2e-20260514032448-sfm`
    - `aws s3 cp s3://spaceport-ml-processing-staging/colmap/md1-baseline-e2e-20260514032448/sfm_metadata.json -`
    - `aws logs get-log-events --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name md1-baseline-e2e-20260514032448-sfm/algo-1-1778729134 --limit 200 --no-start-from-head`
- Continuation decision:
  - Did not relaunch full SfM.
  - Verified no running Step Functions executions for `SpaceportMLPipeline-staging`, no InProgress SageMaker processing jobs, and no InProgress training jobs before launching a bounded downstream continuation.
  - Verified existing validated SfM reference has required COLMAP structure:
    - `s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap/`
    - sample keys include `database.db`, `images/DJI_0001.JPG`, `sparse/0/cameras.txt`, `sparse/0/images.txt`, `sparse/0/points3D.txt`, `sparse/0/frames.txt`, and `sparse/0/rigs.txt`.
- New canonical continuation:
  - Started one 3DGS-only Step Functions execution from the validated SfM reference.
  - Command:
    - `aws stepfunctions start-execution --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --name execution-md1-e2e-vsfm-202605141811 --input <3dgs-only input>`
  - Execution ARN:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-202605141811`
  - Job id/name: `md1-e2e-vsfm-202605141811`.
  - `pipelineStep`: `3dgs`.
  - `colmapOutputS3Uri`: `s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap/`.
  - `gaussianOutputS3Uri`: `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-202605141811/`.
  - `compressedOutputS3Uri`: `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-202605141811/`.
  - 3DGS SageMaker training job: `md1-e2e-vsfm-202605141811-3dgs`.
  - Training instance/runtime: `ml.g5.2xlarge`, `MaxRuntimeInSeconds=14400`.
  - Training image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:latest`.
  - Initial training status: `InProgress`, secondary status `Pending` (waiting for capacity).
- Next step:
  - Monitor `md1-e2e-vsfm-202605141811-3dgs` until it starts training or fails; then validate 3DGS output and compression handoff.

### 2026-05-14T12:47:11-0600

- Heartbeat check after the 3DGS-only continuation:
  - Git branch/head before this patch: `agent-113647-md1-baseline-e2e` @ `07f11807654f2ac1887647a6091408a665bee4c9`.
  - AWS identity: `aws sts get-caller-identity` -> account `975050048887`.
  - GitHub workflows: latest exact-head run `25877162565` / `CDK Deploy` / `success`; deployed viewer preview remains `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev/md1-viewer`.
- 3DGS-only continuation failed before training iterations:
  - Step Functions execution `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-202605141811` ended `SUCCEEDED` only through `NotifyError`; this is not a successful pipeline completion.
  - SageMaker training job `md1-e2e-vsfm-202605141811-3dgs` -> `Failed`.
  - Training start/end: `2026-05-14T12:12:38-0600` / `2026-05-14T12:23:20-0600`; billable time `642s`.
  - Failure reason: `AlgorithmError: , exit code: 1`.
  - 3DGS output prefix is empty despite the SageMaker model-artifact placeholder:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-202605141811/`
  - Compression output prefix is empty:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-202605141811/`
  - Training log stream: `/aws/sagemaker/TrainingJobs` / `md1-e2e-vsfm-202605141811-3dgs/algo-1-1778782357`.
  - Log evidence from `aws logs get-log-events --log-group-name /aws/sagemaker/TrainingJobs --log-stream-name md1-e2e-vsfm-202605141811-3dgs/algo-1-1778782357 --start-from-head`:
    - COLMAP validation passed in the 3DGS container: `Cameras: 1`, `Images registered: 2157`, `Image files: 2157`, `3D points: 1312804`.
    - Failed command: `ns-train splatfacto-w-light --data /tmp/nerfstudio_training/converted_data --output-dir /tmp/nerfstudio_training --max_num_iterations 30000 --pipeline.model.sh_degree 3 --logging.steps_per_log 100 --vis tensorboard --pipeline.datamanager.cache-images cpu --pipeline.model.max-gauss-ratio 10 nerfstudio-data --eval-mode fraction --train-split-fraction 0.9`.
    - Exact CLI error: `Unrecognized or misplaced options`; the live `ns-train` help listed available subcommands including `splatfacto-w`, but not `splatfacto-w-light`.
- Patch applied in this branch:
  - `infrastructure/spaceport_cdk/lambda/start_ml_job/lambda_function.py`: default `MODEL_VARIANT` changed from `splatfacto-w-light` to the deployed plugin command `splatfacto-w`.
  - `infrastructure/containers/3dgs/nerfstudio_config.yaml`, `Dockerfile`, `train_nerfstudio_production.py`, and `test_nerfstudio_pipeline.py`: aligned defaults/checks/logging with `splatfacto-w` so a future container build does not verify an unavailable command.
- Local no-spend verification after the patch:
  - `python3 -m py_compile infrastructure/spaceport_cdk/lambda/start_ml_job/lambda_function.py infrastructure/containers/3dgs/train_nerfstudio_production.py infrastructure/containers/3dgs/export_splatfacto_w_assets.py infrastructure/containers/3dgs/run_export_quality_pass.py infrastructure/containers/3dgs/sky_quality.py infrastructure/containers/3dgs/test_nerfstudio_pipeline.py` -> passed.
  - `ruby -e 'require "yaml"; YAML.load_file("infrastructure/containers/3dgs/nerfstudio_config.yaml"); puts "yaml ok"'` -> passed.
  - `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` -> passed.
  - `git diff --check` -> passed.
  - `python3 infrastructure/containers/3dgs/test_nerfstudio_pipeline.py infrastructure/containers/3dgs/test_input/data/training` was attempted, but this repo fixture is incomplete (`sparse/0/cameras.txt` missing) and the local Python environment lacks optional container deps (`yaml`, `PIL`); use this as non-blocking local-context evidence only.
- Active job inventory at this poll:
  - Processing jobs InProgress: none.
  - Training jobs InProgress: `md1-r0vissent-v2exec-1778783555-tile-04`; external to this canonical run, leave untouched.
- Next step:
  - Commit/push this proven 3DGS fix.
  - Watch the exact-head workflows, including the automatic 3DGS container build triggered by the `infrastructure/containers/3dgs/` changes.
  - After the branch-tagged 3DGS image exists, rerun the smallest continuation only: 3DGS from `s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap/` with `MODEL_VARIANT=splatfacto-w`, then validate compression and the final viewer.

### 2026-05-14T13:23:04-0600

- Git before this ledger update:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `d5447720e305d7da6a57b337ea905be15dc2a2b0`.
  - Working tree: dirty with the new 3DGS retry payload/start artifacts plus the proven 3DGS parser fix.
- GitHub / image build proof for `d5447720`:
  - `CDK Deploy` run `25878909869` -> `success`.
  - `Trigger ML Container Build` run `25878909887` -> `success`.
  - CodeBuild build `spaceport-ml-containers:2ec3bb87-b6ed-478b-a33c-f3d454a599f3` -> `SUCCEEDED`.
  - Branch ECR image used by the retry: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:agent113647md1baselinee2e`.
- 3DGS retry launched from the validated SfM reference:
  - Payload: `logs/md1-baseline-e2e/md1-e2e-vsfm-w-202605141905-payload.json`.
  - Start proof: `logs/md1-baseline-e2e/md1-e2e-vsfm-w-202605141905-start.json`.
  - Execution ARN: `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-w-202605141905`.
  - Job id/name: `md1-e2e-vsfm-w-202605141905`.
  - `pipelineStep`: `3dgs`.
  - `MODEL_VARIANT`: `splatfacto-w`.
  - `colmapOutputS3Uri`: `s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap/`.
  - `gaussianOutputS3Uri`: `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-w-202605141905/`.
  - `compressedOutputS3Uri`: `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-w-202605141905/`.
- 3DGS retry result:
  - Step Functions execution ended `SUCCEEDED` only through the pipeline failure notification path; this is not a successful training/compression completion.
  - SageMaker training job `md1-e2e-vsfm-w-202605141905-3dgs` -> `Failed`.
  - Training start/end: `2026-05-14T13:06:50-0600` / `2026-05-14T13:18:03-0600`; billable time `673s`.
  - Failure reason: `AlgorithmError: , exit code: 1`.
  - 3DGS output prefix empty: `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-w-202605141905/`.
  - Compression output prefix empty: `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-w-202605141905/`.
  - Evidence snapshots:
    - `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-w-202605141905-3dgs-20260514T192304Z.json`.
    - `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-w-202605141905-20260514T192304Z.json`.
    - `logs/md1-baseline-e2e/stepfunctions-history-reverse-md1-e2e-vsfm-w-202605141905-20260514T192304Z.json`.
    - `logs/md1-baseline-e2e/s3api-3dgs-md1-e2e-vsfm-w-202605141905-20260514T192304Z.json`.
    - `logs/md1-baseline-e2e/s3api-compressed-md1-e2e-vsfm-w-202605141905-20260514T192304Z.json`.
    - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-w-202605141905-failure-filtered-20260514T192304Z.txt`.
- Failure root cause:
  - `ns-process-data` succeeded and matched all `2157` images from the validated SfM reference.
  - `transforms.json` validation succeeded with size `1907101` bytes.
  - The patched retry used `ns-train splatfacto-w ...` without a dataparser suffix.
  - The full `splatfacto-w` method selected `splatfactow.nerfw_dataparser.NerfW`, which expects a phototourism/Nerf-W layout at `dense/sparse/cameras.bin`.
  - Exact error: `FileNotFoundError: [Errno 2] No such file or directory: '/tmp/nerfstudio_training/converted_data/dense/sparse/cameras.bin'`.
  - Independent source check: upstream `KevinXu02/splatfacto-w` README states full `splatfacto-w` expects Nerf-W/phototourism data and points generic datasets to `splatfacto-w-light`.
- Patch applied for the proven failure:
  - Reverted the MD1/default 3DGS method to `splatfacto-w-light`.
  - Added the explicit `nerfstudio-data --eval-mode fraction --train-split-fraction 0.9` dataparser suffix for `splatfacto-w-light`.
  - Updated the Dockerfile build gate to verify `ns-train splatfacto-w-light --help` so the next branch image proves the command exists before another paid SageMaker retry.
  - Kept `splatfacto-w` guarded with a warning because it is unsuitable for the generic one-camera MD1 COLMAP/transforms flow.
- No-spend verification after the patch:
  - `python3 -m py_compile infrastructure/spaceport_cdk/lambda/start_ml_job/lambda_function.py infrastructure/containers/3dgs/train_nerfstudio_production.py infrastructure/containers/3dgs/export_splatfacto_w_assets.py infrastructure/containers/3dgs/run_export_quality_pass.py infrastructure/containers/3dgs/sky_quality.py infrastructure/containers/3dgs/test_nerfstudio_pipeline.py` -> passed.
  - `ruby -e 'require "yaml"; YAML.load_file("infrastructure/containers/3dgs/nerfstudio_config.yaml"); puts "yaml ok"'` -> passed.
  - `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` -> passed.
  - `git diff --check` -> passed.
  - `rg -n "splatfacto-w-light|nerfstudio-data|train-split-fraction" ...` verified the default, Docker build gate, and parser suffix.
- Active job inventory at this poll:
  - Processing jobs InProgress: none.
  - Training jobs InProgress: none.
- Next step:
  - Commit/push the proven parser-method fix and retry evidence.
  - Wait for exact-head `CDK Deploy` and `Trigger ML Container Build`.
  - Only after the branch image proves `splatfacto-w-light`, rerun the smallest stage: 3DGS from `s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap/`.

### 2026-05-14T14:04:10-0600

- Git:
  - Committed and pushed parser-method fix: `638da632f507c7b2f86ffa914101d0a6758bdc25` (`fix: use generic splatfacto-w light parser`).
  - Branch: `agent-113647-md1-baseline-e2e`.
- Exact-head workflow gate for `638da632`:
  - `CDK Deploy` run `25880748077` -> `success`.
  - `Trigger ML Container Build` run `25880748113` -> `success`.
  - Run snapshot: `logs/md1-baseline-e2e/gh-runs-agent-113647-md1-baseline-e2e-20260514T194123Z.json`.
- Branch 3DGS image build:
  - CodeBuild: `spaceport-ml-containers:ede36622-9ae1-4c5b-a15e-8f60d82a6724` -> `SUCCEEDED`.
  - Source version: `638da632f507c7b2f86ffa914101d0a6758bdc25`.
  - Build env: `CONTAINERS_TO_BUILD=3dgs`, `BRANCH_SUFFIX=agent113647md1baselinee2e`.
  - Snapshot: `logs/md1-baseline-e2e/codebuild-spaceport-ml-containers-ede36622-20260514T194123Z.json`.
  - Critical no-spend build gate passed inside the Docker build:
    - `RUN ns-train splatfacto-w-light --help > /dev/null && echo "✅ splatfacto-w-light CLI available"`.
    - Proof: `logs/md1-baseline-e2e/codebuild-3dgs-light-cli-proof-ede36622-20260514T194123Z.txt`.
  - ECR branch tag now points to digest `sha256:6b3b2492af7a268cfc5f233e87bdce51c47492ada4c3630f723114ffa464fd0c`.
  - ECR proof: `logs/md1-baseline-e2e/ecr-spaceport-3dgs-agent113647md1baselinee2e-20260514T194123Z.json`.
- New canonical 3DGS-only retry launched after branch image proof:
  - Execution ARN: `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-light-202605141942`.
  - Job id/name: `md1-e2e-vsfm-light-202605141942`.
  - SageMaker training job: `md1-e2e-vsfm-light-202605141942-3dgs`.
  - `pipelineStep`: `3dgs`.
  - `MODEL_VARIANT`: `splatfacto-w-light`.
  - 3DGS image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:agent113647md1baselinee2e`.
  - Input COLMAP: `s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap/`.
  - 3DGS output: `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-light-202605141942/`.
  - Compression output: `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-light-202605141942/`.
  - Payload: `logs/md1-baseline-e2e/md1-e2e-vsfm-light-202605141942-payload.json`.
  - Start proof: `logs/md1-baseline-e2e/md1-e2e-vsfm-light-202605141942-start.json`.
- Latest runtime status:
  - Step Functions execution is `RUNNING`.
  - Training job is `InProgress`, secondary status `Training`.
  - Training started at `2026-05-14T13:41:44-0600`; image download ended and training phase began at `2026-05-14T13:46:01-0600`.
  - Current log stream: `/aws/sagemaker/TrainingJobs` / `md1-e2e-vsfm-light-202605141942-3dgs/algo-1-1778787704`.
  - COLMAP validation passed again: `Cameras: 1`, `Images registered: 2157`, `3D points: 1312804`.
  - `ns-process-data` completed and `transforms.json` validation passed.
  - Current `ns-train` command was accepted and is running beyond the previous quick parser failures:
    - `ns-train splatfacto-w-light --data /tmp/nerfstudio_training/converted_data --output-dir /tmp/nerfstudio_training --vis tensorboard --max_num_iterations 30000 ... nerfstudio-data --eval-mode fraction --train-split-fraction 0.9`.
  - Important caveat: this trainer invocation uses `subprocess.run(..., capture_output=True)`, so NerfStudio iteration logs will appear only after the subprocess exits; SageMaker status is the live progress gate until completion/failure.
- Active job inventory at launch:
  - Running Step Functions executions before launch: none.
  - Processing jobs InProgress: none.
  - External training job observed: `md1-r0vissent-v3density-1778787389-tile-04`; left untouched.
- Next step:
  - Continue polling `md1-e2e-vsfm-light-202605141942-3dgs` for terminal status.
  - If it fails, capture the exact log tail and patch only that failure.
  - If it completes, validate `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-light-202605141942/`, then monitor/validate compression and wire the final viewer.
