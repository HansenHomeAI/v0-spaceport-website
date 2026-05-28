reason: building the development-based Send to Controller feature branch for hosted Litchi browser/controller delivery
last_step: exact-head CDK failed on a CloudFormation circular dependency caused by reusing the Projects Lambda role for the Litchi API, worker, and state machine; replaced token grants/env references with deterministic worker/state-machine ARNs so the shared role policy no longer depends on resources that also depend on the role
next_unblocked_step: commit and push the circular-dependency fix, then monitor exact-head Pages/CDK workflows and use the resolved preview URL for browser validation
owner_action_needed: none
updated: 2026-05-28T15:17:52-06:00
