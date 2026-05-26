reason: MD1 latest seam_graph_sim3_v1 SfM six-GPU timing and quality proof is active. This is SfM-only; no downstream 3DGS/SOGS quality claim is in scope.
last_step: 2026-05-26T16:37:20Z planner md1-sg6-plan-1779812400 completed and validated in about 7m47s: visibility_cell_v1, distributed_chunked_v1, 17 chunks, 3076 image_pose_priors_local, 17 jurisdictions, weak_core_chunks=[], passes_leaf_fanout_contract=true. Launched first six leaves md1-sg6-l00-1779812400 through md1-sg6-l05-1779812400.
next_unblocked_step: Monitor leaves 00-05 to terminal and launch pending leaves 06-16 as slots free up, never exceeding six concurrent ml.g4dn.xlarge processing jobs. After all leaves complete, run strict seam_graph_sim3_v1 reducer, sparse quality gates, and viewer/debug proof before judging output quality.
owner_action_needed: none
active_jobs: ["md1-sg6-l00-1779812400", "md1-sg6-l01-1779812400", "md1-sg6-l02-1779812400", "md1-sg6-l03-1779812400", "md1-sg6-l04-1779812400", "md1-sg6-l05-1779812400"]
branch: agent-29861473-md1-sixgpu-sfm
head: da43372f9d18d4b11348d429360f850002d4e3f4
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
leaf_status: "6 InProgress, 11 not_launched"
current_rung: MD1_SG6_LEAF_FANOUT_RUNNING
project_final_decision: pending
