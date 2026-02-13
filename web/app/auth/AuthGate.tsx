'use client';
import React, { useCallback, useEffect, useState } from 'react';
import { configureAmplify, isAuthAvailable } from '../amplifyClient';
import { Auth } from 'aws-amplify';
import { buildApiUrl } from '../api-config';

type AuthGateProps = {
  children: React.ReactNode;
  onAuthenticated?: (user: any) => void | Promise<void>;
};

type View = 'signin' | 'new_password' | 'forgot_password' | 'reset_password';
type AuthMode = 'waitlist' | 'login';

export default function AuthGate({ children, onAuthenticated }: AuthGateProps): JSX.Element {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [view, setView] = useState<View>('signin');
  const [authMode, setAuthMode] = useState<AuthMode>('waitlist');
  const [signInEmail, setSignInEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [name, setName] = useState('');
  const [waitlistEmail, setWaitlistEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const WAITLIST_API = buildApiUrl.waitlist();
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

  // Detect if coming from checkout flow and set default mode
  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Check if we have a checkout session in storage
    const checkoutData = window.sessionStorage.getItem('checkoutSession');
    if (checkoutData) {
      setAuthMode('login');
      return;
    }

    // Check URL parameters for checkout-related indicators
    const urlParams = new URLSearchParams(window.location.search);
    const checkoutParam = urlParams.get('checkout') || urlParams.get('payment_success');
    if (checkoutParam) {
      setAuthMode('login');
      return;
    }
  }, []);

  if (!ready) return <div style={{ padding: 24 }}>Loading…</div>;
  if (user) return <>{children}</>;

  const signIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      if (!isAuthAvailable()) throw new Error('Sign-in temporarily disabled');
      const res = await Auth.signIn(signInEmail, password);
      if (res.challengeName === 'NEW_PASSWORD_REQUIRED') {
        setPendingUser(res);
        setView('new_password');
        return;
      }
      const current = await Auth.currentAuthenticatedUser();
      completeSignIn(current);
    } catch (err: any) {
      setError(err?.message || 'Sign in failed');
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
      if (!WAITLIST_API) {
        throw new Error('Waitlist signups are temporarily unavailable');
      }

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
    <section className="section" id="signup" style={{ maxWidth: 900, margin: '0 auto', minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="auth-modal">
        {/* Mode Toggle */}
        <div className="auth-mode-toggle">
          <div className={`auth-mode-slider ${authMode === 'login' ? 'slide-right' : 'slide-left'}`} />
          <button
            type="button"
            className={`auth-mode-button ${authMode === 'waitlist' ? 'active' : ''}`}
            onClick={() => setAuthMode('waitlist')}
          >
            Sign Up
          </button>
          <button
            type="button"
            className={`auth-mode-button ${authMode === 'login' ? 'active' : ''}`}
            onClick={() => setAuthMode('login')}
          >
            Login
          </button>
        </div>

        {/* Modal Content */}
        <div className="auth-modal-content">
          <div className="auth-modal-header">
            <img src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport" className="auth-logo" />
            {authMode === 'waitlist' ? (
              <>
                <h2>New here?</h2>
                <p>Join the waitlist to be among the first to access Spaceport.</p>
              </>
            ) : (
              <>
                <h2>Welcome back!</h2>
                <p>Sign in to access your account.</p>
              </>
            )}
          </div>

          {/* Waitlist Form */}
          {authMode === 'waitlist' && (
            <form onSubmit={joinWaitlist} className="auth-form">
              <div className="input-group">
                <input
                  className="auth-input"
                  placeholder="Name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
              <div className="input-group">
                <input
                  className="auth-input"
                  placeholder="Email Address"
                  type="email"
                  value={waitlistEmail}
                  onChange={(e) => setWaitlistEmail(e.target.value)}
                  required
                />
              </div>
              {error && <p className="auth-error">{error}</p>}
              <button type="submit" className="auth-submit-btn" disabled={waitlistSubmitting}>
                <span>{waitlistSubmitting ? 'Submitting…' : 'Join Waitlist'}</span>
                {waitlistSubmitting && <div className="spinner" />}
              </button>
            </form>
          )}

          {/* Login Form */}
          {authMode === 'login' && (
            <>
              {/* Sign In View */}
              {view === 'signin' && (
                <form onSubmit={signIn} className="auth-form">
                  <div className="input-group">
                    <input
                      value={signInEmail}
                      onChange={(e) => setSignInEmail(e.target.value)}
                      type="email"
                      className="auth-input"
                      placeholder="Email"
                      required
                    />
                  </div>
                  <div className="input-group" style={{ position: 'relative' }}>
                    <input
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      type={showPassword ? 'text' : 'password'}
                      className="auth-input"
                      placeholder="Password"
                      required
                    />
                    <button
                      type="button"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      onClick={() => setShowPassword((v) => !v)}
                      className="password-toggle"
                    >
                      <EyeIcon hidden={showPassword} />
                    </button>
                  </div>
                  {error && <p className="auth-error">{error}</p>}
                  {successMessage && <p className="auth-success">{successMessage}</p>}
                  <button className="auth-submit-btn" type="submit" disabled={isLoading}>
                    <span>{isLoading ? 'Signing in...' : 'Sign in'}</span>
                    {isLoading && <div className="spinner" />}
                  </button>
                  <div className="auth-links">
                    <button
                      type="button"
                      onClick={() => setView('forgot_password')}
                      className="auth-link"
                    >
                      Forgot your password?
                    </button>
                  </div>
                </form>
              )}

              {/* Forgot Password View */}
              {view === 'forgot_password' && (
                <form onSubmit={handleForgotPassword} className="auth-form">
                  <p className="auth-description">
                    Enter your email address and we'll send you a code to reset your password.
                  </p>
                  <div className="input-group">
                    <input
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      type="email"
                      className="auth-input"
                      placeholder="Email address"
                      required
                    />
                  </div>
                  {error && <p className="auth-error">{error}</p>}
                  <button className="auth-submit-btn" type="submit" disabled={isLoading}>
                    <span>{isLoading ? 'Sending...' : 'Send reset code'}</span>
                    {isLoading && <div className="spinner" />}
                  </button>
                  <div className="auth-links">
                    <button
                      type="button"
                      onClick={resetForm}
                      className="auth-link"
                    >
                      Back to sign in
                    </button>
                  </div>
                </form>
              )}

              {/* Reset Password View */}
              {view === 'reset_password' && (
                <form onSubmit={handleResetPassword} className="auth-form">
                  <p className="auth-description">
                    Enter the code from your email and choose a new password.
                  </p>
                  <div className="input-group">
                    <input
                      value={resetCode}
                      onChange={(e) => setResetCode(e.target.value)}
                      type="text"
                      className="auth-input"
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
                      className="auth-input"
                      placeholder="New password"
                      required
                      minLength={8}
                    />
                    <button
                      type="button"
                      aria-label={showResetPassword ? 'Hide password' : 'Show password'}
                      onClick={() => setShowResetPassword((v) => !v)}
                      className="password-toggle"
                    >
                      <EyeIcon hidden={showResetPassword} />
                    </button>
                  </div>
                  {error && <p className="auth-error">{error}</p>}
                  <button className="auth-submit-btn" type="submit" disabled={isLoading}>
                    <span>{isLoading ? 'Resetting...' : 'Reset password'}</span>
                    {isLoading && <div className="spinner" />}
                  </button>
                  <div className="auth-links">
                    <button
                      type="button"
                      onClick={() => setView('forgot_password')}
                      className="auth-link"
                    >
                      Resend code
                    </button>
                  </div>
                </form>
              )}

              {/* New Password Required View */}
              {view === 'new_password' && (
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    setError(null);
                    setIsLoading(true);
                    try {
                      if (!pendingUser) throw new Error('Session expired');
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
                  className="auth-form"
                >
                  <p className="auth-description">Finish setup by choosing your password and a unique handle.</p>
                  <div className="input-group" style={{ position: 'relative' }}>
                    <input value={newPassword} onChange={(e) => setNewPassword(e.target.value)} type={showNewPassword ? 'text' : 'password'} required className="auth-input" placeholder="New password" />
                    <button
                      type="button"
                      aria-label={showNewPassword ? 'Hide password' : 'Show password'}
                      onClick={() => setShowNewPassword((v) => !v)}
                      className="password-toggle"
                    >
                      <EyeIcon hidden={showNewPassword} />
                    </button>
                  </div>
                  <div className="input-group">
                    <input value={handle} onChange={(e) => setHandle(e.target.value)} required className="auth-input" placeholder="Handle (e.g. johndoe)" />
                  </div>
                  {error && <p className="auth-error">{error}</p>}
                  <button className="auth-submit-btn" type="submit" disabled={isLoading}>
                    <span>{isLoading ? 'Saving...' : 'Save and sign in'}</span>
                    {isLoading && <div className="spinner" />}
                  </button>
                </form>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
