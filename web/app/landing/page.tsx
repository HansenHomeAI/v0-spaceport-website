export const runtime = 'edge';

export default function Landing(): JSX.Element {
  return (
    <>
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

      {/* Logos carousel (client logos only, each once) */}
      <section className="section" id="landing-carousel">
        <div className="logo-carousel">
          <div className="logos">
            <img src="/assets/MirrRanchGroup.png" alt="Mirr Ranch Group" />
            <img src="/assets/MullinRealEstate.png" alt="Mullin Real Estate" />
          </div>
        </div>
      </section>

      {/* Additional value prop (legacy: landing-additional) */}
      <section className="section two-col-section" id="landing-additional">
        <div className="two-col-content">
          <h2>Show what matters most to buyers.</h2>
          <div className="right-col">
            <p>Captivate buyers for longer with interactive 3D models that capture not just a building, but its location. View your property as if you're right there—feeling the neighborhood and natural flow around it.</p>
            <a href="https://deer-knoll-dr.hansentour.com" className="cta-button2-fixed with-symbol" target="_blank">
              <img src="/assets/3DSymbol.svg" className="symbol-3d" alt="" aria-hidden="true" />
              View example
            </a>
          </div>
        </div>
      </section>

      {/* Stats section matching legacy visuals */}
      <section className="section" id="landing-stats">
        <h2>Virtual experiences work.</h2>
        <div className="stats-grid">
          <div className="stat-box">
            <h1>95%</h1>
            <p>Are more likely to contact listings with 3D tours.</p>
          </div>
          <div className="stat-box">
            <h1>99%</h1>
            <p>See 3D tours as a competitive edge.</p>
          </div>
          <div className="stat-box">
            <h1>82%</h1>
            <p>Consider switching agents if a 3D tour is offered.</p>
          </div>
        </div>
        <p className="stats-source">National Association of Realtors</p>
      </section>

      {/* More sections from legacy */}
      <section className="section two-col-section" id="landing-more">
        <div className="two-col-content">
          <h2>The future of property listings.</h2>
          <div className="right-col">
            <p>Photos and 3D tours only show parts of a property—never the full picture. We create interactive models that let you explore the land, surroundings, and location in a way <span className="inline-white">no photo or video can match.</span></p>
            <a href="https://dolan-road.hansentour.com" className="cta-button2-fixed with-symbol" target="_blank">
              <img src="/assets/3DSymbol.svg" className="symbol-3d" alt="" aria-hidden="true" />
              View example
            </a>
          </div>
        </div>
      </section>

      <section className="section two-col-section" id="landing-more2">
        <div className="two-col-content">
          <h2>Effortless creation with your drone.</h2>
          <div className="right-col">
            <p>Creating your 3D model is effortless. Our system autonomously flies your drone, capturing the perfect shots with zero skill required. Simply upload your photos, and you'll receive the completed model straight to your inbox.</p>
            <a href="/create" className="cta-button2-fixed">Create your own</a>
          </div>
        </div>
      </section>

      <section className="section" id="landing-stats2">
        <div className="stats-grid">
          <div className="stat-box2 grainy">
            <img src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport Logo" />
          </div>
        </div>
      </section>
    </>
  );
}

