import React, { useState, useEffect } from 'react'

interface SecurityEvent {
  event_type: string
  timestamp: string
  severity: 'low' | 'medium' | 'high'
  details: string
  created_at: string
}

interface SecuritySummary {
  total_events: number
  high_severity_events: number
  medium_severity_events: number
  low_severity_events: number
  cheating_score: number
  events_by_type: Record<string, number>
  last_updated: string
}

interface RiskAssessment {
  level: 'MINIMAL' | 'LOW' | 'MEDIUM' | 'HIGH'
  color: string
  cheating_score: number
  recommendation: string
}

interface SecurityReportData {
  session_id: string
  security_summary: SecuritySummary
  security_events: SecurityEvent[]
  risk_assessment: RiskAssessment
}

interface SecurityReportProps {
  sessionId: string
  onClose: () => void
}

export function SecurityReport({ sessionId, onClose }: SecurityReportProps) {
  const [reportData, setReportData] = useState<SecurityReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadSecurityReport()
  }, [sessionId])

  const loadSecurityReport = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('hr_jwt')
      const response = await fetch(`${import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'}/sessions/${sessionId}/security-report`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (response.ok) {
        const data = await response.json()
        setReportData(data)
      } else {
        setError('Failed to load security report')
      }
    } catch (err) {
      setError('Error loading security report')
    } finally {
      setLoading(false)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return '#dc3545'
      case 'medium': return '#ffc107'
      case 'low': return '#28a745'
      default: return '#6c757d'
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high': return '🚨'
      case 'medium': return '⚠️'
      case 'low': return 'ℹ️'
      default: return '📝'
    }
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('it-IT')
  }

  const translateEventType = (eventType: string) => {
    const translations: Record<string, string> = {
      'tab_switch': 'Cambio Tab',
      'focus_loss': 'Perdita Focus',
      'window_resize': 'Ridimensionamento Finestra',
      'copy_paste': 'Copia e Incolla',
      'right_click': 'Click Destro',
      'keyboard_shortcut': 'Scorciatoia Tastiera',
      'page_refresh': 'Ricarica Pagina',
      'dev_tools': 'Strumenti Sviluppatore'
    }
    return translations[eventType] || eventType.replace('_', ' ')
  }

  const translateSeverity = (severity: string) => {
    const translations: Record<string, string> = {
      'high': 'ALTA',
      'medium': 'MEDIA',
      'low': 'BASSA'
    }
    return translations[severity] || severity.toUpperCase()
  }

  const translateRiskLevel = (level: string) => {
    const translations: Record<string, string> = {
      'HIGH': 'ALTO',
      'MEDIUM': 'MEDIO',
      'LOW': 'BASSO',
      'MINIMAL': 'MINIMO'
    }
    return translations[level] || level
  }

  if (loading) {
    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{
          backgroundColor: 'white',
          padding: '40px',
          borderRadius: '12px',
          textAlign: 'center',
          minWidth: '300px'
        }}>
          <div style={{ fontSize: '24px', marginBottom: '16px' }}>⏳</div>
          <div>Caricamento report sicurezza...</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{
          backgroundColor: 'white',
          padding: '40px',
          borderRadius: '12px',
          textAlign: 'center',
          minWidth: '300px'
        }}>
          <div style={{ fontSize: '24px', marginBottom: '16px', color: '#dc3545' }}>❌</div>
          <div style={{ marginBottom: '16px' }}>{error}</div>
          <button
            onClick={onClose}
            style={{
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            Chiudi
          </button>
        </div>
      </div>
    )
  }

  if (!reportData) {
    return null
  }

  const { security_summary, security_events, risk_assessment } = reportData

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '12px',
        maxWidth: '800px',
        width: '100%',
        maxHeight: '90vh',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Header */}
        <div style={{
          padding: '24px',
          borderBottom: '1px solid #e9ecef',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '24px', fontWeight: '600' }}>
              🔒 Report Sicurezza
            </h2>
            <p style={{ margin: '4px 0 0 0', color: '#6c757d', fontSize: '14px' }}>
              ID Sessione: {sessionId}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              fontSize: '24px',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '4px'
            }}
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: '24px' }}>
          {/* Risk Assessment */}
          <div style={{
            backgroundColor: '#f8f9fa',
            border: `2px solid ${risk_assessment.color}`,
            borderRadius: '8px',
            padding: '20px',
            marginBottom: '24px'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginBottom: '12px'
            }}>
              <div style={{ fontSize: '32px' }}>
                {risk_assessment.level === 'HIGH' ? '🚨' : 
                 risk_assessment.level === 'MEDIUM' ? '⚠️' : 
                 risk_assessment.level === 'LOW' ? 'ℹ️' : '✅'}
              </div>
              <div>
                <h3 style={{ 
                  margin: 0, 
                  color: risk_assessment.color,
                  fontSize: '20px',
                  fontWeight: '600'
                }}>
                  Livello di Rischio: {translateRiskLevel(risk_assessment.level)}
                </h3>
                <p style={{ margin: '4px 0 0 0', color: '#6c757d', fontSize: '14px' }}>
                  Punteggio Cheating: {risk_assessment.cheating_score}/100
                </p>
              </div>
            </div>
            <div style={{
              backgroundColor: 'white',
              padding: '12px',
              borderRadius: '6px',
              border: '1px solid #e9ecef'
            }}>
              <strong>Raccomandazione:</strong> {risk_assessment.recommendation}
            </div>
          </div>

          {/* Security Summary */}
          <div style={{ marginBottom: '24px' }}>
            <h3 style={{ marginBottom: '16px', fontSize: '18px', fontWeight: '600' }}>
              📊 Riepilogo Sicurezza
            </h3>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              gap: '16px',
              marginBottom: '16px'
            }}>
              <div style={{
                backgroundColor: '#f8f9fa',
                padding: '16px',
                borderRadius: '8px',
                textAlign: 'center',
                border: '1px solid #e9ecef'
              }}>
                <div style={{ fontSize: '24px', fontWeight: '600', color: '#495057' }}>
                  {security_summary.total_events}
                </div>
                <div style={{ fontSize: '14px', color: '#6c757d' }}>Eventi Totali</div>
              </div>
              <div style={{
                backgroundColor: '#fff3cd',
                padding: '16px',
                borderRadius: '8px',
                textAlign: 'center',
                border: '1px solid #ffeaa7'
              }}>
                <div style={{ fontSize: '24px', fontWeight: '600', color: '#856404' }}>
                  {security_summary.high_severity_events}
                </div>
                <div style={{ fontSize: '14px', color: '#856404' }}>Alta Gravità</div>
              </div>
              <div style={{
                backgroundColor: '#fff3cd',
                padding: '16px',
                borderRadius: '8px',
                textAlign: 'center',
                border: '1px solid #ffeaa7'
              }}>
                <div style={{ fontSize: '24px', fontWeight: '600', color: '#856404' }}>
                  {security_summary.medium_severity_events}
                </div>
                <div style={{ fontSize: '14px', color: '#856404' }}>Media Gravità</div>
              </div>
              <div style={{
                backgroundColor: '#d1f2eb',
                padding: '16px',
                borderRadius: '8px',
                textAlign: 'center',
                border: '1px solid #a3e4d7'
              }}>
                <div style={{ fontSize: '24px', fontWeight: '600', color: '#0c5460' }}>
                  {security_summary.low_severity_events}
                </div>
                <div style={{ fontSize: '14px', color: '#0c5460' }}>Bassa Gravità</div>
              </div>
            </div>

            {/* Events by Type */}
            {Object.keys(security_summary.events_by_type).length > 0 && (
              <div style={{
                backgroundColor: '#f8f9fa',
                padding: '16px',
                borderRadius: '8px',
                border: '1px solid #e9ecef'
              }}>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '16px', fontWeight: '600' }}>
                  Eventi per Tipo
                </h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {Object.entries(security_summary.events_by_type).map(([type, count]) => (
                    <span
                      key={type}
                      style={{
                        backgroundColor: '#e9ecef',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: '500'
                      }}
                    >
                      {translateEventType(type)}: {count}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Security Events */}
          <div>
            <h3 style={{ marginBottom: '16px', fontSize: '18px', fontWeight: '600' }}>
              📋 Eventi Sicurezza Recenti
            </h3>
            {security_events.length === 0 ? (
              <div style={{
                backgroundColor: '#d1f2eb',
                padding: '20px',
                borderRadius: '8px',
                textAlign: 'center',
                border: '1px solid #a3e4d7'
              }}>
                <div style={{ fontSize: '24px', marginBottom: '8px' }}>✅</div>
                <div style={{ color: '#0c5460', fontWeight: '500' }}>
                  Nessuna violazione di sicurezza rilevata
                </div>
              </div>
            ) : (
              <div style={{ maxHeight: '300px', overflow: 'auto' }}>
                {security_events.map((event, index) => (
                  <div
                    key={index}
                    style={{
                      backgroundColor: 'white',
                      border: `1px solid ${getSeverityColor(event.severity)}`,
                      borderRadius: '8px',
                      padding: '16px',
                      marginBottom: '12px'
                    }}
                  >
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      marginBottom: '8px'
                    }}>
                      <div style={{ fontSize: '20px' }}>
                        {getSeverityIcon(event.severity)}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{
                          fontWeight: '600',
                          color: getSeverityColor(event.severity)
                        }}>
                          {translateEventType(event.event_type)}
                        </div>
                        <div style={{ fontSize: '12px', color: '#6c757d' }}>
                          {formatTimestamp(event.timestamp)}
                        </div>
                      </div>
                      <div style={{
                        backgroundColor: getSeverityColor(event.severity),
                        color: 'white',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: '500',
                        textTransform: 'uppercase'
                      }}>
                        {translateSeverity(event.severity)}
                      </div>
                    </div>
                    {event.details && (
                      <div style={{
                        fontSize: '14px',
                        color: '#495057',
                        marginTop: '8px'
                      }}>
                        {event.details}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid #e9ecef',
          backgroundColor: '#f8f9fa',
          display: 'flex',
          justifyContent: 'flex-end'
        }}>
          <button
            onClick={onClose}
            style={{
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '500'
            }}
          >
            Chiudi Report
          </button>
        </div>
      </div>
    </div>
  )
}
