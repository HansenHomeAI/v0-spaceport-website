'use client';
import React, { useCallback, useEffect, useState } from 'react';
import { configureAmplify, isAuthAvailable } from '../amplifyClient';
import { Auth } from 'aws-amplify';
import { useSearchParams } from 'next/navigation';

type AuthGateProps = {
  children: React.ReactNode;
  onAuthenticated?: (user: any) => void | Promise<void>;
};

type View = 'signin' | 'new_password' | 'forgot_password' | 'reset_password';
type ModalMode = 'waitlist' | 'login';

export default function AuthGate({ children, onAuthenticated }: AuthGateProps): JSX.Element {
  const searchParams = useSearchParams();
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
  
  // Modal state
  const [modalMode, setModalMode] = useState<ModalMode>(() => {
    // Check if user came from Stripe checkout or has a plan parameter
    const plan = searchParams?.get('plan');
    const redirect = searchParams?.get('redirect');
    return (plan || redirect === 'pricing') ? 'login' : 'waitlist';
  });

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
    <section className="section" id="signup" style={{ maxWidth: 600, margin: '0 auto' }}>
      <div className="auth-modal-container">
        <div className="auth-modal">
          <div className="auth-modal-header">
            <img src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport AI" className="auth-logo" />
            
            {/* Pill-shaped toggle */}
            <div className="auth-toggle-container">
              <div className="auth-toggle">
                <div 
                  className={`auth-toggle-slider ${modalMode === 'login' ? 'auth-toggle-slider-right' : ''}`}
                />
                <button
                  type="button"
                  className={`auth-toggle-option ${modalMode === 'waitlist' ? 'active' : ''}`}
                  onClick={() => {
                    setModalMode('waitlist');
                    setError(null);
                    setSuccessMessage(null);
                  }}
                >
                  Sign Up for Waitlist
                </button>
                <button
                  type="button"
                  className={`auth-toggle-option ${modalMode === 'login' ? 'active' : ''}`}
                  onClick={() => {
                    setModalMode('login');
                    setError(null);
                    setSuccessMessage(null);
                  }}
                >
                  Login
                </button>
              </div>
            </div>
          </div>
          
          <div className="auth-modal-content">
            {/* Waitlist Mode */}
            {modalMode === 'waitlist' && (
              <div className="auth-mode-content">
                <h2>New here?</h2>
                <p>Join the waitlist to be among the first to access Spaceport AI.</p>
                
                <form onSubmit={joinWaitlist} className="auth-form">
                  <div className="input-group">
                    <input 
                      className="auth-input" 
                      placeholder="Name" 
                      value={name} 
                      onChange={(e) => setName(e.target.value)} 
                    />
                  </div>
                  <div className="input-group">
                    <input 
                      className="auth-input" 
                      placeholder="Email Address" 
                      type="email" 
                      value={waitlistEmail} 
                      onChange={(e) => setWaitlistEmail(e.target.value)} 
                    />
                  </div>
                  {error && <p className="auth-error">{error}</p>}
                  <button type="submit" className="auth-submit-btn" disabled={waitlistSubmitting}>
                    <span>{waitlistSubmitting ? 'Submitting…' : 'Join Waitlist'}</span>
                    {waitlistSubmitting && <div className="spinner" />}
                  </button>
                </form>
              </div>
            )}
            
            {/* Login Mode */}
            {modalMode === 'login' && (
              <div className="auth-mode-content">
                <h2>Sign in to create your model</h2>
                
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
                    <div className="auth-link-container">
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
                    <div className="auth-link-container">
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
                    <div className="auth-link-container">
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
                    className="auth-form"
                  >
                    <p className="auth-description">Finish setup by choosing your password and a unique handle.</p>
                    <div className="input-group" style={{ position: 'relative' }}>
                      <input 
                        value={newPassword} 
                        onChange={(e) => setNewPassword(e.target.value)} 
                        type={showNewPassword ? 'text' : 'password'} 
                        required 
                        className="auth-input" 
                        placeholder="New password" 
                      />
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
                      <input 
                        value={handle} 
                        onChange={(e) => setHandle(e.target.value)} 
                        required 
                        className="auth-input" 
                        placeholder="Handle (e.g. johndoe)" 
                      />
                    </div>
                    {error && <p className="auth-error">{error}</p>}
                    <button className="auth-submit-btn" type="submit" disabled={isLoading}>
                      <span>{isLoading ? 'Saving...' : 'Save and sign in'}</span>
                      {isLoading && <div className="spinner" />}
                    </button>
                  </form>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
