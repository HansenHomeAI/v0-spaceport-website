'use client';

import { useState } from 'react';

import ModelDeliveryModal from '../../components/ModelDeliveryModal';
import NewProjectModal from '../../components/NewProjectModal';
import TermsOfServiceModal from '../../components/TermsOfServiceModal';
import type { ModelDeliveryProject, ResolveClientResponse } from '../hooks/useModelDeliveryAdmin';
import { Button, Container, Input, Layout, Section, Text } from '../../components/foundational';

import '../flight-viewer/styles.css';
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
    <Container variant="component-library">
      <Section variant="component-library-intro">
        <Text.Small withBase={false} className="component-library-kicker">Component Library</Text.Small>
        <Text.H1>Spaceport UI inventory</Text.H1>
        <Text.Body>
          One page to review every text style, layout pattern, and reusable block. Filter and consolidate from here.
        </Text.Body>
        <Container variant="component-library-actions">
          <Button.Primary href="/create">Primary CTA</Button.Primary>
          <Button.Secondary fixed type="button" onClick={() => setNewProjectOpen(true)}>
            Open New Project Modal
          </Button.Secondary>
          <Button.Secondary type="button" onClick={() => setDeliveryOpen(true)}>
            Open Model Delivery
          </Button.Secondary>
        </Container>
        {lastDelivered && (
          <Text.Body withBase={false} className="component-library-note">
            Demo delivery sent for {lastDelivered.title || 'Untitled'}.
          </Text.Body>
        )}
      </Section>

      <Container as="section" variant="component-library-section">
        <Container variant="component-library-section-header">
          <Text.H2 withBase={false}>Foundations</Text.H2>
          <Text.Body withBase={false}>Six unified text styles used throughout the entire web app.</Text.Body>
        </Container>
        <Layout.Grid variant="component-library-grid">
          <Container variant="component-library-card">
            <Text.Small withBase={false} className="component-library-label">Style 1: Heading 1</Text.Small>
            <Text.H1>Heading 1</Text.H1>
            <Text.Small style={{ marginTop: '16px' }}>
              Class: .text-h1<br />
              Font-size: clamp(2.9rem, 8vw, 3.9rem)<br />
              Font-weight: 500<br />
              Color: rgba(255, 255, 255, 1)<br />
              Line-height: 1.05
            </Text.Small>
          </Container>

          <Container variant="component-library-card">
            <Text.Small withBase={false} className="component-library-label">Style 2: Heading 2</Text.Small>
            <Text.H2>Heading 2</Text.H2>
            <Text.Small style={{ marginTop: '16px' }}>
              Class: .text-h2<br />
              Font-size: 2rem<br />
              Font-weight: 500<br />
              Color: rgba(255, 255, 255, 1)<br />
              Line-height: 1.05
            </Text.Small>
          </Container>

          <Container variant="component-library-card">
            <Text.Small withBase={false} className="component-library-label">Style 3: Heading 3</Text.Small>
            <Text.H3>Heading 3</Text.H3>
            <Text.Small style={{ marginTop: '16px' }}>
              Class: .text-h3<br />
              Font-size: 1.3rem<br />
              Font-weight: 500<br />
              Color: rgba(255, 255, 255, 1)<br />
              Line-height: 1.05
            </Text.Small>
          </Container>

          <Container variant="component-library-card">
            <Text.Small withBase={false} className="component-library-label">Style 4: Body Text</Text.Small>
            <Text.Body>
              Body text for paragraphs and main content. This style provides comfortable reading with appropriate line height and color contrast.
            </Text.Body>
            <Text.Small style={{ marginTop: '16px' }}>
              Class: .text-body<br />
              Font-size: 1.2rem<br />
              Font-weight: 400<br />
              Color: rgba(255, 255, 255, 0.5)<br />
              Line-height: 1.6
            </Text.Small>
          </Container>

          <Container variant="component-library-card">
            <Text.Small withBase={false} className="component-library-label">Style 5: Small Text</Text.Small>
            <Text.Small>
              Small text for labels, notes, captions, and secondary information.
            </Text.Small>
            <Text.Small style={{ marginTop: '16px' }}>
              Class: .text-small<br />
              Font-size: 0.9rem<br />
              Font-weight: 400<br />
              Color: rgba(255, 255, 255, 0.6)<br />
              Line-height: 1.5
            </Text.Small>
          </Container>

          <Container variant="component-library-card">
            <Text.Small withBase={false} className="component-library-label">Style 6: Emphasis Text</Text.Small>
            <Text.Emphasis>
              Emphasis text for <Container as="span" style={{ color: 'rgba(255, 255, 255, 1)' }}>highlighted content</Container> and important inline elements.
            </Text.Emphasis>
            <Text.Small style={{ marginTop: '16px' }}>
              Class: .text-emphasis<br />
              Font-size: 1.2rem<br />
              Font-weight: 400<br />
              Color: rgba(255, 255, 255, 1)<br />
              Line-height: 1.6<br />
              <Container as="span" style={{ color: 'rgba(255, 255, 255, 1)' }}>Used for inline emphasis</Container>
            </Text.Small>
          </Container>

          <Container variant="component-library-card">
            <Text.Small withBase={false} className="component-library-label">Color Palette</Text.Small>
            <Container variant="component-library-swatches">
              <Container variant="component-library-swatch">
                <Container as="span" variant="component-library-swatch-chip" style={{ background: '#ffffff' }} />
                <Container as="span">#FFFFFF</Container>
              </Container>
              <Container variant="component-library-swatch">
                <Container as="span" variant="component-library-swatch-chip" style={{ background: '#000000' }} />
                <Container as="span">#000000</Container>
              </Container>
              <Container variant="component-library-swatch">
                <Container as="span" variant="component-library-swatch-chip" style={{ background: '#737373' }} />
                <Container as="span">#737373</Container>
              </Container>
              <Container variant="component-library-swatch">
                <Container as="span" variant="component-library-swatch-chip" style={{ background: '#a6a6a6' }} />
                <Container as="span">#A6A6A6</Container>
              </Container>
              <Container variant="component-library-swatch">
                <Container as="span" variant="component-library-swatch-chip" style={{ background: '#3fb27f' }} />
                <Container as="span">#3FB27F</Container>
              </Container>
              <Container variant="component-library-swatch">
                <Container as="span" variant="component-library-swatch-chip" style={{ background: '#ff6b6b' }} />
                <Container as="span">#FF6B6B</Container>
              </Container>
            </Container>
          </Container>
        </Layout.Grid>
      </Container>

      <Container as="section" variant="component-library-section">
        <Container variant="component-library-section-header">
          <Text.H2 withBase={false}>Non-Unified Text Styles Audit</Text.H2>
          <Text.Body withBase={false} className="text-body">
            The following text styles are still in use but NOT part of the 6 unified styles. These should be migrated to use the unified system.
          </Text.Body>
        </Container>
        <Container variant={['component-library-card', 'component-library-card-wide']}>
          <Text.Body withBase={false} className="component-library-label">⚠️ Text Styles That Need Migration</Text.Body>
          <Layout.Grid style={{ gap: '24px', marginTop: '24px' }}>
            <Container>
              <Text.Small withBase={false} className="text-small" style={{ color: '#ff6b6b', fontWeight: 600, marginBottom: '8px' }}>
                Component Library Specific:
              </Text.Small>
              <Container as="ul" variant="component-library-list">
                <Container as="li"><code>.component-library-kicker</code> - Should use <code>.text-small</code></Container>
                <Container as="li"><code>.component-library-note</code> - Should use <code>.text-small</code></Container>
                <Container as="li"><code>.component-library-h3</code> - Should use <code>.text-h3</code></Container>
              </Container>
            </Container>
            <Container>
              <Text.Small withBase={false} className="text-small" style={{ color: '#ff6b6b', fontWeight: 600, marginBottom: '8px' }}>
                Stats & Pricing:
              </Text.Small>
              <Container as="ul" variant="component-library-list">
                <Container as="li"><code>.stats-source</code> - Should use <code>.text-small</code></Container>
                <Container as="li"><code>.stat-box h1</code> - Special gradient style (may need exception)</Container>
                <Container as="li"><code>.stat-box p</code> - Should use <code>.text-body</code> or <code>.text-emphasis</code></Container>
                <Container as="li"><code>.price</code> - Special gradient style (may need exception)</Container>
                <Container as="li"><code>.pricing-card h2</code> - Should use <code>.text-h2</code></Container>
                <Container as="li"><code>.pricing-card p</code> - Should use <code>.text-body</code></Container>
              </Container>
            </Container>
            <Container>
              <Text.Small withBase={false} className="text-small" style={{ color: '#ff6b6b', fontWeight: 600, marginBottom: '8px' }}>
                Auth & Modals:
              </Text.Small>
              <Container as="ul" variant="component-library-list">
                <Container as="li"><code>.auth-modal-header h2</code> - Should use <code>.text-h2</code></Container>
                <Container as="li"><code>.auth-modal-header p</code> - Should use <code>.text-body</code></Container>
                <Container as="li"><code>.auth-description</code> - Should use <code>.text-small</code></Container>
                <Container as="li"><code>.auth-error</code> - Should use <code>.text-small</code> (with error color)</Container>
                <Container as="li"><code>.auth-success</code> - Should use <code>.text-small</code> (with success color)</Container>
                <Container as="li"><code>.auth-link</code> - Should use <code>.text-small</code> (with link styling)</Container>
                <Container as="li"><code>.terms-modal-content h1</code> - Should use <code>.text-h1</code></Container>
                <Container as="li"><code>.terms-modal-content h2</code> - Should use <code>.text-h2</code></Container>
                <Container as="li"><code>.terms-modal-content p</code> - Should use <code>.text-body</code></Container>
                <Container as="li"><code>.terms-link</code> - Should use <code>.text-small</code> (with link styling)</Container>
              </Container>
            </Container>
            <Container>
              <Text.Small withBase={false} className="text-small" style={{ color: '#ff6b6b', fontWeight: 600, marginBottom: '8px' }}>
                Model Delivery:
              </Text.Small>
              <Container as="ul" variant="component-library-list">
                <Container as="li"><code>.model-delivery-label</code> - Should use <code>.text-small</code></Container>
                <Container as="li"><code>.model-delivery-description</code> - Should use <code>.text-body</code></Container>
                <Container as="li"><code>.model-delivery-meta</code> - Should use <code>.text-small</code></Container>
                <Container as="li"><code>.model-delivery-hint</code> - Should use <code>.text-small</code></Container>
                <Container as="li"><code>.model-delivery-error</code> - Should use <code>.text-small</code> (with error color)</Container>
                <Container as="li"><code>.model-delivery-success</code> - Should use <code>.text-small</code> (with success color)</Container>
              </Container>
            </Container>
            <Container>
              <Text.Small withBase={false} className="text-small" style={{ color: '#ff6b6b', fontWeight: 600, marginBottom: '8px' }}>
                Inline & Special:
              </Text.Small>
              <Container as="ul" variant="component-library-list">
                <Container as="li"><code>.inline-white</code> - Should use <code>.text-emphasis</code> or inline style</Container>
                <Container as="li"><code>.beta-text</code> - Special pill style (may need exception)</Container>
                <Container as="li"><code>.text-highlight</code> - Should use <code>.text-emphasis</code></Container>
              </Container>
            </Container>
            <Container>
              <Text.Small withBase={false} className="text-small" style={{ color: '#ff6b6b', fontWeight: 600, marginBottom: '8px' }}>
                Landing Page:
              </Text.Small>
              <Container as="ul" variant="component-library-list">
                <Container as="li"><code>.landing-content h1</code> - Should use <code>.text-h1</code> (font-weight 700 variant)</Container>
                <Container as="li"><code>.landing-content p</code> - Should use <code>.text-body</code></Container>
              </Container>
            </Container>
          </Layout.Grid>
          <Text.Small
            withBase={false}
            className="text-small"
            style={{ marginTop: '24px', padding: '16px', background: 'rgba(255, 107, 107, 0.1)', border: '1px solid rgba(255, 107, 107, 0.3)', borderRadius: '12px' }}
          >
            <Container as="strong">Note:</Container> Some styles like gradient text (.stat-box h1, .price) and special UI elements (.beta-text) may need to remain as exceptions. All other text should migrate to the 6 unified styles.
          </Text.Small>
        </Container>
      </Container>

      <Container as="section" variant="component-library-section">
        <Container variant="component-library-section-header">
          <Text.H2 withBase={false}>Buttons & Links</Text.H2>
          <Text.Body withBase={false}>Primary and secondary CTA styles plus inline link treatments.</Text.Body>
        </Container>
        <Layout.Flex variant="component-library-row">
          <Button.Primary href="/create">Primary CTA</Button.Primary>
          <Button.Secondary fixed href="/pricing">Secondary CTA</Button.Secondary>
          <Button.Secondary href="/about">Ghost CTA</Button.Secondary>
          <Button.Secondary
            fixed
            withSymbol
            href="https://dolan-road.hansentour.com"
            target="_blank"
            rel="noreferrer"
          >
            <Container as="img" variant="symbol-3d" src="/assets/SpaceportIcons/3D.svg" alt="" aria-hidden="true" />
            View example
          </Button.Secondary>
          <Button.Link type="button" onClick={() => setTermsOpen(true)}>
            Terms of Service
          </Button.Link>
        </Layout.Flex>
      </Container>

      <Container as="section" variant="component-library-section">
        <Container variant="component-library-section-header">
          <Text.H2 withBase={false}>Marketing Layouts</Text.H2>
          <Text.Body withBase={false}>Hero, carousel, two-column, stats, and pricing patterns.</Text.Body>
        </Container>
        <Container variant="component-library-layouts">
          <Container variant="component-library-layout">
            <Section id="landing">
              <Container variant={['landing-iframe', 'component-library-hero-media']} aria-hidden="true" />
              <Container variant="landing-content">
                <Text.H1 withBase={false}>Location. Visualized in 3D.</Text.H1>
                <Text.Body withBase={false}>Show the land, context, and surroundings with an immersive model buyers can explore.</Text.Body>
                <Button.Primary href="/create">Join waitlist</Button.Primary>
              </Container>
            </Section>
          </Container>

          <Container variant="component-library-layout">
            <Section id="landing-carousel">
              <Container variant="logo-carousel">
                <Container variant="logos">
                  <Container as="img" src="/assets/BerkshireNorthwest.png" alt="Berkshire Hathaway Northwest Real Estate" />
                  <Container as="img" src="/assets/ColumbiaRiver.png" alt="Columbia River Realty" />
                  <Container as="img" src="/assets/Engel&Volkers.png" alt="Engel & Volkers" />
                  <Container as="img" src="/assets/BHHS.png" alt="Berkshire Hathaway HomeServices" />
                  <Container as="img" src="/assets/MirrRanchGroup2.png" alt="Mirr Ranch Group" />
                  <Container as="img" src="/assets/MullinRealEstate2.png" alt="Mullin Real Estate" />
                  <Container as="img" src="/assets/VestCapital.png" alt="Vest Capital" />
                  <Container as="img" src="/assets/WoodlandRealEstate.png" alt="Woodland Real Estate" />
                  <Container as="img" src="/assets/BerkshireNorthwest.png" alt="Berkshire Hathaway Northwest Real Estate" aria-hidden="true" />
                  <Container as="img" src="/assets/ColumbiaRiver.png" alt="Columbia River Realty" aria-hidden="true" />
                  <Container as="img" src="/assets/Engel&Volkers.png" alt="Engel & Volkers" aria-hidden="true" />
                  <Container as="img" src="/assets/BHHS.png" alt="Berkshire Hathaway HomeServices" aria-hidden="true" />
                  <Container as="img" src="/assets/MirrRanchGroup2.png" alt="Mirr Ranch Group" aria-hidden="true" />
                  <Container as="img" src="/assets/MullinRealEstate2.png" alt="Mullin Real Estate" aria-hidden="true" />
                  <Container as="img" src="/assets/VestCapital.png" alt="Vest Capital" aria-hidden="true" />
                  <Container as="img" src="/assets/WoodlandRealEstate.png" alt="Woodland Real Estate" aria-hidden="true" />
                </Container>
              </Container>
            </Section>
          </Container>

          <Container variant="component-library-layout">
            <Section variant="two-col-section">
              <Layout.TwoCol>
                <Text.H2 withBase={false}>Two-column value prop</Text.H2>
                <Container variant="right-col">
                  <Text.Body withBase={false}>
                    Captivate buyers with immersive models that capture not just a building, but its location and flow.
                  </Text.Body>
                  <Button.Secondary
                    fixed
                    withSymbol
                    href="https://deer-knoll-dr.hansentour.com"
                    target="_blank"
                    rel="noreferrer"
                  >
                    <Container as="img" variant="symbol-3d" src="/assets/SpaceportIcons/3D.svg" alt="" aria-hidden="true" />
                    View example
                  </Button.Secondary>
                </Container>
              </Layout.TwoCol>
            </Section>
          </Container>

          <Container variant="component-library-layout">
            <Section variant="two-col-section">
              <Layout.TwoCol>
                <Text.H2 withBase={false}>Two-column checklist</Text.H2>
                <Container variant="right-col">
                  <Container as="ul" variant="component-library-list">
                    <Container as="li"><Container as="span" variant="inline-white">Plan your flight</Container> with an optimized spiral path.</Container>
                    <Container as="li"><Container as="span" variant="inline-white">Capture + upload</Container> imagery from the drone.</Container>
                    <Container as="li"><Container as="span" variant="inline-white">Receive the model</Container> in 72 hours.</Container>
                  </Container>
                  <Button.Secondary fixed href="/create">Create your own</Button.Secondary>
                </Container>
              </Layout.TwoCol>
            </Section>
          </Container>

          <Container variant="component-library-layout">
            <Section id="landing-stats">
              <Text.H2 withBase={false}>Virtual experiences work.</Text.H2>
              <Layout.Grid variant="stats-grid">
                <Container variant="stat-box">
                  <Text.H1 withBase={false}>95%</Text.H1>
                  <Text.Body withBase={false}>Are more likely to contact listings with 3D tours.</Text.Body>
                </Container>
                <Container variant="stat-box">
                  <Text.H1 withBase={false}>99%</Text.H1>
                  <Text.Body withBase={false}>See 3D tours as a competitive edge.</Text.Body>
                </Container>
                <Container variant="stat-box">
                  <Text.H1 withBase={false}>82%</Text.H1>
                  <Text.Body withBase={false}>Consider switching agents if a 3D tour is offered.</Text.Body>
                </Container>
              </Layout.Grid>
              <Text.Small withBase={false} className="stats-source">National Association of Realtors</Text.Small>
            </Section>
          </Container>

          <Container variant="component-library-layout">
            <Section id="pricing-header">
              <Text.H1 withBase={false}>Pricing.</Text.H1>
              <Text.Body withBase={false}>
                <Container as="span" variant="inline-white">Capture the imagination of your buyers.</Container>
              </Text.Body>
            </Section>
            <Section id="pricing">
              <Layout.Grid variant="pricing-grid">
                <Container variant="pricing-card">
                  <Text.H2 withBase={false}>Per model.</Text.H2>
                  <Container variant="price">$599</Container>
                  <Text.Body withBase={false}>$29/mo hosting per model. First month free.</Text.Body>
                </Container>
                <Container variant="pricing-card">
                  <Text.H2 withBase={false}>Enterprise.</Text.H2>
                  <Container variant="price">Custom</Container>
                  <Text.Body withBase={false}>
                    Volume pricing for brokerages with large portfolios or deeper integrations.
                  </Text.Body>
                  <Button.Primary href="mailto:sam@spcprt.com">Contact</Button.Primary>
                </Container>
              </Layout.Grid>
            </Section>
          </Container>
        </Container>
      </Container>

      <Container as="section" variant="component-library-section">
        <Container variant="component-library-section-header">
          <Text.H2 withBase={false}>Forms & Input</Text.H2>
          <Text.Body withBase={false}>Waitlist, auth, feedback, and admin invites.</Text.Body>
        </Container>
        <Layout.Grid variant="component-library-grid">
          <Container variant="component-library-card">
            <Text.Body withBase={false} className="component-library-label">Waitlist Card</Text.Body>
            <Container variant="waitlist-card">
              <Container variant="waitlist-header">
                <Container as="img" src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport" className="waitlist-logo" />
                <Text.H1 withBase={false}>Join the Waitlist</Text.H1>
                <Text.Body withBase={false}>Be among the future of 3D visualization.</Text.Body>
              </Container>
              <Container as="form" variant="waitlist-form">
                <Input.Text variant="waitlist-input" placeholder="Email address" />
                <Button.Base type="button" variant="waitlist-submit-btn">Request Access</Button.Base>
              </Container>
              <Container variant="waitlist-terms">
                <Text.Body withBase={false}>By joining, you agree to the Spaceport terms.</Text.Body>
              </Container>
            </Container>
          </Container>

          <Container variant="component-library-card">
            <Text.Body withBase={false} className="component-library-label">Beta Access Invite</Text.Body>
            <Container variant="beta-access-invite">
              <Container variant="beta-access-header">
                <Container as="h4">Beta Access Management</Container>
                <Text.Body withBase={false}>Invite new users to access Spaceport AI</Text.Body>
              </Container>
              <Container as="form" variant="beta-access-form">
                <Container variant="input-group">
                  <Input.Text
                    type="email"
                    placeholder="Enter email address"
                    variant="beta-access-input"
                    defaultValue="pilot@brokerage.com"
                  />
                  <Button.Base type="button" variant="beta-access-button">
                    Grant Access
                  </Button.Base>
                </Container>
                <Container variant={['beta-access-message', 'success']}>
                  Invite sent successfully.
                </Container>
              </Container>
            </Container>
          </Container>
        </Layout.Grid>

        <Layout.Grid variant={['component-library-grid', 'component-library-card-spacer']}>
          <Container variant={['component-library-card', 'component-library-card-wide']}>
            <Text.Body withBase={false} className="component-library-label">Auth Modal</Text.Body>
            <Container variant="component-library-auth">
              <Container variant="auth-modal">
                <Container variant="auth-mode-toggle">
                  <Container variant={['auth-mode-slider', 'slide-left']} />
                  <Button.Base type="button" variant={['auth-mode-button', 'active']}>Sign Up</Button.Base>
                  <Button.Base type="button" variant="auth-mode-button">Login</Button.Base>
                </Container>
                <Container variant="auth-modal-content">
                  <Container variant="auth-modal-header">
                    <Container as="img" src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport AI" className="auth-logo" />
                    <Text.H2 withBase={false}>New here?</Text.H2>
                    <Text.Body withBase={false}>Join the waitlist to be among the first to access Spaceport AI.</Text.Body>
                  </Container>
                  <Container as="form" variant="auth-form">
                    <Container variant="input-group">
                      <Input.Text variant="auth-input" placeholder="Name" />
                    </Container>
                    <Container variant="input-group">
                      <Input.Text variant="auth-input" placeholder="Email address" />
                    </Container>
                    <Button.Base type="button" variant="auth-submit-btn">
                      <Container as="span">Join Waitlist</Container>
                    </Button.Base>
                  </Container>
                  <Container variant="auth-links">
                    <Button.Base type="button" variant="auth-link">Already have an account?</Button.Base>
                  </Container>
                </Container>
              </Container>

              <Container variant="auth-modal">
                <Container variant="auth-mode-toggle">
                  <Container variant={['auth-mode-slider', 'slide-right']} />
                  <Button.Base type="button" variant="auth-mode-button">Sign Up</Button.Base>
                  <Button.Base type="button" variant={['auth-mode-button', 'active']}>Login</Button.Base>
                </Container>
                <Container variant="auth-modal-content">
                  <Container variant="auth-modal-header">
                    <Container as="img" src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport AI" className="auth-logo" />
                    <Text.H2 withBase={false}>Welcome back!</Text.H2>
                    <Text.Body withBase={false}>Sign in to access your account.</Text.Body>
                  </Container>
                  <Container as="form" variant="auth-form">
                    <Container variant="input-group">
                      <Input.Text variant="auth-input" placeholder="Email" />
                    </Container>
                    <Container variant="input-group">
                      <Input.Text variant="auth-input" placeholder="Password" type="password" />
                    </Container>
                    <Button.Base type="button" variant="auth-submit-btn">
                      <Container as="span">Sign In</Container>
                    </Button.Base>
                  </Container>
                  <Container variant="auth-links">
                    <Button.Base type="button" variant="auth-link">Forgot password?</Button.Base>
                  </Container>
                </Container>
              </Container>
            </Container>
          </Container>

          <Container variant={['component-library-card', 'component-library-card-wide']}>
            <Text.Body withBase={false} className="component-library-label">Feedback Form</Text.Body>
            <Container variant="feedback-container">
              <Container as="form" variant="feedback-form">
                <Container variant="feedback-input-container">
                  <Input.Text variant="feedback-input" placeholder="How can we improve?" />
                  <Button.Base type="button" variant={['cta-button2', 'feedback-submit']}>Send Feedback</Button.Base>
                </Container>
                <Container variant="feedback-status">Placeholder for success and error states.</Container>
              </Container>
            </Container>
          </Container>
        </Layout.Grid>
      </Container>

      <Container as="section" variant="component-library-section">
        <Container variant="component-library-section-header">
          <Text.H2 withBase={false}>Dashboard Components</Text.H2>
          <Text.Body withBase={false}>Cards, status pills, and dashboard layout variants.</Text.Body>
        </Container>
        <Container variant={['component-library-card', 'component-library-card-wide']}>
          <Container variant="project-cards">
            <Container variant="project-box">
              <Button.Base variant="project-controls-btn">
                <Container as="img" variant="project-controls-icon" src="/assets/SpaceportIcons/Controls.svg" alt="Edit controls" />
              </Button.Base>
              <Text.H1 withBase={false}>Downtown Property</Text.H1>
              <Text.Body withBase={false}>Processing - neural network training in progress.</Text.Body>
              <Container variant="component-library-progress">
                <Container variant="component-library-progress-bar" style={{ width: '70%' }} />
              </Container>
            </Container>

            <Container variant="project-box">
              <Button.Base variant="project-controls-btn">
                <Container as="img" variant="project-controls-icon" src="/assets/SpaceportIcons/Controls.svg" alt="Edit controls" />
              </Button.Base>
              <Text.H1 withBase={false}>Meadow Ridge</Text.H1>
              <Text.Body withBase={false}>Complete - hosting ready.</Text.Body>
              <Container variant="component-library-progress">
                <Container variant="component-library-progress-bar" style={{ width: '100%' }} />
              </Container>
            </Container>

            <Container variant={['project-box', 'new-project-card']}>
              <Text.H1 withBase={false}>
                New Project
                <Container as="span" variant="plus-icon">
                  <Container as="span" />
                  <Container as="span" />
                </Container>
              </Text.H1>
            </Container>
          </Container>
        </Container>
      </Container>

      <Container as="section" variant="component-library-section">
        <Container variant="component-library-section-header">
          <Text.H2 withBase={false}>Flight Viewer UI</Text.H2>
          <Text.Body withBase={false}>Upload flow, flight list, lens controls, tooltip, and converter modal building blocks.</Text.Body>
        </Container>
        <Layout.Grid variant="component-library-grid">
          <Container variant="component-library-card">
            <Text.Body withBase={false} className="component-library-label">Upload Dropzone</Text.Body>
            <Container as="label" variant="flight-viewer__upload">
              <Container as="span" variant="flight-viewer__upload-title">Add flight files</Container>
              <Container as="span" variant="flight-viewer__upload-hint">
                Support for CSV (Litchi/DJI) and KMZ (DJI WPML) formats.
              </Container>
              <Input.Text type="file" accept=".csv,text/csv,.kmz,application/vnd.google-earth.kmz" />
            </Container>
          </Container>

          <Container variant="component-library-card">
            <Text.Body withBase={false} className="component-library-label">Flight List Item</Text.Body>
            <Container variant="flight-viewer__flight-item">
              <Container variant="flight-viewer__flight-item-header">
                <Container variant="flight-viewer__flight-color" style={{ backgroundColor: '#4f83ff' }} />
                <Container as="span" variant="flight-viewer__flight-name">ridgeview-001.csv</Container>
                <Button.Base variant="flight-viewer__remove-btn" aria-label="Remove ridgeview-001">
                  x
                </Button.Base>
              </Container>
              <Container variant="flight-viewer__flight-stats">
                <Container as="span">210 pts</Container>
                <Container as="span">-</Container>
                <Container as="span">1180m</Container>
                <Container as="span">-</Container>
                <Container as="span">120-320ft</Container>
              </Container>
            </Container>
          </Container>

          <Container variant="component-library-card">
            <Text.Body withBase={false} className="component-library-label">Lens Controls + Tooltip</Text.Body>
            <Container variant="flight-viewer__controls" style={{ position: 'relative' }}>
              <Container as="label" variant="flight-viewer__lens-select">
                <Container as="span">Camera Lens:</Container>
                <Container as="select" defaultValue="mavic3_wide">
                  <Container as="option" value="mavic3_wide">Mavic 3 Wide (24mm)</Container>
                  <Container as="option" value="mavic3_tele">Mavic 3 Tele (162mm)</Container>
                </Container>
              </Container>
            </Container>
            <Container
              variant="flight-viewer__tooltip"
              style={{ position: 'static', marginTop: '16px', pointerEvents: 'auto' }}
            >
              <Container variant="flight-viewer__tooltip-header">
                <Container as="span" variant="flight-viewer__tooltip-marker" style={{ background: '#4f83ff' }} />
                <Container as="strong">ridgeview-001.csv</Container> - Waypoint 12
              </Container>
              <Container variant="flight-viewer__tooltip-body">
                <Container variant="flight-viewer__tooltip-row">
                  <Container as="span">Heading:</Container>
                  <Container as="span">112.5deg</Container>
                </Container>
                <Container variant="flight-viewer__tooltip-row">
                  <Container as="span">Gimbal Pitch:</Container>
                  <Container as="span">-28.0deg</Container>
                </Container>
                <Container variant="flight-viewer__tooltip-row">
                  <Container as="span">Altitude:</Container>
                  <Container as="span">240 ft</Container>
                </Container>
                <Container variant="flight-viewer__tooltip-row">
                  <Container as="span">Speed:</Container>
                  <Container as="span">6.5 m/s</Container>
                </Container>
              </Container>
            </Container>
          </Container>
        </Layout.Grid>

        <Container variant={['component-library-card', 'component-library-card-wide']}>
          <Text.Body withBase={false} className="component-library-label">Converter Modal</Text.Body>
          <Container
            variant="flight-viewer__modal-overlay"
            style={{ position: 'relative', inset: 'auto', minHeight: '320px' }}
          >
            <Container variant="flight-viewer__modal">
              <Container variant="flight-viewer__modal-header">
                <Text.H2 withBase={false}>CSV to KMZ Converter</Text.H2>
                <Button.Base variant="flight-viewer__modal-close" type="button">x</Button.Base>
              </Container>
              <Container variant="flight-viewer__modal-body">
                <Text.Body withBase={false} className="flight-viewer__modal-description">
                  Convert Litchi CSV waypoint missions to DJI Fly/Pilot 2 compatible KMZ files.
                </Text.Body>
                <Container as="label" variant="flight-viewer__converter-upload">
                  <Container as="span">Select Litchi CSV file</Container>
                  <Input.Text type="file" accept=".csv,text/csv" />
                </Container>
                <Container variant="flight-viewer__converter-options">
                  <Container as="label">
                    <Container as="span">Signal Lost Action</Container>
                    <Container as="select" defaultValue="executeLostAction">
                      <Container as="option" value="executeLostAction">Execute Lost Action</Container>
                      <Container as="option" value="continue">Continue Mission</Container>
                    </Container>
                  </Container>
                  <Container as="label">
                    <Container as="span">Mission Speed (m/s)</Container>
                    <Input.Text type="number" min="1" max="15" step="0.1" defaultValue={8.85} />
                  </Container>
                </Container>
              </Container>
              <Container variant="flight-viewer__modal-actions">
                <Button.Base variant={['flight-viewer__modal-btn', 'secondary']} type="button">
                  Cancel
                </Button.Base>
                <Button.Base variant={['flight-viewer__modal-btn', 'primary']} type="button">
                  Convert & Download
                </Button.Base>
              </Container>
            </Container>
          </Container>
        </Container>
      </Container>

      <Container as="section" variant="component-library-section">
        <Container variant="component-library-section-header">
          <Text.H2 withBase={false}>Shape Tools UI</Text.H2>
          <Text.Body withBase={false}>Inline-styled panels used in the Shape Lab and Shape Viewer experiences.</Text.Body>
        </Container>
        <Layout.Grid variant="component-library-grid">
          <Container variant="component-library-card">
            <Text.Body withBase={false} className="component-library-label">Shape Lab Control Panel</Text.Body>
            <Container style={{
              background: 'rgba(28, 28, 30, 0.95)',
              backdropFilter: 'blur(20px)',
              borderRadius: '12px',
              padding: '16px',
              border: '0.5px solid rgba(255, 255, 255, 0.1)',
              color: '#ffffff',
            }}>
              <Text.H3 withBase={false} style={{ fontSize: '16px', marginBottom: '8px' }}>Flight Shape Lab</Text.H3>
              <Text.Body withBase={false} style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.6)', marginBottom: '16px' }}>
                Design and visualize 3D drone flight patterns
              </Text.Body>
              <Container style={{ marginBottom: '12px' }}>
                <Container style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <Container as="span" style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.8)' }}>Number of Batteries</Container>
                  <Container as="span" style={{ fontSize: '12px', color: '#007AFF' }}>3</Container>
                </Container>
                <Input.Text type="range" min="1" max="8" defaultValue={3} style={{ width: '100%' }} />
              </Container>
              <Container style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '8px' }}>
                <Container as="span" style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.8)' }}>Show Labels</Container>
                <Input.Text type="checkbox" defaultChecked style={{ accentColor: '#007AFF' }} />
              </Container>
            </Container>
          </Container>

          <Container variant="component-library-card">
            <Text.Body withBase={false} className="component-library-label">Shape Viewer Panel</Text.Body>
            <Container style={{
              background: '#1a1a1a',
              borderRadius: '12px',
              padding: '16px',
              color: '#ffffff',
              fontFamily: 'monospace',
              border: '1px solid #333',
            }}>
              <Text.H3 withBase={false} style={{ fontSize: '16px', marginBottom: '12px', color: '#00ff88' }}>
                Flight Shape Viewer
              </Text.H3>
              <Container style={{ marginBottom: '12px' }}>
                <Container as="label" style={{ display: 'block', fontSize: '11px', marginBottom: '6px', opacity: 0.8 }}>
                  Number of Bounces (N)
                </Container>
                <Input.Text type="range" min="3" max="12" defaultValue={6} style={{ width: '100%' }} />
                <Container style={{ fontSize: '12px', marginTop: '6px' }}>6</Container>
              </Container>
              <Container style={{ display: 'flex', alignItems: 'center' }}>
                <Input.Text type="checkbox" defaultChecked style={{ marginRight: '8px' }} />
                <Container as="span" style={{ fontSize: '11px' }}>Show Waypoint Labels</Container>
              </Container>
            </Container>
          </Container>
        </Layout.Grid>
      </Container>

      <Container as="section" variant="component-library-section">
        <Container variant="component-library-section-header">
          <Text.H2 withBase={false}>Modals</Text.H2>
          <Text.Body withBase={false}>Live modal components rendered with safe demo data.</Text.Body>
        </Container>
        <Layout.Flex variant="component-library-row">
          <Button.Secondary fixed type="button" onClick={() => setTermsOpen(true)}>
            Open Terms of Service
          </Button.Secondary>
          <Button.Secondary fixed type="button" onClick={() => setNewProjectOpen(true)}>
            Open New Project
          </Button.Secondary>
          <Button.Secondary fixed type="button" onClick={() => setDeliveryOpen(true)}>
            Open Model Delivery
          </Button.Secondary>
        </Layout.Flex>
      </Container>

      <TermsOfServiceModal isOpen={termsOpen} onClose={() => setTermsOpen(false)} />
      <NewProjectModal open={newProjectOpen} onClose={() => setNewProjectOpen(false)} />
      <ModelDeliveryModal
        open={deliveryOpen}
        onClose={() => setDeliveryOpen(false)}
        resolveClient={resolveClient}
        sendDelivery={sendDelivery}
        onDelivered={(project) => setLastDelivered(project as ModelDeliveryProject)}
      />
    </Container>
  );
}
