'use client';
import { useEffect } from 'react';

export default function Create(): JSX.Element {
  useEffect(() => {
    // Load legacy behaviors for uploader/ML UI
    const s = document.createElement('script');
    s.src = '/script.js';
    s.async = false;
    document.body.appendChild(s);
    return () => { document.body.removeChild(s); };
  }, []);

  return (
    <>
      <section className="section" id="create">
        <div id="development-content">
          <h1>Create your space.</h1>
          <p><span className="inline-white">Transform your listings with ease. This streamlined workflow guides you from drone-captured imagery to a fully immersive 3D model.</span></p>
          <p>Compatible with: Mini 2, Mini SE (version 1 only), Air 2S, Mavic Mini 1, Mavic Air 2, Mavic 2 (Zoom/Pro), Mavic (Air/Pro), Phantom 4 (Standard/Advanced/Pro/ProV2), Phantom 3 (Standard/4K/Advanced/Professional), Inspire 1 (X3/Z3/Pro/RAW), Inspire 2 and Spark.</p>
          <p>Unsupported hardware: Air 3 and Mavic 3, as there is no SDK for these yet. DJI RC1/RC2 (with built-in screen), as it's not possible to install apps on it.</p>
        </div>
      </section>

      <section className="section" id="create-dashboard">
        <h2>Dashboard</h2>
        <p><span className="inline-white">Monitor your 3D model creation progress and manage your projects.</span> Track processing status, view completed models, and access all your project files in one centralized location.</p>
        <div className="project-cards">
          <div className="project-box new-project-card" onClick={() => (window as any).openNewProjectPopup?.()}>
            <h1>New Project<span className="plus-icon"><span></span><span></span></span></h1>
          </div>
          <div className="project-box"><button className="project-controls-btn" aria-label="Edit project"><img src="/assets/SpaceportIcons/Controls.svg" className="project-controls-icon" /></button><h1>Downtown Property</h1><p>Processing - Neural network training in progress.</p></div>
          <div className="project-box"><button className="project-controls-btn" aria-label="Edit project"><img src="/assets/SpaceportIcons/Controls.svg" className="project-controls-icon" /></button><h1>Lakeside Home</h1><p>Complete - Ready for deployment.</p></div>
        </div>
      </section>

      <div id="newProjectPopup" className="popup-overlay hidden">
        <div className="popup-content">
          <div className="popup-header">
            <div className="popup-title-section">
              <textarea id="projectTitle" className="popup-title-input" rows={1} placeholder="Untitled"></textarea>
              <span className="edit-icon" />
            </div>
            <button className="popup-close" onClick={() => (window as any).closeNewProjectPopup?.()} />
          </div>
          <div className="popup-content-scroll">
            <div className="accordion-section active" data-section="setup">
              <div className="accordion-header" onClick={() => (window as any).toggleAccordionSection?.('setup')}>
                <div className="accordion-title"><h3>Create Flight Plan</h3></div>
                <span className="accordion-chevron" />
              </div>
              <div className="accordion-content">
                <div className="popup-map-section">
                  <div id="map-container" className="map-container">
                    <button className="expand-button" id="expand-button"><span className="expand-icon" /></button>
                    <div className="map-dim-overlay" />
                    <div className="map-blur-background" />
                    <div className="map-instructions-center" id="map-instructions">
                      <div className="instruction-content">
                        <div className="instruction-pin" />
                        <h3>Select the focus point for your drone flight.</h3>
                      </div>
                    </div>
                    <div className="address-search-overlay">
                      <div className="address-search-wrapper">
                        <input type="text" id="address-search" className="text-fade-right" placeholder="Enter location" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

