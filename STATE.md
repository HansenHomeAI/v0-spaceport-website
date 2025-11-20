reason: implement the /sogs-viewer page and push it through lint/build plus pipeline deploys
last_step: built the SOGS viewer route with PlayCanvas SuperSplat, added ESLint config + cleaned legacy lint errors, ran `npx next lint` + `npm run build`, started the Playwright MCP ensure task, and pushed agent-48291037-sogs-viewer with both Cloudflare Pages (https://agent-48291037-sogs-viewer.v0-spaceport-website-preview2.pages.dev) and CDK runs green
next_unblocked_step: drive preview validation / Playwright MCP flow against the new viewer and prepare the PR summary once UI verification artifacts are captured
owner_action_needed: none
updated: 2025-11-20T14:07:39Z
