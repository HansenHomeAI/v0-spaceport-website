'use client';

import { useCallback, useEffect, useState } from 'react';
import { Auth } from 'aws-amplify';

import { buildApiUrl } from '../api-config';
import { trackEvent, AnalyticsEvents } from '../../lib/analytics';

export type ModelDeliveryClient = {
  user_id: string;
  email: string;
  name?: string;
  preferred_username?: string;
  status?: string;
};

export type ModelDeliveryProject = Record<string, any> & {
  userSub: string;
  projectId: string;
  title?: string;
  status?: string;
};

export type ResolveClientResponse = {
  client: ModelDeliveryClient;
  projects: ModelDeliveryProject[];
};

export type PublishViewerResponse = {
  url: string;
  slug: string;
};

type PermissionState = {
  loading: boolean;
  hasPermission: boolean;
  error: string | null;
  apiConfigured: boolean;
};

async function authorizedFetch(input: RequestInfo, init: RequestInit = {}): Promise<Response> {
  const session = await Auth.currentSession();
  const idToken = session.getIdToken().getJwtToken();

  const headers = new Headers(init.headers || {});
  headers.set('Authorization', `Bearer ${idToken}`);
  headers.set('Content-Type', 'application/json');

  return fetch(input, {
    ...init,
    headers,
  });
}

async function getIdToken(): Promise<string> {
  const session = await Auth.currentSession();
  return session.getIdToken().getJwtToken();
}

export function useModelDeliveryAdmin() {
  const computeEndpoints = useCallback(() => {
    const configuredBase = buildApiUrl.modelDelivery.base();

    let base = configuredBase;
    if (!base && typeof window !== 'undefined') {
      const host = window.location.hostname;
      const isProductionHost = host.endsWith('spcprt.com');
      base = isProductionHost
        ? 'https://rimocf046k.execute-api.us-west-2.amazonaws.com/prod'
        : 'https://tbzxbstibh.execute-api.us-west-2.amazonaws.com/prod';
    }

    if (typeof window !== 'undefined') {
      console.log('[model-delivery] compute endpoints base', base);
    }

    if (!base) {
      return {
        check: '',
        resolve: '',
        send: '',
      } as const;
    }

    return {
      check: `${base}/admin/model-delivery/check-permission`,
      resolve: `${base}/admin/model-delivery/resolve-client`,
      send: `${base}/admin/model-delivery/send`,
    } as const;
  }, []);

  const [endpoints, setEndpoints] = useState(() => computeEndpoints());

  const [state, setState] = useState<PermissionState>({
    loading: true,
    hasPermission: false,
    error: null,
    apiConfigured: Boolean(endpoints.check),
  });

  useEffect(() => {
    if (!endpoints.check) {
      const next = computeEndpoints();
      if (next.check) {
        setEndpoints(next);
        setState(prev => ({ ...prev, apiConfigured: true }));
      }
    }
  }, [computeEndpoints, endpoints.check]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      console.log('[model-delivery] endpoints', endpoints);
    }
  }, [endpoints]);

  const checkPermission = useCallback(async () => {
    if (!endpoints.check) {
      setState({ loading: false, hasPermission: false, error: 'Model delivery API not configured', apiConfigured: false });
      return { hasPermission: false };
    }

    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      const response = await authorizedFetch(endpoints.check, { method: 'GET' });
      if (!response.ok) {
        if (response.status === 403) {
          setState(prev => ({ ...prev, loading: false, hasPermission: false }));
          return { hasPermission: false };
        }
        throw new Error(`Permission check failed (${response.status})`);
      }

      const data = await response.json();
      const allowed = Boolean(data?.has_model_delivery_permission);
      setState(prev => ({ ...prev, loading: false, hasPermission: allowed }));
      return { hasPermission: allowed };
    } catch (error: any) {
      const message = error?.message || 'Failed to verify permissions';
      const benignAuthError = /not authenticated|no current user/i.test(message);
      setState(prev => ({
        ...prev,
        loading: false,
        hasPermission: false,
        error: benignAuthError ? null : message,
      }));
      return { hasPermission: false, error };
    }
  }, [endpoints.check]);

  const resolveClient = useCallback(async (email: string): Promise<ResolveClientResponse> => {
    if (!endpoints.resolve) {
      throw new Error('Model delivery API is not configured');
    }

    const response = await authorizedFetch(endpoints.resolve, {
      method: 'POST',
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || `Failed to load client (${response.status})`);
    }

    const data = await response.json();
    return data as ResolveClientResponse;
  }, [endpoints.resolve]);

  const sendDelivery = useCallback(async (payload: { clientEmail: string; projectId: string; modelLink: string; projectTitle?: string; viewerSlug?: string; viewerTitle?: string; }) => {
    if (!endpoints.send) {
      throw new Error('Model delivery API is not configured');
    }

    try {
      const response = await authorizedFetch(endpoints.send, {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        trackEvent(AnalyticsEvents.MODEL_LINK_SEND_FAILED, {
          project_id: payload.projectId,
          client_email: payload.clientEmail,
          status: response.status,
        });
        throw new Error(data.error || `Failed to send model link (${response.status})`);
      }

      trackEvent(AnalyticsEvents.MODEL_LINK_SENT, {
        project_id: payload.projectId,
        client_email: payload.clientEmail,
      });

      return data;
    } catch (error) {
      throw error;
    }
  }, [endpoints.send]);

  const publishViewer = useCallback(async (payload: { title: string; file: File; }): Promise<PublishViewerResponse> => {
    const publishUrl = buildApiUrl.spacesViewer.publish();
    if (!publishUrl) {
      throw new Error('Spaces viewer is not configured');
    }

    const token = await getIdToken();
    const formData = new FormData();
    formData.append('title', payload.title);
    formData.append('file', payload.file);

    const response = await fetch(publishUrl, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || `Failed to publish viewer (${response.status})`);
    }

    return data as PublishViewerResponse;
  }, []);

  useEffect(() => {
    checkPermission();
  }, [checkPermission]);

  return {
    ...state,
    checkPermission,
    resolveClient,
    sendDelivery,
    publishViewer,
  };
}
