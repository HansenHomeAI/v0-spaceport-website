reason: building a development-based Send to Controller feature branch by merging the latest Litchi automation work and hardening it for hosted browser/controller delivery
last_step: exact-head auth redeploy failed because the AWS account is at the 1000 IAM role quota; patched Litchi to mount on the existing Projects API, reuse the existing Projects Lambda role for Litchi API/worker/Step Functions, and remove unrelated Invite V2 resources from this feature branch
next_unblocked_step: commit and push the IAM-quota mitigation, then monitor exact-head CDK/Pages workflows and use the resolved preview URL for browser validation
owner_action_needed: none
updated: 2026-05-28T14:35:57-06:00
