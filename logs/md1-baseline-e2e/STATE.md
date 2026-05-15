# MD1 Baseline E2E State

updated: 2026-05-15T08:15:00-0600
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

### 2026-05-14T17:15:45-0600

- Canonical `splatfacto-w-light` bg/alpha retry reached pipeline success, but failed the visual quality gate:
  - Step Functions execution `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-light-202605141942` -> `SUCCEEDED`.
  - 3DGS training job `md1-e2e-vsfm-light-202605141942-3dgs` -> `Completed`.
  - Training time/billable time: `11871s` on `ml.g5.2xlarge`.
  - Model artifact: `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-light-202605141942/md1-e2e-vsfm-light-202605141942-3dgs/output/model.tar.gz`.
  - Compression job `md1-e2e-vsfm-light-202605141942-compression` -> `Completed`.
  - Compression output: `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-light-202605141942/`.
  - Bundle manifest: `https://spaceport-ml-processing-staging.s3.amazonaws.com/compressed/md1-e2e-vsfm-light-202605141942/supersplat_bundle/lod-meta.json`.
  - Compression summary: `45` bundle files, `2748289` bytes, `4` LOD levels, `4` chunk files, source `splat.ply`, compression ratio `2.8474`.
  - Training metadata reported only `31083` remaining gaussians and `splat.ply` size `7.35 MB`; visual screenshots were skybox-dominant/overexposed rather than an acceptable MD1 baseline.
  - Evidence:
    - Full 3DGS log: `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-light-202605141942-full-log-20260514T231214Z.txt`.
    - Viewer smoke results: `logs/md1-production-viewer-results.json`.
    - Visual gate screenshots: `logs/md1-baseline-e2e/md1-e2e-vsfm-light-202605141942-visual-gate-desktop.png`, `logs/md1-baseline-e2e/md1-e2e-vsfm-light-202605141942-visual-gate-mobile.png`.
  - Deployed viewer smoke technically passed loading/telemetry against the new bundle:
    - `MD1_VIEWER_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev MD1_LOD_URL=https://spaceport-ml-processing-staging.s3.amazonaws.com/compressed/md1-e2e-vsfm-light-202605141942/supersplat_bundle/lod-meta.json MD1_EXPECT_CHUNK_SUBSTRING=md1-e2e-vsfm-light-202605141942 node scripts/test-md1-production-viewer.mjs` -> passed.
    - Desktop first frame `794.6ms`, `1/4` chunk meta requests.
    - Mobile first frame `93.9ms`, `2/4` chunk meta requests.
- Failure diagnosis and bounded retry:
  - Did not relaunch full SfM.
  - Verified no running Step Functions executions and no InProgress SageMaker training/processing jobs before retry.
  - Root cause candidate is the MD1-specific bg/alpha/robust-mask override on `splatfacto-w-light`; upstream light defaults keep `enable_bg_model`, `enable_alpha_loss`, and `enable_robust_mask` disabled.
  - Launched one smallest-stage retry from the same validated SfM reference, keeping `splatfacto-w-light` but disabling bg/alpha/robust-mask/floater-pruning and using quality-oriented culling:
    - Execution ARN: `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-fg-202605142314`.
    - Job id/name: `md1-e2e-vsfm-fg-202605142314`.
    - Training job: `md1-e2e-vsfm-fg-202605142314-3dgs`.
    - Input COLMAP: `s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap/`.
    - 3DGS output: `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-fg-202605142314/`.
    - Compression output: `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-fg-202605142314/`.
    - Payload: `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-payload.json`.
    - Start proof: `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-start.json`.
    - Key overrides: `ENABLE_BG_MODEL=false`, `ENABLE_ALPHA_LOSS=false`, `ENABLE_ROBUST_MASK=false`, `FLOATER_PRUNING_ENABLED=false`, `CULL_ALPHA_THRESH=0.005`, `CULL_SCALE_THRESH=0.5`, `USE_SCALE_REGULARIZATION=false`, `NEVER_MASK_UPPER=0.0`.
  - Initial status: Step Functions `RUNNING`; SageMaker training job `InProgress/Pending` on `ml.g5.2xlarge` with `MaxRuntimeInSeconds=14400`.
- Next step:
  - Monitor `md1-e2e-vsfm-fg-202605142314-3dgs`.
  - If it succeeds, validate gaussian count/file size before compression is accepted as final; then smoke and visually inspect the final viewer.
  - If it fails, capture exact logs and patch only that proven failure.

### 2026-05-14T17:24:39-0600

- Git / CI:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `a1cd09b8e23fb2de37fb083ccb321591c4b845f7`.
  - Working tree was clean before this ledger update.
  - Exact-head GitHub workflow: `CDK Deploy` run `25891189386` -> `success`.
- AWS identity:
  - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Active pipeline state:
  - Running Step Functions executions for `SpaceportMLPipeline-staging`: only `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-fg-202605142314`.
  - Execution status: `RUNNING`.
  - SageMaker training job: `md1-e2e-vsfm-fg-202605142314-3dgs` -> `InProgress`, secondary status `Training`.
  - Training image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:agent113647md1baselinee2e`.
  - Training instance/runtime: `ml.g5.2xlarge`, `MaxRuntimeInSeconds=14400`.
  - Training started at `2026-05-14T17:16:35-0600`; image download completed and `Training` began at `2026-05-14T17:20:58-0600`.
  - Active processing jobs: none.
  - Active training jobs: only `md1-e2e-vsfm-fg-202605142314-3dgs`.
- Current log proof:
  - Log stream: `/aws/sagemaker/TrainingJobs` / `md1-e2e-vsfm-fg-202605142314-3dgs/algo-1-1778800595`.
  - COLMAP validation passed: `Cameras: 1`, `Images registered: 2157`, `Image files: 2157`, `3D points: 1312804`.
  - Config overrides confirmed in the container: `enable_bg_model=False`, `enable_alpha_loss=False`, `enable_robust_mask=False`, `floater_pruning.enabled=False`, `cull_alpha_thresh=0.005`, `cull_scale_thresh=0.5`, `never_mask_upper=0.0`.
  - `colmap model_converter` completed and produced `cameras.bin`, `images.bin`, and `points3D.bin`.
  - Current visible step: `ns-process-data images --data /opt/ml/input/data/training/images --output-dir /tmp/nerfstudio_training/converted_data --skip-colmap --colmap-model-path /tmp/nerfstudio_training/colmap_bin/0`.
- Output prefixes at this check:
  - 3DGS output still empty as expected until SageMaker job end: `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-fg-202605142314/`.
  - Compression output still empty because compression has not started: `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-fg-202605142314/`.
- Next step:
  - Continue monitoring the same foreground-only 3DGS job. Do not launch another retry while this one is active.

### 2026-05-14T17:31:17-0600

- Foreground retry handoff proof:
  - Command used to inspect logs:
    - `aws logs get-log-events --log-group-name /aws/sagemaker/TrainingJobs --log-stream-name md1-e2e-vsfm-fg-202605142314-3dgs/algo-1-1778800595 --start-time 1778801232246 --start-from-head --limit 300 | jq -r '.events[].message' | rg -n "ns-train|Executing|Training command|transforms|ERROR|validation passed|Max iterations|Dataparser|completed"`
  - `ns-process-data` completed far enough to produce and validate `transforms.json`.
  - `transforms.json` size: `1907101` bytes.
  - `transforms.json validation passed`.
  - The accepted training command is now running:
    - `ns-train splatfacto-w-light --data /tmp/nerfstudio_training/converted_data --output-dir /tmp/nerfstudio_training --vis tensorboard --max_num_iterations 30000 --pipeline.model.sh_degree 3 --logging.steps_per_log 100 --pipeline.model.rasterize_mode classic --pipeline.model.use_scale_regularization False --pipeline.model.cull_alpha_thresh 0.005 --pipeline.model.cull_scale_thresh 0.5 --pipeline.model.enable_bg_model False --pipeline.model.enable_alpha_loss False --pipeline.model.enable_robust_mask False --pipeline.model.bg_sh_degree 4 --pipeline.model.appearance_embed_dim 24 --pipeline.model.never_mask_upper 0.0 --pipeline.model.max-gauss-ratio 10.0 nerfstudio-data --eval-mode fraction --train-split-fraction 0.9`.
  - No `ERROR` events were present in the log stream at this check.
- Current gate:
  - SageMaker still reports `md1-e2e-vsfm-fg-202605142314-3dgs` as `InProgress` / `Training`.
  - Because the trainer captures `ns-train` subprocess output, iteration metrics may not stream until the command exits; keep using SageMaker terminal state as the live gate.

### 2026-05-14T20:40:27-0600

- Git / CI:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `a0e44d75e84d17e0fa6f94f85c4bf3347434dacb`.
  - Working tree was clean before this ledger update.
  - Exact-head GitHub workflow: `CDK Deploy` run `25891672328` -> `success`.
- AWS identity:
  - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
- Foreground-only 3DGS retry completed:
  - Step Functions execution is still `RUNNING` because it has advanced to compression polling:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-fg-202605142314`.
  - SageMaker training job `md1-e2e-vsfm-fg-202605142314-3dgs` -> `Completed`.
  - Training time/billable time: `10749s` on `ml.g5.2xlarge`.
  - Training start/end: `2026-05-14T17:16:35-0600` / `2026-05-14T20:15:44-0600`.
  - Model artifact:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-fg-202605142314/md1-e2e-vsfm-fg-202605142314-3dgs/output/model.tar.gz`.
  - S3 listing currently shows the model artifact only:
    - `aws s3 ls s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-fg-202605142314/ --recursive --summarize`
    - `Total Objects: 1`, `Total Size: 62840511`.
  - Training log tail confirms full 30k iterations completed and export succeeded:
    - Iterations reached `29999 (100.00%)`.
    - `Training Finished`.
    - `Model export completed successfully`.
    - `PLY file: splat.ply (312.4 MB)`.
    - `file_size_mb: 312.391170501709`.
    - `enable_bg_model: False`, `enable_alpha_loss: False`, `enable_robust_mask: False`.
    - `floater_pruning: {'enabled': False, ...}`.
    - `NERFSTUDIO TRAINING PIPELINE COMPLETED SUCCESSFULLY`.
- Compression is now active:
  - Processing job: `md1-e2e-vsfm-fg-202605142314-compression`.
  - Status: `InProgress`.
  - Instance/runtime: `ml.g4dn.xlarge`, `MaxRuntimeInSeconds=86400`.
  - Started: `2026-05-14T20:18:04-0600`.
  - Input:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-fg-202605142314/`.
  - Output:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-fg-202605142314/`.
  - Processing log stream:
    - `/aws/sagemaker/ProcessingJobs` / `md1-e2e-vsfm-fg-202605142314-compression/algo-1-1778811483`.
  - Compression log proof:
    - `splat-transform v1.10.2`.
    - Extracted `model.tar.gz`.
    - Selected PLY source `/opt/ml/processing/input/__extracted_archives/00-model-tar/splat.ply`.
    - Supporting file `training_metadata.json` discovered.
    - Running `splat-transform -w -g cpu .../splat.ply .../generated_bundle/meta.json`.
  - Compression S3 output is still empty as expected until job end (`S3UploadMode=EndOfJob`):
    - `aws s3 ls s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-fg-202605142314/ --recursive --summarize` -> `Total Objects: 0`.
- Active job inventory:
  - Running Step Functions executions: only `execution-md1-e2e-vsfm-fg-202605142314`.
  - InProgress training jobs: none for this run; the 3DGS job is completed.
  - InProgress processing jobs: `md1-e2e-vsfm-fg-202605142314-compression`.
- Next step:
  - Continue monitoring compression. If it completes, validate bundle files/summary, smoke the deployed `/md1-viewer` with the new foreground-only manifest, then visually inspect screenshots before accepting the output.
  - If compression fails, capture exact processing logs and patch only that proven failure.

### 2026-05-14T23:14:33-0600

- Git / CI / AWS verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `98c2c6cfa560ba75dae20772a94dbf8c9a5f18b7`.
  - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - `aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING` -> `[]`.
  - `aws sagemaker list-processing-jobs --status-equals InProgress` -> no processing jobs.
  - `aws sagemaker list-training-jobs --status-equals InProgress` -> one external job only, `md1-r0vissent-v4scaffold-1778819897-tile-04`; left untouched.
  - Exact-head GitHub workflow: `CDK Deploy` run `25897327078` @ `98c2c6cfa560ba75dae20772a94dbf8c9a5f18b7` -> `success`.
- Foreground retry terminal state:
  - Step Functions execution `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-fg-202605142314` -> `SUCCEEDED`, started `2026-05-14T17:15:05-0600`, stopped `2026-05-14T22:32:53-0600`.
  - 3DGS job `md1-e2e-vsfm-fg-202605142314-3dgs` -> `Completed`; training/billable time `10749s` on `ml.g5.2xlarge`.
  - Model artifact: `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-fg-202605142314/md1-e2e-vsfm-fg-202605142314-3dgs/output/model.tar.gz`.
  - Full training log snapshots:
    - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-fg-202605142314-full-log-20260515T0505Z.json`
    - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-fg-202605142314-full-log-20260515T0505Z.txt`
  - Log proof includes `Training Finished`, `Model export completed successfully`, `PLY file: splat.ply (312.4 MB)`, and `enable_bg_model=False`, `enable_alpha_loss=False`, `enable_robust_mask=False`, `floater_pruning.enabled=False`.
- Compression terminal state:
  - Processing job `md1-e2e-vsfm-fg-202605142314-compression` -> `Completed` on `ml.g4dn.xlarge`, started `2026-05-14T20:18:04-0600`, ended `2026-05-14T22:29:31-0600`.
  - Input: `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-fg-202605142314/`.
  - Output: `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-fg-202605142314/`.
  - `aws s3 ls s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-fg-202605142314/ --recursive --summarize` -> `Total Objects: 46`, `Total Size: 18052144`.
  - Downloaded evidence:
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-sogs_compression_summary.json`
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-lod-meta.json`
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-training_metadata.json`
  - Bundle facts: `lodLevels=4`, `chunkFiles=4`, `lodTreeNodes=2`, `bundleSizeBytes=18050750`, compression ratio `18.1877`, LOD0 count `1320824` gaussians.
- Deployed viewer smoke:
  - URL tested:
    - `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev/md1-viewer?url=https%3A%2F%2Fspaceport-ml-processing-staging.s3.amazonaws.com%2Fcompressed%2Fmd1-e2e-vsfm-fg-202605142314%2Fsupersplat_bundle%2Flod-meta.json`
  - Command:
    - `MD1_VIEWER_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev MD1_LOD_URL=https://spaceport-ml-processing-staging.s3.amazonaws.com/compressed/md1-e2e-vsfm-fg-202605142314/supersplat_bundle/lod-meta.json MD1_EXPECT_CHUNK_SUBSTRING=md1-e2e-vsfm-fg-202605142314 node scripts/test-md1-production-viewer.mjs`
  - Technical load gate passed: strict no-header/no-footer/no-feedback assertions, LOD telemetry, chunk requests, and first frame.
  - Viewer smoke results:
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-viewer-results.json`
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-visual-gate-desktop.png`
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-visual-gate-mobile.png`
- Visual gate rejected the foreground retry:
  - Manual screenshots from default/front/side/top/back viewpoints remain skybox-dominant or dark and do not show an acceptable MD1 property baseline:
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-manual-default-iframe.png`
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-manual-front-tight.png`
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-manual-side.png` is represented by right/left side captures:
      `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-manual-right-side.png`,
      `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-manual-left-side.png`.
  - No-spend PLY diagnostics from `/tmp/md1-fg-model/splat.ply`:
    - `element vertex 1320824`.
    - `93.77%` of gaussians have `sigmoid(opacity) < 0.01`.
    - Position duplication is high: `5dp` duplicate fraction `0.9285`, `4dp` duplicate fraction `0.9520`, `3dp` duplicate fraction `0.9912`.
    - Alpha counts: `>0.02` -> `73565`, `>0.05` -> `54252`, `>0.12` -> `41212`, `>0.5` -> `20634`.
    - Scatter proof:
      `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-ply-scatter-alpha002-xy.png`,
      `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-ply-scatter-alpha002-xz.png`,
      `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-ply-scatter-alpha002-yz.png`.
  - Local alpha-filter experiment (`sigmoid(opacity) > 0.02`) produced `73565` gaussians and a compressed bundle, but it did not improve the visible model:
    - Local smoke result: `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-filter-alpha002-local-viewer-results.json`.
    - No-sky gate failure log after patching the smoke to inspect the right-side model region:
      `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-filter-alpha002-nosky-smoke-20260515T0521Z.log`.
- Proven code issue fixed locally:
  - The compressor had been inserting the bundled default skybox into every SuperSplat bundle even when the trained export produced no `background_skybox` sidecar. This can make a bad or invisible splat look non-empty in screenshots.
  - Patched `infrastructure/containers/compressor/compress.py` so `spaceport_bundle.json` uses a trained `background_skybox.*` sidecar when present, writes `"skybox": null` when absent, and only uses the bundled default skybox when `SOGS_BUNDLE_DEFAULT_SKYBOX=1`.
  - Patched `/md1-viewer` to honor `?skybox=none` and patched `resolveSogsViewerBundle` to preserve `spaceport_bundle.json` with `"skybox": null` instead of falling back to the site default.
  - Patched `web/scripts/test-md1-production-viewer.mjs` with `MD1_RUN_NO_SKY=1`, using a right-side model-region crop so the control panel cannot satisfy the visual gate.
- No-spend verification after the patch:
  - `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` -> `OK`.
  - `python3 -m py_compile infrastructure/containers/compressor/compress.py` -> passed.
  - `npm run build` in `web/` -> passed with pre-existing lint warnings only.
  - `git diff --check` -> passed.
- Current conclusion:
  - End-to-end 3DGS and compression handoffs are functioning, but the current MD1 foreground bundle is not accepted visually.
  - Do not relaunch full SfM.
  - Next step is to commit/push the skybox/no-sky gate fix, wait for exact-head workflows/container build, then run the smallest downstream retry that can produce a better model from the validated SfM reference. The likely next paid retry should be 3DGS-only with standard NerfStudio `splatfacto` from `s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap/`, because both `splatfacto-w-light` variants have now completed but failed visual acceptance.

### 2026-05-14T23:27:44-0600

- Commit/push:
  - Committed/pushed `2ebbe806381adf1965a6c94c34605b8f41438483` (`fix: gate md1 viewer without default skybox`).
  - The push initially proved a second viewer issue: the parent `/md1-viewer?skybox=none` suppressed its own resolved skybox param, but the embedded `supersplat-lod-viewer` still loaded `spaceport_bundle.json` and restored the bundle skybox.
  - Patched `web/public/supersplat-lod-viewer/index.html` so `skybox=none|off|0|null` disables both explicit and bundle-manifest skyboxes.
  - Patched `Md1ProductionViewer` to pass `skybox=none` through to the iframe when the route has an explicit no-skybox request or the resolved bundle has `skyboxUrl=null`.
- Exact-head workflow gate for `2ebbe806`:
  - `CDK Deploy` run `25901641141` -> `success`.
  - `Trigger ML Container Build` run `25901641155` -> `success`.
  - `Deploy Next.js to Cloudflare Pages` run `25901641139` -> `success`.
  - CodeBuild `spaceport-ml-containers:7ee179b6-25a6-4614-8694-e3847dadf172` -> `SUCCEEDED`; source `2ebbe806381adf1965a6c94c34605b8f41438483`; `CONTAINERS_TO_BUILD=compressor`; `BRANCH_SUFFIX=agent113647md1baselinee2e`.
  - Branch compressor image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor:agent113647md1baselinee2e` -> digest `sha256:dc4f599270807420f42aa859b9e93b9cac539c20acd5f73a47ca346cc3987d41`, pushed `2026-05-14T23:20:50-0600`.
  - Branch 3DGS image remains the proven `splatfacto-w-light` image digest `sha256:6b3b2492af7a268cfc5f233e87bdce51c47492ada4c3630f723114ffa464fd0c`.
- No-spend verification after the iframe no-sky patch:
  - `npm run build` in `web/` -> passed with pre-existing lint warnings only.
  - `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` -> `OK`.
  - `python3 -m py_compile infrastructure/containers/compressor/compress.py` -> passed.
  - `git diff --check` -> passed.
  - Local no-sky gate against the alpha-filtered foreground bundle now fails for the intended reason, proving the skybox suppression path works and the model itself is not visually acceptable:
    - `MD1_VIEWER_URL=http://127.0.0.1:3031 MD1_LOD_URL=http://127.0.0.1:8034/supersplat_bundle/lod-meta.json MD1_RUN_NO_SKY=1 node scripts/test-md1-production-viewer.mjs`
    - Failure log: `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-filter-alpha002-nosky-smoke-20260515T0529Z.log`.
- Current next step:
  - Commit/push the iframe no-sky follow-up patch and rerun exact-head workflows.
  - Then launch the next smallest paid retry from the validated SfM reference, not full SfM. Use 3DGS-only with `MODEL_VARIANT=splatfacto` unless a no-spend preflight finds a concrete blocker in the current branch image/export path.

### 2026-05-14T23:41:20-0600

- Commit/push:
  - Committed/pushed `e108490ef7f7422c6edec03a1699940f20b9d9ce` (`fix: pass md1 no-sky gate into lod viewer`).
  - Exact-head workflow gate for `e108490ef7f7422c6edec03a1699940f20b9d9ce`:
    - `CDK Deploy` run `25902014533` -> `success`.
    - `Deploy Next.js to Cloudflare Pages` run `25902014536` -> `success`.
    - Preview alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`.
    - Hash URL: `https://541dab62.v0-spaceport-website-preview2.pages.dev`.
- AWS / active job verification before launching another paid stage:
  - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - `aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --status-filter RUNNING` -> `[]`.
  - `aws sagemaker list-processing-jobs --status-equals InProgress` -> no processing jobs.
  - `aws sagemaker list-training-jobs --status-equals InProgress` -> one external job, `md1-full2157-ds4-r25-1778823276`; left untouched.
  - Branch 3DGS image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs:agent113647md1baselinee2e` -> digest `sha256:6b3b2492af7a268cfc5f233e87bdce51c47492ada4c3630f723114ffa464fd0c`, pushed `2026-05-14T13:37:06-0600`.
  - Branch compressor image: `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor:agent113647md1baselinee2e` -> digest `sha256:dc4f599270807420f42aa859b9e93b9cac539c20acd5f73a47ca346cc3987d41`, pushed `2026-05-14T23:20:50-0600`.
- Deployed no-sky validation:
  - Command:
    - `MD1_VIEWER_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev MD1_LOD_URL=https://spaceport-ml-processing-staging.s3.amazonaws.com/compressed/md1-e2e-vsfm-fg-202605142314/supersplat_bundle/lod-meta.json MD1_EXPECT_CHUNK_SUBSTRING=md1-e2e-vsfm-fg-202605142314 MD1_RUN_NO_SKY=1 node scripts/test-md1-production-viewer.mjs`
  - Result: expected failure at the stricter visual gate, proving the deployed iframe no-sky path works and the foreground model remains unacceptable without a skybox:
    - `desktop-nosky: no-sky model region did not show model pixels`.
  - Evidence:
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-deployed-nosky-smoke-20260515T0537Z.log`.
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-deployed-desktop.png`.
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-deployed-mobile.png`.
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-deployed-nosky.png`.
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-fg-202605142314-deployed-nosky-model.png`.
- New canonical downstream retry launched; no full SfM was relaunched:
  - Reason: both `splatfacto-w-light` variants reached 3DGS+compression but failed the no-sky/visual MD1 gate, so the smallest next paid retry is 3DGS-only with standard NerfStudio `splatfacto` from the validated SfM reference.
  - Payload: `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-202605150539-payload.json`.
  - Start proof: `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-202605150539-start.json`.
  - Command:
    - `aws stepfunctions start-execution --state-machine-arn arn:aws:states:us-west-2:975050048887:stateMachine:SpaceportMLPipeline-staging --name execution-md1-e2e-vsfm-splatfacto-202605150539 --input file://logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-202605150539-payload.json --region us-west-2`.
  - Execution ARN:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-202605150539`.
  - Job id/name: `md1-e2e-vsfm-splatfacto-202605150539`.
  - `MODEL_VARIANT`: `splatfacto`.
  - COLMAP input:
    - `s3://spaceport-ml-processing-staging/manual-validations/md1p24e752k-1776314974/colmap/`.
  - 3DGS output:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/`.
  - Compression output:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-202605150539/`.
  - SageMaker training job:
    - `md1-e2e-vsfm-splatfacto-202605150539-3dgs`.
    - Initial status: `InProgress` / `Pending` on `ml.g5.2xlarge`, `MaxRuntimeInSeconds=14400`.
  - Snapshots:
    - `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-202605150539-20260515T0540Z.json`.
    - `logs/md1-baseline-e2e/stepfunctions-history-reverse-md1-e2e-vsfm-splatfacto-202605150539-20260515T0540Z.json`.
    - `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-202605150539-3dgs-20260515T0540Z.json`.
- Follow-up poll:
  - SageMaker training job `md1-e2e-vsfm-splatfacto-202605150539-3dgs` -> `InProgress` / `Training`; `TrainingStartTime=2026-05-14T23:39:57-0600`; no failure reason.
  - CloudWatch log stream:
    - `/aws/sagemaker/TrainingJobs` / `md1-e2e-vsfm-splatfacto-202605150539-3dgs/algo-1-1778823597`.
  - Startup log snapshots:
    - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-training-start-20260515T0547Z.json`.
    - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-training-start-20260515T0547Z.txt`.
    - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-training-start-filtered-20260515T0552Z.txt`.
  - Log proof so far:
    - `MODEL_VARIANT=splatfacto` override was applied.
    - COLMAP validation passed: `Cameras: 1`, `Images registered: 2157`, `Image files: 2157`, `3D points: 1312804`.
    - COLMAP TXT-to-BIN conversion completed successfully.
    - The job is still in the conversion/training startup phase; S3 3DGS output remains empty until SageMaker job end.
- Next step:
  - Continue monitoring `md1-e2e-vsfm-splatfacto-202605150539-3dgs` through terminal status.
  - If it fails, capture the exact SageMaker/CloudWatch error and patch only that proven issue.
  - If it completes, validate S3 artifact handoff, compression, gaussian count/file size, then smoke and visually gate `/md1-viewer` with no skybox before accepting the baseline.

### 2026-05-15T00:02:39-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `eb166a12832dedafaef9bdc627d174d17bf04f76`.
  - Local dirty files not staged: top-level generated viewer screenshots/results only (`logs/md1-production-viewer-desktop.png`, `logs/md1-production-viewer-results.json`).
  - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Exact-head GitHub workflow: `CDK Deploy` run `25902702055` @ `eb166a12832dedafaef9bdc627d174d17bf04f76` -> `success`.
- Current active AWS state:
  - Running Step Functions executions:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-202605150539`.
  - InProgress training jobs:
    - This run: `md1-e2e-vsfm-splatfacto-202605150539-3dgs` -> `InProgress` / `Training`.
    - External/not owned by this automation: `md1-full2157-ds4-r25-1778823276` -> `InProgress` / `Training`; left untouched.
  - InProgress processing jobs: none.
  - 3DGS output prefix is still empty as expected until SageMaker job end:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/` -> `Total Objects: 0`.
  - Compression output prefix is still empty because compression has not started:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-202605150539/` -> `Total Objects: 0`.
- SageMaker details:
  - Training job `md1-e2e-vsfm-splatfacto-202605150539-3dgs` remains `InProgress` / `Training`.
  - `TrainingStartTime=2026-05-14T23:39:57-0600`.
  - `TrainingTimeInSeconds=1388` at the poll.
  - No failure reason.
- CloudWatch log snapshot:
  - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-cloudwatch-20260515T0602Z.json`.
  - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-cloudwatch-20260515T0602Z.txt`.
  - New proof since the previous poll:
    - `transforms.json` validation passed, file size `1907101` bytes.
    - `ns-train` command accepted and is running:
      `ns-train splatfacto --data /tmp/nerfstudio_training/converted_data --output-dir /tmp/nerfstudio_training --vis tensorboard --max_num_iterations 30000 --pipeline.model.sh_degree 3 --logging.steps_per_log 100 --pipeline.model.max-gauss-ratio 10.0`.
    - Training subprocess captures stdout/stderr, so iteration logs may not stream until `ns-train` exits.
- Next step:
  - Continue polling SageMaker status as the live gate. If it fails, capture the exact stdout/stderr from the final CloudWatch log and patch the smallest proven issue. If it completes, validate the S3 3DGS artifact and compression handoff before visual acceptance.

### 2026-05-15T00:33:10-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `eb166a12832dedafaef9bdc627d174d17bf04f76`.
  - Local dirty files not staged: `logs/md1-baseline-e2e/STATE.md`, the 00:02/00:33 poll snapshots, and top-level generated viewer screenshots/results.
  - `aws sts get-caller-identity` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Exact-head GitHub workflow: `CDK Deploy` run `25902702055` @ `eb166a12832dedafaef9bdc627d174d17bf04f76` -> `success`.
- Current active AWS state:
  - Running Step Functions executions:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-202605150539`.
  - InProgress training jobs:
    - This run: `md1-e2e-vsfm-splatfacto-202605150539-3dgs` -> `InProgress` / `Training`.
    - External/not owned by this automation: `md1-full2157-ds4-r25-1778823276` -> `InProgress` / `Training`; left untouched.
  - InProgress processing jobs: none.
  - 3DGS output prefix remains empty as expected until SageMaker job end:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/` -> `Total Objects: 0`.
  - Compression output prefix remains empty because compression has not started:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-202605150539/` -> `Total Objects: 0`.
- SageMaker details:
  - Training job `md1-e2e-vsfm-splatfacto-202605150539-3dgs` remains `InProgress` / `Training`.
  - `TrainingStartTime=2026-05-14T23:39:57-0600`.
  - `TrainingTimeInSeconds=3217` at the poll.
  - No failure reason.
  - Snapshot:
    - `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-202605150539-3dgs-20260515T0633Z.json`.
- Step Functions snapshot:
  - `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-202605150539-20260515T0633Z.json`.
- CloudWatch log snapshot:
  - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-cloudwatch-20260515T0633Z.json`.
  - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-cloudwatch-20260515T0633Z.txt`.
  - Latest meaningful log line remains the accepted `ns-train splatfacto ... --pipeline.model.max-gauss-ratio 10.0` command at `2026-05-15T05:50:24Z`; no streamed iteration logs yet because the wrapper captures subprocess output.
- Next step:
  - Continue polling SageMaker status as the live gate. If it fails, capture final CloudWatch stdout/stderr and patch only the proven issue. If it completes, validate model artifact/S3 handoff, monitor compression, then run the no-sky visual gate before accepting the viewer.

### 2026-05-15T01:33:12-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `eb166a12832dedafaef9bdc627d174d17bf04f76`.
  - Local dirty files not staged: `logs/md1-baseline-e2e/STATE.md`, prior/current poll snapshots, and top-level generated viewer screenshots/results.
  - `aws sts get-caller-identity --region us-west-2` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Exact-head GitHub workflow: `CDK Deploy` run `25902702055` @ `eb166a12832dedafaef9bdc627d174d17bf04f76` -> `success`.
- Current active AWS state:
  - Running Step Functions executions:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-202605150539`.
  - InProgress training jobs:
    - This run: `md1-e2e-vsfm-splatfacto-202605150539-3dgs` -> `InProgress` / `Training`.
    - External/not owned by this automation: `md1-full2157-ds4-r25-1778823276` -> `InProgress` / `Training`; left untouched.
  - InProgress processing jobs: none.
  - 3DGS output prefix remains empty as expected until SageMaker job end:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/` -> `Total Objects: 0`.
  - Compression output prefix remains empty because compression has not started:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-202605150539/` -> `Total Objects: 0`.
- SageMaker details:
  - Training job `md1-e2e-vsfm-splatfacto-202605150539-3dgs` remains `InProgress` / `Training`.
  - `TrainingStartTime=2026-05-14T23:39:57-0600`.
  - `TrainingTimeInSeconds=6866` at the poll.
  - No failure reason.
  - Snapshot:
    - `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-202605150539-3dgs-20260515T0733Z.json`.
- Step Functions snapshot:
  - `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-202605150539-20260515T0733Z.json`.
- CloudWatch log snapshot:
  - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-cloudwatch-20260515T0733Z.json`.
  - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-cloudwatch-20260515T0733Z.txt`.
  - Latest meaningful log line remains the accepted `ns-train splatfacto ... --pipeline.model.max-gauss-ratio 10.0` command at `2026-05-15T05:50:24Z`; no streamed iteration logs yet because the wrapper captures subprocess output.
- S3 listing snapshots:
  - `logs/md1-baseline-e2e/s3-3dgs-md1-e2e-vsfm-splatfacto-202605150539-20260515T0733Z.txt`.
  - `logs/md1-baseline-e2e/s3-compressed-md1-e2e-vsfm-splatfacto-202605150539-20260515T0733Z.txt`.
- Next step:
  - Continue polling SageMaker status. If it fails or times out near `MaxRuntimeInSeconds=14400`, capture the final CloudWatch stdout/stderr and patch only the proven issue. If it completes, validate model artifact/S3 handoff, monitor compression, then run the no-sky visual gate before accepting the viewer.

### 2026-05-15T02:03:15-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `eb166a12832dedafaef9bdc627d174d17bf04f76`.
  - Local dirty files not staged: `logs/md1-baseline-e2e/STATE.md`, prior/current poll snapshots, and top-level generated viewer screenshots/results.
  - `aws sts get-caller-identity --region us-west-2` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Exact-head GitHub workflow: `CDK Deploy` run `25902702055` @ `eb166a12832dedafaef9bdc627d174d17bf04f76` -> `success`.
- Current active AWS state:
  - Running Step Functions executions:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-202605150539`.
  - InProgress training jobs:
    - This run: `md1-e2e-vsfm-splatfacto-202605150539-3dgs` -> `InProgress` / `Training`.
    - External/not owned by this automation: `md1-full2157-ds4-r25-1778823276` -> `InProgress` / `Training`; left untouched.
  - InProgress processing jobs: none.
  - 3DGS output prefix remains empty as expected until SageMaker job end:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/` -> `Total Objects: 0`.
  - Compression output prefix remains empty because compression has not started:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-202605150539/` -> `Total Objects: 0`.
- SageMaker details:
  - Training job `md1-e2e-vsfm-splatfacto-202605150539-3dgs` remains `InProgress` / `Training`.
  - `TrainingStartTime=2026-05-14T23:39:57-0600`.
  - `TrainingTimeInSeconds=8649` at the poll.
  - No failure reason.
  - Snapshot:
    - `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-202605150539-3dgs-20260515T0803Z.json`.
- Step Functions snapshot:
  - `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-202605150539-20260515T0803Z.json`.
- CloudWatch log snapshot:
  - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-cloudwatch-20260515T0803Z.json`.
  - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-cloudwatch-20260515T0803Z.txt`.
  - Latest meaningful log line remains the accepted `ns-train splatfacto ... --pipeline.model.max-gauss-ratio 10.0` command at `2026-05-15T05:50:24Z`; no streamed iteration logs yet because the wrapper captures subprocess output.
- S3 listing snapshots:
  - `logs/md1-baseline-e2e/s3-3dgs-md1-e2e-vsfm-splatfacto-202605150539-20260515T0803Z.txt`.
  - `logs/md1-baseline-e2e/s3-compressed-md1-e2e-vsfm-splatfacto-202605150539-20260515T0803Z.txt`.
- Next step:
  - Continue polling SageMaker status. The job has used about 60% of its 14400s runtime budget; if it fails or times out, capture the final CloudWatch stdout/stderr and patch only the proven issue. If it completes, validate model artifact/S3 handoff, monitor compression, then run the no-sky visual gate before accepting the viewer.

### 2026-05-15T02:33:18-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `eb166a12832dedafaef9bdc627d174d17bf04f76`.
  - Local dirty files not staged: `logs/md1-baseline-e2e/STATE.md`, prior/current poll snapshots, and top-level generated viewer screenshots/results.
  - `aws sts get-caller-identity --region us-west-2` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Exact-head GitHub workflow: `CDK Deploy` run `25902702055` @ `eb166a12832dedafaef9bdc627d174d17bf04f76` -> `success`.
- Current active AWS state:
  - Running Step Functions executions:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-202605150539`.
  - InProgress training jobs:
    - External/not owned by this automation: `md1-full2157-ds4-r25-1778823276` -> `InProgress` / `Training`; left untouched.
  - InProgress processing jobs:
    - This run: `md1-e2e-vsfm-splatfacto-202605150539-compression` -> `InProgress`.
- Standard splatfacto 3DGS terminal state:
  - Training job `md1-e2e-vsfm-splatfacto-202605150539-3dgs` -> `Completed`.
  - `TrainingStartTime=2026-05-14T23:39:57-0600`.
  - `TrainingEndTime=2026-05-15T02:13:20-0600`.
  - Training/billable time: `9203s` on `ml.g5.2xlarge`.
  - Model artifact:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/md1-e2e-vsfm-splatfacto-202605150539-3dgs/output/model.tar.gz`.
  - 3DGS S3 listing:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/` -> `Total Objects: 1`, `Total Size: 64488068`.
  - SageMaker snapshot:
    - `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-202605150539-3dgs-20260515T0833Z.json`.
  - Final training log snapshots:
    - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-full-log-20260515T0833Z.json`.
    - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-full-log-20260515T0833Z.txt`.
    - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-final-log-20260515T0833Z.json`.
    - `logs/md1-baseline-e2e/3dgs-md1-e2e-vsfm-splatfacto-202605150539-final-log-20260515T0833Z.txt`.
  - Final log proof:
    - `Training Finished` at 30000 iterations.
    - `Model export completed successfully`.
    - PLY file `splat.ply` size `310.3 MB`.
    - Metadata `model_variant: splatfacto`, `enable_bg_model: False`, `enable_alpha_loss: False`, `enable_robust_mask: False`, `max_iterations: 30000`.
- Compression is now active:
  - Processing job: `md1-e2e-vsfm-splatfacto-202605150539-compression`.
  - Status: `InProgress`.
  - Instance/runtime: `ml.g4dn.xlarge`, `MaxRuntimeInSeconds=86400`.
  - Started: `2026-05-15T02:14:08-0600`.
  - Input:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/`.
  - Output:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-202605150539/`.
  - Compression S3 output remains empty as expected until job end (`S3UploadMode=EndOfJob`):
    - `Total Objects: 0`, `Total Size: 0`.
  - Processing snapshot:
    - `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-202605150539-compression-20260515T0833Z.json`.
  - Processing log stream:
    - `/aws/sagemaker/ProcessingJobs` / `md1-e2e-vsfm-splatfacto-202605150539-compression/algo-1-1778832848`.
  - Compression log proof:
    - `splat-transform v1.10.2`.
    - Extracted `model.tar.gz`.
    - Selected PLY source `/opt/ml/processing/input/__extracted_archives/00-model-tar/splat.ply`.
    - Supporting file `training_metadata.json` discovered.
    - Running `splat-transform -w -g cpu .../splat.ply .../generated_bundle/meta.json`.
  - Compression log snapshots:
    - `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-202605150539-log-streams-20260515T0833Z.json`.
    - `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-202605150539-cloudwatch-20260515T0833Z.json`.
    - `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-202605150539-cloudwatch-20260515T0833Z.txt`.
- Step Functions snapshot:
  - `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-202605150539-20260515T0833Z.json`.
- S3 listing snapshots:
  - `logs/md1-baseline-e2e/s3-3dgs-md1-e2e-vsfm-splatfacto-202605150539-20260515T0833Z.txt`.
  - `logs/md1-baseline-e2e/s3-compressed-md1-e2e-vsfm-splatfacto-202605150539-20260515T0833Z.txt`.
- Next step:
  - Continue monitoring compression. If it completes, validate bundle files/summary, gaussian count/file size, and smoke the deployed `/md1-viewer` with no skybox against the new standard-splatfacto manifest before accepting the baseline. If compression fails, capture exact processing logs and patch only that proven failure.

### 2026-05-15T06:06:45-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022`.
  - Local dirty/untracked files remain poll artifacts and existing viewer smoke outputs; no new code changes.
  - `aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Exact-head GitHub workflow: `CDK Deploy` run `25911519106` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022` -> `success`.
- Current active AWS state:
  - Running Step Functions executions:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-cfix-202605150946`.
  - InProgress processing jobs:
    - This run: `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression` -> `InProgress`.
  - InProgress training jobs:
    - External/not owned by this automation: `md1-worst447-ds1500-r27-1778846018` -> `InProgress`; left untouched.
- Compression-only retry status:
  - Step Functions execution:
    - `status=RUNNING`.
    - Snapshot `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1206Z.json`.
  - SageMaker processing:
    - `ProcessingJobName=md1-e2e-vsfm-splatfacto-cfix-202605150946-compression`.
    - `ProcessingJobStatus=InProgress`.
    - `ProcessingStartTime=2026-05-15T03:47:07.043000-0600`.
    - `ProcessingEndTime=null`.
    - `FailureReason=null`.
    - `ImageUri=975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor:agent113647md1baselinee2e`.
    - `InstanceType=ml.g4dn.xlarge`.
    - Snapshot `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-compression-20260515T1205Z.json`.
  - Input:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/`.
  - Output:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/`.
    - Current S3 listing remains empty as expected until EndOfJob upload: `Total Objects: 0`, `Total Size: 0 Bytes`.
    - S3 listing snapshot `logs/md1-baseline-e2e/s3-compressed-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1205Z.txt`.
  - CloudWatch log:
    - Log stream `/aws/sagemaker/ProcessingJobs` / `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression/algo-1-1778838426`.
    - Snapshot `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T1205Z.json`.
    - Text `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T1205Z.txt`.
    - Progress changed materially: the first single-bundle `splat-transform -w -g cpu .../splat.ply .../generated_bundle/meta.json` passed the old 3600s timeout barrier, LOD input generation completed through `lod3.ply` (`39365` gaussians loaded, `done in 142.775569473s`), and the job is now running the LOD bundle command:
      - `splat-transform -w -g cpu -C 1024 -X 32 /opt/ml/processing/input/__extracted_archives/00-model-tar/splat.ply -l 0 /tmp/sogs-work-yalufyvo/lod_inputs/lod1.ply -l 1 /tmp/sogs-work-yalufyvo/lod_inputs/lod2.ply -l 2 /tmp/sogs-work-yalufyvo/lod_inputs/lod3.ply -l 3 /tmp/sogs-work-yalufyvo/generated_bundle/lod-meta.json`.
- Commands run this poll:
  - `aws sagemaker describe-processing-job --processing-job-name md1-e2e-vsfm-splatfacto-cfix-202605150946-compression --region us-west-2 --output json`.
  - `aws logs get-log-events --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name md1-e2e-vsfm-splatfacto-cfix-202605150946-compression/algo-1-1778838426 --region us-west-2 --start-from-head --output json`.
  - `aws s3 ls s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/ --recursive --summarize --human-readable --region us-west-2`.
  - `aws stepfunctions describe-execution --execution-arn arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-cfix-202605150946 --region us-west-2 --output json`.
  - `gh run list --branch agent-113647-md1-baseline-e2e --limit 8 --json databaseId,workflowName,headSha,status,conclusion,createdAt,url`.
- Next step:
  - Continue monitoring this compression-only retry. No duplicate SfM, 3DGS, or compression job is warranted. If the LOD transform completes, validate the uploaded bundle, gaussian counts/file sizes, and the deployed no-sky viewer before accepting the MD1 baseline.

### 2026-05-15T07:04:44-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022`.
  - Local dirty/untracked files remain poll artifacts and existing viewer smoke outputs; no code changes.
  - `aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Exact-head GitHub workflow: `CDK Deploy` run `25911519106` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022` -> `success`.
- Current active AWS state:
  - Running Step Functions executions:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-cfix-202605150946`.
  - InProgress processing jobs:
    - This run: `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression` -> `InProgress`.
  - InProgress training jobs:
    - External/not owned by this automation: `md1-worst447-ds1500-r27-1778846018` -> `InProgress`; left untouched.
- Compression-only retry status:
  - Step Functions execution:
    - `status=RUNNING`.
    - Snapshot `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1304Z.json`.
  - SageMaker processing:
    - `ProcessingJobName=md1-e2e-vsfm-splatfacto-cfix-202605150946-compression`.
    - `ProcessingJobStatus=InProgress`.
    - `ProcessingStartTime=2026-05-15T03:47:07.043000-0600`.
    - `ProcessingEndTime=null`.
    - `FailureReason=null`.
    - `ImageUri=975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor:agent113647md1baselinee2e`.
    - `InstanceType=ml.g4dn.xlarge`.
    - Snapshot `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-compression-20260515T1304Z.json`.
  - Input:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/`.
  - Output:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/`.
    - Current S3 listing remains empty as expected until EndOfJob upload: `Total Objects: 0`, `Total Size: 0 Bytes`.
    - S3 listing snapshot `logs/md1-baseline-e2e/s3-compressed-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1304Z.txt`.
  - CloudWatch log:
    - Log stream `/aws/sagemaker/ProcessingJobs` / `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression/algo-1-1778838426`.
    - Snapshot `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T1304Z.json`.
    - Text `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T1304Z.txt`.
    - Latest visible command remains the LOD bundle transform:
      - `splat-transform -w -g cpu -C 1024 -X 32 /opt/ml/processing/input/__extracted_archives/00-model-tar/splat.ply -l 0 /tmp/sogs-work-yalufyvo/lod_inputs/lod1.ply -l 1 /tmp/sogs-work-yalufyvo/lod_inputs/lod2.ply -l 2 /tmp/sogs-work-yalufyvo/lod_inputs/lod3.ply -l 3 /tmp/sogs-work-yalufyvo/generated_bundle/lod-meta.json`.
    - Important progress still holds: the first single-bundle transform completed in `6499.789827272s`, which proves the 14400s timeout fix crossed the prior 3600s failure point; no OOM, timeout, or failure is visible.
- Commands run this poll:
  - `aws sagemaker describe-processing-job --processing-job-name md1-e2e-vsfm-splatfacto-cfix-202605150946-compression --region us-west-2 --output json`.
  - `aws logs get-log-events --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name md1-e2e-vsfm-splatfacto-cfix-202605150946-compression/algo-1-1778838426 --region us-west-2 --start-from-head --output json`.
  - `aws s3 ls s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/ --recursive --summarize --human-readable --region us-west-2`.
  - `aws stepfunctions describe-execution --execution-arn arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-cfix-202605150946 --region us-west-2 --output json`.
  - `gh run list --branch agent-113647-md1-baseline-e2e --limit 8 --json databaseId,workflowName,headSha,status,conclusion,createdAt,url`.
- Next step:
  - Continue monitoring this compression-only retry. No duplicate SfM, 3DGS, or compression job is warranted. If the LOD transform completes, validate the uploaded bundle, gaussian counts/file sizes, and the deployed no-sky viewer before accepting the MD1 baseline.

### 2026-05-15T04:03:27-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022`.
  - Dirty/untracked local files are poll artifacts and existing viewer smoke outputs; no code changes.
  - `aws sts get-caller-identity --region us-west-2` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Exact-head GitHub workflow: `CDK Deploy` run `25911519106` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022` -> `success`.
- Current active AWS state:
  - Running Step Functions executions:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-cfix-202605150946`.
  - InProgress processing jobs:
    - This run: `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression` -> `InProgress`.
  - InProgress training jobs:
    - External/not owned by this automation: `md1-r0vissent-v5relax-1778837840-tile-04` -> `InProgress` / `Training`; left untouched.
- Compression-only retry status:
  - Step Functions execution:
    - `status=RUNNING`.
    - Snapshot `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1003Z.json`.
  - SageMaker processing:
    - `ProcessingJobName=md1-e2e-vsfm-splatfacto-cfix-202605150946-compression`.
    - `ProcessingJobStatus=InProgress`.
    - `ProcessingStartTime=2026-05-15T03:47:07.043000-0600`.
    - `ProcessingEndTime=null`.
    - `FailureReason=null`.
    - `InstanceType=ml.g4dn.xlarge`.
    - Snapshot `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-compression-20260515T1003Z.json`.
  - Input:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/`.
  - Output:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/`.
    - Current S3 listing: `Total Objects: 0`, `Total Size: 0 Bytes`, expected until EndOfJob upload.
    - S3 listing snapshot `logs/md1-baseline-e2e/s3-compressed-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1003Z.txt`.
  - CloudWatch log:
    - Log stream `/aws/sagemaker/ProcessingJobs` / `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression/algo-1-1778838426`.
    - Snapshot `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T1003Z.json`.
    - Text `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T1003Z.txt`.
    - Latest line remains the first long-running command: `splat-transform -w -g cpu .../splat.ply .../generated_bundle/meta.json`.
    - The patched timeout is still proven active in the same log stream: `transform_timeout=14400s, lod_transform_timeout=14400s`.
- Next step:
  - Continue waiting; the retry has only been inside the patched 14400s single-bundle transform for about 16 minutes. Do not launch any duplicate compression or training job.

### 2026-05-15T04:33:26-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022`.
  - Dirty/untracked local files are poll artifacts and existing viewer smoke outputs; no code changes.
  - `aws sts get-caller-identity --region us-west-2` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Exact-head GitHub workflow: `CDK Deploy` run `25911519106` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022` -> `success`.
- Current active AWS state:
  - Running Step Functions executions:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-cfix-202605150946`.
  - InProgress processing jobs:
    - This run: `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression` -> `InProgress`.
  - InProgress training jobs:
    - External/not owned by this automation: `md1-worst447-ds1000-r26-1778840348` -> `InProgress` / `Training`; left untouched.
- Compression-only retry status:
  - Step Functions execution:
    - `status=RUNNING`.
    - Snapshot `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1033Z.json`.
  - SageMaker processing:
    - `ProcessingJobName=md1-e2e-vsfm-splatfacto-cfix-202605150946-compression`.
    - `ProcessingJobStatus=InProgress`.
    - `ProcessingStartTime=2026-05-15T03:47:07.043000-0600`.
    - `ProcessingEndTime=null`.
    - `FailureReason=null`.
    - `InstanceType=ml.g4dn.xlarge`.
    - Snapshot `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-compression-20260515T1033Z.json`.
  - Input:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/`.
  - Output:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/`.
    - Current S3 listing remains empty as expected until EndOfJob upload: `Total Objects: 0`, `Total Size: 0 Bytes`.
    - S3 listing snapshot `logs/md1-baseline-e2e/s3-compressed-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1033Z.txt`.
  - CloudWatch log:
    - Log stream `/aws/sagemaker/ProcessingJobs` / `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression/algo-1-1778838426`.
    - Snapshot `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T1033Z.json`.
    - Text `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T1033Z.txt`.
    - Latest line remains the first long-running command: `splat-transform -w -g cpu .../splat.ply .../generated_bundle/meta.json`.
    - The patched timeout remains active: `transform_timeout=14400s, lod_transform_timeout=14400s`.
- Next step:
  - Continue waiting; the retry has been inside the patched 14400s single-bundle transform for about 46 minutes. Do not launch any duplicate compression or training job.

### 2026-05-15T05:03:38-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022`.
  - Dirty/untracked local files are poll artifacts and existing viewer smoke outputs; no code changes.
  - `aws sts get-caller-identity --region us-west-2` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Exact-head GitHub workflow: `CDK Deploy` run `25911519106` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022` -> `success`.
- Current active AWS state:
  - Running Step Functions executions:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-cfix-202605150946`.
  - InProgress processing jobs:
    - This run: `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression` -> `InProgress`.
  - InProgress training jobs:
    - External/not owned by this automation: `md1-worst447-ds1000-r26-1778840348` -> `InProgress` / `Training`; left untouched.
- Compression-only retry status:
  - Step Functions execution:
    - `status=RUNNING`.
    - Snapshot `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1103Z.json`.
  - SageMaker processing:
    - `ProcessingJobName=md1-e2e-vsfm-splatfacto-cfix-202605150946-compression`.
    - `ProcessingJobStatus=InProgress`.
    - `ProcessingStartTime=2026-05-15T03:47:07.043000-0600`.
    - `ProcessingEndTime=null`.
    - `FailureReason=null`.
    - `InstanceType=ml.g4dn.xlarge`.
    - Snapshot `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-compression-20260515T1103Z.json`.
  - Input:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/`.
  - Output:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/`.
    - Current S3 listing remains empty as expected until EndOfJob upload: `Total Objects: 0`, `Total Size: 0 Bytes`.
    - S3 listing snapshot `logs/md1-baseline-e2e/s3-compressed-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1103Z.txt`.
  - CloudWatch log:
    - Log stream `/aws/sagemaker/ProcessingJobs` / `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression/algo-1-1778838426`.
    - Snapshot `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T1103Z.json`.
    - Text `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T1103Z.txt`.
    - Latest line remains the first long-running command: `splat-transform -w -g cpu .../splat.ply .../generated_bundle/meta.json`.
    - The patched timeout remains active: `transform_timeout=14400s, lod_transform_timeout=14400s`.
- Next step:
  - Continue waiting; the retry has been inside the patched 14400s single-bundle transform for about 76 minutes. Do not launch any duplicate compression or training job.

### 2026-05-15T05:33:36-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022`.
  - Dirty/untracked local files are poll artifacts and existing viewer smoke outputs; no code changes.
  - `aws sts get-caller-identity --region us-west-2` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Exact-head GitHub workflow: `CDK Deploy` run `25911519106` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022` -> `success`.
- Current active AWS state:
  - Running Step Functions executions:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-cfix-202605150946`.
  - InProgress processing jobs:
    - This run: `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression` -> `InProgress`.
  - InProgress training jobs:
    - None returned by the poll.
- Compression-only retry status:
  - Step Functions execution:
    - `status=RUNNING`.
    - Snapshot `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1133Z.json`.
  - SageMaker processing:
    - `ProcessingJobName=md1-e2e-vsfm-splatfacto-cfix-202605150946-compression`.
    - `ProcessingJobStatus=InProgress`.
    - `ProcessingStartTime=2026-05-15T03:47:07.043000-0600`.
    - `ProcessingEndTime=null`.
    - `FailureReason=null`.
    - `InstanceType=ml.g4dn.xlarge`.
    - Snapshot `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-compression-20260515T1133Z.json`.
  - Input:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/`.
  - Output:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/`.
    - Current S3 listing remains empty as expected until EndOfJob upload: `Total Objects: 0`, `Total Size: 0 Bytes`.
    - S3 listing snapshot `logs/md1-baseline-e2e/s3-compressed-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1133Z.txt`.
  - CloudWatch log:
    - Log stream `/aws/sagemaker/ProcessingJobs` / `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression/algo-1-1778838426`.
    - Snapshot `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T1133Z.json`.
    - Text `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T1133Z.txt`.
    - Latest line remains the first long-running command: `splat-transform -w -g cpu .../splat.ply .../generated_bundle/meta.json`.
    - The patched timeout remains active: `transform_timeout=14400s, lod_transform_timeout=14400s`.
- Next step:
  - Continue waiting; the retry has been inside the patched 14400s single-bundle transform for about 106 minutes. Do not launch any duplicate compression or training job.

### 2026-05-15T03:33:23-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `eb166a12832dedafaef9bdc627d174d17bf04f76`.
  - `aws sts get-caller-identity --region us-west-2` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Exact-head GitHub workflow: `CDK Deploy` run `25902702055` @ `eb166a12832dedafaef9bdc627d174d17bf04f76` -> `success`.
- Current active AWS state:
  - Running Step Functions executions: none.
  - InProgress training jobs: none returned by the poll.
  - InProgress processing jobs: none returned by the poll.
- Standard splatfacto compression terminal state:
  - Step Functions execution:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-202605150539`.
    - `describe-execution` shows `status=SUCCEEDED`, but this is the state machine's `NotifyError` path, not a completed pipeline.
  - Processing job:
    - `md1-e2e-vsfm-splatfacto-202605150539-compression` -> `Failed`.
    - `ProcessingStartTime=2026-05-15T02:14:08-0600`.
    - `ProcessingEndTime=2026-05-15T03:14:48-0600`.
    - `FailureReason=AlgorithmError: , exit code: 1`.
  - Exact CloudWatch failure:
    - `Compression job failed: Command '['splat-transform', '-w', '-g', 'cpu', '/opt/ml/processing/input/__extracted_archives/00-model-tar/splat.ply', '/tmp/sogs-work-kjqt837e/generated_bundle/meta.json']' timed out after 3600 seconds`.
  - Compression output remains empty:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-202605150539/` -> `Total Objects: 0`, `Total Size: 0`.
  - Failure snapshots:
    - `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-202605150539-20260515T0933Z.json`.
    - `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-202605150539-compression-20260515T0933Z.json`.
    - `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-202605150539-cloudwatch-20260515T0933Z.json`.
    - `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-202605150539-cloudwatch-20260515T0933Z.txt`.
    - `logs/md1-baseline-e2e/s3-compressed-md1-e2e-vsfm-splatfacto-202605150539-20260515T0933Z.txt`.
    - `logs/md1-baseline-e2e/stepfunctions-history-reverse-md1-e2e-vsfm-splatfacto-202605150539-20260515T0933Z.json`.
- Patch applied for the proven failure:
  - `infrastructure/containers/compressor/compress.py` now defaults `SOGS_TRANSFORM_TIMEOUT_SECONDS` and `SOGS_LOD_TRANSFORM_TIMEOUT_SECONDS` to `14400`, logs the configured values, and passes them to single-bundle, decimation, and LOD `splat-transform` invocations.
  - `tests/unit/test_sogs_supersplat_bundle.py` now covers the long-running default, independent env overrides, and command timeout propagation.
  - The Step Functions compression task does not currently pass arbitrary timeout env vars, so the compressor default was changed instead of relying on payload-only configuration.
- Local validation:
  - `python3 -m py_compile infrastructure/containers/compressor/compress.py` -> pass.
  - `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` -> pass (`Ran 7 tests`).
  - `git diff --check` -> pass.
- Next step:
  - Commit and push the compressor timeout fix, rely on the automatic ML container build from the push, watch exact-head workflows/build evidence, then launch the smallest retry: compression-only from `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/` to a fresh compressed prefix.

### 2026-05-15T03:48:00-0600

- Commit/push after patch:
  - Commit: `5682b21363c305626706e4b40edcff49a7bd1fb2` (`fix: extend md1 compression transform timeout`).
  - Push: `git push origin agent-113647-md1-baseline-e2e` -> `eb166a12..5682b213`.
- Exact-head workflow/build verification:
  - `gh run watch 25911077932 --exit-status` -> `CDK Deploy` succeeded at head `5682b21363c305626706e4b40edcff49a7bd1fb2`.
  - `gh run watch 25911077935 --exit-status` -> `Trigger ML Container Build` succeeded at head `5682b21363c305626706e4b40edcff49a7bd1fb2`.
  - `aws codebuild batch-get-builds --ids spaceport-ml-containers:d4691f87-0684-47fe-a235-3fa7c5c6e98d --region us-west-2`:
    - Build number `698`.
    - `sourceVersion=5682b21363c305626706e4b40edcff49a7bd1fb2`.
    - `buildStatus=SUCCEEDED`.
    - Build phase `BUILD` duration `189s`.
  - `aws ecr describe-images --repository-name spaceport/compressor --image-ids imageTag=agent113647md1baselinee2e --region us-west-2`:
    - Digest `sha256:c667899d7e844083e8d50b04329edd3841bbfb26f8876c917ade78be8f27d603`.
    - Pushed `2026-05-15T03:44:31.581000-0600`.
    - Tags: `agent113647md1baselinee2e`, `latest`.
- Pre-retry cost gate:
  - `aws stepfunctions list-executions ... --status-filter RUNNING` -> none.
  - `aws sagemaker list-processing-jobs --status-equals InProgress` -> none.
  - `aws sagemaker list-training-jobs --status-equals InProgress` -> one external job `md1-r0vissent-v5relax-1778837840-tile-04`; left untouched because it is not owned by this automation.
- Smallest-stage retry launched:
  - Job name/id: `md1-e2e-vsfm-splatfacto-cfix-202605150946`.
  - Pipeline step: `compression`.
  - Step Functions execution:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-cfix-202605150946`.
  - Processing job:
    - `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression`.
  - Input:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/`.
  - Output:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/`.
  - Image:
    - `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor:agent113647md1baselinee2e`.
  - Payload/start proof:
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-cfix-202605150946-payload.json`.
    - `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-cfix-202605150946-start.json`.
- Current retry status:
  - Step Functions `describe-execution`:
    - `status=RUNNING`.
    - Snapshot `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T0946Z.json`.
  - SageMaker processing `describe-processing-job`:
    - `ProcessingJobStatus=InProgress`.
    - Snapshot `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-compression-20260515T0946Z.json`.
    - Poll snapshot `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-compression-20260515T0947Z.json`.
  - Log stream:
    - `/aws/sagemaker/ProcessingJobs` / `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression/algo-1-1778838426`.
    - Log stream snapshot `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-log-streams-20260515T0947Z.json`.
    - CloudWatch log snapshot `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T0948Z.json`.
    - Text log `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T0948Z.txt`.
  - Critical log proof that the new image is active:
    - `Using splat-transform splat-transform v1.10.2 (device=cpu, lod_decimation=30%,10%,3%, chunk_count=1024K, chunk_extent=32, transform_timeout=14400s, lod_transform_timeout=14400s)`.
    - Selected PLY source `/opt/ml/processing/input/__extracted_archives/00-model-tar/splat.ply`.
    - Running `splat-transform -w -g cpu .../splat.ply .../generated_bundle/meta.json`.
- Next step:
  - Continue monitoring this compression-only retry. S3 output is expected to remain empty until EndOfJob upload. If it completes, validate the SuperSplat bundle, gaussian count/file size, and deployed no-sky viewer. If it fails, capture exact CloudWatch logs and patch only that proven failure.

### 2026-05-15T03:56:00-0600

- Ledger commit/push:
  - Commit: `de00f0d7707a1fa76b1e8b50ebf188531e4bf022` (`chore: launch md1 compression retry`).
  - Push: `git push origin agent-113647-md1-baseline-e2e` -> `5682b213..de00f0d7`.
- Exact-head workflow verification:
  - `gh run watch 25911519106 --exit-status` -> `CDK Deploy` succeeded for head `de00f0d7707a1fa76b1e8b50ebf188531e4bf022`.
- Current retry still active at the last status check:
  - `aws sagemaker describe-processing-job --processing-job-name md1-e2e-vsfm-splatfacto-cfix-202605150946-compression --region us-west-2`:
    - `ProcessingJobStatus=InProgress`.
    - `ProcessingStartTime=2026-05-15T03:47:07.043000-0600`.
    - `ProcessingEndTime=null`.
    - `FailureReason=null`.
- Next step:
  - Keep monitoring compression-only retry `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression`; do not launch more jobs unless it fails or completes and the smallest next stage is clear.

### 2026-05-15T03:03:20-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `eb166a12832dedafaef9bdc627d174d17bf04f76`.
  - Local dirty files not staged: `logs/md1-baseline-e2e/STATE.md`, prior/current poll snapshots, and top-level generated viewer screenshots/results.
  - `aws sts get-caller-identity --region us-west-2` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Exact-head GitHub workflow: `CDK Deploy` run `25902702055` @ `eb166a12832dedafaef9bdc627d174d17bf04f76` -> `success`.
- Current active AWS state:
  - Running Step Functions executions:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-202605150539`.
  - InProgress training jobs:
    - External/not owned by this automation: `md1-full2157-ds4-r25-1778823276` -> `InProgress` / `Training`; left untouched.
  - InProgress processing jobs:
    - This run: `md1-e2e-vsfm-splatfacto-202605150539-compression` -> `InProgress`.
- Compression status:
  - Processing job: `md1-e2e-vsfm-splatfacto-202605150539-compression`.
  - Status: `InProgress`.
  - Started: `2026-05-15T02:14:08-0600`; still no `ProcessingEndTime` and no failure reason.
  - Input remains:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/`.
  - Output remains:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-202605150539/`.
  - 3DGS S3 prefix:
    - `Total Objects: 1`, `Total Size: 64488068`.
  - Compression S3 output remains empty as expected until job end (`S3UploadMode=EndOfJob`):
    - `Total Objects: 0`, `Total Size: 0`.
  - Latest CloudWatch line remains the `splat-transform -w -g cpu .../splat.ply .../generated_bundle/meta.json` invocation; no completion or error line yet.
- Snapshots:
  - Step Functions:
    - `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-202605150539-20260515T0903Z.json`.
  - Compression SageMaker:
    - `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-202605150539-compression-20260515T0903Z.json`.
  - Compression CloudWatch:
    - `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-202605150539-cloudwatch-20260515T0903Z.json`.
    - `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-202605150539-cloudwatch-20260515T0903Z.txt`.
  - S3 listings:
    - `logs/md1-baseline-e2e/s3-3dgs-md1-e2e-vsfm-splatfacto-202605150539-20260515T0903Z.txt`.
    - `logs/md1-baseline-e2e/s3-compressed-md1-e2e-vsfm-splatfacto-202605150539-20260515T0903Z.txt`.
- Next step:
  - Continue monitoring compression. If it completes, validate bundle files/summary, gaussian count/file size, and smoke the deployed `/md1-viewer` with no skybox against the new standard-splatfacto manifest before accepting the baseline. If compression fails, capture exact processing logs and patch only that proven failure.

### 2026-05-15T06:34:43-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022`.
  - Local dirty/untracked files remain poll artifacts and existing viewer smoke outputs; no code changes.
  - `aws sts get-caller-identity --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Exact-head GitHub workflow: `CDK Deploy` run `25911519106` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022` -> `success`.
- Current active AWS state:
  - Running Step Functions executions:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-cfix-202605150946`.
  - InProgress processing jobs:
    - This run: `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression` -> `InProgress`.
  - InProgress training jobs:
    - External/not owned by this automation: `md1-worst447-ds1500-r27-1778846018` -> `InProgress`; left untouched.
- Compression-only retry status:
  - Step Functions execution:
    - `status=RUNNING`.
    - Snapshot `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1234Z.json`.
  - SageMaker processing:
    - `ProcessingJobName=md1-e2e-vsfm-splatfacto-cfix-202605150946-compression`.
    - `ProcessingJobStatus=InProgress`.
    - `ProcessingStartTime=2026-05-15T03:47:07.043000-0600`.
    - `ProcessingEndTime=null`.
    - `FailureReason=null`.
    - `ImageUri=975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/compressor:agent113647md1baselinee2e`.
    - `InstanceType=ml.g4dn.xlarge`.
    - Snapshot `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-compression-20260515T1234Z.json`.
  - Input:
    - `s3://spaceport-ml-processing-staging/3dgs/md1-e2e-vsfm-splatfacto-202605150539/`.
  - Output:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/`.
    - Current S3 listing remains empty as expected until EndOfJob upload: `Total Objects: 0`, `Total Size: 0 Bytes`.
    - S3 listing snapshot `logs/md1-baseline-e2e/s3-compressed-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1234Z.txt`.
  - CloudWatch log:
    - Log stream `/aws/sagemaker/ProcessingJobs` / `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression/algo-1-1778838426`.
    - Snapshot `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T1234Z.json`.
    - Text `logs/md1-baseline-e2e/compression-md1-e2e-vsfm-splatfacto-cfix-202605150946-cloudwatch-20260515T1234Z.txt`.
    - Latest visible command remains the LOD bundle transform:
      - `splat-transform -w -g cpu -C 1024 -X 32 /opt/ml/processing/input/__extracted_archives/00-model-tar/splat.ply -l 0 /tmp/sogs-work-yalufyvo/lod_inputs/lod1.ply -l 1 /tmp/sogs-work-yalufyvo/lod_inputs/lod2.ply -l 2 /tmp/sogs-work-yalufyvo/lod_inputs/lod3.ply -l 3 /tmp/sogs-work-yalufyvo/generated_bundle/lod-meta.json`.
    - Prior progress still holds: the first single-bundle transform passed the old 3600s timeout barrier and LOD input generation completed through `lod3.ply`; no OOM, timeout, or failure is visible.
- Commands run this poll:
  - `aws sagemaker describe-processing-job --processing-job-name md1-e2e-vsfm-splatfacto-cfix-202605150946-compression --region us-west-2 --output json`.
  - `aws logs get-log-events --log-group-name /aws/sagemaker/ProcessingJobs --log-stream-name md1-e2e-vsfm-splatfacto-cfix-202605150946-compression/algo-1-1778838426 --region us-west-2 --start-from-head --output json`.
  - `aws s3 ls s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/ --recursive --summarize --human-readable --region us-west-2`.
  - `aws stepfunctions describe-execution --execution-arn arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-cfix-202605150946 --region us-west-2 --output json`.
  - `gh run list --branch agent-113647-md1-baseline-e2e --limit 8 --json databaseId,workflowName,headSha,status,conclusion,createdAt,url`.
- Next step:
  - Continue monitoring this compression-only retry. No duplicate SfM, 3DGS, or compression job is warranted. If the LOD transform completes, validate the uploaded bundle, gaussian counts/file sizes, and the deployed no-sky viewer before accepting the MD1 baseline.

### 2026-05-15T08:01:00-0600

- Verification before action:
  - Branch/head: `agent-113647-md1-baseline-e2e` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022`.
  - `aws sts get-caller-identity --region us-west-2 --output json` -> account `975050048887`, ARN `arn:aws:iam::975050048887:root`.
  - Running Step Functions executions: none (`aws stepfunctions list-executions ... --status-filter RUNNING` -> `executions: []`).
  - SageMaker InProgress processing jobs: none (`logs/md1-baseline-e2e/sagemaker-processing-inprogress-20260515T1401Z.json`).
  - SageMaker InProgress training jobs: one external job `md1-worst447-ds1000-r28-1778852094`, left untouched (`logs/md1-baseline-e2e/sagemaker-training-inprogress-20260515T1401Z.json`).
  - Exact-head GitHub workflow still green: `CDK Deploy` run `25911519106` @ `de00f0d7707a1fa76b1e8b50ebf188531e4bf022` -> `success`.
- Compression-only retry completed successfully:
  - Step Functions execution:
    - `arn:aws:states:us-west-2:975050048887:execution:SpaceportMLPipeline-staging:execution-md1-e2e-vsfm-splatfacto-cfix-202605150946`.
    - `status=SUCCEEDED`, `stopDate=2026-05-15T07:32:15.265000-0600`.
    - Snapshot: `logs/md1-baseline-e2e/stepfunctions-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1354Z.json`.
  - SageMaker processing job:
    - `md1-e2e-vsfm-splatfacto-cfix-202605150946-compression`.
    - `ProcessingJobStatus=Completed`, `ProcessingStartTime=2026-05-15T03:47:07.043000-0600`, `ProcessingEndTime=2026-05-15T07:27:58.895000-0600`.
    - Snapshot: `logs/md1-baseline-e2e/sagemaker-describe-md1-e2e-vsfm-splatfacto-cfix-202605150946-compression-20260515T1354Z.json`.
  - Staging output:
    - `s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/`.
    - `Total Objects: 45`, `Total Size: 22.2 MiB`.
    - Listing: `logs/md1-baseline-e2e/s3-compressed-md1-e2e-vsfm-splatfacto-cfix-202605150946-20260515T1354Z.txt`.
  - Bundle metadata:
    - `sogs_compression_summary.json`: original `310.344 MB`, compressed `22.24 MB`, compression ratio `13.9543`, `lodLevels=4`, `chunkFiles=4`, `skybox=null`.
    - Root single bundle `meta.json`: `count=1312166`.
    - LOD manifest `lod-meta.json`: LOD0 `1,312,166`, LOD1 `393,650`, LOD2 `131,217`, LOD3 `39,365`.
    - Metadata snapshots:
      - `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-cfix-202605150946-sogs_compression_summary.json`.
      - `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-cfix-202605150946-meta.json`.
      - `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-cfix-202605150946-lod-meta.json`.
- Public artifact handoff:
  - Staging objects are SSE-KMS and cannot be fetched anonymously from the staging bucket, so the validated bundle was copied to the public processing bucket with:
    - `aws s3 sync s3://spaceport-ml-processing-staging/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/ s3://spaceport-ml-processing/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/ --region us-west-2 --sse AES256`
  - Public root manifest:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/supersplat_bundle/meta.json`.
  - Public LOD manifest:
    - `https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/supersplat_bundle/lod-meta.json`.
  - Public `lod-meta.json` GET returned `200`; proof:
    - `logs/md1-baseline-e2e/public-lod-meta-md1-e2e-vsfm-splatfacto-cfix-202605150946-headers.txt`.
    - `logs/md1-baseline-e2e/public-lod-meta-md1-e2e-vsfm-splatfacto-cfix-202605150946-body.json`.
- Visual/debug gate:
  - The generated LOD root loaded but rendered black in the current route; direct inner-viewer checks showed root `meta.json` and chunk `0_0/meta.json` render visible pixels, so this branch now supports single-bundle validation URLs as the smallest proven viewer handoff.
  - PLY diagnostics for the standard splatfacto training output are recorded at `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-202605150539-ply-diagnostics-20260515T1342Z.json`.
  - Viewer patch:
    - `web/lib/sogsViewerBundle.ts` now extracts single-bundle `means.mins/maxs` bounds and `count`.
    - `web/components/md1-viewer/Md1ProductionViewer.tsx` now auto-frames non-production custom bundles from manifest bounds and preserves explicit camera/scene query overrides.
    - `web/scripts/test-md1-production-viewer.mjs` now supports `MD1_EXPECT_ROOT_FILE=meta.json` for single-bundle smoke checks.
  - Local validation:
    - `npm run build` -> pass; pre-existing lint warnings only.
    - `python3 -m unittest tests.unit.test_sogs_supersplat_bundle` -> pass (`Ran 7 tests`).
    - `git diff --check` -> pass.
    - `MD1_VIEWER_URL=http://127.0.0.1:3032 MD1_LOD_URL=https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/supersplat_bundle/meta.json MD1_EXPECT_ROOT_FILE=meta.json MD1_RUN_NO_SKY=1 node web/scripts/test-md1-production-viewer.mjs` -> pass.
  - Local no-sky proof:
    - Smoke log: `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-cfix-202605150946-local-meta-nosky-smoke-20260515T1359Z.log`.
    - Results: `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-cfix-202605150946-local-meta-nosky-results-20260515T1359Z.json`.
    - Desktop screenshot: `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-cfix-202605150946-local-meta-nosky-desktop-nosky-20260515T1359Z.png`.
    - Metrics: desktop first frame `1216.3ms`, mobile first frame `1376.8ms`, desktop no-sky first frame `1324.9ms`, `bundleKind=single`, `rootFile=meta.json`, `Full source=1,312,166`.
- Next step:
  - Commit and push the viewer single-bundle framing fix, watch the exact-head Pages and CDK runs, then run the deployed `/md1-viewer` smoke against the public `meta.json` URL. If deployed smoke passes visually, provide the final URL and screenshots as proof.

### 2026-05-15T08:15:00-0600

- Commit/push:
  - Commit: `8d8361ab67c65e2e0165b7e400df08d6d36c6fbd` (`fix: frame md1 baseline single bundle viewer`).
  - Push: `git push origin agent-113647-md1-baseline-e2e` -> `de00f0d7..8d8361ab`.
- Exact-head workflow verification:
  - `gh run watch 25922045300 --exit-status` -> `CDK Deploy` succeeded for head `8d8361ab67c65e2e0165b7e400df08d6d36c6fbd`.
  - `gh run watch 25922045293 --exit-status` -> `Deploy Next.js to Cloudflare Pages` succeeded for head `8d8361ab67c65e2e0165b7e400df08d6d36c6fbd`.
  - Pages output from run `25922045293`:
    - Alias: `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev`.
    - Hash: `https://9777a8f1.v0-spaceport-website-preview2.pages.dev`.
- Deployed viewer smoke:
  - Command:
    - `MD1_VIEWER_URL=https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev MD1_LOD_URL=https://spaceport-ml-processing.s3.amazonaws.com/compressed/md1-e2e-vsfm-splatfacto-cfix-202605150946/supersplat_bundle/meta.json MD1_EXPECT_ROOT_FILE=meta.json MD1_RUN_NO_SKY=1 node web/scripts/test-md1-production-viewer.mjs`
  - Result: pass.
  - Smoke log: `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-cfix-202605150946-deployed-meta-nosky-smoke-20260515T1410Z.log`.
  - Results: `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-cfix-202605150946-deployed-meta-nosky-results-20260515T1410Z.json`.
  - Desktop no-sky screenshot: `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-cfix-202605150946-deployed-meta-nosky-desktop-nosky-20260515T1410Z.png`.
  - Mobile screenshot: `logs/md1-baseline-e2e/md1-e2e-vsfm-splatfacto-cfix-202605150946-deployed-meta-nosky-mobile-20260515T1410Z.png`.
  - Metrics: desktop first frame `1224.1ms`, mobile first frame `908.1ms`, desktop no-sky first frame `440.5ms`, `bundleKind=single`, `rootFile=meta.json`, `Full source=1,312,166`.
- Visual gate:
  - The deployed viewer is functioning and renders the completed MD1 standard splatfacto output without skybox masking.
  - The current trained baseline is visibly soft/low-detail compared with the existing V18 reference; I am not marking it as production-quality geometry, only as the verified current development-branch baseline render.
  - Camera sweep screenshots for manual visual inspection:
    - `logs/md1-baseline-e2e/md1-deployed-camera-auto-20260515T1413Z.png`.
    - `logs/md1-baseline-e2e/md1-deployed-camera-front-low-20260515T1413Z.png`.
    - `logs/md1-baseline-e2e/md1-deployed-camera-top-20260515T1413Z.png`.
- Final verified URL:
  - `https://agent-113647-md1-baseline-e2.v0-spaceport-website-preview2.pages.dev/md1-viewer?url=https%3A%2F%2Fspaceport-ml-processing.s3.amazonaws.com%2Fcompressed%2Fmd1-e2e-vsfm-splatfacto-cfix-202605150946%2Fsupersplat_bundle%2Fmeta.json&skybox=none`
- Remaining known limitation:
  - The `/lod-meta.json` route for this freshly generated LOD bundle still renders black in the current viewer, while the root single-bundle `meta.json` and chunk `0_0/meta.json` render. The delivered URL intentionally uses the verified root `meta.json` handoff.
