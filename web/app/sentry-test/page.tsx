'use client';

import { useEffect } from 'react';
import * as Sentry from '@sentry/nextjs';

export default function SentryTestPage() {
  useEffect(() => {
    // Test Sentry initialization
    console.log('Sentry DSN:', process.env.NEXT_PUBLIC_SENTRY_DSN);
    console.log('Sentry loaded:', typeof Sentry);
    
    // Test error capture
    try {
      throw new Error('Test error from Sentry test page');
    } catch (error) {
      Sentry.captureException(error);
      console.log('Error captured by Sentry');
    }
  }, []);

  const triggerError = () => {
    throw new Error('Manual error trigger');
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>Sentry Test Page</h1>
      <p>Check the console for Sentry initialization logs.</p>
      <button 
        onClick={triggerError}
        style={{
          padding: '10px 20px',
          backgroundColor: '#ff4444',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        Trigger Error
      </button>
      <p>After clicking the button, check your Sentry dashboard for the error.</p>
    </div>
  );
}
