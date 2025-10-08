import { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'
const CANDIDATE_BASE = import.meta.env.VITE_CANDIDATE_BASE || 'http://localhost:3001'

type Session = {
  session_id: string
  candidate_name: string
  candidate_email?: string
  position_id?: string
  position_name?: string
  status?: string
  interview_token?: string
  token_sent?: boolean
  token_sent_by?: string
  token_sent_at?: string
}

export function NuovaSessione() {
  const [positionId, setPositionId] = useState('')
  const [candidateName, setCandidateName] = useState('')
  const [candidateEmail, setCandidateEmail] = useState('')
  const [cvFile, setCvFile] = useState<File | null>(null)
  const [result, setResult] = useState<any | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [positions, setPositions] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const token = localStorage.getItem('hr_jwt')

  async function loadSessions() {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/sessions`, { headers: { Authorization: `Bearer ${token}` } })
      if (res.status === 401) {
        // Token expired, redirect to login
        localStorage.removeItem('hr_jwt')
        window.location.href = '/login'
        return
      }
      if (res.ok) {
        const data = await res.json()
        console.log('Loaded sessions data:', data.items)
        setSessions(data.items || [])
      } else {
        console.error('Failed to load sessions:', res.statusText)
      }
    } catch (error) {
      console.error('Error loading sessions:', error)
    } finally {
      setLoading(false)
    }
  }

  async function loadPositions() {
    try {
      const res = await fetch(`${API_BASE}/positions`, { headers: { Authorization: `Bearer ${token}` } })
      if (res.status === 401) {
        // Token expired, redirect to login
        localStorage.removeItem('hr_jwt')
        window.location.href = '/login'
        return
      }
      if (res.ok) {
        const data = await res.json()
        setPositions(data.positions || [])
      } else {
        console.error('Failed to load positions:', res.statusText)
      }
    } catch (error) {
      console.error('Error loading positions:', error)
    }
  }

  useEffect(() => { 
    loadSessions()
    loadPositions()
  }, [])

  async function createSession() {
    if (!cvFile) return
    
    try {
      // Step 1: Create session
      const formData = new FormData()
      formData.append('position_id', positionId)
      formData.append('candidate_name', candidateName)
      formData.append('candidate_email', candidateEmail)
      formData.append('frontend_base_url', CANDIDATE_BASE)
      formData.append('cv_file', cvFile)
      
      const resp = await fetch(`${API_BASE}/sessions`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: formData })
      if (!resp.ok) {
        throw new Error(`Session creation failed: ${resp.statusText}`)
      }
      const data = await resp.json()
      setResult(data)
      
      // Step 2: Wait a moment for DB consistency, then start CV analysis
      if (data.session_id) {
        console.log('Session created, starting CV analysis...')
        await new Promise(resolve => setTimeout(resolve, 1000)) // 1 second delay
        
        const prepResp = await fetch(`${API_BASE}/sessions/${data.session_id}/prepare`, { 
          method: 'POST', 
          headers: { Authorization: `Bearer ${token}` } 
        })
        
        if (prepResp.ok) {
          console.log('CV analysis started successfully')
        } else {
          console.error('CV analysis failed:', await prepResp.text())
        }
      }
      
      // Step 3: Clean up form and refresh
      setPositionId('')
      setCandidateName('')
      setCandidateEmail('')
      setCvFile(null)
      await loadSessions()
      
    } catch (error) {
      console.error('Error in createSession:', error)
      alert(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  async function prepareSession() {
    if (!result?.session_id) return
    await fetch(`${API_BASE}/sessions/${result.session_id}/prepare`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } })
    alert('Preparazione avviata')
    await loadSessions()
  }

  async function markTokenSent(sessionId: string) {
    try {
      console.log(`Marking token as sent for session: ${sessionId}`)
      const resp = await fetch(`${API_BASE}/sessions/${sessionId}/token-sent`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` }
      })
      
      console.log(`Response status: ${resp.status}`)
      
      if (resp.ok) {
        const result = await resp.json()
        console.log('Token marked as sent successfully:', result)
        alert('Token marcato come inviato!')
        await loadSessions()
      } else {
        const error = await resp.json()
        console.error('Error response:', error)
        alert(`Errore: ${error.detail || 'Errore sconosciuto'}`)
      }
    } catch (error) {
      console.error('Error marking token as sent:', error)
      alert('Errore di connessione')
    }
  }

  function getStatusColor(status?: string) {
    switch (status) {
      case 'initialized': return '#f59e0b'
      case 'Colloquio da completare': return '#3b82f6'
      case 'CV analysis failed': return '#ef4444'
      default: return '#6b7280'
    }
  }

  return (
    <div className="container" style={{ display: 'grid', gap: '32px' }}>
      <div>
        <h2>Nuova Sessione</h2>
        <p className="muted">Crea nuove sessioni di candidati e monitora lo stato di tutti i candidati che non hanno ancora completato l'intero processo di selezione.</p>
      </div>
      
      {/* Form */}
      <div className="card fade-in">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
          <div style={{ 
            width: '40px', 
            height: '40px', 
            borderRadius: '50%', 
            background: 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: '18px'
          }}>
            👤
          </div>
          <h3>Crea Nuova Sessione Candidato</h3>
        </div>
        
        <div style={{ display: 'grid', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: 'var(--text-primary)' }}>
              Seleziona Posizione
            </label>
            <select value={positionId} onChange={e => setPositionId(e.target.value)}>
              <option value="">Scegli una posizione...</option>
              {positions.map((p) => (
                <option key={p._id} value={p._id}>
                  {p.position_name} ({p._id})
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: 'var(--text-primary)' }}>
              Nome Candidato
            </label>
            <input placeholder="Inserisci il nome completo del candidato" value={candidateName} onChange={e => setCandidateName(e.target.value)} />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: 'var(--text-primary)' }}>
              Indirizzo Email
            </label>
            <input placeholder="candidato@esempio.com" value={candidateEmail} onChange={e => setCandidateEmail(e.target.value)} />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: 'var(--text-primary)' }}>
              File CV
            </label>
            <input type="file" accept=".pdf,.txt" onChange={e => setCvFile(e.target.files?.[0] || null)} />
            {cvFile && (
              <div style={{ 
                marginTop: '8px', 
                padding: '8px 12px', 
                background: 'var(--light-purple)', 
                borderRadius: 'var(--radius-md)',
                fontSize: '14px',
                color: 'var(--text-secondary)'
              }}>
                📄 {cvFile.name}
              </div>
            )}
          </div>
          
          <button 
            onClick={createSession} 
            disabled={!cvFile || !positionId || !candidateName}
            style={{ width: '100%', justifyContent: 'center', marginTop: '8px' }}
          >
            🚀 Crea Sessione & Invia Invito
          </button>
        </div>
        
        {result && (
          <div className="card" style={{ 
            background: 'linear-gradient(135deg, var(--light-purple), var(--pastel-pink))',
            border: '1px solid var(--primary-purple)',
            marginTop: '24px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{ 
                width: '32px', 
                height: '32px', 
                borderRadius: '50%', 
                background: 'var(--primary-purple)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontSize: '16px'
              }}>
                ✅
              </div>
              <strong>Sessione Creata con Successo!</strong>
            </div>
            <div style={{ display: 'grid', gap: '12px', fontSize: '14px' }}>
              <div><strong>ID Sessione:</strong> <code style={{ background: 'rgba(255,255,255,0.5)', padding: '2px 6px', borderRadius: '4px' }}>{result.session_id}</code></div>
              <div><strong>Token Colloquio:</strong> <code style={{ background: 'rgba(255,255,255,0.5)', padding: '2px 6px', borderRadius: '4px' }}>{result.interview_token}</code></div>
              <div>
                <strong>Link Candidato:</strong>
                <div style={{ 
                  wordBreak: 'break-all', 
                  fontSize: '12px', 
                  color: 'var(--text-secondary)',
                  background: 'rgba(255,255,255,0.5)',
                  padding: '8px',
                  borderRadius: 'var(--radius-md)',
                  marginTop: '4px'
                }}>
                  {CANDIDATE_BASE}/interview/{result.interview_token}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Dashboard */}
      <div className="card fade-in">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
          <div style={{ 
            width: '40px', 
            height: '40px', 
            borderRadius: '50%', 
            background: 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: '18px'
          }}>
            📊
          </div>
          <h3>Monitoraggio Candidati Attivi</h3>
        </div>
        
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '24px', marginBottom: '8px' }}>⏳</div>
            Caricamento sessioni...
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '16px' }}>
            {sessions.length === 0 ? (
              <div style={{ 
                textAlign: 'center', 
                padding: '40px', 
                color: 'var(--text-muted)',
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-lg)'
              }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>
                <div style={{ fontSize: '18px', marginBottom: '8px' }}>Nessuna sessione attiva</div>
                <div>Crea la tua prima sessione candidato qui sopra</div>
              </div>
            ) : (
              sessions.map((s) => (
                <div key={s.session_id} className="card" style={{ 
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '20px',
                  padding: '24px',
                  transition: 'all 0.2s ease'
                }}>
                  {/* Header Section */}
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'flex-start',
                    gap: '20px'
                  }}>
                    {/* Candidate Info */}
                    <div style={{ flex: 1 }}>
                      <h4 style={{ 
                        fontSize: '20px', 
                        fontWeight: '700', 
                        margin: '0 0 8px 0',
                        color: 'var(--text-primary)'
                      }}>
                        {s.candidate_name || '—'}
                      </h4>
                      <div style={{ 
                        fontSize: '16px', 
                        color: 'var(--text-secondary)',
                        marginBottom: '8px',
                        fontWeight: '500'
                      }}>
                        {s.position_name || s.position_id || '—'}
                      </div>
                      {s.candidate_email && (
                        <div style={{ 
                          fontSize: '14px', 
                          color: 'var(--text-secondary)',
                          marginBottom: '8px',
                          fontWeight: '400',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}>
                          <span style={{ fontSize: '16px' }}>📧</span>
                          <span>{s.candidate_email}</span>
                        </div>
                      )}
                      <div style={{ 
                        fontSize: '12px', 
                        color: 'var(--text-muted)',
                        fontFamily: 'monospace',
                        background: 'var(--bg-secondary)',
                        padding: '4px 8px',
                        borderRadius: 'var(--radius-sm)',
                        display: 'inline-block'
                      }}>
                        ID: {s.session_id}
                      </div>
                    </div>
                    
                    {/* Status Badge */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '8px 16px',
                      background: 'var(--bg-secondary)',
                      borderRadius: 'var(--radius-lg)',
                      border: '1px solid var(--border-light)'
                    }}>
                      <div style={{ 
                        width: '8px', 
                        height: '8px', 
                        borderRadius: '50%', 
                        backgroundColor: getStatusColor(s.status) 
                      }}></div>
                      <span style={{ 
                        fontSize: '14px', 
                        fontWeight: '500',
                        color: 'var(--text-primary)'
                      }}>
                        {s.status || 'unknown'}
                      </span>
                    </div>
                  </div>
                  
                  {/* Token Section */}
                  <div style={{
                    background: 'linear-gradient(135deg, var(--light-purple), var(--pastel-pink))',
                    borderRadius: 'var(--radius-lg)',
                    padding: '20px',
                    border: '1px solid rgba(139, 92, 246, 0.2)'
                  }}>
                    <div style={{ 
                      fontSize: '14px', 
                      color: 'var(--text-secondary)',
                      marginBottom: '16px',
                      fontWeight: '500'
                    }}>
                      📧 Gestione Token Colloquio
                    </div>
                    
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      gap: '16px',
                      flexWrap: 'wrap'
                    }}>
                      {/* Token Status */}
                      <div style={{ flex: 1, minWidth: '200px' }}>
                        {s.token_sent ? (
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '12px 16px',
                            background: 'rgba(16, 185, 129, 0.1)',
                            color: '#065F46',
                            borderRadius: 'var(--radius-md)',
                            fontSize: '14px',
                            fontWeight: '600',
                            border: '1px solid rgba(16, 185, 129, 0.2)'
                          }}>
                            <span style={{ fontSize: '16px' }}>✅</span>
                            <span>Token Inviato al Candidato</span>
                          </div>
                        ) : (
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '12px 16px',
                            background: 'rgba(245, 158, 11, 0.1)',
                            color: '#92400E',
                            borderRadius: 'var(--radius-md)',
                            fontSize: '14px',
                            fontWeight: '600',
                            border: '1px solid rgba(245, 158, 11, 0.2)'
                          }}>
                            <span style={{ fontSize: '16px' }}>⏳</span>
                            <span>Token da Inviare</span>
                          </div>
                        )}
                        
                        {s.token_sent && (
                          <div style={{
                            fontSize: '12px',
                            color: 'var(--text-muted)',
                            marginTop: '8px',
                            padding: '8px 12px',
                            background: 'rgba(255, 255, 255, 0.5)',
                            borderRadius: 'var(--radius-sm)'
                          }}>
                            <div><strong>Inviato da:</strong> {s.token_sent_by || 'HR'}</div>
                            {s.token_sent_at && (
                              <div><strong>Il:</strong> {new Date(s.token_sent_at).toLocaleString('it-IT')}</div>
                            )}
                          </div>
                        )}
                      </div>
                      
                      {/* Action Buttons */}
                      <div style={{ 
                        display: 'flex', 
                        gap: '12px', 
                        alignItems: 'center',
                        flexWrap: 'wrap'
                      }}>
                        <button
                          onClick={() => {
                            if (s.interview_token) {
                              navigator.clipboard.writeText(s.interview_token)
                              alert('Token copiato negli appunti!')
                            } else {
                              alert('Token non disponibile. La sessione potrebbe non essere ancora pronta o potrebbe esserci un problema di sincronizzazione. Prova a ricaricare la pagina.')
                            }
                          }}
                          style={{ 
                            fontSize: '14px', 
                            padding: '12px 20px',
                            background: s.interview_token ? 'var(--primary-purple)' : '#9CA3AF',
                            color: 'white',
                            border: 'none',
                            borderRadius: 'var(--radius-md)',
                            cursor: s.interview_token ? 'pointer' : 'not-allowed',
                            transition: 'all 0.2s ease',
                            fontWeight: '600',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                          }}
                          title={s.interview_token ? "Copia token colloquio" : "Token non disponibile"}
                          disabled={!s.interview_token}
                        >
                          <span>📋</span>
                          <span>{s.interview_token ? 'Copia Token' : 'Token N/A'}</span>
                        </button>

                        {s.candidate_email && (
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(s.candidate_email!)
                              alert('Email copiata negli appunti!')
                            }}
                            style={{ 
                              fontSize: '14px', 
                              padding: '12px 20px',
                              background: '#3b82f6',
                              color: 'white',
                              border: 'none',
                              borderRadius: 'var(--radius-md)',
                              cursor: 'pointer',
                              transition: 'all 0.2s ease',
                              fontWeight: '600',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '8px'
                            }}
                            title="Copia email candidato"
                          >
                            <span>📧</span>
                            <span>Copia Email</span>
                          </button>
                        )}
                        
                        {s.interview_token && !s.token_sent && (
                          <button
                            onClick={() => {
                              if (confirm('Confermi di aver inviato il token al candidato? Questa azione impedirà ad altri HR di inviare nuovamente il token.')) {
                                markTokenSent(s.session_id)
                              }
                            }}
                            style={{ 
                              fontSize: '14px', 
                              padding: '12px 20px',
                              background: '#059669',
                              color: 'white',
                              border: 'none',
                              borderRadius: 'var(--radius-md)',
                              cursor: 'pointer',
                              transition: 'all 0.2s ease',
                              fontWeight: '600',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '8px'
                            }}
                            title="Marca come inviato per evitare doppi invii"
                          >
                            <span>✅</span>
                            <span>Marca Inviato</span>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
