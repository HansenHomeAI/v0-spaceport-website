reason: geometry-first md1 tiled 3DGS reset from pinned ffef97e646046f204267ec30dd7dbf6f19027cad
current_rung: R2_bounded_pair_training_live
root_cause_classification: merge_bad
live_compute_status: CDK Deploy run 24866283054 and Cloudflare Pages run 24866392058 are green for a4cee4dba1ac804e1f7cef278ef3cd5129aa6fc5. Exact preview alias is https://agent-90742618-md1-geometry.v0-spaceport-website-preview2.pages.dev and hash URL is https://9dc0019f.v0-spaceport-website-preview2.pages.dev. Branch 3dgs image tag agent90742618md1geometryconsistency points to digest sha256:039416aaf53bed7ab8a60202acf125c80083de3b14177fbd6ee2979b7b0725f6; R2 live job md1-r2-pair-1776991746-tiled is running on untagged digest sha256:0e9492295885735deb6ef1e8ce8bbe1e8d72dd84f2c38082bd601a9c9e2ab750, output root s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-consistency-r2-20260424004906/3dgs/T2_tiled_pipeline, tile ids tile_02,tile_05, support_weighted_overlap merge, scaffold enabled, and 12000 leaf iterations. R2 useful signal observed: scaffold training reached 4000/4000, scaffold PLY exported, and tile_02 leaf training started at 2026-04-24T01:20:10Z with 188 selected images. R1 candidate reviews completed: support_weighted_overlap matched strict_core and remained blocked by fallback_tile_count=2; raw_union improved metrics and was fallback-free but is diagnostic-only and now blocked by diagnostic_raw_union_not_promotable. No duplicate R2 job should be launched while md1-r2-pair-1776991746-tiled is active.
branch: agent-90742618-md1-geometry-consistency
base_commit: ffef97e646046f204267ec30dd7dbf6f19027cad
head: a4cee4dba1ac804e1f7cef278ef3cd5129aa6fc5
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
next_unblocked_step: monitor md1-r2-pair-1776991746-tiled for useful scaffold/leaf artifact formation; if it completes, run the strengthened R1/R2 direct-candidate review gate on its model artifact before any broader rung, and if it stalls without new signal stop it and relaunch R2 only after verifying the exact current branch image and scaffold-init metadata path.
owner_action_needed: none
updated: 2026-04-23T19:25:46-06:00
