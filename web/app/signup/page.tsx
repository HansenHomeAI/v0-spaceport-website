"use client";
export const runtime = 'edge';
import { useState } from 'react';

export default function Signup(): JSX.Element {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const WAITLIST_API = 'https://o7d0i4to5a.execute-api.us-west-2.amazonaws.com/prod/waitlist';

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(WAITLIST_API, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ name, email }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.error || 'Failed to join waitlist');
      }
      setSuccess(true);
      setName('');
      setEmail('');
    } catch (err: any) {
      setError(err?.message || 'Failed to join waitlist');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="section" id="signup">
      <div className="waitlist-container">
        <div className="waitlist-card">
          <div className="waitlist-header">
            <img src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport AI" className="waitlist-logo" />
            <h1>Join the waitlist for early access</h1>
            <p>Be among the first to experience the future of property visualization. We'll notify you when Spaceport AI is ready for launch.</p>
          </div>

          {!success ? (
            <form className="waitlist-form" onSubmit={onSubmit}>
              <div className="input-group">
                <input
                  type="text"
                  name="name"
                  placeholder="Name"
                  required
                  className="waitlist-input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div className="input-group">
                <input
                  type="email"
                  name="email"
                  placeholder="Email Address"
                  required
                  className="waitlist-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              {error && (
                <p style={{ color: '#ff6b6b', margin: '0 0 8px 0', fontSize: 14 }}>{error}</p>
              )}

              <button type="submit" className="waitlist-submit-btn" disabled={submitting}>
                <span id="waitlist-btn-text">{submitting ? 'Submitting…' : 'Join Waitlist'}</span>
                <div id="waitlist-spinner" className="spinner" style={{ display: submitting ? 'inline-block' : 'none' }} />
              </button>
            </form>
          ) : (
            <div id="waitlist-success" className="waitlist-success">
              <div className="success-icon">✓</div>
              <h3>You're on the list!</h3>
              <p>Thank you for your interest in Spaceport AI. We'll be in touch soon with early access details.</p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}


