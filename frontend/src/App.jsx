import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import VerifyEmail from './pages/VerifyEmail'
import Dashboard from './pages/Dashboard'
import Deals from './pages/Deals'
import Companies from './pages/Companies'
import WhatsAppIntelligence from './pages/WhatsAppIntelligence'
import CallIntelligence from './pages/CallIntelligence'
import CompanyGraph from './pages/CompanyGraph'
import Forecasting from './pages/Forecasting'
import { api, setTokens, clearTokens } from './api/client'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [user, setUser] = useState(null)

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    // On load, try to restore session via refresh token
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      try {
        const response = await api.post('/auth/refresh', { refresh_token: refreshToken })
        const { access_token, refresh_token: newRefresh } = response.data
        setTokens(access_token, newRefresh)

        const userResponse = await api.get('/auth/me')
        setUser(userResponse.data)
        setIsAuthenticated(true)
      } catch {
        clearTokens()
        setIsAuthenticated(false)
      }
    }
    setIsLoading(false)
  }

  const handleLogin = (accessToken, refreshToken, userData) => {
    setTokens(accessToken, refreshToken)
    setUser(userData)
    setIsAuthenticated(true)
  }

  const handleLogout = async () => {
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      try {
        await api.post('/auth/logout', { refresh_token: refreshToken })
      } catch {
        // Best-effort — clear locally even if server call fails
      }
    }
    clearTokens()
    setUser(null)
    setIsAuthenticated(false)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl text-gray-500">Loading...</div>
      </div>
    )
  }

  return (
    <Router>
      <Routes>
        {/* Public routes */}
        <Route
          path="/login"
          element={isAuthenticated ? <Navigate to="/" replace /> : <Login onLogin={handleLogin} />}
        />
        <Route
          path="/register"
          element={isAuthenticated ? <Navigate to="/" replace /> : <Register />}
        />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />

        {/* Protected routes */}
        <Route
          path="/*"
          element={
            isAuthenticated ? (
              <Layout user={user} onLogout={handleLogout}>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/deals" element={<Deals />} />
                  <Route path="/companies" element={<Companies />} />
                  <Route path="/whatsapp-intelligence" element={<WhatsAppIntelligence />} />
                  <Route path="/call-intelligence" element={<CallIntelligence />} />
                  <Route path="/company-graph" element={<CompanyGraph />} />
                  <Route path="/forecasting" element={<Forecasting />} />
                </Routes>
              </Layout>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
      </Routes>
    </Router>
  )
}

export default App
