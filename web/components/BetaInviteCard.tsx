'use client';
import React, { useState, useEffect } from 'react';
import { Auth } from 'aws-amplify';
import { buildApiUrl } from '../app/api-config';

interface BetaInviteCardProps {
  user: any;
}

export default function BetaInviteCard({ user }: BetaInviteCardProps): JSX.Element | null {
  const [canInvite, setCanInvite] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [inviteEmail, setInviteEmail] = useState<string>('');
  const [inviteName, setInviteName] = useState<string>('');
  const [sending, setSending] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    checkInvitePermission();
  }, []);

  const checkInvitePermission = async () => {
    try {
      setLoading(true);
      const session = await Auth.currentSession();
      const idToken = session.getIdToken().getJwtToken();
      
      const response = await fetch(buildApiUrl.betaInvite.checkPermission(), {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setCanInvite(data.canInvite || false);
      } else {
        setCanInvite(false);
      }
    } catch (error) {
      console.error('Error checking invite permission:', error);
      setCanInvite(false);
    } finally {
      setLoading(false);
    }
  };

  const sendInvitation = async () => {
    if (!inviteEmail.trim()) {
      setMessage({ type: 'error', text: 'Email is required' });
      return;
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(inviteEmail.trim())) {
      setMessage({ type: 'error', text: 'Please enter a valid email address' });
      return;
    }

    try {
      setSending(true);
      setMessage(null);
      
      const session = await Auth.currentSession();
      const idToken = session.getIdToken().getJwtToken();
      
      const response = await fetch(buildApiUrl.betaInvite.sendInvitation(), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: inviteEmail.trim(),
          name: inviteName.trim(),
        }),
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        setMessage({ type: 'success', text: `Beta invitation sent to ${inviteEmail}` });
        setInviteEmail('');
        setInviteName('');
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to send invitation' });
      }
    } catch (error) {
      console.error('Error sending invitation:', error);
      setMessage({ type: 'error', text: 'Network error. Please try again.' });
    } finally {
      setSending(false);
    }
  };

  const clearMessage = () => {
    setMessage(null);
  };

  // Don't render if user can't invite or still loading
  if (loading || !canInvite) {
    return null;
  }

  return (
    <div className="project-box beta-invite-card">
      <div className="beta-invite-content">
        <div className="beta-invite-header">
          <h3>Invite Beta Users</h3>
          <p>Send beta access invitations to new users</p>
        </div>
        
        <div className="beta-invite-form">
          <div className="input-group">
            <label htmlFor="invite-email">Email Address *</label>
            <input
              id="invite-email"
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="user@example.com"
              className="beta-invite-input"
              disabled={sending}
            />
          </div>
          
          <div className="input-group">
            <label htmlFor="invite-name">Name (optional)</label>
            <input
              id="invite-name"
              type="text"
              value={inviteName}
              onChange={(e) => setInviteName(e.target.value)}
              placeholder="User's full name"
              className="beta-invite-input"
              disabled={sending}
            />
          </div>
          
          {message && (
            <div className={`beta-invite-message ${message.type}`}>
              <span>{message.text}</span>
              <button 
                className="message-close"
                onClick={clearMessage}
                aria-label="Dismiss message"
              >
                ×
              </button>
            </div>
          )}
          
          <button
            className="beta-invite-button"
            onClick={sendInvitation}
            disabled={sending || !inviteEmail.trim()}
          >
            {sending ? (
              <>
                <span className="loading-spinner"></span>
                Sending...
              </>
            ) : (
              'Send Invitation'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}