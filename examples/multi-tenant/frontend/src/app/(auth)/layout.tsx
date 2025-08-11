'use client'

import { AuthProvider } from '@auth-kit/react'
import { StorageType } from '@auth-kit/core'

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthProvider
      config={{
        apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
        storageType: StorageType.LocalStorage,
        enableAutoRefresh: true,
      }}
    >
      <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          {children}
        </div>
      </div>
    </AuthProvider>
  )
}