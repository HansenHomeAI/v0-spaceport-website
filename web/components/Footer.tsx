'use client';
import { useState } from 'react';
import TermsOfServiceModal from './TermsOfServiceModal';

const FEEDBACK_ENDPOINT =
  process.env.NEXT_PUBLIC_FEEDBACK_API_URL || '/api/feedback';

export default function Footer(): JSX.Element {
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTermsModalOpen, setIsTermsModalOpen] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [statusType, setStatusType] = useState<'success' | 'error' | null>(null);

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedback.trim()) return;

    setIsSubmitting(true);
    setStatusMessage(null);
    setStatusType(null);

    try {
      const response = await fetch(FEEDBACK_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: feedback.trim(),
          source: 'web-footer',
        }),
      });

      const result = await response.json().catch(() => ({}));

      if (!response.ok || result?.success === false) {
        const errorMessage =
          result?.error || 'We could not send your feedback. Please try again.';
        setStatusMessage(errorMessage);
        setStatusType('error');
        return;
      }

      setStatusMessage('Thanks for the feedback!');
      setStatusType('success');
      setFeedback('');
    } catch (error) {
      console.error('Failed to send feedback', error);
      setStatusMessage('We could not send your feedback. Please try again.');
      setStatusType('error');
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
            {statusMessage && (
              <p
                className={`feedback-status ${
                  statusType === 'error' ? 'feedback-status-error' : 'feedback-status-success'
                }`}
                role="status"
                aria-live="polite"
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
