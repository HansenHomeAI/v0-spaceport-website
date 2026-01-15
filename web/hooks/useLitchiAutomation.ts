import { useCallback, useEffect, useMemo, useState } from 'react';
import { Auth } from 'aws-amplify';
import { API_CONFIG, buildApiUrl } from '../app/api-config';

export type LitchiStatus = {
  status: string;
  connected: boolean;
  lastUsed?: string;
  updatedAt?: string;
  message?: string;
  progress?: {
    current?: number;
    total?: number;
    label?: string;
  };
  logs?: string[];
  needsTwoFactor?: boolean;
};

export type LitchiMissionPayload = {
  name: string;
  csv: string;
};

type UseLitchiAutomationOptions = {
  pollIntervalMs?: number;
};

const DEFAULT_POLL_INTERVAL_MS = 15000;

async function authHeaders(): Promise<HeadersInit> {
  const session = await Auth.currentSession();
  const token = session.getIdToken().getJwtToken();
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

export function useLitchiAutomation(options: UseLitchiAutomationOptions = {}) {
  const [status, setStatus] = useState<LitchiStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connectMessage, setConnectMessage] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const apiConfigured = useMemo(() => Boolean(API_CONFIG.LITCHI_API_URL), []);
  const pollIntervalMs = options.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS;

  const refreshStatus = useCallback(async () => {
    if (!apiConfigured) return;
    try {
      setError(null);
      const response = await fetch(buildApiUrl.litchi.status(), {
        headers: await authHeaders(),
      });
      if (!response.ok) {
        throw new Error(`Status request failed (${response.status})`);
      }
      const data = await response.json();
      setStatus(data);
    } catch (fetchError: any) {
      setError(fetchError?.message || 'Unable to load Litchi status');
    }
  }, [apiConfigured]);

  useEffect(() => {
    refreshStatus();
    if (!apiConfigured) return;
    const interval = setInterval(refreshStatus, pollIntervalMs);
    return () => clearInterval(interval);
  }, [apiConfigured, pollIntervalMs, refreshStatus]);

  const connect = useCallback(async (email: string, password: string, code?: string) => {
    if (!apiConfigured) return null;
    if (!email || !password) {
      setConnectMessage('Enter your Litchi email and password.');
      return null;
    }

    try {
      setIsConnecting(true);
      setConnectMessage(null);
      setError(null);
      const response = await fetch(buildApiUrl.litchi.connect(), {
        method: 'POST',
        headers: await authHeaders(),
        body: JSON.stringify({
          username: email,
          password,
          twoFactorCode: code || undefined,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || 'Connect failed');
      }
      setStatus(data);
      setConnectMessage(data?.message || 'Connection updated');
      return data as LitchiStatus;
    } catch (connectError: any) {
      setConnectMessage(connectError?.message || 'Connect failed');
      setError(connectError?.message || 'Connect failed');
      return null;
    } finally {
      setIsConnecting(false);
      refreshStatus();
    }
  }, [apiConfigured, refreshStatus]);

  const testConnection = useCallback(async () => {
    if (!apiConfigured) return;
    try {
      setIsTesting(true);
      setError(null);
      const response = await fetch(buildApiUrl.litchi.testConnection(), {
        method: 'POST',
        headers: await authHeaders(),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || 'Test failed');
      }
      setStatus(data);
    } catch (testError: any) {
      setError(testError?.message || 'Test failed');
    } finally {
      setIsTesting(false);
      refreshStatus();
    }
  }, [apiConfigured, refreshStatus]);

  const uploadMissions = useCallback(async (missions: LitchiMissionPayload[]) => {
    if (!apiConfigured) return null;
    if (!missions.length) {
      setError('No missions to upload.');
      return null;
    }

    try {
      setIsUploading(true);
      setError(null);
      const response = await fetch(buildApiUrl.litchi.upload(), {
        method: 'POST',
        headers: await authHeaders(),
        body: JSON.stringify({ missions }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || 'Upload failed');
      }
      return data;
    } catch (uploadError: any) {
      setError(uploadError?.message || 'Upload failed');
      return null;
    } finally {
      setIsUploading(false);
      refreshStatus();
    }
  }, [apiConfigured, refreshStatus]);

  const connected = Boolean(status?.connected || status?.status === 'active');
  const progress = status?.progress ?? null;
  const logs = status?.logs ?? [];

  return {
    apiConfigured,
    status,
    connected,
    isConnecting,
    isTesting,
    isUploading,
    progress,
    logs,
    error,
    connectMessage,
    refreshStatus,
    connect,
    testConnection,
    uploadMissions,
  };
}
