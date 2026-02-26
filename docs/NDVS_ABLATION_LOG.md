# NDVS Ablation Log

## 2026-02-26 - Iteration 001 - Scale Regularization
- Branch: `agent-70931462-phase5-scale-regularization`
- Change: enabled `--pipeline.model.use-scale-regularization True`.
- NDVS run: `22457191875` (control9/progress).
- Result: no metric delta vs baseline (PSNR/SSIM/LPIPS/time unchanged).
- Decision: reverted via commit `8c68d7e`.
