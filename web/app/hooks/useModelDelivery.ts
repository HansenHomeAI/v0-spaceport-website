'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Auth } from 'aws-amplify';
import { buildApiUrl } from '../api-config';

export interface DeliveryProject {
  projectId: string;
  title: string;
  status: string;
  progress: number;
  updatedAt?: number;
  delivery?: {
    link: string;
    deliveredAt?: number;
    deliveredByEmail?: string;
    deliveredBySub?: string;
  } | null;
}

interface ModelDeliveryState {
  hasPermission: boolean;
  loading: boolean;
  error: string | null;
  fetchingProjects: boolean;
  sendingDelivery: boolean;
  projects: DeliveryProject[];
}

interface ModelDeliveryActions {
  checkPermission: () => Promise<void>;
  fetchProjects: (email: string) => Promise<{ success: boolean; projects?: DeliveryProject[]; message?: string }>;
  sendDelivery: (params: { email: string; projectId: string; link: string }) => Promise<{ success: boolean; message: string }>;
  clearError: () => void;
}

function isApiConfigured(url: string | undefined): boolean {
  if (!url) return false;
  return /^https?:\/\//i.test(url);
}

export function useModelDelivery(): ModelDeliveryState & ModelDeliveryActions {
  const [state, setState] = useState<ModelDeliveryState>({
    hasPermission: false,
    loading: true,
    error: null,
    fetchingProjects: false,
    sendingDelivery: false,
    projects: [],
  });

  const apiUrls = useMemo(() => ({
    checkPermission: buildApiUrl.modelDelivery.checkPermission(),
    listProjects: buildApiUrl.modelDelivery.listProjects(),
    send: buildApiUrl.modelDelivery.send(),
  }), []);

  const configured = useMemo(() => isApiConfigured(apiUrls.checkPermission), [apiUrls.checkPermission]);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  const checkPermission = useCallback(async () => {
    if (!configured) {
      setState(prev => ({
        ...prev,
        hasPermission: false,
        loading: false,
        error: 'Model delivery API is not configured',
      }));
      return;
    }

    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      const session = await Auth.currentSession();
      const token = session.getIdToken().getJwtToken();

      const res = await fetch(apiUrls.checkPermission, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!res.ok) {
        if (res.status === 403) {
          setState(prev => ({ ...prev, hasPermission: false, loading: false }));
          return;
        }
        throw new Error(`Failed to check permissions (${res.status})`);
      }

      const data = await res.json();
      setState(prev => ({
        ...prev,
        hasPermission: Boolean(data.has_model_delivery_permission),
        loading: false,
        error: null,
      }));
    } catch (error: any) {
      console.error('Model delivery permission check failed:', error);
      setState(prev => ({
        ...prev,
        hasPermission: false,
        loading: false,
        error: error?.message || 'Failed to check permissions',
      }));
    }
  }, [apiUrls.checkPermission, configured]);

  const fetchProjects = useCallback(async (email: string) => {
    if (!configured) {
      const message = 'Model delivery API is not configured';
      setState(prev => ({ ...prev, error: message }));
      return { success: false, message };
    }

    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail) {
      const message = 'Please enter an email address';
      setState(prev => ({ ...prev, error: message }));
      return { success: false, message };
    }

    try {
      setState(prev => ({ ...prev, fetchingProjects: true, error: null }));
      const session = await Auth.currentSession();
      const token = session.getIdToken().getJwtToken();

      const res = await fetch(apiUrls.listProjects, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: normalizedEmail }),
      });

      const data = await res.json();

      if (!res.ok) {
        const message = data?.error || `Unable to load projects (${res.status})`;
        setState(prev => ({ ...prev, error: message, fetchingProjects: false, projects: [] }));
        return { success: false, message };
      }

      const projects = Array.isArray(data?.projects) ? data.projects : [];
      setState(prev => ({ ...prev, projects, fetchingProjects: false }));
      return { success: true, projects };
    } catch (error: any) {
      console.error('Failed to fetch projects for delivery:', error);
      const message = error?.message || 'Failed to load projects';
      setState(prev => ({ ...prev, error: message, fetchingProjects: false }));
      return { success: false, message };
    }
  }, [apiUrls.listProjects, configured]);

  const sendDelivery = useCallback(async ({ email, projectId, link }: { email: string; projectId: string; link: string }) => {
    if (!configured) {
      const message = 'Model delivery API is not configured';
      setState(prev => ({ ...prev, error: message }));
      return { success: false, message };
    }

    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail || !projectId.trim()) {
      const message = 'Email and project are required';
      setState(prev => ({ ...prev, error: message }));
      return { success: false, message };
    }

    try {
      setState(prev => ({ ...prev, sendingDelivery: true, error: null }));
      const session = await Auth.currentSession();
      const token = session.getIdToken().getJwtToken();

      const res = await fetch(apiUrls.send, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: normalizedEmail, projectId: projectId.trim(), link: link.trim() }),
      });

      const data = await res.json();

      if (!res.ok) {
        const message = data?.error || `Failed to deliver model (${res.status})`;
        setState(prev => ({ ...prev, error: message, sendingDelivery: false }));
        return { success: false, message };
      }

      setState(prev => ({ ...prev, sendingDelivery: false }));
      return { success: true, message: 'Model link sent to client' };
    } catch (error: any) {
      console.error('Failed to send model delivery:', error);
      const message = error?.message || 'Failed to send model link';
      setState(prev => ({ ...prev, error: message, sendingDelivery: false }));
      return { success: false, message };
    }
  }, [apiUrls.send, configured]);

  useEffect(() => {
    checkPermission();
  }, [checkPermission]);

  return {
    ...state,
    checkPermission,
    fetchProjects,
    sendDelivery,
    clearError,
  };
}
