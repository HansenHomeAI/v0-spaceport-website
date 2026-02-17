'use client';

import { useCallback, useEffect, useMemo, useState, useId } from 'react';

import type {
  ModelDeliveryClient,
  ModelDeliveryProject,
  ResolveClientResponse,
  PublishViewerResponse,
} from '../app/hooks/useModelDeliveryAdmin';

interface ModelDeliveryModalProps {
  open: boolean;
  onClose: () => void;
  resolveClient: (email: string) => Promise<ResolveClientResponse>;
  sendDelivery: (payload: { clientEmail: string; projectId: string; modelLink: string; projectTitle?: string; viewerSlug?: string; viewerTitle?: string }) => Promise<any>;
  publishViewer: (payload: { title: string; file: File; slug?: string; mode?: 'create' | 'update' }) => Promise<PublishViewerResponse>;
  onDelivered: (project: Record<string, any>) => void;
}

const VIEWER_SLUG_REGEX = /^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/;

function normalizeViewerSlug(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (VIEWER_SLUG_REGEX.test(trimmed)) return trimmed;

  try {
    const parsed = new URL(trimmed);
    const segments = parsed.pathname.split('/').filter(Boolean);
    const candidate = segments[segments.length - 1] || '';
    if (VIEWER_SLUG_REGEX.test(candidate)) return candidate;
  } catch {
    // Fall back to path-like parsing below.
  }

  const withoutQuery = trimmed.split('?')[0].split('#')[0];
  const pathSegments = withoutQuery.split('/').filter(Boolean);
  const fallbackCandidate = pathSegments[pathSegments.length - 1] || '';
  return VIEWER_SLUG_REGEX.test(fallbackCandidate) ? fallbackCandidate : null;
}

export default function ModelDeliveryModal({
  open,
  onClose,
  resolveClient,
  sendDelivery,
  publishViewer,
  onDelivered,
}: ModelDeliveryModalProps): JSX.Element | null {
  const headingId = useId();
  const descriptionId = useId();
  const [clientEmail, setClientEmail] = useState('');
  const [client, setClient] = useState<ModelDeliveryClient | null>(null);
  const [projects, setProjects] = useState<ModelDeliveryProject[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [preferredTitle, setPreferredTitle] = useState('');
  const [viewerFile, setViewerFile] = useState<File | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [successState, setSuccessState] = useState<{ messageId: string; updated?: boolean } | null>(null);
  const [loadingClient, setLoadingClient] = useState(false);
  const [sending, setSending] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [updateAtExistingLink, setUpdateAtExistingLink] = useState(false);

  const selectedProject = useMemo(
    () => projects.find((p) => p.projectId === selectedProjectId) || null,
    [projects, selectedProjectId]
  );

  const existingViewerSlug = useMemo(() => {
    const d = selectedProject?.delivery;
    if (!d) return null;
    const fromDelivery = normalizeViewerSlug(d.viewerSlug || d.viewer_slug);
    if (fromDelivery) return fromDelivery;
    const link = d.modelLink || d.model_link || selectedProject?.modelLink;
    return normalizeViewerSlug(link);
  }, [selectedProject]);

  const existingModelLink = useMemo(() => {
    const d = selectedProject?.delivery;
    const link = d?.modelLink || d?.model_link || selectedProject?.modelLink;
    return typeof link === 'string' && link.startsWith('http') ? link : null;
  }, [selectedProject]);

  useEffect(() => {
    if (!open) return;
    setClientEmail('');
    setClient(null);
    setProjects([]);
    setSelectedProjectId('');
    setPreferredTitle('');
    setViewerFile(null);
    setLookupError(null);
    setSubmissionError(null);
    setSuccessState(null);
    setUpdateAtExistingLink(false);
  }, [open]);

  useEffect(() => {
    if (existingViewerSlug && selectedProject) {
      const d = selectedProject.delivery;
      const title = d?.viewerTitle || d?.viewer_title;
      if (typeof title === 'string' && title.trim()) {
        setPreferredTitle(title.trim());
      } else {
        setPreferredTitle(existingViewerSlug);
      }
    }
  }, [existingViewerSlug, selectedProject?.projectId]);

  const handleLookup = useCallback(async () => {
    if (!clientEmail.trim()) {
      setLookupError('Client email is required');
      setClient(null);
      setProjects([]);
      return;
    }

    setLookupError(null);
    setLoadingClient(true);
    setProjects([]);
    setClient(null);
    setSelectedProjectId('');
    setSuccessState(null);

    try {
      const result = await resolveClient(clientEmail.trim());
      setClient(result.client);
      setProjects(result.projects || []);
      if ((result.projects || []).length === 1) {
        setSelectedProjectId(result.projects[0].projectId);
      }
    } catch (error: any) {
      setLookupError(error?.message || 'Unable to load client');
    } finally {
      setLoadingClient(false);
    }
  }, [clientEmail, resolveClient]);

  const handleSubmit = useCallback(async () => {
    if (!client || !selectedProjectId) {
      setSubmissionError('Provide a client and project.');
      return;
    }

    if (!viewerFile) {
      setSubmissionError('Upload a viewer HTML file to continue.');
      return;
    }

    const title = preferredTitle.trim();
    if (!title) {
      setSubmissionError('Preferred URL title is required.');
      return;
    }

    const isUpdate = updateAtExistingLink && Boolean(existingViewerSlug);
    if (updateAtExistingLink && !existingViewerSlug) {
      setSubmissionError('Cannot update: no existing viewer slug for this project.');
      return;
    }

    setSubmissionError(null);
    setSending(true);
    setSuccessState(null);

    try {
      setPublishing(true);
      const publishResult = await publishViewer({
        title,
        file: viewerFile,
        mode: isUpdate ? 'update' : 'create',
        ...(isUpdate ? { slug: existingViewerSlug! } : {}),
      });
      const finalLink = publishResult.url;
      const viewerSlug = publishResult.slug;

      if (isUpdate) {
        if (!viewerSlug || viewerSlug !== existingViewerSlug) {
          throw new Error(
            `Update did not target the existing viewer slug (${existingViewerSlug}).`
          );
        }
        setSuccessState({ messageId: 'updated', updated: true });
      } else {
        const response = await sendDelivery({
          clientEmail: client.email,
          projectId: selectedProjectId,
          modelLink: finalLink,
          projectTitle: selectedProject?.title,
          viewerSlug,
          viewerTitle: title || undefined,
        });

        const deliveredProject = response?.project as ModelDeliveryProject | undefined;
        if (deliveredProject) {
          onDelivered(deliveredProject);
        }

        setSuccessState({ messageId: response?.messageId || 'unknown' });
      }
    } catch (error: any) {
      setSubmissionError(error?.message || 'Unable to send model link');
    } finally {
      setSending(false);
      setPublishing(false);
    }
  }, [client, existingViewerSlug, onDelivered, preferredTitle, publishViewer, selectedProject, selectedProjectId, sendDelivery, updateAtExistingLink, viewerFile]);

  if (!open) return null;

  return (
    <div
      className="model-delivery-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby={headingId}
      aria-describedby={descriptionId}
    >
      <div className="model-delivery-modal" role="document">
        <div className="model-delivery-header">
          <h2 id={headingId}>Send Model Link</h2>
          <button className="model-delivery-close" onClick={onClose} aria-label="Close model delivery modal">
            <img src="/assets/SpaceportIcons/Close.svg" alt="Close" />
          </button>
        </div>

        <p className="model-delivery-description" id={descriptionId}>
          Upload the viewer HTML and choose a URL title. We host it, save the link to the project, and email the client.
        </p>

        <form
          className="model-delivery-form"
          onSubmit={(event) => {
            event.preventDefault();
            handleSubmit();
          }}
        >
          <label className="model-delivery-label" htmlFor="client-email">
            Client Email
          </label>
          <div className="model-delivery-lookup">
            <input
              id="client-email"
              type="email"
              value={clientEmail}
              onChange={(event) => setClientEmail(event.target.value)}
              placeholder="client@example.com"
              className="model-delivery-input"
              required
            />
            <button
              type="button"
              className="model-delivery-secondary"
              onClick={handleLookup}
              disabled={loadingClient}
            >
              {loadingClient ? 'Searching…' : 'Lookup'}
            </button>
          </div>
          {client && (
            <p className="model-delivery-client-summary">
              Sending to <strong>{client.name || client.email}</strong>
            </p>
          )}
          {lookupError && <p className="model-delivery-error" role="alert">{lookupError}</p>}

          <label className="model-delivery-label" htmlFor="project-select">
            Project
          </label>
          <select
            id="project-select"
            className="model-delivery-input"
            value={selectedProjectId}
            onChange={(event) => setSelectedProjectId(event.target.value)}
            disabled={!projects.length}
            required
          >
            <option value="" disabled>
              {projects.length ? 'Select project' : 'Lookup a client first'}
            </option>
            {projects.map((project) => (
              <option key={project.projectId} value={project.projectId}>
                {project.title || 'Untitled'}
                {project.status ? ` · ${project.status}` : ''}
              </option>
            ))}
          </select>

          {existingViewerSlug && existingModelLink && (
            <div className="model-delivery-existing-link">
              <p className="model-delivery-label">Existing link for this project</p>
              <p className="model-delivery-link-display" title={existingModelLink}>
                <a href={existingModelLink} target="_blank" rel="noopener noreferrer">
                  {existingModelLink}
                </a>
              </p>
              <label className="model-delivery-checkbox-label">
                <input
                  type="checkbox"
                  checked={updateAtExistingLink}
                  onChange={(e) => setUpdateAtExistingLink(e.target.checked)}
                  className="model-delivery-checkbox"
                />
                Update content at this link (keep same URL)
              </label>
            </div>
          )}

          <label className="model-delivery-label" htmlFor="preferred-title-input">
            Preferred URL Title
          </label>
          <input
            id="preferred-title-input"
            type="text"
            value={preferredTitle}
            onChange={(event) => setPreferredTitle(event.target.value)}
            placeholder="123 Main Street"
            className="model-delivery-input"
            required
          />
          <p className="model-delivery-hint">
            This becomes the public URL slug (we auto-suffix if needed).
          </p>

          <label className="model-delivery-label" htmlFor="viewer-file-input">
            Upload Viewer File (HTML)
          </label>
          <input
            id="viewer-file-input"
            type="file"
            accept=".html,text/html"
            className="model-delivery-input"
            onChange={(event) => {
              const file = event.target.files?.[0] || null;
              setViewerFile(file);
            }}
            required
          />
          <p className="model-delivery-hint">
            Upload the viewer HTML to generate the hosted link automatically.
          </p>

          {submissionError && <p className="model-delivery-error" role="alert">{submissionError}</p>}
          {successState && (
            <div className="model-delivery-success" role="status">
              {successState.updated ? (
                <p>Content updated at existing link.</p>
              ) : (
                <>
                  <p>Model link sent successfully.</p>
                  <p className="model-delivery-meta">Resend message ID: {successState.messageId}</p>
                </>
              )}
            </div>
          )}

          <div className="model-delivery-actions">
            <button
              type="button"
              className="model-delivery-secondary"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="model-delivery-primary"
              disabled={sending || publishing || !client || !selectedProjectId || !viewerFile || !preferredTitle.trim()}
            >
              {sending ? 'Sending…' : publishing ? 'Publishing…' : updateAtExistingLink ? 'Update content' : 'Send to client'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
