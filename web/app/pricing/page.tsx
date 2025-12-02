'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useSubscription } from '../hooks/useSubscription';
import { configureAmplify } from '../amplifyClient';
import { Auth } from 'aws-amplify';
import { trackEvent, AnalyticsEvents } from '../../lib/analytics';

export const runtime = 'edge';

export default function Pricing(): JSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { redirectToCheckout, loading: subscriptionLoading } = useSubscription();

  const referralCode = useMemo(() => {
    const value = searchParams.get('ref') || searchParams.get('referral');
    return value ? value.trim() : null;
  }, [searchParams]);

  useEffect(() => {
    console.log('Pricing page useEffect running...');
    
    // Configure Amplify and check authentication status
    const amplifyConfigured = configureAmplify();
    console.log('Amplify configured:', amplifyConfigured);
    
    const checkAuth = async () => {
      try {
        console.log('Checking authentication...');
        await Auth.currentAuthenticatedUser();
        console.log('User is authenticated');
        setIsAuthenticated(true);
        setIsLoading(false);
        
        // Check for pending plan selection
        const selectedPlanStr = sessionStorage.getItem('selectedPlan');
        if (selectedPlanStr) {
          try {
            const { plan, referral } = JSON.parse(selectedPlanStr);
            sessionStorage.removeItem('selectedPlan');
            console.log('Found pending plan selection, starting checkout:', plan);
            await redirectToCheckout(plan, referral || undefined);
          } catch (parseError) {
            console.error('Failed to parse pending plan selection', parseError);
            sessionStorage.removeItem('selectedPlan');
          }
        }
      } catch (error) {
        console.log('User is not authenticated:', error);
        setIsAuthenticated(false);
        setIsLoading(false);
      }
    };
    
    checkAuth();
  }, [redirectToCheckout]);

  const handleSubscribe = async (planType: 'single' | 'starter' | 'growth') => {
    trackEvent(AnalyticsEvents.BUTTON_CLICK, {
      action: 'subscribe_plan',
      plan_type: planType,
      page: 'pricing',
      is_authenticated: isAuthenticated
    });

    if (isAuthenticated === false) {
      // Persist choice so we can resume checkout after authentication
      if (typeof window !== 'undefined') {
        window.sessionStorage.setItem(
          'selectedPlan',
          JSON.stringify({ plan: planType, referral: referralCode || null })
        );
      }

      const params = new URLSearchParams({ redirect: 'pricing', plan: planType });
      if (referralCode) params.set('ref', referralCode);
      router.push(`/auth?${params.toString()}`);
      return;
    }
    
    if (isAuthenticated === true) {
      try {
        await redirectToCheckout(planType, referralCode || undefined);
      } catch (error) {
        console.error('Subscription error:', error);
        trackEvent(AnalyticsEvents.ERROR_OCCURRED, {
          error_message: error instanceof Error ? error.message : 'Unknown error',
          context: 'subscription_checkout',
          plan_type: planType
        });
      }
    }
  };

  return (
    <>
      <section className="section" id="pricing-header">
        <h1>Pricing.</h1>
        <p><span className="inline-white">Be among the first to capture the imagination of your buyers like never before.</span></p>

      </section>
      <section className="section" id="pricing">
        <div className="pricing-grid">
          <div className="pricing-card">
            <h2>Single model.</h2>
            <div className="price">$29/mo</div>
            <p>Subscribe per model. Ideal for one-off projects or trying Spaceport with a single active model.</p>

            <a 
              href="#" 
              onClick={(e) => {
                e.preventDefault();
                handleSubscribe('single');
              }}
              className="cta-button"
              style={{ 
                opacity: (isLoading || subscriptionLoading) ? 0.6 : 1,
                cursor: (isLoading || subscriptionLoading) ? 'not-allowed' : 'pointer',
                pointerEvents: (isLoading || subscriptionLoading) ? 'none' : 'auto'
              }}
            >
              {(() => {
                console.log('Button render - isAuthenticated:', isAuthenticated, 'isLoading:', isLoading, 'subscriptionLoading:', subscriptionLoading);
                if (isLoading) return 'Loading...';
                if (isAuthenticated === false) return 'Sign in to Subscribe';
                if (subscriptionLoading) return 'Loading...';
                return 'Get started';
              })()}
            </a>
          </div>

          <div className="pricing-card">
            <h2>Starter (up to 5 models).</h2>
            <div className="price">$99/mo</div>
            <p>Includes up to five active models. Need more? Add additional models at $29/mo each.</p>
            <a 
              href="#" 
              onClick={(e) => {
                e.preventDefault();
                handleSubscribe('starter');
              }}
              className="cta-button"
              style={{ 
                opacity: (isLoading || subscriptionLoading) ? 0.6 : 1,
                cursor: (isLoading || subscriptionLoading) ? 'not-allowed' : 'pointer',
                pointerEvents: (isLoading || subscriptionLoading) ? 'none' : 'auto'
              }}
            >
              {isLoading ? 'Loading...' : 
               isAuthenticated === false ? 'Sign in to Subscribe' : 
               subscriptionLoading ? 'Loading...' : 'Start Starter'}
            </a>
          </div>

          <div className="pricing-card">
            <h2>Growth (up to 20 models).</h2>
            <div className="price">$299/mo</div>
            <p>Includes up to twenty active models. Additional models are $29/mo each beyond your plan.</p>
            <a 
              href="#" 
              onClick={(e) => {
                e.preventDefault();
                handleSubscribe('growth');
              }}
              className="cta-button"
              style={{ 
                opacity: (isLoading || subscriptionLoading) ? 0.6 : 1,
                cursor: (isLoading || subscriptionLoading) ? 'not-allowed' : 'pointer',
                pointerEvents: (isLoading || subscriptionLoading) ? 'none' : 'auto'
              }}
            >
              {isLoading ? 'Loading...' : 
               isAuthenticated === false ? 'Sign in to Subscribe' : 
               subscriptionLoading ? 'Loading...' : 'Start Growth'}
            </a>
          </div>

          <div className="pricing-card">
            <h2>Enterprise.</h2>
            <p>High-volume or specialized projects? We&apos;ll tailor a plan for teams with larger model counts or specific needs.</p>

            <a href="mailto:gabriel@spcprt.com?subject=Enterprise%20Pricing%20Inquiry&body=Hello%2C%20I%27m%20interested%20in%20learning%20more%20about%20enterprise%20pricing%20at%20Spaceport." className="cta-button">Contact Us</a>

          </div>
        </div>
        <p style={{ marginTop: '24px' }}>All plans support additional active models at <span className="inline-white">$29/mo</span> per model beyond your plan.</p>

      </section>
    </>
  );
}
