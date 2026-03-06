'use client';
import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
export const runtime = 'edge';
import NewProjectModal from '../../components/NewProjectModal';
import AuthGate from '../auth/AuthGate';
import { useSubscription } from '../hooks/useSubscription';
import BetaAccessInvite from '../../components/BetaAccessInvite';
import { Auth } from 'aws-amplify';
import { useRouter } from 'next/navigation';
import { trackEvent, AnalyticsEvents } from '../../lib/analytics';
import ModelDeliveryModal from '../../components/ModelDeliveryModal';
import { useModelDeliveryAdmin } from '../hooks/useModelDeliveryAdmin';

type ProjectRecord = Record<string, any> & {
  projectId?: string;
  title?: string;
  status?: string;
  progress?: number;
};

const MODEL_LINK_KEYS = [
  'modelLink',
  'model_link',
  'modelUrl',
  'model_url',
  'finalModelUrl',
  'final_model_url',
  'viewerUrl',
  'viewer_url',
  'finalViewerUrl',
  'final_viewer_url',
  'deliveryUrl',
  'delivery_url',
  'viewerLink',
  'viewer_link',
] as const;

const MODEL_LINK_KEY_SET = new Set<string>(Array.from(MODEL_LINK_KEYS));
const MODEL_LINK_CONTAINER_KEYS = ['delivery', 'links', 'assets', 'urls', 'outputs', 'result', 'metadata'];
const MODEL_LINK_KEY_PATTERN = /(model|viewer).*(url|link)|(url|link).*(model|viewer)/i;

const isLinkString = (value: unknown): value is string =>
  typeof value === 'string' && /^https?:\/\//i.test(value.trim());

const pickLinkFromObject = (source: Record<string, any> | undefined | null): string | null => {
  if (!source || typeof source !== 'object') return null;
  for (const [key, value] of Object.entries(source)) {
    if (isLinkString(value) && (MODEL_LINK_KEY_PATTERN.test(key) || MODEL_LINK_KEY_SET.has(key))) {
      return value.trim();
    }
  }
  return null;
};

const extractModelLink = (project: ProjectRecord): string | null => {
  const direct = pickLinkFromObject(project);
  if (direct) return direct;

  for (const key of MODEL_LINK_KEYS) {
    const candidate = project?.[key];
    if (isLinkString(candidate)) {
      return candidate.trim();
    }
  }

  for (const containerKey of MODEL_LINK_CONTAINER_KEYS) {
    const container = project?.[containerKey];
    if (isLinkString(container) && MODEL_LINK_KEY_PATTERN.test(containerKey)) {
      return container.trim();
    }
    if (container && typeof container === 'object') {
      const nested = pickLinkFromObject(container as Record<string, any>);
      if (nested) return nested;
    }
  }

  const visited = new Set<any>();
  const deepSearch = (node: any, depth: number): string | null => {
    if (!node || typeof node !== 'object' || depth > 3 || visited.has(node)) {
      return null;
    }
    visited.add(node);

    for (const [key, value] of Object.entries(node)) {
      if (isLinkString(value) && (MODEL_LINK_KEY_PATTERN.test(key) || MODEL_LINK_KEY_SET.has(key))) {
        return value.trim();
      }
    }

    for (const value of Object.values(node)) {
      if (typeof value === 'object') {
        const nested = deepSearch(value, depth + 1);
        if (nested) return nested;
      }
    }

    return null;
  };

  return deepSearch(project, 0);
};

const formatModelLinkDisplay = (link: string): string => {
  try {
    const url = new URL(link);
    const pathSegments = url.pathname.split('/').filter(Boolean);
    const finalSegment = pathSegments[pathSegments.length - 1];
    return finalSegment ? `${url.host}/${finalSegment}` : url.host;
  } catch {
    return link;
  }
};

export default function Create(): JSX.Element {
  const router = useRouter();
  const [modalOpen, setModalOpen] = useState(false);
  const [projects, setProjects] = useState<any[]>([]);
  const [editing, setEditing] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const [modelDeliveryOpen, setModelDeliveryOpen] = useState(false);
  
  // Subscription hook
  const {
    subscription,
    loading: subscriptionLoading,
    error: subscriptionError,
    isSubscriptionActive,
    isOnTrial,
    getTrialDaysRemaining,
  } = useSubscription();

  const {
    loading: modelDeliveryLoading,
    hasPermission: hasModelDeliveryPermission,
    error: modelDeliveryError,
    apiConfigured: modelDeliveryApiConfigured,
    resolveClient,
    sendDelivery,
    publishViewer,
    checkPermission: refreshModelDeliveryPermission,
  } = useModelDeliveryAdmin();


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
    refreshModelDeliveryPermission();
  }, [refreshModelDeliveryPermission]);

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

  const handleDeliverySuccess = useCallback((delivered: ProjectRecord) => {
    setProjects((prev) => prev.map((project) => {
      if (project.projectId === delivered.projectId) {
        return { ...project, ...delivered };
      }
      return project;
    }));
    fetchProjects();
  }, [fetchProjects]);

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
                          {projects.length} active models
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
              className="project-box new-project-card"
              onClick={() => setModalOpen(true)}
            >
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
            {!loading && projects.map((project, index) => (
              <ProjectCard
                key={project?.projectId || `project-${index}`}
                project={project as ProjectRecord}
                onEdit={(selected) => {
                  setEditing(selected);
                  setModalOpen(true);
                }}
              />
            ))}
            
            {/* Beta Access Management - Only shown to authorized employees */}
            <BetaAccessInvite />

            {/* Model Delivery - Only shown to authorized employees */}
            {hasModelDeliveryPermission && (
              <div className="project-box model-delivery-card">
                <h4>Model Delivery</h4>
                <p>Send a final model link to a client and attach it to their project.</p>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                  <button
                    className="model-delivery-primary"
                    onClick={() => setModelDeliveryOpen(true)}
                    disabled={modelDeliveryLoading || !modelDeliveryApiConfigured}
                  >
                    Send Model Link
                  </button>
                  {modelDeliveryError && (
                    <p className="model-delivery-banner-error" role="status" style={{ margin: 0 }}>
                      {modelDeliveryError}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </section>


        <NewProjectModal
          open={modalOpen}
          onClose={() => { setModalOpen(false); setEditing(null); }}
          project={editing || undefined}
          onSaved={fetchProjects}
        />

        {hasModelDeliveryPermission && (
          <ModelDeliveryModal
            open={modelDeliveryOpen}
            onClose={() => setModelDeliveryOpen(false)}
            resolveClient={resolveClient}
            sendDelivery={sendDelivery}
            publishViewer={publishViewer}
            onDelivered={handleDeliverySuccess}
          />
        )}

      </AuthGate>
    </>
  );
}

type ProjectCardProps = {
  project: ProjectRecord;
  onEdit: (project: ProjectRecord) => void;
};

function ProjectCard({ project, onEdit }: ProjectCardProps): JSX.Element {
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'error'>('idle');
  const [copyMessage, setCopyMessage] = useState('');
  const [paymentBusy, setPaymentBusy] = useState(false);
  const [paymentError, setPaymentError] = useState('');
  const feedbackTimerRef = useRef<NodeJS.Timeout | null>(null);
  const viewTrackedRef = useRef(false);
  const unavailableTrackedRef = useRef(false);

  const modelLink = useMemo(() => extractModelLink(project), [project]);
  const displayLink = useMemo(() => (modelLink ? formatModelLinkDisplay(modelLink) : ''), [modelLink]);

  const normalizedStatus = useMemo(() => {
    const rawStatus = project?.status;
    return typeof rawStatus === 'string' ? rawStatus.toLowerCase() : '';
  }, [project?.status]);
  const normalizedPaymentStatus = useMemo(() => {
    const rawStatus = project?.paymentStatus;
    return typeof rawStatus === 'string' ? rawStatus.toLowerCase() : '';
  }, [project?.paymentStatus]);

  const isDelivered = normalizedStatus === 'delivered';
  const showPaymentLink = Boolean(normalizedPaymentStatus && normalizedPaymentStatus !== 'paid');

  const progressValue = useMemo(() => {
    const rawProgress = project?.progress;
    const numeric = typeof rawProgress === 'number' ? rawProgress : Number(rawProgress ?? 0);
    if (!Number.isFinite(numeric)) return 0;
    return Math.max(0, Math.min(100, numeric));
  }, [project?.progress]);

  useEffect(() => {
    if (modelLink && !viewTrackedRef.current) {
      trackEvent(AnalyticsEvents.MODEL_LINK_VIEWED, {
        project_id: project?.projectId,
        status: normalizedStatus || undefined,
      });
      viewTrackedRef.current = true;
    }
  }, [modelLink, normalizedStatus, project?.projectId]);

  useEffect(() => {
    if (!modelLink && isDelivered && !unavailableTrackedRef.current) {
      trackEvent(AnalyticsEvents.MODEL_LINK_UNAVAILABLE, {
        project_id: project?.projectId,
        status: normalizedStatus || undefined,
      });
      unavailableTrackedRef.current = true;
    }
  }, [isDelivered, modelLink, normalizedStatus, project?.projectId]);

  useEffect(() => () => {
    if (feedbackTimerRef.current) {
      clearTimeout(feedbackTimerRef.current);
    }
  }, []);

  const setFeedback = useCallback((state: 'copied' | 'error', message: string) => {
    setCopyState(state);
    setCopyMessage(message);
    if (feedbackTimerRef.current) {
      clearTimeout(feedbackTimerRef.current);
    }
    feedbackTimerRef.current = setTimeout(() => {
      setCopyState('idle');
      setCopyMessage('');
    }, 2500);
  }, []);

  const handleCopy = useCallback(async () => {
    if (!modelLink) return;

    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(modelLink);
      } else if (typeof document !== 'undefined') {
        const textarea = document.createElement('textarea');
        textarea.value = modelLink;
        textarea.setAttribute('readonly', '');
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      } else {
        throw new Error('Clipboard unavailable');
      }

      setFeedback('copied', 'Link copied to clipboard');
      trackEvent(AnalyticsEvents.MODEL_LINK_COPIED, {
        project_id: project?.projectId,
        status: normalizedStatus || undefined,
      });
    } catch (error: any) {
      setFeedback('error', 'Unable to copy link');
      trackEvent(AnalyticsEvents.MODEL_LINK_COPY_FAILED, {
        project_id: project?.projectId,
        status: normalizedStatus || undefined,
        error: error?.message,
      });
    }
  }, [modelLink, normalizedStatus, project?.projectId, setFeedback]);

  const handleOpen = useCallback(() => {
    if (!modelLink) return;
    trackEvent(AnalyticsEvents.MODEL_LINK_OPENED, {
      project_id: project?.projectId,
      status: normalizedStatus || undefined,
    });
  }, [modelLink, normalizedStatus, project?.projectId]);

  const handlePayment = useCallback(async () => {
    if (!project?.projectId || paymentBusy) return;
    setPaymentBusy(true);
    setPaymentError('');
    try {
      const session = await Auth.currentSession();
      const idToken = session.getIdToken().getJwtToken();
      const apiBase = (process.env.NEXT_PUBLIC_PROJECTS_API_URL || '').replace(/\/$/, '');
      if (!apiBase) {
        throw new Error('Projects API is not configured');
      }
      const res = await fetch(`${apiBase}/${project.projectId}/payment-session`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${idToken}`,
        },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.error || 'Unable to start payment');
      }
      const paymentUrl = data?.paymentLink;
      if (!paymentUrl) {
        throw new Error('Payment link unavailable');
      }
      window.location.href = paymentUrl;
    } catch (error: any) {
      setPaymentError(error?.message || 'Unable to start payment');
    } finally {
      setPaymentBusy(false);
    }
  }, [paymentBusy, project?.projectId]);

  const handleEdit = useCallback(() => {
    onEdit(project);
  }, [onEdit, project]);

  const getGuidanceText = (): string => {
    const p = progressValue;
    const s = normalizedStatus;
    if (modelLink) return '';

    // Friendly, stage-based guidance
    if (isDelivered) return 'Model link not delivered yet';
    if (!s && p <= 0) return 'Plan drone flight';
    if (/new|created|draft/.test(s) || p === 0) return 'Plan drone flight';
    if (/upload|pending_upload/.test(s) || (p > 0 && p < 15)) return 'Upload photos';
    if (/processing|reconstruct|colmap|sfm|dense/.test(s) || (p >= 15 && p < 60)) return 'Reconstructing scene';
    if (/training|3dgs|render/.test(s) || (p >= 60 && p < 90)) return 'Training model';
    if (/compress|optimiz|sogs/.test(s) || (p >= 90 && p < 100)) return 'Optimizing web';
    return 'Preparing model';
  };

  return (
    <div className="project-box">
      <button className="project-controls-btn" aria-label="Edit project" onClick={handleEdit}>
        <img src="/assets/SpaceportIcons/Controls.svg" className="project-controls-icon" alt="Edit controls" />
      </button>
      <h1>{project?.title || 'Untitled'}</h1>
      <div className="project-progress">
        <div className="project-progress-track">
          <div className="project-progress-fill" style={{ width: `${progressValue}%` }}></div>
        </div>
      </div>

      <div className="model-link-area" role={modelLink ? 'group' : 'status'} aria-live={modelLink ? undefined : 'polite'}>
        {modelLink ? (
          <>
            <div className="model-link-pill">
              <span className="model-link-text" title={modelLink}>{displayLink}</span>
              <div className="model-link-actions">
                <a
                  className="model-link-button"
                  href={modelLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={handleOpen}
                  aria-label="Open model link in a new tab"
                >
                  Open
                </a>
                <button
                  type="button"
                  className="model-link-button"
                  onClick={handleCopy}
                  aria-label="Copy model link to clipboard"
                >
                  Copy
                </button>
              </div>
            </div>
            {copyState !== 'idle' && (
              <span className={`model-link-feedback ${copyState === 'error' ? 'error' : ''}`} role="status">
                {copyMessage}
              </span>
            )}
          </>
        ) : (
          <div className={`model-link-status ${isDelivered ? 'pending' : 'pending'}`} role="status">
            {getGuidanceText()}
          </div>
        )}
        {showPaymentLink && (
          <>
            <div className="payment-link-pill" role="group" aria-label="Payment required">
              <span className="payment-link-text">Payment pending</span>
              <div className="payment-link-actions">
                <button
                  type="button"
                  className="payment-link-button"
                  onClick={handlePayment}
                  disabled={paymentBusy}
                >
                  {paymentBusy ? 'Opening checkout...' : 'Complete payment'}
                </button>
              </div>
            </div>
            {paymentError && (
              <span className="payment-link-feedback" role="status">
                {paymentError}
              </span>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Beta access admin system deployed - Thu Sep  4 00:26:19 MDT 2025
// Beta access API URL secret added - Thu Sep  4 00:29:32 MDT 2025
// Production database switch completed - Thu Sep  4 15:14:48 MDT 2025
// Production database switch completed - Thu Sep  4 15:16:49 MDT 2025
// Fixed production Cognito client ID - Thu Sep  4 15:30:35 MDT 2025
