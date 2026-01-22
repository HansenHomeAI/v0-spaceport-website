reason: blocked - local E2E cannot proceed because Litchi API resources are missing in AWS and GitHub CLI cannot read preview secret values
last_step: restarted local dev with .env.local and attempted Litchi connect; status remains unconnected due to missing backend and invalid/unknown Litchi API URL
next_unblocked_step: set correct Litchi API URL + Cognito/Projects preview secrets (or restore Litchi API + Lambda in staging), then rerun local Playwright E2E
owner_action_needed: provide preview secret values (COGNITO_REGION_PREVIEW, COGNITO_USER_POOL_ID_PREVIEW, COGNITO_USER_POOL_CLIENT_ID_PREVIEW, PROJECTS_API_URL_PREVIEW, LITCHI_API_URL_PREVIEW) or restore Litchi API/Lambda in staging so DNS resolves and status/connect succeed
updated: 2026-01-22T20:05:00Z
