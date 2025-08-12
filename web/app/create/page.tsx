'use client';
import { useState } from 'react';
export const runtime = 'edge';
import NewProjectModal from '../../components/NewProjectModal';

export default function Create(): JSX.Element {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <section className="section" id="create">
        <div id="development-content">
          <h1>Create your space.</h1>
          <p><span className="inline-white">Transform your listings with ease. This streamlined workflow guides you from drone-captured imagery to a fully immersive 3D model.</span></p>
        </div>
      </section>
      <section className="section" id="create-dashboard">
        <h2>Dashboard</h2>
        <div className="project-cards">
          <div className="project-box new-project-card" onClick={() => setModalOpen(true)}>
            <h1>New Project<span className="plus-icon"><span></span><span></span></span></h1>
          </div>
        </div>
      </section>
      <section className="section" id="create-steps1">
        <div className="flight-path-section">
          <div className="two-col-content">
            <div className="left-col">
              <h2 className="flight-path-title">Step 1: plan your drone flight.</h2>
            </div>
            <div className="right-col">
              <p>Our advanced algorithm creates exponential spiral flight patterns optimized for battery duration and neural network training. The system automatically calculates the perfect flight path that captures differentiated altitude data for maximum photo quality while respecting your constraints.</p>
              <p>Each battery flies one complete slice of the pattern for optimal coverage.</p>
            </div>
          </div>
        </div>
      </section>
      <section className="section" id="create-steps2">
        <div className="flight-path-section">
          <div className="two-col-content">
            <div className="left-col">
              <h2 className="flight-path-title">Step 2: upload drone photos.</h2>
            </div>
            <div className="right-col">
              <p>Enter the relevant info to create the model. Include optional notes if you want property lines or tags added.</p>
            </div>
          </div>
        </div>
      </section>
      <section className="section" id="create-steps3">
        <div>
          <h2>Step 3: model processing.</h2>
          <p>Sit tight—creating your model can take up to 3 days. We'll email you once it's ready.</p>
        </div>
      </section>
      <NewProjectModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </>
  );
}

