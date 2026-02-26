# NDVS Ablation Log

## 2026-02-26 - Iteration 003 - SH Degree 4
- Branch: `agent-96742051-phase5-sh-degree`
- Change: `model.sh_degree` 3→4 (higher SH order for finer view-dependent shading).
- NDVS run: `22459887093`, artifact `5679571399`.
- Result: metrics identical to baseline (PSNR/SSIM/LPIPS/time unchanged) and gate failure.
- Decision: reverted via commit `2ef252e`.
