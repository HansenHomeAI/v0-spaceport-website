# NDVS Ablation Log

## 2026-02-26 - Iteration 001 - Scale Regularization
- Branch: `agent-70931462-phase5-scale-regularization`
- Single change: enable splatfacto `use-scale-regularization` in production training path.
- Rationale: scale regularization is a low-overhead safeguard against stretched/spiky gaussians, which is typically favorable for LPIPS/SSIM stability without large runtime increase.
- Files:
  - `infrastructure/containers/3dgs/nerfstudio_config.yaml`
  - `infrastructure/containers/3dgs/train_nerfstudio_production.py`
- NDVS run: pending
- Decision: pending
