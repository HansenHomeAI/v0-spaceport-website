'use client';

import React from 'react';
import { TEAM_MEMBERS } from '../lib/data';

export default function TeamSection(): JSX.Element {
  return (
    <section className="section" id="team" style={{ padding: '70px 20px 40px' }}>
      <div className="team-content">
        <h2 style={{ 
          textAlign: 'left', 
          marginBottom: '2rem', 
          fontSize: '2rem', 
          fontWeight: 500, 
          color: 'white'
        }}>
          Meet the Team.
        </h2>
        
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          flexWrap: 'wrap',
          gap: '60px',
        }}>
          {TEAM_MEMBERS.map((member) => (
            <div key={member.id} style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              textAlign: 'center',
              width: '240px',
            }}>
              <div style={{
                width: '120px',
                height: '120px',
                borderRadius: '50%',
                overflow: 'hidden',
                marginBottom: '20px',
                background: 'rgba(255, 255, 255, 0.1)',
              }}>
                <img 
                  src={member.imageSrc} 
                  alt={member.name}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              </div>
              
              <h3 style={{ fontSize: '1.4rem', marginBottom: '8px', color: 'white', fontWeight: 500 }}>{member.name}</h3>
              <p style={{ color: 'rgba(255, 255, 255, 0.5)', fontSize: '1rem', marginBottom: '16px', fontWeight: 400 }}>{member.role}</p>
              
              <a 
                href={member.linkedinUrl} 
                target="_blank" 
                rel="noopener noreferrer"
                style={{
                  display: 'inline-block',
                  opacity: 0.8,
                  transition: 'opacity 0.2s',
                  cursor: 'pointer',
                }}
                onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                onMouseLeave={(e) => e.currentTarget.style.opacity = '0.8'}
                aria-label={`${member.name}'s LinkedIn`}
              >
                <img src="/assets/linkedin.svg" alt="LinkedIn" style={{ width: '24px', height: '24px' }} />
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
