import { useState } from 'react'
import { useAuth, UpdateProfileForm, ChangePasswordForm } from '@auth-kit/react'

export default function ProfilePage() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState('profile')
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const handleProfileSuccess = () => {
    setMessage({ type: 'success', text: 'Profile updated successfully!' })
    setTimeout(() => setMessage(null), 3000)
  }

  const handlePasswordSuccess = () => {
    setMessage({ type: 'success', text: 'Password changed successfully!' })
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
            Account Settings
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

          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('profile')}
                className={`${
                  activeTab === 'profile'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                Profile Information
              </button>
              <button
                onClick={() => setActiveTab('password')}
                className={`${
                  activeTab === 'password'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                Change Password
              </button>
            </nav>
          </div>

          <div className="mt-6">
            {activeTab === 'profile' && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Profile Information
                </h3>
                <p className="text-sm text-gray-600 mb-6">
                  Update your account's profile information and email address.
                </p>
                
                <UpdateProfileForm
                  initialValues={{
                    email: user?.email || '',
                    firstName: user?.firstName || '',
                    lastName: user?.lastName || '',
                    phoneNumber: user?.phoneNumber || ''
                  }}
                  onSuccess={handleProfileSuccess}
                  onError={handleError}
                  className="space-y-6"
                  submitButtonText="Save Changes"
                  submitButtonClassName="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                />
              </div>
            )}

            {activeTab === 'password' && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Change Password
                </h3>
                <p className="text-sm text-gray-600 mb-6">
                  Ensure your account is using a long, random password to stay secure.
                </p>
                
                <ChangePasswordForm
                  onSuccess={handlePasswordSuccess}
                  onError={handleError}
                  showPasswordStrength={true}
                  className="space-y-6 max-w-lg"
                  submitButtonText="Update Password"
                  submitButtonClassName="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}