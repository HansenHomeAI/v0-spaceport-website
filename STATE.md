reason: blocked - cannot provision Litchi API locally because Docker is missing; preview still points at NXDOMAIN Litchi endpoint
last_step: attempted CDK deploy for SpaceportAuthStagingStack with deployTarget=auth; failed bundling due to missing docker (spawnSync docker ENOENT)
next_unblocked_step: install/configure Docker or provide the correct Litchi API endpoint so I can update LITCHI_API_URL_PREVIEW and rerun E2E validation
owner_action_needed: either (a) install Docker so CDK bundling can run, or (b) supply a valid Litchi API Gateway URL to set in LITCHI_API_URL_PREVIEW
updated: 2026-01-22T16:36:00Z
