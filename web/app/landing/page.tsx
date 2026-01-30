import HeroCarousel from './HeroCarousel';
import FAQ from '../../components/FAQ';

export const runtime = 'edge';

export default function Landing(): JSX.Element {
  return (
    <>
      <HeroCarousel />

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
          <h2>Built for innovative brokerages.</h2>
          <div className="right-col">
            <p>Give buyers the clearest understanding of the listing. Less time on market, and much more convenient.</p>
            <a href="/create" className="cta-button2-fixed">
              Join waitlist
            </a>
          </div>
        </div>
      </section>

      {/* Stats section matching legacy visuals */}
      <section className="section" id="landing-stats">
        <h2>Virtual experiences work.</h2>
        <div className="stats-grid">
          <div className="stat-box">
            <h1>87%</h1>
            <p>more views</p>
          </div>
          <div className="stat-box">
            <h1>31%</h1>
            <p>faster sales</p>
          </div>
          <div className="stat-box">
            <h1>5-10x</h1>
            <p>longer engaging with listing</p>
          </div>
        </div>
        <p className="stats-source">Sources: Redfin, Matterport & NAR (2024-2025)</p>
      </section>

      {/* More sections from legacy */}
      <section className="section two-col-section" id="landing-more2">
        <div className="two-col-content">
          <h2>Works with most DJI drones.</h2>
          <div className="right-col">
            <p>Creating your 3D tour is effortless. Fly it yourself, or share with your drone photographer.</p>
            <a href="/create" className="cta-button2-fixed">Create your own</a>
          </div>
        </div>
      </section>

      <FAQ />

      <section className="section two-col-section" id="landing-more">
        <div className="two-col-content">
          <h2>Seeing is believing.</h2>
          <div className="right-col">
            <p>Our vision is to create a listing experience better than visiting in-person. Apply to become a select partner as we reimagine real estate for the 3D future.</p>
            <a href="/create" className="cta-button2-fixed">
              Join waitlist
            </a>
          </div>
        </div>
      </section>


    </>
  );
}

