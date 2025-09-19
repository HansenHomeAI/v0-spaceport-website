'use client';

import { FormEvent, useCallback, useMemo, useState } from 'react';

import { buildApiUrl } from '../api-config';

const EMAIL_REGEX = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

type SubmissionState = 'idle' | 'loading' | 'success' | 'error';

export function ContactForm(): JSX.Element {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState<SubmissionState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isSubmitting = status === 'loading';

  const isFormValid = useMemo(() => {
    return Boolean(
      name.trim() &&
      email.trim() &&
      EMAIL_REGEX.test(email.trim()) &&
      message.trim().length >= 10
    );
  }, [email, message, name]);

  const resetForm = useCallback(() => {
    setName('');
    setEmail('');
    setMessage('');
  }, []);

  const handleSubmit = useCallback(async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting || !isFormValid) return;

    setStatus('loading');
    setErrorMessage(null);

    try {
      const response = await fetch(buildApiUrl.contact(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          message: message.trim(),
        }),
      });

      const payload = await response.json().catch(() => ({}));

      if (!response.ok) {
        const friendlyError = typeof payload?.error === 'string' ? payload.error : 'Something went wrong. Please try again.';
        setErrorMessage(friendlyError);
        setStatus('error');
        return;
      }

      resetForm();
      setStatus('success');
    } catch (error) {
      if (process.env.NODE_ENV !== 'production') {
        console.warn('Contact form submission failed', error);
      }
      setErrorMessage('Unable to send message right now. Please check your connection and try again.');
      setStatus('error');
    }
  }, [email, isFormValid, isSubmitting, message, name, resetForm]);

  return (
    <form className="contact-form" onSubmit={handleSubmit} noValidate>
      <div className="contact-form-grid">
        <label className="contact-form-field">
          <span>Name</span>
          <input
            type="text"
            name="name"
            autoComplete="name"
            placeholder="Jane Doe"
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={isSubmitting}
            required
          />
        </label>

        <label className="contact-form-field">
          <span>Email</span>
          <input
            type="email"
            name="email"
            autoComplete="email"
            placeholder="jane@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={isSubmitting}
            required
          />
        </label>
      </div>

      <label className="contact-form-field">
        <span>Message</span>
        <textarea
          name="message"
          placeholder="Tell us about your project..."
          rows={5}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          disabled={isSubmitting}
          required
        />
      </label>

      <div className="contact-form-footer">
        <button type="submit" className="contact-form-submit" disabled={isSubmitting || !isFormValid}>
          {isSubmitting ? 'Sending…' : 'Send Message'}
        </button>
        <div className="contact-form-feedback" aria-live="polite">
          {status === 'success' && <span className="contact-form-success">Message sent! We will reach out soon.</span>}
          {status === 'error' && errorMessage && <span className="contact-form-error">{errorMessage}</span>}
        </div>
      </div>
    </form>
  );
}
