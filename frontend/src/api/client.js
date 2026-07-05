import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api'

export const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ─────────────────────────────────────────────────────────────
// Token storage helpers (access token in memory, refresh in
// localStorage — trade-off: simpler than httpOnly cookie for now)
// ─────────────────────────────────────────────────────────────

let _accessToken = null

export function setTokens(accessToken, refreshToken) {
  _accessToken = accessToken
  if (refreshToken) {
    localStorage.setItem('refresh_token', refreshToken)
  }
}

export function clearTokens() {
  _accessToken = null
  localStorage.removeItem('refresh_token')
}

export function getAccessToken() {
  return _accessToken
}

// ─────────────────────────────────────────────────────────────
// Request interceptor — attach access token
// ─────────────────────────────────────────────────────────────

api.interceptors.request.use(
  (config) => {
    const token = _accessToken
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ─────────────────────────────────────────────────────────────
// Response interceptor — silent token refresh on 401
// ─────────────────────────────────────────────────────────────

let _isRefreshing = false
let _failedQueue = []

function _processQueue(error, token = null) {
  _failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  _failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem('refresh_token')

      if (!refreshToken) {
        clearTokens()
        window.location.href = '/login'
        return Promise.reject(error)
      }

      if (_isRefreshing) {
        // Queue requests that arrive while a refresh is in flight
        return new Promise((resolve, reject) => {
          _failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      _isRefreshing = true

      try {
        const response = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        })
        const { access_token, refresh_token: newRefresh } = response.data
        setTokens(access_token, newRefresh)
        _processQueue(null, access_token)
        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return api(originalRequest)
      } catch (refreshError) {
        _processQueue(refreshError, null)
        clearTokens()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      } finally {
        _isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)
