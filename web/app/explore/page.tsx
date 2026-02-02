'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { PROPERTIES } from '../../lib/data';

export const runtime = 'edge';

const DEBUG_ENDPOINT = 'http://127.0.0.1:7249/ingest/256c2b17-3bda-4985-b0bf-1f11562cd483';
const FALLBACK_IMAGE = '/assets/SpaceportIcons/SpcprtLarge.png';

type ExploreCard = {
  id: string;
  title: string;
  location: string;
  link: string;
  thumbnailUrl?: string;
};

function logVisitButtonEvent(
  event: 'enter' | 'leave',
  propertyId: string,
  target: HTMLElement
): void {
  // #region agent log
  const rect = target.getBoundingClientRect();
  fetch(DEBUG_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      location: 'explore/page.tsx:Visit button',
      message: `Visit button mouse${event}`,
      data: {
        event,
        propertyId,
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        left: Math.round(rect.left),
        top: Math.round(rect.top),
      },
      timestamp: Date.now(),
      sessionId: 'debug-session',
      hypothesisId: event === 'enter' ? 'H1' : 'H1',
    }),
  }).catch(() => {});
  // #endregion
}

export default function ExplorePage(): JSX.Element {
  const fallbackCards = useMemo<ExploreCard[]>(
    () => PROPERTIES.map((property) => ({
      id: property.id,
      title: property.title,
      location: property.location,
      link: property.link,
      thumbnailUrl: property.imageSrc,
    })),
    []
  );
  const [properties, setProperties] = useState<ExploreCard[]>(fallbackCards);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_EXPLORE_API_URL;
    if (!apiUrl) return;

    let cancelled = false;
    const load = async () => {
      try {
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error(`Explore API failed (${response.status})`);
        const data = await response.json();
        const items = (data?.items || []) as Array<any>;
        const mapped = items
          .filter((item) => item?.viewerUrl)
          .map((item) => ({
            id: item.id || item.viewerUrl || crypto.randomUUID(),
            title: item.title || 'Untitled',
            location: item.location || '',
            link: item.viewerUrl || '#',
            thumbnailUrl: item.thumbnailUrl || '',
          }));
        if (!cancelled && mapped.length) {
          setProperties(mapped);
        }
      } catch {
        // Keep fallback
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleVisitEnter = useCallback(
    (e: React.MouseEvent<HTMLSpanElement>, propertyId: string) => {
      logVisitButtonEvent('enter', propertyId, e.currentTarget);
    },
    []
  );
  const handleVisitLeave = useCallback(
    (e: React.MouseEvent<HTMLSpanElement>, propertyId: string) => {
      logVisitButtonEvent('leave', propertyId, e.currentTarget);
    },
    []
  );

  return (
    <>
      <section className="section" id="explore-header">
        <h1>Explore.</h1>
        <p><span className="inline-white">Discover 3D spaces created by our partners.</span></p>
      </section>
      <section className="section" id="explore-content">
        <div className="explore-grid">
          {properties.map((property) => (
            <a
              key={property.id}
              href={property.link}
              target="_blank"
              rel="noopener noreferrer"
              className="property-card"
            >
              <div className="property-card-inner">
                <div
                  className="property-card-image"
                  role="img"
                  aria-label={property.title}
                  style={{
                    ['--property-thumb' as any]: `url(${property.thumbnailUrl || FALLBACK_IMAGE})`,
                  }}
                />
                <div className="property-card-content">
                  <div className="property-card-content-left">
                    <h3>{property.title}</h3>
                    <p className="property-card-location">{property.location}</p>
                  </div>
                  <span
                    className="cta-button property-card-visit"
                    onMouseEnter={(e) => handleVisitEnter(e, property.id)}
                    onMouseLeave={(e) => handleVisitLeave(e, property.id)}
                  >
                    Visit
                  </span>
                </div>
              </div>
            </a>
          ))}
        </div>
      </section>
    </>
  );
}
