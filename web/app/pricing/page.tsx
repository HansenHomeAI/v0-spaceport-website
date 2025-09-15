export const runtime = 'edge';

export default function Pricing(): JSX.Element {
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
            <p>High-volume or specialized projects? We'll tailor a plan for teams with larger model counts or specific needs.</p>

            <a href="mailto:gabriel@spcprt.com?subject=Enterprise%20Pricing%20Inquiry&body=Hello%2C%20I%27m%20interested%20in%20learning%20more%20about%20enterprise%20pricing%20at%20Spaceport." className="cta-button">Contact Us</a>

          </div>
        </div>
        <p style={{ marginTop: '24px' }}>All plans support additional active models at <span className="inline-white">$29/mo</span> per model beyond your plan.</p>

      </section>
    </>
  );
}