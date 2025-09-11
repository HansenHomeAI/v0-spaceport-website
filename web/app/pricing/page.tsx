'use client';

import { useSubscription } from '../hooks/useSubscription';

export const runtime = 'edge';

export default function Pricing(): JSX.Element {
  const { redirectToCheckout, loading } = useSubscription();

  const handleSubscribe = async (planType: 'single' | 'starter' | 'growth') => {
    try {
      await redirectToCheckout(planType);
    } catch (error) {
      console.error('Subscription error:', error);
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
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Get started'}
            </button>
          </div>

          <div className="pricing-card">
            <h2>Starter (up to 5 models).</h2>
            <div className="price">$99/mo</div>
            <p>Includes up to five active models. Need more? Add additional models at $29/mo each.</p>
            <button 
              onClick={() => handleSubscribe('starter')} 
              className="cta-button"
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Start Starter'}
            </button>
          </div>

          <div className="pricing-card">
            <h2>Growth (up to 20 models).</h2>
            <div className="price">$299/mo</div>
            <p>Includes up to twenty active models. Additional models are $29/mo each beyond your plan.</p>
            <button 
              onClick={() => handleSubscribe('growth')} 
              className="cta-button"
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Start Growth'}
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