# 🚀 Stripe Subscription System Setup Guide

This guide walks you through setting up Stripe for the Spaceport subscription system, including products, prices, webhooks, and testing.

## 📋 Prerequisites

- Stripe account (already have)
- AWS CDK access
- Environment variables configured

## 🔧 Step 1: Stripe Dashboard Setup

### 1.1 Create Products

Navigate to **Products** in your Stripe dashboard and create the following products:

#### Single Model Plan
- **Name**: Single Model
- **Description**: One active 3D model with premium features
- **Metadata**: 
  - `plan_type`: single
  - `max_models`: 1
  - `support_level`: email

#### Starter Plan
- **Name**: Starter
- **Description**: Up to 5 active 3D models
- **Metadata**:
  - `plan_type`: starter
  - `max_models`: 5
  - `support_level`: priority

#### Growth Plan
- **Name**: Growth
- **Description**: Up to 20 active 3D models
- **Metadata**:
  - `plan_type`: growth
  - `max_models`: 20
  - `support_level`: dedicated

### 1.2 Create Prices

For each product, create a **Recurring Price**:

#### Single Model Price
- **Amount**: $29.00
- **Currency**: USD
- **Billing**: Monthly
- **Trial period**: 30 days
- **Price ID**: Copy this - you'll need it for environment variables

#### Starter Price
- **Amount**: $99.00
- **Currency**: USD
- **Billing**: Monthly
- **Trial period**: 30 days
- **Price ID**: Copy this

#### Growth Price
- **Amount**: $299.00
- **Currency**: USD
- **Billing**: Monthly
- **Trial period**: 30 days
- **Price ID**: Copy this

## 🔗 Step 2: Webhook Configuration

### 2.1 Create Webhook Endpoint

1. Go to **Developers > Webhooks** in Stripe
2. Click **Add endpoint**
3. Set **Endpoint URL** to: `{YOUR_API_URL}/webhook`
4. Select these events to send:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Click **Add endpoint**
6. **Copy the webhook signing secret** - you'll need this for environment variables

## 🌍 Step 3: Environment Configuration

### 3.1 Backend Environment Variables

Add these to your environment or `.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_live_... # Use sk_test_ for development
STRIPE_PUBLISHABLE_KEY=pk_live_... # Use pk_test_ for development
STRIPE_WEBHOOK_SECRET=whsec_... # From webhook setup

# Stripe Price IDs
STRIPE_PRICE_SINGLE=price_... # Single model price ID
STRIPE_PRICE_STARTER=price_... # Starter price ID
STRIPE_PRICE_GROWTH=price_... # Growth price ID

# Referral Configuration
REFERRAL_KICKBACK_PERCENTAGE=10
COFOUNDER_KICKBACK_PERCENTAGE=30
REFERRAL_DURATION_MONTHS=6

# Co-founder User ID (Cognito username)
COFOUNDER_USER_ID=your_cofounder_username

# Frontend URL
FRONTEND_URL=https://spcprt.com
```

### 3.2 Frontend Environment Variables

Create `web/.env.local`:

```bash
# Stripe Configuration
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_... # Same as backend

# Subscription API
NEXT_PUBLIC_SUBSCRIPTION_API_URL={YOUR_API_URL}

# Referral Configuration
NEXT_PUBLIC_REFERRAL_KICKBACK_PERCENTAGE=10
NEXT_PUBLIC_COFOUNDER_KICKBACK_PERCENTAGE=30
NEXT_PUBLIC_REFERRAL_DURATION_MONTHS=6
```

## 🚀 Step 4: Deployment

### 4.1 Deploy Infrastructure

```bash
# Run the deployment script
./scripts/deployment/deploy_subscriptions.sh

# Or manually deploy CDK
cd infrastructure/spaceport_cdk
npx cdk deploy SpaceportSubscriptionStack
```

### 4.2 Update Webhook URL

After deployment, update your Stripe webhook endpoint URL with the new API Gateway URL from the CDK output.

## 🧪 Step 5: Testing

### 5.1 Test Cards

Use these Stripe test cards:

#### Successful Payment
- **Number**: 4242 4242 4242 4242
- **Expiry**: Any future date
- **CVC**: Any 3 digits
- **ZIP**: Any 5 digits

#### Declined Payment
- **Number**: 4000 0000 0000 0002
- **Expiry**: Any future date
- **CVC**: Any 3 digits
- **ZIP**: Any 5 digits

#### Insufficient Funds
- **Number**: 4000 0000 0000 9995
- **Expiry**: Any future date
- **CVC**: Any 3 digits
- **ZIP**: Any 5 digits

### 5.2 Test Flow

1. **Create Account**: Sign up with a new email
2. **Choose Plan**: Select any subscription plan
3. **Enter Referral**: Use a referral code if testing referral system
4. **Complete Payment**: Use test card details
5. **Verify Webhook**: Check Lambda logs for webhook processing
6. **Check Database**: Verify subscription data in DynamoDB
7. **Test Features**: Verify subscription gating works

## 🔍 Step 6: Monitoring

### 6.1 CloudWatch Logs

Monitor these Lambda functions:
- `Spaceport-SubscriptionManager`

### 6.2 Stripe Dashboard

Monitor:
- **Payments**: Successful/failed transactions
- **Subscriptions**: Active/canceled subscriptions
- **Webhooks**: Delivery success/failure rates
- **Customers**: New customer acquisition

### 6.3 Key Metrics

Track these business metrics:
- **Conversion Rate**: % of users who subscribe
- **Churn Rate**: % of users who cancel
- **Referral Effectiveness**: % using referral codes
- **Revenue per User**: Average subscription value

## 🚨 Troubleshooting

### Common Issues

#### Webhook Failures
- **Symptom**: Webhook events not being processed
- **Solution**: Check webhook secret, verify endpoint URL, check Lambda logs

#### Payment Failures
- **Symptom**: Users can't complete payment
- **Solution**: Verify Stripe keys, check checkout session creation

#### Referral Issues
- **Symptom**: Referral codes not working
- **Solution**: Check user handle format, verify referral tracking logic

#### Subscription Gating
- **Symptom**: Users can't access premium features
- **Solution**: Check subscription status, verify Cognito attributes

### Debug Commands

```bash
# Check Lambda logs
aws logs tail /aws/lambda/Spaceport-SubscriptionManager --follow

# Test webhook endpoint
curl -X POST {YOUR_API_URL}/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Check DynamoDB table
aws dynamodb scan --table-name Spaceport-Subscriptions
```

## 🔐 Security Considerations

### 1. API Keys
- **Never commit** Stripe keys to version control
- Use environment variables for all sensitive data
- Rotate keys regularly

### 2. Webhook Security
- Always verify webhook signatures
- Use HTTPS for all webhook endpoints
- Monitor webhook delivery failures

### 3. Data Protection
- Encrypt sensitive data at rest
- Use least-privilege IAM policies
- Monitor access logs

## 📈 Production Readiness

### 1. Load Testing
- Test with realistic user volumes
- Monitor Lambda cold starts
- Verify DynamoDB performance

### 2. Error Handling
- Implement comprehensive error logging
- Set up CloudWatch alarms
- Create runbooks for common issues

### 3. Backup & Recovery
- Enable DynamoDB point-in-time recovery
- Document recovery procedures
- Test backup restoration

## 🎯 Next Steps

After successful setup:

1. **Monitor Performance**: Watch metrics and logs
2. **Optimize**: Tune Lambda memory/timeout settings
3. **Scale**: Add CloudWatch alarms and auto-scaling
4. **Enhance**: Add more subscription features
5. **Analytics**: Implement detailed reporting

## 📞 Support

For issues:
1. Check CloudWatch logs first
2. Review Stripe dashboard for payment issues
3. Verify environment variables
4. Check CDK deployment status
5. Contact development team

---

**Last Updated**: Initial setup guide
**Status**: Ready for deployment 🚀
