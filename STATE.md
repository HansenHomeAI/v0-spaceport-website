reason: geometry-first md1 tiled 3DGS reset from pinned ffef97e646046f204267ec30dd7dbf6f19027cad
current_rung: R1_candidate_comparison
root_cause_classification: merge_bad
live_compute_status: CDK Deploy is green for defd015dd93b7539a4b44a328f751235ad3f42db; Cloudflare Pages run 24865959733 for defd015d reached deployed URLs but remained stuck in health verification, so the workflow now bounds curl health probes. Exact preview alias from the prior green c00091ae gate is https://agent-90742618-md1-geometry.v0-spaceport-website-preview2.pages.dev and hash URL is https://d090e306.v0-spaceport-website-preview2.pages.dev. Branch 3dgs image tag agent90742618md1geometryconsistency points to digest sha256:039416aaf53bed7ab8a60202acf125c80083de3b14177fbd6ee2979b7b0725f6. Exact-head R1 strict_core review job md1-r1-strict-core-1776989969-quality completed and produced render_sanity=ok, but promotion is blocked by fallback_tile_count=2 and weak/flat boundary tile visuals. Live SageMaker training job md1-r1a-embeddedposes-20260424003441 is in progress as a camera/pose diagnostic and is being monitored for useful artifact signal.
branch: agent-90742618-md1-geometry-consistency
base_commit: ffef97e646046f204267ec30dd7dbf6f19027cad
head: defd015dd93b7539a4b44a328f751235ad3f42db
base_worktree: /Users/gabrielhansen/worktrees/agent-86580563-hierarchical-splat-merge-plan
canonical_model_artifact: s3://spaceport-ml-processing-staging/manual-validations/md1-1k-full-r2-1776194089/3dgs/T2_tiled_pipeline/md1-1k-full-r2-1776194089-tiled/output/model.tar.gz
local_audit_root: /Users/gabrielhansen/worktrees/agent-90742618-md1-geometry-consistency/logs/audit/md1-1k-full-r2
audit_manifest: logs/audit/md1-1k-full-r2/audit_manifest.json
review_camera_manifest: logs/audit/md1-1k-full-r2/review_camera_manifest.json
review_comparison: logs/audit/md1-1k-full-r2/review_comparison.json
offline_merge_reports: logs/audit/md1-1k-full-r2/offline_merges/{raw_union,strict_core,support_weighted_overlap}/merge_report.json
r0_inventory: complete; 7 tile splats, merged splat, merge report, tile manifest, and view bucket manifest found
r1_result: exact-head c00091ae strict_core review completed: near_detail median PSNR=10.2046 SSIM=0.3251 LPIPS=0.9124; boundary median PSNR=13.1340 SSIM=0.4168 LPIPS=0.8233; horizon median PSNR=16.2155 SSIM=0.3831 LPIPS=0.8721; render_sanity=ok; fallback_tile_count=2; retain_all_tile_count=0. Visuals are no longer blank but boundary/individual tile renders remain poor, so run support/raw candidate comparison before pivoting.
candidate_pair_top_rank: tile_02/tile_05; shared_assigned_images=64; boundary_support=52; eligible=true
blocked_promotion_reason: strict_core still has fallback_tile_count=2 and weak/flat boundary/tile renders; candidate comparison has not yet rerun on valid render_sanity baseline
next_unblocked_step: commit and push the bounded Pages health-probe guard, cancel/retry the stuck Pages run for the exact head, keep monitoring md1-r1a-embeddedposes-20260424003441, then run support_weighted_overlap and raw_union R1 candidate reviews against strict_core baseline manifest s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-r1-review-c00091ae-render-sanity/baselines/strict_core once the branch gate is green
owner_action_needed: none
updated: 2026-04-23T18:45:00-06:00
