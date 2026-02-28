'use client';

import React from 'react';
import { TEAM_MEMBERS } from '../lib/data';

export default function TeamSection(): JSX.Element {
  return (
    <section className="section" id="team" style={{ padding: '70px 20px 40px' }}>
      <div className="team-content">
        <h2 style={{ 
          textAlign: 'center', 
          marginBottom: '30px', 
          fontSize: '2rem', 
          fontWeight: 500, 
          color: 'white'
        }}>
          Meet the team.
        </h2>
        
        <div className="team-grid">
          {TEAM_MEMBERS.map((member) => (
            <div key={member.id} className="team-member-card">
              <div className="member-photo-container">
                <img 
                  src={member.imageSrc} 
                  alt={member.name}
                  className="member-photo"
                />
              </div>
              
              <div className="member-info">
                <h3 className="member-name">{member.name}</h3>
                <div className="member-role-row">
                  <p className="member-role">{member.role}</p>
                  <a 
                    href={member.linkedinUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="linkedin-link"
                    aria-label={`${member.name}'s LinkedIn`}
                  >
                    <img src="/assets/linkedin.svg" alt="LinkedIn" />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>

        <style jsx>{`
          .team-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 60px;
            align-items: start;
            justify-items: center;
          }

          /* Desktop: all three in one row (lower threshold so row kicks in sooner) */
          @media (min-width: 800px) {
            .team-grid {
              grid-template-columns: repeat(3, 1fr);
            }
          }

          .team-member-card {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            width: 200px;
            margin-top: 30px;
            margin-bottom: 30px;
          }

          .member-photo-container {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            overflow: hidden;
            margin-bottom: 20px;
            background: rgba(255, 255, 255, 0.1);
            flex-shrink: 0;
          }

          .member-photo {
            width: 100%;
            height: 100%;
            object-fit: cover;
          }

          .member-info {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            width: 100%;
          }

          .member-name {
            font-size: 1.4rem;
            margin-bottom: 8px;
            color: white;
            font-weight: 500;
            text-align: center;
          }

          .member-role-row {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
          }

          .member-role {
            color: rgba(255, 255, 255, 0.5);
            font-size: 1rem;
            margin: 0;
            font-weight: 400;
            text-align: center;
          }

          .linkedin-link {
            display: inline-block;
            opacity: 0.5;
            transition: opacity 0.2s;
            cursor: pointer;
          }
          
          .linkedin-link:hover {
            opacity: 1;
          }

          .linkedin-link img {
            display: flex;
            width: 14px;
            height: 14px;
          }

          /* Mobile: vertical center stack, centered on page */
          @media (max-width: 799px) {
            .team-grid {
              grid-template-columns: 1fr;
              gap: 28px;
              justify-items: center;
            }

            .team-member-card {
              flex-direction: column;
              align-items: center;
              text-align: center;
            }

            .member-photo-container {
              width: 80px;
              height: 80px;
              margin-bottom: 16px;
            }

            .member-info {
              align-items: center;
              text-align: center;
            }

            .member-name {
              margin-bottom: 4px;
            }
            
            .member-role-row {
              gap: 10px;
            }
          }
        `}</style>
      </div>
    </section>
  );
}
