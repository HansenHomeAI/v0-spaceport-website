reason: implementing CloudFront edge bundle delivery on an isolated branch worktree and iterating through CI and preview validation
last_step: fixed the Cloudflare Pages build by marking the non-static viewer and sandbox routes as edge runtime routes and verified next-on-pages locally
next_unblocked_step: commit and push the edge runtime route fix, monitor the resulting CDK and Pages runs to green, then validate the preview viewer with the published edge bundle URL
owner_action_needed: none
updated: 2026-03-28T21:13:00Z
