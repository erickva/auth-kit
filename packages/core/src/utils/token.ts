/**
 * JWT Token utilities
 */

export interface JWTPayload {
  sub: string;
  email?: string;
  exp?: number;
  iat?: number;
  jti?: string;
  [key: string]: any;
}

/**
 * Parse JWT token without verification
 * WARNING: This does not verify the token signature
 */
export function parseToken(token: string): JWTPayload | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) {
      return null;
    }

    const payload = parts[1];
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decoded);
  } catch (error) {
    console.error('Error parsing token:', error);
    return null;
  }
}

/**
 * Check if token is expired
 */
export function isTokenExpired(token: string): boolean {
  const payload = parseToken(token);
  if (!payload || !payload.exp) {
    return true;
  }

  const now = Date.now() / 1000;
  return now >= payload.exp;
}

/**
 * Check if token will expire soon
 */
export function isTokenExpiringSoon(token: string, bufferSeconds: number = 300): boolean {
  const payload = parseToken(token);
  if (!payload || !payload.exp) {
    return true;
  }

  const now = Date.now() / 1000;
  return now >= (payload.exp - bufferSeconds);
}

/**
 * Get time until token expiry in seconds
 */
export function getTokenTimeToExpiry(token: string): number {
  const payload = parseToken(token);
  if (!payload || !payload.exp) {
    return 0;
  }

  const now = Date.now() / 1000;
  return Math.max(0, payload.exp - now);
}

/**
 * Extract user ID from token
 */
export function getUserIdFromToken(token: string): string | null {
  const payload = parseToken(token);
  return payload?.sub || null;
}

/**
 * Calculate when to refresh token (5 minutes before expiry by default)
 */
export function calculateTokenRefreshTime(token: string, bufferSeconds: number = 300): number {
  const timeToExpiry = getTokenTimeToExpiry(token);
  const refreshTime = timeToExpiry - bufferSeconds;
  return Math.max(0, refreshTime * 1000); // Convert to milliseconds
}