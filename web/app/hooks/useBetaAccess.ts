'use client';
import { useState, useEffect, useCallback } from 'react';
import { Auth } from 'aws-amplify';
import { buildApiUrl } from '../api-config';

interface BetaAccessState {
  hasBetaAccessPermission: boolean;
  loading: boolean;
  error: string | null;
  sendingInvitation: boolean;
}

interface BetaAccessActions {
  sendInvitation: (email: string, name?: string) => Promise<{ success: boolean; message: string }>;
  checkPermission: () => Promise<void>;
}

export function useBetaAccess(): BetaAccessState & BetaAccessActions {
  const [state, setState] = useState<BetaAccessState>({
    hasBetaAccessPermission: false,
    loading: true,
    error: null,
    sendingInvitation: false,
  });

  // Get API URLs from centralized configuration
  const getApiUrls = useCallback(() => ({
    checkPermission: buildApiUrl.betaAccess.checkPermission(),
    sendInvitation: buildApiUrl.betaAccess.sendInvitation(),
  }), []);

  const checkPermission = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      
      const apiUrls = getApiUrls();
      if (!apiUrls.checkPermission) {
        // API not configured yet - silently fail (user won't see beta access UI)
        setState(prev => ({
          ...prev,
          hasBetaAccessPermission: false,
          loading: false,
          error: null
        }));
        return;
      }
      
      const session = await Auth.currentSession();
      const idToken = session.getIdToken().getJwtToken();
      
      const response = await fetch(apiUrls.checkPermission, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication required');
        } else if (response.status === 403) {
          // User doesn't have permission - this is expected for most users
          setState(prev => ({
            ...prev,
            hasBetaAccessPermission: false,
            loading: false,
            error: null
          }));
          return;
        } else {
          throw new Error(`Failed to check permissions: ${response.status}`);
        }
      }

      const data = await response.json();
      setState(prev => ({
        ...prev,
        hasBetaAccessPermission: data.has_beta_access_permission || false,
        loading: false,
        error: null
      }));
    } catch (error: any) {
      const message = error?.message || 'Failed to check permissions';
      const benignAuthError = /not authenticated|no current user/i.test(message);
      if (!benignAuthError) {
        console.error('Error checking beta access permission:', error);
      }
      setState(prev => ({
        ...prev,
        hasBetaAccessPermission: false,
        loading: false,
        error: benignAuthError ? null : message
      }));
    }
  }, [getApiUrls]);

  const sendInvitation = useCallback(async (email: string, name: string = ''): Promise<{ success: boolean; message: string }> => {
    try {
      setState(prev => ({ ...prev, sendingInvitation: true, error: null }));
      
      const apiUrls = getApiUrls();
      if (!apiUrls.sendInvitation) {
        throw new Error('Beta access API is not configured');
      }
      
      const session = await Auth.currentSession();
      const idToken = session.getIdToken().getJwtToken();
      
      const response = await fetch(apiUrls.sendInvitation, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${idToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          name: name.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication required');
        } else if (response.status === 403) {
          throw new Error('You do not have permission to send invitations');
        } else {
          throw new Error(data.error || `Failed to send invitation: ${response.status}`);
        }
      }

      setState(prev => ({ ...prev, sendingInvitation: false }));
      return {
        success: true,
        message: data.message || 'Invitation sent successfully'
      };
    } catch (error: any) {
      console.error('Error sending invitation:', error);
      setState(prev => ({
        ...prev,
        sendingInvitation: false,
        error: error.message || 'Failed to send invitation'
      }));
      return {
        success: false,
        message: error.message || 'Failed to send invitation'
      };
    }
  }, [getApiUrls]);

  // Check permission on mount
  useEffect(() => {
    checkPermission();
  }, [checkPermission]);

  return {
    ...state,
    sendInvitation,
    checkPermission,
  };
}
