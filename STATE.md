reason: MD1 latest seam_graph_sim3_v1 SfM six-GPU timing and quality proof is active. This is SfM-only; no downstream 3DGS/SOGS quality claim is in scope.
last_step: 2026-05-26T20:14Z all 17 leaves completed and basic verification passed, but the strict seam_graph_sim3_v1 reducer failed safely. No merged sparse output was promoted: accepted tree edges=0, merged_registered_images=0, blockers include accepted_seam_graph_is_disconnected, model_merge_failed, and missing_sparse0.
next_unblocked_step: Run no-spend reducer/leaf-solve diagnostics for the meter-level shared-camera drift. The current evidence says the six-GPU leaves have small scale deltas and baseline-normalized residuals, but no >=20-shared-image seam passes max_sim3_p95_residual_m=0.25; determine whether the fix is stronger global-prior/rig constraints in leaf solving or a seam-local normalization/refinement pass before any paid relaunch.
owner_action_needed: none yet; this is a material regression but the next step is still no-spend diagnosis.
active_jobs: []
branch: agent-29861473-md1-sixgpu-sfm
head: 0ba36246
source_branch_artifact: agent-73948216-sfm-production-spine
source_image_uri: 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:agent73948216sfmproductionspine
aws_account: "975050048887"
quota_decision: No quota raise needed for exactly six concurrent ml.g4dn.xlarge processing jobs; SageMaker quota L-2F1EB012 is 6.0 and active processing/training jobs were empty before planner launch.
run_status: logs/sfm-production-spine/md1_sg6_status_20260526T1620Z.json
run_root: s3://spaceport-ml-processing-staging/manual-validations/md1-seamgraph-sixgpu-20260526T1620Z
planner_manifest_uri: s3://spaceport-ml-processing-staging/manual-validations/md1-seamgraph-sixgpu-20260526T1620Z/planner/colmap/chunk_planner_manifest.json
max_concurrency: 6
planner_completed_seconds: 467.49
planner_validation: "visibility_cell_v1; chunks=17; image_pose_priors_local=3076; jurisdictions=17; weak_core_chunks=[]; passes_leaf_fanout_contract=true"
leaf_status: "17 Completed and basic-verified, 0 InProgress, 0 not_launched, 0 failed"
strict_reducer_report: logs/sfm-production-spine/md1_sg6_seam_graph_reducer_20260526T2004Z.json
strict_seam_report: logs/sfm-production-spine/md1_sg6_seam_merge_report_20260526T2004Z.json
blocker_isolation: logs/sfm-production-spine/md1_sg6_strict_reducer_blocker_isolation_20260526T2014Z.json
current_rung: MD1_SG6_STRICT_REDUCER_BLOCKED
project_final_decision: do_not_promote_yet
