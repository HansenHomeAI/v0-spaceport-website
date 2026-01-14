'use client';

import { useCallback, useEffect, useMemo, useState, useId } from 'react';

import type {
  ModelDeliveryClient,
  ModelDeliveryProject,
  ResolveClientResponse,
} from '../app/hooks/useModelDeliveryAdmin';
import { Button, Container, Input, Modal, Text } from './foundational';

interface ModelDeliveryModalProps {
  open: boolean;
  onClose: () => void;
  resolveClient: (email: string) => Promise<ResolveClientResponse>;
  sendDelivery: (payload: { clientEmail: string; projectId: string; modelLink: string; projectTitle?: string }) => Promise<any>;
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
  onDelivered,
}: ModelDeliveryModalProps): JSX.Element | null {
  const headingId = useId();
  const descriptionId = useId();
  const [clientEmail, setClientEmail] = useState('');
  const [client, setClient] = useState<ModelDeliveryClient | null>(null);
  const [projects, setProjects] = useState<ModelDeliveryProject[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [modelLink, setModelLink] = useState('');
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [successState, setSuccessState] = useState<{ messageId: string } | null>(null);
  const [loadingClient, setLoadingClient] = useState(false);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (!open) return;
    setClientEmail('');
    setClient(null);
    setProjects([]);
    setSelectedProjectId('');
    setModelLink('');
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
    if (!client || !selectedProjectId || !isValidUrl(modelLink)) {
      setSubmissionError('Provide a valid link, client, and project.');
      return;
    }

    setSubmissionError(null);
    setSending(true);
    setSuccessState(null);

    try {
      const response = await sendDelivery({
        clientEmail: client.email,
        projectId: selectedProjectId,
        modelLink: modelLink.trim(),
        projectTitle: selectedProject?.title,
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
    }
  }, [client, modelLink, onDelivered, selectedProject, selectedProjectId, sendDelivery]);

  if (!open) return null;

  return (
    <Modal.Overlay
      variant="model-delivery-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby={headingId}
      aria-describedby={descriptionId}
    >
      <Modal.Content variant="model-delivery-modal" role="document">
        <Container variant="model-delivery-header">
          <Text.H2 withBase={false} id={headingId}>Send Model Link</Text.H2>
          <Button.Base variant="model-delivery-close" onClick={onClose} aria-label="Close model delivery modal">
            <img src="/assets/SpaceportIcons/Close.svg" alt="Close" />
          </Button.Base>
        </Container>

        <Text.Body withBase={false} className="model-delivery-description" id={descriptionId}>
          Deliver the final 3D model to a client. The link is saved to their project and an email is sent instantly.
        </Text.Body>

        <Container
          as="form"
          variant="model-delivery-form"
          onSubmit={(event) => {
            event.preventDefault();
            handleSubmit();
          }}
        >
          <Container as="label" variant="model-delivery-label" htmlFor="client-email">
            Client Email
          </Container>
          <Container variant="model-delivery-lookup">
            <Input.Text
              id="client-email"
              type="email"
              value={clientEmail}
              onChange={(event) => setClientEmail(event.target.value)}
              placeholder="client@example.com"
              variant="model-delivery-input"
              required
            />
            <Button.Base
              type="button"
              variant="model-delivery-secondary"
              onClick={handleLookup}
              disabled={loadingClient}
            >
              {loadingClient ? 'Searching…' : 'Lookup'}
            </Button.Base>
          </Container>
          {client && (
            <Text.Body withBase={false} className="model-delivery-client-summary">
              Sending to <strong>{client.name || client.email}</strong>
            </Text.Body>
          )}
          {lookupError && <Text.Body withBase={false} className="model-delivery-error" role="alert">{lookupError}</Text.Body>}

          <Container as="label" variant="model-delivery-label" htmlFor="project-select">
            Project
          </Container>
          <Container
            as="select"
            id="project-select"
            variant="model-delivery-input"
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
          </Container>

          <Container as="label" variant="model-delivery-label" htmlFor="model-link-input">
            Model Link URL
          </Container>
          <Input.Text
            id="model-link-input"
            type="url"
            value={modelLink}
            onChange={(event) => setModelLink(event.target.value)}
            placeholder="https://viewer.spaceport.ai/..."
            variant="model-delivery-input"
            required
          />
          <Text.Body withBase={false} className="model-delivery-hint">
            URL must start with <code>https://</code>.
          </Text.Body>

          {submissionError && <Text.Body withBase={false} className="model-delivery-error" role="alert">{submissionError}</Text.Body>}
          {successState && (
            <Container variant="model-delivery-success" role="status">
              <Text.Body withBase={false}>Model link sent successfully.</Text.Body>
              <Text.Body withBase={false} className="model-delivery-meta">Resend message ID: {successState.messageId}</Text.Body>
            </Container>
          )}

          <Container variant="model-delivery-actions">
            <Button.Base
              type="button"
              variant="model-delivery-secondary"
              onClick={onClose}
            >
              Cancel
            </Button.Base>
            <Button.Base
              type="submit"
              variant="model-delivery-primary"
              disabled={sending || !client || !selectedProjectId || !isValidUrl(modelLink)}
            >
              {sending ? 'Sending…' : 'Send to client'}
            </Button.Base>
          </Container>
        </Container>
      </Modal.Content>
    </Modal.Overlay>
  );
}
