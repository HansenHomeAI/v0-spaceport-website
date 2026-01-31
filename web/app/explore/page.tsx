import React from 'react';
import Header from '../../components/Header';
import Footer from '../../components/Footer';
import ExploreGrid from '../../components/ExploreGrid';

export const runtime = 'edge';

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

        <ExploreGrid />
      </main>
      <Footer />
      
      {/* Page-specific styles that don't need styled-jsx (global classes or inline styles) */}
      {/* We use a style tag for the Server Component parts if needed, but styled-jsx is not supported here. 
          The hero styles were:
          .hero-title { font-size: 3.5rem; ... }
          .hero-subtitle { font-size: 1.2rem; ... }
          
          We can move these to a global CSS file or use inline styles for now to avoid the error.
          Given the project structure, adding a new CSS file might be overkill if we can just inline or use globals.
          However, let's use inline styles for the hero section to keep it simple and server-side compatible.
      */}
      <style>{`
        #explore-hero .hero-title {
          font-size: 3.5rem;
          margin-bottom: 1rem;
          background: linear-gradient(180deg, #FFFFFF 0%, rgba(255, 255, 255, 0.7) 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        
        #explore-hero .hero-subtitle {
          font-size: 1.2rem;
          color: rgba(255, 255, 255, 0.7);
          max-width: 600px;
        }

        @media (max-width: 768px) {
          #explore-hero .hero-title {
            font-size: 2.5rem;
          }
        }
      `}</style>
    </>
  );
}
