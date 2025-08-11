import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { RegisterForm } from '@auth-kit/react'
import { useAuth } from '@auth-kit/react'

export default function RegisterPage() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const [showSuccess, setShowSuccess] = useState(false)

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true })
    }
  }, [isAuthenticated, navigate])

  const handleSuccess = () => {
    setShowSuccess(true)
    setTimeout(() => {
      navigate('/login')
    }, 2000)
  }

  const handleError = (error: Error) => {
    console.error('Registration error:', error)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Create your account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Or{' '}
            <Link
              to="/login"
              className="font-medium text-indigo-600 hover:text-indigo-500"
            >
              sign in to your existing account
            </Link>
          </p>
        </div>

        {showSuccess && (
          <div className="rounded-md bg-green-50 p-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-green-800">
                  Registration successful!
                </h3>
                <div className="mt-2 text-sm text-green-700">
                  <p>
                    Please check your email to verify your account.
                    Redirecting to login...
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        <RegisterForm
          onSuccess={handleSuccess}
          onError={handleError}
          showPasswordStrength={true}
          requireEmailVerification={true}
          className="mt-8 space-y-6"
          submitButtonText="Create account"
          submitButtonClassName="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        />

        <div className="text-sm text-center text-gray-600">
          By creating an account, you agree to our{' '}
          <a href="/terms" className="text-indigo-600 hover:text-indigo-500">
            Terms of Service
          </a>{' '}
          and{' '}
          <a href="/privacy" className="text-indigo-600 hover:text-indigo-500">
            Privacy Policy
          </a>
        </div>
      </div>
    </div>
  )
}