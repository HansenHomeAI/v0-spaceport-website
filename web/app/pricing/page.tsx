'use client';

import { Button, Container, Layout, Section, Text } from '../../components/foundational';

export const runtime = 'edge';

export default function Pricing(): JSX.Element {
  const enterpriseMailto =
    'mailto:sam@spcprt.com?subject=Enterprise%20Brokerage%20Pricing&body=Hello%20Spaceport%20team%2C%0A%0AWe%27re%20interested%20in%20enterprise%20brokerage%20pricing%20for%20multiple%20models.%0ACompany%3A%0AModel%20count%3A%0ATimeline%3A%0A%0AThanks%2C';

  return (
    <>
      <Section id="pricing-header">
        <Text.H1>Pricing.</Text.H1>
        <Text.Body>
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
            <Text.Body withBase={false}>Volume pricing for brokerages with large portfolios or deeper integrations.</Text.Body>
            <Button.Primary href={enterpriseMailto}>Contact</Button.Primary>
          </Container>
        </Layout.Grid>
      </Section>
    </>
  );
}
