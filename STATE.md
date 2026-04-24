reason: geometry-first md1 tiled 3DGS reset; continuing beyond offline R1 toward bounded proof gates
current_rung: R1a review-gate hardening; embedded-pose renderer fix implemented locally after camera-viewmat smoke
root_cause_classification: merge_bad
live_compute_status: none; md1-r1a-viewfix-20260423235854 completed in 532 billable seconds but review output was invalid because it used freshly converted COLMAP poses instead of bundled training poses
current_branch: agent-53821974-md1-geometry-consistency
current_head_at_state_write: 9fff5423f3203fcf92b55df8568454a844eaef4e plus uncommitted embedded pose-source fix
base_branch: agent-86580563-hierarchical-splat-merge-plan
base_commit: ffef97e646046f204267ec30dd7dbf6f19027cad
automation:
  heartbeat_id: md1-geometry-proof-continuation
  cadence: every 30 minutes
  purpose: reassess branch, PR, workflow, AWS, artifact, and audit status; keep moving the proof ladder
exact_artifacts:
  canonical_training_tarball: s3://spaceport-ml-processing-staging/manual-validations/md1-1k-full-r2-1776194089/3dgs/T2_tiled_pipeline/md1-1k-full-r2-1776194089-tiled/output/model.tar.gz
  active_smoke_review_job: md1-r1a-viewfix-20260423235854
  active_smoke_review_output_root: s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-consistency-r1a-20260423235854/review-render-job-output
  active_smoke_review_artifact: s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-consistency-r1a-20260423235854/review-render-job-output/md1-r1a-viewfix-20260423235854/output/model.tar.gz
  active_smoke_review_image: 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:83899e61c91fef1adc932bfe33ba30e061883c8c0cb98de3e58c82ac24b10853
  active_smoke_review_camera_manifest: s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-consistency-r1a-20260423235854/inputs/review_camera_manifest.json
  preview_url: https://agent-53821974-md1-geometry.v0-spaceport-website-preview2.pages.dev
  preview_hash_url: https://391ae750.v0-spaceport-website-preview2.pages.dev
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
review_gate_delta:
  added_merged_no_background_renders: true
  added_no_background_bucket_medians: true
  added_deterministic_view_capped_rendering: true
  renderer_failure_root_cause: full merged 3.6M-Gaussian artifact requested ~454GiB during gsplat tile intersection
  failed_smoke_review_job: md1-r1a-render-20260423211511
  completed_black_render_job: md1-r1a-rendercap-20260423214434
  black_render_root_cause: PLY opacity logits and log-scales were passed to gsplat without sigmoid/exp conversion
  added_ply_decode_fix: true
  added_frozen_camera_smoke_cap: true
  completed_flat_render_job: md1-r1a-renderfix-20260423221859
  flat_render_root_cause: f_rest_* SH coefficients were loaded as RGB-interleaved triples, but the exporter writes channel-major SH rest fields
  added_sh_rest_order_fix: true
  added_blank_flat_render_health_gate: true
  completed_camera_convention_probe_job: md1-r1a-shfix-20260423233228
  camera_convention_root_cause: remaining blank views selected negative-Z support but rendered with an unconverted view matrix, producing alpha=0 despite high projected support
  added_camera_view_candidate_selection: true
  completed_pose_source_probe_job: md1-r1a-viewfix-20260423235854
  pose_source_root_cause: exported Nerfstudio splats are in the bundled tiled_pipeline training-pose coordinate frame, but the review renderer rebuilt COLMAP transforms in a different frame
  added_embedded_training_pose_source: true
  smoke_review_target: tile_02/tile_05 using frozen 4/4/4 camera set before bounded R2 retraining
next_unblocked_step: commit and push embedded training-pose review fix, watch CDK/Pages/container workflows to green, rerun 4/4/4 smoke with render_scale=0.25, and require spatially credible side-by-side evidence before R2 spend
owner_action_needed: none
updated: 2026-04-24T00:20:43Z
