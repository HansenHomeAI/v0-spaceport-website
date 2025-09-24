// Analytics configuration and utilities
// This file centralizes all analytics setup for easy management

import posthog from 'posthog-js';

// Environment variables for analytics (to be set in production)
const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;
const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com';

// Initialize PostHog
export const initPostHog = () => {
  if (typeof window !== 'undefined' && POSTHOG_KEY) {
    posthog.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      capture_pageview: true,
      capture_pageleave: true,
      disable_cookie: true, // Cookie-less as requested
      disable_session_recording: true, // Privacy-first approach
      loaded: (posthog) => {
        if (process.env.NODE_ENV === 'development') {
          posthog.debug();
        }
      }
    });
  }
};

// PostHog event tracking utilities
export const trackEvent = (eventName: string, properties?: Record<string, any>) => {
  if (typeof window !== 'undefined' && posthog) {
    posthog.capture(eventName, properties);
  }
};

// Common events for your app
export const AnalyticsEvents = {
  // User engagement
  PAGE_VIEW: 'page_view',
  BUTTON_CLICK: 'button_click',
  FORM_SUBMIT: 'form_submit',
  
  // ML Pipeline specific
  ML_JOB_STARTED: 'ml_job_started',
  ML_JOB_COMPLETED: 'ml_job_completed',
  ML_JOB_FAILED: 'ml_job_failed',
  DRONE_PATH_CALCULATED: 'drone_path_calculated',
  
  // Business events
  PRICING_VIEWED: 'pricing_viewed',
  CREATE_PAGE_VIEWED: 'create_page_viewed',
  WAITLIST_SIGNUP: 'waitlist_signup',

  // Project delivery
  MODEL_LINK_VIEWED: 'model_link_viewed',
  MODEL_LINK_OPENED: 'model_link_opened',
  MODEL_LINK_COPIED: 'model_link_copied',
  MODEL_LINK_COPY_FAILED: 'model_link_copy_failed',
  MODEL_LINK_UNAVAILABLE: 'model_link_unavailable',

  // Error tracking
  ERROR_OCCURRED: 'error_occurred',
  API_ERROR: 'api_error',
} as const;

// Track page views with additional context
export const trackPageView = (pageName: string, additionalProperties?: Record<string, any>) => {
  trackEvent(AnalyticsEvents.PAGE_VIEW, {
    page: pageName,
    timestamp: new Date().toISOString(),
    ...additionalProperties
  });
};

// Track user actions
export const trackUserAction = (action: string, element?: string, properties?: Record<string, any>) => {
  trackEvent(AnalyticsEvents.BUTTON_CLICK, {
    action,
    element,
    timestamp: new Date().toISOString(),
    ...properties
  });
};

// Track ML pipeline events
export const trackMLJob = (jobType: 'started' | 'completed' | 'failed', jobId: string, properties?: Record<string, any>) => {
  const eventName = jobType === 'started' ? AnalyticsEvents.ML_JOB_STARTED :
                   jobType === 'completed' ? AnalyticsEvents.ML_JOB_COMPLETED :
                   AnalyticsEvents.ML_JOB_FAILED;
  
  trackEvent(eventName, {
    job_id: jobId,
    job_type: jobType,
    timestamp: new Date().toISOString(),
    ...properties
  });
};

// Error tracking helper
export const trackError = (error: Error, context?: Record<string, any>) => {
  trackEvent(AnalyticsEvents.ERROR_OCCURRED, {
    error_message: error.message,
    error_stack: error.stack,
    error_name: error.name,
    timestamp: new Date().toISOString(),
    ...context
  });
};
