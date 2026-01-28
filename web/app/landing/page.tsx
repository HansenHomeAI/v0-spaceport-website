export const runtime = 'edge';

export default function Landing(): JSX.Element {
  return (
    <>
      <section className="section" id="landing">
        <iframe className="landing-iframe" src="https://hansenhomeai.github.io/WebbyDeerKnoll/" />
        <div id="iframe-overlay" />
        <div className="landing-content">
          <h1>Sell the location</h1>
          <p>Convert drone imagery to life-like 3D Models.</p>
          <a href="https://dolan-road.hansentour.com" className="cta-button with-symbol" target="_blank">
            <img src="/assets/SpaceportIcons/3D.svg" className="symbol-3d" alt="" aria-hidden="true" />
            View example
          </a>
        </div>
      </section>

      {/* Logos carousel (client logos, seamless loop) */}
      <section className="section" id="landing-carousel">
        <div className="logo-carousel">
          <div className="logos">
            {/* Set 1 (reordered to separate BHHS logos) */}
            <img src="/assets/BerkshireNorthwest.png" alt="Berkshire Hathaway Northwest Real Estate" />
            <img src="/assets/ColumbiaRiver.png" alt="Columbia River Realty" />
            <img src="/assets/Engel&Volkers.png" alt="Engel & Volkers" />
            <img src="/assets/BHHS.png" alt="Berkshire Hathaway HomeServices" />
            <img src="/assets/MirrRanchGroup2.png" alt="Mirr Ranch Group" />
            <img src="/assets/MullinRealEstate2.png" alt="Mullin Real Estate" />
            <img src="/assets/VestCapital.png" alt="Vest Capital" />
            <img src="/assets/WoodlandRealEstate.png" alt="Woodland Real Estate" />

            {/* Set 2 (duplicate for seamless scrolling) */}
            <img src="/assets/BerkshireNorthwest.png" alt="Berkshire Hathaway Northwest Real Estate" aria-hidden="true" />
            <img src="/assets/ColumbiaRiver.png" alt="Columbia River Realty" aria-hidden="true" />
            <img src="/assets/Engel&Volkers.png" alt="Engel & Volkers" aria-hidden="true" />
            <img src="/assets/BHHS.png" alt="Berkshire Hathaway HomeServices" aria-hidden="true" />
            <img src="/assets/MirrRanchGroup2.png" alt="Mirr Ranch Group" aria-hidden="true" />
            <img src="/assets/MullinRealEstate2.png" alt="Mullin Real Estate" aria-hidden="true" />
            <img src="/assets/VestCapital.png" alt="Vest Capital" aria-hidden="true" />
            <img src="/assets/WoodlandRealEstate.png" alt="Woodland Real Estate" aria-hidden="true" />
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
              <img src="/assets/SpaceportIcons/3D.svg" className="symbol-3d" alt="" aria-hidden="true" />
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
              <img src="/assets/SpaceportIcons/3D.svg" className="symbol-3d" alt="" aria-hidden="true" />
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


    </>
  );
}

