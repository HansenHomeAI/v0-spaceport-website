'use client';

import React, { useCallback } from 'react';
import { PROPERTIES } from '../../lib/data';

export const runtime = 'edge';

const DEBUG_ENDPOINT = 'http://127.0.0.1:7249/ingest/256c2b17-3bda-4985-b0bf-1f11562cd483';

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
        <h1>Explore Spaces.</h1>
        <p><span className="inline-white">Browse 3D experiences from our partners.</span></p>
      </section>
      <section className="section" id="explore-content">
        <div className="explore-grid">
          {PROPERTIES.map((property) => (
            <a
              key={property.id}
              href={property.link}
              target="_blank"
              rel="noopener noreferrer"
              className="property-card"
            >
              <div className="property-card-inner">
                <div className="property-card-image">
                  <img src={property.imageSrc} alt={property.title} />
                </div>
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
