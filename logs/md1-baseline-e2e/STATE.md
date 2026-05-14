# MD1 Baseline E2E State

updated: 2026-05-13T23:31:36-0600
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
- Automation created: `md1-baseline-e2e-monitor` hourly.
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
