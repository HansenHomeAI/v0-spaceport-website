# Beta Invitation Feature Guide

## Overview
The Beta Invitation feature allows designated employees to invite new users to the Spaceport beta program directly through the web dashboard. This replaces the need for employees to use CLI tools, providing a user-friendly interface for managing beta access.

## 🚀 Features

### For Administrators
- **CLI Management**: Grant or revoke beta invitation permissions for specific employees
- **Permission Control**: Fine-grained control over who can invite beta users
- **Audit Trail**: All invitations are logged with requester information

### For Employees
- **Web Interface**: Clean, intuitive form integrated into the dashboard
- **Email Validation**: Automatic email format validation
- **Real-time Feedback**: Success/error messages with proper handling
- **Responsive Design**: Works seamlessly on desktop and mobile

## 🏗️ Architecture

### Backend Components
1. **Lambda Function**: `Spaceport-BetaInviteManager-{env}`
   - Permission checking via Cognito custom attributes
   - Invitation sending through existing invite API
   - Comprehensive error handling and logging

2. **API Gateway**: RESTful endpoints with Cognito authorization
   - `GET /beta-invite/check-permission` - Check if user can invite
   - `POST /beta-invite/send-invitation` - Send beta invitation

3. **Cognito Custom Attribute**: `custom:can_invite_beta`
   - Controls access to the invitation feature
   - Managed via CLI tool for administrators

### Frontend Components
1. **BetaInviteCard**: React component that appears on dashboard
   - Only visible to users with permission
   - Form validation and error handling
   - Consistent with existing UI design

2. **API Integration**: Uses centralized API configuration
   - Proper authentication headers
   - Error handling and user feedback

## 📋 Setup Instructions

### 1. Deploy Infrastructure
```bash
# Deploy the updated auth stack with beta invite resources
cd infrastructure/spaceport_cdk
cdk deploy SpaceportAuthStack

# Note the BetaInviteApiUrl output for environment configuration
```

### 2. Configure Environment Variables
Add to your `.env` file:
```bash
# Beta Invite API URL (from CDK output)
NEXT_PUBLIC_BETA_INVITE_API_URL=https://your-api-id.execute-api.us-west-2.amazonaws.com/prod

# Invite API Key (if using API key authentication)
INVITE_API_KEY=your-invite-api-key
```

### 3. Grant Employee Permissions
Use the CLI tool to grant beta invitation access to employees:

```bash
# Grant permission
./scripts/admin/manage_beta_invite_access.sh employee@company.com grant

# Check permission status
./scripts/admin/manage_beta_invite_access.sh employee@company.com check

# Revoke permission
./scripts/admin/manage_beta_invite_access.sh employee@company.com revoke
```

## 🎯 Usage Guide

### For Administrators

#### Granting Access to Employees
```bash
# Make the script executable (first time only)
chmod +x scripts/admin/manage_beta_invite_access.sh

# Grant beta invitation access to an employee
./scripts/admin/manage_beta_invite_access.sh john@company.com grant

# Verify the permission was set
./scripts/admin/manage_beta_invite_access.sh john@company.com check
```

#### Revoking Access
```bash
# Remove beta invitation access from an employee
./scripts/admin/manage_beta_invite_access.sh john@company.com revoke
```

### For Employees

#### Using the Web Interface
1. **Login** to your Spaceport dashboard
2. **Locate** the "Invite Beta Users" card (only appears if you have permission)
3. **Enter** the email address of the person to invite
4. **Optionally** enter their full name for personalization
5. **Click** "Send Invitation" to send the beta access email

#### What Happens After Sending
- The user receives a personalized email with setup instructions
- They get a temporary password to sign in at `spcprt.com/create`
- The invitation is logged in CloudWatch for audit purposes
- You receive immediate feedback on success or failure

## 🔧 Technical Details

### Permission System
- Uses Cognito custom attribute: `custom:can_invite_beta=true`
- Checked on every API request for security
- Can be managed only via CLI by administrators

### Security Features
- **Authentication Required**: All endpoints require valid Cognito JWT
- **Permission Validation**: Double-checked on backend
- **Input Validation**: Email format validation on frontend and backend
- **Rate Limiting**: Inherits from API Gateway default limits

### Integration with Existing System
- **Reuses Invite API**: Leverages existing invitation infrastructure
- **Consistent Styling**: Matches dashboard design patterns
- **Error Handling**: Uses established error handling patterns
- **Logging**: Integrates with CloudWatch logging

## 🚨 Troubleshooting

### Common Issues

#### "You do not have permission to invite beta users"
**Cause**: User doesn't have the `custom:can_invite_beta` attribute set to `true`
**Solution**: Admin needs to run the grant command:
```bash
./scripts/admin/manage_beta_invite_access.sh user@company.com grant
```

#### Beta Invite Card Not Appearing
**Possible Causes**:
1. User doesn't have permission (check with CLI tool)
2. API configuration issue (check environment variables)
3. Authentication issue (check browser console for errors)

#### "Network error. Please try again."
**Possible Causes**:
1. API Gateway endpoint not configured
2. Lambda function deployment issue
3. CORS configuration problem

**Debug Steps**:
```bash
# Check if the Lambda function exists
aws lambda get-function --function-name Spaceport-BetaInviteManager-prod

# Check API Gateway endpoint
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://your-api-id.execute-api.us-west-2.amazonaws.com/prod/beta-invite/check-permission
```

### Logging and Monitoring
- **CloudWatch Logs**: Check `/aws/lambda/Spaceport-BetaInviteManager-{env}`
- **API Gateway Logs**: Monitor request/response patterns
- **Frontend Console**: Check browser console for client-side errors

## 🔮 Future Enhancements

### Planned Features
1. **Bulk Invitations**: Upload CSV to invite multiple users
2. **Invitation History**: View previously sent invitations
3. **Usage Analytics**: Track invitation success rates
4. **Custom Email Templates**: Customize invitation email content

### Scalability Considerations
- Lambda function can handle concurrent requests
- DynamoDB for invitation tracking (future enhancement)
- CloudWatch metrics for monitoring usage

## 📝 Maintenance

### Regular Tasks
1. **Monitor Usage**: Check CloudWatch metrics monthly
2. **Review Permissions**: Audit employee permissions quarterly
3. **Update Dependencies**: Keep Lambda runtime updated
4. **Test Functionality**: Verify end-to-end flow monthly

### Backup and Recovery
- Cognito user attributes are automatically backed up
- Lambda function code is version controlled
- API Gateway configuration is managed via CDK

---

**Last Updated**: 2024-01-XX  
**Version**: 1.0  
**Status**: Production Ready ✅