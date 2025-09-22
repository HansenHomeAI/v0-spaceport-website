'use client';
import React, { useCallback, useEffect, useState } from 'react';
import { configureAmplify, isAuthAvailable } from '../amplifyClient';
import { Auth } from 'aws-amplify';

type AuthGateProps = {
  children: React.ReactNode;
  onAuthenticated?: (user: any) => void | Promise<void>;
};

type View = 'signin' | 'new_password' | 'forgot_password' | 'reset_password';

export default function AuthGate({ children, onAuthenticated }: AuthGateProps): JSX.Element {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [view, setView] = useState<View>('signin');
  const [signInEmail, setSignInEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [name, setName] = useState('');
  const [waitlistEmail, setWaitlistEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const WAITLIST_API = process.env.NEXT_PUBLIC_WAITLIST_API_URL;
  const [waitlistSubmitting, setWaitlistSubmitting] = useState(false);
  const [pendingUser, setPendingUser] = useState<any>(null);
  const [newPassword, setNewPassword] = useState('');
  const [handle, setHandle] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  
  // Forgot password states
  const [forgotEmail, setForgotEmail] = useState('');
  const [resetCode, setResetCode] = useState('');
  const [resetPassword, setResetPassword] = useState('');
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const completeSignIn = useCallback(
    (authUser: any) => {
      if (!authUser) return;
      setUser(authUser);
      if (!onAuthenticated) return;

      try {
        const result = onAuthenticated(authUser);
        if (result && typeof (result as Promise<unknown>).then === 'function') {
          (result as Promise<unknown>).catch((callbackError) => {
            console.error('onAuthenticated callback rejected', callbackError);
          });
        }
      } catch (callbackError) {
        console.error('onAuthenticated callback threw an error', callbackError);
      }
    },
    [onAuthenticated]
  );

  const EyeIcon = ({ hidden = false }: { hidden?: boolean }) => (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
      style={{ display: 'block' }}
    >
      {hidden ? (
        <>
          <path d="M3 3l18 18" stroke="#bbb" strokeWidth="2" strokeLinecap="round" />
          <path d="M2 12s4-7 10-7 10 7 10 7c-.54.95-1.2 1.83-1.95 2.62" stroke="#bbb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M14.12 14.12A3 3 0 0 1 9.88 9.88" stroke="#bbb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </>
      ) : (
        <>
          <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12Z" stroke="#bbb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="12" cy="12" r="3" stroke="#bbb" strokeWidth="2" />
        </>
      )}
    </svg>
  );

  useEffect(() => {
    const ok = configureAmplify();
    (async () => {
      try {
        if (ok && isAuthAvailable()) {
          const current = await Auth.currentAuthenticatedUser();
          completeSignIn(current);
        } else {
          setUser(null);
        }
      } catch {
        setUser(null);
      } finally {
        setReady(true);
      }
    })();
  }, [completeSignIn]);

  if (!ready) return <div style={{ padding: 24 }}>Loading…</div>;
  if (user) return <>{children}</>;

  const signIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      if (!isAuthAvailable()) throw new Error('Sign-in temporarily disabled');
      const normalizedEmail = (signInEmail || '').trim().toLowerCase();
      const res = await Auth.signIn(normalizedEmail, password.trim());
      if (res.challengeName === 'NEW_PASSWORD_REQUIRED') {
        setPendingUser(res);
        setView('new_password');
        return;
      }
      const current = await Auth.currentAuthenticatedUser();
      completeSignIn(current);
    } catch (err: any) {
      const raw = (err?.message || '').toString();
      const msg = raw.toLowerCase();
      if (msg.includes('user does not exist') || msg.includes('user not found')) {
        setError('No account found for that email. Check spelling or contact support.');
      } else if (msg.includes('incorrect username or password') || msg.includes('invalid parameter') || msg.includes('not authorized')) {
        setError('Invalid email or password. Remove any extra spaces and try again, or use Forgot Password.');
      } else {
        setError(err?.message || 'Sign in failed');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      if (!isAuthAvailable()) throw new Error('Password reset temporarily disabled');
      await Auth.forgotPassword(forgotEmail);
      setSuccessMessage('Password reset code sent to your email');
      setView('reset_password');
    } catch (err: any) {
      setError(err?.message || 'Failed to send reset code');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      if (!isAuthAvailable()) throw new Error('Password reset temporarily disabled');
      await Auth.forgotPasswordSubmit(forgotEmail, resetCode, resetPassword);
      setSuccessMessage('Password reset successfully! You can now sign in.');
      setView('signin');
      // Clear form data
      setForgotEmail('');
      setResetCode('');
      setResetPassword('');
    } catch (err: any) {
      setError(err?.message || 'Failed to reset password');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setError(null);
    setSuccessMessage(null);
    setForgotEmail('');
    setResetCode('');
    setResetPassword('');
    setView('signin');
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
            
            {/* Sign In View */}
            {view === 'signin' && (
              <form onSubmit={signIn} className="waitlist-form">
                <div className="input-group">
                  <input 
                    value={signInEmail} 
                    onChange={(e) => setSignInEmail(e.target.value)} 
                    type="email" 
                    className="waitlist-input" 
                    placeholder="Email" 
                    required 
                  />
                </div>
                <div className="input-group" style={{ position: 'relative' }}>
                  <input 
                    value={password} 
                    onChange={(e) => setPassword(e.target.value)} 
                    type={showPassword ? 'text' : 'password'} 
                    className="waitlist-input" 
                    placeholder="Password" 
                    required 
                  />
                  <button
                    type="button"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    onClick={() => setShowPassword((v) => !v)}
                    style={{ position: 'absolute', right: 16, top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 0, padding: 0, cursor: 'pointer' }}
                  >
                    <EyeIcon hidden={showPassword} />
                  </button>
                </div>
                {error && <p style={{ color: '#ff6b6b', fontSize: '14px', marginTop: '8px' }}>{error}</p>}
                {successMessage && <p style={{ color: '#4CAF50', fontSize: '14px', marginTop: '8px' }}>{successMessage}</p>}
                <button className="waitlist-submit-btn" type="submit" disabled={isLoading}>
                  <span>{isLoading ? 'Signing in...' : 'Sign in'}</span>
                  {isLoading && <div className="spinner" style={{ display: 'inline-block', marginLeft: 8 }} />}
                </button>
                <div style={{ textAlign: 'center', marginTop: '16px' }}>
                  <button
                    type="button"
                    onClick={() => setView('forgot_password')}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: '#4CAF50',
                      textDecoration: 'underline',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                  >
                    Forgot your password?
                  </button>
                </div>
              </form>
            )}

            {/* Forgot Password View */}
            {view === 'forgot_password' && (
              <form onSubmit={handleForgotPassword} className="waitlist-form">
                <p style={{ marginBottom: '16px', fontSize: '14px', color: '#666' }}>
                  Enter your email address and we'll send you a code to reset your password.
                </p>
                <div className="input-group">
                  <input 
                    value={forgotEmail} 
                    onChange={(e) => setForgotEmail(e.target.value)} 
                    type="email" 
                    className="waitlist-input" 
                    placeholder="Email address" 
                    required 
                  />
                </div>
                {error && <p style={{ color: '#ff6b6b', fontSize: '14px', marginTop: '8px' }}>{error}</p>}
                <button className="waitlist-submit-btn" type="submit" disabled={isLoading}>
                  <span>{isLoading ? 'Sending...' : 'Send reset code'}</span>
                  {isLoading && <div className="spinner" style={{ display: 'inline-block', marginLeft: 8 }} />}
                </button>
                <div style={{ textAlign: 'center', marginTop: '16px' }}>
                  <button
                    type="button"
                    onClick={resetForm}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: '#4CAF50',
                      textDecoration: 'underline',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                  >
                    Back to sign in
                  </button>
                </div>
              </form>
            )}

            {/* Reset Password View */}
            {view === 'reset_password' && (
              <form onSubmit={handleResetPassword} className="waitlist-form">
                <p style={{ marginBottom: '16px', fontSize: '14px', color: '#666' }}>
                  Enter the code from your email and choose a new password.
                </p>
                <div className="input-group">
                  <input 
                    value={resetCode} 
                    onChange={(e) => setResetCode(e.target.value)} 
                    type="text" 
                    className="waitlist-input" 
                    placeholder="Reset code" 
                    required 
                    maxLength={6}
                  />
                </div>
                <div className="input-group" style={{ position: 'relative' }}>
                  <input 
                    value={resetPassword} 
                    onChange={(e) => setResetPassword(e.target.value)} 
                    type={showResetPassword ? 'text' : 'password'} 
                    className="waitlist-input" 
                    placeholder="New password" 
                    required 
                    minLength={8}
                  />
                  <button
                    type="button"
                    aria-label={showResetPassword ? 'Hide password' : 'Show password'}
                    onClick={() => setShowResetPassword((v) => !v)}
                    style={{ position: 'absolute', right: 16, top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 0, padding: 0, cursor: 'pointer' }}
                  >
                    <EyeIcon hidden={showResetPassword} />
                  </button>
                </div>
                {error && <p style={{ color: '#ff6b6b', fontSize: '14px', marginTop: '8px' }}>{error}</p>}
                <button className="waitlist-submit-btn" type="submit" disabled={isLoading}>
                  <span>{isLoading ? 'Resetting...' : 'Reset password'}</span>
                  {isLoading && <div className="spinner" style={{ display: 'inline-block', marginLeft: 8 }} />}
                </button>
                <div style={{ textAlign: 'center', marginTop: '16px' }}>
                  <button
                    type="button"
                    onClick={() => setView('forgot_password')}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: '#4CAF50',
                      textDecoration: 'underline',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                  >
                    Resend code
                  </button>
                </div>
              </form>
            )}
          </div>

          {/* New Password Required View */}
          {view === 'new_password' && (
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setError(null);
                setIsLoading(true);
                try {
                  if (!pendingUser) throw new Error('Session expired');
                  // First attempt: set password and preferred_username if provided (v3 pool supports this)
                  const attrs: any = {};
                  if (handle) attrs.preferred_username = handle;
                  try {
                    const completed = await Auth.completeNewPassword(pendingUser, newPassword, attrs);
                    const current = await Auth.currentAuthenticatedUser();
                    completeSignIn(current || completed);
                  } catch (errInner: any) {
                    const msg = (errInner?.message || '').toLowerCase();
                    const code = (errInner?.name || errInner?.code || '').toString();
                    const isPrefUsernameIssue =
                      code === 'InvalidParameterException' ||
                      msg.includes('preferred_username') ||
                      msg.includes('mutability') ||
                      msg.includes('invalid user attributes');
                    if (isPrefUsernameIssue) {
                      // Fallback for v2 pool where preferred_username is immutable; complete without attributes
                      const completed = await Auth.completeNewPassword(pendingUser, newPassword);
                      const current = await Auth.currentAuthenticatedUser();
                      completeSignIn(current || completed);
                    } else {
                      throw errInner;
                    }
                  }
                } catch (err: any) {
                  const code = err?.name || err?.code || '';
                  if (code === 'AliasExistsException') {
                    setError('Username is taken. Please choose another.');
                  } else {
                    setError(err?.message || 'Failed to set password/handle');
                  }
                } finally {
                  setIsLoading(false);
                }
              }}
              className="waitlist-form"
            >
              <p>Finish setup by choosing your password and a unique handle.</p>
              <div className="input-group" style={{ position: 'relative' }}>
                <input value={newPassword} onChange={(e) => setNewPassword(e.target.value)} type={showNewPassword ? 'text' : 'password'} required className="waitlist-input" placeholder="New password" />
                <button
                  type="button"
                  aria-label={showNewPassword ? 'Hide password' : 'Show password'}
                  onClick={() => setShowNewPassword((v) => !v)}
                  style={{ position: 'absolute', right: 16, top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 0, padding: 0, cursor: 'pointer' }}
                >
                  <EyeIcon hidden={showNewPassword} />
                </button>
              </div>
              <div className="input-group">
                <input value={handle} onChange={(e) => setHandle(e.target.value)} required className="waitlist-input" placeholder="Handle (e.g. johndoe)" />
              </div>
              {error && <p style={{ color: '#ff6b6b' }}>{error}</p>}
              <button className="waitlist-submit-btn" type="submit" disabled={isLoading}>
                <span>{isLoading ? 'Saving...' : 'Save and sign in'}</span>
                {isLoading && <div className="spinner" style={{ display: 'inline-block', marginLeft: 8 }} />}
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}
