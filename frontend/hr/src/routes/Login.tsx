import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mail, Lock, Eye, EyeOff } from 'lucide-react'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'

const API_BASE = (import.meta as any).env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'

export function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
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
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Animated Background */}
      <div style={{
        position: 'absolute',
        inset: 0,
        background: 'linear-gradient(135deg, #F5F3FF 0%, #FCE7F3 50%, #FDF2F8 100%)'
      }} />
      
      {/* Decorative Elements */}
      <div style={{
        position: 'absolute',
        top: '80px',
        left: '80px',
        width: '288px',
        height: '288px',
        background: 'rgba(196, 181, 253, 0.2)',
        borderRadius: '50%',
        filter: 'blur(60px)',
        animation: 'pulse 3s ease-in-out infinite'
      }} />
      <div style={{
        position: 'absolute',
        bottom: '80px',
        right: '80px',
        width: '384px',
        height: '384px',
        background: 'rgba(251, 113, 133, 0.2)',
        borderRadius: '50%',
        filter: 'blur(60px)',
        animation: 'pulse 3s ease-in-out infinite',
        animationDelay: '1s'
      }} />
      
      {/* Login Card */}
      <div className="fade-in" style={{
        position: 'relative',
        width: '100%',
        maxWidth: '440px'
      }}>
        <div style={{
          background: 'rgba(255, 255, 255, 0.7)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderRadius: '20px',
          boxShadow: '0 20px 40px rgba(124, 58, 237, 0.15)',
          border: '1px solid rgba(255, 255, 255, 0.5)',
          padding: '32px',
          transition: 'all 0.3s ease'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.boxShadow = '0 25px 50px rgba(124, 58, 237, 0.2)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.boxShadow = '0 20px 40px rgba(124, 58, 237, 0.15)'
        }}
        >
          {/* Logo & Title */}
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <h1 style={{
              fontSize: '36px',
              fontWeight: '700',
              marginBottom: '8px',
              background: 'linear-gradient(135deg, #7C3AED 0%, #EC4899 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              Vertigo AI
            </h1>
            <p style={{ color: '#6B7280', fontWeight: '500', fontSize: '16px' }}>Dashboard HR</p>
          </div>
          
          {/* Login Form */}
          <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <Input
              type="email"
              label="Email"
              placeholder="nome@azienda.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              leftIcon={<Mail size={18} />}
              fullWidth
              required
            />
            
            <Input
              type={showPassword ? 'text' : 'password'}
              label="Password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              leftIcon={<Lock size={18} />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: '#6B7280',
                    transition: 'color 0.2s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.color = '#7C3AED'}
                  onMouseLeave={(e) => e.currentTarget.style.color = '#6B7280'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              }
              fullWidth
              required
            />
            
            {error && (
              <div className="shake" style={{
                background: '#FEF2F2',
                borderLeft: '4px solid #EF4444',
                padding: '12px',
                borderRadius: '8px'
              }}>
                <p style={{ fontSize: '14px', color: '#991B1B', fontWeight: '500', margin: 0 }}>
                  {error}
                </p>
              </div>
            )}
            
            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isLoading}
              style={{ width: '100%' }}
            >
              {isLoading ? 'Accesso in corso...' : 'Accedi'}
            </Button>
          </form>
          
          {/* Footer */}
          <div style={{
            marginTop: '24px',
            paddingTop: '24px',
            borderTop: '1px solid #E5E7EB',
            textAlign: 'center'
          }}>
            <p style={{ fontSize: '14px', color: '#6B7280', margin: 0 }}>
              Accedendo accetti i{' '}
              <a href="#" style={{
                color: '#7C3AED',
                textDecoration: 'none',
                fontWeight: '500'
              }}
              onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
              onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
              >
                Termini di Servizio
              </a>
            </p>
          </div>
        </div>
        
        {/* Subtle decorative elements */}
        <div style={{
          position: 'absolute',
          top: '-16px',
          right: '-16px',
          width: '96px',
          height: '96px',
          background: 'radial-gradient(circle, rgba(124, 58, 237, 0.1), transparent)',
          borderRadius: '50%',
          filter: 'blur(20px)'
        }} />
        <div style={{
          position: 'absolute',
          bottom: '-16px',
          left: '-16px',
          width: '128px',
          height: '128px',
          background: 'radial-gradient(circle, rgba(236, 72, 153, 0.1), transparent)',
          borderRadius: '50%',
          filter: 'blur(20px)'
        }} />
      </div>
    </div>
  )
}


