import { useEffect, useState } from 'react'
import { BarChart3, Clock, Target, MessageCircle, Mail, Copy, Link2, CheckCircle2, FileText, Plus, Send, MessageSquare } from 'lucide-react'
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
  const [whatsappData, setWhatsappData] = useState<Record<string, { status?: string; phone_number?: string }>>({})
  const [engaging, setEngaging] = useState<Record<string, boolean>>({})
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

  // Load WhatsApp data when sessions change
  useEffect(() => {
    if (sessions.length > 0) {
      loadWhatsappData(sessions)
    }
  }, [sessions])

  async function loadWhatsappData(sessions: Session[]) {
    const whatsappDataMap: Record<string, { status?: string; phone_number?: string }> = {}
    
    const promises = sessions.map(async (session) => {
      try {
        const res = await fetch(`${API_BASE}/whatsapp/session/${session.session_id}`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (res.ok) {
          const data = await res.json()
          whatsappDataMap[session.session_id] = {
            status: data.whatsapp_status || 'ready',
            phone_number: data.phone_number
          }
        } else if (res.status === 404) {
          // Session might not have WhatsApp data yet, set default
          whatsappDataMap[session.session_id] = {
            status: 'ready',
            phone_number: undefined
          }
        }
      } catch (error) {
        console.error(`Error loading WhatsApp data for ${session.session_id}:`, error)
      }
    })
    
    await Promise.all(promises)
    setWhatsappData(whatsappDataMap)
  }

  async function engageCandidate(sessionId: string, phoneNumber: string) {
    setEngaging(prev => ({ ...prev, [sessionId]: true }))
    try {
      const res = await fetch(`${API_BASE}/whatsapp/engage`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          phone_number: phoneNumber
        })
      })
      
      if (res.ok) {
        const data = await res.json()
        // Aggiorna lo stato locale
        setWhatsappData(prev => ({
          ...prev,
          [sessionId]: {
            ...prev[sessionId],
            status: 'sent'
          }
        }))
        alert('Messaggio WhatsApp inviato con successo!')
        // Ricarica i dati
        await loadSessions()
      } else {
        const errorData = await res.json().catch(() => ({}))
        alert(`Errore nell'invio: ${errorData.detail || res.statusText}`)
      }
    } catch (error) {
      console.error('Error engaging candidate:', error)
      alert('Errore nell\'invio del messaggio WhatsApp')
    } finally {
      setEngaging(prev => ({ ...prev, [sessionId]: false }))
    }
  }

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
    candidatePhone?: string
    cvFile: File
  }) => {
    try {
      const formData = new FormData()
      formData.append('position_id', data.positionId)
      formData.append('candidate_name', data.candidateName)
      formData.append('candidate_email', data.candidateEmail)
      if (data.candidatePhone) {
        formData.append('candidate_phone', data.candidatePhone)
      }
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
    // Nuova nomenclatura stati
    const statusLower = (status || '').toLowerCase()
    if (statusLower.includes('cv analizzato')) return '#8B5CF6'  // Viola
    if (statusLower.includes('ingaggiato')) return '#3b82f6'    // Blu
    if (statusLower.includes('failed')) return '#ef4444'        // Rosso
    // Legacy
    if (status === 'initialized') return '#f59e0b'
    if (status === 'Colloquio da completare') return '#3b82f6'
    return '#6b7280'
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
          <Plus size={20} style={{ marginRight: '8px' }} />
          Crea Nuove Sessioni
        </button>
      </div>

      {/* Filter Bar */}
      <div className="filter-bar">
        <button 
          className={`filter-button ${statusFilter === 'all' ? 'active' : ''}`}
          onClick={() => setStatusFilter('all')}
        >
          <BarChart3 size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Tutti
        </button>
        <button 
          className={`filter-button ${statusFilter === 'processing' ? 'active' : ''}`}
          onClick={() => setStatusFilter('processing')}
        >
          <Clock size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Batch in corso
        </button>
        <button 
          className={`filter-button ${statusFilter === 'ready' ? 'active' : ''}`}
          onClick={() => setStatusFilter('ready')}
        >
          <Target size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Token pronto
        </button>
        <button 
          className={`filter-button ${statusFilter === 'ongoing' ? 'active' : ''}`}
          onClick={() => setStatusFilter('ongoing')}
        >
          <MessageCircle size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Colloquio in corso
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
              color: 'white'
            }}>
              <BarChart3 size={20} />
            </div>
          <h3>Candidati Attivi ({filteredAndSortedSessions.length})</h3>
        </div>
        
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            <Clock size={24} color="#9CA3AF" style={{ marginBottom: '8px' }} />
            <div style={{ marginTop: '8px' }}>Caricamento sessioni...</div>
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
                      <p className="card-email" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Mail size={14} /> {session.candidate_email}
                      </p>
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
                
                <div className="card-actions">
                  {/* WhatsApp Engage Button - Mostra se c'è numero e status è ready */}
                  {whatsappData[session.session_id]?.phone_number && 
                   whatsappData[session.session_id]?.status === 'ready' && (
                    <button
                      className="engage-whatsapp-btn"
                      onClick={() => {
                        if (confirm('Vuoi inviare il messaggio WhatsApp iniziale a questo candidato?')) {
                          engageCandidate(session.session_id, whatsappData[session.session_id].phone_number!)
                        }
                      }}
                      disabled={engaging[session.session_id]}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '8px 16px',
                        borderRadius: '8px',
                        fontSize: '13px',
                        fontWeight: '600',
                        border: 'none',
                        background: engaging[session.session_id] 
                          ? '#9CA3AF' 
                          : 'linear-gradient(135deg, #8B5CF6, #A78BFA)',
                        color: 'white',
                        cursor: engaging[session.session_id] ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s ease',
                        opacity: engaging[session.session_id] ? 0.7 : 1
                      }}
                    >
                      <Send size={16} />
                      <span>{engaging[session.session_id] ? 'Invio...' : 'Ingaggia WhatsApp'}</span>
                    </button>
                  )}
                  
                  {/* WhatsApp Status Badge */}
                  {whatsappData[session.session_id]?.status && (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '6px 12px',
                      borderRadius: '8px',
                      fontSize: '12px',
                      fontWeight: '500',
                      background: whatsappData[session.session_id].status === 'qualified' ? '#D1FAE5' :
                                 whatsappData[session.session_id].status === 'disqualified' ? '#FEE2E2' :
                                 whatsappData[session.session_id].status === 'active' ? '#DBEAFE' :
                                 whatsappData[session.session_id].status === 'sent' ? '#FEF3C7' :
                                 whatsappData[session.session_id].status === 'ready' ? '#E0E7FF' :
                                 whatsappData[session.session_id].status === 'interrupted' ? '#FEE2E2' :
                                 '#F3F4F6',
                      color: whatsappData[session.session_id].status === 'qualified' ? '#065F46' :
                             whatsappData[session.session_id].status === 'disqualified' ? '#991B1B' :
                             whatsappData[session.session_id].status === 'active' ? '#1E40AF' :
                             whatsappData[session.session_id].status === 'sent' ? '#92400E' :
                             whatsappData[session.session_id].status === 'ready' ? '#3730A3' :
                             whatsappData[session.session_id].status === 'interrupted' ? '#991B1B' :
                             '#374151',
                      border: `1px solid ${
                        whatsappData[session.session_id].status === 'qualified' ? '#10B981' :
                        whatsappData[session.session_id].status === 'disqualified' ? '#EF4444' :
                        whatsappData[session.session_id].status === 'active' ? '#3B82F6' :
                        whatsappData[session.session_id].status === 'sent' ? '#F59E0B' :
                        whatsappData[session.session_id].status === 'ready' ? '#6366F1' :
                        whatsappData[session.session_id].status === 'interrupted' ? '#EF4444' :
                        '#D1D5DB'
                      }`
                    }}>
                      <MessageSquare size={14} />
                      <span>
                        {whatsappData[session.session_id].status === 'ready' ? 'Pronto' :
                         whatsappData[session.session_id].status === 'sent' ? 'Inviato' :
                         whatsappData[session.session_id].status === 'active' ? 'Attivo' :
                         whatsappData[session.session_id].status === 'qualified' ? 'Qualificato' :
                         whatsappData[session.session_id].status === 'disqualified' ? 'Squalificato' :
                         whatsappData[session.session_id].status === 'interrupted' ? 'Interrotto' :
                         whatsappData[session.session_id].status}
                      </span>
                    </div>
                  )}

                  {(session.interview_token || session.status === 'Colloquio da completare') && (
                    <>
                      {session.interview_token ? (
                        <button
                          className="copy-token-btn"
                          onClick={() => {
                            navigator.clipboard.writeText(session.interview_token!)
                            alert('Token copiato!')
                          }}
                        >
                          <Copy size={14} style={{ marginRight: '4px', verticalAlign: 'middle' }} /> Copia Token
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
                          <Link2 size={14} style={{ marginRight: '4px', verticalAlign: 'middle' }} /> Genera Token
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
                          <CheckCircle2 size={14} style={{ marginRight: '4px', verticalAlign: 'middle' }} /> Marca Inviato
                        </button>
                      )}
                    </>
                  )}
                </div>
                
                {session.token_sent && session.token_sent_by && (
                  <div style={{
                    marginTop: '12px',
                    padding: '8px 12px',
                    background: 'var(--bg-success, #d1fae5)',
                    border: '1px solid var(--border-success, #6ee7b7)',
                    borderRadius: '8px',
                    fontSize: '13px',
                    color: 'var(--text-success, #065f46)'
                  }}>
                    ✓ Inviato da: {session.token_sent_by} alle ore {formatDate(session.token_sent_at)}
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
                <FileText size={48} color="#9CA3AF" style={{ marginBottom: '16px' }} />
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