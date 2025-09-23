'use client';
import { useCallback, useEffect, useState } from 'react';
export const runtime = 'edge';
import NewProjectModal from '../../components/NewProjectModal';
import AuthGate from '../auth/AuthGate';
import { useSubscription } from '../hooks/useSubscription';
import BetaAccessInvite from '../../components/BetaAccessInvite';
import { Auth } from 'aws-amplify';
import { useRouter } from 'next/navigation';
import { trackEvent, AnalyticsEvents } from '../../lib/analytics';

export default function Create(): JSX.Element {
  const router = useRouter();
  const [modalOpen, setModalOpen] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [editing, setEditing] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  
  // Subscription hook
  const { 
    subscription, 
    loading: subscriptionLoading, 
    error: subscriptionError,
    isSubscriptionActive,
    isOnTrial,
    getTrialDaysRemaining,
    canCreateModel,
    getPlanFeatures
  } = useSubscription();


  const fetchProjects = useCallback(async () => {
    try {
      setLoading(true);
      const session = await Auth.currentSession();
      const idToken = session.getIdToken().getJwtToken();
      const res = await fetch(process.env.NEXT_PUBLIC_PROJECTS_API_URL!, {
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
  }, []);

  useEffect(() => {
    if (!user) return;
    fetchProjects();
  }, [fetchProjects, user]);

  const handleAuthenticated = useCallback((currentUser: any) => {
    setUser(currentUser);
  }, []);

  const signOut = async () => {
    try {
      await Auth.signOut();
      window.location.reload();
    } catch {
      // ignore
    }
  };



  const getSubscriptionStatusDisplay = () => {
    if (subscriptionLoading) return 'Loading...';
    if (subscriptionError) return 'Beta Plan'; // Show Beta Plan instead of error
    
    if (!subscription) return 'Beta Plan'; // Default to Beta Plan
    
    if (isOnTrial()) {
      const daysLeft = getTrialDaysRemaining();
      return `Trial - ${daysLeft} days left`;
    }
    
    return subscription.status.charAt(0).toUpperCase() + subscription.status.slice(1);
  };

  const getSubscriptionBadgeClass = () => {
    if (!subscription) return 'subscription-status active'; // Beta plan is active
    
    switch (subscription.status) {
      case 'active':
        return 'subscription-status active';
      case 'trialing':
        return 'subscription-status trialing';
      case 'past_due':
        return 'subscription-status past_due';
      case 'canceled':
        return 'subscription-status canceled';
      default:
        return 'subscription-status active'; // Default to active for beta
    }
  };

  return (
    <>
      {/* Always-visible header matching pricing/about spacing and swirl */}
      <section className="section" id="create">
        <div id="development-content">
          <h1>Dashboard</h1>
          <a 
            href="https://www.loom.com/share/e5b2d593df724c279742d9d4dcdbb5cf" 
            target="_blank" 
            rel="noopener noreferrer"
            className="cta-button"
          >
            Watch Tutorial
          </a>
        </div>
      </section>

      {/* Auth-gated creation experience below the header */}
      <AuthGate onAuthenticated={handleAuthenticated}>
        <section className="section" id="create-dashboard">
          <div className="project-cards">
            {/* Account Settings Card */}
            <div className="project-box account-card">
              <div className="account-info">
                <div className="account-details">
                  <div className="account-header">
                    <div className="account-info-compact">
                      <h3 className="account-handle">{user?.attributes?.preferred_username || user?.username || 'User'}</h3>
                      <div className="subscription-compact">
                        <button
                          className="subscription-pill clickable"
                          onClick={() => router.push('/pricing')}
                        >
                          {subscription ? subscription.planType.charAt(0).toUpperCase() + subscription.planType.slice(1) : 'Beta Plan'}
                        </button>
                        <span className="model-count">
                          {projects.length}/{subscription?.planFeatures?.maxModels || getPlanFeatures().maxModels} active models
                        </span>
                      </div>
                    </div>
                  </div>
                  
                </div>
                <button className="sign-out-btn" onClick={signOut}>
                  <span className="sign-out-icon"></span>
                  Sign Out
                </button>
              </div>
            </div>
            
            {/* New Project Button */}
            <div 
              className={`project-box new-project-card ${!canCreateModel(projects.length) ? 'disabled' : ''}`} 
              onClick={canCreateModel(projects.length) ? () => setModalOpen(true) : undefined}
            >
              <h1>New Project<span className="plus-icon"><span></span><span></span></span></h1>
              {!canCreateModel(projects.length) && (
                <p className="upgrade-prompt">
                  Upgrade your plan to create more models
                </p>
              )}
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
            
            {/* Beta Access Management - Only shown to authorized employees */}
            <BetaAccessInvite />
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

// Beta access admin system deployed - Thu Sep  4 00:26:19 MDT 2025
// Beta access API URL secret added - Thu Sep  4 00:29:32 MDT 2025
// Production database switch completed - Thu Sep  4 15:14:48 MDT 2025
// Production database switch completed - Thu Sep  4 15:16:49 MDT 2025
// Fixed production Cognito client ID - Thu Sep  4 15:30:35 MDT 2025
