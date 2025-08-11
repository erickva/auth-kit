import { useAuth } from '@auth-kit/react'

export default function DashboardPage() {
  const { user } = useAuth()

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            Dashboard
          </h1>
          
          <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6">
            <div className="flex">
              <div className="ml-3">
                <p className="text-sm text-blue-700">
                  Welcome back, {user?.firstName || user?.email}! You are successfully authenticated.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div className="bg-white overflow-hidden shadow rounded-lg border">
              <div className="px-4 py-5 sm:p-6">
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Account Status
                </dt>
                <dd className="mt-1 text-3xl font-semibold text-gray-900">
                  Active
                </dd>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg border">
              <div className="px-4 py-5 sm:p-6">
                <dt className="text-sm font-medium text-gray-500 truncate">
                  Email Verified
                </dt>
                <dd className="mt-1 text-3xl font-semibold text-gray-900">
                  {user?.isVerified ? 'Yes' : 'No'}
                </dd>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg border">
              <div className="px-4 py-5 sm:p-6">
                <dt className="text-sm font-medium text-gray-500 truncate">
                  2FA Enabled
                </dt>
                <dd className="mt-1 text-3xl font-semibold text-gray-900">
                  {user?.twoFactorEnabled ? 'Yes' : 'No'}
                </dd>
              </div>
            </div>
          </div>

          <div className="mt-8">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Quick Actions
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <a
                href="/profile"
                className="relative rounded-lg border border-gray-300 bg-white px-6 py-5 shadow-sm flex items-center space-x-3 hover:border-gray-400 focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-indigo-500"
              >
                <div className="flex-1 min-w-0">
                  <span className="absolute inset-0" aria-hidden="true" />
                  <p className="text-sm font-medium text-gray-900">
                    Update Profile
                  </p>
                  <p className="text-sm text-gray-500">
                    Manage your personal information
                  </p>
                </div>
              </a>

              <a
                href="/settings"
                className="relative rounded-lg border border-gray-300 bg-white px-6 py-5 shadow-sm flex items-center space-x-3 hover:border-gray-400 focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-indigo-500"
              >
                <div className="flex-1 min-w-0">
                  <span className="absolute inset-0" aria-hidden="true" />
                  <p className="text-sm font-medium text-gray-900">
                    Security Settings
                  </p>
                  <p className="text-sm text-gray-500">
                    Configure authentication options
                  </p>
                </div>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}