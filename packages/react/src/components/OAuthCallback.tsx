import React, { useEffect, useState, useRef } from 'react';
import { OAuthProvider } from '@erickva/auth-kit-core';
import { useSocialLogin } from '../hooks/useSocialLogin';

export interface OAuthCallbackProps {
  /**
   * Called when OAuth login completes successfully
   */
  onSuccess?: (user: any) => void;

  /**
   * Called when OAuth login fails
   */
  onError?: (error: string) => void;

  /**
   * URL to navigate to after successful login (if not using onSuccess)
   */
  successRedirect?: string;

  /**
   * URL to navigate to on error (if not using onError)
   */
  errorRedirect?: string;

  /**
   * Custom loading component
   */
  loadingComponent?: React.ReactNode;

  /**
   * Custom error component
   */
  errorComponent?: (error: string) => React.ReactNode;
}

/**
 * OAuth callback handler component
 *
 * Place this component at your OAuth callback route (e.g., /auth/callback)
 * It automatically extracts the code and state from URL params and completes the OAuth flow
 *
 * @example
 * ```tsx
 * // In your router
 * <Route path="/auth/callback" element={
 *   <OAuthCallback
 *     onSuccess={(user) => navigate('/dashboard')}
 *     onError={(error) => navigate('/login', { state: { error } })}
 *   />
 * } />
 * ```
 */
export function OAuthCallback({
  onSuccess,
  onError,
  successRedirect,
  errorRedirect,
  loadingComponent,
  errorComponent
}: OAuthCallbackProps) {
  const { completeOAuth, error: hookError } = useSocialLogin();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);
  const processedRef = useRef(false);

  useEffect(() => {
    // Prevent double processing in React StrictMode
    if (processedRef.current) return;
    processedRef.current = true;

    const handleCallback = async () => {
      try {
        // Extract params from URL
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        const state = urlParams.get('state');
        const errorParam = urlParams.get('error');
        const errorDescription = urlParams.get('error_description');

        // Check for OAuth error response
        if (errorParam) {
          const errorMessage = errorDescription || errorParam;
          throw new Error(errorMessage);
        }

        // Validate required params
        if (!code || !state) {
          throw new Error('Missing required OAuth parameters');
        }

        // Extract provider from state (it's stored in sessionStorage)
        // We need to peek at the state to get the provider
        const stateKey = `auth_oauth_state_${state}`;
        const stateData = sessionStorage.getItem(stateKey);

        if (!stateData) {
          throw new Error('OAuth state not found or expired');
        }

        const parsedState = JSON.parse(stateData);
        const provider = parsedState.provider as OAuthProvider;

        // Complete OAuth flow
        const response = await completeOAuth(provider, code, state);

        // Handle success
        // For login mode: response contains user
        // For link mode: response is null (account was linked, user already authenticated)
        if (onSuccess) {
          onSuccess(response?.user || null);
        } else if (successRedirect) {
          window.location.href = successRedirect;
        }

        setIsProcessing(false);
      } catch (err: any) {
        const errorMessage = err.message || 'OAuth authentication failed';
        setError(errorMessage);
        setIsProcessing(false);

        if (onError) {
          onError(errorMessage);
        } else if (errorRedirect) {
          const redirectUrl = new URL(errorRedirect, window.location.origin);
          redirectUrl.searchParams.set('error', errorMessage);
          window.location.href = redirectUrl.toString();
        }
      }
    };

    handleCallback();
  }, [completeOAuth, onSuccess, onError, successRedirect, errorRedirect]);

  // Show error if present
  const displayError = error || hookError;
  if (displayError && !isProcessing) {
    if (errorComponent) {
      return <>{errorComponent(displayError)}</>;
    }

    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '200px',
        padding: '20px',
        textAlign: 'center'
      }}>
        <div style={{
          color: '#dc2626',
          marginBottom: '16px',
          fontSize: '16px'
        }}>
          {displayError}
        </div>
        <button
          onClick={() => window.location.href = '/login'}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            border: 'none',
            backgroundColor: '#3b82f6',
            color: 'white',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          Return to Login
        </button>
      </div>
    );
  }

  // Show loading state
  if (loadingComponent) {
    return <>{loadingComponent}</>;
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '200px',
      padding: '20px'
    }}>
      <div style={{
        width: '40px',
        height: '40px',
        border: '3px solid #e5e7eb',
        borderTopColor: '#3b82f6',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite'
      }} />
      <p style={{
        marginTop: '16px',
        color: '#6b7280',
        fontSize: '14px'
      }}>
        Completing sign in...
      </p>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
