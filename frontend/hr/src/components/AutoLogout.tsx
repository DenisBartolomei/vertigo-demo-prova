import { useEffect, useState } from 'react'
import { useAuth } from '../hooks/useAuth'

interface AutoLogoutProps {
  children: React.ReactNode
}

export function AutoLogout({ children }: AutoLogoutProps) {
  const { isAuthenticated, user, logout } = useAuth()
  const [showWarning, setShowWarning] = useState(false)
  const [timeLeft, setTimeLeft] = useState(0)

  useEffect(() => {
    if (!isAuthenticated) return

    const token = localStorage.getItem('hr_jwt')
    if (!token) return

    // Decode JWT to get expiration time
    try {
      const base64Url = token.split('.')[1]
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
      const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
      }).join(''))
      const decoded = JSON.parse(jsonPayload)
      
      if (decoded.exp) {
        const expirationTime = decoded.exp * 1000
        const now = Date.now()
        const timeUntilExpiry = expirationTime - now

        if (timeUntilExpiry > 0) {
          // Show warning 5 minutes before expiry
          const warningTime = 5 * 60 * 1000 // 5 minutes
          const warningTimeout = timeUntilExpiry - warningTime

          if (warningTimeout > 0) {
            const warningTimer = setTimeout(() => {
              setShowWarning(true)
              setTimeLeft(Math.floor(warningTime / 1000))
            }, warningTimeout)

            // Update countdown every second
            const countdownInterval = setInterval(() => {
              const remaining = Math.max(0, Math.floor((expirationTime - Date.now()) / 1000))
              setTimeLeft(remaining)
              
              if (remaining <= 0) {
                clearInterval(countdownInterval)
                setShowWarning(false)
              }
            }, 1000)

            return () => {
              clearTimeout(warningTimer)
              clearInterval(countdownInterval)
            }
          } else {
            // Token expires soon, show warning immediately
            setShowWarning(true)
            setTimeLeft(Math.floor(timeUntilExpiry / 1000))
            
            const countdownInterval = setInterval(() => {
              const remaining = Math.max(0, Math.floor((expirationTime - Date.now()) / 1000))
              setTimeLeft(remaining)
              
              if (remaining <= 0) {
                clearInterval(countdownInterval)
                setShowWarning(false)
              }
            }, 1000)

            return () => clearInterval(countdownInterval)
          }
        }
      }
    } catch (error) {
      console.error('Error decoding JWT:', error)
    }
  }, [isAuthenticated])

  const handleExtendSession = async () => {
    try {
      const token = localStorage.getItem('hr_jwt')
      if (!token) return

      const response = await fetch(`${import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'}/auth/refresh`, {
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
          setShowWarning(false)
          setTimeLeft(0)
        }
      }
    } catch (error) {
      console.error('Error extending session:', error)
    }
  }

  const handleLogout = () => {
    setShowWarning(false)
    logout()
  }

  return (
    <>
      {children}
      
      {showWarning && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '32px',
            borderRadius: '12px',
            maxWidth: '400px',
            textAlign: 'center',
            boxShadow: '0 20px 40px rgba(0, 0, 0, 0.3)'
          }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏰</div>
            <h2 style={{ margin: '0 0 16px 0', color: '#333' }}>Sessione in scadenza</h2>
            <p style={{ margin: '0 0 24px 0', color: '#666', lineHeight: '1.5' }}>
              La tua sessione scadrà tra <strong>{timeLeft} secondi</strong>.
              <br />
              Vuoi estendere la sessione o effettuare il logout?
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                onClick={handleExtendSession}
                style={{
                  backgroundColor: '#007bff',
                  color: 'white',
                  border: 'none',
                  padding: '12px 24px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '16px',
                  fontWeight: '500'
                }}
              >
                Estendi Sessione
              </button>
              <button
                onClick={handleLogout}
                style={{
                  backgroundColor: '#dc3545',
                  color: 'white',
                  border: 'none',
                  padding: '12px 24px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '16px',
                  fontWeight: '500'
                }}
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
