# NDVS Ablation Log

## 2026-02-26 - Iteration 002 - Max Gauss Ratio +20%
- Branch: `agent-52419073-phase5-gauss-ratio`
- Change: `--pipeline.model.max-gauss-ratio` from `10.0` to `12.0`.
- NDVS run: `22458474836` (control9/progress).
- Result: no metric delta vs baseline (PSNR/SSIM/LPIPS/time unchanged).
- Decision: reverted via commit `f539f7b`.
