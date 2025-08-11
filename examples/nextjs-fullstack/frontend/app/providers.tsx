'use client';

import { AuthKitProvider } from '@auth-kit/react';
import { ReactNode } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <AuthKitProvider
      config={{
        api: {
          baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
        },
        features: {
          passkeys: true,
          twoFactor: true,
          emailVerification: true,
          rememberMe: true,
        },
        storage: {
          driver: 'localStorage',
        },
      }}
    >
      {children}
    </AuthKitProvider>
  );
}