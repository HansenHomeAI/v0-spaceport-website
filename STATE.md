reason: Full SfM dataset pushed through 3DGS + SOGS manually (TORCH_CUDA_ARCH_LIST enforced) while Step Functions path still failing on gsplat compile and missing MLNotification Lambda
last_step: Step Functions run with staging COLMAP output failed (gsplat build + missing notification Lambda); reran manually via SageMaker create_training_job/create_processing_job with TORCH_CUDA_ARCH_LIST=8.0 8.6, yielding completed 3DGS (model.tar.gz ~340 MB) and SOGS bundle in staging
next_unblocked_step: align the state machine/3DGS container so TORCH_CUDA_ARCH_LIST is forced (and MLNotification restored) then rerun Step Functions end-to-end using the same staging COLMAP prefix
owner_action_needed: restore arn:aws:lambda:us-west-2:975050048887:function:Spaceport-MLNotification or allow tests to bypass notification; confirm if we can update the state machine to set TORCH_CUDA_ARCH_LIST=8.0 8.6 (or rebuild 3dgs image to hardcode it)
updated: 2025-12-13
