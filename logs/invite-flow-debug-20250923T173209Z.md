# Invite Flow Debug Notes

## Context
- Investigated repeated "Invalid username or password" errors after sending invite emails.
- Working in dev account (`AWS_PROFILE=spaceport-dev`, pool `us-west-2_a2jf3ldGV`).

## Reproduction (Before Fix)
1. Created user with `admin-create-user` (temp password `Spcprt1111A`).
2. Attempted to re-invite with `MessageAction=SUPPRESS` and new password `Spcprt2222A`.
3. Login attempt with `Spcprt2222A` failed: `NotAuthorizedException: Incorrect username or password.`
   - Confirms Cognito never received updated password.

## Validation (After Fix Logic)
1. Applied new flow: after catching `UsernameExistsException`, call `admin_set_user_password`.
2. Login with regenerated password (`nuAAi5CM9VDT`) succeeded and returned `NEW_PASSWORD_REQUIRED` challenge.
3. Confirmed email alias lower-casing + attribute sync succeeds even when preferred username cannot be updated.

## Cleanup
- Deleted temporary test users `codex.invite+00{1,2,3}@example.com` and `codex.invite+resend@example.com`.

