# NDVS Ablation Log

## 2026-02-26 - Iteration 004 - Gaussian Cap +10%
- Branch: `agent-18364289-phase5-gauss-cap`
- Change: `model.max_num_gaussians` 1,500,000→1,650,000.
- NDVS run: `22460998252`, artifact `5680062193`.
- Result: metrics indistinguishable from baseline (PSNR/SSIM/LPIPS/time zero delta) and gate failure → revert commit `038927b`.
