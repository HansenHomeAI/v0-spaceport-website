'use client';

import React from 'react';
import { PROPERTIES } from '../../lib/data';

export const runtime = 'edge';

export default function ExplorePage(): JSX.Element {
  return (
    <div style={{ paddingTop: '100px', minHeight: '100vh' }}>
      <section className="section" style={{ padding: '0 20px 40px' }}>
        <div className="section-content">
          <h1 style={{ 
            fontSize: 'clamp(2.5rem, 5vw, 3.5rem)', 
            marginBottom: '40px',
            color: 'white',
            textAlign: 'center'
          }}>
            Explore Spaces.
          </h1>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: '30px',
            maxWidth: '1200px',
            margin: '0 auto',
          }}>
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
        </div>
      </section>
    </div>
  );
}
