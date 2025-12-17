import React from 'react';
import { OAuthProvider, OAuthProviderInfo } from '@erickva/auth-kit-core';
import { useSocialLogin } from '../hooks/useSocialLogin';

export interface SocialLoginButtonsProps {
  /**
   * Mode: 'login' for signing in, 'link' for linking accounts
   */
  mode?: 'login' | 'link';

  /**
   * Custom redirect URI for OAuth callback
   */
  redirectUri?: string;

  /**
   * Filter to only show specific providers
   */
  providers?: OAuthProvider[];

  /**
   * Button layout direction
   */
  direction?: 'horizontal' | 'vertical';

  /**
   * Button size
   */
  size?: 'small' | 'medium' | 'large';

  /**
   * Show provider name on button
   */
  showLabels?: boolean;

  /**
   * Custom button styles
   */
  buttonStyle?: React.CSSProperties;

  /**
   * Custom container styles
   */
  containerStyle?: React.CSSProperties;

  /**
   * Custom class name for buttons
   */
  buttonClassName?: string;

  /**
   * Custom class name for container
   */
  containerClassName?: string;

  /**
   * Called when login starts
   */
  onLoginStart?: (provider: OAuthProvider) => void;

  /**
   * Called on error
   */
  onError?: (error: string) => void;
}

// Provider brand colors and icons
const providerConfig: Record<OAuthProvider, {
  displayName: string;
  color: string;
  hoverColor: string;
  textColor: string;
  icon: React.ReactNode;
}> = {
  google: {
    displayName: 'Google',
    color: '#ffffff',
    hoverColor: '#f8f8f8',
    textColor: '#1f1f1f',
    icon: (
      <svg width="18" height="18" viewBox="0 0 18 18">
        <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z"/>
        <path fill="#34A853" d="M9.003 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9.003 18z"/>
        <path fill="#FBBC05" d="M3.964 10.712A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.33z"/>
        <path fill="#EA4335" d="M9.003 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.464.891 11.428 0 9.002 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29c.708-2.127 2.692-3.71 5.036-3.71z"/>
      </svg>
    )
  },
  github: {
    displayName: 'GitHub',
    color: '#24292e',
    hoverColor: '#2f363d',
    textColor: '#ffffff',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
      </svg>
    )
  },
  apple: {
    displayName: 'Apple',
    color: '#000000',
    hoverColor: '#1a1a1a',
    textColor: '#ffffff',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
        <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
      </svg>
    )
  }
};

const sizeStyles = {
  small: {
    padding: '8px 12px',
    fontSize: '13px',
    iconSize: 16,
    gap: '6px'
  },
  medium: {
    padding: '10px 16px',
    fontSize: '14px',
    iconSize: 18,
    gap: '8px'
  },
  large: {
    padding: '12px 20px',
    fontSize: '16px',
    iconSize: 20,
    gap: '10px'
  }
};

/**
 * Social login buttons component
 *
 * Renders styled buttons for each available OAuth provider
 *
 * @example
 * ```tsx
 * // Login buttons
 * <SocialLoginButtons mode="login" />
 *
 * // Link account buttons (when authenticated)
 * <SocialLoginButtons mode="link" showLabels={true} />
 *
 * // Only show specific providers
 * <SocialLoginButtons providers={['google', 'github']} />
 * ```
 */
export function SocialLoginButtons({
  mode = 'login',
  redirectUri,
  providers: filterProviders,
  direction = 'vertical',
  size = 'medium',
  showLabels = true,
  buttonStyle,
  containerStyle,
  buttonClassName,
  containerClassName,
  onLoginStart,
  onError
}: SocialLoginButtonsProps) {
  const { providers, linkedAccounts, isLoading, error, startLogin, startLink } = useSocialLogin();

  // Get size config
  const sizeConfig = sizeStyles[size];

  // Filter providers if specified
  const availableProviders = filterProviders
    ? providers.filter(p => filterProviders.includes(p.name) && p.enabled)
    : providers.filter(p => p.enabled);

  // Check if provider is already linked
  const isLinked = (provider: OAuthProvider) =>
    linkedAccounts.some(a => a.provider === provider);

  // Handle button click
  const handleClick = async (provider: OAuthProvider) => {
    try {
      onLoginStart?.(provider);

      if (mode === 'link') {
        await startLink(provider, redirectUri);
      } else {
        await startLogin(provider, redirectUri);
      }
    } catch (err: any) {
      onError?.(err.message || 'Failed to start OAuth');
    }
  };

  // Report errors
  React.useEffect(() => {
    if (error && onError) {
      onError(error);
    }
  }, [error, onError]);

  if (availableProviders.length === 0) {
    return null;
  }

  return (
    <div
      className={containerClassName}
      style={{
        display: 'flex',
        flexDirection: direction === 'horizontal' ? 'row' : 'column',
        gap: '12px',
        width: '100%',
        ...containerStyle
      }}
    >
      {availableProviders.map((provider) => {
        const config = providerConfig[provider.name];
        const linked = isLinked(provider.name);

        // In link mode, skip already linked providers
        if (mode === 'link' && linked) {
          return null;
        }

        return (
          <button
            key={provider.name}
            onClick={() => handleClick(provider.name)}
            disabled={isLoading}
            className={buttonClassName}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: sizeConfig.gap,
              padding: sizeConfig.padding,
              fontSize: sizeConfig.fontSize,
              fontWeight: 500,
              backgroundColor: config.color,
              color: config.textColor,
              border: provider.name === 'google' ? '1px solid #dadce0' : 'none',
              borderRadius: '6px',
              cursor: isLoading ? 'wait' : 'pointer',
              transition: 'background-color 0.2s ease',
              opacity: isLoading ? 0.7 : 1,
              flex: direction === 'horizontal' ? 1 : undefined,
              minWidth: showLabels ? '200px' : '44px',
              ...buttonStyle
            }}
            onMouseEnter={(e) => {
              if (!isLoading) {
                e.currentTarget.style.backgroundColor = config.hoverColor;
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = config.color;
            }}
          >
            <span style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: sizeConfig.iconSize,
              height: sizeConfig.iconSize
            }}>
              {config.icon}
            </span>
            {showLabels && (
              <span>
                {mode === 'login'
                  ? `Continue with ${config.displayName}`
                  : `Link ${config.displayName}`}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
