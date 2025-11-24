import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { AutoLogout } from '../components/AutoLogout'
import { VertigoLogo } from '../components/AstronautLogo'
import { LayoutDashboard, FileText, Settings, Users, Plus, BarChart3, LogOut, Building2, Mail, TrendingUp, MessageSquare } from 'lucide-react'
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
            <Link to="/app/dashboard" className="nav-link">
              <LayoutDashboard size={20} />
              Dashboard
            </Link>
            <Link to="/app/positions" className="nav-link">
              <FileText size={20} />
              Annunci
            </Link>
            <Link to="/app/candidati" className="nav-link">
              <BarChart3 size={20} />
              Reportistica Candidati
            </Link>
            <Link to="/app/nuova-sessione" className="nav-link">
              <Plus size={20} />
              Nuova Sessione
            </Link>
            <Link to="/app/benchmark" className="nav-link">
              <TrendingUp size={20} />
              Benchmark
            </Link>
            <Link to="/app/whatsapp-setup" className="nav-link">
              <MessageSquare size={20} />
              WhatsApp Screener
            </Link>
            <Link to="/app/users" className="nav-link">
              <Users size={20} />
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
                alignItems: 'center',
                gap: '12px'
              }}>
                <div style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '12px',
                  background: 'linear-gradient(135deg, #7C3AED 0%, #EC4899 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontWeight: '600',
                  fontSize: '16px',
                  flexShrink: 0
                }}>
                  {user.email[0].toUpperCase()}
                </div>
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  flex: 1,
                  minWidth: 0
                }}>
                  <div style={{
                    fontSize: '14px',
                    fontWeight: '600',
                    color: 'var(--text-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}>
                    <Mail size={14} style={{ flexShrink: 0 }} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{user.email}</span>
                  </div>
                  <div style={{
                    fontSize: '12px',
                    color: 'var(--text-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}>
                    <Building2 size={14} style={{ flexShrink: 0 }} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{user.company}</span>
                  </div>
                </div>
              </div>
            )}
            <button
              onClick={logout}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 18px',
                background: 'linear-gradient(135deg, #ef4444, #dc2626)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--radius-lg)',
                fontSize: '14px',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: '0 2px 8px rgba(239, 68, 68, 0.2)'
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.transform = 'translateY(-1px)'
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(239, 68, 68, 0.3)'
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = '0 2px 8px rgba(239, 68, 68, 0.2)'
              }}
            >
              <LogOut size={18} />
              Logout
            </button>
          </header>
          <Outlet />
        </main>
      </div>
    </AutoLogout>
  )
}