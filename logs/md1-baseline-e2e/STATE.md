# MD1 Baseline E2E State

updated: 2026-05-13T11:48:00-06:00
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
