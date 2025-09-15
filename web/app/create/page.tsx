'use client';
import { useEffect, useState } from 'react';
export const runtime = 'edge';
import NewProjectModal from '../../components/NewProjectModal';
import AuthGate from '../auth/AuthGate';
import { useSubscription } from '../hooks/useSubscription';
import BetaAccessInvite from '../../components/BetaAccessInvite';
import { Auth } from 'aws-amplify';

export default function Create(): JSX.Element {
  const [modalOpen, setModalOpen] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [editing, setEditing] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const [subscriptionPopupOpen, setSubscriptionPopupOpen] = useState(false);
  
  // Subscription hook
  const { 
    subscription, 
    loading: subscriptionLoading, 
    error: subscriptionError,
    redirectToCheckout,
    cancelSubscription,
    isSubscriptionActive,
    isOnTrial,
    getTrialDaysRemaining,
    canCreateModel,
    getPlanFeatures
  } = useSubscription();

  // Lock body scroll when popup is open
  useEffect(() => {
    if (subscriptionPopupOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    
    // Cleanup on unmount
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [subscriptionPopupOpen]);

  const fetchProjects = async () => {
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
    // Wait for user to be authenticated before fetching data
    const initializeData = async () => {
      try {
        // Wait for user to be available
        const currentUser = await Auth.currentAuthenticatedUser();
        setUser(currentUser);
        
        // Now fetch projects and subscription data
        await fetchProjects();
      } catch (error) {
        console.log('User not authenticated yet, waiting...');
        // Retry after a short delay
        setTimeout(initializeData, 1000);
      }
    };
    
    initializeData();
  }, []);

  const signOut = async () => {
    try {
      await Auth.signOut();
      window.location.reload();
    } catch {
      // ignore
    }
  };

  const handleUpgrade = async (planType: string) => {
    await redirectToCheckout(planType as any);
  };

  const handleCancelSubscription = async () => {
    if (confirm('Are you sure you want to cancel your subscription? You\'ll lose access to premium features at the end of your current billing period.')) {
      await cancelSubscription();
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
      <AuthGate>
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
                          onClick={() => setSubscriptionPopupOpen(true)}
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

        {/* Subscription Popup */}
        {subscriptionPopupOpen && (
          <div className="subscription-popup-overlay" onClick={() => setSubscriptionPopupOpen(false)}>
            <div className="subscription-popup" onClick={(e) => e.stopPropagation()}>
              <div className="subscription-popup-header">
                <h2>Choose Your Plan</h2>
                <button className="popup-close" onClick={() => setSubscriptionPopupOpen(false)} />
              </div>
              
              <div className="subscription-plans">
                {/* Current Plan Display */}
                {subscription ? (
                  <div className="plan-card current">
                    <div className="plan-header">
                      <h3>{subscription.planType.charAt(0).toUpperCase() + subscription.planType.slice(1)} Plan</h3>
                      <span className="current-badge">Current</span>
                    </div>
                    <div className="plan-price">
                      {subscription.status === 'trialing' ? 'Free Trial' : 'Active'}
                    </div>
                    <div className="plan-features">
                      <div className="feature">• {subscription.planFeatures.maxModels === -1 ? 'Unlimited' : `Up to ${subscription.planFeatures.maxModels}`} active models</div>
                      <div className="feature">• {subscription.planFeatures.support} support</div>
                      <div className="feature">• {subscription.planFeatures.trialDays > 0 ? `${subscription.planFeatures.trialDays}-day trial` : 'No trial'}</div>
                    </div>
                    {subscription.status !== 'canceled' && (
                      <button 
                        className="plan-cancel-btn"
                        onClick={handleCancelSubscription}
                      >
                        Cancel Subscription
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="plan-card current">
                    <div className="plan-header">
                      <h3>Beta Plan</h3>
                      <span className="current-badge">Current</span>
                    </div>
                    <div className="plan-price">Free</div>
                    <div className="plan-features">
                      <div className="feature">• {projects.length} of 5 active models used</div>
                      <div className="feature">• Email support</div>
                      <div className="feature">• Perfect for getting started</div>
                    </div>
                  </div>
                )}

                {/* Available Plans */}
                <div className="plan-card">
                  <div className="plan-header">
                    <h3>Single Model</h3>
                  </div>
                  <div className="plan-price">$29<span className="plan-period">/mo</span></div>
                  <div className="plan-features">
                    <div className="feature">• One active model</div>
                    <div className="feature">• 1-month free trial</div>
                    <div className="feature">• Perfect for trying Spaceport</div>
                  </div>
                  <button 
                    className="plan-upgrade-btn"
                    onClick={() => handleUpgrade('single')}
                    disabled={subscription?.planType === 'single'}
                  >
                    {subscription?.planType === 'single' ? 'Current Plan' : 'Get Started'}
                  </button>
                </div>

                <div className="plan-card">
                  <div className="plan-header">
                    <h3>Starter</h3>
                  </div>
                  <div className="plan-price">$99<span className="plan-period">/mo</span></div>
                  <div className="plan-features">
                    <div className="feature">• Up to 5 active models</div>
                    <div className="feature">• Additional models $29/mo each</div>
                    <div className="feature">• 1-month free trial included</div>
                  </div>
                  <button 
                    className="plan-upgrade-btn"
                    onClick={() => handleUpgrade('starter')}
                    disabled={subscription?.planType === 'starter'}
                  >
                    {subscription?.planType === 'starter' ? 'Current Plan' : 'Start Starter'}
                  </button>
                </div>

                <div className="plan-card">
                  <div className="plan-header">
                    <h3>Growth</h3>
                  </div>
                  <div className="plan-price">$299<span className="plan-period">/mo</span></div>
                  <div className="plan-features">
                    <div className="feature">• Up to 20 active models</div>
                    <div className="feature">• Additional models $29/mo each</div>
                    <div className="feature">• 1-month free trial included</div>
                  </div>
                  <button 
                    className="plan-upgrade-btn"
                    onClick={() => handleUpgrade('growth')}
                    disabled={subscription?.planType === 'growth'}
                  >
                    {subscription?.planType === 'growth' ? 'Current Plan' : 'Start Growth'}
                  </button>
                </div>

                <div className="plan-card">
                  <div className="plan-header">
                    <h3>Enterprise</h3>
                  </div>
                  <div className="plan-price">Custom</div>
                  <div className="plan-features">
                    <div className="feature">• High-volume projects</div>
                    <div className="feature">• Custom integrations</div>
                    <div className="feature">• Dedicated support</div>
                    <div className="feature">• Team management</div>
                  </div>
                  <button className="plan-contact-btn">
                    Contact Sales
                  </button>
                </div>
              </div>
              
              <p style={{ marginTop: '24px', textAlign: 'center', fontSize: '0.9rem', opacity: '0.7' }}>
                All plans support additional active models at <span style={{ color: '#fff', opacity: '1' }}>$29/mo</span> per model beyond your plan.
              </p>
              
              {/* Referral Program Info */}
              <div className="referral-program-info">
                <h3>Referral Program</h3>
                <p>Share your unique handle with others. When they subscribe using your code, you'll receive 10% of their subscription for 6 months!</p>
                <p><strong>Your handle:</strong> {user?.attributes?.preferred_username || 'Not set'}</p>
              </div>
            </div>
          </div>
        )}
      </AuthGate>
    </>
  );
}

// Beta access admin system deployed - Thu Sep  4 00:26:19 MDT 2025
// Beta access API URL secret added - Thu Sep  4 00:29:32 MDT 2025
// Production database switch completed - Thu Sep  4 15:14:48 MDT 2025
// Production database switch completed - Thu Sep  4 15:16:49 MDT 2025
// Fixed production Cognito client ID - Thu Sep  4 15:30:35 MDT 2025
