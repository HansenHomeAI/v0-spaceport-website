import { loadStripe } from '@stripe/stripe-js';

// Stripe configuration
export const stripeConfig = {
  publishableKey: process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || '',
  // Add any other Stripe-specific configuration here
};

// Load Stripe instance
export const getStripe = () => {
  if (!stripeConfig.publishableKey) {
    throw new Error('Stripe publishable key is not configured');
  }
  return loadStripe(stripeConfig.publishableKey);
};

// Subscription plan types
export const SUBSCRIPTION_PLANS = {
  SINGLE: 'single',
  STARTER: 'starter', 
  GROWTH: 'growth',
  ENTERPRISE: 'enterprise'
} as const;

export type SubscriptionPlanType = typeof SUBSCRIPTION_PLANS[keyof typeof SUBSCRIPTION_PLANS];

// Plan pricing information - CENTRALIZED CONFIGURATION
export const PLAN_PRICING = {
  [SUBSCRIPTION_PLANS.SINGLE]: {
    name: 'Single Model',
    price: 29,
    period: 'month',
    description: 'One active model with premium features',
    features: ['1 active model', 'Premium 3D models', 'Email support'],
    maxModels: 1,
    trialDays: 0,
    support: 'email'
  },
  [SUBSCRIPTION_PLANS.STARTER]: {
    name: 'Starter',
    price: 99,
    period: 'month',
    description: 'Up to five active models',
    features: ['Up to 5 active models', 'Premium 3D models', 'Priority support'],
    maxModels: 5,
    trialDays: 0,
    support: 'priority'
  },
  [SUBSCRIPTION_PLANS.GROWTH]: {
    name: 'Growth',
    price: 299,
    period: 'month',
    description: 'Up to twenty active models',
    features: ['Up to 20 active models', 'Premium 3D models', 'Dedicated support'],
    maxModels: 20,
    trialDays: 0,
    support: 'dedicated'
  },
  [SUBSCRIPTION_PLANS.ENTERPRISE]: {
    name: 'Enterprise',
    price: null,
    period: 'custom',
    description: 'Custom solutions for high-volume projects',
    features: ['High-volume projects', 'Custom integrations', 'Dedicated support', 'Team management'],
    maxModels: -1, // Unlimited
    trialDays: 0,
    support: 'dedicated'
  }
} as const;

// Referral system configuration
export const REFERRAL_CONFIG = {
  KICKBACK_PERCENTAGE: 10, // 10% for users
  EMPLOYEE_KICKBACK_PERCENTAGE: 30, // 30% of referee amount goes to employee
  COMPANY_KICKBACK_PERCENTAGE: 70, // 70% of referee amount goes to company
  DURATION_MONTHS: 6, // 6 months duration
} as const;

// Dynamic pricing getter - allows runtime updates
export const getPlanPricing = (planType: SubscriptionPlanType) => {
  return PLAN_PRICING[planType];
};

// Get all plan pricing for admin updates
export const getAllPlanPricing = () => {
  return PLAN_PRICING;
};
