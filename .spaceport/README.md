`deploy-auth-preview` is an opt-in marker for preview branches.

Create `.spaceport/deploy-auth-preview` on a non-`development`/non-`main` branch when that branch should redeploy the shared staging auth stack on every push.

Remove the marker to return the branch to the default auth read-only preview behavior.
