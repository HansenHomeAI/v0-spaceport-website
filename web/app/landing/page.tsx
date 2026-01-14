import { Button, Container, Layout, Section, Text } from '../../components/foundational';

export const runtime = 'edge';

export default function Landing(): JSX.Element {
  return (
    <>
      <Section id="landing">
        <Container as="iframe" variant="landing-iframe" src="https://hansenhomeai.github.io/WebbyDeerKnoll/" />
        <Container id="iframe-overlay" />
        <Container variant="landing-content">
          <Text.H1>Location. Visualized in 3D.</Text.H1>
          <Button.Primary href="/create">Join waitlist</Button.Primary>
        </Container>
      </Section>

      {/* Logos carousel (client logos, seamless loop) */}
      <Section id="landing-carousel">
        <Container variant="logo-carousel">
          <Container variant="logos">
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
          </Container>
        </Container>
      </Section>

      {/* Additional value prop (legacy: landing-additional) */}
      <Section id="landing-additional" variant="two-col-section">
        <Layout.TwoCol>
          <Text.H2>Show what matters most to buyers.</Text.H2>
          <Container variant="right-col">
            <Text.Body>Captivate buyers for longer with interactive 3D models that capture not just a building, but its location. View your property as if you're right there—feeling the neighborhood and natural flow around it.</Text.Body>
            <Button.Secondary href="https://deer-knoll-dr.hansentour.com" fixed withSymbol target="_blank">
              <Container as="img" variant="symbol-3d" src="/assets/SpaceportIcons/3D.svg" alt="" aria-hidden="true" />
              View example
            </Button.Secondary>
          </Container>
        </Layout.TwoCol>
      </Section>

      {/* Stats section matching legacy visuals */}
      <Section id="landing-stats">
        <Text.H2>Virtual experiences work.</Text.H2>
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

      {/* More sections from legacy */}
      <Section id="landing-more" variant="two-col-section">
        <Layout.TwoCol>
          <Text.H2>The future of property listings.</Text.H2>
          <Container variant="right-col">
            <Text.Body>
              Photos and 3D tours only show parts of a property—never the full picture. We create interactive models that let you explore the land, surroundings, and location in a way{' '}
              <Container as="span" variant="inline-white">no photo or video can match.</Container>
            </Text.Body>
            <Button.Secondary href="https://dolan-road.hansentour.com" fixed withSymbol target="_blank">
              <Container as="img" variant="symbol-3d" src="/assets/SpaceportIcons/3D.svg" alt="" aria-hidden="true" />
              View example
            </Button.Secondary>
          </Container>
        </Layout.TwoCol>
      </Section>

      <Section id="landing-more2" variant="two-col-section">
        <Layout.TwoCol>
          <Text.H2>Effortless creation with your drone.</Text.H2>
          <Container variant="right-col">
            <Text.Body>Creating your 3D model is effortless. Our system autonomously flies your drone, capturing the perfect shots with zero skill required. Simply upload your photos, and you'll receive the completed model straight to your inbox.</Text.Body>
            <Button.Secondary href="/create" fixed>Create your own</Button.Secondary>
          </Container>
        </Layout.TwoCol>
      </Section>


    </>
  );
}
