'use client';

import { useState } from 'react';

import ModelDeliveryModal from '../../components/ModelDeliveryModal';
import NewProjectModal from '../../components/NewProjectModal';
import TermsOfServiceModal from '../../components/TermsOfServiceModal';
import type { ModelDeliveryProject, ResolveClientResponse } from '../hooks/useModelDeliveryAdmin';

import './component-library.css';

export const runtime = 'edge';

const demoProjects: ModelDeliveryProject[] = [
  {
    userSub: 'demo-user',
    projectId: 'ridgeview-001',
    title: 'Ridgeview Ranch',
    status: 'processing',
  },
  {
    userSub: 'demo-user',
    projectId: 'high-desert-002',
    title: 'High Desert Listing',
    status: 'ready',
  },
  {
    userSub: 'demo-user',
    projectId: 'evergreen-003',
    title: 'Evergreen Estate',
    status: 'delivered',
  },
];

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export default function ComponentLibrary(): JSX.Element {
  const [termsOpen, setTermsOpen] = useState(false);
  const [newProjectOpen, setNewProjectOpen] = useState(false);
  const [deliveryOpen, setDeliveryOpen] = useState(false);
  const [lastDelivered, setLastDelivered] = useState<ModelDeliveryProject | null>(null);

  const resolveClient = async (email: string): Promise<ResolveClientResponse> => {
    await delay(450);
    return {
      client: {
        user_id: 'demo-client',
        email,
        name: 'Avery Brooks',
        status: 'active',
      },
      projects: demoProjects,
    };
  };

  const sendDelivery = async (payload: {
    clientEmail: string;
    projectId: string;
    modelLink: string;
    projectTitle?: string;
  }) => {
    await delay(650);
    const projectMatch = demoProjects.find((project) => project.projectId === payload.projectId) || demoProjects[0];
    const deliveredProject = {
      ...projectMatch,
      status: 'delivered',
      modelLink: payload.modelLink,
    } as ModelDeliveryProject;
    setLastDelivered(deliveredProject);
    return { messageId: 'demo-8431', project: deliveredProject };
  };

  return (
    <div className="component-library">
      <section className="section component-library-intro">
        <p className="component-library-kicker">Component Library</p>
        <h1>Spaceport UI inventory</h1>
        <p>
          One page to review every text style, layout pattern, and reusable block. Filter and consolidate from here.
        </p>
        <div className="component-library-actions">
          <a href="/create" className="cta-button">Primary CTA</a>
          <button type="button" className="cta-button2-fixed" onClick={() => setNewProjectOpen(true)}>
            Open New Project Modal
          </button>
          <button type="button" className="cta-button2" onClick={() => setDeliveryOpen(true)}>
            Open Model Delivery
          </button>
        </div>
        {lastDelivered && (
          <p className="component-library-note">
            Demo delivery sent for {lastDelivered.title || 'Untitled'}.
          </p>
        )}
      </section>

      <section className="component-library-section">
        <div className="component-library-section-header">
          <h2>Foundations</h2>
          <p>Typography, color palette, and core text treatments used across the site.</p>
        </div>
        <div className="component-library-grid">
          <div className="component-library-card">
            <p className="component-library-label">Typography</p>
            <h1>Heading One</h1>
            <h2>Heading Two</h2>
            <h3 className="component-library-h3">Heading Three</h3>
            <p>
              Body copy with <span className="inline-white">inline emphasis</span> and supporting detail for longer
              sentences.
            </p>
          </div>
          <div className="component-library-card">
            <p className="component-library-label">Color Palette</p>
            <div className="component-library-swatches">
              <div className="component-library-swatch">
                <span className="component-library-swatch-chip" style={{ background: '#ffffff' }} />
                <span>#FFFFFF</span>
              </div>
              <div className="component-library-swatch">
                <span className="component-library-swatch-chip" style={{ background: '#000000' }} />
                <span>#000000</span>
              </div>
              <div className="component-library-swatch">
                <span className="component-library-swatch-chip" style={{ background: '#737373' }} />
                <span>#737373</span>
              </div>
              <div className="component-library-swatch">
                <span className="component-library-swatch-chip" style={{ background: '#a6a6a6' }} />
                <span>#A6A6A6</span>
              </div>
              <div className="component-library-swatch">
                <span className="component-library-swatch-chip" style={{ background: '#3fb27f' }} />
                <span>#3FB27F</span>
              </div>
              <div className="component-library-swatch">
                <span className="component-library-swatch-chip" style={{ background: '#ff6b6b' }} />
                <span>#FF6B6B</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="component-library-section">
        <div className="component-library-section-header">
          <h2>Buttons & Links</h2>
          <p>Primary and secondary CTA styles plus inline link treatments.</p>
        </div>
        <div className="component-library-row">
          <a href="/create" className="cta-button">Primary CTA</a>
          <a href="/pricing" className="cta-button2-fixed">Secondary CTA</a>
          <a href="/about" className="cta-button2">Ghost CTA</a>
          <a
            href="https://dolan-road.hansentour.com"
            className="cta-button2-fixed with-symbol"
            target="_blank"
            rel="noreferrer"
          >
            <img src="/assets/SpaceportIcons/3D.svg" className="symbol-3d" alt="" aria-hidden="true" />
            View example
          </a>
          <button type="button" className="terms-link" onClick={() => setTermsOpen(true)}>
            Terms of Service
          </button>
        </div>
      </section>

      <section className="component-library-section">
        <div className="component-library-section-header">
          <h2>Marketing Layouts</h2>
          <p>Hero, carousel, two-column, stats, and pricing patterns.</p>
        </div>
        <div className="component-library-layouts">
          <div className="component-library-layout">
            <section className="section" id="landing">
              <div className="landing-iframe component-library-hero-media" aria-hidden="true" />
              <div className="landing-content">
                <h1>Location. Visualized in 3D.</h1>
                <p>Show the land, context, and surroundings with an immersive model buyers can explore.</p>
                <a href="/create" className="cta-button">Join waitlist</a>
              </div>
            </section>
          </div>

          <div className="component-library-layout">
            <section className="section" id="landing-carousel">
              <div className="logo-carousel">
                <div className="logos">
                  <img src="/assets/BerkshireNorthwest.png" alt="Berkshire Hathaway Northwest Real Estate" />
                  <img src="/assets/ColumbiaRiver.png" alt="Columbia River Realty" />
                  <img src="/assets/Engel&Volkers.png" alt="Engel & Volkers" />
                  <img src="/assets/BHHS.png" alt="Berkshire Hathaway HomeServices" />
                  <img src="/assets/MirrRanchGroup2.png" alt="Mirr Ranch Group" />
                  <img src="/assets/MullinRealEstate2.png" alt="Mullin Real Estate" />
                  <img src="/assets/VestCapital.png" alt="Vest Capital" />
                  <img src="/assets/WoodlandRealEstate.png" alt="Woodland Real Estate" />
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
          </div>

          <div className="component-library-layout">
            <section className="section two-col-section">
              <div className="two-col-content">
                <h2>Two-column value prop</h2>
                <div className="right-col">
                  <p>
                    Captivate buyers with immersive models that capture not just a building, but its location and flow.
                  </p>
                  <a href="https://deer-knoll-dr.hansentour.com" className="cta-button2-fixed with-symbol" target="_blank" rel="noreferrer">
                    <img src="/assets/SpaceportIcons/3D.svg" className="symbol-3d" alt="" aria-hidden="true" />
                    View example
                  </a>
                </div>
              </div>
            </section>
          </div>

          <div className="component-library-layout">
            <section className="section two-col-section">
              <div className="two-col-content">
                <h2>Two-column checklist</h2>
                <div className="right-col">
                  <ul className="component-library-list">
                    <li><span className="inline-white">Plan your flight</span> with an optimized spiral path.</li>
                    <li><span className="inline-white">Capture + upload</span> imagery from the drone.</li>
                    <li><span className="inline-white">Receive the model</span> in 72 hours.</li>
                  </ul>
                  <a href="/create" className="cta-button2-fixed">Create your own</a>
                </div>
              </div>
            </section>
          </div>

          <div className="component-library-layout">
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
          </div>

          <div className="component-library-layout">
            <section className="section" id="pricing-header">
              <h1>Pricing.</h1>
              <p><span className="inline-white">Capture the imagination of your buyers.</span></p>
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
                  <a href="mailto:sam@spcprt.com" className="cta-button">Contact</a>
                </div>
              </div>
            </section>
          </div>
        </div>
      </section>

      <section className="component-library-section">
        <div className="component-library-section-header">
          <h2>Forms & Input</h2>
          <p>Waitlist, auth, feedback, and admin invites.</p>
        </div>
        <div className="component-library-grid">
          <div className="component-library-card">
            <p className="component-library-label">Waitlist Card</p>
            <div className="waitlist-card">
              <div className="waitlist-header">
                <img src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport" className="waitlist-logo" />
                <h1>Join the Waitlist</h1>
                <p>Be among the future of 3D visualization.</p>
              </div>
              <form className="waitlist-form">
                <input className="waitlist-input" placeholder="Email address" />
                <button type="button" className="waitlist-submit-btn">Request Access</button>
              </form>
              <div className="waitlist-terms">
                <p>By joining, you agree to the Spaceport terms.</p>
              </div>
            </div>
          </div>

          <div className="component-library-card">
            <p className="component-library-label">Beta Access Invite</p>
            <div className="beta-access-invite">
              <div className="beta-access-header">
                <h4>Beta Access Management</h4>
                <p>Invite new users to access Spaceport AI</p>
              </div>
              <form className="beta-access-form">
                <div className="input-group">
                  <input
                    type="email"
                    placeholder="Enter email address"
                    className="beta-access-input"
                    defaultValue="pilot@brokerage.com"
                  />
                  <button type="button" className="beta-access-button">
                    Grant Access
                  </button>
                </div>
                <div className="beta-access-message success">
                  Invite sent successfully.
                </div>
              </form>
            </div>
          </div>
        </div>

        <div className="component-library-grid component-library-card-spacer">
          <div className="component-library-card component-library-card-wide">
            <p className="component-library-label">Auth Modal</p>
            <div className="component-library-auth">
              <div className="auth-modal">
                <div className="auth-mode-toggle">
                  <div className="auth-mode-slider slide-left" />
                  <button type="button" className="auth-mode-button active">Sign Up</button>
                  <button type="button" className="auth-mode-button">Login</button>
                </div>
                <div className="auth-modal-content">
                  <div className="auth-modal-header">
                    <img src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport AI" className="auth-logo" />
                    <h2>New here?</h2>
                    <p>Join the waitlist to be among the first to access Spaceport AI.</p>
                  </div>
                  <form className="auth-form">
                    <div className="input-group">
                      <input className="auth-input" placeholder="Name" />
                    </div>
                    <div className="input-group">
                      <input className="auth-input" placeholder="Email address" />
                    </div>
                    <button type="button" className="auth-submit-btn">
                      <span>Join Waitlist</span>
                    </button>
                  </form>
                  <div className="auth-links">
                    <button type="button" className="auth-link">Already have an account?</button>
                  </div>
                </div>
              </div>

              <div className="auth-modal">
                <div className="auth-mode-toggle">
                  <div className="auth-mode-slider slide-right" />
                  <button type="button" className="auth-mode-button">Sign Up</button>
                  <button type="button" className="auth-mode-button active">Login</button>
                </div>
                <div className="auth-modal-content">
                  <div className="auth-modal-header">
                    <img src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport AI" className="auth-logo" />
                    <h2>Welcome back!</h2>
                    <p>Sign in to access your account.</p>
                  </div>
                  <form className="auth-form">
                    <div className="input-group">
                      <input className="auth-input" placeholder="Email" />
                    </div>
                    <div className="input-group">
                      <input className="auth-input" placeholder="Password" type="password" />
                    </div>
                    <button type="button" className="auth-submit-btn">
                      <span>Sign In</span>
                    </button>
                  </form>
                  <div className="auth-links">
                    <button type="button" className="auth-link">Forgot password?</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="component-library-card component-library-card-wide">
            <p className="component-library-label">Feedback Form</p>
            <div className="feedback-container">
              <form className="feedback-form">
                <div className="feedback-input-container">
                  <input className="feedback-input" placeholder="How can we improve?" />
                  <button type="button" className="cta-button2 feedback-submit">Send Feedback</button>
                </div>
                <div className="feedback-status">Placeholder for success and error states.</div>
              </form>
            </div>
          </div>
        </div>
      </section>

      <section className="component-library-section">
        <div className="component-library-section-header">
          <h2>Dashboard Components</h2>
          <p>Cards, status pills, and dashboard layout variants.</p>
        </div>
        <div className="component-library-card component-library-card-wide">
          <div className="project-cards">
            <div className="project-box">
              <button className="project-controls-btn">
                <img src="/assets/SpaceportIcons/Controls.svg" className="project-controls-icon" alt="Edit controls" />
              </button>
              <h1>Downtown Property</h1>
              <p>Processing - neural network training in progress.</p>
              <div className="component-library-progress">
                <div className="component-library-progress-bar" style={{ width: '70%' }} />
              </div>
            </div>

            <div className="project-box">
              <button className="project-controls-btn">
                <img src="/assets/SpaceportIcons/Controls.svg" className="project-controls-icon" alt="Edit controls" />
              </button>
              <h1>Meadow Ridge</h1>
              <p>Complete - hosting ready.</p>
              <div className="component-library-progress">
                <div className="component-library-progress-bar" style={{ width: '100%' }} />
              </div>
            </div>

            <div className="project-box new-project-card">
              <h1>
                New Project
                <span className="plus-icon">
                  <span></span>
                  <span></span>
                </span>
              </h1>
            </div>
          </div>
        </div>
      </section>

      <section className="component-library-section">
        <div className="component-library-section-header">
          <h2>Modals</h2>
          <p>Live modal components rendered with safe demo data.</p>
        </div>
        <div className="component-library-row">
          <button type="button" className="cta-button2-fixed" onClick={() => setTermsOpen(true)}>
            Open Terms of Service
          </button>
          <button type="button" className="cta-button2-fixed" onClick={() => setNewProjectOpen(true)}>
            Open New Project
          </button>
          <button type="button" className="cta-button2-fixed" onClick={() => setDeliveryOpen(true)}>
            Open Model Delivery
          </button>
        </div>
      </section>

      <TermsOfServiceModal isOpen={termsOpen} onClose={() => setTermsOpen(false)} />
      <NewProjectModal open={newProjectOpen} onClose={() => setNewProjectOpen(false)} />
      <ModelDeliveryModal
        open={deliveryOpen}
        onClose={() => setDeliveryOpen(false)}
        resolveClient={resolveClient}
        sendDelivery={sendDelivery}
        onDelivered={(project) => setLastDelivered(project as ModelDeliveryProject)}
      />
    </div>
  );
}
