reason: geometry-first md1 tiled 3DGS reset from pinned ffef97e646046f204267ec30dd7dbf6f19027cad
current_rung: R2_bounded_pair_training_cap450k_live
root_cause_classification: merge_bad
live_compute_status: Active R2 capped pair job md1-r2-cap450k-1776999423-tiled is InProgress/Downloading on ml.g5.2xlarge with exact image 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:225b73f994499ab720d282994bed7b53c73b35090e24761a6429153075e9ce1b. Output root is s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-consistency-r2-cap450k-20260424025651/T2_tiled_pipeline. Environment keeps full image scale and 12000 leaf iterations, uses tile_02,tile_05, support_weighted_overlap, eval suppression, GLOBAL_SCAFFOLD_INIT_MAX_POINTS=450000, and PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 with proof_profile=none and no TRAINING_STOP_SPLIT_AT fallback. Exact-head gates are green for d061d339865b66494d4f9d75cf57514de9bc96e5: CDK 24869499856, ML container 24869499848 / CodeBuild spaceport-ml-containers:7c3d56fb-5bfa-4ea5-bee8-48b5bc5401f1 / digest sha256:225b73f994499ab720d282994bed7b53c73b35090e24761a6429153075e9ce1b, and Pages 24869725060 with alias https://agent-90742618-md1-geometry.v0-spaceport-website-preview2.pages.dev and hash https://686baa4f.v0-spaceport-website-preview2.pages.dev. Prior R2 failures remain classified as memory during tile_02 leaf training after uncapped scaffold inheritance.
live_compute_correction_20260424025813Z: Duplicate capped retry md1-r2-cap450k-1776999409-tiled was stopped while still pending/downloading to avoid duplicate bounded spend. Active capped retry is md1-r2-cap450k-1776999423-tiled, output prefix s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-consistency-r2-cap450k-20260424025651/T2_tiled_pipeline, exact image digest sha256:225b73f994499ab720d282994bed7b53c73b35090e24761a6429153075e9ce1b, GLOBAL_SCAFFOLD_INIT_MAX_POINTS=450000, eval suppression retained, no downscale, no iteration reduction.
branch: agent-90742618-md1-geometry-consistency
base_commit: ffef97e646046f204267ec30dd7dbf6f19027cad
head: d061d339865b66494d4f9d75cf57514de9bc96e5
base_worktree: /Users/gabrielhansen/worktrees/agent-86580563-hierarchical-splat-merge-plan
canonical_model_artifact: s3://spaceport-ml-processing-staging/manual-validations/md1-1k-full-r2-1776194089/3dgs/T2_tiled_pipeline/md1-1k-full-r2-1776194089-tiled/output/model.tar.gz
local_audit_root: /Users/gabrielhansen/worktrees/agent-90742618-md1-geometry-consistency/logs/audit/md1-1k-full-r2
audit_manifest: logs/audit/md1-1k-full-r2/audit_manifest.json
review_camera_manifest: logs/audit/md1-1k-full-r2/review_camera_manifest.json
review_comparison: logs/audit/md1-1k-full-r2/review_comparison.json
offline_merge_reports: logs/audit/md1-1k-full-r2/offline_merges/{raw_union,strict_core,support_weighted_overlap}/merge_report.json
r0_inventory: complete; 7 tile splats, merged splat, merge report, tile manifest, and view bucket manifest found
r1_result: exact-head c00091ae strict_core review completed: near_detail median PSNR=10.2046 SSIM=0.3251 LPIPS=0.9124; boundary median PSNR=13.1340 SSIM=0.4168 LPIPS=0.8233; horizon median PSNR=16.2155 SSIM=0.3831 LPIPS=0.8721; render_sanity=ok; fallback_tile_count=2; retain_all_tile_count=0. support_weighted_overlap produced zero metric delta and fallback_tile_count=2. raw_union improved near_detail +0.706 dB PSNR/+0.024 SSIM/-0.012 LPIPS, boundary +0.931 dB/+0.0049 SSIM/-0.012 LPIPS, horizon +0.169 dB/+0.0048 SSIM/-0.0016 LPIPS with fallback_tile_count=0, but raw_union is diagnostic-only because it keeps all source gaussians and is not consistency-preserving.
candidate_pair_top_rank: tile_02/tile_05; shared_assigned_images=64; boundary_support=52; eligible=true
blocked_promotion_reason: R1 merge-only promotion is blocked because support_weighted_overlap did not improve over strict_core and still has fallback_tile_count=2; raw_union passed numeric deltas but is diagnostic-only and blocked by diagnostic_raw_union_not_promotable.
next_unblocked_step: monitor md1-r2-cap450k-1776999423-tiled until it either writes scaffold-init metadata proving the cap and completes, or produces a new failure artifact to classify before the next bounded pivot.
owner_action_needed: none
updated: 2026-04-24T02:58:13Z
