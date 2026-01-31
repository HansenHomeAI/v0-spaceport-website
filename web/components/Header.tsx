'use client';
import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

// rebuild
export default function Header(): JSX.Element {
  const [expanded, setExpanded] = useState(false);
  const pathname = usePathname();

  const close = () => setExpanded(false);

  return (
    <header className={`header${expanded ? ' expanded' : ''}`}>
      <div className="header-top">
        <div className="logo" onClick={close}>
          <Link href="/landing" aria-label="Spaceport AI Home">
            <img src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport AI" className="logo-image" />
          </Link>
        </div>

        <div className="nav-links-desktop">
          <Link href="/pricing" className={pathname === '/pricing' ? 'active' : ''}>Pricing</Link>
          <Link href="/explore" className={pathname === '/explore' ? 'active' : ''}>Explore</Link>
          <Link href="/create" className={pathname === '/create' ? 'active' : ''}>Create</Link>
          {/* Signup is now handled inline on the create page via AuthGate */}
        </div>

        <div className={`toggle${expanded ? ' rotated' : ''}`} onClick={() => setExpanded(v => !v)}>
          <img 
            src="/assets/SpaceportIcons/Arrow.svg" 
            alt={expanded ? 'Close menu' : 'Open menu'}
            className="toggle-arrow"
          />
        </div>
      </div>

      <div className="nav-links" style={{ display: expanded ? 'flex' : 'none' }}>
        <Link href="/pricing" onClick={close}>Pricing</Link>
        <Link href="/explore" onClick={close}>Explore</Link>
        <Link href="/create" onClick={close}>Create</Link>
      </div>
    </header>
  );
}
