reason: geometry-first md1 tiled 3DGS reset from pinned ffef97e646046f204267ec30dd7dbf6f19027cad
current_rung: R1_offline_merge_arbitration
root_cause_classification: merge_bad
live_compute_status: R1 strict_core render-backed smoke review md1-r1-strict-core-1776980821-quality failed before rendering because the 3dgs image did not copy geometry_review.py; Dockerfile fix is local and must be pushed for a fresh 3dgs image before retry
branch: agent-90742618-md1-geometry-consistency
base_commit: ffef97e646046f204267ec30dd7dbf6f19027cad
head: committed branch tip; exact hash captured by git rev-parse HEAD and final proof
base_worktree: /Users/gabrielhansen/worktrees/agent-86580563-hierarchical-splat-merge-plan
canonical_model_artifact: s3://spaceport-ml-processing-staging/manual-validations/md1-1k-full-r2-1776194089/3dgs/T2_tiled_pipeline/md1-1k-full-r2-1776194089-tiled/output/model.tar.gz
local_audit_root: /Users/gabrielhansen/worktrees/agent-90742618-md1-geometry-consistency/logs/audit/md1-1k-full-r2
audit_manifest: logs/audit/md1-1k-full-r2/audit_manifest.json
review_camera_manifest: logs/audit/md1-1k-full-r2/review_camera_manifest.json
review_comparison: logs/audit/md1-1k-full-r2/review_comparison.json
offline_merge_reports: logs/audit/md1-1k-full-r2/offline_merges/{raw_union,strict_core,support_weighted_overlap}/merge_report.json
r0_inventory: complete; 7 tile splats, merged splat, merge report, tile manifest, and view bucket manifest found
r1_result: raw_union retained 5103651/5103651; strict_core retained 4500379/5103651 with fallback_tile_count=2; support_weighted_overlap retained 4500379/5103651 with fallback_tile_count=2
candidate_pair_top_rank: tile_02/tile_05; shared_assigned_images=64; boundary_support=52; eligible=true
blocked_promotion_reason: fallback_tile_count remains >0 and render metrics are not yet available for comparative promotion
next_unblocked_step: commit and push the Dockerfile geometry_review.py copy fix, wait for CDK/Pages and the fresh 3dgs image workflow on the exact head, then retry the staged R1 strict_core smoke review on quota-supported ml.g4dn.xlarge without restaging inputs
owner_action_needed: none
updated: 2026-04-23T15:56:01-06:00
