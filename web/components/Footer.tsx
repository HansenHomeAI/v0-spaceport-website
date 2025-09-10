'use client';
import { useState } from 'react';
import TermsOfServiceModal from './TermsOfServiceModal';

export default function Footer(): JSX.Element {
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTermsModalOpen, setIsTermsModalOpen] = useState(false);

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedback.trim()) return;

    setIsSubmitting(true);
    
    // Create mailto link
    const subject = encodeURIComponent('Spaceport AI Feedback');
    const body = encodeURIComponent(feedback);
    const mailtoLink = `mailto:hello@spcprt.com?subject=${subject}&body=${body}`;
    
    // Open email client
    window.location.href = mailtoLink;
    
    // Reset form
    setFeedback('');
    setIsSubmitting(false);
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
                placeholder="Where do we have room for improvement?"
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

