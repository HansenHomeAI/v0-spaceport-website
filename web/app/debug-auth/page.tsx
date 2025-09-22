'use client';

import React, { useState } from 'react';
import { configureAmplify, isAuthAvailable } from '../amplifyClient';

export default function DebugAuthPage(): JSX.Element {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const testAuthFlow = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // Configure Amplify first
      const configured = configureAmplify();
      if (!configured) {
        throw new Error('Amplify configuration failed - check environment variables');
      }

      const response = await fetch('/api/debug-auth', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
          action: 'test-invite-flow'
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || 'Test failed');
        setResult(data);
      } else {
        setResult(data);
      }
    } catch (err: any) {
      setError(err.message || 'Unexpected error');
      setResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const checkAmplifyConfig = () => {
    const configured = configureAmplify();
    setResult({
      amplifyConfigured: configured,
      authAvailable: isAuthAvailable(),
      environment: {
        userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID ? 'Set' : 'Not set',
        userPoolClientId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_CLIENT_ID ? 'Set' : 'Not set',
        region: process.env.NEXT_PUBLIC_COGNITO_REGION || 'Not set'
      }
    });
  };

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Authentication Debug Tool</h1>

      <div style={{ marginBottom: '24px' }}>
        <h2>Configuration Check</h2>
        <button
          onClick={checkAmplifyConfig}
          style={{
            padding: '8px 16px',
            background: '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Check Amplify Configuration
        </button>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <h2>Test Authentication Flow</h2>
        <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email address"
            style={{
              padding: '8px',
              border: '1px solid #ccc',
              borderRadius: '4px',
              flex: 1
            }}
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            style={{
              padding: '8px',
              border: '1px solid #ccc',
              borderRadius: '4px',
              flex: 1
            }}
          />
          <button
            onClick={testAuthFlow}
            disabled={loading || !email || !password}
            style={{
              padding: '8px 16px',
              background: loading ? '#ccc' : '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? 'Testing...' : 'Test Auth Flow'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '16px',
          background: '#ffebee',
          border: '1px solid #f44336',
          borderRadius: '4px',
          marginBottom: '16px'
        }}>
          <h3 style={{ color: '#d32f2f', margin: '0 0 8px 0' }}>Error</h3>
          <p style={{ margin: 0 }}>{error}</p>
        </div>
      )}

      {result && (
        <div style={{
          padding: '16px',
          background: result.success ? '#e8f5e8' : '#fff3e0',
          border: `1px solid ${result.success ? '#4caf50' : '#ff9800'}`,
          borderRadius: '4px'
        }}>
          <h3 style={{ margin: '0 0 8px 0' }}>
            {result.success ? '✅ Success' : '⚠️ Result'}
          </h3>
          <pre style={{
            background: '#f5f5f5',
            padding: '8px',
            borderRadius: '4px',
            overflow: 'auto',
            fontSize: '12px'
          }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}

      <div style={{ marginTop: '24px', padding: '16px', background: '#e3f2fd', borderRadius: '4px' }}>
        <h3>Instructions</h3>
        <ol>
          <li>First, click "Check Amplify Configuration" to verify your setup</li>
          <li>Enter the email and temporary password from an invitation</li>
          <li>Click "Test Auth Flow" to simulate the authentication process</li>
          <li>Review the results to diagnose any issues</li>
        </ol>
      </div>
    </div>
  );
}