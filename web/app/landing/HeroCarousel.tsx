'use client';

import React, { useState, useEffect, useRef } from 'react';

// Default landing page state
const DEFAULT_IFRAME = "https://hansenhomeai.github.io/WebbyDeerKnoll/";
const DEFAULT_SUBTITLE = "Create life-like 3D tours with your drone.";
const TIP_TEXT = "Tip: Pinch to zoom";

// Example data
const EXAMPLES = [
  {
    title: "Deer Knoll, Utah",
    src: "https://hansenhomeai.github.io/WebbyDeerKnoll/",
    originalLink: "https://hansenhomeai.github.io/WebbyDeerKnoll/"
  },
  {
    title: "Forest Creek, Utah",
    src: "https://spcprt.com/spaces/forest-creek-nux",
    originalLink: "https://spcprt.com/spaces/forest-creek-nux"
  },
  {
    title: "Edgewood Farm, Virginia",
    src: "https://spcprt.com/spaces/edgewood-farm-nux",
    originalLink: "https://spcprt.com/spaces/edgewood-farm-nux"
  },
  {
    title: "Cromwell Island, Montana",
    src: "https://spcprt.com/spaces/cromwell-island-nux",
    originalLink: "https://spcprt.com/spaces/cromwell-island-nux"
  }
];

export default function HeroCarousel(): JSX.Element {
  const [isActive, setIsActive] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1); // -1 means default state
  
  // Subtitle animation state
  const [subtitleText, setSubtitleText] = useState(DEFAULT_SUBTITLE);
  const [isTextVisible, setIsTextVisible] = useState(true);
  
  // Interaction state
  const [hasInteracted, setHasInteracted] = useState(false);
  const prevIndexRef = useRef(-1);
  const timeoutsRef = useRef<NodeJS.Timeout[]>([]);
  
  // Refs for dynamic blocking layer positioning
  const controlContainerRef = useRef<HTMLDivElement>(null);
  const blockingLayerRef = useRef<HTMLDivElement>(null);
  const topTriggerRef = useRef<HTMLDivElement>(null);

  // Helper to clear all timeouts
  const clearTimeouts = () => {
    timeoutsRef.current.forEach(t => clearTimeout(t));
    timeoutsRef.current = [];
  };
  
  // Handle user interaction (clears tooltip, marks interacted)
  const handleInteraction = () => {
    if (hasInteracted) return; // Already marked
    
    // Clear any pending tooltip timers immediately
    clearTimeouts();
    setHasInteracted(true);
    // The useEffect will catch the state change and revert text if needed
  };

  // Listen for interactions (messages from iframe or blur)
  useEffect(() => {
    const onBlur = () => {
      // Assuming blur means user clicked iframe
      if (isActive) handleInteraction();
    };
    
    const onMessage = (e: MessageEvent) => {
      // Listen for generic interaction messages if the iframe sends them
      // Also can listen for "scroll", "touch" if passed
      if (e.data === 'user-interaction') {
        handleInteraction();
      }
    };
    
    window.addEventListener('blur', onBlur);
    window.addEventListener('message', onMessage);
    
    return () => {
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('message', onMessage);
    };
  }, [isActive, hasInteracted, subtitleText, activeIndex]);

  // Update blocking layer position dynamically
  useEffect(() => {
    const updatePosition = () => {
      const landing = document.getElementById('landing');
      if (controlContainerRef.current && blockingLayerRef.current && landing) {
        // Measure the first child (the actual button/controls) if available, otherwise the container
        // This accounts for margins/padding that might push the visual controls down inside the container
        const targetEl = controlContainerRef.current.firstElementChild || controlContainerRef.current;
        
        const controlRect = targetEl.getBoundingClientRect();
        const landingRect = landing.getBoundingClientRect();
        
        // Calculate offset relative to the #landing container
        const relativeTop = controlRect.top - landingRect.top;
        
        blockingLayerRef.current.style.top = `${relativeTop}px`;
        if (topTriggerRef.current) {
          topTriggerRef.current.style.height = `${relativeTop}px`;
        }
      }
    };

    // Update on mount, resize, and when active state/content changes
    updatePosition();
    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition); // Also update on scroll just in case
    
    // Also update after a short delay to allow for transitions (H1 collapse)
    const t = setTimeout(updatePosition, 550); 
    
    return () => {
      window.removeEventListener('resize', updatePosition);
      window.removeEventListener('scroll', updatePosition);
      clearTimeout(t);
    };
  }, [isActive, subtitleText, activeIndex]);

  // Sync subtitle text with animation delay to match H1 collapse
  // AND handle the tooltip cycle
  useEffect(() => {
    const targetTitle = activeIndex === -1 ? DEFAULT_SUBTITLE : EXAMPLES[activeIndex].title;
    const prevIndex = prevIndexRef.current;
    
    // Determine if we are switching modes (Default <-> Carousel)
    const isModeChange = (prevIndex === -1 && activeIndex !== -1) || (prevIndex !== -1 && activeIndex === -1);
    
    // When carousel/iframe position changes: clear tooltip timers and reset displayed text
    // so the tooltip never sticks for 5s; the 2.75s buffer restarts for the new slide.
    if (prevIndex !== activeIndex) {
      clearTimeouts();
      // If we were showing the tooltip (or any stale text), immediately switch to the new title
      if (subtitleText !== targetTitle) {
        setIsTextVisible(false);
        const delay = isModeChange ? 400 : 200;
        const t1 = setTimeout(() => {
          setSubtitleText(targetTitle);
          setIsTextVisible(true);
          // Restart tooltip cycle for new slide (2.75s buffer, then show tip for 5s)
          if (activeIndex !== -1 && !hasInteracted) {
            const t2 = setTimeout(() => {
              setIsTextVisible(false);
              const t3 = setTimeout(() => {
                setSubtitleText(TIP_TEXT);
                setIsTextVisible(true);
                const t4 = setTimeout(() => {
                  setIsTextVisible(false);
                  const t5 = setTimeout(() => {
                    setSubtitleText(targetTitle);
                    setIsTextVisible(true);
                  }, 500);
                  timeoutsRef.current.push(t5);
                }, 5000);
                timeoutsRef.current.push(t4);
              }, 500);
              timeoutsRef.current.push(t3);
            }, 2750);
            timeoutsRef.current.push(t2);
          }
        }, delay);
        timeoutsRef.current.push(t1);
        prevIndexRef.current = activeIndex;
        return;
      }
    }

    // 1. Initial Transition (Title Change)
    if (subtitleText !== targetTitle && (subtitleText !== TIP_TEXT || hasInteracted)) {
      // Fade out immediately
      setIsTextVisible(false);
      
      const delay = isModeChange ? 500 : 250;
      
      const t1 = setTimeout(() => {
        setSubtitleText(targetTitle);
        setIsTextVisible(true);
        
        // 2. Queue Tooltip Logic (if active, not interacted, and not default)
        if (activeIndex !== -1 && !hasInteracted) {
          // Wait 2.75s after title appears
          const t2 = setTimeout(() => {
            // Fade out title
            setIsTextVisible(false);
            
            const t3 = setTimeout(() => {
              // Show Tooltip
              setSubtitleText(TIP_TEXT);
              setIsTextVisible(true);
              
              // Wait 5s
              const t4 = setTimeout(() => {
                // Fade out tooltip
                setIsTextVisible(false);
                
                const t5 = setTimeout(() => {
                  // Revert to Title
                  setSubtitleText(targetTitle);
                  setIsTextVisible(true);
                  // Cycle complete. Next model will restart logic because logic runs on activeIndex change 
                  // or we can recurse? "repeats until a model is interacted with"
                  // Since logic is tied to activeIndex, navigating to next model restarts this effect.
                  // If user stays on SAME model, does it repeat? "repeats until a model is interacted with" 
                  // usually implies across session (next model). 
                  // "If that 7.75 second tooltip cycle completes ... the next model they interact with will also show"
                  // implies single cycle per model view.
                }, 500);
                timeoutsRef.current.push(t5);
              }, 5000); // Hold for 5s
              timeoutsRef.current.push(t4);
            }, 500); // Transition time
            timeoutsRef.current.push(t3);
          }, 2750); // Wait 2.75s
          timeoutsRef.current.push(t2);
        }
        
      }, delay);
      timeoutsRef.current.push(t1);
    } else if (activeIndex !== -1 && !hasInteracted && subtitleText === targetTitle) {
      // This case handles mounting or updates where text matches but we still need tooltip cycle
      // (e.g. if we navigated back to same slide and effect re-ran? No, activeIndex changes)
      // Actually, standard path is above. This else block is safety.
      // But if we just rendered and text is correct, we still might need to trigger the tooltip sequence
      // if it hasn't run.
      // However, the above block runs when `subtitleText !== targetTitle`.
      // If they match initially, we might miss it.
      // But `subtitleText` usually starts as something else or previous value.
    }
    
    prevIndexRef.current = activeIndex;
    
    // Cleanup on unmount only, not every render, because we manually manage timeouts via ref
    return () => {
      // We don't clear timeouts here because we want them to persist during minor re-renders
      // unless activeIndex changes (handled at top of effect)
    };
  }, [activeIndex, hasInteracted]); // Dependencies: if interaction happens, effect runs? 
  // If `hasInteracted` changes to true, we want to stop the cycle.
  // `handleInteraction` calls `clearTimeouts`, which stops the cycle.
  // So we don't necessarily need `hasInteracted` in dependency array to trigger effect, 
  // but `handleInteraction` handles the cleanup.
  // However, if we add `hasInteracted` to deps, this effect runs again.
  // If `hasInteracted` is true, `!hasInteracted` block is skipped.
  // `subtitleText` might be `TIP_TEXT`. `targetTitle` is title.
  // `subtitleText !== targetTitle` is true.
  // It enters first block -> fades out TIP -> sets Title.
  // Then skips tooltip block.
  // This essentially implements the "revert to title" logic automatically!
  // So yes, include `hasInteracted`.

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

  // Handle iframe engagement - triggers carousel activation (same as Examples button)
  const handleIframeEngage = () => {
    if (activeIndex === -1) {
      setIsTextVisible(false); // Fade out title + subtitle together
      setActiveIndex(0);
    }
    setIsActive(true);
  };

  // Add non-passive listeners to top trigger to block scroll while capturing interaction
  useEffect(() => {
    const triggerEl = topTriggerRef.current;
    if (!triggerEl) return;

    const onScrollInteract = (e: Event) => {
      // Prevent page scroll
      if (e.cancelable) e.preventDefault();
      // Trigger carousel
      handleIframeEngage();
    };

    // Attach non-passive listeners for wheel and touchmove to block scrolling
    triggerEl.addEventListener('wheel', onScrollInteract, { passive: false });
    triggerEl.addEventListener('touchmove', onScrollInteract, { passive: false });

    return () => {
      triggerEl.removeEventListener('wheel', onScrollInteract);
      triggerEl.removeEventListener('touchmove', onScrollInteract);
    };
  }, [activeIndex, isActive]); // Re-bind if state changes (though handleIframeEngage logic is stable, we need latest closures if not using refs)


  const isDefaultState = activeIndex === -1;
  const currentExample = isDefaultState ? null : EXAMPLES[activeIndex];
  const currentIframeSrc = isDefaultState ? DEFAULT_IFRAME : currentExample?.src || DEFAULT_IFRAME;

  // Title and subtitle enter/exit together: title visible only when default content is shown and subtitle is visible
  const isTitleVisible = isDefaultState && subtitleText === DEFAULT_SUBTITLE && isTextVisible;

  return (
    <section className="section" id="landing">
      <iframe 
        className="landing-iframe" 
        src={currentIframeSrc} 
        title={currentExample?.title || "Spaceport"}
        style={{ opacity: 1, transition: 'opacity 0.5s ease' }}
        onFocus={handleIframeEngage}
        onPointerDown={handleIframeEngage}
        onTouchStart={handleIframeEngage}
        onWheel={handleIframeEngage}
      />
      <div id="iframe-overlay" className={isActive ? 'carousel-active' : ''} />
      {/* Capture top-area interactions to activate carousel, then pass through afterwards */}
      <div
        id="landing-top-trigger"
        ref={topTriggerRef}
        className={isActive ? '' : 'active'}
        onPointerDown={handleIframeEngage} // Keep click handling for pointer devices
        aria-hidden="true"
      />
      {/* Block iframe interaction below the controls - always active to limit interaction to area above controls */}
      <div
        id="landing-bottom-block"
        ref={blockingLayerRef}
        className="active"
        aria-hidden="true"
      />
      
      <div className={`landing-content ${isActive ? 'carousel-active' : ''}`}>
        
        {/* Title logic: Fade in/out in sync with subtitle (same timing) */}
        <h1 style={{ 
          opacity: isTitleVisible ? 1 : 0, 
          maxHeight: isTitleVisible ? '100px' : 0, 
          overflow: 'hidden',
          marginBottom: isTitleVisible ? '6px' : 0,
          transition: 'opacity 0.5s ease, maxHeight 0.5s ease, margin-bottom 0.5s ease',
          pointerEvents: 'none'
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
            color: 'rgba(255, 255, 255, 0.5)',
            opacity: isTextVisible ? 1 : 0
        }}>
          {subtitleText}
        </p>

        {/* Button / Carousel Control */}
        <div className="carousel-control-container" ref={controlContainerRef}>
          {isDefaultState ? (
            <button 
              className="cta-button with-symbol" 
              onClick={() => {
                setIsTextVisible(false); // Fade out title + subtitle together
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
