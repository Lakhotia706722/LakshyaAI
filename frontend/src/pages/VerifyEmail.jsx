import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'

export default function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const [status, setStatus] = useState('loading') // loading | success | error

  useEffect(() => {
    if (!token) {
      setStatus('error')
      return
    }
    api.get(`/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then(() => setStatus('success'))
      .catch(() => setStatus('error'))
  }, [token])

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-600 to-primary-800 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl p-8 w-full max-w-md text-center">
        {status === 'loading' && (
          <>
            <div className="text-4xl mb-4 animate-pulse">🔄</div>
            <p className="text-gray-600">Verifying your email...</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="text-5xl mb-4">✅</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Email Verified</h2>
            <p className="text-gray-600 mb-6">Your account is now active. You can sign in.</p>
            <Link
              to="/login"
              className="inline-block bg-primary-600 text-white py-2 px-6 rounded-lg hover:bg-primary-700 transition-colors"
            >
              Sign In
            </Link>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="text-5xl mb-4">❌</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Verification Failed</h2>
            <p className="text-gray-600 mb-6">
              This link is invalid or has already been used. You can request a new one after signing in.
            </p>
            <Link
              to="/login"
              className="inline-block bg-primary-600 text-white py-2 px-6 rounded-lg hover:bg-primary-700 transition-colors"
            >
              Back to Login
            </Link>
          </>
        )}
      </div>
    </div>
  )
}
