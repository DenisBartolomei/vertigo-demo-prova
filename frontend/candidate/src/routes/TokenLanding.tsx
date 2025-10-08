import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export function TokenLanding() {
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (token.trim()) {
      navigate(`/interview/${token.trim()}`)
    }
  }

  return (
    <div className="token-landing">
      <div className="token-form">
        <div style={{ marginBottom: '32px', textAlign: 'center' }}>
          <div style={{ 
            width: '60px', 
            height: '60px', 
            borderRadius: '50%', 
            background: 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '24px',
            margin: '0 auto 16px'
          }}>
            🎯
          </div>
          <h1 style={{ 
            fontSize: '24px',
            background: 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            marginBottom: '8px'
          }}>
            Enter Interview Token
          </h1>
          <p className="muted">Paste the token you received via email to start your interview</p>
          <div style={{
            backgroundColor: '#e3f2fd',
            border: '1px solid #2196f3',
            borderRadius: '8px',
            padding: '12px',
            marginTop: '16px',
            fontSize: '13px',
            color: '#1565c0'
          }}>
            <strong>⚠️ Importante:</strong> Il token può essere utilizzato una sola volta. Una volta iniziato il colloquio, non potrai più accedere con lo stesso token.
          </div>
        </div>
        
        <form onSubmit={handleSubmit}>
          <input
            className="token-input"
            value={token}
            onChange={e => setToken(e.target.value)}
            placeholder="Paste your interview token here..."
          />
          <button 
            type="submit" 
            className="token-submit"
            disabled={!token.trim()}
          >
            🚀 Start Interview
          </button>
        </form>
      </div>
    </div>
  )
}