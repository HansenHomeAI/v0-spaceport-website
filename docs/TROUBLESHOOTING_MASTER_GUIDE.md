# Troubleshooting Master Guide - Spaceport Website

## 🎯 **Overview**

This guide consolidates all troubleshooting knowledge gained during the Spaceport website development and deployment. It provides step-by-step solutions for common issues and a systematic approach to debugging.

---

## 🚨 **Critical Issues & Solutions**

### **1. API "Server not found" Errors**

#### **Symptoms:**
- Frontend console shows "A server with the specified hostname could not be found"
- Network tab shows 404 or connection refused errors
- API calls fail with hostname resolution errors

#### **Root Cause:**
Frontend is calling incorrect API Gateway IDs due to:
- Hardcoded fallback URLs in frontend code
- Incorrect environment variables in GitHub Secrets
- Environment variables not being injected during build

#### **Solution:**
1. **Remove all hardcoded fallbacks** from frontend code
2. **Update GitHub Secrets** with correct API Gateway IDs
3. **Trigger new build** to inject environment variables

#### **Verification:**
```bash
# Check GitHub Secrets
gh secret list --repo HansenHomeAI/v0-spaceport-website

# Verify environment variables in build logs
# Check .env file creation in GitHub Actions
```

---

### **2. CORS "Preflight response is not successful" Errors**

#### **Symptoms:**
- Browser console shows CORS errors for OPTIONS requests
- Preflight requests return 403 or 404 status codes
- API calls fail with "Origin not allowed" errors

#### **Root Cause:**
Missing OPTIONS methods in API Gateway for CORS preflight requests.

#### **Solution:**
Add OPTIONS method to API Gateway endpoint:

```bash
# Get resource ID for endpoint
aws apigateway get-resources --rest-api-id API_ID

# Add OPTIONS method
aws apigateway put-method \
  --rest-api-id API_ID \
  --resource-id RESOURCE_ID \
  --http-method OPTIONS \
  --authorization-type NONE

# Add method response with CORS headers
aws apigateway put-method-response \
  --rest-api-id API_ID \
  --resource-id RESOURCE_ID \
  --http-method OPTIONS \
  --status-code 200 \
  --response-parameters '{"method.response.header.Access-Control-Allow-Origin":true,"method.response.header.Access-Control-Allow-Headers":true,"method.response.header.Access-Control-Allow-Methods":true}'

# Add mock integration for OPTIONS
aws apigateway put-integration \
  --rest-api-id API_ID \
  --resource-id RESOURCE_ID \
  --http-method OPTIONS \
  --type MOCK \
  --request-templates '{"application/json":"{\"statusCode\": 200}"}'

# Add integration response with CORS headers
aws apigateway put-integration-response \
  --rest-api-id API_ID \
  --resource-id RESOURCE_ID \
  --http-method OPTIONS \
  --status-code 200 \
  --response-parameters '{"method.response.header.Access-Control-Allow-Headers":"'"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent'"'"'","method.response.header.Access-Control-Allow-Methods":"'"'"'OPTIONS,GET,PUT,POST,DELETE,PATCH,HEAD'"'"'","method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'"}'

# Deploy API Gateway
aws apigateway create-deployment \
  --rest-api-id API_ID \
  --stage-name prod \
  --description "Add OPTIONS method for CORS"
```

---

### **3. Lambda "Access Denied" Errors**

#### **Symptoms:**
- API calls return 500 "Access Denied" errors
- Lambda logs show permission denied for AWS services
- S3, DynamoDB, or SES operations fail

#### **Root Cause:**
Lambda function lacks required IAM permissions for:
- API Gateway invocation
- S3 bucket access
- DynamoDB table access
- SES email sending

#### **Solution:**
Add required Lambda permissions:

```bash
# Add API Gateway invocation permission
aws lambda add-permission \
  --function-name FUNCTION_NAME \
  --statement-id apigw-ENDPOINT_NAME \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-west-2:ACCOUNT_ID:API_ID/PROD/POST/ENDPOINT_PATH"

# Add S3 permissions (inline policy)
aws iam put-role-policy \
  --role-name ROLE_NAME \
  --policy-name S3AccessPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:DeleteObject",
          "s3:AbortMultipartUpload",
          "s3:ListMultipartUploadParts",
          "s3:ListBucketMultipartUploads"
        ],
        "Resource": [
          "arn:aws:s3:::BUCKET_NAME",
          "arn:aws:s3:::BUCKET_NAME/*"
        ]
      }
    ]
  }'

# Add DynamoDB permissions
aws iam put-role-policy \
  --role-name ROLE_NAME \
  --policy-name DynamoDBAccessPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ],
        "Resource": "arn:aws:dynamodb:us-west-2:ACCOUNT_ID:table/TABLE_NAME"
      }
    ]
  }'

# Add SES permissions
aws iam put-role-policy \
  --role-name ROLE_NAME \
  --policy-name SESAccessPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ],
        "Resource": "*"
      }
    ]
  }'
```

---

### **4. Environment Variables Not Loading**

#### **Symptoms:**
- Frontend shows "Amplify has not been configured correctly"
- API calls fail with undefined environment variables
- Build-time variables not available in runtime

#### **Root Cause:**
- Environment variables not injected during build
- Hardcoded fallbacks overriding environment variables
- GitHub Actions not creating `.env` file

#### **Solution:**
1. **Verify GitHub Actions workflow** creates `.env` file
2. **Remove hardcoded fallbacks** from frontend code
3. **Check GitHub Secrets** contain correct values
4. **Trigger new build** to inject environment variables

#### **Verification:**
```bash
# Check GitHub Secrets
gh secret list --repo HansenHomeAI/v0-spaceport-website

# Verify .env file creation in build logs
# Check environment variable injection in build step
```

---

### **5. SES Email Not Sending**

#### **Symptoms:**
- Waitlist submissions succeed but no confirmation emails
- Lambda logs show "Email address is not verified" errors
- SES returns MessageRejected errors

#### **Root Cause:**
- **SES Configuration**: Check sender identity verification
- **Lambda Permissions**: Verify SES permissions are configured
- **Email Templates**: Verify email content and formatting

#### **Solution:**
1. **Verify sender identity**:
```bash
aws ses get-identity-verification-attributes --identities "gabriel@spcprt.com"
```

2. **Check SES production status**:
```bash
aws ses get-account-sending-enabled
aws ses get-send-quota
```

3. **Verify Lambda SES permissions** (see Lambda permissions section above)

4. **Test email sending directly**:
```bash
aws ses send-email \
  --source "gabriel@spcprt.com" \
  --destination "ToAddresses=test@example.com" \
  --message "Subject={Data=Test},Body={Text={Data=Test message}}"
```

---

## 🔍 **Systematic Troubleshooting Approach**

### **Step 1: Identify the Problem**
1. **Check browser console** for error messages
2. **Check network tab** for failed requests
3. **Check Lambda logs** for backend errors
4. **Check API Gateway logs** for request/response issues

### **Step 2: Determine Root Cause**
1. **Frontend Issues**: Environment variables, hardcoded URLs
2. **API Gateway Issues**: Missing resources, methods, or CORS
3. **Lambda Issues**: Permissions, code errors, or configuration
4. **AWS Service Issues**: S3, DynamoDB, SES configuration

### **Step 3: Apply Solution**
1. **Follow specific solution** for identified issue
2. **Test fix** in development environment first
3. **Deploy to production** after verification
4. **Monitor** for any new issues

### **Step 4: Document Solution**
1. **Update this guide** with new learnings
2. **Share solution** with team members
3. **Prevent recurrence** through better practices

---

## 📋 **Common Debugging Commands**

### **API Gateway Debugging:**
```bash
# List all APIs
aws apigateway get-rest-apis

# Get API resources
aws apigateway get-resources --rest-api-id API_ID

# Get specific resource
aws apigateway get-resource --rest-api-id API_ID --resource-id RESOURCE_ID

# Get method details
aws apigateway get-method --rest-api-id API_ID --resource-id RESOURCE_ID --http-method METHOD

# Test endpoint directly
curl -X POST "https://API_ID.execute-api.us-west-2.amazonaws.com/prod/ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}' \
  -v
```

### **Lambda Debugging:**
```bash
# List functions
aws lambda list-functions

# Get function details
aws lambda get-function --function-name FUNCTION_NAME

# Get function policy
aws lambda get-policy --function-name FUNCTION_NAME

# Check function logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda"

# Get latest log stream
aws logs describe-log-streams \
  --log-group-name "/aws/lambda/FUNCTION_NAME" \
  --order-by LastEventTime \
  --descending \
  --max-items 1

# Get log events
aws logs get-log-events \
  --log-group-name "/aws/lambda/FUNCTION_NAME" \
  --log-stream-name "STREAM_NAME"
```

### **IAM Debugging:**
```bash
# List attached policies
aws iam list-attached-role-policies --role-name ROLE_NAME

# Get inline policies
aws iam list-role-policies --role-name ROLE_NAME

# Get specific policy
aws iam get-role-policy --role-name ROLE_NAME --policy-name POLICY_NAME

# Get role details
aws iam get-role --role-name ROLE_NAME
```

### **SES Debugging:**
```bash
# Check sending status
aws ses get-account-sending-enabled

# Check send quota
aws ses get-send-quota

# List verified identities
aws ses list-identities --identity-type EmailAddress

# Check verification status
aws ses get-identity-verification-attributes --identities "EMAIL_ADDRESS"

# Test sending email
aws ses send-email \
  --source "gabriel@spcprt.com" \
  --destination "ToAddresses=test@example.com" \
  --message "Subject={Data=Test},Body={Text={Data=Test message}}"
```

---

## 🎯 **Prevention Best Practices**

### **1. Environment Variables:**
- **Never hardcode** API URLs in frontend code
- **Use centralized configuration** in `api-config.ts`
- **Validate environment variables** at startup
- **Test both environments** before deployment

### **2. API Development:**
- **Always add OPTIONS methods** for CORS
- **Test endpoints** with curl before frontend integration
- **Verify Lambda permissions** for all endpoints
- **Use consistent naming** conventions

### **3. Infrastructure:**
- **Test in development** before production
- **Monitor CloudWatch logs** regularly
- **Use Infrastructure as Code** (CDK) for consistency
- **Follow least-privilege** IAM principles

### **4. Deployment:**
- **Automate environment variable injection** in CI/CD
- **Test builds** in preview environment
- **Monitor deployment logs** for errors
- **Have rollback plan** ready

---

## 🚀 **Quick Fix Reference**

### **Immediate Actions for Common Issues:**

| Issue | Quick Fix | Full Solution |
|-------|-----------|---------------|
| **API not found** | Check GitHub Secrets | Update environment variables |
| **CORS errors** | Add OPTIONS method | Configure CORS properly |
| **Lambda access denied** | Check IAM permissions | Add required policies |
| **Email not sending** | Verify SES identity | Request production access |
| **Env vars not loading** | Trigger new build | Fix GitHub Actions workflow |

### **Emergency Contacts:**
- **AWS Support**: If you have subscription
- **GitHub Issues**: For code-related problems
- **Team Chat**: For immediate collaboration

---

**Last Updated**: 2025-08-22 - After resolving all major API and infrastructure issues
**Status**: **Production Ready** ✅
**Next Review**: When new issues arise or after major deployments
