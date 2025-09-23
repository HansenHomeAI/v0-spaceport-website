'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { DeliveryProject } from '../app/hooks/useModelDelivery';

type Message = { type: 'success' | 'error'; text: string } | null;

type ModelDeliveryModalProps = {
  open: boolean;
  onClose: () => void;
  projects: DeliveryProject[];
  fetchingProjects: boolean;
  sendingDelivery: boolean;
  fetchProjects: (email: string) => Promise<{ success: boolean; projects?: DeliveryProject[]; message?: string }>;
  sendDelivery: (params: { email: string; projectId: string; link: string }) => Promise<{ success: boolean; message: string }>;
  clearError: () => void;
  error: string | null;
};

export default function ModelDeliveryModal({
  open,
  onClose,
  projects,
  fetchingProjects,
  sendingDelivery,
  fetchProjects,
  sendDelivery,
  clearError,
  error,
}: ModelDeliveryModalProps): JSX.Element | null {
  const [email, setEmail] = useState('');
  const [link, setLink] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [message, setMessage] = useState<Message>(null);

  useEffect(() => {
    if (!open) {
      setEmail('');
      setLink('');
      setSelectedProjectId('');
      setMessage(null);
      clearError();
    }
  }, [open, clearError]);

  useEffect(() => {
    if (projects.length === 0) {
      setSelectedProjectId('');
      return;
    }
    if (!selectedProjectId) {
      setSelectedProjectId(projects[0].projectId);
    } else if (!projects.some(project => project.projectId === selectedProjectId)) {
      setSelectedProjectId(projects[0].projectId);
    }
  }, [projects, selectedProjectId]);

  useEffect(() => {
    if (error) {
      setMessage({ type: 'error', text: error });
    }
  }, [error]);

  const selectedProject = useMemo(
    () => projects.find(project => project.projectId === selectedProjectId) || null,
    [projects, selectedProjectId]
  );

  if (!open) return null;

  const handleFetchProjects = async () => {
    clearError();
    setMessage(null);
    if (!email.trim()) {
      setMessage({ type: 'error', text: 'Enter a client email to continue' });
      return;
    }
    const result = await fetchProjects(email);
    if (!result.success) {
      setMessage({ type: 'error', text: result.message || 'Could not find any projects for that email' });
      return;
    }
    if (!result.projects || result.projects.length === 0) {
      setMessage({ type: 'error', text: 'No projects found for that email address' });
    } else {
      setMessage({ type: 'success', text: `Loaded ${result.projects.length} project${result.projects.length === 1 ? '' : 's'}` });
    }
  };

  const handleSendDelivery = async () => {
    clearError();
    setMessage(null);
    if (!email.trim() || !selectedProjectId) {
      setMessage({ type: 'error', text: 'Select a project and confirm the client email before sending' });
      return;
    }
    if (!link.trim()) {
      setMessage({ type: 'error', text: 'Paste the model link before sending' });
      return;
    }

    const result = await sendDelivery({ email, projectId: selectedProjectId, link });
    if (result.success) {
      setMessage({ type: 'success', text: result.message || 'Model link sent' });
    } else {
      setMessage({ type: 'error', text: result.message });
    }
  };

  const projectLabel = (project: DeliveryProject) => {
    const progress = Math.min(100, Math.max(0, Number(project.progress) || 0));
    const status = project.status ? project.status.replace(/_/g, ' ') : 'pending';
    return `${project.title} • ${status} • ${progress}%`;
  };

  const deliveryPreviewText = link.trim() || 'https://your-model-link.example.com';

  return (
    <div className="model-delivery-overlay" role="dialog" aria-modal="true">
      <div className="model-delivery-panel">
        <div className="modal-header">
          <div>
            <h2>Send 3D Model</h2>
            <p className="modal-subtitle">Share the final model link with your client directly inside their project space.</p>
          </div>
          <button className="close-btn" aria-label="Close" onClick={onClose}>
            <span />
            <span />
          </button>
        </div>

        {message && (
          <div className={`modal-banner ${message.type}`}>
            {message.text}
          </div>
        )}

        <div className="modal-body">
          <label className="field-label" htmlFor="model-delivery-email">Client email</label>
          <div className="field-row">
            <input
              id="model-delivery-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="client@email.com"
              autoComplete="off"
            />
            <button
              type="button"
              className="secondary"
              onClick={handleFetchProjects}
              disabled={fetchingProjects}
            >
              {fetchingProjects ? 'Loading…' : 'Find projects'}
            </button>
          </div>

          <label className="field-label" htmlFor="model-delivery-project">Project</label>
          <div className="field-row select-row">
            <select
              id="model-delivery-project"
              value={selectedProjectId}
              onChange={(event) => setSelectedProjectId(event.target.value)}
              disabled={projects.length === 0 || fetchingProjects}
            >
              {projects.length === 0 && <option value="">No projects loaded yet</option>}
              {projects.map(project => (
                <option key={project.projectId} value={project.projectId}>
                  {projectLabel(project)}
                </option>
              ))}
            </select>
          </div>

          <label className="field-label" htmlFor="model-delivery-link">3D model link</label>
          <input
            id="model-delivery-link"
            type="url"
            value={link}
            onChange={(event) => setLink(event.target.value)}
            placeholder="https://…"
            autoComplete="off"
          />
          <p className="field-hint">Paste the final hosted link from the ML pipeline or your storage provider.</p>

          <div className="preview-block">
            <span className="preview-label">Client view preview</span>
            <div className="link-pill">
              <span className="pill-link" title={deliveryPreviewText}>{deliveryPreviewText}</span>
              <span className="pill-copy">Copy</span>
            </div>
            <p className="preview-meta">The client will see this link highlighted inside their project modal and receive an email notification.</p>
          </div>

          {selectedProject?.delivery && (
            <div className="previous-delivery">
              <h4>Previous delivery</h4>
              <p>
                Sent link to {selectedProject.delivery.link} on{' '}
                {selectedProject.delivery.deliveredAt
                  ? new Date(selectedProject.delivery.deliveredAt * 1000).toLocaleString()
                  : 'an earlier date'}
              </p>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button
            type="button"
            className="primary"
            onClick={handleSendDelivery}
            disabled={sendingDelivery || !selectedProjectId || !email.trim() || !link.trim()}
          >
            {sendingDelivery ? 'Sending…' : 'Send to client'}
          </button>
        </div>
      </div>

      <style jsx>{`
        .model-delivery-overlay {
          position: fixed;
          inset: 0;
          background: rgba(4, 6, 14, 0.72);
          backdrop-filter: blur(16px);
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px;
          z-index: 1200;
        }
        .model-delivery-panel {
          width: min(640px, 100%);
          background: rgba(15, 19, 32, 0.92);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 24px;
          padding: 32px;
          color: #fff;
          box-shadow: 0 24px 48px rgba(0, 0, 0, 0.35);
        }
        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 16px;
        }
        .modal-header h2 {
          margin: 0;
          font-size: 1.5rem;
        }
        .modal-subtitle {
          margin: 8px 0 0 0;
          color: rgba(255, 255, 255, 0.68);
          font-size: 0.95rem;
        }
        .close-btn {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.18);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          position: relative;
        }
        .close-btn span {
          position: absolute;
          width: 16px;
          height: 2px;
          background: #fff;
          border-radius: 1px;
        }
        .close-btn span:first-of-type {
          transform: rotate(45deg);
        }
        .close-btn span:last-of-type {
          transform: rotate(-45deg);
        }
        .close-btn:hover {
          background: rgba(255, 255, 255, 0.14);
        }
        .modal-banner {
          margin: 24px 0 0 0;
          padding: 12px 16px;
          border-radius: 12px;
          font-size: 0.95rem;
        }
        .modal-banner.success {
          background: rgba(34, 197, 94, 0.16);
          border: 1px solid rgba(34, 197, 94, 0.35);
          color: #bbf7d0;
        }
        .modal-banner.error {
          background: rgba(239, 68, 68, 0.18);
          border: 1px solid rgba(239, 68, 68, 0.32);
          color: #fecaca;
        }
        .modal-body {
          margin-top: 28px;
          display: flex;
          flex-direction: column;
          gap: 18px;
        }
        .field-label {
          font-size: 0.85rem;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          color: rgba(255, 255, 255, 0.64);
        }
        .field-row {
          display: flex;
          gap: 12px;
          align-items: center;
        }
        input, select {
          flex: 1;
          border-radius: 18px;
          border: 1px solid rgba(255, 255, 255, 0.18);
          background: rgba(12, 16, 28, 0.65);
          padding: 12px 18px;
          color: #fff;
          font-size: 1rem;
        }
        input::placeholder {
          color: rgba(255, 255, 255, 0.38);
        }
        select:disabled {
          color: rgba(255, 255, 255, 0.45);
        }
        button.primary, button.secondary {
          border-radius: 999px;
          padding: 12px 24px;
          font-weight: 600;
          cursor: pointer;
          border: none;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        button.primary {
          background: #ffffff;
          color: #05070f;
        }
        button.secondary {
          background: rgba(255, 255, 255, 0.1);
          color: #ffffff;
          border: 1px solid rgba(255, 255, 255, 0.25);
        }
        button.primary:disabled,
        button.secondary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          transform: none;
          box-shadow: none;
        }
        button.primary:not(:disabled):hover {
          transform: translateY(-1px);
          box-shadow: 0 12px 32px rgba(255, 255, 255, 0.22);
        }
        button.secondary:not(:disabled):hover {
          transform: translateY(-1px);
          box-shadow: 0 12px 32px rgba(59, 130, 246, 0.25);
        }
        .field-row.select-row select {
          width: 100%;
        }
        .field-hint {
          margin: -12px 0 0 0;
          font-size: 0.85rem;
          color: rgba(255, 255, 255, 0.5);
        }
        .preview-block {
          margin-top: 8px;
          padding: 18px;
          border-radius: 16px;
          background: rgba(15, 20, 34, 0.8);
          border: 1px solid rgba(255, 255, 255, 0.12);
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .preview-label {
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          color: rgba(255, 255, 255, 0.5);
        }
        .link-pill {
          display: inline-flex;
          align-items: center;
          gap: 12px;
          border-radius: 999px;
          border: 1px solid rgba(255, 255, 255, 0.22);
          background: rgba(255, 255, 255, 0.08);
          padding: 10px 18px;
          max-width: 100%;
        }
        .pill-link {
          max-width: calc(100% - 56px);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-weight: 500;
        }
        .pill-copy {
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          color: rgba(255, 255, 255, 0.6);
        }
        .preview-meta {
          margin: 0;
          font-size: 0.85rem;
          color: rgba(255, 255, 255, 0.55);
        }
        .previous-delivery {
          margin-top: 4px;
          padding: 16px;
          border-radius: 12px;
          background: rgba(34, 197, 94, 0.1);
          border: 1px solid rgba(34, 197, 94, 0.25);
        }
        .previous-delivery h4 {
          margin: 0 0 6px 0;
          font-size: 0.95rem;
        }
        .previous-delivery p {
          margin: 0;
          color: rgba(203, 253, 222, 0.9);
          font-size: 0.9rem;
        }
        .modal-footer {
          margin-top: 28px;
          display: flex;
          justify-content: flex-end;
        }
        @media (max-width: 640px) {
          .model-delivery-panel {
            padding: 24px;
            border-radius: 18px;
          }
          .field-row {
            flex-direction: column;
            align-items: stretch;
          }
          button.secondary {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}
