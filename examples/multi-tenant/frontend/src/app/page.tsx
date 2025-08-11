'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AuthProvider } from '@auth-kit/react'
import { StorageType } from '@auth-kit/core'
import LandingPage from '@/components/LandingPage'

export default function Home() {
  const router = useRouter()

  return (
    <AuthProvider
      config={{
        apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
        storageType: StorageType.LocalStorage,
        enableAutoRefresh: true,
      }}
    >
      <LandingPage />
    </AuthProvider>
  )
}