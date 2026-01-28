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
      <section className="section" id="pricing">
        <div className="pricing-grid" style={{ display: 'flex', justifyContent: 'center', width: '100%' }}>
          <div className="pricing-card" style={{ maxWidth: '500px', width: '100%', padding: '40px' }}>
            <h2>Contact Sales</h2>
            <p style={{ marginBottom: '30px' }}>Fill out the form below and our team will get back to you shortly.</p>
            
            <form onSubmit={handleSubmit} style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '15px' }}>
              <input
                type="text"
                placeholder="Name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                style={{
                  width: '100%',
                  padding: '15px 20px',
                  borderRadius: '12px',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  background: 'rgba(255, 255, 255, 0.05)',
                  color: 'white',
                  fontSize: '1rem',
                  outline: 'none'
                }}
              />
              <input
                type="tel"
                placeholder="Phone"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                required
                style={{
                  width: '100%',
                  padding: '15px 20px',
                  borderRadius: '12px',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  background: 'rgba(255, 255, 255, 0.05)',
                  color: 'white',
                  fontSize: '1rem',
                  outline: 'none'
                }}
              />
              <input
                type="text"
                placeholder="Listing Link or Address"
                value={formData.listingInfo}
                onChange={(e) => setFormData({ ...formData, listingInfo: e.target.value })}
                required
                style={{
                  width: '100%',
                  padding: '15px 20px',
                  borderRadius: '12px',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  background: 'rgba(255, 255, 255, 0.05)',
                  color: 'white',
                  fontSize: '1rem',
                  outline: 'none'
                }}
              />
              
              <button 
                type="submit" 
                className="cta-button" 
                disabled={status === 'submitting'}
                style={{ 
                  marginTop: '10px',
                  width: '100%',
                  opacity: status === 'submitting' ? 0.7 : 1,
                  cursor: status === 'submitting' ? 'not-allowed' : 'pointer'
                }}
              >
                {status === 'submitting' ? 'Sending...' : 'Contact'}
              </button>

              {status === 'success' && (
                <p style={{ color: '#3fb27f', marginTop: '15px', fontSize: '0.9rem' }}>
                  Thanks! We'll be in touch soon.
                </p>
              )}
              {status === 'error' && (
                <p style={{ color: '#ff6b6b', marginTop: '15px', fontSize: '0.9rem' }}>
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
