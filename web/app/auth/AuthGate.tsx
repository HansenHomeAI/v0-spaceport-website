'use client';
import React, { useEffect, useState } from 'react';
import { configureAmplify, isAuthAvailable } from '../amplifyClient';
import { Auth } from 'aws-amplify';

type AuthGateProps = {
  children: React.ReactNode;
};

type View = 'signin' | 'new_password';

export default function AuthGate({ children }: AuthGateProps): JSX.Element {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [view, setView] = useState<View>('signin');
  const [signInEmail, setSignInEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [name, setName] = useState('');
  const [waitlistEmail, setWaitlistEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const WAITLIST_API = 'https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/waitlist';
  const [waitlistSubmitting, setWaitlistSubmitting] = useState(false);
  const [pendingUser, setPendingUser] = useState<any>(null);
  const [newPassword, setNewPassword] = useState('');
  const [handle, setHandle] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);

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
      const res = await Auth.signIn(signInEmail, password);
      if (res.challengeName === 'NEW_PASSWORD_REQUIRED') {
        setPendingUser(res);
        setView('new_password');
        return;
      }
      const current = await Auth.currentAuthenticatedUser();
      setUser(current);
    } catch (err: any) {
      setError(err?.message || 'Sign in failed');
    }
  };

  // Sign-up and confirm flows are disabled (invite-only)

  const joinWaitlist = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setWaitlistSubmitting(true);
    try {
      const res = await fetch(WAITLIST_API, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ name: name || 'Friend', email: waitlistEmail }),
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
    <section className="section" id="signup" style={{ maxWidth: 900, margin: '0 auto' }}>
      <div className="signup-stack">
        <div className="waitlist-card" style={{ width: '100%', maxWidth: 520 }}>
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
              <input className="waitlist-input" placeholder="Email Address" type="email" value={waitlistEmail} onChange={(e) => setWaitlistEmail(e.target.value)} />
            </div>
            <button type="submit" className="waitlist-submit-btn" disabled={waitlistSubmitting}>
              <span>{waitlistSubmitting ? 'Submitting…' : 'Join Waitlist'}</span>
              <div className="spinner" style={{ display: waitlistSubmitting ? 'inline-block' : 'none', marginLeft: 8 }} />
            </button>
          </form>
        </div>

        <div className="signin-block" style={{ width: '100%', maxWidth: 520 }}>
          <div className="waitlist-card" style={{ width: '100%' }}>
            <div className="waitlist-header">
              <h2>Sign in to create your model</h2>
            </div>
            {view === 'signin' && (
              <form onSubmit={signIn} className="waitlist-form">
                <div className="input-group">
                  <input value={signInEmail} onChange={(e) => setSignInEmail(e.target.value)} type="email" className="waitlist-input" placeholder="Email" required />
                </div>
                <div className="input-group" style={{ position: 'relative' }}>
                  <input value={password} onChange={(e) => setPassword(e.target.value)} type={showPassword ? 'text' : 'password'} className="waitlist-input" placeholder="Password" required />
                  <button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword((v) => !v)} style={{ position: 'absolute', right: 10, top: 10, background: 'transparent', border: 0, color: '#bbb', cursor: 'pointer' }}>
                    {showPassword ? '🙈' : '👁️'}
                  </button>
                </div>
                {error && <p style={{ color: '#ff6b6b' }}>{error}</p>}
                <button className="waitlist-submit-btn" type="submit">
                  <span>Sign in</span>
                </button>
              </form>
            )}
          </div>

          {view === 'new_password' && (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setError(null);
                try {
                  if (!pendingUser) throw new Error('Session expired');
                  const completed = await Auth.completeNewPassword(pendingUser, newPassword, {
                    preferred_username: handle,
                  });
                  const current = await Auth.currentAuthenticatedUser();
                  setUser(current || completed);
                } catch (err: any) {
                  const code = err?.name || err?.code || '';
                  if (code === 'AliasExistsException') {
                    setError('Username is taken. Please choose another.');
                  } else {
                    setError(err?.message || 'Failed to set password/handle');
                  }
                }
              }}
              className="waitlist-form"
            >
              <p>Finish setup by choosing your password and a unique handle.</p>
              <div className="input-group" style={{ position: 'relative' }}>
                <input value={newPassword} onChange={(e) => setNewPassword(e.target.value)} type={showNewPassword ? 'text' : 'password'} required className="waitlist-input" placeholder="New password" />
                <button type="button" aria-label={showNewPassword ? 'Hide password' : 'Show password'} onClick={() => setShowNewPassword((v) => !v)} style={{ position: 'absolute', right: 10, top: 10, background: 'transparent', border: 0, color: '#bbb', cursor: 'pointer' }}>
                  {showNewPassword ? '🙈' : '👁️'}
                </button>
              </div>
              <div className="input-group">
                <input value={handle} onChange={(e) => setHandle(e.target.value)} required className="waitlist-input" placeholder="Handle (e.g. johndoe)" />
              </div>
              {error && <p style={{ color: '#ff6b6b' }}>{error}</p>}
              <button className="waitlist-submit-btn" type="submit">
                <span>Save and sign in</span>
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}


