import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { AutoLogout } from '../components/AutoLogout'
import { VertigoLogo } from '../components/AstronautLogo'
import '../styles.css'

export function App() {
  const { isAuthenticated, isLoading, user, logout } = useAuth()
  
  if (isLoading) {
    return (
      <div className="layout" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #F3F0FF 0%, #FDF2F8 100%)'
      }}>
        <div style={{ 
          textAlign: 'center',
          background: 'white',
          padding: '40px',
          borderRadius: '16px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
          maxWidth: '400px'
        }}>
          <div style={{
            display: 'inline-block',
            width: '48px',
            height: '48px',
            border: '4px solid rgba(139, 92, 246, 0.2)',
            borderTopColor: '#8B5CF6',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
            marginBottom: '16px'
          }} />
          <div style={{ 
            fontSize: '18px', 
            color: '#6B7280',
            fontWeight: '500',
            marginBottom: '8px'
          }}>
            Validazione sessione in corso...
          </div>
          <div style={{ 
            fontSize: '14px', 
            color: '#9CA3AF'
          }}>
            Attendere prego
          </div>
          <style>{`
            @keyframes spin {
              to { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      </div>
    )
  }
  
  if (!isAuthenticated) {
    return (
      <div className="layout">
        <div className="content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '24px', marginBottom: '8px' }}>🔒</div>
            <div>Session expired. Please login again.</div>
            <button 
              onClick={() => window.location.href = '/'}
              style={{ 
                marginTop: '16px', 
                padding: '8px 16px', 
                backgroundColor: '#007bff', 
                color: 'white', 
                border: 'none', 
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Go to Login
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <AutoLogout>
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
            <Link to="/app/setup-colloqui">
              <span style={{ fontSize: '18px' }}>⚙️</span>
              Setup Colloqui
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
            {user && (
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
                  📧 {user.email}
                </div>
                <div style={{
                  fontSize: '12px',
                  color: 'var(--text-secondary)'
                }}>
                  🏢 {user.company}
                </div>
              </div>
            )}
            <button
              onClick={logout}
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
    </AutoLogout>
  )
}