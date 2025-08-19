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
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);

  const fetchProjects = async () => {
    try {
      setLoading(true);
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
      setLoading(false);
    }
  };

  const fetchUser = async () => {
    try {
      const currentUser = await Auth.currentAuthenticatedUser();
      setUser(currentUser);
    } catch {
      // ignore
    }
  };

  useEffect(() => { 
    fetchProjects(); 
    fetchUser();
  }, []);

  const signOut = async () => {
    try {
      await Auth.signOut();
      window.location.reload();
    } catch {
      // ignore
    }
  };

  return (
    <>
      {/* Always-visible header matching pricing/about spacing and swirl */}
      <section className="section" id="create">
        <div id="development-content">
          <h1>Dashboard</h1>
        </div>
      </section>

      {/* Auth-gated creation experience below the header */}
      <AuthGate>
        <section className="section" id="create-dashboard">
          <div className="project-cards">
            {/* Account Settings Card */}
            <div className="project-box account-card">
              <div className="account-info">
                <div className="account-details">
                  <h3 className="account-handle">{user?.attributes?.preferred_username || user?.username || 'User'}</h3>
                  <p className="account-subscription">Free Plan</p>
                </div>
                <button className="sign-out-btn" onClick={signOut}>
                  Sign Out
                </button>
              </div>
            </div>
            
            {/* New Project Button */}
            <div className="project-box new-project-card" onClick={() => setModalOpen(true)}>
              <h1>New Project<span className="plus-icon"><span></span><span></span></span></h1>
            </div>
            
            {/* Loading Spinner */}
            {loading && (
              <div className="project-box loading-card">
                <div className="loading-spinner">
                  <div className="spinner"></div>
                  <p>Loading projects...</p>
                </div>
              </div>
            )}
            
            {/* Projects */}
            {!loading && projects.map((p) => (
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

