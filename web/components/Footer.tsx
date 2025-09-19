'use client';
import { useState } from 'react';
import { buildApiUrl } from '../app/api-config';
import TermsOfServiceModal from './TermsOfServiceModal';

export default function Footer(): JSX.Element {
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [statusMessage, setStatusMessage] = useState('');
  const [isTermsModalOpen, setIsTermsModalOpen] = useState(false);

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedback.trim()) return;

    setIsSubmitting(true);
    setStatus('idle');
    setStatusMessage('');

    try {
      const response = await fetch(buildApiUrl.feedback(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ feedback: feedback.trim() }),
      });

      const data = await response.json().catch(() => ({ }));

      if (!response.ok) {
        const errorMessage = typeof data?.error === 'string' && data.error
          ? data.error
          : 'Failed to send feedback. Please try again.';
        throw new Error(errorMessage);
      }

      setFeedback('');
      setStatus('success');
      setStatusMessage('Thanks! Your feedback has been sent.');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to send feedback. Please try again.';
      setStatus('error');
      setStatusMessage(message);
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
                  if (status !== 'idle') {
                    setStatus('idle');
                    setStatusMessage('');
                  }
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
            {status !== 'idle' && (
              <p
                className={`feedback-status feedback-status-${status}`}
                aria-live="polite"
                role={status === 'error' ? 'alert' : undefined}
              >
                {statusMessage}
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

