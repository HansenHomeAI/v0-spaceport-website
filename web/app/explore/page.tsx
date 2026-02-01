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
            gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
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
                style={{ textDecoration: 'none' }}
                className="property-card"
              >
                <div style={{
                  borderRadius: '24px',
                  overflow: 'hidden',
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  height: '400px',
                  display: 'flex',
                  flexDirection: 'column',
                  position: 'relative',
                  transition: 'transform 0.3s ease, box-shadow 0.3s ease',
                  cursor: 'pointer',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-5px)';
                  e.currentTarget.style.boxShadow = '0 10px 30px rgba(0,0,0,0.3)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
                >
                  {/* Top 2/3 Image */}
                  <div style={{
                    height: '66%',
                    width: '100%',
                    position: 'relative',
                    overflow: 'hidden',
                  }}>
                    <img 
                      src={property.imageSrc} 
                      alt={property.title}
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                      }}
                    />
                  </div>
                  
                  {/* Bottom 1/3 Content */}
                  <div style={{
                    height: '34%',
                    padding: '24px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    position: 'relative',
                  }}>
                    <h3 style={{ 
                      color: 'white', 
                      fontSize: '1.4rem', 
                      marginBottom: '4px',
                      fontWeight: 500 
                    }}>
                      {property.title}
                    </h3>
                    <p style={{ 
                      color: 'rgba(255, 255, 255, 0.6)',
                      fontSize: '1rem',
                    }}>
                      {property.location}
                    </p>
                    
                    {/* Button in corner */}
                    <div style={{
                      position: 'absolute',
                      bottom: '24px',
                      right: '24px',
                      width: '40px',
                      height: '40px',
                      borderRadius: '50%',
                      background: 'rgba(255, 255, 255, 0.1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                    }}>
                       <img 
                        src="/assets/SpaceportIcons/Arrow.svg" 
                        alt="Visit" 
                        style={{ 
                          width: '14px', 
                          height: '14px',
                          filter: 'invert(1)', // Ensure white arrow
                        }} 
                      />
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
