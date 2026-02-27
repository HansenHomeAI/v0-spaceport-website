'use client';

import { useState } from 'react';

export const runtime = 'edge';

export default function Pricing(): JSX.Element {
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    listingInfo: '',
  });
  const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('submitting');

    try {
      // Use the feedback API but with a specific source
      const rawFeedbackEndpoint = process.env.NEXT_PUBLIC_FEEDBACK_API_URL;
      const normalizedFeedbackEndpoint = rawFeedbackEndpoint
        ?.trim()
        .replace(/\s+/g, '');
      const feedbackEndpoint = normalizedFeedbackEndpoint && normalizedFeedbackEndpoint !== '/-' && normalizedFeedbackEndpoint !== '-'
        ? normalizedFeedbackEndpoint
        : undefined;

      if (!feedbackEndpoint) {
        throw new Error('Feedback endpoint not configured');
      }

      const endpoint = `${feedbackEndpoint.replace(/\/$/, '')}/feedback`;
      
      const message = `Name: ${formData.name}\nPhone: ${formData.phone}\nListing/Address: ${formData.listingInfo}`;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: message,
          source: 'contact-sales',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to submit');
      }

      setStatus('success');
      setFormData({ name: '', phone: '', listingInfo: '' });
      
      // Reset success message after 5 seconds
      setTimeout(() => setStatus('idle'), 5000);
    } catch (err) {
      console.error('Submission error:', err);
      setStatus('error');
    }
  };

  return (
    <>
      <section className="section" id="pricing-header">
        <h1>Pricing.</h1>
        <p><span className="inline-white">Capture the imagination of your buyers.</span></p>
      </section>
      <section className="section" id="pricing" style={{ padding: '40px 20px' }}>
        <div style={{ display: 'flex', justifyContent: 'center', width: '100%' }}>
          <div className="auth-modal" style={{ margin: 0 }}>
            <div className="auth-modal-header">
              <h2>Contact Sales</h2>
              <p>Fill out the form below and our team will get back to you shortly.</p>
            </div>
            
            <form onSubmit={handleSubmit} className="auth-form">
              <div className="input-group">
                <input
                  type="text"
                  placeholder="Name"
                  className="auth-input"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="input-group">
                <input
                  type="tel"
                  placeholder="Phone"
                  className="auth-input"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  required
                />
              </div>
              <div className="input-group">
                <input
                  type="text"
                  placeholder="Listing Link or Address"
                  className="auth-input"
                  value={formData.listingInfo}
                  onChange={(e) => setFormData({ ...formData, listingInfo: e.target.value })}
                  required
                />
              </div>
              
              <button 
                type="submit" 
                className="cta-button2" 
                disabled={status === 'submitting'}
                style={{ width: '100%', marginLeft: 0, marginTop: '10px', fontWeight: 500 }}
              >
                {status === 'submitting' ? 'Sending...' : 'Contact'}
              </button>

              {status === 'success' && (
                <p className="auth-success">
                  Thanks! We'll be in touch soon.
                </p>
              )}
              {status === 'error' && (
                <p className="auth-error">
                  Something went wrong. Please try again.
                </p>
              )}
            </form>
          </div>
        </div>
      </section>
    </>
  );
}
