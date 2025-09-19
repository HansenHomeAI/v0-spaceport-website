'use client';
import { useState } from 'react';
import { buildApiUrl } from '../app/api-config';
import TermsOfServiceModal from './TermsOfServiceModal';

type FeedbackStatus = {
  type: 'success' | 'error';
  message: string;
};

export default function Footer(): JSX.Element {
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [status, setStatus] = useState<FeedbackStatus | null>(null);
  const [isTermsModalOpen, setIsTermsModalOpen] = useState(false);

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedFeedback = feedback.trim();
    if (!trimmedFeedback) return;

    setIsSubmitting(true);
    setStatus(null);

    try {
      const response = await fetch(buildApiUrl.feedback(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: trimmedFeedback,
          pageUrl: typeof window !== 'undefined' ? window.location.href : undefined,
        }),
      });

      const data = await response
        .json()
        .catch(() => ({ message: 'Unable to parse response' }));

      if (!response.ok) {
        const errorMessage = typeof data?.error === 'string' ? data.error : 'Failed to send feedback. Please try again.';
        setStatus({ type: 'error', message: errorMessage });
        return;
      }

      setStatus({
        type: 'success',
        message: 'Thanks for the feedback! Our team will review it shortly.',
      });
      setFeedback('');
    } catch (error) {
      const fallbackMessage = error instanceof Error ? error.message : 'Something went wrong. Please try again later.';
      setStatus({ type: 'error', message: fallbackMessage });
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
                onChange={(e) => setFeedback(e.target.value)}
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
            {status && (
              <p className={`feedback-status ${status.type}`}>
                {status.message}
              </p>
            )}
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
