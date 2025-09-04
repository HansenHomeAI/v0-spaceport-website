# User Migration Guide: Staging to Production

This guide covers the complete process of migrating users from the staging Cognito pool to the production pool, including all user data and handling password resets.

## 🎯 Overview

When you merge the updated CDK code to main, it will create a new production user pool (`Spaceport-Users-prod`). This guide explains how to safely migrate existing users and their data to the new production environment.

## 📋 Prerequisites

- ✅ Updated CDK code deployed to main branch
- ✅ Production user pool created (`Spaceport-Users-prod`)
- ✅ AWS credentials configured for production account
- ✅ Python 3.x and boto3 installed
- ✅ Access to both staging and production AWS accounts

## 🔄 Migration Process

### Step 1: Verify Production Pool Creation

After merging to main, verify the production pool was created:

```bash
# Check production account
export AWS_PROFILE=spaceport-prod
aws cognito-idp list-user-pools --region us-west-2 --max-results 50
```

You should see `Spaceport-Users-prod` in the list.

### Step 2: Update Migration Script Configuration

Edit `scripts/admin/migrate_users_to_production.py`:

```python
# Update these values with your actual pool IDs
SOURCE_POOL_ID = "us-west-2_a2jf3ldGV"  # Your staging pool
TARGET_POOL_ID = "us-west-2_XXXXX"      # Your new production pool ID
```

### Step 3: Run Dry Run Migration

Test the migration process without making changes:

```bash
cd scripts/admin
./run_migration.sh
```

This will:
- ✅ Show what users would be migrated
- ✅ Check for potential issues
- ✅ Verify AWS permissions
- ✅ No actual changes made

### Step 4: Perform Live Migration

When ready for the actual migration:

```bash
./run_migration.sh --live
```

This will:
- ✅ Create users in production pool
- ✅ Migrate all user data (projects, profiles)
- ✅ Send password reset emails
- ✅ Log all actions

## 🔧 What Gets Migrated

### ✅ User Accounts
- Email addresses
- User attributes
- Account status (CONFIRMED users only)

### ✅ User Data
- Projects (from `Spaceport-Projects-staging` to `Spaceport-Projects-prod`)
- User profiles (from `Spaceport-Users-staging` to `Spaceport-Users-prod`)
- All project metadata and file references

### ❌ What Doesn't Get Migrated
- **Passwords** (AWS security policy prevents this)
- **User IDs** (new pool = new user IDs)
- **Session tokens** (users must sign in again)

## 📧 Password Reset Process

### How It Works
1. **Migration script** creates users with temporary passwords
2. **Cognito automatically** sends "Reset your password" emails
3. **Users click** email link and set new passwords
4. **Users sign in** with new passwords

### User Experience
```
User receives email: "Reset your Spaceport password"
↓
User clicks link → Goes to password reset page
↓
User enters new password → Password updated
↓
User can sign in normally
```

## 🎯 Frontend Integration

### Forgot Password Flow
The frontend now includes a complete forgot password flow:

1. **"Forgot your password?"** link on sign-in page
2. **Email input** for password reset request
3. **Code verification** from email
4. **New password** setup
5. **Success confirmation** and return to sign-in

### Features
- ✅ Mobile-friendly design
- ✅ Loading states and error handling
- ✅ Password visibility toggle
- ✅ Form validation
- ✅ Success/error messaging

## 🚨 Important Considerations

### Before Migration
- ✅ **Backup staging data** (just in case)
- ✅ **Test with small batch** first
- ✅ **Communicate with users** about the change
- ✅ **Have rollback plan** ready

### During Migration
- ✅ **Monitor migration logs** for errors
- ✅ **Check email delivery** status
- ✅ **Verify data integrity** after migration

### After Migration
- ✅ **Update GitHub secrets** to point to production pool
- ✅ **Test user sign-in** with new passwords
- ✅ **Monitor for issues** in production

## 🔍 Troubleshooting

### Common Issues

#### "User already exists in target pool"
- **Cause**: User was previously migrated
- **Solution**: Skip user (already handled by script)

#### "Failed to send reset email"
- **Cause**: Email service issues or invalid email
- **Solution**: Check Cognito email configuration

#### "Error migrating projects"
- **Cause**: DynamoDB permissions or table issues
- **Solution**: Verify table names and permissions

#### "Password reset link not working"
- **Cause**: Frontend not configured for production pool
- **Solution**: Update GitHub secrets and redeploy frontend

### Debugging Commands

```bash
# Check user count in pools
aws cognito-idp list-users --user-pool-id SOURCE_POOL_ID --profile spaceport-dev
aws cognito-idp list-users --user-pool-id TARGET_POOL_ID --profile spaceport-prod

# Check DynamoDB tables
aws dynamodb scan --table-name Spaceport-Projects-staging --profile spaceport-dev
aws dynamodb scan --table-name Spaceport-Projects-prod --profile spaceport-prod

# Check migration logs
cat migration_log_YYYYMMDD_HHMMSS.json
```

## 📊 Migration Monitoring

### Key Metrics to Track
- **Migration success rate** (should be 100%)
- **Password reset email delivery** (check SES metrics)
- **User sign-in success** (monitor auth logs)
- **Data integrity** (verify project counts)

### Log Files
- `migration_log_YYYYMMDD_HHMMSS.json` - Detailed migration log
- CloudWatch logs for Cognito and DynamoDB operations
- SES delivery logs for password reset emails

## 🎯 Rollback Plan

If issues occur, you can rollback by:

1. **Keep staging pool active** (don't delete it)
2. **Update GitHub secrets** back to staging pool
3. **Redeploy frontend** to use staging
4. **Communicate with users** about temporary rollback

## 📞 User Communication

### Email Template
```
Subject: Spaceport Account Update - Action Required

Hi [User Name],

We're upgrading Spaceport to a new, more secure system. Your account has been migrated to the new system.

To access your account:
1. Click "Forgot Password?" on the sign-in page
2. Enter your email address
3. Check your email for a reset link
4. Set a new password
5. Sign in normally

All your projects and data have been preserved.

If you have any issues, please contact support.

Best regards,
The Spaceport Team
```

## ✅ Success Checklist

- [ ] Production pool created successfully
- [ ] Migration script configured with correct pool IDs
- [ ] Dry run completed without errors
- [ ] Live migration completed successfully
- [ ] All users received password reset emails
- [ ] GitHub secrets updated to production pool
- [ ] Frontend deployed with new configuration
- [ ] Users can sign in with new passwords
- [ ] All user data accessible in production
- [ ] Monitoring and alerting configured

## 🎯 Next Steps

After successful migration:

1. **Monitor production** for any issues
2. **Clean up staging** resources (optional)
3. **Update documentation** with new pool IDs
4. **Plan future migrations** (if needed)

---

**Need Help?** Check the migration logs or contact the development team for assistance.
