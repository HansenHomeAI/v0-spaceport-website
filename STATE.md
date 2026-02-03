reason: Unblocked. Triggering CI/CDK deploy to recreate missing Litchi API without local Docker.
last_step: Added local /api/litchi proxy + localhost routing and verified it returns a clear 502 when Litchi API is missing; updated local Cognito client to match staging pool.
next_unblocked_step: Commit + push branch to trigger CDK deploy; monitor workflows; update NEXT_PUBLIC_LITCHI_API_URL from stack outputs; re-test local Litchi connect via proxy.
owner_action_needed: none
updated: 2026-02-03T20:05:00Z
