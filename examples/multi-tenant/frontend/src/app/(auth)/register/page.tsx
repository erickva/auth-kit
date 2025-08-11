'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { RegisterForm } from '@auth-kit/react'
import { useAuth } from '@auth-kit/react'

export default function RegisterPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuth()
  const [error, setError] = useState<string | null>(null)

  const handleSuccess = () => {
    // After registration, redirect to create organization
    router.push('/onboarding/organization')
  }

  const handleError = (error: Error) => {
    setError(error.message)
  }

  if (isAuthenticated) {
    router.push('/dashboard')
    return null
  }

  return (
    <>
      <div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Create your account
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Or{' '}
          <Link
            href="/login"
            className="font-medium text-indigo-600 hover:text-indigo-500"
          >
            sign in to your existing account
          </Link>
        </p>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Error creating account
              </h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <RegisterForm
        onSuccess={handleSuccess}
        onError={handleError}
        showPasswordStrength={true}
        requireEmailVerification={false}
        className="mt-8 space-y-6"
        submitButtonText="Create account"
        submitButtonClassName="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
      />

      <div className="mt-6">
        <p className="text-center text-xs text-gray-600">
          By creating an account, you agree to our{' '}
          <Link href="/terms" className="text-indigo-600 hover:text-indigo-500">
            Terms of Service
          </Link>{' '}
          and{' '}
          <Link href="/privacy" className="text-indigo-600 hover:text-indigo-500">
            Privacy Policy
          </Link>
        </p>
      </div>
    </>
  )
}