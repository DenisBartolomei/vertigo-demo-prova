import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const API_BASE = (import.meta as any).env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'

export function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    const resp = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })
    if (!resp.ok) {
      setError('Credenziali non valide')
      return
    }
    const data = await resp.json()
    localStorage.setItem('hr_jwt', data.token)
    navigate('/app/dashboard')
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
          <button type="submit" style={{ width: '100%', justifyContent: 'center' }}>
            Accedi
          </button>
        </form>
      </div>
    </div>
  )
}


