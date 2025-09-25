# Analytics Stack Setup Guide

This guide walks you through setting up the complete analytics stack for Spaceport AI: **Cloudflare Web Analytics**, **Sentry**, and **PostHog**.

## 🎯 What You'll Get

- **Error Detection**: Real-time error tracking with Sentry
- **Traffic Insights**: Referrer tracking and geo data with Cloudflare
- **Feature Usage**: User behavior and funnel analysis with PostHog
- **Cookie-less**: Privacy-first approach, no cookies required

## ⚡ Quick Setup (15 minutes)

### 1. Cloudflare Web Analytics (2 minutes)

**Already deployed?** If your site is on Cloudflare, this is already working!

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select your domain
3. Go to **Analytics** → **Web Analytics**
4. Click **Enable Web Analytics**
5. **Done!** No code changes needed

**What you'll see:**
- Page views and unique visitors
- Traffic sources and referrers
- Geographic distribution
- Device and browser breakdown

### 2. Sentry Error Tracking (5 minutes)

1. **Create Sentry Account**
   - Go to [sentry.io](https://sentry.io)
   - Sign up for free account
   - Create new project (Next.js)

2. **Get Your DSN**
   - Copy the DSN from your project settings
   - Format: `https://your-dsn@sentry.io/project-id`

3. **Set Environment Variables**
   ```bash
   # Add to your .env.local file
   NEXT_PUBLIC_SENTRY_DSN=https://your-dsn@sentry.io/project-id
   SENTRY_ORG=your-org-slug
   SENTRY_PROJECT=your-project-slug
   SENTRY_AUTH_TOKEN=your-auth-token
   ```

4. **Deploy**
   - Push to GitHub to trigger deployment
   - Errors will start flowing in automatically

**What you'll see:**
- Real-time error notifications
- Stack traces with source maps
- Error frequency and impact
- User context and session replay

### 3. PostHog Feature Analytics (8 minutes)

1. **Create PostHog Account**
   - Go to [posthog.com](https://posthog.com)
   - Sign up for free account
   - Create new project

2. **Get Your Project Key**
   - Copy the project key from project settings
   - Format: `phc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

3. **Set Environment Variables**
   ```bash
   # Add to your .env.local file
   NEXT_PUBLIC_POSTHOG_KEY=phc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
   ```

4. **Deploy**
   - Push to GitHub to trigger deployment
   - Events will start flowing in automatically

**What you'll see:**
- User behavior funnels
- Feature usage analytics
- Custom event tracking
- Retention analysis

## 🔧 Environment Variables

Create a `.env.local` file in your `web/` directory:

```bash
# Sentry Configuration
NEXT_PUBLIC_SENTRY_DSN=https://your-dsn@sentry.io/project-id
SENTRY_ORG=your-org-slug
SENTRY_PROJECT=your-project-slug
SENTRY_AUTH_TOKEN=your-auth-token

# PostHog Configuration
NEXT_PUBLIC_POSTHOG_KEY=phc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com

# App Version (for release tracking)
NEXT_PUBLIC_APP_VERSION=1.0.0
```

## 📊 Dashboard Access

### Cloudflare Analytics
- **URL**: Cloudflare Dashboard → Analytics → Web Analytics
- **Access**: Your Cloudflare account
- **Data**: Real-time traffic insights

### Sentry
- **URL**: `https://sentry.io/organizations/your-org/projects/your-project/`
- **Access**: Your Sentry account
- **Data**: Error tracking and performance

### PostHog
- **URL**: `https://app.posthog.com/project/your-project`
- **Access**: Your PostHog account
- **Data**: Feature usage and funnels

## 🚨 Alerts Setup

### Sentry Alerts (Recommended)
1. Go to Sentry → Settings → Alerts
2. Create new alert rule:
   - **Trigger**: Error rate > 5% in 5 minutes
   - **Action**: Email notification
3. Add your team email addresses

### PostHog Alerts (Optional)
1. Go to PostHog → Settings → Alerts
2. Create alerts for:
   - Significant drop in daily active users
   - High error rates in key funnels

## 📈 Key Metrics to Monitor

### Error Tracking (Sentry)
- **Error Rate**: Should be < 1%
- **Critical Errors**: JavaScript errors, API failures
- **Performance**: Page load times, API response times

### Traffic Analytics (Cloudflare)
- **Traffic Sources**: Which channels drive users
- **Geographic Distribution**: Where users are located
- **Device Breakdown**: Mobile vs desktop usage

### Feature Usage (PostHog)
- **Key Funnels**: Landing → Create → Subscribe
- **Feature Adoption**: Which features are used most
- **User Retention**: Daily/weekly active users

## 🔍 Event Tracking

The following events are automatically tracked:

### Page Views
- All page visits with referrer and user agent
- Route changes in single-page app

### User Actions
- Button clicks on key actions
- Form submissions
- Subscription upgrades/cancellations

### ML Pipeline Events
- Job started/completed/failed
- Drone path calculations
- Error occurrences

### Business Events
- Pricing page views
- Create page visits
- Waitlist signups

## 🛠 Customization

### Adding New Events
```typescript
import { trackEvent, AnalyticsEvents } from '../lib/analytics';

// Track custom event
trackEvent('custom_action', {
  property1: 'value1',
  property2: 'value2'
});
```

### Error Tracking
```typescript
import { trackError } from '../lib/analytics';

try {
  // Your code
} catch (error) {
  trackError(error, { context: 'additional_info' });
}
```

## 🚀 Production Deployment

1. **Set Production Environment Variables**
   - Add all analytics variables to your production environment
   - Use production DSNs and keys

2. **Deploy**
   - Push to `main` branch
   - GitHub Actions will deploy automatically

3. **Verify**
   - Check Sentry for error events
   - Check PostHog for page views
   - Check Cloudflare for traffic data

## 🔒 Privacy & Compliance

- **Cookie-less**: No cookies are set by any analytics service
- **GDPR Compliant**: All services support GDPR requirements
- **Data Retention**: Configurable retention periods
- **User Consent**: Optional consent management integration

## 📞 Support

- **Cloudflare**: [Cloudflare Support](https://support.cloudflare.com)
- **Sentry**: [Sentry Documentation](https://docs.sentry.io)
- **PostHog**: [PostHog Docs](https://posthog.com/docs)

---

**Status**: ✅ Ready for Production
**Last Updated**: Today
**Next Steps**: Set up environment variables and deploy
