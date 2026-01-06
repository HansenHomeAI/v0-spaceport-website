'use client';

export const runtime = 'edge';

export default function Pricing(): JSX.Element {
  const enterpriseMailto =
    'mailto:sam@spcprt.com?subject=Enterprise%20Brokerage%20Pricing&body=Hello%20Spaceport%20team%2C%0A%0AWe%27re%20interested%20in%20enterprise%20brokerage%20pricing%20for%20multiple%20models.%0ACompany%3A%0AModel%20count%3A%0ATimeline%3A%0A%0AThanks%2C';

  return (
    <>
      <section className="section" id="pricing-header">
        <h1>Pricing.</h1>
        <p><span className="inline-white">Brokerage integration, priced per model.</span></p>
      </section>
      <section className="section" id="pricing">
        <div className="pricing-grid">
          <div className="pricing-card">
            <h2>Per model.</h2>
            <div className="price">$599</div>
            <p>$29/mo hosting per model. First month free.</p>
          </div>

          <div className="pricing-card">
            <h2>Enterprise.</h2>
            <div className="price">Custom</div>
            <p>Volume pricing for brokerages with large portfolios or deeper integrations.</p>
            <a href={enterpriseMailto} className="cta-button">Contact</a>
          </div>
        </div>
      </section>
    </>
  );
}
