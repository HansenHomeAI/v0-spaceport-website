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
  publishViewer: (payload: { title: string; file: File }) => Promise<PublishViewerResponse>;
  onDelivered: (project: Record<string, any>) => void;
}

function isValidUrl(link: string): boolean {
  if (!link) return false;
  try {
    const url = new URL(link);
    return url.protocol === 'https:' || url.protocol === 'http:';
  } catch {
    return false;
  }
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
  const [modelLink, setModelLink] = useState('');
  const [preferredTitle, setPreferredTitle] = useState('');
  const [viewerFile, setViewerFile] = useState<File | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [successState, setSuccessState] = useState<{ messageId: string } | null>(null);
  const [loadingClient, setLoadingClient] = useState(false);
  const [sending, setSending] = useState(false);
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    if (!open) return;
    setClientEmail('');
    setClient(null);
    setProjects([]);
    setSelectedProjectId('');
    setModelLink('');
    setPreferredTitle('');
    setViewerFile(null);
    setLookupError(null);
    setSubmissionError(null);
    setSuccessState(null);
  }, [open]);

  const selectedProject = useMemo(
    () => projects.find((p) => p.projectId === selectedProjectId) || null,
    [projects, selectedProjectId]
  );

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

    setSubmissionError(null);
    setSending(true);
    setSuccessState(null);

    try {
      let finalLink = modelLink.trim();
      let viewerSlug: string | undefined;

      if (viewerFile) {
        if (!preferredTitle.trim()) {
          throw new Error('Preferred URL title is required when uploading a viewer file.');
        }

        setPublishing(true);
        const publishResult = await publishViewer({
          title: preferredTitle.trim(),
          file: viewerFile,
        });
        finalLink = publishResult.url;
        viewerSlug = publishResult.slug;
        setModelLink(finalLink);
      } else if (!isValidUrl(finalLink)) {
        throw new Error('Provide a valid model link URL.');
      }

      const response = await sendDelivery({
        clientEmail: client.email,
        projectId: selectedProjectId,
        modelLink: finalLink,
        projectTitle: selectedProject?.title,
        viewerSlug,
        viewerTitle: preferredTitle.trim() || undefined,
      });

      const deliveredProject = response?.project as ModelDeliveryProject | undefined;
      if (deliveredProject) {
        onDelivered(deliveredProject);
      }

      setSuccessState({ messageId: response?.messageId || 'unknown' });
    } catch (error: any) {
      setSubmissionError(error?.message || 'Unable to send model link');
    } finally {
      setSending(false);
      setPublishing(false);
    }
  }, [client, modelLink, onDelivered, preferredTitle, publishViewer, selectedProject, selectedProjectId, sendDelivery, viewerFile]);

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
          Deliver the final 3D model to a client. The link is saved to their project and an email is sent instantly.
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

          <label className="model-delivery-label" htmlFor="model-link-input">
            Model Link URL
          </label>
          <input
            id="model-link-input"
            type="url"
            value={modelLink}
            onChange={(event) => setModelLink(event.target.value)}
            placeholder="https://viewer.spaceport.ai/..."
            className="model-delivery-input"
            disabled={Boolean(viewerFile)}
            required
          />
          <p className="model-delivery-hint">
            URL must start with <code>https://</code>.
          </p>

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
          />
          <p className="model-delivery-hint">
            Used to generate the public link when you upload a viewer file.
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
          />
          <p className="model-delivery-hint">
            Upload the prepared viewer HTML to auto-generate a branded link.
          </p>

          {submissionError && <p className="model-delivery-error" role="alert">{submissionError}</p>}
          {successState && (
            <div className="model-delivery-success" role="status">
              <p>Model link sent successfully.</p>
              <p className="model-delivery-meta">Resend message ID: {successState.messageId}</p>
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
              disabled={sending || publishing || !client || !selectedProjectId || (!viewerFile && !isValidUrl(modelLink))}
            >
              {sending ? 'Sending…' : publishing ? 'Publishing…' : 'Send to client'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
