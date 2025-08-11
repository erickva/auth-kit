'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { LoginForm } from '@auth-kit/react'
import { useAuth } from '@auth-kit/react'

export default function LoginPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuth()
  const [error, setError] = useState<string | null>(null)

  const handleSuccess = () => {
    router.push('/dashboard')
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
          Sign in to your account
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Or{' '}
          <Link
            href="/register"
            className="font-medium text-indigo-600 hover:text-indigo-500"
          >
            create a new account
          </Link>
        </p>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Error signing in
              </h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <LoginForm
        onSuccess={handleSuccess}
        onError={handleError}
        showPasskey={true}
        showRememberMe={true}
        className="mt-8 space-y-6"
        submitButtonText="Sign in"
        submitButtonClassName="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
      />
    </>
  )
}