reason: geometry-first md1 tiled 3DGS reset; continuing beyond offline R1 toward bounded proof gates
current_rung: R2 bounded adjacent-pair retry on tile_02/tile_05 after eval and training-memory failures
root_cause_classification: tile_training_bad
live_compute_status: md1-r2-evalskip-1776995639-tiled passed the prior step-2900 eval-OOM point but failed at tile_02 step 5900 with CUDA OOM during gsplat SH backward after gaussian growth reached 1,138,496; larger single-GPU SageMaker quota is unavailable in us-west-2, so bounded retry md1-r2-splitsafe-1776998926-tiled is launched with the same two-tile/full-image/no-downscale scope and TRAINING_STOP_SPLIT_AT=5000; no full-scene training spend active
current_branch: agent-53821974-md1-geometry-consistency
current_head_at_state_write: 4f4ce2325543e7a242f7a4354333b28802f8c4c7
base_branch: agent-86580563-hierarchical-splat-merge-plan
base_commit: ffef97e646046f204267ec30dd7dbf6f19027cad
automation:
  heartbeat_id: md1-geometry-proof-continuation
  cadence: every 30 minutes
  purpose: reassess branch, PR, workflow, AWS, artifact, and audit status; keep moving the proof ladder
exact_artifacts:
  canonical_training_tarball: s3://spaceport-ml-processing-staging/manual-validations/md1-1k-full-r2-1776194089/3dgs/T2_tiled_pipeline/md1-1k-full-r2-1776194089-tiled/output/model.tar.gz
  active_smoke_review_job: md1-r1a-embeddedposes-20260424003441
  active_smoke_review_artifact: s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-consistency-r1a-20260424003441/review-render-job-output/md1-r1a-embeddedposes-20260424003441/output/model.tar.gz
  active_smoke_review_camera_manifest: s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-consistency-r1a-20260424003441/inputs/review_camera_manifest.json
  active_smoke_review_metrics_manifest: logs/audit/md1-1k-full-r2/r1a_smoke_review_20260424003441.json
  active_smoke_review_baseline_manifest_s3: s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-consistency-r1a-20260424003441/baseline/quality_review_manifest.json
  failed_r2_training_job: md1-r2-pair-1776991746-tiled
  failed_r2_model_artifact: s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-consistency-r2-20260424004906/3dgs/T2_tiled_pipeline/md1-r2-pair-1776991746-tiled/output/model.tar.gz
  failed_r2_failure_summary: logs/audit/md1-1k-full-r2/r2_pair_failure_20260424013844.json
  failed_r2_extracted_evidence: logs/audit/md1-1k-full-r2/r2_pair_failed_20260424013844/extracted
  failed_r2_evalskip_training_job: md1-r2-evalskip-1776995639-tiled
  failed_r2_evalskip_model_artifact: s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-consistency-r2-evalskip-20260424015359/3dgs/T2_tiled_pipeline/md1-r2-evalskip-1776995639-tiled/output/model.tar.gz
  failed_r2_evalskip_failure_summary: logs/audit/md1-1k-full-r2/r2_pair_evalskip_failure_20260424024459.json
  failed_r2_evalskip_extracted_evidence: logs/audit/md1-1k-full-r2/r2_pair_evalskip_failed_20260424024459/extracted
  active_r2_training_job: md1-r2-splitsafe-1776998926-tiled
  active_r2_output_root: s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-consistency-r2-splitsafe-20260424025045/3dgs
  active_r2_stage_output: s3://spaceport-ml-processing-staging/manual-validations/md1-geometry-consistency-r2-splitsafe-20260424025045/3dgs/T2_tiled_pipeline
  active_r2_image: 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:3c4c34a04d411ca671bad9865f31254f685e88e28c635c18c9866e53c1e2c7c0
  active_r2_submit_summary: logs/audit/md1-1k-full-r2/r2_pair_splitsafe_submit_20260424025045.json
  r2_retry_checkpoint_head: 4f4ce2325543e7a242f7a4354333b28802f8c4c7
  review_gate_image_source_head: 5db6fcd22db380d2441c5dafcbb70c8989df45fa
  review_gate_image_after_absolute_floor_patch: 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/3dgs@sha256:3c4c34a04d411ca671bad9865f31254f685e88e28c635c18c9866e53c1e2c7c0
  review_existing_artifact_launcher_head: dd8c48626075acbb8530c39f5f6764e6759d62a2
  preview_url: https://agent-53821974-md1-geometry.v0-spaceport-website-preview2.pages.dev
  preview_hash_url: https://4d6fd2b4.v0-spaceport-website-preview2.pages.dev
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
  completed_embedded_pose_smoke_job: md1-r1a-embeddedposes-20260424003441
  embedded_pose_smoke_billable_seconds: 531
  embedded_pose_smoke_result: nonblank but visually invalid; individual boundary tile renders are flat and historical tile stages used 8x downscale with 12 selected images, so the bottleneck is now classified as tile_training_bad for the saved md1 artifact
  embedded_pose_smoke_medians: near_detail_psnr=6.934, boundary_psnr=9.628, horizon_psnr=15.531, boundary_lpips=0.929
  launcher_baseline_review_input_support_commit: 5d17ae3c405291ad2336f4296431579650e0e831
  launcher_frozen_camera_review_input_support_commit: 5d17ae3c405291ad2336f4296431579650e0e831
  local_absolute_quality_floor_gate: blocks ready_for_manual_signoff when near_detail/boundary/horizon median PSNR or LPIPS are below conservative spatial-quality floors
  local_quality_floor_tests: py_compile plus 65 targeted geometry/tile/review tests green
  local_review_existing_artifact_launcher: adds --review-model-artifact-s3-uri path so completed R2 artifacts can be reviewed with frozen cameras and baseline without relaunching training
  local_review_launcher_tests: dry-run resolved frozen camera/baseline inputs and review env; py_compile plus 66 targeted geometry/tile/review tests green
  failed_r2_eval_oom: tile_02 reached step 2900/12000 with 676114 gaussians, then OOMed in Nerfstudio eval image metrics/background SH path; artifact contains scaffold splat and tile_02 logs but no tile_02/tile_05/merged splat, so it is not promotable
  r2_retry_eval_suppression: md1-r2-evalskip-1776995639-tiled keeps full quality/no downscale and only suppresses expensive eval metrics until after training by setting TRAINING_STEPS_PER_EVAL_IMAGE=12001 and TRAINING_STEPS_PER_EVAL_ALL_IMAGES=12001
  r2_training_target: tile_02/tile_05 using full-quality bounded scope, scaffold enabled, merge_mode=support_weighted_overlap, no proof downscale
  checkpoint_workflows_green: CDK 24869439956 and Pages 24869444575 green for 4f4ce232; preview hash https://4d6fd2b4.v0-spaceport-website-preview2.pages.dev
  r2_retry_current_signal: md1-r2-evalskip-1776995639-tiled failed at tile_02 step 5900/12000 after reaching 1,138,496 gaussians; it passed the original eval-OOM point, proving eval suppression worked, but training memory now needs gaussian-growth control
  r2_splitsafe_retry: md1-r2-splitsafe-1776998926-tiled launched with same bounded pair, downscale_factor=1, proof_profile=none, eval suppression retained, and TRAINING_STOP_SPLIT_AT=5000 after quota probe showed no larger single-GPU training quota available
next_unblocked_step: monitor md1-r2-splitsafe-1776998926-tiled through tile_02 past step 5900, then through tile_05 and support_weighted_overlap merge; run frozen 4/4/4 comparative review against the saved R1a baseline manifest if a merged artifact lands
owner_action_needed: none
updated: 2026-04-24T02:49:16Z
