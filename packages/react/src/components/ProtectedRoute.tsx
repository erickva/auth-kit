import React, { useEffect } from 'react';
import { useAuth } from '../hooks';

export interface ProtectedRouteProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  redirectTo?: string;
  requiredRole?: string | string[];
  requiredPermissions?: string | string[];
  onUnauthorized?: () => void;
}

export function ProtectedRoute({
  children,
  fallback = null,
  redirectTo,
  requiredRole,
  requiredPermissions,
  onUnauthorized
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated && redirectTo) {
      window.location.href = redirectTo;
    }
  }, [isLoading, isAuthenticated, redirectTo]);

  useEffect(() => {
    if (!isLoading && isAuthenticated && user) {
      // Check role requirements
      if (requiredRole) {
        const roles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
        if (!user.role || !roles.includes(user.role)) {
          onUnauthorized?.();
          if (redirectTo) {
            window.location.href = redirectTo;
          }
        }
      }

      // Check permission requirements (if your user model has permissions)
      if (requiredPermissions && user.metadata?.permissions) {
        const permissions = Array.isArray(requiredPermissions) ? requiredPermissions : [requiredPermissions];
        const userPermissions = user.metadata.permissions as string[];
        const hasAllPermissions = permissions.every(perm => userPermissions.includes(perm));
        
        if (!hasAllPermissions) {
          onUnauthorized?.();
          if (redirectTo) {
            window.location.href = redirectTo;
          }
        }
      }
    }
  }, [isLoading, isAuthenticated, user, requiredRole, requiredPermissions, redirectTo, onUnauthorized]);

  if (isLoading) {
    return <>{fallback || <div className="auth-kit-loading">Loading...</div>}</>;
  }

  if (!isAuthenticated) {
    return <>{fallback}</>;
  }

  // Check role requirements
  if (requiredRole && user) {
    const roles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
    if (!user.role || !roles.includes(user.role)) {
      return <>{fallback}</>;
    }
  }

  // Check permission requirements
  if (requiredPermissions && user?.metadata?.permissions) {
    const permissions = Array.isArray(requiredPermissions) ? requiredPermissions : [requiredPermissions];
    const userPermissions = user.metadata.permissions as string[];
    const hasAllPermissions = permissions.every(perm => userPermissions.includes(perm));
    
    if (!hasAllPermissions) {
      return <>{fallback}</>;
    }
  }

  return <>{children}</>;
}