# Agent Progress – 3DGS & Pipeline Stability

## Context & Goal
- Objective: verify high-quality Gaussian Splat (3DGS) training and move toward full SfM → 3DGS → Compression validation.
- Constraints: run on branch `agent-48291375-3dgs-testing`, push often to trigger Cloudflare/CodeBuild workflows, log loop steps in `logs/agent-loop.log`.
- Infrastructure: SageMaker jobs (`ml.g5.2xlarge` target), Step Functions state machine `SpaceportMLPipeline`, CodeBuild project `spaceport-ml-containers`.

---

## Work Completed

### 1. Stabilized 3DGS Container Runtime
- **Problem**: gsplat JIT failed with `cooperative_groups::labeled_partition` and missing `libcudart` when running on SageMaker (ml.g5).
- **Fixes**:
  - Constrained `TORCH_CUDA_ARCH_LIST` to `8.0 8.6` in `train_nerfstudio_production.py` and exported the same via Step Functions/Lambda/test harness.
  - Installed CUDA developer bits (`cuda-nvcc-11-8`, `cuda-cudart-dev-11-8`) inside `infrastructure/containers/3dgs/Dockerfile`; set `CUDA_HOME`, `LD_LIBRARY_PATH`, and `LIBRARY_PATH` explicitly.
  - Ensured Step Functions environment variables propagate `CUDA_HOME`, `LD_LIBRARY_PATH`, `LIBRARY_PATH`, `TORCH_CUDA_ARCH_LIST`.
- **Result**: `tests/pipeline/test_3dgs_only.py` now completes successfully. Latest run:
  - SageMaker job: `ml-job-20251117-120429-3dgs-tes-3dgs`
  - Duration: 2,257s (~37 min)
  - Output: `s3://spaceport-ml-processing/3dgs/3dgs-test-1763406269/ml-job-.../model.tar.gz`
  - Exported `splat.ply` (~280 MB), SOGS-compatible. Logs saved to `logs/test_3dgs_only_run4.log` and CloudWatch copy `logs/sagemaker-ml-job-20251117-120429-3dgs-tes-3dgs.log`.

### 2. Container Build Pipeline (CodeBuild) Reliability
- Triggered `build-containers.yml` multiple times until CodeBuild succeeded (`run 19440774132`, build ID `spaceport-ml-containers:d87f95aa-0fc5-481b-9518-47ea19ff62ea`).
- Added guard in `buildspec.yml` to **skip Docker Hub login when creds absent**, preventing rate-limit failures (`Must provide --username` / 429 errors).
- Documented in `logs/build-containers-*.log` and `logs/codebuild-spaceport-ml-containers-*.log`.

### 3. Test Harness Alignment with Production Inputs
- Updated `tests/pipeline/test_full_pipeline.py` to match actual Step Functions expectations:
  - Includes `jobId`, `jobName`, `email`, `sfmProcessingInputs`, bucket URIs, pipeline metadata.
  - Uses `spaceport/sfm:latest` (since `real-colmap-fixed-final` image no longer exists).
  - Passes hyperparameters + CUDA env values to Step Functions.
- Added env propagation for CUDA variables in `lambda/start_ml_job`.

---

## Current Test Status

| Test | Result | Notes |
|------|--------|-------|
| `tests/pipeline/test_3dgs_only.py` | ✅ Pass | Verified multiple iterations, final run 4 succeeded on ml.g5.2xlarge. |
| `tests/pipeline/test_full_pipeline.py` | ❌ Blocked | Fails early because Lambda `Spaceport-MLNotification` is missing (`ResourceNotFoundException`), preventing pipeline completion despite SfM starting. |

Artifacts & logs parked under `logs/`:
- `test_3dgs_only_run4.log` – console output for the successful SageMaker run.
- `sagemaker-ml-job-20251117-120429-3dgs-tes-3dgs.log` – CloudWatch events (shows export/metrics).
- `test_full_pipeline_run*.log` – attempts with failure reasons (missing Lambda, invalid sfm image, etc.).

---

## Outstanding Items / Not Yet Tested

1. **Full Pipeline Completion** – blocked by missing `Spaceport-MLNotification` Lambda. Need owner to redeploy or adjust state machine to skip notifications for test executions.
2. **Compression Stage** – not reached due to pipeline abort; once Lambda restored, rerun `tests/pipeline/test_full_pipeline.py`.
3. **Automated Quality Assertions** – PSNR/gaussian-count thresholds currently logged but not enforced. Could parse `logs/sagemaker-ml-job-...` to assert `target_psnr` reached and gaussian counts (~1.5M cap).
4. **Playwright MCP / CF Preview Validation** – not triggered; focus was backend pipeline.

---

## Next Steps (Recommended)
1. Restore or stub `Spaceport-MLNotification` Lambda so Step Functions can complete (or temporarily bypass notification states during tests).
2. Re-run `tests/pipeline/test_full_pipeline.py` to verify SfM → 3DGS → Compression after Lambda fix.
3. Capture PSNR + gaussian metrics from CloudWatch logs into test output for auditable quality thresholds.
4. Once end-to-end is green, document compression output location and run `tests/pipeline/test_compression_only.py` if needed for regression.

---

**Branch**: `agent-48291375-3dgs-testing` (commits include `fix: stabilize 3dgs training runtime`, `chore: allow CodeBuild to skip Docker Hub login`, `chore: document CUDA deps for 3dgs container`). Continuous loop entries recorded in `logs/agent-loop.log`.
