import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const API_BASE = (import.meta as any).env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'

export function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const navigate = useNavigate()

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setIsLoading(true)
    
    try {
      const resp = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      
      if (!resp.ok) {
        setError('Credenziali non valide')
        setIsLoading(false)
        return
      }
      
      const data = await resp.json()
      localStorage.setItem('hr_jwt', data.token)
      
      // Reindirizza alla dashboard (la route esiste ora)
      window.location.href = '/app/dashboard'
    } catch (err) {
      setError('Errore durante l\'accesso. Riprova.')
      setIsLoading(false)
    }
  }

  return (
    <div style={{ 
      display: 'grid', 
      placeItems: 'center', 
      minHeight: '100vh',
      padding: '20px'
    }}>
      <div className="card" style={{ 
        width: '100%', 
        maxWidth: '400px',
        textAlign: 'center',
        background: 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(139, 92, 246, 0.2)'
      }}>
        <div style={{ marginBottom: '32px', textAlign: 'center' }}>
          <h1 style={{ 
            fontSize: '36px',
            fontWeight: '700',
            background: 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            margin: '0 0 8px 0'
          }}>
            Vertigo AI
          </h1>
          <div style={{ 
            fontSize: '16px', 
            color: 'var(--text-secondary)',
            fontWeight: '500'
          }}>
            Dashboard HR
          </div>
        </div>
        
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: '20px' }}>
          <div>
            <input 
              placeholder="Indirizzo email" 
              value={email} 
              onChange={e => setEmail(e.target.value)}
              style={{ marginBottom: '4px' }}
            />
          </div>
          <div>
            <input 
              placeholder="Password" 
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)}
              style={{ marginBottom: '4px' }}
            />
          </div>
          {error && (
            <div style={{ 
              color: '#EF4444',
              background: '#FEE2E2',
              padding: '12px',
              borderRadius: 'var(--radius-md)',
              fontSize: '14px'
            }}>
              {error}
            </div>
          )}
          <button 
            type="submit" 
            disabled={isLoading}
            style={{ 
              width: '100%', 
              justifyContent: 'center',
              opacity: isLoading ? 0.6 : 1,
              cursor: isLoading ? 'wait' : 'pointer',
              position: 'relative'
            }}
          >
            {isLoading ? (
              <>
                <span style={{ 
                  display: 'inline-block',
                  width: '16px',
                  height: '16px',
                  border: '2px solid rgba(255,255,255,0.3)',
                  borderTopColor: 'white',
                  borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite',
                  marginRight: '8px'
                }} />
                Accesso in corso...
              </>
            ) : (
              'Accedi'
            )}
          </button>
          
          {isLoading && (
            <style>{`
              @keyframes spin {
                to { transform: rotate(360deg); }
              }
            `}</style>
          )}
        </form>
      </div>
    </div>
  )
}


