import { useEffect, useState } from 'react'
import { BatchStatusMonitor } from '../components/BatchStatusMonitor'
import { CreateSessionPanel } from '../components/CreateSessionPanel'
import '../components/batch-components.css'

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
  batch_date?: string
  batch_id?: string
  is_new_batch?: boolean
  candidate_surname?: string
}

type BatchGroup = {
  batch_date: string
  batch_id: string
  sessions: Session[]
  total_count: number
  new_count: number
}

export function NuovaSessione() {
  // Panel state
  const [isPanelOpen, setIsPanelOpen] = useState(false)
  const [batchUploading, setBatchUploading] = useState(false)
  
  // Filter and sort state
  const [statusFilter, setStatusFilter] = useState<'all' | 'processing' | 'ready' | 'ongoing'>('all')
  const [sortOrder, setSortOrder] = useState<'newest' | 'oldest'>('newest')
  
  // Sessions and positions
  const [sessions, setSessions] = useState<Session[]>([])
  const [positions, setPositions] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const token = localStorage.getItem('hr_jwt')

  async function loadSessions() {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/sessions`, { headers: { Authorization: `Bearer ${token}` } })
      if (res.status === 401) {
        localStorage.removeItem('hr_jwt')
        window.location.href = '/login'
        return
      }
      if (res.ok) {
        const data = await res.json()
        console.log('Loaded sessions data:', data)
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

  // Panel upload functions
  const handleBatchUpload = async (files: File[], positionId: string) => {
    setBatchUploading(true)
    try {
      const formData = new FormData()
      formData.append('position_id', positionId)
      files.forEach(file => formData.append('files', file))
      
      const response = await fetch(`${API_BASE}/api/batch/upload-cvs`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })
      
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`)
      }
      
      const data = await response.json()
      alert('Batch creato con successo!')
      await loadSessions()
      
    } catch (error) {
      console.error('Error in batch upload:', error)
      alert(`Errore: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setBatchUploading(false)
    }
  }

  const handleSingleUpload = async (data: {
    positionId: string
    candidateName: string
    candidateEmail: string
    cvFile: File
  }) => {
    try {
      const formData = new FormData()
      formData.append('position_id', data.positionId)
      formData.append('candidate_name', data.candidateName)
      formData.append('candidate_email', data.candidateEmail)
      formData.append('frontend_base_url', CANDIDATE_BASE)
      formData.append('cv_file', data.cvFile)
      
      const resp = await fetch(`${API_BASE}/sessions`, { 
        method: 'POST', 
        headers: { Authorization: `Bearer ${token}` }, 
        body: formData 
      })
      
      if (!resp.ok) {
        throw new Error(`Session creation failed: ${resp.statusText}`)
      }
      
      const result = await resp.json()
      
      // Start CV analysis
      if (result.session_id) {
        await new Promise(resolve => setTimeout(resolve, 1000))
        const prepResp = await fetch(`${API_BASE}/sessions/${result.session_id}/prepare`, { 
          method: 'POST', 
          headers: { Authorization: `Bearer ${token}` } 
        })
        
        if (prepResp.ok) {
          console.log('CV analysis started successfully')
        }
      }
      
      alert('Sessione creata con successo!')
      await loadSessions()
      
    } catch (error) {
      console.error('Error in single upload:', error)
      alert(`Errore: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const markTokenSent = async (sessionId: string) => {
    try {
      const resp = await fetch(`${API_BASE}/sessions/${sessionId}/token-sent`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (resp.ok) {
        alert('Token marcato come inviato!')
        await loadSessions()
      } else {
        const error = await resp.json()
        alert(`Errore: ${error.detail || 'Errore sconosciuto'}`)
      }
    } catch (error) {
      console.error('Error marking token as sent:', error)
      alert('Errore di connessione')
    }
  }

  const generateTokenForSession = async (sessionId: string) => {
    try {
      const resp = await fetch(`${API_BASE}/sessions/${sessionId}/generate-token`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (resp.ok) {
        alert('Token generato con successo!')
        await loadSessions()
      } else {
        const error = await resp.json()
        alert(`Errore: ${error.detail || 'Errore sconosciuto'}`)
      }
    } catch (error) {
      console.error('Error generating token:', error)
      alert('Errore di connessione')
    }
  }

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'initialized': return '#f59e0b'
      case 'Colloquio da completare': return '#3b82f6'
      case 'CV analysis failed': return '#ef4444'
      default: return '#6b7280'
    }
  }

  const getStatusCategory = (session: Session): 'processing' | 'ready' | 'ongoing' => {
    if (session.token_sent) return 'ongoing'
    if (session.interview_token) return 'ready'
    return 'processing'
  }

  const filteredAndSortedSessions = sessions
    .filter(session => {
      if (statusFilter === 'all') return true
      return getStatusCategory(session) === statusFilter
    })
    .sort((a, b) => {
      const dateA = new Date(a.batch_date || a.token_sent_at || 0).getTime()
      const dateB = new Date(b.batch_date || b.token_sent_at || 0).getTime()
      return sortOrder === 'newest' ? dateB - dateA : dateA - dateB
    })

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'In attesa'
    return new Date(dateString).toLocaleDateString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="container" style={{ display: 'grid', gap: '32px' }}>
      <div>
        <h2>Nuova Sessione</h2>
        <p className="muted">Crea nuove sessioni di candidati e monitora lo stato di tutti i candidati che non hanno ancora completato l'intero processo di selezione.</p>
      </div>
      
      {/* Create Session Button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button 
          className="create-session-btn"
          onClick={() => setIsPanelOpen(true)}
        >
          <div className="btn-icon">+</div>
          Crea Nuove Sessioni
        </button>
      </div>

      {/* Filter Bar */}
      <div className="filter-bar">
        <button 
          className={`filter-button ${statusFilter === 'all' ? 'active' : ''}`}
          onClick={() => setStatusFilter('all')}
        >
          📊 Tutti
        </button>
        <button 
          className={`filter-button ${statusFilter === 'processing' ? 'active' : ''}`}
          onClick={() => setStatusFilter('processing')}
        >
          ⏳ Batch in corso
        </button>
        <button 
          className={`filter-button ${statusFilter === 'ready' ? 'active' : ''}`}
          onClick={() => setStatusFilter('ready')}
        >
          🎯 Token pronto
        </button>
        <button 
          className={`filter-button ${statusFilter === 'ongoing' ? 'active' : ''}`}
          onClick={() => setStatusFilter('ongoing')}
        >
          💬 Colloquio in corso
        </button>
        
        <div className="sort-controls">
          <label>Ordina per:</label>
          <select 
            value={sortOrder} 
            onChange={e => setSortOrder(e.target.value as 'newest' | 'oldest')}
          >
            <option value="newest">Più recenti</option>
            <option value="oldest">Più vecchi</option>
          </select>
        </div>
      </div>

      {/* Unified Candidate Cards */}
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
          <h3>Candidati Attivi ({filteredAndSortedSessions.length})</h3>
        </div>
        
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '24px', marginBottom: '8px' }}>⏳</div>
            Caricamento sessioni...
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '16px' }}>
            {filteredAndSortedSessions.map((session) => (
              <div key={session.session_id} className="candidate-card">
                <div className="card-header">
                  <div className="card-info">
                    <h5>{session.candidate_name || 'Nome da inserire'}</h5>
                    <p>{session.position_name || session.position_id}</p>
                    {session.candidate_email && (
                      <p className="card-email">📧 {session.candidate_email}</p>
                    )}
                  </div>
                  <div className="card-status">
                    <div 
                      className="status-dot"
                      style={{ backgroundColor: getStatusColor(session.status) }}
                    ></div>
                    <span>{session.status || 'unknown'}</span>
                  </div>
                </div>
                
                <div className="card-date">
                  {formatDate(session.batch_date || session.token_sent_at)}
                </div>
                
                {(session.interview_token || session.status === 'Colloquio da completare') && (
                  <div className="card-actions">
                    {session.interview_token ? (
                      <button
                        className="copy-token-btn"
                        onClick={() => {
                          navigator.clipboard.writeText(session.interview_token!)
                          alert('Token copiato!')
                        }}
                      >
                        📋 Copia Token
                      </button>
                    ) : (
                      <button
                        className="generate-token-btn"
                        onClick={() => {
                          if (confirm('Generare token per questo candidato?')) {
                            generateTokenForSession(session.session_id)
                          }
                        }}
                      >
                        🔗 Genera Token
                      </button>
                    )}
                    
                    {!session.token_sent && (
                      <button
                        className="mark-sent-btn"
                        onClick={() => {
                          if (confirm('Confermi di aver inviato il token al candidato?')) {
                            markTokenSent(session.session_id)
                          }
                        }}
                      >
                        ✅ Marca Inviato
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
            
            {filteredAndSortedSessions.length === 0 && (
              <div style={{ 
                textAlign: 'center', 
                padding: '40px', 
                color: 'var(--text-muted)',
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-lg)'
              }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>
                <div style={{ fontSize: '18px', marginBottom: '8px' }}>Nessuna sessione attiva</div>
                <div>Carica i tuoi primi CV usando il pulsante "Crea Nuove Sessioni"</div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Batch Status Monitor */}
      <div className="card fade-in">
        <BatchStatusMonitor />
      </div>

      {/* Create Session Panel */}
      <CreateSessionPanel
        isOpen={isPanelOpen}
        onClose={() => setIsPanelOpen(false)}
        positions={positions}
        onBatchUpload={handleBatchUpload}
        onSingleUpload={handleSingleUpload}
        batchUploading={batchUploading}
      />
    </div>
  )
}