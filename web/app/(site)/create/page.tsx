'use client';
import React, { useEffect } from 'react';

export default function Create(): JSX.Element {
  // Load the existing script-based functionality for uploader/ML, keeping behavior intact
  useEffect(() => {
    // The legacy script depends on specific element IDs; ensure it is loaded
    const s = document.createElement('script');
    s.src = '/script.js';
    s.async = false;
    document.body.appendChild(s);
    return () => { document.body.removeChild(s); };
  }, []);

  return (
    <section className="section" id="create">
      <div id="development-content">
        <h1>Create your space.</h1>
        <p><span className="inline-white">Transform your listings with ease. This streamlined workflow guides you from drone-captured imagery to a fully immersive 3D model.</span></p>
      </div>
      {/* Mount points relied on by the legacy script for uploader & ML sections remain intact below */}
      <section className="section" id="create-dashboard">
        <div className="project-cards">
          <div className="project-box new-project-card"><h1>New Project<span className="plus-icon"><span></span><span></span></span></h1></div>
        </div>
      </section>
      <div id="newProjectPopup" className="popup-overlay hidden"></div>
      <section className="section" id="create-ml-processing">
        <div id="ml-container" className="dpu-container"><div className="dpu-container-inner"></div></div>
      </section>
    </section>
  );
}

