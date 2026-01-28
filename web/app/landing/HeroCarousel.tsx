'use client';

import React, { useState, useEffect } from 'react';

// Default landing page state
const DEFAULT_IFRAME = "https://hansenhomeai.github.io/WebbyDeerKnoll/";

// Example data
const EXAMPLES = [
  {
    title: "Deer Knoll Drive",
    src: "https://hansenhomeai.github.io/WebbyDeerKnoll/",
    originalLink: "https://hansenhomeai.github.io/WebbyDeerKnoll/"
  },
  {
    title: "Dolan Road",
    src: "https://dolan-road.hansentour.com",
    originalLink: "https://dolan-road.hansentour.com"
  },
  {
    title: "Edgewood Farm, Virginia",
    src: "https://dolan-road.hansentour.com", // Duplicate for demo as requested
    originalLink: "https://dolan-road.hansentour.com"
  },
  {
    title: "Mullin Real Estate",
    src: "https://deer-knoll-dr.hansentour.com",
    originalLink: "https://deer-knoll-dr.hansentour.com"
  }
];

export default function HeroCarousel(): JSX.Element {
  const [isActive, setIsActive] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1); // -1 means default state
  const [showCarouselTitle, setShowCarouselTitle] = useState(false);
  const [showDefaultSubtitle, setShowDefaultSubtitle] = useState(true);

  const handleNext = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (activeIndex === EXAMPLES.length - 1) {
      // Go back to default after last example
      setActiveIndex(-1);
      setIsActive(false);
    } else {
      setActiveIndex((prev) => prev + 1);
    }
  };

  const handlePrev = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (activeIndex === 0) {
      // Go back to default from first example
      setActiveIndex(-1);
      setIsActive(false);
    } else {
      setActiveIndex((prev) => prev - 1);
    }
  };

  const handleDotClick = (idx: number) => {
    setActiveIndex(idx);
    setIsActive(true);
  };

  const isDefaultState = activeIndex === -1;
  const currentExample = isDefaultState ? null : EXAMPLES[activeIndex];
  const currentIframeSrc = isDefaultState ? DEFAULT_IFRAME : currentExample?.src || DEFAULT_IFRAME;

  // Handle subtitle visibility with proper timing for smooth transitions
  useEffect(() => {
    if (isDefaultState) {
      // When going back to default, hide carousel title immediately, then show default subtitle
      setShowCarouselTitle(false);
      setShowDefaultSubtitle(false);
      const timer = setTimeout(() => setShowDefaultSubtitle(true), 500);
      return () => clearTimeout(timer);
    } else {
      // When going to carousel, hide default subtitle first, then show carousel title after delay
      setShowDefaultSubtitle(false);
      setShowCarouselTitle(false);
      const timer = setTimeout(() => setShowCarouselTitle(true), 500);
      return () => clearTimeout(timer);
    }
  }, [isDefaultState]);

  return (
    <section className="section" id="landing">
      <iframe 
        className="landing-iframe" 
        src={currentIframeSrc} 
        title={currentExample?.title || "Spaceport AI"}
        style={{ opacity: 1, transition: 'opacity 0.5s ease' }} 
      />
      <div id="iframe-overlay" style={{ pointerEvents: isActive ? 'none' : 'auto' }} />
      
      <div className={`landing-content ${isActive ? 'carousel-active' : ''}`}>
        
        {/* Title logic: Hides H1 when active */}
        <h1 style={{ 
          opacity: isDefaultState ? 1 : 0, 
          maxHeight: isDefaultState ? '100px' : 0, 
          overflow: 'hidden',
          marginBottom: isDefaultState ? '6px' : 0,
          transition: 'all 0.5s ease',
          pointerEvents: isDefaultState ? 'auto' : 'none'
        }}>
          Sell the location.
        </h1>

        {/* Subtitle logic: Smooth fade transitions with proper timing */}
        {isDefaultState ? (
          <p className="hero-subtitle" style={{
              fontSize: '1.1rem',
              fontWeight: 400,
              textShadow: '0 3px 16px rgba(0,0,0,1)',
              transition: 'opacity 0.5s ease, max-height 0.5s ease, margin-bottom 0.5s ease',
              marginBottom: showDefaultSubtitle ? '6px' : 0,
              color: '#fff',
              opacity: showDefaultSubtitle ? 1 : 0,
              maxHeight: showDefaultSubtitle ? '100px' : 0,
              overflow: 'hidden'
          }}>
            Convert drone imagery to life-like 3D models.
          </p>
        ) : (
          <p className="hero-subtitle" style={{
              fontSize: '1.1rem',
              fontWeight: 400,
              textShadow: '0 3px 16px rgba(0,0,0,1)',
              transition: 'opacity 0.5s ease, max-height 0.5s ease, margin-bottom 0.5s ease',
              marginBottom: showCarouselTitle ? '6px' : 0,
              color: '#fff',
              opacity: showCarouselTitle ? 1 : 0,
              maxHeight: showCarouselTitle ? '100px' : 0,
              overflow: 'hidden'
          }}>
            {currentExample?.title || ""}
          </p>
        )}

        {/* Button / Carousel Control */}
        <div className="carousel-control-container">
          {isDefaultState ? (
            <button 
              className="cta-button with-symbol" 
              onClick={() => {
                setActiveIndex(0);
                setIsActive(true);
              }}
              style={{ display: 'inline-flex', alignItems: 'center', border: 'none', color: 'white', fontSize: '1.1rem' }}
            >
              <img src="/assets/SpaceportIcons/3D.svg" className="symbol-3d" alt="" aria-hidden="true" />
              Examples
            </button>
          ) : (
            <div className="carousel-controls cta-button">
              <button onClick={handlePrev} className="carousel-arrow left" aria-label="Previous example">
                 <img src="/assets/SpaceportIcons/Arrow.svg" alt="Previous" style={{ transform: 'rotate(180deg)' }} />
              </button>
              
              <div className="carousel-dots">
                {EXAMPLES.map((_, idx) => (
                  <button 
                    key={idx} 
                    className={`dot ${idx === activeIndex ? 'active' : ''}`}
                    onClick={(e) => { e.stopPropagation(); handleDotClick(idx); }}
                    aria-label={`Go to example ${idx + 1}`}
                  />
                ))}
              </div>

              <button onClick={handleNext} className="carousel-arrow right" aria-label="Next example">
                 <img src="/assets/SpaceportIcons/Arrow.svg" alt="Next" />
              </button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
