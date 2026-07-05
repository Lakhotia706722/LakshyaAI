import { Link, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { api } from '../api/client'

const navigation = [
  { name: 'Dashboard', path: '/', icon: '📊' },
  { name: 'Deals', path: '/deals', icon: '🤝' },
  { name: 'WhatsApp Intelligence', path: '/whatsapp-intelligence', icon: '💬' },
  { name: 'Call Intelligence', path: '/call-intelligence', icon: '📞' },
  { name: 'Company Graph', path: '/company-graph', icon: '🏢' },
  { name: 'Forecasting', path: '/forecasting', icon: '📈' },
]

export default function Layout({ children, user, onLogout }) {
  const location = useLocation()
  const [apiStatus, setApiStatus] = useState(null)
  const [org, setOrg] = useState(null)

  useEffect(() => {
    api.get('/status').then(r => setApiStatus(r.data)).catch(() => {})
    api.get('/org').then(r => setOrg(r.data)).catch(() => {})
  }, [])

  const currentPage = navigation.find(item =>
    item.path === location.pathname ||
    (item.path !== '/' && location.pathname.startsWith(item.path))
  )

  const showEmailWarning = user && user.is_email_verified === false

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-primary-800 text-white flex flex-col shrink-0">
        <div className="p-6">
          <h1 className="text-2xl font-bold tracking-tight">LAKSHYA AI</h1>
          <p className="text-xs text-primary-200 mt-1">Revenue Intelligence</p>
        </div>

        <nav className="flex-1 px-3 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = location.pathname === item.path ||
              (item.path !== '/' && location.pathname.startsWith(item.path))
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-4 py-3 mb-1 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-primary-600 text-white'
                    : 'text-primary-100 hover:bg-primary-700'
                }`}
              >
                <span className="text-xl mr-3">{item.icon}</span>
                <span className="text-sm font-medium">{item.name}</span>
              </Link>
            )
          })}
        </nav>

        {/* User / Org info */}
        <div className="p-4 border-t border-primary-700 shrink-0">
          {org && (
            <p className="text-xs text-primary-300 mb-2 truncate">
              🏢 {org.name}
            </p>
          )}
          <div className="flex items-center">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-primary-200 truncate">{user?.email}</p>
            </div>
            <button
              onClick={onLogout}
              className="text-primary-200 hover:text-white text-sm ml-2 shrink-0"
              title="Logout"
            >
              🚪
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Email verification warning */}
        {showEmailWarning && (
          <div className="bg-amber-50 border-b border-amber-200 px-6 py-2 flex items-center gap-2 text-sm text-amber-800">
            <span>⚠️</span>
            <span>
              Your email address is not verified. Check your inbox for a verification link.
            </span>
          </div>
        )}

        {/* Top Bar */}
        <header className="bg-white shadow-sm shrink-0">
          <div className="px-6 py-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-800">
              {currentPage?.name || 'Dashboard'}
            </h2>
            <div className="flex items-center gap-3">
              {apiStatus && !apiStatus.anthropic_configured && (
                <span className="text-xs bg-orange-100 text-orange-700 border border-orange-200 px-3 py-1 rounded-full">
                  ⚠️ Add ANTHROPIC_API_KEY to enable AI
                </span>
              )}
              {apiStatus && !apiStatus.openai_configured && (
                <span className="text-xs bg-orange-100 text-orange-700 border border-orange-200 px-3 py-1 rounded-full">
                  ⚠️ Add OPENAI_API_KEY to enable transcription
                </span>
              )}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
