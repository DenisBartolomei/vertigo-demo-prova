import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { VertigoLogo } from '../components/AstronautLogo'
import '../styles.css'

const API_BASE = (import.meta as any).env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'


function decodeJWT(token: string) {
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
}

export function App() {
  const navigate = useNavigate()
  const [tokenValid, setTokenValid] = useState<boolean | null>(null)
  const [userInfo, setUserInfo] = useState<{email: string, company: string} | null>(null)
  
  useEffect(() => {
    const token = localStorage.getItem('hr_jwt')
    if (!token) {
      navigate('/')
      return
    }
    
    // Validate token and fetch user info in one request
    fetch(`${API_BASE}/user/info`, { 
      headers: { Authorization: `Bearer ${token}` }
    })
    .then(res => {
      if (res.status === 401) {
        localStorage.removeItem('hr_jwt')
        navigate('/')
        return
      } else if (res.ok) {
        setTokenValid(true)
        return res.json()
      } else {
        setTokenValid(false)
        throw new Error('Token validation failed')
      }
    })
    .then(data => {
      if (data) {
        setUserInfo({
          email: data.email || 'Unknown',
          company: data.company || 'Unknown Company'
        })
      }
    })
    .catch(() => {
      // Fallback to JWT decoding if API fails
      const decoded = decodeJWT(token)
      if (decoded) {
        setUserInfo({
          email: decoded.sub || 'Unknown',
          company: 'Unknown Company'
        })
        setTokenValid(true)
      } else {
        setTokenValid(false)
      }
    })
  }, [navigate])
  
  if (tokenValid === null) {
    return (
      <div className="layout">
        <div className="content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '24px', marginBottom: '8px' }}>⏳</div>
            <div>Validating session...</div>
          </div>
        </div>
      </div>
    )
  }
  
  if (tokenValid === false) {
    return (
      <div className="layout">
        <div className="content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '24px', marginBottom: '8px' }}>⚠️</div>
            <div>Sessione scaduta. Reindirizzamento al login...</div>
          </div>
        </div>
      </div>
    )
  }

  const handleLogout = () => {
    localStorage.removeItem('hr_jwt')
    window.location.href = '/'
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <h3 style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          marginBottom: '0px'
        }}>
          <VertigoLogo 
            height="100px"
            width="auto"
            maxWidth="600px"
          />
        </h3>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Link to="/app/dashboard">
            <span style={{ fontSize: '18px' }}>📊</span>
            Dashboard
          </Link>
          <Link to="/app/positions">
            <span style={{ fontSize: '18px' }}>📋</span>
            Annunci
          </Link>
          <Link to="/app/candidati">
            <span style={{ fontSize: '18px' }}>📈</span>
            Reportistica Candidati
          </Link>
          <Link to="/app/nuova-sessione">
            <span style={{ fontSize: '18px' }}>➕</span>
            Nuova Sessione
          </Link>
          <Link to="/app/users">
            <span style={{ fontSize: '18px' }}>👥</span>
            Gestione Utenti
          </Link>
        </nav>
      </aside>
      <main className="content">
        {/* Header with user info and logout button */}
        <header style={{
          position: 'sticky',
          top: 0,
          zIndex: 100,
          background: 'white',
          borderBottom: '1px solid var(--border-light)',
          padding: '12px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          {userInfo && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '4px'
            }}>
              <div style={{
                fontSize: '14px',
                fontWeight: '600',
                color: 'var(--text-primary)'
              }}>
                📧 {userInfo.email}
              </div>
              <div style={{
                fontSize: '12px',
                color: 'var(--text-secondary)'
              }}>
                🏢 {userInfo.company}
              </div>
            </div>
          )}
          <button
            onClick={handleLogout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              background: 'linear-gradient(135deg, #ef4444, #dc2626)',
              color: 'white',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              boxShadow: '0 2px 4px rgba(239, 68, 68, 0.2)'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-1px)'
              e.currentTarget.style.boxShadow = '0 4px 8px rgba(239, 68, 68, 0.3)'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = '0 2px 4px rgba(239, 68, 68, 0.2)'
            }}
          >
            <span style={{ fontSize: '16px' }}>🚪</span>
            Logout
          </button>
        </header>
        <Outlet />
      </main>
    </div>
  )
}


