'use client';
import React, { useEffect, useState } from 'react';
import { configureAmplify, isAuthAvailable } from '../amplifyClient';
import { Auth } from 'aws-amplify';

type AuthGateProps = {
  children: React.ReactNode;
};

type View = 'signin' | 'signup' | 'confirm';

export default function AuthGate({ children }: AuthGateProps): JSX.Element {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [view, setView] = useState<View>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const WAITLIST_API = 'https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/waitlist';
  const [waitlistSubmitting, setWaitlistSubmitting] = useState(false);

  useEffect(() => {
    const ok = configureAmplify();
    (async () => {
      try {
        if (ok && isAuthAvailable()) {
          const current = await Auth.currentAuthenticatedUser();
          setUser(current);
        } else {
          setUser(null);
        }
      } catch {
        setUser(null);
      } finally {
        setReady(true);
      }
    })();
  }, []);

  if (!ready) return <div style={{ padding: 24 }}>Loading…</div>;
  if (user) return <>{children}</>;

  const signIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (!isAuthAvailable()) throw new Error('Sign-in temporarily disabled');
      await Auth.signIn(email, password);
      const current = await Auth.currentAuthenticatedUser();
      setUser(current);
    } catch (err: any) {
      setError(err?.message || 'Sign in failed');
    }
  };

  // Disable open sign-up: invite-only flow
  const signUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('Account creation is invite-only. Please use the invite link we send to approved beta users.');
  };

  const confirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await Auth.confirmSignUp(email, code);
      await signIn(e);
    } catch (err: any) {
      setError(err?.message || 'Confirmation failed');
    }
  };

  const joinWaitlist = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setWaitlistSubmitting(true);
    try {
      const res = await fetch(WAITLIST_API, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ name: name || 'Friend', email }),
      });
      if (!res.ok) throw new Error('Failed to join waitlist');
      alert('Thanks! You have been added to the waitlist.');
    } catch (err: any) {
      setError(err?.message || 'Failed to join waitlist');
    } finally {
      setWaitlistSubmitting(false);
    }
  };

  return (
    <section className="section" id="signup" style={{ maxWidth: 720, margin: '0 auto' }}>
      <h1>Sign in to create your model</h1>
      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 320px', minWidth: 320 }}>
          {view === 'signin' && (
            <form onSubmit={signIn} className="waitlist-form" style={{ maxWidth: 520 }}>
              <label>
                Email
                <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required className="waitlist-input" />
              </label>
              <label>
                Password
                <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required className="waitlist-input" />
              </label>
              {error && <p style={{ color: '#ff6b6b' }}>{error}</p>}
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="cta-button" type="submit">Sign in</button>
                <button type="button" className="cta-button2-fixed" onClick={() => { setView('signup'); setError(null); }}>Request access</button>
              </div>
            </form>
          )}

          {view === 'signup' && (
            <form onSubmit={signUp} className="waitlist-form" style={{ maxWidth: 520 }}>
              <label>
                Name
                <input value={name} onChange={(e) => setName(e.target.value)} className="waitlist-input" />
              </label>
              <label>
                Email
                <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required className="waitlist-input" />
              </label>
              <label>
                Password
                <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required className="waitlist-input" />
              </label>
              {error && <p style={{ color: '#ff6b6b' }}>{error}</p>}
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="cta-button" type="submit">Create account (invite only)</button>
                <button type="button" className="cta-button2-fixed" onClick={() => { setView('signin'); setError(null); }}>Back to sign in</button>
              </div>
            </form>
          )}

          {view === 'confirm' && (
            <form onSubmit={confirm} className="waitlist-form" style={{ maxWidth: 520 }}>
              <p>We sent a verification code to your email. Enter it below to verify your account.</p>
              <label>
                Verification code
                <input value={code} onChange={(e) => setCode(e.target.value)} required className="waitlist-input" />
              </label>
              {error && <p style={{ color: '#ff6b6b' }}>{error}</p>}
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="cta-button" type="submit">Verify</button>
                <button type="button" className="cta-button2-fixed" onClick={() => setView('signin')}>Back to sign in</button>
              </div>
            </form>
          )}
        </div>

        <div style={{ flex: '1 1 320px', minWidth: 320 }}>
          <div className="waitlist-card">
            <div className="waitlist-header">
              <img src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport AI" className="waitlist-logo" />
              <h2>New here?</h2>
              <p>Join the waitlist to be among the first to access Spaceport AI.</p>
            </div>
            <form onSubmit={joinWaitlist} className="waitlist-form">
              <div className="input-group">
                <input className="waitlist-input" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="input-group">
                <input className="waitlist-input" placeholder="Email Address" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
              <button type="submit" className="waitlist-submit-btn" disabled={waitlistSubmitting}>
                <span>{waitlistSubmitting ? 'Submitting…' : 'Join Waitlist'}</span>
                <div className="spinner" style={{ display: waitlistSubmitting ? 'inline-block' : 'none', marginLeft: 8 }} />
              </button>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}


