import React from 'react';
import Link from 'next/link';
import Header from '../../components/Header';
import Footer from '../../components/Footer';

export const runtime = 'edge';

// Data from HeroCarousel
const PROPERTIES = [
  {
    title: "Deer Knoll, Utah",
    image: "/assets/1.png", // Placeholder mapping
    link: "https://hansenhomeai.github.io/WebbyDeerKnoll/"
  },
  {
    title: "Forest Creek, Utah",
    image: "/assets/2.png", // Placeholder mapping
    link: "https://spcprt.com/spaces/forest-creek-nux"
  },
  {
    title: "Edgewood Farm, Virginia",
    image: "/assets/3.png", // Placeholder mapping
    link: "https://spcprt.com/spaces/edgewood-farm-nux"
  },
  {
    title: "Cromwell Island, Montana",
    image: "/assets/4.png", // Placeholder mapping
    link: "https://spcprt.com/spaces/cromwell-island-nux"
  }
];

export default function Explore(): JSX.Element {
  return (
    <>
      <Header />
      <main className="main-content">
        <section className="section" id="explore-hero">
          <div className="section-content">
            <h1 className="hero-title">Explore Spaces.</h1>
            <p className="hero-subtitle">Immersive 3D tours created with Spaceport AI.</p>
          </div>
        </section>

        <section className="section" id="explore-grid">
          <div className="property-grid">
            {PROPERTIES.map((property, index) => (
              <div key={index} className="property-card">
                <div className="card-image-container">
                  <img src={property.image} alt={property.title} className="card-image" />
                  <div className="card-overlay">
                    <a href={property.link} target="_blank" rel="noopener noreferrer" className="cta-button">
                      Visit
                    </a>
                  </div>
                </div>
                <div className="card-content">
                  <h3>{property.title}</h3>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
      <Footer />
      
      <style jsx>{`
        .hero-title {
          font-size: 3.5rem;
          margin-bottom: 1rem;
          background: linear-gradient(180deg, #FFFFFF 0%, rgba(255, 255, 255, 0.7) 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        
        .hero-subtitle {
          font-size: 1.2rem;
          color: rgba(255, 255, 255, 0.7);
          max-width: 600px;
        }

        .property-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 2rem;
          width: 100%;
          max-width: 1200px;
          margin: 0 auto;
        }

        .property-card {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          overflow: hidden;
          transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .property-card:hover {
          transform: translateY(-5px);
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
          border-color: rgba(255, 255, 255, 0.2);
        }

        .card-image-container {
          position: relative;
          aspect-ratio: 16/9;
          overflow: hidden;
        }

        .card-image {
          width: 100%;
          height: 100%;
          object-fit: cover;
          transition: transform 0.5s ease;
        }

        .property-card:hover .card-image {
          transform: scale(1.05);
        }

        .card-overlay {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.4);
          display: flex;
          align-items: center;
          justify-content: center;
          opacity: 0;
          transition: opacity 0.3s ease;
        }

        .property-card:hover .card-overlay {
          opacity: 1;
        }

        .card-content {
          padding: 1.5rem;
        }

        .card-content h3 {
          margin: 0;
          font-size: 1.2rem;
          color: white;
          font-weight: 500;
        }

        @media (max-width: 768px) {
          .hero-title {
            font-size: 2.5rem;
          }
          
          .property-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </>
  );
}
