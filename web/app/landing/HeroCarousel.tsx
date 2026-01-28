'use client';

import React, { useState, useEffect, useRef } from 'react';

// Default landing page state
const DEFAULT_IFRAME = "https://hansenhomeai.github.io/WebbyDeerKnoll/";
const DEFAULT_SUBTITLE = "Convert drone imagery to life-like 3D models.";

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
  
  // Subtitle animation state
  const [subtitleText, setSubtitleText] = useState(DEFAULT_SUBTITLE);
  const [isTextVisible, setIsTextVisible] = useState(true);
  const prevIndexRef = useRef(-1);

  // Sync subtitle text with animation delay to match H1 collapse
  useEffect(() => {
    const targetText = activeIndex === -1 ? DEFAULT_SUBTITLE : EXAMPLES[activeIndex].title;
    const prevIndex = prevIndexRef.current;
    
    // Determine if we are switching modes (Default <-> Carousel)
    const isModeChange = (prevIndex === -1 && activeIndex !== -1) || (prevIndex !== -1 && activeIndex === -1);
    
    // Only animate if text actually changes
    if (subtitleText !== targetText) {
      // Fade out immediately
      setIsTextVisible(false);
      
      // If switching modes, wait for H1 animation (500ms). Otherwise faster transition (200ms).
      // The user specifically asked to tune the default <-> carousel transition.
      const delay = isModeChange ? 500 : 250;
      
      const timer = setTimeout(() => {
        setSubtitleText(targetText);
        setIsTextVisible(true);
      }, delay);
      
      return () => clearTimeout(timer);
    }
    
    prevIndexRef.current = activeIndex;
  }, [activeIndex, subtitleText]);

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

        {/* Subtitle logic: Changes text when active, but keeps subtitle font size */}
        <p className="hero-subtitle" style={{
            fontSize: '1.1rem', // Always subtitle font size
            fontWeight: 400,
            textShadow: '0 3px 16px rgba(0,0,0,1)',
            transition: 'opacity 0.5s ease, text-shadow 0.5s ease',
            marginBottom: '6px',
            color: '#fff',
            opacity: isTextVisible ? 1 : 0
        }}>
          {subtitleText}
        </p>

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
