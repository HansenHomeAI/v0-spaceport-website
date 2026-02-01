'use client';
import React from 'react';

// Team data
const teamMembers = [
  {
    id: 1,
    name: 'Team Member 1',
    role: 'Co-Founder & CEO',
    image: '/assets/SpaceportIcons/SpcprtBWIcon.png', // Placeholder
    linkedin: 'https://linkedin.com',
  },
  {
    id: 2,
    name: 'Team Member 2',
    role: 'Co-Founder & CTO',
    image: '/assets/SpaceportIcons/SpcprtBWIcon.png', // Placeholder
    linkedin: 'https://linkedin.com',
  },
  {
    id: 3,
    name: 'Team Member 3',
    role: 'Head of Product',
    image: '/assets/SpaceportIcons/SpcprtBWIcon.png', // Placeholder
    linkedin: 'https://linkedin.com',
  },
  {
    id: 4,
    name: 'Team Member 4',
    role: 'Lead Engineer',
    image: '/assets/SpaceportIcons/SpcprtBWIcon.png', // Placeholder
    linkedin: 'https://linkedin.com',
  },
];

export default function TeamSection(): JSX.Element {
  return (
    <section className="section team-section" id="team">
      <h2>Meet the Team</h2>
      <div className="team-grid">
        {teamMembers.map((member) => (
          <div key={member.id} className="team-card">
            <div className="member-photo-container">
              <img 
                src={member.image} 
                alt={member.name} 
                className="member-photo" 
              />
            </div>
            <div className="member-info">
              <h3>{member.name}</h3>
              <p className="member-role">{member.role}</p>
              <a 
                href={member.linkedin} 
                target="_blank" 
                rel="noopener noreferrer"
                className="linkedin-link"
                aria-label={`${member.name}'s LinkedIn`}
              >
                LinkedIn <span>↗</span>
              </a>
            </div>
          </div>
        ))}
      </div>

      <style jsx>{`
        .team-section {
          padding: 6rem 2rem;
          background-color: #000;
          color: #fff;
          text-align: center;
        }

        .team-section h2 {
          font-size: 2.5rem;
          margin-bottom: 3rem;
          background: linear-gradient(90deg, #fff, #888);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .team-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 3rem;
          max-width: 1200px;
          margin: 0 auto;
        }

        .team-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 1rem;
          transition: transform 0.3s ease;
        }

        .team-card:hover {
          transform: translateY(-5px);
        }

        .member-photo-container {
          width: 150px;
          height: 150px;
          border-radius: 50%;
          overflow: hidden;
          margin-bottom: 1.5rem;
          border: 2px solid #333;
          background: #111;
        }

        .member-photo {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .member-info h3 {
          font-size: 1.25rem;
          margin: 0 0 0.5rem 0;
          color: #fff;
        }

        .member-role {
          color: #888;
          font-size: 0.9rem;
          margin: 0 0 1rem 0;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .linkedin-link {
          color: #fff;
          text-decoration: none;
          font-size: 0.9rem;
          border: 1px solid #333;
          padding: 0.5rem 1rem;
          border-radius: 20px;
          transition: all 0.2s ease;
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
        }

        .linkedin-link:hover {
          background: #222;
          border-color: #666;
        }

        .linkedin-link span {
          font-size: 0.8em;
        }

        @media (max-width: 768px) {
          .team-section {
            padding: 4rem 1rem;
          }
        }
      `}</style>
    </section>
  );
}
