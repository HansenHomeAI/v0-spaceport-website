reason: Unblocked. EXIF-only SfM priors are implemented in the SfM container and a staging SfM-only execution is currently running to validate outputs.
last_step: Started Step Functions execution (staging) with pipelineStopAfter="sfm" on 2026-02-09 22:27 MST (execution-2fcf68f2-2fa3-4ba7-953b-1c7afc55d75b).
next_unblocked_step: Wait for the SageMaker SfM processing job to complete; verify S3 output exists and sfm_metadata.json reports priors_source="exif" and gps_enhanced=true; if it fails or stalls, capture CloudWatch logs and iterate on run_opensfm_gps.py (timeouts/streaming).
owner_action_needed: None (unless AWS permissions/secrets change or the pipeline needs manual stop).
