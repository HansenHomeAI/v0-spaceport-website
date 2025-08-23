'use client';
import { useState } from 'react';
import { useSubscription } from '../hooks/useSubscription';
import { SUBSCRIPTION_PLANS, PLAN_PRICING, type SubscriptionPlanType } from '../stripe';

export const runtime = 'edge';

export default function Pricing(): JSX.Element {
  const [referralCode, setReferralCode] = useState('');
  const [showReferralInput, setShowReferralInput] = useState(false);
  const { subscription, loading, redirectToCheckout, error } = useSubscription();

  const handleSubscribe = async (planType: SubscriptionPlanType) => {
    if (planType === 'enterprise') {
      // Handle enterprise contact
      window.location.href = 'mailto:gabriel@spcprt.com?subject=Enterprise%20Pricing%20Inquiry&body=Hello%2C%20I%27m%20interested%20in%20learning%20more%20about%20enterprise%20pricing%20at%20Spaceport.';
      return;
    }

    if (showReferralInput && referralCode.trim()) {
      await redirectToCheckout(planType, referralCode.trim());
    } else {
      await redirectToCheckout(planType);
    }
  };

  const getCurrentPlanBadge = (planType: SubscriptionPlanType) => {
    if (subscription?.planType === planType) {
      return (
        <span className="current-plan-badge">
          {subscription.status === 'trialing' ? 'Trial' : 'Current Plan'}
        </span>
      );
    }
    return null;
  };

  const getSubscribeButton = (planType: SubscriptionPlanType) => {
    if (planType === 'enterprise') {
      return (
        <button 
          className="cta-button enterprise-button"
          onClick={() => handleSubscribe(planType)}
        >
          Contact Sales
        </button>
      );
    }

    const isCurrentPlan = subscription?.planType === planType;
    const isActive = subscription?.status === 'active' || subscription?.status === 'trialing';

    if (isCurrentPlan && isActive) {
      return (
        <button className="cta-button current-plan-button" disabled>
          Current Plan
        </button>
      );
    }

    return (
      <button 
        className="cta-button"
        onClick={() => handleSubscribe(planType)}
        disabled={loading}
      >
        {loading ? 'Loading...' : 'Subscribe'}
      </button>
    );
  };

  return (
    <>
      <section className="section" id="pricing-header">
        <h1>Pricing.</h1>
        <p><span className="inline-white">Be among the first to capture the imagination of your buyers like never before. Each model includes premium 3D features and dedicated support.</span></p>
        
        {/* Referral Code Input */}
        <div className="referral-section">
          <button 
            className="referral-toggle"
            onClick={() => setShowReferralInput(!showReferralInput)}
          >
            {showReferralInput ? 'Hide' : 'Have a referral code?'}
          </button>
          
          {showReferralInput && (
            <div className="referral-input-container">
              <input
                type="text"
                placeholder="Enter referral code (e.g., johndoe)"
                value={referralCode}
                onChange={(e) => setReferralCode(e.target.value)}
                className="referral-input"
              />
              <p className="referral-info">
                Using a referral code? The referrer gets 10% of your subscription for 6 months!
              </p>
            </div>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
      </section>

      <section className="section" id="pricing">
        <div className="pricing-grid">
          <div className="pricing-card">
            <h2>{PLAN_PRICING[SUBSCRIPTION_PLANS.SINGLE].name}</h2>
            {getCurrentPlanBadge(SUBSCRIPTION_PLANS.SINGLE)}
            <div className="price">${PLAN_PRICING[SUBSCRIPTION_PLANS.SINGLE].price}<span className="period">/{PLAN_PRICING[SUBSCRIPTION_PLANS.SINGLE].period}</span></div>
            <p>{PLAN_PRICING[SUBSCRIPTION_PLANS.SINGLE].description}</p>
            <ul className="features-list">
              {PLAN_PRICING[SUBSCRIPTION_PLANS.SINGLE].features.map((feature, index) => (
                <li key={index}>{feature}</li>
              ))}
            </ul>
            {getSubscribeButton(SUBSCRIPTION_PLANS.SINGLE)}
          </div>

          <div className="pricing-card">
            <h2>{PLAN_PRICING[SUBSCRIPTION_PLANS.STARTER].name}</h2>
            {getCurrentPlanBadge(SUBSCRIPTION_PLANS.STARTER)}
            <div className="price">${PLAN_PRICING[SUBSCRIPTION_PLANS.STARTER].price}<span className="period">/{PLAN_PRICING[SUBSCRIPTION_PLANS.STARTER].period}</span></div>
            <p>{PLAN_PRICING[SUBSCRIPTION_PLANS.STARTER].description}</p>
            <ul className="features-list">
              {PLAN_PRICING[SUBSCRIPTION_PLANS.STARTER].features.map((feature, index) => (
                <li key={index}>{feature}</li>
              ))}
            </ul>
            {getSubscribeButton(SUBSCRIPTION_PLANS.STARTER)}
          </div>

          <div className="pricing-card">
            <h2>{PLAN_PRICING[SUBSCRIPTION_PLANS.GROWTH].name}</h2>
            {getCurrentPlanBadge(SUBSCRIPTION_PLANS.GROWTH)}
            <div className="price">${PLAN_PRICING[SUBSCRIPTION_PLANS.GROWTH].price}<span className="period">/{PLAN_PRICING[SUBSCRIPTION_PLANS.GROWTH].period}</span></div>
            <p>{PLAN_PRICING[SUBSCRIPTION_PLANS.GROWTH].description}</p>
            <ul className="features-list">
              {PLAN_PRICING[SUBSCRIPTION_PLANS.GROWTH].features.map((feature, index) => (
                <li key={index}>{feature}</li>
              ))}
            </ul>
            {getSubscribeButton(SUBSCRIPTION_PLANS.GROWTH)}
          </div>

          <div className="pricing-card">
            <h2>{PLAN_PRICING[SUBSCRIPTION_PLANS.ENTERPRISE].name}</h2>
            <div className="price">{PLAN_PRICING[SUBSCRIPTION_PLANS.ENTERPRISE].price}</div>
            <p>{PLAN_PRICING[SUBSCRIPTION_PLANS.ENTERPRISE].description}</p>
            <ul className="features-list">
              {PLAN_PRICING[SUBSCRIPTION_PLANS.ENTERPRISE].features.map((feature, index) => (
                <li key={index}>{feature}</li>
              ))}
            </ul>
            {getSubscribeButton(SUBSCRIPTION_PLANS.ENTERPRISE)}
          </div>
        </div>
        
        <p style={{ marginTop: '24px' }}>All plans support additional active models at <span className="inline-white">$29/mo</span> per model beyond your plan.</p>
        
        {/* Referral Program Info */}
        <div className="referral-program-info">
          <h3>Referral Program</h3>
          <p>Share your unique handle with others. When they subscribe using your code, you'll receive 10% of their subscription for 6 months!</p>
          <p><strong>Revenue Split:</strong> 30% goes to our employee, 70% goes to the company</p>
          <p><strong>Your handle:</strong> {subscription?.referralCode || 'Not set'}</p>
        </div>
      </section>
    </>
  );
}

