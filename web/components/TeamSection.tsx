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
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: '20px',
        }}>
          {TEAM_MEMBERS.map((member) => (
            <div key={member.id} className="stat-box" style={{
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              textAlign: 'center',
              background: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '20px',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}>
              <div style={{
                width: '100px',
                height: '100px',
                borderRadius: '50%',
                overflow: 'hidden',
                marginBottom: '16px',
                background: 'rgba(255, 255, 255, 0.1)',
              }}>
                <img 
                  src={member.imageSrc} 
                  alt={member.name}
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              </div>
              
              <h3 style={{ fontSize: '1.4rem', marginBottom: '4px', color: 'white' }}>{member.name}</h3>
              <p style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '0.9rem', marginBottom: '12px', fontWeight: 500 }}>{member.role}</p>
              
              <p style={{ 
                color: 'rgba(255, 255, 255, 0.5)', 
                fontSize: '0.95rem', 
                marginBottom: '20px',
                lineHeight: '1.5',
                flexGrow: 1,
              }}>
                {member.bio}
              </p>
              
              <a 
                href={member.linkedinUrl} 
                target="_blank" 
                rel="noopener noreferrer"
                className="cta-button2"
                style={{
                  padding: '8px 20px',
                  fontSize: '0.9rem',
                  textDecoration: 'none',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                LinkedIn
                <img src="/assets/SpaceportIcons/Arrow.svg" alt="" style={{ width: '10px', height: '10px' }} />
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
