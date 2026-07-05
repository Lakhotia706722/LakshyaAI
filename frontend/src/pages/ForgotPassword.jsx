import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      await api.post('/auth/forgot-password', { email })
    } catch {
      // Always show success — prevents email enumeration
    } finally {
      setIsLoading(false)
      setSubmitted(true)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-600 to-primary-800 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Reset Password</h1>
          <p className="text-gray-500 mt-1 text-sm">
            {submitted
              ? 'Check your inbox for the reset link.'
              : "Enter your email and we'll send a reset link."}
          </p>
        </div>

        {submitted ? (
          <div className="text-center">
            <div className="text-5xl mb-4">📬</div>
            <p className="text-gray-600 mb-6 text-sm">
              If that email is registered, a reset link has been sent. Check your spam folder too.
            </p>
            <Link
              to="/login"
              className="inline-block bg-primary-600 text-white py-2 px-6 rounded-lg hover:bg-primary-700 transition-colors text-sm"
            >
              Back to Login
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="you@company.com"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-primary-600 text-white py-2 px-4 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Sending...' : 'Send Reset Link'}
            </button>

            <p className="text-center text-sm text-gray-500">
              <Link to="/login" className="text-primary-600 hover:text-primary-700">
                Back to Login
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}
