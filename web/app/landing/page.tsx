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
            <p>More listing views generated via 3D tours.</p>
          </div>
          <div className="stat-box">
            <h1>31%</h1>
            <p>Faster sales achieved with 3D tours.</p>
          </div>
          <div className="stat-box">
            <h1>10x</h1>
            <p>Higher engagement than standard photos.</p>
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

      {/* Team Section */}
      <section className="section" id="team">
        <h2>The Team.</h2>
        <div className="team-grid">
          <div className="team-member">
            <div className="member-photo-container">
              <img src="/assets/SpaceportIcons/SpcprtBWIcon.png" alt="Gabriel Hansen" className="member-photo" />
            </div>
            <div className="member-info">
              <h3>Gabriel Hansen</h3>
              <p className="member-title">Founder & Engineer</p>
              <p className="member-bio">Noticing firsthand how listings fail to capture what buyers actually care about, Gabriel built Spaceport to combine neural networks with drone technology.</p>
              <a href="#" target="_blank" rel="noopener noreferrer" className="linkedin-link">
                LinkedIn <img src="/assets/SpaceportIcons/Arrow.svg" alt="" className="linkedin-icon" />
              </a>
            </div>
          </div>

          <div className="team-member">
             <div className="member-photo-container placeholder">
               <span className="placeholder-initial">?</span>
             </div>
             <div className="member-info">
              <h3>Join the team</h3>
              <p className="member-title">We are hiring</p>
              <p className="member-bio">Passionate about 3D AI and real estate? We are looking for talented individuals to join our mission.</p>
              <a href="mailto:hello@spcprt.com" className="linkedin-link">
                Contact Us <img src="/assets/SpaceportIcons/Arrow.svg" alt="" className="linkedin-icon" />
              </a>
            </div>
          </div>
        </div>
      </section>

      <style jsx>{`
        #team {
          padding-top: 4rem;
          padding-bottom: 4rem;
        }
        
        .team-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 3rem;
          margin-top: 3rem;
        }
        
        .team-member {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 2rem;
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          transition: transform 0.3s ease;
        }
        
        .team-member:hover {
          transform: translateY(-5px);
          background: rgba(255, 255, 255, 0.05);
        }
        
        .member-photo-container {
          width: 120px;
          height: 120px;
          border-radius: 50%;
          overflow: hidden;
          margin-bottom: 1.5rem;
          border: 2px solid rgba(255, 255, 255, 0.1);
        }

        .member-photo-container.placeholder {
          background: rgba(255, 255, 255, 0.1);
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .placeholder-initial {
          font-size: 2rem;
          color: rgba(255, 255, 255, 0.5);
        }
        
        .member-photo {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        
        .member-info h3 {
          font-size: 1.5rem;
          margin-bottom: 0.5rem;
          color: white;
        }
        
        .member-title {
          font-size: 1rem;
          color: #9CA3AF;
          margin-bottom: 1rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          font-weight: 500;
        }
        
        .member-bio {
          font-size: 0.95rem;
          line-height: 1.6;
          color: rgba(255, 255, 255, 0.8);
          margin-bottom: 1.5rem;
        }
        
        .linkedin-link {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          color: white;
          text-decoration: none;
          font-weight: 500;
          padding: 0.5rem 1rem;
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 20px;
          transition: all 0.3s ease;
        }
        
        .linkedin-link:hover {
          background: white;
          color: black;
        }
        
        .linkedin-icon {
          width: 12px;
          height: 12px;
          transition: filter 0.3s ease;
        }
        
        .linkedin-link:hover .linkedin-icon {
          filter: invert(1);
        }
      `}</style>

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

