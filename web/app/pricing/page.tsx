'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSubscription } from '../hooks/useSubscription';
import { configureAmplify } from '../amplifyClient';
import { Auth } from 'aws-amplify';

export const runtime = 'edge';

export default function Pricing(): JSX.Element {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { redirectToCheckout, loading: subscriptionLoading } = useSubscription();

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
          const { plan, referral } = JSON.parse(selectedPlanStr);
          sessionStorage.removeItem('selectedPlan');
          console.log('Found pending plan selection, starting checkout:', plan);
          await redirectToCheckout(plan, referral);
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
    if (isAuthenticated === false) {
      // Redirect to auth page with plan selection
      router.push(`/auth?redirect=pricing&plan=${planType}`);
      return;
    }
    
    if (isAuthenticated === true) {
      try {
        await redirectToCheckout(planType);
      } catch (error) {
        console.error('Subscription error:', error);
      }
    }
  };

  return (
    <>
      <section className="section" id="pricing-header">
        <h1>Pricing.</h1>
        <p><span className="inline-white">Be among the first to capture the imagination of your buyers like never before. Each model includes a 1-month free trial for the $29/mo hosting.</span></p>

      </section>
      <section className="section" id="pricing">
        <div className="pricing-grid">
          <div className="pricing-card">
            <h2>Single model.</h2>
            <div className="price">$29/mo</div>
            <p>Subscribe per model. Ideal for one-off projects or trying Spaceport with a single active model.</p>

            <button 
              onClick={() => handleSubscribe('single')} 
              className="cta-button"
              disabled={isLoading || subscriptionLoading}
            >
              {(() => {
                console.log('Button render - isAuthenticated:', isAuthenticated, 'isLoading:', isLoading, 'subscriptionLoading:', subscriptionLoading);
                if (isLoading) return 'Loading...';
                if (isAuthenticated === false) return 'Sign in to Subscribe';
                if (subscriptionLoading) return 'Loading...';
                return 'Get started';
              })()}
            </button>
          </div>

          <div className="pricing-card">
            <h2>Starter (up to 5 models).</h2>
            <div className="price">$99/mo</div>
            <p>Includes up to five active models. Need more? Add additional models at $29/mo each.</p>
            <button 
              onClick={() => handleSubscribe('starter')} 
              className="cta-button"
              disabled={isLoading || subscriptionLoading}
            >
              {isLoading ? 'Loading...' : 
               isAuthenticated === false ? 'Sign in to Subscribe' : 
               subscriptionLoading ? 'Loading...' : 'Start Starter'}
            </button>
          </div>

          <div className="pricing-card">
            <h2>Growth (up to 20 models).</h2>
            <div className="price">$299/mo</div>
            <p>Includes up to twenty active models. Additional models are $29/mo each beyond your plan.</p>
            <button 
              onClick={() => handleSubscribe('growth')} 
              className="cta-button"
              disabled={isLoading || subscriptionLoading}
            >
              {isLoading ? 'Loading...' : 
               isAuthenticated === false ? 'Sign in to Subscribe' : 
               subscriptionLoading ? 'Loading...' : 'Start Growth'}
            </button>
          </div>

          <div className="pricing-card">
            <h2>Enterprise.</h2>
            <p>High-volume or specialized projects? We'll tailor a plan for teams with larger model counts or specific needs.</p>

            <a href="mailto:gabriel@spcprt.com?subject=Enterprise%20Pricing%20Inquiry&body=Hello%2C%20I%27m%20interested%20in%20learning%20more%20about%20enterprise%20pricing%20at%20Spaceport." className="cta-button">Contact Us</a>

          </div>
        </div>
        <p style={{ marginTop: '24px' }}>All plans support additional active models at <span className="inline-white">$29/mo</span> per model beyond your plan.</p>

      </section>
    </>
  );
}