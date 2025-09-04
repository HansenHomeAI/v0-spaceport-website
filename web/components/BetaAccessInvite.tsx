'use client';
import React, { useState } from 'react';
import { useBetaAccess } from '../app/hooks/useBetaAccess';

interface BetaAccessInviteProps {
  className?: string;
}

export default function BetaAccessInvite({ className = '' }: BetaAccessInviteProps): JSX.Element | null {
  const { hasBetaAccessPermission, loading, sendingInvitation, sendInvitation } = useBetaAccess();
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Don't render anything if user doesn't have permission or still loading
  if (loading || !hasBetaAccessPermission) {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email.trim()) {
      setMessage({ type: 'error', text: 'Please enter an email address' });
      return;
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setMessage({ type: 'error', text: 'Please enter a valid email address' });
      return;
    }

    const result = await sendInvitation(email);
    
    if (result.success) {
      setMessage({ type: 'success', text: result.message });
      setEmail(''); // Clear the input on success
    } else {
      setMessage({ type: 'error', text: result.message });
    }

    // Clear message after 5 seconds
    setTimeout(() => setMessage(null), 5000);
  };

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEmail(e.target.value);
    // Clear any existing message when user starts typing
    if (message) {
      setMessage(null);
    }
  };

  return (
    <div className={`beta-access-invite ${className}`}>
      <div className="beta-access-header">
        <h4>Beta Access Management</h4>
        <p>Invite new users to access Spaceport AI</p>
      </div>
      
      <form onSubmit={handleSubmit} className="beta-access-form">
        <div className="input-group">
          <input
            type="email"
            value={email}
            onChange={handleEmailChange}
            placeholder="Enter email address"
            className="beta-access-input"
            disabled={sendingInvitation}
            required
          />
          <button
            type="submit"
            className={`beta-access-button ${sendingInvitation ? 'loading' : ''}`}
            disabled={sendingInvitation || !email.trim()}
          >
            {sendingInvitation ? (
              <>
                <span className="loading-spinner"></span>
                Sending...
              </>
            ) : (
              'Grant Access'
            )}
          </button>
        </div>
        
        {message && (
          <div className={`beta-access-message ${message.type}`}>
            {message.text}
          </div>
        )}
      </form>
      
      <style jsx>{`
        .beta-access-invite {
          margin-top: 24px;
          padding: 24px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
          backdrop-filter: blur(10px);
        }
        
        .beta-access-header h4 {
          margin: 0 0 8px 0;
          color: #ffffff;
          font-size: 1.125rem;
          font-weight: 600;
        }
        
        .beta-access-header p {
          margin: 0 0 20px 0;
          color: rgba(255, 255, 255, 0.7);
          font-size: 0.875rem;
        }
        
        .beta-access-form {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        
        .input-group {
          display: flex;
          gap: 16px;
          align-items: center;
        }
        
        .beta-access-input {
          flex: 1;
          padding: 16px 20px;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 50px;
          color: #ffffff;
          font-size: 0.875rem;
          transition: all 0.2s ease;
        }
        
        .beta-access-input:focus {
          outline: none;
          border-color: rgba(255, 255, 255, 0.4);
          background: rgba(255, 255, 255, 0.15);
        }
        
        .beta-access-input::placeholder {
          color: rgba(255, 255, 255, 0.5);
        }
        
        .beta-access-input:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        
        .beta-access-button {
          padding: 16px 32px;
          background: #ffffff;
          border: none;
          border-radius: 50px;
          color: #000000;
          font-size: 0.875rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          gap: 8px;
          min-width: 140px;
          justify-content: center;
        }
        
        .beta-access-button:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(255, 255, 255, 0.3);
        }
        
        .beta-access-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }
        
        .beta-access-button.loading {
          pointer-events: none;
        }
        
        .loading-spinner {
          width: 14px;
          height: 14px;
          border: 2px solid rgba(0, 0, 0, 0.3);
          border-top: 2px solid #000000;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        
        .beta-access-message {
          padding: 12px 16px;
          border-radius: 50px;
          font-size: 0.875rem;
          margin-top: 8px;
        }
        
        .beta-access-message.success {
          background: rgba(34, 197, 94, 0.15);
          border: 1px solid rgba(34, 197, 94, 0.3);
          color: #22c55e;
        }
        
        .beta-access-message.error {
          background: rgba(239, 68, 68, 0.15);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #ef4444;
        }
        
        @media (max-width: 768px) {
          .input-group {
            flex-direction: column;
            align-items: stretch;
          }
          
          .beta-access-button {
            min-width: auto;
          }
        }
      `}</style>
    </div>
  );
}