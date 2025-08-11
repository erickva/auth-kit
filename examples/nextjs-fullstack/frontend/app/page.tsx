import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between text-sm">
        <h1 className="text-4xl font-bold text-center mb-8">
          Welcome to Auth Kit Example
        </h1>
        
        <p className="text-center text-gray-600 mb-12">
          This example demonstrates a full-featured authentication system with Next.js and FastAPI
        </p>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-md mx-auto">
          <Link
            href="/login"
            className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100"
          >
            <h2 className="mb-3 text-2xl font-semibold">
              Login{' '}
              <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
                →
              </span>
            </h2>
            <p className="m-0 max-w-[30ch] text-sm opacity-50">
              Sign in to your account with email or passkey
            </p>
          </Link>
          
          <Link
            href="/signup"
            className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100"
          >
            <h2 className="mb-3 text-2xl font-semibold">
              Sign Up{' '}
              <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
                →
              </span>
            </h2>
            <p className="m-0 max-w-[30ch] text-sm opacity-50">
              Create a new account in seconds
            </p>
          </Link>
        </div>
        
        <div className="mt-16 text-center">
          <h3 className="text-lg font-semibold mb-4">Features Included:</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm text-gray-600">
            <div>✅ Email/Password</div>
            <div>🔑 Passkeys</div>
            <div>🔐 Two-Factor Auth</div>
            <div>📧 Email Verification</div>
            <div>🔄 Password Reset</div>
            <div>👤 User Profile</div>
            <div>🎨 Themed UI</div>
            <div>🌍 i18n Ready</div>
          </div>
        </div>
      </div>
    </div>
  );
}