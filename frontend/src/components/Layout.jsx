import { Link, useLocation } from 'react-router-dom'

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

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-primary-800 text-white flex flex-col">
        <div className="p-6">
          <h1 className="text-2xl font-bold">LAKSHYA AI</h1>
          <p className="text-xs text-primary-200 mt-1">Revenue Intelligence</p>
        </div>
        
        <nav className="flex-1 px-3">
          {navigation.map((item) => {
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-4 py-3 mb-2 rounded-lg transition-colors ${
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
        
        <div className="p-4 border-t border-primary-700">
          <div className="flex items-center">
            <div className="flex-1">
              <p className="text-sm font-medium">{user?.name}</p>
              <p className="text-xs text-primary-200">{user?.email}</p>
            </div>
            <button
              onClick={onLogout}
              className="text-primary-200 hover:text-white text-sm"
              title="Logout"
            >
              🚪
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="bg-white shadow-sm">
          <div className="px-6 py-4">
            <h2 className="text-xl font-semibold text-gray-800">
              {navigation.find(item => item.path === location.pathname)?.name || 'Dashboard'}
            </h2>
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
