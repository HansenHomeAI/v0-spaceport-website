"use client";
import React, { useEffect, useState } from "react";
import { Auth } from 'aws-amplify';

type AccountModalProps = {
  className?: string;
};

export default function AccountModal({ className = "" }: AccountModalProps): JSX.Element {
  const [user, setUser] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const getCurrentUser = async () => {
      try {
        const currentUser = await Auth.currentAuthenticatedUser();
        setUser(currentUser);
      } catch (error) {
        console.error('Error getting current user:', error);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    getCurrentUser();
  }, []);

  const handleSignOut = async () => {
    try {
      await Auth.signOut();
      // The page will automatically redirect to sign-in via AuthGate
      window.location.reload();
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  if (isLoading) {
    return (
      <div className={`account-modal ${className}`}>
        <div className="account-loading">
          <div className="spinner"></div>
          <span>Loading account...</span>
        </div>
      </div>
    );
  }

  // Extract user information
  const email = user?.attributes?.email || user?.username || 'Unknown';
  const handle = user?.attributes?.preferred_username || user?.attributes?.name || email.split('@')[0];
  const subscriptionLevel = 'Beta Tester'; // For now, all users are beta testers

  return (
    <div className={`account-modal ${className}`}>
      <div className="account-info">
        <div className="account-header">
          <h3>Account</h3>
        </div>
        <div className="account-details">
          <div className="account-field">
            <span className="account-label">Handle:</span>
            <span className="account-value">{handle}</span>
          </div>
          <div className="account-field">
            <span className="account-label">Email:</span>
            <span className="account-value">{email}</span>
          </div>
          <div className="account-field">
            <span className="account-label">Subscription:</span>
            <span className="account-value subscription-level">{subscriptionLevel}</span>
          </div>
        </div>
        <div className="account-actions">
          <button 
            className="sign-out-btn"
            onClick={handleSignOut}
          >
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}
