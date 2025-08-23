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
  planFeatures: {
    maxModels: number;
    support: string;
    trialDays: number;
  };
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
      setError(err instanceof Error ? err.message : 'Failed to fetch subscription');
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
      
      const session = await Auth.currentSession();
      const idToken = session.getIdToken().getJwtToken();
      
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
  const canCreateModel = useCallback(() => {
    if (!subscription) return false;
    
    const { planFeatures } = subscription;
    if (planFeatures.maxModels === -1) return true; // Unlimited
    
    // TODO: Get actual model count from user's projects
    const currentModelCount = 0; // This should come from your projects API
    
    return currentModelCount < planFeatures.maxModels;
  }, [subscription]);

  // Get plan features
  const getPlanFeatures = useCallback(() => {
    if (!subscription) return null;
    return subscription.planFeatures;
  }, [subscription]);

  // Check if subscription is active
  const isSubscriptionActive = useCallback(() => {
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
