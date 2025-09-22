# 🔍 Spaceport AI Invitation Flow Troubleshooting Guide

## 📋 Overview

This guide provides comprehensive troubleshooting for the "Invalid username or password" errors in the Spaceport AI invitation system. Based on deep analysis of the authentication flow, this covers the most likely root causes and provides actionable solutions.

## 🚨 Most Likely Root Causes

### 1. **User Pool Mismatch (HIGH PROBABILITY)**
**Symptoms:** Users receive invitation emails but get "Invalid username or password" when trying to sign in.

**Root Cause:** Users are created in one Cognito User Pool, but the frontend is configured to authenticate against a different User Pool.

**How it happens:**
- Infrastructure deployments switch between User Pools
- Environment variables point to different pools than where users were created
- The fallback logic in `auth_stack.py` creates confusion between pools

**Verification:**
```bash
# Run the comprehensive diagnosis
./scripts/admin/comprehensive_auth_diagnosis.sh test@example.com

# Check which pool users are actually in
aws cognito-idp list-users --user-pool-id us-west-2_POOL_ID_HERE
```

### 2. **Temporary Password Race Conditions (MEDIUM PROBABILITY)**
**Symptoms:** Intermittent failures, especially on weekends or during low-traffic periods.

**Root Cause:** Timing issues between user creation, password setting, and authentication attempts.

**How it happens:**
- User tries to sign in before Cognito has fully processed the user creation
- Custom email delivery is faster than Cognito's internal processing
- Lambda function doesn't wait for user creation to propagate

### 3. **Environment Variable Synchronization Issues (MEDIUM PROBABILITY)**
**Symptoms:** Works in one environment but not another, or stops working after deployments.

**Root Cause:** Frontend environment variables don't match the actual infrastructure.

**How it happens:**
- GitHub secrets not updated after CDK deployments
- Multiple environments with different configurations
- Cached environment variables in CI/CD

## 🛠️ Immediate Action Plan

### Step 1: Run Comprehensive Diagnosis
```bash
# Install dependencies if needed
pip3 install boto3 requests

# Run the comprehensive test
python3 scripts/admin/robust_invite_system.py your-test-email@domain.com "Test User"

# Or use the shell version
./scripts/admin/comprehensive_auth_diagnosis.sh your-test-email@domain.com
```

### Step 2: Verify Configuration Consistency
```bash
# Check CloudFormation outputs
aws cloudformation describe-stacks --stack-name SpaceportAuthStack --query "Stacks[0].Outputs[?contains(OutputKey, 'Cognito')]"

# Check GitHub secrets
gh secret list | grep COGNITO

# Verify frontend environment variables match
grep COGNITO web/.env*
```

### Step 3: Test with Known User Pool
If you know the correct User Pool ID:
```bash
# List recent users to verify the pool
aws cognito-idp list-users --user-pool-id us-west-2_YOUR_POOL_ID --limit 5

# Test authentication directly
aws cognito-idp admin-initiate-auth \
  --user-pool-id us-west-2_YOUR_POOL_ID \
  --client-id YOUR_CLIENT_ID \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=test@example.com,PASSWORD=TempPassword123!
```

## 🔧 Robustness Improvements

### 1. Deploy Improved Lambda Function
Replace the current invite Lambda with the improved version:
```bash
# Backup current function
cp infrastructure/spaceport_cdk/lambda/invite_user/lambda_function.py infrastructure/spaceport_cdk/lambda/invite_user/lambda_function_backup.py

# Deploy improved version
cp infrastructure/spaceport_cdk/lambda/invite_user/lambda_function_improved.py infrastructure/spaceport_cdk/lambda/invite_user/lambda_function.py

# Redeploy
cd infrastructure/spaceport_cdk && cdk deploy SpaceportAuthStack
```

### 2. Add Configuration Validation to Frontend
Add this to your `amplifyClient.ts`:
```typescript
export function validateAmplifyConfig(): boolean {
  const region = process.env.NEXT_PUBLIC_COGNITO_REGION;
  const userPoolId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID;
  const clientId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID;
  
  if (!region || !userPoolId || !clientId) {
    console.error('Missing Cognito configuration:', { region, userPoolId, clientId });
    return false;
  }
  
  // Log configuration for debugging (remove in production)
  console.log('Cognito Config:', { region, userPoolId: userPoolId.substring(0, 15) + '...', clientId: clientId.substring(0, 10) + '...' });
  
  return true;
}
```

### 3. Enhanced Monitoring
Add CloudWatch alarms for invitation failures:
```python
# Add to your CDK stack
invite_error_alarm = cloudwatch.Alarm(
    self, "InviteErrorAlarm",
    metric=invite_lambda.metric_errors(),
    threshold=1,
    evaluation_periods=1,
    alarm_description="Invitation Lambda function errors"
)
```

## 🕵️ Deep Debugging Steps

### For Persistent Issues

1. **Enable Detailed Logging**
   ```bash
   # Update Lambda environment variables
   aws lambda update-function-configuration \
     --function-name Spaceport-InviteUserFunction \
     --environment Variables='{COGNITO_USER_POOL_ID=us-west-2_YOUR_POOL,LOG_LEVEL=DEBUG}'
   ```

2. **Check Lambda Logs**
   ```bash
   # Get recent logs
   aws logs filter-log-events \
     --log-group-name /aws/lambda/Spaceport-InviteUserFunction \
     --start-time $(date -d '1 hour ago' +%s)000
   ```

3. **Verify User Pool Client Settings**
   ```bash
   aws cognito-idp describe-user-pool-client \
     --user-pool-id us-west-2_YOUR_POOL \
     --client-id YOUR_CLIENT_ID
   ```

4. **Check for Multiple User Pools**
   ```bash
   aws cognito-idp list-user-pools --max-results 60 | jq '.UserPools[] | select(.Name | contains("Spaceport"))'
   ```

## 📊 Common Error Patterns

### "Invalid username or password" with correct credentials
- **Cause:** User created in wrong pool
- **Solution:** Verify pool IDs match between backend and frontend

### "User does not exist" immediately after invitation
- **Cause:** Race condition in user creation
- **Solution:** Add wait logic in invitation flow

### Works sometimes, fails other times
- **Cause:** Multiple User Pools or environment inconsistency
- **Solution:** Audit all environments and standardize configuration

### Password policy errors
- **Cause:** Generated password doesn't meet policy requirements
- **Solution:** Use improved password generation with special characters

## 🚀 Prevention Strategies

1. **Consistent Environment Management**
   - Use parameter store for configuration
   - Automate environment variable updates
   - Add configuration validation to deployment pipeline

2. **Robust Error Handling**
   - Implement retry logic with exponential backoff
   - Add comprehensive logging
   - Monitor invitation success rates

3. **Testing Automation**
   - Run invitation flow tests after each deployment
   - Monitor authentication success rates
   - Alert on configuration mismatches

## 📞 Emergency Response

If users are experiencing widespread authentication issues:

1. **Immediate Triage**
   ```bash
   # Quick health check
   python3 scripts/admin/robust_invite_system.py emergency-test@yourdomain.com
   ```

2. **Identify Affected Pool**
   ```bash
   # Find the correct pool
   aws cognito-idp list-user-pools --max-results 60 | jq '.UserPools[] | select(.Name | contains("Spaceport"))'
   ```

3. **Update Frontend Configuration**
   ```bash
   # Update GitHub secrets with correct values
   gh secret set NEXT_PUBLIC_COGNITO_USER_POOL_ID --body "us-west-2_CORRECT_POOL_ID"
   gh secret set NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID --body "CORRECT_CLIENT_ID"
   ```

4. **Force Deployment**
   ```bash
   # Trigger immediate deployment
   git commit --allow-empty -m "Emergency: Fix Cognito configuration"
   git push origin main
   ```

## 📈 Success Metrics

Monitor these metrics to ensure invitation flow health:
- Invitation success rate (target: >95%)
- Time from invitation to first successful login (target: <5 minutes)
- Authentication error rate (target: <2%)
- User pool consistency checks (target: 100% match)

## 🔗 Related Resources

- [AWS Cognito Troubleshooting Guide](https://docs.aws.amazon.com/cognito/latest/developerguide/troubleshooting.html)
- [Amplify Authentication Troubleshooting](https://docs.amplify.aws/lib/troubleshooting/q/platform/js/)
- [Spaceport Infrastructure Documentation](./CURRENT_INFRASTRUCTURE_VISUALIZATION.md)

---

**Last Updated:** After comprehensive authentication flow analysis
**Next Review:** After implementing robustness improvements