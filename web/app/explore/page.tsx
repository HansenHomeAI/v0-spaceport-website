'use client';

import React from 'react';
import Link from 'next/link';
import Header from '../../components/Header';
import Footer from '../../components/Footer';

// Mock data for properties
const properties = [
  {
    id: 1,
    title: 'Edgewood Residence',
    image: '/assets/1.png',
    link: '/flight?scene=https://spaceport-upload-bucket.s3.us-west-2.amazonaws.com/1728518868672-Edgewood-1/1728518868672-Edgewood-1_header.json', // Example link based on known structure or placeholder
  },
  {
    id: 2,
    title: 'Mountain View Estate',
    image: '/assets/2.png',
    link: '#',
  },
  {
    id: 3,
    title: 'Lakeside Manor',
    image: '/assets/3.png',
    link: '#',
  },
  {
    id: 4,
    title: 'Urban Loft',
    image: '/assets/4.png',
    link: '#',
  },
  {
    id: 5,
    title: 'Seaside Villa',
    image: '/assets/5.png',
    link: '#',
  },
  {
    id: 6,
    title: 'Country Ranch',
    image: '/assets/6.png',
    link: '#',
  },
];

export default function ExplorePage(): JSX.Element {
  return (
    <div className="explore-page">
      <Header />
      
      <main className="explore-main">
        <section className="explore-hero">
          <h1>Explore Properties</h1>
          <p>Discover immersive 3D tours of our featured listings.</p>
        </section>

        <section className="property-grid">
          {properties.map((property) => (
            <div key={property.id} className="property-card">
              <div 
                className="card-image" 
                style={{ backgroundImage: `url(${property.image})` }}
                role="img"
                aria-label={property.title}
              />
              <div className="card-content">
                <h3>{property.title}</h3>
                <Link href={property.link} className="visit-button">
                  Visit
                </Link>
              </div>
            </div>
          ))}
        </section>
      </main>

      <Footer />
      
      <style jsx>{`
        .explore-page {
          background-color: #000;
          min-height: 100vh;
          color: #fff;
          display: flex;
          flex-direction: column;
        }

        .explore-main {
          padding-top: 100px; /* Space for fixed header */
          flex: 1;
          max-width: 1400px;
          margin: 0 auto;
          width: 100%;
          padding-left: 2rem;
          padding-right: 2rem;
          padding-bottom: 4rem;
        }

        .explore-hero {
          text-align: center;
          margin-bottom: 3rem;
        }

        .explore-hero h1 {
          font-size: 3rem;
          margin-bottom: 1rem;
          background: linear-gradient(90deg, #fff, #aaa);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .explore-hero p {
          color: #888;
          font-size: 1.2rem;
        }

        .property-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 2rem;
        }

        .property-card {
          background: #111;
          border-radius: 16px;
          overflow: hidden;
          transition: transform 0.3s ease, box-shadow 0.3s ease;
          border: 1px solid #222;
          height: 360px; /* Fixed height for consistency */
          display: flex;
          flex-direction: column;
        }

        .property-card:hover {
          transform: translateY(-5px);
          box-shadow: 0 10px 20px rgba(0,0,0,0.5);
          border-color: #333;
        }

        /* Top 2/3 Image */
        .card-image {
          height: 66.66%;
          width: 100%;
          background-size: cover;
          background-position: center;
        }

        /* Bottom 1/3 Content */
        .card-content {
          height: 33.33%;
          padding: 1.5rem;
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: linear-gradient(180deg, #1a1a1a 0%, #111 100%);
          position: relative;
        }

        .card-content h3 {
          font-size: 1.2rem;
          margin: 0;
          color: #fff;
          font-weight: 500;
          max-width: 60%;
        }

        .visit-button {
          background: #fff;
          color: #000;
          padding: 0.6rem 1.2rem;
          border-radius: 24px;
          text-decoration: none;
          font-weight: 600;
          transition: all 0.2s ease;
          font-size: 0.9rem;
        }

        .visit-button:hover {
          background: #ccc;
          transform: scale(1.05);
        }

        @media (max-width: 768px) {
          .property-grid {
            grid-template-columns: 1fr;
          }
          
          .explore-hero h1 {
            font-size: 2rem;
          }
        }
      `}</style>
    </div>
  );
}
