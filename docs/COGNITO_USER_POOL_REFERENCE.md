# Cognito User Pool Reference

## TL;DR – Correct Values

| Environment | Branch(es) | User Pool ID | Client ID | Region |
|-------------|------------|--------------|-----------|--------|
| **Staging (Preview)** | `development`, `agent-*` | `us-west-2_VuNwiNkPC` | `79ch7hmvnpq1die3b18a3ep28s` | `us-west-2` |
| **Production** | `main` | `us-west-2_a2jf3ldGV` | `3ctkuqu98pmug5k5kgc119sq67` | `us-west-2` |

---

## How It Works

The user pool **does not change per commit**. It is fixed per environment:

- **main** → uses `*_PROD` GitHub secrets → production pool
- **development** and **agent-*** → use `*_PREVIEW` GitHub secrets → staging pool

## Staging (Preview Builds)

- **CloudFormation stack:** `SpaceportAuthStagingStack`
- **Pool name:** `Spaceport-Users-staging`
- **User Pool ID:** `us-west-2_VuNwiNkPC`
- **Client ID:** `79ch7hmvnpq1die3b18a3ep28s`
- **Region:** `us-west-2`

GitHub secrets used by Cloudflare Pages workflow:
- `COGNITO_USER_POOL_ID_PREVIEW`
- `COGNITO_USER_POOL_CLIENT_ID_PREVIEW`
- `COGNITO_REGION_PREVIEW`

## Production

- **CloudFormation stack:** Production Auth stack may not be deployed (only staging exists in some setups)
- **User Pool ID:** `us-west-2_a2jf3ldGV` (from `scripts/admin/update_production_secrets.sh`)
- **Client ID:** `3ctkuqu98pmug5k5kgc119sq67`

GitHub secrets:
- `COGNITO_USER_POOL_ID_PROD`
- `COGNITO_USER_POOL_CLIENT_ID_PROD`
- `COGNITO_REGION_PROD`

## Fixing "User Pool Not Found" on Preview Builds

If preview builds (development, agent branches) fail with "user pool not found", update the PREVIEW secrets:

```bash
gh secret set COGNITO_USER_POOL_ID_PREVIEW --body "us-west-2_VuNwiNkPC"
gh secret set COGNITO_USER_POOL_CLIENT_ID_PREVIEW --body "79ch7hmvnpq1die3b18a3ep28s"
gh secret set COGNITO_REGION_PREVIEW --body "us-west-2"
```

Or run the diagnostic script (pulls from CloudFormation and updates secrets):

```bash
./scripts/admin/diagnose_auth_issue.sh
```

## Verifying Current Values

```bash
# Staging pool (from CloudFormation)
aws cloudformation describe-stacks --stack-name SpaceportAuthStagingStack \
  --query "Stacks[0].Outputs[?contains(OutputKey,'Cognito')]"

# Verify pool exists
aws cognito-idp describe-user-pool --user-pool-id us-west-2_VuNwiNkPC --region us-west-2
```
