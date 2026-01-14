import { Button, Container, Layout, Section, Text } from '../../components/foundational';

export const runtime = 'edge'; // build trigger: 2025-08-12-1:05pm

export default function About(): JSX.Element {
  return (
    <>
      <Section id="about" variant="two-col-section">
        <Text.H1>About Spaceport AI.</Text.H1>
        <Text.Body>
          <Container as="span" variant="inline-white">Real estate is all about location—yet most listings fail to showcase it properly. Photos and 3D tours capture the inside of a home well, but they leave out what matters most: the context, the surroundings, the feel of the space.</Container>
        </Text.Body>
        <Container variant="right-col">
          <Text.Body>
            <Container as="span" variant="inline-white">That's where Spaceport AI comes in.</Container>
          </Text.Body>
        </Container>
      </Section>
      <Section id="about-mission" variant="two-col-section">
        <Layout.TwoCol>
          <Text.H2>How it works.</Text.H2>
          <Container variant="right-col">
            <Text.Body>
              <Container as="span" variant="inline-white">Plan your flight</Container> – A drone pilot generates a flight path right here on our platform.
            </Text.Body>
            <Text.Body>
              <Container as="span" variant="inline-white">Capture and upload</Container> – The drone follows the path, taking photos, which are then uploaded back to us.
            </Text.Body>
            <Text.Body>
              <Container as="span" variant="inline-white">Get your model</Container> – We train a neural network on the images, and within 3 days, you receive a fully immersive 3D model straight to your inbox.
            </Text.Body>
            <Button.Secondary href="/create" fixed>Create your own</Button.Secondary>
          </Container>
        </Layout.TwoCol>
      </Section>
      <Section id="about-innovation" variant="two-col-section">
        <Layout.TwoCol>
          <Text.H2>Bringing AI to real estate.</Text.H2>
          <Container variant="right-col">
            <Text.Body>Noticing firsthand how listings fail to capture what buyers actually care about, avid engineer and founder Gabriel Hansen set out to fix it, building Spaceport to combine advances in neural networks with drone technology–creating a whole new way to showcase location.</Text.Body>
            <Text.Body>Our mission is simple: make the best tool for property marketing.</Text.Body>
          </Container>
        </Layout.TwoCol>
      </Section>
    </>
  );
}
