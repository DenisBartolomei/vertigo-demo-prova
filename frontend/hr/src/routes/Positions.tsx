import { useEffect, useState } from 'react'
import { FileText, BarChart3, Clock, Save, Rocket, Trash2, Briefcase, Pin, Settings, ChevronDown, X } from 'lucide-react'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'

interface InterviewConfig {
  reasoning_steps: number
  max_attempts: number
  estimated_duration_minutes: number
  max_questions: number
}

export function Positions() {
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ position_id: '', position_name: '', job_description: '', seniority_level: 'Mid-Level', hr_special_needs: '' })
  const [kbDocs, setKbDocs] = useState<{ title: string; content: string }[]>([])
  const [expanded, setExpanded] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Record<string, 'text' | 'cases' | 'evaluation' | null>>({})
  const [details, setDetails] = useState<Record<string, any>>({})
  const [editedCriteria, setEditedCriteria] = useState<Record<string, any>>({})
  const [savingCriteria, setSavingCriteria] = useState(false)
  const [isPreparing, setIsPreparing] = useState(false)
  const [isCreateFormExpanded, setIsCreateFormExpanded] = useState(false)
  const [expandedCriteria, setExpandedCriteria] = useState<Record<string, Set<number>>>({})
  
  // Interview configuration states
  const [showInterviewConfig, setShowInterviewConfig] = useState(false)
  const [interviewConfig, setInterviewConfig] = useState<InterviewConfig>({
    reasoning_steps: 4,
    max_attempts: 5,
    estimated_duration_minutes: 35,
    max_questions: 11
  })
  const [configLoading, setConfigLoading] = useState(false)
  const [configSaving, setConfigSaving] = useState(false)
  const [configMessage, setConfigMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  
  const token = localStorage.getItem('hr_jwt')

  async function load() {
    setLoading(true)
    const resp = await fetch(`${API_BASE}/positions`, { headers: { Authorization: `Bearer ${token}` } })
    if (resp.ok) {
      const data = await resp.json()
      setItems(data.positions || [])
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  async function upsertPosition() {
    setIsPreparing(true)
    
    try {
      console.log('Creating position with form:', form)
      
      // First save the position
      const resp = await fetch(`${API_BASE}/positions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ...form, knowledge_base: kbDocs })
      })
      
      if (resp.ok) {
        const result = await resp.json()
        console.log('Position creation result:', result)
        const positionId = result.position_id || form.position_id
        
        console.log('Using position_id:', positionId)
        
        // If save successful and we have a position_id, automatically run data preparation
        if (positionId && positionId.trim() !== '') {
          try {
            console.log(`Running data prep for position: ${positionId}`)
            await fetch(`${API_BASE}/positions/${positionId}/data-prep`, { 
              method: 'POST', 
              headers: { Authorization: `Bearer ${token}` } 
            })
            alert('Posizione salvata e preparazione dati avviata!')
          } catch (error) {
            console.error('Data prep error:', error)
            alert('Posizione salvata ma la preparazione dati è fallita. Puoi eseguirla manualmente.')
          }
        } else {
          console.log('No valid position_id, skipping data prep')
          alert('Posizione salvata!')
        }
      } else {
        const error = await resp.json()
        console.error('Position creation failed:', error)
        alert(`Errore nel salvataggio: ${error.detail || 'Errore sconosciuto'}`)
      }
      
      setForm({ position_id: '', position_name: '', job_description: '', seniority_level: 'Mid-Level', hr_special_needs: '' })
      setKbDocs([])
      await load()
    } finally {
      setIsPreparing(false)
    }
  }

  async function runPrep(id: string) {
    setIsPreparing(true)
    try {
      await fetch(`${API_BASE}/positions/${id}/data-prep`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } })
      alert('Preparazione dati avviata!')
      await load()
    } finally {
      setIsPreparing(false)
    }
  }

  async function deletePosition(id: string, name: string) {
    if (!id || id.trim() === '') {
      alert('Errore: ID posizione non valido')
      return
    }
    
    if (!confirm(`Sei sicuro di voler eliminare la posizione "${name}"? Questa azione non può essere annullata.`)) {
      return
    }
    
    try {
      console.log(`Deleting position with ID: ${id}`)
      const resp = await fetch(`${API_BASE}/positions/${id}`, { 
        method: 'DELETE', 
        headers: { Authorization: `Bearer ${token}` } 
      })
      
      if (resp.ok) {
        alert('Posizione eliminata con successo!')
        await load()
      } else {
        const error = await resp.json()
        alert(`Errore nell'eliminazione: ${error.detail || 'Errore sconosciuto'}`)
      }
    } catch (error) {
      console.error('Delete error:', error)
      alert('Errore di connessione durante l\'eliminazione della posizione.')
    }
  }

  async function toggleExpand(id: string) {
    setExpanded(prev => (prev === id ? null : id))
    if (!details[id]) {
      const res = await fetch(`${API_BASE}/positions/${id}`, { headers: { Authorization: `Bearer ${token}` } })
      if (res.ok) {
        const d = await res.json()
        setDetails(prev => ({ ...prev, [id]: d }))
      }
    }
  }

  function handleTabClick(positionId: string, tab: 'text' | 'cases' | 'evaluation') {
    setActiveTab(prev => ({
      ...prev,
      [positionId]: prev[positionId] === tab ? null : tab
    }))
  }

  function initializeEditedCriteria(positionId: string, criteria: any) {
    if (!editedCriteria[positionId] && criteria?.evaluation_schema) {
      // Clone and migrate old format if needed
      const clonedSchema = JSON.parse(JSON.stringify(criteria.evaluation_schema))
      
      // Migrate old format (evaluation_criteria) to new format (evaluation_criteria_1)
      const migratedSchema = clonedSchema.map((req: any) => {
        if (req.criteria && req.criteria.evaluation_criteria && !req.criteria.evaluation_criteria_1) {
          // Old format detected - migrate to new format
          return {
            ...req,
            criteria: {
              evaluation_criteria_1: req.criteria.evaluation_criteria
            }
          }
        }
        return req
      })
      
      setEditedCriteria(prev => ({
        ...prev,
        [positionId]: migratedSchema
      }))
    }
  }

  function updateCriterion(positionId: string, reqIndex: number, field: 'evaluation_criteria_1', value: string) {
    setEditedCriteria(prev => {
      const updated = { ...prev }
      if (!updated[positionId]) {
        updated[positionId] = []
      }
      updated[positionId] = [...updated[positionId]]
      updated[positionId][reqIndex] = {
        ...updated[positionId][reqIndex],
        criteria: {
          ...updated[positionId][reqIndex].criteria,
          [field]: value
        }
      }
      return updated
    })
  }

  // Toggle criterion expansion
  function toggleCriterionExpansion(positionId: string, criterionIndex: number) {
    setExpandedCriteria(prev => {
      const positionCriteria = prev[positionId] || new Set<number>()
      const newSet = new Set(positionCriteria)
      
      if (newSet.has(criterionIndex)) {
        newSet.delete(criterionIndex)
      } else {
        newSet.add(criterionIndex)
      }
      
      return {
        ...prev,
        [positionId]: newSet
      }
    })
  }

  // Check if criterion is expanded
  function isCriterionExpanded(positionId: string, criterionIndex: number): boolean {
    return expandedCriteria[positionId]?.has(criterionIndex) || false
  }

  async function saveCriteria(positionId: string) {
    setSavingCriteria(true)
    try {
      const resp = await fetch(`${API_BASE}/positions/${positionId}/evaluation-criteria`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ evaluation_schema: editedCriteria[positionId] })
      })

      if (resp.ok) {
        alert('Criteri di valutazione aggiornati con successo!')
        // Ricarica i dettagli della posizione
        const res = await fetch(`${API_BASE}/positions/${positionId}`, { headers: { Authorization: `Bearer ${token}` } })
        if (res.ok) {
          const d = await res.json()
          setDetails(prev => ({ ...prev, [positionId]: d }))
          setEditedCriteria(prev => ({ ...prev, [positionId]: null }))
        }
      } else {
        const error = await resp.json()
        alert(`Errore nel salvataggio: ${error.detail || 'Errore sconosciuto'}`)
      }
    } catch (error) {
      console.error('Save error:', error)
      alert('Errore di connessione durante il salvataggio.')
    } finally {
      setSavingCriteria(false)
    }
  }

  function addKb() {
    setKbDocs(prev => [...prev, { title: '', content: '' }])
  }

  function updateKb(idx: number, field: 'title' | 'content', value: string) {
    setKbDocs(prev => prev.map((d, i) => i === idx ? { ...d, [field]: value } : d))
  }

  function removeKb(idx: number) {
    setKbDocs(prev => prev.filter((_, i) => i !== idx))
  }

  // Interview configuration functions
  const loadInterviewConfig = async () => {
    setConfigLoading(true)
    try {
      const response = await fetch(`${API_BASE}/interview-config`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setInterviewConfig(data)
      }
    } catch (error) {
      console.error('Error loading config:', error)
    } finally {
      setConfigLoading(false)
    }
  }

  const saveInterviewConfig = async () => {
    setConfigSaving(true)
    setConfigMessage(null)
    
    try {
      const response = await fetch(`${API_BASE}/interview-config`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          reasoning_steps: interviewConfig.reasoning_steps,
          max_attempts: interviewConfig.max_attempts
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setInterviewConfig(data)
        setConfigMessage({ type: 'success', text: 'Configurazione salvata con successo!' })
      } else {
        const error = await response.json()
        setConfigMessage({ type: 'error', text: error.detail || 'Errore nel salvataggio' })
      }
    } catch (error) {
      setConfigMessage({ type: 'error', text: 'Errore di connessione' })
    } finally {
      setConfigSaving(false)
    }
  }

  const updateInterviewConfig = (field: keyof InterviewConfig, value: number) => {
    setInterviewConfig(prev => {
      const updated = { ...prev, [field]: value }
      
      // Ricalcola automaticamente i valori derivati
      if (field === 'reasoning_steps' || field === 'max_attempts') {
        updated.estimated_duration_minutes = Math.round((updated.reasoning_steps * updated.max_attempts * 1.5) + 5)
        updated.max_questions = (updated.reasoning_steps * 2) + 3
      }
      
      return updated
    })
  }

  useEffect(() => {
    if (showInterviewConfig) {
      loadInterviewConfig()
    }
  }, [showInterviewConfig])

  return (
    <div className="container" style={{ display: 'grid', gap: '32px', position: 'relative' }}>
      {/* Loading Notification - Non bloccante */}
      {isPreparing && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          background: 'white',
          padding: '24px',
          borderRadius: 'var(--radius-xl)',
          boxShadow: 'var(--shadow-lg)',
          maxWidth: '400px',
          zIndex: 9999,
          border: '2px solid var(--primary-purple)'
        }}>
          <div style={{ 
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            marginBottom: '16px'
          }}>
            <Settings size={32} color="#7C3AED" style={{ marginRight: '12px' }} />
            <button
              onClick={() => setIsPreparing(false)}
              style={{
                background: 'transparent',
                border: 'none',
                fontSize: '20px',
                cursor: 'pointer',
                color: 'var(--text-secondary)',
                padding: '0',
                width: '24px',
                height: '24px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: '50%',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--bg-secondary)'
                e.currentTarget.style.color = 'var(--text-primary)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent'
                e.currentTarget.style.color = 'var(--text-secondary)'
              }}
            >
              <X size={16} />
            </button>
          </div>
          <h3 style={{ 
            fontSize: '18px', 
            fontWeight: '600', 
            marginBottom: '8px',
            color: 'var(--text-primary)'
          }}>
            Preparazione in corso...
          </h3>
          <p style={{ 
            fontSize: '14px', 
            color: 'var(--text-secondary)',
            lineHeight: '1.5',
            marginBottom: '12px'
          }}>
            Stiamo generando i casi di studio e i criteri di valutazione per questa posizione. Questo processo può richiedere alcuni minuti.
          </p>
          <div style={{
            background: 'var(--light-purple)',
            padding: '8px 12px',
            borderRadius: 'var(--radius-md)',
            fontSize: '12px',
            color: 'var(--text-secondary)'
          }}>
            <Clock size={14} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }} /> Il processo continua in background
          </div>
        </div>
      )}
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Annunci</h2>
          <p className="muted">Crea e gestisci le posizioni lavorative per i colloqui dei candidati</p>
        </div>
        <button
          onClick={() => setShowInterviewConfig(true)}
          style={{
            background: 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
            color: 'white',
            border: 'none',
            padding: '12px 24px',
            borderRadius: '8px',
            fontSize: '14px',
            fontWeight: '600',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            transition: 'all 0.2s ease',
            boxShadow: '0 2px 8px rgba(124, 58, 237, 0.2)',
            marginTop: '8px'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)'
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(124, 58, 237, 0.3)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = '0 2px 8px rgba(124, 58, 237, 0.2)'
          }}
        >
          <Settings size={18} />
          Configura colloqui
        </button>
      </div>
      
      {/* Form */}
      <div className="card fade-in">
        <div 
          onClick={() => setIsCreateFormExpanded(!isCreateFormExpanded)}
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            marginBottom: isCreateFormExpanded ? '24px' : '0',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: '8px',
            transition: 'background 0.2s ease'
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-secondary)'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
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
              <FileText size={20} />
            </div>
            <h3>Crea Nuova Posizione</h3>
          </div>
          <ChevronDown size={20} style={{
            transform: isCreateFormExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.3s ease'
          }} />
        </div>
        
        {isCreateFormExpanded && (
          <div style={{ display: 'grid', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: 'var(--text-primary)' }}>
              ID Posizione
            </label>
            <input placeholder="es. senior-dev-2024" value={form.position_id} onChange={e => setForm({ ...form, position_id: e.target.value })} />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: 'var(--text-primary)' }}>
              Titolo Posizione
            </label>
            <input placeholder="es. Senior Software Engineer" value={form.position_name} onChange={e => setForm({ ...form, position_name: e.target.value })} />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: 'var(--text-primary)' }}>
              Livello di Seniority
            </label>
            <select value={form.seniority_level} onChange={e => setForm({ ...form, seniority_level: e.target.value })}>
              <option>Junior</option>
              <option>Mid-Level</option>
              <option>Senior</option>
              <option>Lead</option>
            </select>
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: 'var(--text-primary)' }}>
              Descrizione del Lavoro
            </label>
            <textarea placeholder="Descrivi il ruolo, le responsabilità e i requisiti..." value={form.job_description} onChange={e => setForm({ ...form, job_description: e.target.value })} rows={6}></textarea>
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: 'var(--text-primary)' }}>
              Esigenze Speciali HR (Opzionale)
            </label>
            <textarea placeholder="Eventuali requisiti specifici o preferenze da parte dell'HR..." value={form.hr_special_needs} onChange={e => setForm({ ...form, hr_special_needs: e.target.value })} rows={3}></textarea>
          </div>
          
          {/* Knowledge Base */}
          <div>
            <label style={{ display: 'block', marginBottom: '12px', fontWeight: '500', color: 'var(--text-primary)' }}>
              Documenti Knowledge Base
            </label>
            <div style={{ display: 'grid', gap: '12px' }}>
              {kbDocs.map((d, idx) => (
                <div key={idx} style={{ 
                  padding: '16px', 
                  background: 'var(--bg-secondary)', 
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-light)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <span style={{ fontSize: '14px', fontWeight: '500', color: 'var(--text-secondary)' }}>
                      Document {idx + 1}
                    </span>
                    <button 
                      type="button" 
                      onClick={() => removeKb(idx)}
                      style={{ 
                        background: '#FEE2E2', 
                        color: '#991B1B', 
                        border: 'none', 
                        borderRadius: '4px', 
                        padding: '4px 8px', 
                        fontSize: '12px',
                        cursor: 'pointer'
                      }}
                    >
                      Rimuovi
                    </button>
                  </div>
                  <input 
                    placeholder="Titolo documento (nome file)" 
                    value={d.title} 
                    onChange={e => updateKb(idx, 'title', e.target.value)} 
                    style={{ marginBottom: '8px' }}
                  />
                  <textarea 
                    placeholder="Contenuto documento..." 
                    value={d.content} 
                    onChange={e => updateKb(idx, 'content', e.target.value)} 
                    rows={3}
                  />
                </div>
              ))}
            </div>
            <button 
              type="button" 
              onClick={addKb} 
              className="secondary"
              style={{ marginTop: '12px', width: 'auto' }}
            >
              + Aggiungi Documento
            </button>
          </div>
          
          <button 
            onClick={upsertPosition}
            disabled={!form.position_name || !form.job_description}
            style={{ width: '100%', justifyContent: 'center', marginTop: '8px' }}
          >
            <Save size={18} style={{ marginRight: '8px' }} /> Salva Posizione & Avvia Preparazione Dati
          </button>
          </div>
        )}
      </div>

      {/* Existing Positions */}
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
          <h3>Posizioni Esistenti</h3>
        </div>
        
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            <Clock size={24} color="#9CA3AF" style={{ marginBottom: '8px' }} />
            <div style={{ marginTop: '8px' }}>Caricamento posizioni...</div>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '20px' }}>
            {items.length === 0 ? (
              <div style={{ 
                textAlign: 'center', 
                padding: '40px', 
                color: 'var(--text-muted)',
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-lg)'
              }}>
                <FileText size={48} color="#9CA3AF" style={{ marginBottom: '16px' }} />
                <div style={{ fontSize: '18px', marginBottom: '8px' }}>Nessuna posizione ancora</div>
                <div>Crea la tua prima posizione qui sopra</div>
              </div>
            ) : (
              items.map((p) => {
                const isExpanded = expanded === p._id
                const info = details[p._id]
                const hasCases = !!(info && info.all_cases && Array.isArray(info.all_cases.cases) && info.all_cases.cases.length > 0)
                
                return (
                  <div key={p._id} className="card" style={{ 
                    border: hasCases ? '2px solid var(--primary-purple)' : '1px solid var(--border-light)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                      <div>
                        <h4 style={{ fontSize: '18px', fontWeight: '600', margin: 0, marginBottom: '4px' }}>
                          {p.position_name}
                        </h4>
                        <div className="muted" style={{ fontSize: '14px' }}>
                          ID: {p._id}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        {hasCases && (
                          <div className="status-indicator status-completed">
                            <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#065F46' }}></div>
                            Pronto per i colloqui
                          </div>
                        )}
                        <button 
                          onClick={() => toggleExpand(p._id)}
                          className="secondary"
                          style={{ width: 'auto' }}
                        >
                          {isExpanded ? 'Nascondi' : 'Mostra'} Dettagli
                        </button>
                      </div>
                    </div>
                    
                    {isExpanded && (
                      <div style={{ marginTop: '20px' }}>
                        {/* Tab Navigation */}
                        <div style={{ 
                          display: 'flex', 
                          gap: '8px', 
                          marginBottom: '20px',
                          borderBottom: '2px solid var(--border-light)'
                        }}>
                          <button
                            onClick={() => handleTabClick(p._id, 'text')}
                            style={{
                              padding: '12px 24px',
                              background: activeTab[p._id] === 'text' ? 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))' : 'transparent',
                              color: activeTab[p._id] === 'text' ? 'white' : 'var(--text-primary)',
                              border: 'none',
                              borderBottom: activeTab[p._id] === 'text' ? '3px solid var(--primary-purple)' : '3px solid transparent',
                              borderRadius: '8px 8px 0 0',
                              fontSize: '14px',
                              fontWeight: '600',
                              cursor: 'pointer',
                              transition: 'all 0.2s ease'
                            }}
                          >
                            <FileText size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Testo annuncio
                          </button>
                          <button
                            onClick={() => handleTabClick(p._id, 'cases')}
                            style={{
                              padding: '12px 24px',
                              background: activeTab[p._id] === 'cases' ? 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))' : 'transparent',
                              color: activeTab[p._id] === 'cases' ? 'white' : 'var(--text-primary)',
                              border: 'none',
                              borderBottom: activeTab[p._id] === 'cases' ? '3px solid var(--primary-purple)' : '3px solid transparent',
                              borderRadius: '8px 8px 0 0',
                              fontSize: '14px',
                              fontWeight: '600',
                              cursor: 'pointer',
                              transition: 'all 0.2s ease'
                            }}
                          >
                            <Briefcase size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Casi da colloquio
                          </button>
                          <button
                            onClick={() => {
                              handleTabClick(p._id, 'evaluation')
                              if (info?.evaluation_criteria) {
                                initializeEditedCriteria(p._id, info.evaluation_criteria)
                              }
                            }}
                            style={{
                              padding: '12px 24px',
                              background: activeTab[p._id] === 'evaluation' ? 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))' : 'transparent',
                              color: activeTab[p._id] === 'evaluation' ? 'white' : 'var(--text-primary)',
                              border: 'none',
                              borderBottom: activeTab[p._id] === 'evaluation' ? '3px solid var(--primary-purple)' : '3px solid transparent',
                              borderRadius: '8px 8px 0 0',
                              fontSize: '14px',
                              fontWeight: '600',
                              cursor: 'pointer',
                              transition: 'all 0.2s ease'
                            }}
                          >
                            <BarChart3 size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Griglia valutativa
                          </button>
                        </div>

                        {/* Tab Content */}
                        {info ? (
                          <div style={{ 
                            padding: '20px', 
                            background: 'linear-gradient(135deg, var(--light-purple), var(--pastel-pink))', 
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid rgba(139, 92, 246, 0.2)'
                          }}>
                            {/* Testo annuncio Tab */}
                            {activeTab[p._id] === 'text' && (
                              <div style={{ display: 'grid', gap: '20px' }}>
                                <div>
                                  <div style={{ color: 'var(--text-secondary)', fontSize: '12px', fontWeight: '500', marginBottom: '8px' }}>
                                    LIVELLO DI SENIORITY
                                  </div>
                                  <div style={{ 
                                    fontSize: '16px', 
                                    fontWeight: '500',
                                    padding: '12px',
                                    background: 'rgba(255, 255, 255, 0.7)',
                                    borderRadius: 'var(--radius-md)'
                                  }}>
                                    {info.seniority_level || '—'}
                                  </div>
                                </div>

                                <div>
                                  <div style={{ color: 'var(--text-secondary)', fontSize: '12px', fontWeight: '500', marginBottom: '8px' }}>
                                    DESCRIZIONE DEL LAVORO
                                  </div>
                                  <div style={{ 
                                    whiteSpace: 'pre-wrap',
                                    padding: '16px',
                                    background: 'rgba(255, 255, 255, 0.7)',
                                    borderRadius: 'var(--radius-md)',
                                    fontSize: '14px',
                                    lineHeight: '1.6'
                                  }}>
                                    {info.job_description || '—'}
                                  </div>
                                </div>

                                {info.hr_special_needs && (
                                  <div>
                                    <div style={{ color: 'var(--text-secondary)', fontSize: '12px', fontWeight: '500', marginBottom: '8px' }}>
                                      ESIGENZE SPECIALI HR
                                    </div>
                                    <div style={{ 
                                      whiteSpace: 'pre-wrap',
                                      padding: '16px',
                                      background: 'rgba(255, 255, 255, 0.7)',
                                      borderRadius: 'var(--radius-md)',
                                      fontSize: '14px',
                                      lineHeight: '1.6'
                                    }}>
                                      {info.hr_special_needs}
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Casi da colloquio Tab */}
                            {activeTab[p._id] === 'cases' && (
                              <div>
                                <div style={{ color: 'var(--text-secondary)', fontSize: '12px', fontWeight: '500', marginBottom: '8px' }}>
                                  CASI GENERATI
                                </div>
                                {hasCases ? (
                                  <div style={{ display: 'grid', gap: '12px' }}>
                                    {info.all_cases.cases.map((c: any) => (
                                      <div key={c.question_id} style={{ 
                                        padding: '16px', 
                                        background: 'rgba(255, 255, 255, 0.7)', 
                                        borderRadius: 'var(--radius-md)',
                                        border: '1px solid rgba(139, 92, 246, 0.1)'
                                      }}>
                                        <div style={{ fontWeight: '600', marginBottom: '8px', color: 'var(--text-primary)' }}>
                                          {c.question_title}
                                        </div>
                                        <div style={{ 
                                          whiteSpace: 'pre-wrap', 
                                          color: 'var(--text-secondary)', 
                                          marginBottom: '12px',
                                          fontSize: '14px',
                                          lineHeight: '1.5'
                                        }}>
                                          {c.question_text}
                                        </div>
                                        <div>
                                          <div style={{ color: 'var(--text-primary)', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
                                            Passaggi di Ragionamento
                                          </div>
                                          <ul style={{ paddingLeft: '16px', fontSize: '14px' }}>
                                            {c.reasoning_steps?.map((s: any) => (
                                              <li key={s.id} style={{ marginBottom: '8px', lineHeight: '1.4' }}>
                                                <strong>Passaggio {s.id}:</strong> {s.title}
                                                <div style={{ color: 'var(--text-secondary)', marginTop: '2px' }}>
                                                  {s.description}
                                                </div>
                                                {Array.isArray(s.skills_to_test) && s.skills_to_test.length > 0 && (
                                                  <div style={{ 
                                                    fontSize: '12px', 
                                                    color: 'var(--text-muted)', 
                                                    marginTop: '4px',
                                                    background: 'rgba(139, 92, 246, 0.1)',
                                                    padding: '2px 6px',
                                                    borderRadius: '4px',
                                                    display: 'inline-block'
                                                  }}>
                                                    Competenze: {s.skills_to_test.map((x: any) => x.skill_name).filter(Boolean).join(', ') || '—'}
                                                  </div>
                                                )}
                                              </li>
                                            ))}
                                          </ul>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <div style={{ 
                                    textAlign: 'center', 
                                    padding: '20px', 
                                    color: 'var(--text-muted)',
                                    background: 'rgba(255, 255, 255, 0.5)',
                                    borderRadius: 'var(--radius-md)'
                                  }}>
                                    <Clock size={24} color="#9CA3AF" style={{ marginBottom: '8px' }} />
                                    <div style={{ marginTop: '8px' }}>Nessun caso disponibile ancora. Esegui la preparazione dati per generare i casi di colloquio.</div>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Griglia valutativa Tab */}
                            {activeTab[p._id] === 'evaluation' && (
                              <div>
                                <div style={{ color: 'var(--text-secondary)', fontSize: '12px', fontWeight: '500', marginBottom: '12px' }}>
                                  CRITERI DI VALUTAZIONE
                                </div>
                                {info.evaluation_criteria?.evaluation_schema ? (
                                  <div>
                                    <div style={{ display: 'grid', gap: '16px', marginBottom: '20px' }}>
                                      {(editedCriteria[p._id] || info.evaluation_criteria.evaluation_schema).map((req: any, idx: number) => {
                                        const isExpanded = isCriterionExpanded(p._id, idx)
                                        
                                        return (
                                          <div key={idx} style={{ 
                                            padding: '16px', 
                                            background: 'rgba(255, 255, 255, 0.7)', 
                                            borderRadius: 'var(--radius-md)',
                                            border: '1px solid rgba(139, 92, 246, 0.1)',
                                            transition: 'all 0.2s ease'
                                          }}>
                                            <div style={{ 
                                              display: 'flex',
                                              justifyContent: 'space-between',
                                              alignItems: 'center',
                                              marginBottom: isExpanded ? '12px' : '0'
                                            }}>
                                              <div style={{ 
                                                fontWeight: '600', 
                                                color: 'var(--text-primary)',
                                                fontSize: '15px',
                                                padding: '8px',
                                                background: 'rgba(139, 92, 246, 0.1)',
                                                borderRadius: '6px',
                                                flex: 1
                                              }}>
                                                <Pin size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> {req.requirement}
                                              </div>
                                              <button
                                                onClick={() => toggleCriterionExpansion(p._id, idx)}
                                                style={{
                                                  marginLeft: '12px',
                                                  padding: '8px 16px',
                                                  background: isExpanded ? 'rgba(139, 92, 246, 0.15)' : 'rgba(139, 92, 246, 0.08)',
                                                  border: '1px solid rgba(139, 92, 246, 0.3)',
                                                  borderRadius: '6px',
                                                  color: 'var(--primary-purple)',
                                                  fontSize: '13px',
                                                  fontWeight: '600',
                                                  cursor: 'pointer',
                                                  transition: 'all 0.2s ease',
                                                  display: 'flex',
                                                  alignItems: 'center',
                                                  gap: '6px',
                                                  whiteSpace: 'nowrap'
                                                }}
                                                onMouseOver={(e) => {
                                                  e.currentTarget.style.background = 'rgba(139, 92, 246, 0.2)'
                                                  e.currentTarget.style.transform = 'scale(1.02)'
                                                }}
                                                onMouseOut={(e) => {
                                                  e.currentTarget.style.background = isExpanded ? 'rgba(139, 92, 246, 0.15)' : 'rgba(139, 92, 246, 0.08)'
                                                  e.currentTarget.style.transform = 'scale(1)'
                                                }}
                                              >
                                                <span>{isExpanded ? '▼' : '▶'}</span>
                                                <span>{isExpanded ? 'Nascondi' : 'Visualizza e modifica'}</span>
                                              </button>
                                            </div>
                                            
                                            {isExpanded && (
                                              <div style={{
                                                marginTop: '12px',
                                                animation: 'fadeIn 0.2s ease-in'
                                              }}>
                                                <label style={{ 
                                                  display: 'block', 
                                                  fontSize: '13px', 
                                                  fontWeight: '500', 
                                                  color: 'var(--text-secondary)',
                                                  marginBottom: '6px' 
                                                }}>
                                                  Criterio di Valutazione
                                                </label>
                                                <textarea
                                                  value={editedCriteria[p._id]?.[idx]?.criteria?.evaluation_criteria_1 || req.criteria?.evaluation_criteria_1 || req.criteria?.evaluation_criteria || ''}
                                                  onChange={(e) => updateCriterion(p._id, idx, 'evaluation_criteria_1', e.target.value)}
                                                  rows={4}
                                                  style={{ 
                                                    width: '100%', 
                                                    padding: '10px',
                                                    fontSize: '14px',
                                                    borderRadius: '6px',
                                                    border: '1px solid rgba(139, 92, 246, 0.3)',
                                                    background: 'white'
                                                  }}
                                                />
                                              </div>
                                            )}
                                          </div>
                                        )
                                      })}
                                    </div>
                                    {editedCriteria[p._id] && (
                                      <button
                                        onClick={() => saveCriteria(p._id)}
                                        disabled={savingCriteria}
                                        style={{
                                          width: '100%',
                                          padding: '12px',
                                          background: savingCriteria ? '#94a3b8' : 'linear-gradient(135deg, #10b981, #059669)',
                                          color: 'white',
                                          border: 'none',
                                          borderRadius: '8px',
                                          fontSize: '15px',
                                          fontWeight: '600',
                                          cursor: savingCriteria ? 'not-allowed' : 'pointer',
                                          transition: 'all 0.2s ease'
                                        }}
                                      >
                                        {savingCriteria ? (
                                          <>
                                            <Clock size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Salvataggio...
                                          </>
                                        ) : (
                                          <>
                                            <Save size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Salva Modifiche
                                          </>
                                        )}
                                      </button>
                                    )}
                                  </div>
                                ) : (
                                  <div style={{ 
                                    textAlign: 'center', 
                                    padding: '20px', 
                                    color: 'var(--text-muted)',
                                    background: 'rgba(255, 255, 255, 0.5)',
                                    borderRadius: 'var(--radius-md)'
                                  }}>
                                    <Clock size={24} color="#9CA3AF" style={{ marginBottom: '8px' }} />
                                    <div style={{ marginTop: '8px' }}>Nessun criterio di valutazione disponibile. Esegui la preparazione dati per generarli.</div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div style={{ 
                            textAlign: 'center', 
                            padding: '20px', 
                            color: 'var(--text-muted)',
                            background: 'linear-gradient(135deg, var(--light-purple), var(--pastel-pink))',
                            borderRadius: 'var(--radius-md)'
                          }}>
                            <Clock size={24} color="#9CA3AF" style={{ marginBottom: '8px' }} />
                            <div style={{ marginTop: '8px' }}>Caricamento dettagli...</div>
                          </div>
                        )}
                        
                        {/* Action Buttons */}
                        <div style={{ 
                          display: 'flex', 
                          gap: '12px', 
                          marginTop: '20px'
                        }}>
                          <button 
                            onClick={() => runPrep(p._id)}
                            disabled={isPreparing}
                            className="primary"
                            style={{ flex: 1 }}
                          >
                            {isPreparing ? (
                              <>
                                <Clock size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Elaborazione...
                              </>
                            ) : (
                              <>
                                <Rocket size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Esegui Preparazione Dati
                              </>
                            )}
                          </button>
                          <button 
                            onClick={() => deletePosition(p._id, p.position_name)}
                            className="secondary"
                            style={{ 
                              background: '#FEE2E2', 
                              color: '#991B1B', 
                              border: '1px solid #FECACA',
                              flex: '0 0 auto',
                              minWidth: '120px'
                            }}
                          >
                            <Trash2 size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Elimina
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>
        )}
      </div>

      {/* Interview Configuration Modal */}
      {showInterviewConfig && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10000,
            padding: '20px'
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowInterviewConfig(false)
            }
          }}
        >
          <div
            className="card fade-in"
            style={{
              maxWidth: '700px',
              width: '100%',
              maxHeight: '90vh',
              overflow: 'auto',
              position: 'relative'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button
              onClick={() => setShowInterviewConfig(false)}
              style={{
                position: 'absolute',
                top: '16px',
                right: '16px',
                background: 'transparent',
                border: 'none',
                fontSize: '24px',
                cursor: 'pointer',
                color: 'var(--text-secondary)',
                padding: '4px',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '32px',
                height: '32px',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--bg-secondary)'
                e.currentTarget.style.color = 'var(--text-primary)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent'
                e.currentTarget.style.color = 'var(--text-secondary)'
              }}
            >
              <X size={20} />
            </button>

            <div style={{ marginBottom: '24px' }}>
              <h2 style={{ margin: 0, fontSize: '20px', fontWeight: '600', color: 'var(--primary-purple)' }}>
                Configurazione Interviste
              </h2>
              <p style={{ margin: '8px 0 0 0', fontSize: '14px', color: 'var(--text-secondary)' }}>
                Personalizza la durata e la complessità dei colloqui
              </p>
            </div>

            {configMessage && (
              <div style={{
                marginBottom: '20px',
                padding: '12px',
                borderRadius: '8px',
                backgroundColor: configMessage.type === 'success' ? '#d4edda' : '#f8d7da',
                color: configMessage.type === 'success' ? '#155724' : '#721c24',
                border: `1px solid ${configMessage.type === 'success' ? '#c3e6cb' : '#f5c6cb'}`
              }}>
                {configMessage.text}
              </div>
            )}

            {configLoading ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <Clock size={24} color="#9CA3AF" style={{ marginBottom: '8px' }} />
                <div style={{ marginTop: '8px' }}>Caricamento configurazione...</div>
              </div>
            ) : (
              <div style={{ display: 'grid', gap: '24px' }}>
                {/* Reasoning Steps */}
                <div>
                  <label style={{ display: 'block', fontSize: '16px', fontWeight: '500', color: 'var(--text-primary)', marginBottom: '12px' }}>
                    Numero di Reasoning Steps
                  </label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <input
                      type="range"
                      min="2"
                      max="5"
                      value={interviewConfig.reasoning_steps}
                      onChange={(e) => updateInterviewConfig('reasoning_steps', parseInt(e.target.value))}
                      style={{ flex: 1, height: '8px', borderRadius: '4px', background: '#e2e8f0' }}
                    />
                    <div style={{ 
                      fontSize: '24px', 
                      fontWeight: '700', 
                      color: 'var(--primary-purple)',
                      minWidth: '40px',
                      textAlign: 'center'
                    }}>
                      {interviewConfig.reasoning_steps}
                    </div>
                  </div>
                  <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: '1.4' }}>
                    I reasoning steps sono i passaggi logici che l'agente AI segue per guidare il candidato attraverso la risoluzione del case study.
                  </p>
                </div>

                {/* Max Attempts */}
                <div>
                  <label style={{ display: 'block', fontSize: '16px', fontWeight: '500', color: 'var(--text-primary)', marginBottom: '12px' }}>
                    Tentativi Massimi per Step
                  </label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <input
                      type="range"
                      min="2"
                      max="4"
                      value={interviewConfig.max_attempts}
                      onChange={(e) => updateInterviewConfig('max_attempts', parseInt(e.target.value))}
                      style={{ flex: 1, height: '8px', borderRadius: '4px', background: '#e2e8f0' }}
                    />
                    <div style={{ 
                      fontSize: '24px', 
                      fontWeight: '700', 
                      color: 'var(--primary-purple)',
                      minWidth: '40px',
                      textAlign: 'center'
                    }}>
                      {interviewConfig.max_attempts}
                    </div>
                  </div>
                  <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: '1.4' }}>
                    Numero massimo di tentativi che l'agente intervistatore concede al candidato per completare ogni reasoning step.
                  </p>
                </div>

                {/* Stime Calcolate */}
                <div style={{ 
                  padding: '20px',
                  borderRadius: '12px',
                  border: '1px solid var(--border-light)',
                  background: 'var(--bg-secondary)'
                }}>
                  <h3 style={{ margin: '0 0 16px 0', fontSize: '18px', fontWeight: '600', color: 'var(--text-primary)' }}>
                    <BarChart3 size={18} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> Stime Calcolate
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div>
                      <div style={{ fontSize: '12px', marginBottom: '4px', color: 'var(--text-secondary)' }}>Durata Stimata</div>
                      <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--text-primary)' }}>{interviewConfig.estimated_duration_minutes} min</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', marginBottom: '4px', color: 'var(--text-secondary)' }}>Domande Massime</div>
                      <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--text-primary)' }}>{interviewConfig.max_questions}</div>
                    </div>
                  </div>
                  <p style={{ fontSize: '12px', marginTop: '12px', margin: '12px 0 0 0', color: 'var(--text-secondary)' }}>
                    * Stima basata su 1.5 minuti per tentativo + 5 minuti per setup iniziale
                  </p>
                </div>

                {/* Pulsante Salva */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                  <button
                    onClick={() => setShowInterviewConfig(false)}
                    style={{
                      background: 'var(--bg-secondary)',
                      color: 'var(--text-primary)',
                      border: '1px solid var(--border-light)',
                      padding: '12px 24px',
                      borderRadius: '8px',
                      fontSize: '16px',
                      fontWeight: '600',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    Annulla
                  </button>
                  <button
                    onClick={saveInterviewConfig}
                    disabled={configSaving}
                    style={{
                      background: configSaving ? '#94a3b8' : 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
                      color: 'white',
                      border: 'none',
                      padding: '12px 24px',
                      borderRadius: '8px',
                      fontSize: '16px',
                      fontWeight: '600',
                      cursor: configSaving ? 'not-allowed' : 'pointer',
                      transition: 'all 0.2s ease',
                      opacity: configSaving ? 0.7 : 1
                    }}
                  >
                    {configSaving ? 'Salvataggio...' : 'Salva Configurazione'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}