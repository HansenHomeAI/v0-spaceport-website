reason: geometry-first md1 tiled 3DGS reset; offline R0/R1 gates now block promotion before new AWS spend
current_rung: R1 offline merge/evaluation gate implemented; no new AWS training launched
root_cause_classification: merge_bad
live_compute_status: none
current_branch: agent-53821974-md1-geometry-consistency
current_head_at_state_write: ffef97e646046f204267ec30dd7dbf6f19027cad
base_branch: agent-86580563-hierarchical-splat-merge-plan
base_commit: ffef97e646046f204267ec30dd7dbf6f19027cad
exact_artifacts:
  canonical_training_tarball: s3://spaceport-ml-processing-staging/manual-validations/md1-1k-full-r2-1776194089/3dgs/T2_tiled_pipeline/md1-1k-full-r2-1776194089-tiled/output/model.tar.gz
  local_audit_manifest: logs/audit/md1-1k-full-r2/audit_manifest.json
  local_review_comparison: logs/audit/md1-1k-full-r2/review_comparison.json
  frozen_review_cameras: logs/audit/md1-1k-full-r2/review_camera_manifest.json
  recovered_historical_merge: /Users/gabrielhansen/worktrees/agent-86580563-hierarchical-splat-merge-plan/logs/aws/md1-1k-full-r2/remerge-fixed/merged-fixed-2/
audit_result:
  tile_splat_count: 7
  required_artifacts_present: true
  fallback_tile_count: 2
  retain_all_tile_count: 0
  offline_merge_reports: raw_union=5103651 retained, strict_core=4500379 retained with 2 fallbacks, support_weighted_overlap=4500379 retained with 2 fallbacks
  support_weighted_overlap_vs_strict: no retained-gaussian recovery; pivot to training-time overlap consistency/global guidance before R2 promotion
  top_candidate_pair: tile_02/tile_05
  top_candidate_shared_assigned_images: 64
  top_candidate_boundary_support_images: 52
next_unblocked_step: push branch, watch required workflows to green, then run containerized review with the frozen camera manifest before any bounded R2 retraining
owner_action_needed: none
updated: 2026-04-23T19:12:38Z
