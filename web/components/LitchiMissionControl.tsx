'use client';

import { useCallback, useMemo, useState } from 'react';
import { useLitchiAutomation, type LitchiMissionPayload } from '../hooks/useLitchiAutomation';

const STATUS_LABELS: Record<string, string> = {
  not_connected: 'Not connected',
  connecting: 'Connecting',
  active: 'Connected',
  pending_2fa: 'Needs 2FA',
  expired: 'Expired',
  uploading: 'Uploading',
  testing: 'Testing connection',
  rate_limited: 'Rate limited',
  error: 'Error',
};

type LitchiMissionControlProps = {
  batteryCount?: number;
  buildMissions?: (batteryIndexes: number[]) => Promise<LitchiMissionPayload[]>;
};

export default function LitchiMissionControl({
  batteryCount = 0,
  buildMissions,
}: LitchiMissionControlProps): JSX.Element {
  const [connectOpen, setConnectOpen] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [missionName, setMissionName] = useState('');
  const [missionFile, setMissionFile] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [selectedBatteries, setSelectedBatteries] = useState<Set<number>>(new Set<number>());
  const [prepProgress, setPrepProgress] = useState<{ current: number; total: number } | null>(null);
  const [showAllLogs, setShowAllLogs] = useState(false);
  const [localLogs, setLocalLogs] = useState<string[]>([]);

  const {
    apiConfigured,
    status,
    error,
    connectMessage,
    isConnecting,
    isTesting,
    isUploading,
    connect,
    testConnection,
    uploadMissions,
  } = useLitchiAutomation();

  const appendLocalLog = useCallback((message: string) => {
    setLocalLogs((prev) => [...prev, `[${new Date().toISOString()}] ${message}`].slice(-50));
  }, []);

  const handleConnect = useCallback(async (event: React.FormEvent) => {
    event.preventDefault();
    const result = await connect(username, password, twoFactorCode || undefined);
    if (result?.status === 'active') {
      setConnectOpen(false);
    }
  }, [connect, password, twoFactorCode, username]);

  const toggleBatterySelection = useCallback((batteryIndex: number) => {
    setSelectedBatteries((prev) => {
      const next = new Set(prev);
      if (next.has(batteryIndex)) {
        next.delete(batteryIndex);
      } else {
        next.add(batteryIndex);
      }
      return next;
    });
  }, []);

  const selectAllBatteries = useCallback(() => {
    if (!batteryCount) return;
    setSelectedBatteries(new Set<number>(Array.from({ length: batteryCount }, (_, index) => index + 1)));
  }, [batteryCount]);

  const clearBatterySelection = useCallback(() => {
    setSelectedBatteries(new Set<number>());
  }, []);

  const handleSendGeneratedMissions = useCallback(async () => {
    if (!buildMissions) return;

    const batteryIndexes: number[] = [];
    selectedBatteries.forEach((batteryIndex: number) => {
      batteryIndexes.push(batteryIndex);
    });
    batteryIndexes.sort((a, b) => a - b);
    if (batteryIndexes.length === 0) {
      setLocalError('Select at least one battery to send.');
      appendLocalLog('Select at least one battery before sending.');
      return;
    }

    try {
      setLocalError(null);
      setPrepProgress({ current: 0, total: batteryIndexes.length });
      appendLocalLog(`Preparing ${batteryIndexes.length} battery missions for Litchi.`);
      const missions = await buildMissions(batteryIndexes);
      setPrepProgress({ current: batteryIndexes.length, total: batteryIndexes.length });
      appendLocalLog(`Queueing ${missions.length} mission ${missions.length === 1 ? 'upload' : 'uploads'}.`);
      const result = await uploadMissions(missions);
      if (!result) {
        setLocalError('Upload failed');
        appendLocalLog('Upload request failed. Check your connection and try again.');
        return;
      }
      appendLocalLog('Upload queued. You can close this window while it completes.');
    } catch (sendError: any) {
      const message = sendError?.message || 'Unable to prepare Litchi missions';
      setLocalError(message);
      appendLocalLog(`Upload failed: ${message}`);
    } finally {
      setPrepProgress(null);
    }
  }, [appendLocalLog, buildMissions, selectedBatteries, uploadMissions]);

  const handleUpload = useCallback(async (event: React.FormEvent) => {
    event.preventDefault();
    if (!missionFile) {
      setLocalError('Select a CSV mission file to upload.');
      return;
    }

    setLocalError(null);
    const csvText = await missionFile.text();
    const result = await uploadMissions([
      {
        name: missionName || missionFile.name.replace(/\.csv$/i, ''),
        csv: csvText,
      },
    ]);
    if (!result) {
      setLocalError('Upload failed');
    }
  }, [missionFile, missionName, uploadMissions]);

  const statusLabel = status ? (STATUS_LABELS[status.status] || status.status) : 'Unknown';
  const statusError = localError || error;
  const emailUnverified = /email is not verified/i.test(`${status?.message ?? ''} ${statusError ?? ''}`.trim());
  const emailUnverifiedMessage = 'Verify your Litchi email to enable mission saving. Check your inbox (and spam) for the verification link.';
  const logs = useMemo(() => [...(status?.logs || []), ...localLogs].slice(-50), [localLogs, status?.logs]);
  const visibleLogs = showAllLogs ? logs : logs.slice(-5);
  const selectedCount = selectedBatteries.size;
  const uploadIndicator = status?.progress?.current && status?.progress?.total
    ? `Uploading ${status.progress.current}/${status.progress.total}...`
    : prepProgress
      ? `Preparing ${prepProgress.current}/${prepProgress.total}...`
      : null;

  if (!apiConfigured) {
    return (
      <div className="litchi-card">
        <h4>Litchi Mission Control</h4>
        <p className="litchi-muted">Litchi automation API is not configured for this environment.</p>
      </div>
    );
  }

  return (
    <div className="litchi-card">
      <div className="litchi-card-header">
        <div>
          <h4>Litchi Mission Control</h4>
          <p className="litchi-muted">Uploads run at a safe, human pace to protect your account.</p>
        </div>
        <span className={`litchi-status-pill litchi-status-${status?.status || 'unknown'}`}>{statusLabel}</span>
      </div>

      {status?.message && <p className="litchi-status-message">{status.message}</p>}
      {emailUnverified && <p className="litchi-error" role="status">{emailUnverifiedMessage}</p>}
      {statusError && <p className="litchi-error" role="status">{statusError}</p>}

      <div className="litchi-actions">
        <button className="litchi-primary" onClick={() => setConnectOpen(true)} disabled={isConnecting}>
          {status?.needsTwoFactor ? 'Enter 2FA Code' : 'Connect Litchi Account'}
        </button>
        <button className="litchi-secondary" onClick={testConnection} disabled={isTesting}>
          {isTesting ? 'Testing...' : 'Test Connection'}
        </button>
      </div>

      {buildMissions && batteryCount > 0 && (
        <div className="litchi-selection">
          <div className="litchi-selection-header">
            <span className="litchi-muted">{selectedCount}/{batteryCount} batteries selected</span>
            <div className="litchi-actions">
              <button type="button" className="litchi-secondary" onClick={selectAllBatteries}>
                Select all
              </button>
              <button type="button" className="litchi-secondary" onClick={clearBatterySelection}>
                Clear
              </button>
            </div>
          </div>
          <div className="litchi-select-grid">
            {Array.from({ length: batteryCount }, (_, index) => {
              const batteryIndex = index + 1;
              const selected = selectedBatteries.has(batteryIndex);
              return (
                <button
                  key={batteryIndex}
                  type="button"
                  className={`litchi-select-btn${selected ? ' selected' : ''}`}
                  onClick={() => toggleBatterySelection(batteryIndex)}
                  aria-pressed={selected}
                >
                  Battery {batteryIndex}
                </button>
              );
            })}
          </div>
          <button
            type="button"
            className="litchi-primary"
            onClick={handleSendGeneratedMissions}
            disabled={isUploading || selectedCount === 0}
          >
            {isUploading ? 'Queueing upload...' : 'Send Selected Batteries'}
          </button>
        </div>
      )}

      {uploadIndicator && <p className="litchi-muted">{uploadIndicator}</p>}

      <form className="litchi-upload" onSubmit={handleUpload}>
        <div className="litchi-field">
          <label htmlFor="litchi-mission-name">Mission name</label>
          <input
            id="litchi-mission-name"
            type="text"
            value={missionName}
            onChange={(event) => setMissionName(event.target.value)}
            placeholder="Edgewood-1"
          />
        </div>
        <div className="litchi-field">
          <label htmlFor="litchi-mission-file">Mission CSV</label>
          <input
            id="litchi-mission-file"
            type="file"
            accept=".csv"
            onChange={(event) => setMissionFile(event.target.files?.[0] || null)}
          />
        </div>
        <button className="litchi-primary" type="submit" disabled={isUploading}>
          {isUploading ? 'Queueing upload...' : 'Upload Mission'}
        </button>
      </form>

      <div className="litchi-log-panel" aria-live="polite">
        <h5>Activity</h5>
        <div className="litchi-logs">
          {visibleLogs.length === 0 && <span className="litchi-muted">No activity yet.</span>}
          {visibleLogs.map((entry, index) => (
            <div key={`${entry}-${index}`} className="litchi-log-entry">
              {entry}
            </div>
          ))}
        </div>
        {logs.length > 5 && (
          <button type="button" className="litchi-secondary" onClick={() => setShowAllLogs((prev) => !prev)}>
            {showAllLogs ? 'Show recent activity' : 'Show full activity'}
          </button>
        )}
      </div>

      {connectOpen && (
        <div className="litchi-modal-overlay" role="dialog" aria-modal="true">
          <div className="litchi-modal">
            <div className="litchi-modal-header">
              <h3>Connect Litchi Account</h3>
              <button className="litchi-close" onClick={() => setConnectOpen(false)} aria-label="Close">
                ×
              </button>
            </div>
            <form className="litchi-form" onSubmit={handleConnect}>
              <label htmlFor="litchi-email">Email</label>
              <input
                id="litchi-email"
                type="email"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="you@example.com"
              />
              <label htmlFor="litchi-password">Password</label>
              <input
                id="litchi-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              {(status?.needsTwoFactor || connectMessage === 'Two-factor code required') && (
                <>
                  <label htmlFor="litchi-2fa">Two-factor code</label>
                  <input
                    id="litchi-2fa"
                    type="text"
                    value={twoFactorCode}
                    onChange={(event) => setTwoFactorCode(event.target.value)}
                    placeholder="123456"
                  />
                </>
              )}
              {connectMessage && <p className="litchi-muted" role="status">{connectMessage}</p>}
              <div className="litchi-modal-actions">
                <button type="button" className="litchi-secondary" onClick={() => setConnectOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="litchi-primary" disabled={isConnecting}>
                  {isConnecting ? 'Connecting...' : 'Connect'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
