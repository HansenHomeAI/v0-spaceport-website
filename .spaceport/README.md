`deploy-auth-preview` is an opt-in marker for preview branches.

Create `.spaceport/deploy-auth-preview` on a non-`development`/non-`main` branch when that branch should redeploy the shared staging auth stack on every push.

Remove the marker to return the branch to the default auth read-only preview behavior.

Use `scripts/audit_edge_api_usage.py` to report current API Gateway EDGE usage and identify stale preview branch IDs still consuming EDGE APIs.

Use `scripts/check_cdk_endpoint_policy.py` to verify the current branch synthesizes `REGIONAL` API Gateway endpoints for all preview stacks and all non-production shared auth stacks.
