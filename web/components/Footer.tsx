'use client';
import { useEffect, useState } from 'react';
import TermsOfServiceModal from './TermsOfServiceModal';
import { Button, Container, Input, Layout, Section } from './foundational';

export default function Footer(): JSX.Element {
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [isTermsModalOpen, setIsTermsModalOpen] = useState(false);

  const rawFeedbackEndpoint = process.env.NEXT_PUBLIC_FEEDBACK_API_URL;
  const normalizedFeedbackEndpoint = rawFeedbackEndpoint
    ?.trim()
    .replace(/\s+/g, '');
  const invalidSentinels = new Set(['/-', '-']);
  const feedbackEndpoint = normalizedFeedbackEndpoint && !invalidSentinels.has(normalizedFeedbackEndpoint)
    ? normalizedFeedbackEndpoint
    : undefined;

  useEffect(() => {
    if (status !== 'success') {
      return;
    }

    const timer = setTimeout(() => {
      setStatus('idle');
    }, 5000);

    return () => {
      clearTimeout(timer);
    };
  }, [status]);

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
      <Section id="footer-stats">
        <Layout.Grid variant="stats-grid">
          <Container variant={['stat-box2', 'grainy']}>
            <img src="/assets/SpaceportIcons/SpaceportFullLogoWhite.svg" alt="Spaceport Logo" />
          </Container>
        </Layout.Grid>
      </Section>

      {/* Feedback form section */}
      <Section id="feedback-section">
        <Container variant="feedback-container">
          <Container as="form" variant="feedback-form" onSubmit={handleFeedbackSubmit}>
            <Container variant="feedback-input-container">
              <Input.Text
                type="text"
                value={feedback}
                onChange={(e) => {
                  setFeedback(e.target.value);
                  if (status !== 'idle') setStatus('idle');
                }}
                placeholder="How can we improve?"
                variant="feedback-input"
                disabled={isSubmitting}
              />
              <Button.Base
                type="submit"
                disabled={isSubmitting || !feedback.trim()}
                variant={['cta-button2', 'feedback-submit']}
              >
                {isSubmitting ? 'Sending...' : 'Send Feedback'}
              </Button.Base>
            </Container>
            <Container
              aria-live="polite"
              variant={['feedback-status', status]}
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
            </Container>
          </Container>
        </Container>
      </Section>

      {/* Traditional footer content */}
      <footer>
        <Container variant="footer-content">
          <p>
            © 2025 Spaceport AI · By using Spaceport AI, you agree to the{' '}
            <Button.Link
              onClick={() => setIsTermsModalOpen(true)}
            >
              Terms of Service
            </Button.Link>
          </p>
        </Container>
      </footer>

      {/* Terms of Service Modal */}
      <TermsOfServiceModal 
        isOpen={isTermsModalOpen} 
        onClose={() => setIsTermsModalOpen(false)} 
      />
    </>
  );
}
