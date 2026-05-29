# 3DGS SfM-Authority Pivot Handoff

Status: stopped on 2026-05-29 after company direction pivot.

Worktree: `/Users/gabrielhansen/worktrees/agent-52689431-3dgs-sfm-authority`

Branch: `agent-52689431-3dgs-sfm-authority`

## Final Compute State

- All local `codex-3dgs-*` tmux watcher sessions were killed.
- SageMaker Processing jobs in `InProgress`: none.
- SageMaker Training jobs in `InProgress`: none.
- `spaceport-ml-containers` CodeBuild builds queued/in-progress: none.
- R38 tile_00 completed before the stop request took effect, but no R38 merge or review was launched.

## What Was Accomplished

- Kept 3DGS work isolated in the local worktree, leaving the root checkout clean for other agents.
- Built and pushed 3DGS code improvements through the remote branch and AWS build path, without using local Docker.
- Verified exact-head CDK/GitHub ML trigger/CodeBuild for the latest meaningful code commit.
- Produced and used the exact 3DGS image digest:
  `975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:d0c82c5bea7d23e9f813a5a76c1d5645ac5811dc85ab85a73751a7738f8c1f2c`
- Added per-tile quality review diagnostics so horizon/boundary failures can identify which tile is responsible.
- Fixed merge packaging to honor sidecar SfM-authority bounds, which materially improved the two-tile canary versus stale observed-point bounds.
- Ran a sequence of bounded CV-HR two-tile no/full-light canaries to understand the quality frontier without launching a full production retrain.

## Best Known 3DGS Result

R30/R37 class results are the best preserved-quality path:

- Strict-core merge worked with `fallback_tile_count=0` and `retain_all_tile_count=0`.
- V18 non-regression promoted on the evaluated frozen-camera smoke set.
- Sidecar bounds cleared the earlier `DJI_00801.JPG` horizon saturation issue.
- Remaining hard blocker was narrowly focused on `DJI_00809.JPG`.

Latest R37 review facts:

- Merge retained `354,317 / 410,836` gaussians.
- Baseline non-regression promoted.
- Horizon SSIM delta versus V18 was positive at about `+0.000916`.
- `DJI_00809.JPG` horizon alpha coverage remained `0.9954604444` against the hard threshold `0.995`.
- Absolute canary PSNR/SSIM/LPIPS gates were still below production thresholds.

## Important Learnings

- The SfM seam-graph work transfers well as a 3DGS ownership contract: use the camera-to-tile graph, core/overlap roles, and strict bounds as source of truth.
- The current two-tile path can merge without fallback or retain-all behavior once sidecar bounds are honored.
- The remaining `DJI_00809.JPG` failure is tile_00-led:
  - tile_00 horizon coverage was about `0.999156`
  - tile_07 horizon coverage was about `0.899084`
- Simple center-projection pruning is not enough. R37 removed the intended hcov-only candidates but did not move the rendered alpha gate.
- Broad pruning can clear the alpha gate but damages quality:
  - R32 cleared foreground saturation but regressed V18 near-detail PSNR and horizon SSIM.
  - R33/R34 fixed near-detail but still regressed horizon SSIM by too much.
  - R35/R36/R37 preserved quality but left alpha barely over threshold.

## If This Is Revived

Start from no-spend diagnosis, not a full retrain.

Recommended next technical move:

1. Add render-contribution or footprint-aware pruning diagnostics for `DJI_00809.JPG`.
2. Identify gaussians whose projected footprints cover sky even when their centers land on roof/building texture.
3. Only then run a single tile_00 no-training canary and compare against R30/R35/R37.
4. Do not promote until hard visual QA passes, absolute quality policy is resolved, and viewer/LOD proof is complete.

Avoid more blind tuning of `min_edge_support`, sky color distance, or hcov center projection. That loop was already explored enough to show diminishing returns.

## Key Commits

- `60e705c3` - targeted horizon coverage pruning for 3DGS.
- `dabb386a` - honor sidecar bounds in 3DGS merge.
- `bea9580f` - add per-tile quality review diagnostics.

## Key Artifacts

- R37 mixed merge preflight:
  `logs/3dgs-sfm-authority/cvhr_sfm_authority_r37_mixed_merge_preflight.json`
- R37 hard visual QA gate:
  `logs/3dgs-sfm-authority/cvhr_sfm_authority_r37_mixed_visual_qa_gate.json`
- Agent loop log:
  `logs/agent-loop.log`
- Current stopped state:
  `STATE.md`
