export const runtime = 'edge';

export default function Landing(): JSX.Element {
  return (
    <section className="section" id="landing">
      <iframe className="landing-iframe" src="https://hansenhomeai.github.io/WebbyDeerKnoll/" />
      <div id="iframe-overlay" />
      <div className="landing-content">
        <h1>Location. Visualized in 3D.</h1>
        <a href="https://10716eforestcreekrd.hansentour.com" className="cta-button with-symbol">
          <img src="/assets/3DSymbol.svg" className="symbol-3d" alt="" aria-hidden="true" />
          View example
        </a>
      </div>
    </section>
  );
}

