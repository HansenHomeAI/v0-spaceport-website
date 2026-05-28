reason: building a development-based Send to Controller feature branch by merging the latest Litchi automation work and hardening it for hosted browser/controller delivery
last_step: initial branch push produced green CDK but Pages waited on missing shared-auth LitchiApiUrl; patched CDK deploy scope so preview auth opt-in and missing LitchiApiUrl force shared auth redeploy, then bumped the Pages trigger
next_unblocked_step: commit and push the auth-output fix, then monitor exact-head CDK/Pages workflows and use the resolved preview URL for browser validation
owner_action_needed: none
updated: 2026-05-28T14:22:05-06:00
