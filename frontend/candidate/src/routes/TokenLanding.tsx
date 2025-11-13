import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Target, User, Lightbulb, X, Clock, Search, CheckCircle2, Rocket, ArrowLeft } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'

type InterviewInfo = {
  session_id: string
  position_name: string
  case_id?: string
}

export function TokenLanding() {
  const [step, setStep] = useState<'token' | 'details'>('token')
  const [token, setToken] = useState('')
  const [name, setName] = useState('')
  const [surname, setSurname] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [interviewInfo, setInterviewInfo] = useState<InterviewInfo | null>(null)
  const navigate = useNavigate()

  async function handleTokenSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    try {
      if (!token.trim()) {
        setError('Please enter a valid token')
        return
      }

      // Verifica il token
      const response = await fetch(`${API_BASE}/interviews/${token.trim()}`)
      
      if (!response.ok) {
        if (response.status === 404) {
          setError('Invalid or expired token. Please check your email and try again.')
        } else {
          setError('Error verifying token. Please try again.')
        }
        return
      }

      const data = await response.json()
      setInterviewInfo(data)
      setStep('details')
      
    } catch (error) {
      console.error('Error verifying token:', error)
      setError('Connection error. Please check your internet connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  async function handleDetailsSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    try {
      if (!name.trim() || !surname.trim()) {
        setError('Please enter both your name and surname')
        return
      }

      // PRIMA: Salva solo nome e cognome
      const saveResponse = await fetch(`${API_BASE}/interviews/${token}/save-name`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: name.trim(),
          surname: surname.trim()
        })
      })

      if (!saveResponse.ok) {
        if (saveResponse.status === 404) {
          setError('Invalid or expired token. Please check your email and try again.')
        } else if (saveResponse.status === 410) {
          setError('This interview has been completed and is no longer available.')
        } else {
          const errorData = await saveResponse.json()
          setError(errorData.detail || 'Error saving your information. Please try again.')
        }
        return
      }

      // DOPO: Naviga alla pagina termini e condizioni
      navigate(`/interview/${token}`)
      
    } catch (error) {
      console.error('Error saving details:', error)
      setError('Connection error. Please check your internet connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  function goBack() {
    if (step === 'details') {
      setStep('token')
      setError('')
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
            {step === 'token' ? <Target size={24} color="white" /> : <User size={24} color="white" />}
          </div>
          <h1 style={{ 
            fontSize: '24px',
            background: 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            marginBottom: '8px'
          }}>
            {step === 'token' ? 'Enter Interview Token' : 'Complete Your Profile'}
          </h1>
          <p className="muted">
            {step === 'token' 
              ? 'Paste the token you received via email to start your interview'
              : 'Please provide your name and surname to continue'
            }
          </p>
          
          {step === 'token' && (
            <div style={{
              backgroundColor: '#e3f2fd',
              border: '1px solid #2196f3',
              borderRadius: '8px',
              padding: '12px',
              marginTop: '16px',
              fontSize: '14px',
              color: '#1976d2'
            }}>
              <strong style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Lightbulb size={16} /> Tip:
              </strong> Check your email for the interview invitation. The token should look like: <code>abc123def456</code>
            </div>
          )}
        </div>

        {/* Step 1: Token Input */}
        {step === 'token' && (
          <form onSubmit={handleTokenSubmit}>
            <div style={{ marginBottom: '24px' }}>
              <label style={{ 
                display: 'block', 
                marginBottom: '8px', 
                fontWeight: '600',
                color: 'var(--text-primary)'
              }}>
                Interview Token
              </label>
              <input
                type="text"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Paste your interview token here..."
                style={{
                  width: '100%',
                  padding: '16px',
                  border: '2px solid #e1e5e9',
                  borderRadius: '12px',
                  fontSize: '16px',
                  fontFamily: 'monospace',
                  letterSpacing: '1px',
                  backgroundColor: '#f8f9fa',
                  transition: 'all 0.2s ease'
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = 'var(--primary-purple)'
                  e.target.style.backgroundColor = 'white'
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#e1e5e9'
                  e.target.style.backgroundColor = '#f8f9fa'
                }}
              />
            </div>

            {error && (
              <div style={{
                backgroundColor: '#ffebee',
                border: '1px solid #f44336',
                borderRadius: '8px',
                padding: '12px',
                marginBottom: '24px',
                color: '#c62828',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <X size={16} /> {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !token.trim()}
              style={{
                width: '100%',
                padding: '16px',
                background: loading || !token.trim() 
                  ? '#9ca3af' 
                  : 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
                color: 'white',
                border: 'none',
                borderRadius: '12px',
                fontSize: '16px',
                fontWeight: '600',
                cursor: loading || !token.trim() ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px'
              }}
            >
              {loading ? <Clock size={18} /> : <Search size={18} />} {loading ? 'Verifying...' : 'Verify Token'}
            </button>
          </form>
        )}

        {/* Step 2: Name and Surname */}
        {step === 'details' && interviewInfo && (
          <div>
            <div style={{
              backgroundColor: '#e8f5e8',
              border: '1px solid #4caf50',
              borderRadius: '8px',
              padding: '16px',
              marginBottom: '24px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                <CheckCircle2 size={20} color="#2e7d32" />
                <strong style={{ color: '#2e7d32' }}>Token Verified!</strong>
              </div>
              <div style={{ fontSize: '14px', color: '#388e3c' }}>
                <div><strong>Position:</strong> {interviewInfo.position_name}</div>
                <div><strong>Session ID:</strong> {interviewInfo.session_id}</div>
              </div>
            </div>

            <form onSubmit={handleDetailsSubmit}>
              <div style={{ display: 'grid', gap: '20px', marginBottom: '24px' }}>
                <div>
                  <label style={{ 
                    display: 'block', 
                    marginBottom: '8px', 
                    fontWeight: '600',
                    color: 'var(--text-primary)'
                  }}>
                    First Name *
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Enter your first name"
                    style={{
                      width: '100%',
                      padding: '16px',
                      border: '2px solid #e1e5e9',
                      borderRadius: '12px',
                      fontSize: '16px',
                      backgroundColor: '#f8f9fa',
                      transition: 'all 0.2s ease'
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = 'var(--primary-purple)'
                      e.target.style.backgroundColor = 'white'
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = '#e1e5e9'
                      e.target.style.backgroundColor = '#f8f9fa'
                    }}
                  />
                </div>

                <div>
                  <label style={{ 
                    display: 'block', 
                    marginBottom: '8px', 
                    fontWeight: '600',
                    color: 'var(--text-primary)'
                  }}>
                    Last Name *
                  </label>
                  <input
                    type="text"
                    value={surname}
                    onChange={(e) => setSurname(e.target.value)}
                    placeholder="Enter your last name"
                    style={{
                      width: '100%',
                      padding: '16px',
                      border: '2px solid #e1e5e9',
                      borderRadius: '12px',
                      fontSize: '16px',
                      backgroundColor: '#f8f9fa',
                      transition: 'all 0.2s ease'
                    }}
                    onFocus={(e) => {
                      e.target.style.borderColor = 'var(--primary-purple)'
                      e.target.style.backgroundColor = 'white'
                    }}
                    onBlur={(e) => {
                      e.target.style.borderColor = '#e1e5e9'
                      e.target.style.backgroundColor = '#f8f9fa'
                    }}
                  />
                </div>
              </div>

              {error && (
                <div style={{
                  backgroundColor: '#ffebee',
                  border: '1px solid #f44336',
                  borderRadius: '8px',
                  padding: '12px',
                  marginBottom: '24px',
                  color: '#c62828',
                  fontSize: '14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <X size={16} /> {error}
                </div>
              )}

              <div style={{ display: 'grid', gap: '12px' }}>
                <button
                  type="submit"
                  disabled={loading || !name.trim() || !surname.trim()}
                  style={{
                    width: '100%',
                    padding: '16px',
                    background: loading || !name.trim() || !surname.trim()
                      ? '#9ca3af' 
                      : 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
                    color: 'white',
                    border: 'none',
                    borderRadius: '12px',
                    fontSize: '16px',
                    fontWeight: '600',
                    cursor: loading || !name.trim() || !surname.trim() ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px'
                  }}
                >
                  {loading ? <Clock size={18} /> : <Rocket size={18} />} {loading ? 'Starting Interview...' : 'Start Interview'}
                </button>

                <button
                  type="button"
                  onClick={goBack}
                  style={{
                    width: '100%',
                    padding: '12px',
                    background: 'transparent',
                    color: 'var(--text-muted)',
                    border: '2px solid #e1e5e9',
                    borderRadius: '12px',
                    fontSize: '14px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <ArrowLeft size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Back to Token Entry
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Powered by Vertigo AI */}
        <div style={{
          marginTop: '32px',
          paddingTop: '24px',
          borderTop: '1px solid #e1e5e9',
          textAlign: 'center'
        }}>
          <p style={{
            fontSize: '12px',
            color: '#9ca3af',
            margin: 0,
            fontWeight: '500'
          }}>
            Powered by <span style={{ 
              background: 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              fontWeight: '600'
            }}>Vertigo AI</span>
          </p>
        </div>
      </div>
    </div>
  )
}