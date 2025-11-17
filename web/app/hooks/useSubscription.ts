import { useState, useEffect, useCallback } from 'react';
import { Auth } from 'aws-amplify';
import { getStripe, SUBSCRIPTION_PLANS, type SubscriptionPlanType } from '../stripe';

export interface SubscriptionData {
  userId: string;
  subscriptionId: string;
  planType: SubscriptionPlanType;
  status: 'active' | 'past_due' | 'canceled' | 'trialing';
  createdAt: string;
  updatedAt: string;
  maxModels: number;  // Direct maxModels field for additive total
  support: string;    // Direct support field
  planFeatures: {
    maxModels: number;
    support: string;
    trialDays: number;
  };
  subscriptionHistory?: Array<{
    planType: string;
    modelIncrease: number;
    previousMax: number;
    newMax: number;
    timestamp: string;
  }>;
  referralCode?: string;
  referredBy?: string;
  referralEarnings?: number;
}

export interface CheckoutSession {
  sessionId: string;
  url: string;
}

export const useSubscription = () => {
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch subscription status
  const fetchSubscription = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Check if user is authenticated first
      const currentUser = await Auth.currentAuthenticatedUser();
      if (!currentUser) {
        console.log('No authenticated user, skipping subscription fetch');
        setLoading(false);
        return;
      }
      
      const session = await Auth.currentSession();
      const idToken = session.getIdToken().getJwtToken();
      
      const response = await fetch('/api/subscription-status', {
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch subscription status');
      }

      const data = await response.json();
      setSubscription(data.subscription);
    } catch (err) {
      console.error('Error fetching subscription:', err);
      // Don't set error for authentication issues - just use default beta
      if (err instanceof Error && !err.message.includes('No current user')) {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // Create checkout session
  const createCheckoutSession = useCallback(async (
    planType: SubscriptionPlanType,
    referralCode?: string
  ): Promise<CheckoutSession | null> => {
    try {
      setError(null);
      
      const session = await Auth.currentSession();
      const idToken = session.getIdToken().getJwtToken();
      const currentUser = await Auth.currentAuthenticatedUser();
      
      const response = await fetch('/api/create-checkout-session', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          planType,
          userId: currentUser.username,
          referralCode,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create checkout session');
      }

      const data = await response.json();
      return data;
    } catch (err) {
      console.error('Error creating checkout session:', err);
      setError(err instanceof Error ? err.message : 'Failed to create checkout session');
      return null;
    }
  }, []);

  // Redirect to Stripe checkout
  const redirectToCheckout = useCallback(async (
    planType: SubscriptionPlanType,
    referralCode?: string
  ) => {
    try {
      const checkoutSession = await createCheckoutSession(planType, referralCode);
      if (checkoutSession?.url) {
        // Redirect to Stripe checkout
        window.location.href = checkoutSession.url;
      }
    } catch (err) {
      console.error('Error redirecting to checkout:', err);
    }
  }, [createCheckoutSession]);

  // Cancel subscription
  const cancelSubscription = useCallback(async () => {
    try {
      setError(null);
      
      // Check if user is authenticated
      let idToken;
      try {
        const session = await Auth.currentSession();
        idToken = session.getIdToken().getJwtToken();
      } catch (authError) {
        console.error('User not authenticated, cannot cancel subscription');
        setError('You must be signed in to cancel your subscription');
        return;
      }
      
      const response = await fetch('/api/cancel-subscription', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to cancel subscription');
      }

      // Refresh subscription data
      await fetchSubscription();
    } catch (err) {
      console.error('Error canceling subscription:', err);
      setError(err instanceof Error ? err.message : 'Failed to cancel subscription');
    }
  }, [fetchSubscription]);

  // Check if user can create more models
  const canCreateModel = useCallback((currentModelCount: number = 0) => {
    if (!subscription) return true; // Default to allowing creation (beta access)
    
    const { planFeatures } = subscription;
    if (planFeatures.maxModels === -1) return true; // Unlimited
    
    return currentModelCount < planFeatures.maxModels;
  }, [subscription]);

  // Get plan features
  const getPlanFeatures = useCallback(() => {
    if (!subscription) {
      // Default beta plan features
      return {
        maxModels: 5,
        support: 'email'
      };
    }
    // Return the actual maxModels from the user's subscription (additive total)
    return {
      maxModels: subscription.maxModels || subscription.planFeatures?.maxModels || 5,
      support: subscription.support || subscription.planFeatures?.support || 'email'
    };
  }, [subscription]);

  // Check if subscription is active
  const isSubscriptionActive = useCallback(() => {
    if (!subscription) return true; // Beta access is considered active
    return subscription?.status === 'active' || subscription?.status === 'trialing';
  }, [subscription]);

  // Check if user is on trial
  const isOnTrial = useCallback(() => {
    return false; // NO TRIAL PERIODS in new structure
  }, []);

  // Get trial days remaining
  const getTrialDaysRemaining = useCallback(() => {
    return 0; // NO TRIAL PERIODS in new structure
  }, []);

  // Initialize subscription data
  useEffect(() => {
    fetchSubscription();
  }, [fetchSubscription]);

  return {
    subscription,
    loading,
    error,
    fetchSubscription,
    createCheckoutSession,
    redirectToCheckout,
    cancelSubscription,
    canCreateModel,
    getPlanFeatures,
    isSubscriptionActive,
    isOnTrial,
    getTrialDaysRemaining,
  };
};
