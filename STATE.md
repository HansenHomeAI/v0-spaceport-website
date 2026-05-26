reason: MD1 latest seam_graph_sim3_v1 SfM six-GPU timing and quality proof is active. This is SfM-only; no downstream 3DGS/SOGS quality claim is in scope.
last_step: 2026-05-26T16:27:03Z launched planner-only SageMaker processing job md1-sg6-plan-1779812400 using image 975050048887.dkr.ecr.us-west-2.amazonaws.com/spaceport/sfm:agent73948216sfmproductionspine. Output prefix is s3://spaceport-ml-processing-staging/manual-validations/md1-seamgraph-sixgpu-20260526T1620Z/planner/colmap.
next_unblocked_step: Monitor planner to terminal. Only launch MD1 leaf jobs after chunk_planner_manifest.json validates with visibility_cell_v1, image_pose_priors_local, no weak-core chunks below 20 core images, and jurisdiction data for every chunk. Then launch pending leaves up to six concurrent ml.g4dn.xlarge processing jobs.
owner_action_needed: none
active_jobs: ["md1-sg6-plan-1779812400"]
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
current_rung: MD1_SG6_PLANNER_RUNNING
project_final_decision: pending
