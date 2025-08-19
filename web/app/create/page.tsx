'use client';
import { useEffect, useState } from 'react';
export const runtime = 'edge';
import NewProjectModal from '../../components/NewProjectModal';
import AccountModal from '../../components/AccountModal';
import AuthGate from '../auth/AuthGate';
import { Auth } from 'aws-amplify';

export default function Create(): JSX.Element {
  const [modalOpen, setModalOpen] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [editing, setEditing] = useState<any | null>(null);
  const [isLoadingProjects, setIsLoadingProjects] = useState(true);

  const fetchProjects = async () => {
    try {
      setIsLoadingProjects(true);
      const session = await Auth.currentSession();
      const idToken = session.getIdToken().getJwtToken();
      const res = await fetch(process.env.NEXT_PUBLIC_PROJECTS_API_URL || 'https://34ap3qgem7.execute-api.us-west-2.amazonaws.com/prod/projects', {
        headers: { Authorization: `Bearer ${idToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        setProjects(data.projects || []);
      }
    } catch {
      // ignore
    } finally {
      setIsLoadingProjects(false);
    }
  };

  useEffect(() => { fetchProjects(); }, []);

  return (
    <>
      {/* Auth-gated creation experience */}
      <AuthGate>
        <section className="section" id="create-dashboard">
          <h1>Dashboard</h1>
          
          {/* Account Settings Modal */}
          <AccountModal />
          
          <div className="project-cards">
            <div className="project-box new-project-card" onClick={() => setModalOpen(true)}>
              <h1>New Project<span className="plus-icon"><span></span><span></span></span></h1>
            </div>
            
            {/* Loading state for projects */}
            {isLoadingProjects && (
              <div className="projects-loading">
                <div className="spinner"></div>
                <span>Loading projects...</span>
              </div>
            )}
            
            {/* Existing projects */}
            {!isLoadingProjects && projects.map((p) => (
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


        <NewProjectModal
          open={modalOpen}
          onClose={() => { setModalOpen(false); setEditing(null); }}
          project={editing || undefined}
          onSaved={fetchProjects}
        />
      </AuthGate>
    </>
  );
}

