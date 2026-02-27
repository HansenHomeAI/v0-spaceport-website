# Multi-Dataset Metrics Protocol (Phase 3 Stub)

This protocol standardizes evaluation outputs across benchmark datasets (not NDVS-only).

## Scope

Datasets in scope:

- `mipnerf360`
- `tanksandtemples`
- `deepblending`
- `zipnerf`

## Primary NVS Metrics

Per scene, emit:

- `psnr` (higher is better)
- `ssim` (higher is better)
- `lpips_vgg` (lower is better)

## Secondary Reliability / Cost Metrics

Per scene, emit:

- `success` (boolean)
- `runtime_seconds`
- `peak_gpu_memory_mb` (if available)

## Output Contract

Per-run JSON result format (stub):

```json
{
  "run_id": "2026-02-27T18-00-00Z",
  "dataset": "mipnerf360",
  "scene": "garden",
  "metrics": {
    "psnr": 0.0,
    "ssim": 0.0,
    "lpips_vgg": 0.0,
    "success": true,
    "runtime_seconds": 0.0,
    "peak_gpu_memory_mb": null
  }
}
```

Aggregate output should include:

- per-dataset scene averages
- overall weighted/unweighted averages (to be finalized)
- gate verdicts (pass/fail) once threshold policy is finalized

## CI Gate Stub

Phase 3 CI should run evaluator for selected scenes per dataset and fail if:

- required metric keys are missing
- any scene marked `success=false`
- metric JSON schema/shape is invalid

Threshold enforcement is deferred to the next increment.
