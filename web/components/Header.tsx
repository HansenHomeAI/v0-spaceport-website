'use client';
import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button, Container, Layout } from './foundational';

export default function Header(): JSX.Element {
  const [expanded, setExpanded] = useState(false);
  const pathname = usePathname();

  const close = () => setExpanded(false);
  const headerVariants = ['header', expanded ? 'expanded' : undefined].filter(Boolean) as string[];
  const toggleVariants = ['toggle', expanded ? 'rotated' : undefined].filter(Boolean) as string[];

  return (
    <Container as="header" variant={headerVariants}>
      <Layout.Flex variant="header-top">
        <Container variant="logo" onClick={close}>
          <Link href="/landing" aria-label="Spaceport AI Home">
            <Container
              as="img"
              variant="logo-image"
              src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg"
              alt="Spaceport AI"
            />
          </Link>
        </Container>

        <Container variant="nav-links-desktop">
          <Button.Base href="/pricing" variant={pathname === '/pricing' ? 'active' : undefined}>
            Pricing
          </Button.Base>
          <Button.Base href="/about" variant={pathname === '/about' ? 'active' : undefined}>
            About
          </Button.Base>
          <Button.Base href="/create" variant={pathname === '/create' ? 'active' : undefined}>
            Create
          </Button.Base>
          {/* Signup is now handled inline on the create page via AuthGate */}
        </Container>

        <Container variant={toggleVariants} onClick={() => setExpanded(v => !v)}>
          <span />
          <span />
        </Container>
      </Layout.Flex>

      <Layout.Flex variant="nav-links" style={{ display: expanded ? 'flex' : 'none' }}>
        <Button.Base href="/pricing" onClick={close}>Pricing</Button.Base>
        <Button.Base href="/about" onClick={close}>About</Button.Base>
        <Button.Base href="/create" onClick={close}>Create</Button.Base>
      </Layout.Flex>
    </Container>
  );
}
