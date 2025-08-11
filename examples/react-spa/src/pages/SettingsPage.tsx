import { useState } from 'react'
import { useAuth, usePasskey, use2FA, PasskeyList, TwoFactorSetup } from '@auth-kit/react'

export default function SettingsPage() {
  const { user } = useAuth()
  const { passkeys } = usePasskey()
  const { status: twoFactorStatus } = use2FA()
  const [activeSection, setActiveSection] = useState('security')
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const handleSuccess = (message: string) => {
    setMessage({ type: 'success', text: message })
    setTimeout(() => setMessage(null), 3000)
  }

  const handleError = (error: Error) => {
    setMessage({ type: 'error', text: error.message })
    setTimeout(() => setMessage(null), 5000)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-6">
            Security Settings
          </h1>

          {message && (
            <div className={`rounded-md p-4 mb-6 ${
              message.type === 'success' ? 'bg-green-50' : 'bg-red-50'
            }`}>
              <p className={`text-sm font-medium ${
                message.type === 'success' ? 'text-green-800' : 'text-red-800'
              }`}>
                {message.text}
              </p>
            </div>
          )}

          {/* Two-Factor Authentication Section */}
          <div className="mb-8">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Two-Factor Authentication
            </h2>
            <p className="text-sm text-gray-600 mb-4">
              Add an extra layer of security to your account by enabling two-factor authentication.
            </p>
            
            {twoFactorStatus.enabled ? (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-green-800">
                      Two-factor authentication is enabled
                    </h3>
                    <div className="mt-2 text-sm text-green-700">
                      <p>
                        Your account is protected with two-factor authentication.
                        {twoFactorStatus.backup_codes_remaining && (
                          <span className="block mt-1">
                            Recovery codes remaining: {twoFactorStatus.backup_codes_remaining}
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <TwoFactorSetup
                onSuccess={() => handleSuccess('Two-factor authentication enabled successfully!')}
                onError={handleError}
              />
            )}
          </div>

          <hr className="my-8" />

          {/* Passkeys Section */}
          <div>
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Passkeys
            </h2>
            <p className="text-sm text-gray-600 mb-4">
              Passkeys are a safer and easier alternative to passwords. They let you sign in with your fingerprint, face, or device lock.
            </p>
            
            <PasskeyList
              passkeys={passkeys}
              onRegisterSuccess={() => handleSuccess('Passkey registered successfully!')}
              onDeleteSuccess={() => handleSuccess('Passkey deleted successfully!')}
              onError={handleError}
              showRegisterButton={true}
              className="space-y-4"
            />
          </div>

          <hr className="my-8" />

          {/* Sessions Section */}
          <div>
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Active Sessions
            </h2>
            <p className="text-sm text-gray-600 mb-4">
              Manage and monitor active sessions across your devices.
            </p>
            
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-yellow-800">
                    Session management coming soon
                  </h3>
                  <div className="mt-2 text-sm text-yellow-700">
                    <p>
                      You'll soon be able to view and manage all active sessions.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}