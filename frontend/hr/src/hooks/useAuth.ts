import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

const API_BASE = (import.meta as any).env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'

interface UserInfo {
  email: string
  company: string
  role: string
}

interface AuthState {
  isAuthenticated: boolean
  isLoading: boolean
  user: UserInfo | null
  token: string | null
}

export function useAuth() {
  const navigate = useNavigate()
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    user: null,
    token: null
  })

  // Function to decode JWT token
  const decodeJWT = useCallback((token: string) => {
    try {
      const base64Url = token.split('.')[1]
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
      const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
      }).join(''))
      return JSON.parse(jsonPayload)
    } catch (error) {
      return null
    }
  }, [])

  // Function to check if token is expired
  const isTokenExpired = useCallback((token: string) => {
    const decoded = decodeJWT(token)
    if (!decoded || !decoded.exp) return true
    return Date.now() >= decoded.exp * 1000
  }, [decodeJWT])

  // Function to refresh token
  const refreshToken = useCallback(async (token: string) => {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data = await response.json()
        if (data.refreshed && data.token) {
          localStorage.setItem('hr_jwt', data.token)
          return data.token
        }
      }
    } catch (error) {
      console.error('Error refreshing token:', error)
    }
    return null
  }, [])

  // Function to validate token and get user info
  const validateToken = useCallback(async (token: string) => {
    try {
      const response = await fetch(`${API_BASE}/user/info`, {
        headers: { Authorization: `Bearer ${token}` }
      })

      if (response.status === 401) {
        // Token is invalid or expired
        return { valid: false, user: null }
      }

      if (response.ok) {
        const userData = await response.json()
        return { valid: true, user: userData }
      }

      return { valid: false, user: null }
    } catch (error) {
      console.error('Error validating token:', error)
      return { valid: false, user: null }
    }
  }, [])

  // Function to logout
  const logout = useCallback(() => {
    localStorage.removeItem('hr_jwt')
    setAuthState({
      isAuthenticated: false,
      isLoading: false,
      user: null,
      token: null
    })
    navigate('/')
  }, [navigate])

  // Function to check authentication status
  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem('hr_jwt')
    
    if (!token) {
      setAuthState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        token: null
      })
      return
    }

    // Check if token is expired
    if (isTokenExpired(token)) {
      console.log('Token expired, logging out')
      logout()
      return
    }

    // Try to validate token
    const validation = await validateToken(token)
    
    if (validation.valid && validation.user) {
      setAuthState({
        isAuthenticated: true,
        isLoading: false,
        user: validation.user,
        token: token
      })
    } else {
      // Try to refresh token if validation failed
      const newToken = await refreshToken(token)
      if (newToken) {
        const newValidation = await validateToken(newToken)
        if (newValidation.valid && newValidation.user) {
          setAuthState({
            isAuthenticated: true,
            isLoading: false,
            user: newValidation.user,
            token: newToken
          })
        } else {
          logout()
        }
      } else {
        logout()
      }
    }
  }, [isTokenExpired, validateToken, refreshToken, logout])

  // Function to make authenticated requests with automatic token refresh
  const authenticatedFetch = useCallback(async (url: string, options: RequestInit = {}) => {
    let token = authState.token || localStorage.getItem('hr_jwt')
    
    if (!token) {
      logout()
      throw new Error('No authentication token')
    }

    // Check if token is close to expiration (less than 5 minutes)
    const decoded = decodeJWT(token)
    if (decoded && decoded.exp) {
      const timeLeft = (decoded.exp * 1000) - Date.now()
      if (timeLeft < 5 * 60 * 1000 && timeLeft > 0) {
        // Try to refresh token
        const newToken = await refreshToken(token)
        if (newToken) {
          token = newToken
          setAuthState(prev => ({ ...prev, token: newToken }))
        }
      }
    }

    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.status === 401) {
      logout()
      throw new Error('Authentication failed')
    }

    return response
  }, [authState.token, decodeJWT, refreshToken, logout])

  // Set up automatic token refresh every 5 minutes
  useEffect(() => {
    if (!authState.isAuthenticated) return

    const interval = setInterval(async () => {
      const token = localStorage.getItem('hr_jwt')
      if (token && !isTokenExpired(token)) {
        const newToken = await refreshToken(token)
        if (newToken) {
          setAuthState(prev => ({ ...prev, token: newToken }))
        }
      }
    }, 5 * 60 * 1000) // Check every 5 minutes

    return () => clearInterval(interval)
  }, [authState.isAuthenticated, isTokenExpired, refreshToken])

  // Set up automatic logout when token expires
  useEffect(() => {
    if (!authState.isAuthenticated || !authState.token) return

    const decoded = decodeJWT(authState.token)
    if (decoded && decoded.exp) {
      const timeUntilExpiry = (decoded.exp * 1000) - Date.now()
      
      if (timeUntilExpiry > 0) {
        const timeout = setTimeout(() => {
          console.log('Token expired, logging out automatically')
          logout()
        }, timeUntilExpiry)

        return () => clearTimeout(timeout)
      }
    }
  }, [authState.isAuthenticated, authState.token, decodeJWT, logout])

  // Initialize authentication on mount
  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  return {
    ...authState,
    logout,
    authenticatedFetch,
    checkAuth
  }
}
