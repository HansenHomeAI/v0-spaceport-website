reason: MD1 six-GPU seam_graph_sim3_v1 SfM rerun has passed SfM-only reducer, quality, and viewer proof. This is SfM-only; no downstream 3DGS/SOGS readiness is claimed.
last_step: 2026-05-26T21:45Z strict seam_graph_sim3_v1 reducer passed after merge hardening. Final output has 3076/3076 registered images, 1,318,077 points, 16 accepted seam-tree edges, cycle_consistency=pass, promotion_blockers=[], cross-leaf flagged overlap ratio=0.0, global double-surface flagged ratio=0.0, sparse reprojection p95=1.7651/p99=1.9382, and /pipeline-viewer debugSeams loaded nonblank.
next_unblocked_step: Hand off the SfM-only artifact and reducer changes to downstream 3DGS chunking/bounds work; do not claim 3DGS/SOGS quality without separate render/compression/viewer gates.
owner_action_needed: none.
active_jobs: []
branch: agent-29861473-md1-sixgpu-sfm
head: 20cd18ca36710bfa5c3123d9c82923592645a44a
aws_account: "975050048887"
source_branch_artifact: agent-73948216-sfm-production-spine
source_image_uri: 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:agent73948216sfmproductionspine
run_status: logs/sfm-production-spine/md1_sg6_status_20260526T1620Z.json
run_root: s3://spaceport-ml-processing-staging/manual-validations/md1-seamgraph-sixgpu-20260526T1620Z
final_sfm_output_uri: s3://spaceport-ml-processing-staging/manual-validations/md1-seamgraph-sixgpu-20260526T1620Z/merged-pruned-culled-seamtree-r2/colmap
viewer_url: http://127.0.0.1:3000/pipeline-viewer?url=s3%3A%2F%2Fspaceport-ml-processing-staging%2Fmanual-validations%2Fmd1-seamgraph-sixgpu-20260526T1620Z%2Fmerged-pruned-culled-seamtree-r2%2Fcolmap&maxPoints=160000&debugSeams=1
planner_completed_seconds: 467.49
leaf_wall_hours: 3.283
planner_plus_leaf_compute_hours: 11.989
max_concurrency: 6
quota_decision: No quota raise needed for exactly six concurrent ml.g4dn.xlarge processing jobs; SageMaker quota L-2F1EB012 is 6.0.
planner_validation: "visibility_cell_v1; chunks=17; image_pose_priors_local=3076; jurisdictions=17; weak_core_chunks=[]; passes_leaf_fanout_contract=true"
leaf_status: "17 Completed and basic-verified, 0 InProgress, 0 not_launched, 0 failed"
reducer_report: logs/sfm-production-spine/md1_sg6_seamtree_reducer_20260526T2145Z.json
seam_report: logs/sfm-production-spine/md1_sg6_seamtree_seam_merge_report_20260526T2145Z.json
quality_report: logs/sfm-production-spine/md1_sg6_seamtree_sfm_only_quality_20260526T2145Z.json
viewer_api_report: logs/sfm-production-spine/md1_sg6_seamtree_pipeline_viewer_api_20260526T2145Z.json
viewer_screenshot: logs/sfm-production-spine/md1_sg6_seamtree_pipeline_viewer_debugseams_20260526T2145Z.jpg
final_proof_summary: logs/sfm-production-spine/md1_sg6_seamtree_final_proof_summary_20260526T2145Z.json
exact_head_ci: CDK Deploy run 26477013861 success for 20cd18ca36710bfa5c3123d9c82923592645a44a
current_rung: MD1_SG6_SFM_ONLY_PRODUCTION_PROOF_PASSED
project_final_decision: promote_sfm_only_md1_sixgpu
