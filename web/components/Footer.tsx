'use client';
import { useState } from 'react';
import TermsOfServiceModal from './TermsOfServiceModal';

export default function Footer(): JSX.Element {
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [isTermsModalOpen, setIsTermsModalOpen] = useState(false);

  const rawFeedbackEndpoint = process.env.NEXT_PUBLIC_FEEDBACK_API_URL;
  const feedbackEndpoint = rawFeedbackEndpoint && rawFeedbackEndpoint !== '/-'
    ? rawFeedbackEndpoint
    : undefined;

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedback.trim()) {
      return;
    }

    if (!feedbackEndpoint) {
      console.error('Feedback endpoint is not configured.');
      setStatus('error');
      return;
    }

    const endpoint = `${feedbackEndpoint.replace(/\/$/, '')}/feedback`;

    setIsSubmitting(true);
    setStatus('idle');

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: feedback.trim(),
          source: 'footer',
        }),
      });

      const data = await response.json().catch(() => null);

      if (!response.ok || (data && data.success === false)) {
        throw new Error(data?.error || 'Feedback submission failed');
      }

      setFeedback('');
      setStatus('success');
    } catch (err) {
      console.error('Feedback submission error:', err);
      setStatus('error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      {/* Gradient logo section (previously landing-stats2) */}
      <section className="section" id="footer-stats">
        <div className="stats-grid">
          <div className="stat-box2 grainy">
            <img src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport Logo" />
          </div>
        </div>
      </section>

      {/* Feedback form section */}
      <section className="section" id="feedback-section">
        <div className="feedback-container">
          <form onSubmit={handleFeedbackSubmit} className="feedback-form">
            <div className="feedback-input-container">
              <input
                type="text"
                value={feedback}
                onChange={(e) => {
                  setFeedback(e.target.value);
                  if (status !== 'idle') setStatus('idle');
                }}
                placeholder="How can we improve?"
                className="feedback-input"
                disabled={isSubmitting}
              />
              <button
                type="submit"
                disabled={isSubmitting || !feedback.trim()}
                className="cta-button2 feedback-submit"
              >
                {isSubmitting ? 'Sending...' : 'Send Feedback'}
              </button>
            </div>
            <div
              aria-live="polite"
              className={`feedback-status ${status}`}
              style={{
                minHeight: '1.5rem',
                marginTop: '0.5rem',
                fontSize: '0.9rem',
                color: status === 'success' ? '#3fb27f' : status === 'error' ? '#ff6b6b' : 'transparent',
                transition: 'color 0.2s ease',
              }}
            >
              {status === 'success' && 'Thanks for sharing your feedback!'}
              {status === 'error' && 'Something went wrong. Please try again soon.'}
              {status === 'idle' && '‎'}
            </div>
          </form>
        </div>
      </section>

      {/* Traditional footer content */}
      <footer>
        <div className="footer-content">
          <p>
            © 2025 Spaceport AI · By using Spaceport AI, you agree to the{' '}
            <button 
              className="terms-link" 
              onClick={() => setIsTermsModalOpen(true)}
            >
              Terms of Service
            </button>
          </p>
        </div>
      </footer>

      {/* Terms of Service Modal */}
      <TermsOfServiceModal 
        isOpen={isTermsModalOpen} 
        onClose={() => setIsTermsModalOpen(false)} 
      />
    </>
  );
}
