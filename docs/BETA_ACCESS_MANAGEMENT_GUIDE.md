# Beta Access Management System

## 🎯 Overview

This system provides a web-based interface for authorized employees to send beta access invitations directly from the dashboard, replacing the need for CLI tools for employee use.

## 🏗️ Architecture

### Backend Components
- **Lambda Function**: `infrastructure/spaceport_cdk/lambda/beta_access_admin/lambda_function.py`
- **API Gateway**: REST endpoints for permission checking and invitation sending
- **DynamoDB Table**: `Spaceport-BetaAccessPermissions` for storing employee permissions
- **CDK Integration**: Added to `AuthStack` in `auth_stack.py`

### Frontend Components
- **React Hook**: `web/app/hooks/useBetaAccess.ts` - Manages API calls and state
- **UI Component**: `web/components/BetaAccessInvite.tsx` - Email input and send button
- **Dashboard Integration**: Added to Account Settings card in `web/app/create/page.tsx`

### CLI Tools
- **Permission Management**: `scripts/admin/grant_beta_access.sh` - Grant/revoke employee permissions
- **Original Invite Tool**: `scripts/admin/invite_user.sh` - Still available for admin use

## 🚀 Deployment Steps

### 1. Deploy Infrastructure

```bash
# Deploy the updated AuthStack with beta access resources
cd infrastructure/spaceport_cdk
cdk deploy SpaceportAuthStack

# Note the output URLs - you'll need the BetaAccessAdminApiUrl
```

### 2. Update Environment Configuration

Add the beta access API URL to your environment:

```bash
# In your .env file or environment variables
NEXT_PUBLIC_BETA_ACCESS_API_URL=https://your-api-id.execute-api.us-west-2.amazonaws.com/prod
```

### 3. Deploy Frontend

```bash
# Build and deploy the updated frontend
cd web
npm run build
# Deploy to your hosting platform (Vercel, CloudFront, etc.)
```

## 👥 Employee Permission Management

### Grant Beta Access Permissions

```bash
# Grant permissions to an employee
./scripts/admin/grant_beta_access.sh employee@company.com

# Example output:
# ✅ Beta access admin permissions granted to employee@company.com
# The user will now see the beta invitation interface on their dashboard.
```

### Revoke Beta Access Permissions

```bash
# Revoke permissions from an employee
./scripts/admin/grant_beta_access.sh employee@company.com --revoke

# Example output:
# ✅ Beta access admin permissions revoked for employee@company.com
# The user will no longer see the invitation interface on their dashboard.
```

### Check Current Permissions

The script automatically verifies permissions after each operation:

```bash
✓ Current status: employee@company.com HAS beta access admin permissions
```

## 🎨 User Experience

### For Employees WITH Permissions
1. **Dashboard Access**: Employee logs into their dashboard at `/create`
2. **Beta Access Section**: Sees "Beta Access Management" section in Account Settings card
3. **Send Invitation**: Enters email address and clicks "Grant Access"
4. **Confirmation**: Receives success/error message
5. **Email Sent**: Recipient gets the same invitation email as CLI tool sends

### For Employees WITHOUT Permissions
- **No UI Changes**: The beta access section is completely hidden
- **Seamless Experience**: Dashboard functions normally without any indication of the feature

### For Recipients
- **Same Experience**: Receives identical invitation email as CLI tool
- **Account Setup**: Same signup flow through `/create` page
- **No Changes**: Existing user experience is unchanged

## 🔒 Security Features

### Authentication & Authorization
- **JWT Verification**: All API calls require valid Cognito JWT tokens
- **Permission Checks**: Database lookup verifies employee permissions
- **Least Privilege**: Employees can only send invitations, not manage permissions

### API Security
- **CORS Configuration**: Properly configured for your domain
- **Rate Limiting**: AWS API Gateway built-in protections
- **Input Validation**: Email format validation on both frontend and backend

### Audit Trail
- **CloudWatch Logs**: All invitation sends are logged with employee email
- **Database Records**: Permission grants/revokes are timestamped
- **Error Tracking**: Failed attempts are logged for monitoring

## 🧪 Testing Guide

### 1. Test Permission System

```bash
# Test granting permissions
./scripts/admin/grant_beta_access.sh test-employee@company.com

# Test revoking permissions  
./scripts/admin/grant_beta_access.sh test-employee@company.com --revoke
```

### 2. Test Frontend Integration

1. **Login as employee** with permissions
2. **Check dashboard** - should see Beta Access Management section
3. **Try invalid email** - should show error message
4. **Send valid invitation** - should show success message
5. **Login as employee** without permissions - section should be hidden

### 3. Test Email Flow

1. **Send invitation** through web interface
2. **Check recipient email** - should receive invitation
3. **Test signup flow** - recipient should be able to create account
4. **Verify account** - should be in beta-testers-v2 group

### 4. Test Error Handling

1. **Network errors** - should show appropriate error messages
2. **Invalid emails** - should validate and show errors
3. **Duplicate invitations** - should handle gracefully
4. **Permission revocation** - UI should disappear immediately

## 🔧 API Endpoints

### Check Permission
```
GET /admin/beta-access/check-permission
Authorization: Bearer {jwt-token}

Response:
{
  "has_beta_access_permission": true,
  "user_email": "employee@company.com",
  "user_id": "uuid"
}
```

### Send Invitation
```
POST /admin/beta-access/send-invitation
Authorization: Bearer {jwt-token}
Content-Type: application/json

Body:
{
  "email": "newuser@example.com",
  "name": "Optional Name"
}

Response:
{
  "success": true,
  "message": "Invitation sent successfully",
  "email": "newuser@example.com"
}
```

## 🐛 Troubleshooting

### Common Issues

1. **"API not configured" error**
   - Check `NEXT_PUBLIC_BETA_ACCESS_API_URL` environment variable
   - Verify CDK deployment completed successfully

2. **Permission denied errors**
   - Run `./scripts/admin/grant_beta_access.sh employee@email.com`
   - Check employee exists in Cognito pool first

3. **Email not sending**
   - Verify SES permissions in Lambda role
   - Check CloudWatch logs for detailed errors

4. **UI not appearing**
   - Check browser console for JavaScript errors
   - Verify employee has correct permissions in DynamoDB

### Debug Commands

```bash
# Check if permissions table exists
aws dynamodb describe-table --table-name Spaceport-BetaAccessPermissions

# Check employee permissions
aws dynamodb get-item \
  --table-name Spaceport-BetaAccessPermissions \
  --key '{"user_id": {"S": "employee-user-id"}}'

# Check CloudWatch logs
aws logs tail /aws/lambda/Spaceport-BetaAccessAdmin --follow
```

## 📊 Monitoring

### Key Metrics
- **Invitation Success Rate**: Monitor successful vs failed invitations
- **Permission Usage**: Track which employees use the feature
- **Error Rates**: Monitor API Gateway and Lambda errors

### CloudWatch Alarms
- **High Error Rate**: Alert if invitation failure rate > 10%
- **Permission Abuse**: Alert if single user sends > 50 invitations/hour
- **API Latency**: Alert if response time > 5 seconds

## 🔄 Maintenance

### Regular Tasks
1. **Review Permissions**: Quarterly review of who has beta access admin rights
2. **Clean Up**: Remove permissions for employees who leave the company
3. **Monitor Usage**: Review CloudWatch logs for unusual activity

### Updates
- **Frontend Updates**: Deploy through normal CI/CD process
- **Backend Updates**: Deploy through CDK stack updates
- **Permission Changes**: Use CLI script for immediate effect

## 📝 Integration Notes

### Existing Systems
- **Preserves CLI Tool**: Original `invite_user.sh` still works for admin use
- **Same Email Flow**: Uses identical invitation email template and process
- **Cognito Integration**: Works with existing user pool and groups
- **Dashboard Integration**: Seamlessly integrated with existing UI patterns

### Future Enhancements
- **Bulk Invitations**: Upload CSV for multiple invitations
- **Invitation History**: Track sent invitations per employee
- **Advanced Permissions**: Role-based permissions (e.g., department-specific)
- **Usage Analytics**: Dashboard showing invitation statistics

This system provides a secure, user-friendly way for employees to manage beta access invitations while maintaining all existing functionality and security measures.