import React, { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          justifyContent: 'center', 
          minHeight: '100vh',
          padding: '20px',
          textAlign: 'center',
          background: 'linear-gradient(135deg, #F3F0FF 0%, #FDF2F8 100%)'
        }}>
          <div style={{ 
            background: 'white',
            padding: '40px',
            borderRadius: '16px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
            maxWidth: '500px'
          }}>
            <h1 style={{ 
              color: '#8B5CF6', 
              fontSize: '32px', 
              marginBottom: '16px',
              fontWeight: '700'
            }}>
              Oops! Qualcosa è andato storto
            </h1>
            <p style={{ 
              color: '#6B7280', 
              fontSize: '18px', 
              marginBottom: '24px' 
            }}>
              Si è verificato un errore imprevisto. Riprova a ricaricare la pagina.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button 
                onClick={() => window.location.reload()}
                style={{
                  background: 'linear-gradient(135deg, #8B5CF6, #A78BFA)',
                  color: 'white',
                  border: 'none',
                  padding: '12px 24px',
                  borderRadius: '8px',
                  fontSize: '16px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
                onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                onMouseOut={(e) => e.currentTarget.style.transform = 'translateY(0)'}
              >
                🔄 Ricarica Pagina
              </button>
              <button 
                onClick={() => window.location.href = '/app'}
                style={{
                  background: '#F3F4F6',
                  color: '#374151',
                  border: '2px solid #E5E7EB',
                  padding: '12px 24px',
                  borderRadius: '8px',
                  fontSize: '16px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
                onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                onMouseOut={(e) => e.currentTarget.style.transform = 'translateY(0)'}
              >
                🏠 Dashboard
              </button>
            </div>
            {import.meta.env.DEV && this.state.error && (
              <details style={{ 
                marginTop: '20px', 
                padding: '16px', 
                background: '#FEF2F2', 
                borderRadius: '8px',
                textAlign: 'left'
              }}>
                <summary style={{ cursor: 'pointer', fontWeight: '600', color: '#DC2626' }}>
                  Dettagli Errore (Solo in Sviluppo)
                </summary>
                <pre style={{ 
                  marginTop: '8px', 
                  fontSize: '12px', 
                  color: '#7F1D1D',
                  overflow: 'auto'
                }}>
                  {this.state.error.stack}
                </pre>
              </details>
            )}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

