'use client';
import Link from 'next/link';
import { useState } from 'react';

export default function Header(): JSX.Element {
  const [expanded, setExpanded] = useState(false);

  return (
    <header className={`header${expanded ? ' expanded' : ''}`}>
      <div className="header-top">
        <div className="logo" onClick={() => setExpanded(false)}>
          <Link href="/landing" aria-label="Spaceport AI Home">
            <img src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport AI" className="logo-image" />
          </Link>
        </div>

        <div className="nav-links-desktop">
          <Link href="/pricing">Pricing</Link>
          <Link href="/about">About</Link>
          <Link href="/create">Create</Link>
        </div>

        <div className={`toggle${expanded ? ' rotated' : ''}`} onClick={() => setExpanded((v) => !v)}>
          <span></span>
          <span></span>
        </div>
      </div>

      <div className="nav-links">
        <Link href="/pricing" onClick={() => setExpanded(false)}>Pricing</Link>
        <Link href="/about" onClick={() => setExpanded(false)}>About</Link>
        <Link href="/create" onClick={() => setExpanded(false)}>Create</Link>
      </div>
    </header>
  );
}

