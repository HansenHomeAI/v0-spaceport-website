'use client';
import { useEffect, useState } from 'react';
export const runtime = 'edge';
import NewProjectModal from '../../components/NewProjectModal';
import AuthGate from '../auth/AuthGate';
import { Auth } from 'aws-amplify';

export default function Create(): JSX.Element {
  const [modalOpen, setModalOpen] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [editing, setEditing] = useState<any | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const session = await Auth.currentSession();
        const idToken = session.getIdToken().getJwtToken();
        const res = await fetch(process.env.NEXT_PUBLIC_PROJECTS_API_URL || (globalThis as any).NEXT_PUBLIC_PROJECTS_API_URL || 'https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod/projects', {
          headers: { Authorization: `Bearer ${idToken}` },
        });
        if (res.ok) {
          const data = await res.json();
          setProjects(data.projects || []);
        }
      } catch {
        // ignore
      }
    })();
  }, []);

  return (
    <>
      {/* Always-visible header matching pricing/about spacing and swirl */}
      <section className="section" id="create">
        <div id="development-content">
          <h1>Create your space.</h1>
          <p><span className="inline-white">Transform your listings with ease. This streamlined workflow guides you from drone-captured imagery to a fully immersive 3D model.</span></p>
        </div>
      </section>

      {/* Auth-gated creation experience below the header */}
      <AuthGate>
        <section className="section" id="create-dashboard">
          <h2>Dashboard</h2>
          <div className="project-cards">
            <div className="project-box new-project-card" onClick={() => setModalOpen(true)}>
              <h1>New Project<span className="plus-icon"><span></span><span></span></span></h1>
            </div>
            {projects.map((p) => (
              <div key={p.projectId} className="project-box">
                <button className="project-controls-btn" aria-label="Edit project" onClick={() => { setEditing(p); setModalOpen(true); }}>
                  <img src="/assets/SpaceportIcons/Controls.svg" className="project-controls-icon" alt="Edit controls" />
                </button>
                <h1>{p.title || 'Untitled'}</h1>
                <div style={{marginTop:12}}>
                  <div style={{height:6, borderRadius:3, background:'rgba(255,255,255,0.1)'}}>
                    <div style={{height:6, borderRadius:3, width:`${Math.max(0, Math.min(100, p.progress||0))}%`, background:'#fff'}}></div>
                  </div>
                </div>
              </div>
            ))}
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
                <p>Each battery flies one complete slice of the pattern for optimal coverage. The system uses intelligent battery optimization with 95% utilization safety margin and neural network-optimized altitude logic for superior 3D model quality.</p>
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
                <p>Enter the relevant info to create the model. If you'd like property lines or embeded name tags, include the site map documents within the drone photos zip file, and make mention in the "optional notes" field.</p>
              </div>
            </div>
          </div>
        </section>
        <section className="section" id="create-steps3">
          <div>
            <h2>Step 3: model processing.</h2>
            <p>Sit tight—creating your model can take up to 3 days. We'll send a fully immersive 3D tour straight to your inbox once it's ready. If you run into any issues, just reach out using the feedback form below.</p>
          </div>
        </section>
        <NewProjectModal
          open={modalOpen}
          onClose={() => { setModalOpen(false); setEditing(null); }}
          project={editing || undefined}
          onSaved={async () => {
            try {
              const session = await Auth.currentSession();
              const idToken = session.getIdToken().getJwtToken();
              const res = await fetch(process.env.NEXT_PUBLIC_PROJECTS_API_URL || 'https://gcqqr7bwpg.execute-api.us-west-2.amazonaws.com/prod/projects', {
                headers: { Authorization: `Bearer ${idToken}` },
              });
              if (res.ok) {
                const data = await res.json();
                setProjects(data.projects || []);
              }
            } catch {}
          }}
        />
      </AuthGate>
    </>
  );
}

