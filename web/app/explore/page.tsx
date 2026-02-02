'use client';

import React from 'react';
import { PROPERTIES } from '../../lib/data';

export const runtime = 'edge';

export default function ExplorePage(): JSX.Element {
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
                  <h3>{property.title}</h3>
                  <div className="property-card-bottom-row">
                    <p className="property-card-location">{property.location}</p>
                    <span className="cta-button2-fixed property-card-visit">
                      Visit
                    </span>
                  </div>
                </div>
              </div>
            </a>
          ))}
        </div>
      </section>
    </>
  );
}
