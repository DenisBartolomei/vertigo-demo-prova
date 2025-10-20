import { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'

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
      setEditedCriteria(prev => ({
        ...prev,
        [positionId]: JSON.parse(JSON.stringify(criteria.evaluation_schema))
      }))
    }
  }

  function updateCriterion(positionId: string, reqIndex: number, field: 'evaluation_criteria_1' | 'evaluation_criteria_2', value: string) {
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

  return (
    <div className="container" style={{ display: 'grid', gap: '32px', position: 'relative' }}>
      {/* Loading Overlay */}
      {isPreparing && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          backdropFilter: 'blur(4px)'
        }}>
          <div style={{
            background: 'white',
            padding: '40px',
            borderRadius: 'var(--radius-xl)',
            textAlign: 'center',
            boxShadow: 'var(--shadow-lg)',
            maxWidth: '400px',
            margin: '20px'
          }}>
            <div style={{ 
              fontSize: '48px', 
              marginBottom: '20px',
              background: 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              ⚙️
            </div>
            <h3 style={{ 
              fontSize: '24px', 
              fontWeight: '600', 
              marginBottom: '12px',
              color: 'var(--text-primary)'
            }}>
              Preparazione in corso...
            </h3>
            <p style={{ 
              fontSize: '16px', 
              color: 'var(--text-secondary)',
              lineHeight: '1.5',
              marginBottom: '20px'
            }}>
              Stiamo generando i casi di studio e i criteri di valutazione per questa posizione. Questo processo può richiedere alcuni minuti.
            </p>
            <div style={{
              background: 'var(--light-purple)',
              padding: '12px',
              borderRadius: 'var(--radius-md)',
              fontSize: '14px',
              color: 'var(--text-secondary)'
            }}>
              ⏳ Non chiudere questa pagina durante la preparazione
            </div>
          </div>
        </div>
      )}
      
      <div>
        <h2>Annunci</h2>
        <p className="muted">Crea e gestisci le posizioni lavorative per i colloqui dei candidati</p>
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
            📋
          </div>
          <h3>Crea Nuova Posizione</h3>
        </div>
        
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
            💾 Salva Posizione & Avvia Preparazione Dati
          </button>
        </div>
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
            color: 'white',
            fontSize: '18px'
          }}>
            📊
          </div>
          <h3>Posizioni Esistenti</h3>
        </div>
        
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '24px', marginBottom: '8px' }}>⏳</div>
            Caricamento posizioni...
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
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>
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
                            📄 Testo annuncio
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
                            💼 Casi da colloquio
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
                            📊 Griglia valutativa
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
                                    <div style={{ fontSize: '24px', marginBottom: '8px' }}>⏳</div>
                                    Nessun caso disponibile ancora. Esegui la preparazione dati per generare i casi di colloquio.
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
                                      {(editedCriteria[p._id] || info.evaluation_criteria.evaluation_schema).map((req: any, idx: number) => (
                                        <div key={idx} style={{ 
                                          padding: '16px', 
                                          background: 'rgba(255, 255, 255, 0.7)', 
                                          borderRadius: 'var(--radius-md)',
                                          border: '1px solid rgba(139, 92, 246, 0.1)'
                                        }}>
                                          <div style={{ 
                                            fontWeight: '600', 
                                            marginBottom: '12px', 
                                            color: 'var(--text-primary)',
                                            fontSize: '15px',
                                            padding: '8px',
                                            background: 'rgba(139, 92, 246, 0.1)',
                                            borderRadius: '6px'
                                          }}>
                                            📌 {req.requirement}
                                          </div>
                                          <div style={{ display: 'grid', gap: '12px' }}>
                                            <div>
                                              <label style={{ 
                                                display: 'block', 
                                                fontSize: '13px', 
                                                fontWeight: '500', 
                                                color: 'var(--text-secondary)',
                                                marginBottom: '6px' 
                                              }}>
                                                Criterio di Valutazione 1
                                              </label>
                                              <textarea
                                                value={editedCriteria[p._id]?.[idx]?.criteria?.evaluation_criteria_1 || req.criteria.evaluation_criteria_1}
                                                onChange={(e) => updateCriterion(p._id, idx, 'evaluation_criteria_1', e.target.value)}
                                                rows={3}
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
                                            <div>
                                              <label style={{ 
                                                display: 'block', 
                                                fontSize: '13px', 
                                                fontWeight: '500', 
                                                color: 'var(--text-secondary)',
                                                marginBottom: '6px' 
                                              }}>
                                                Criterio di Valutazione 2
                                              </label>
                                              <textarea
                                                value={editedCriteria[p._id]?.[idx]?.criteria?.evaluation_criteria_2 || req.criteria.evaluation_criteria_2}
                                                onChange={(e) => updateCriterion(p._id, idx, 'evaluation_criteria_2', e.target.value)}
                                                rows={3}
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
                                          </div>
                                        </div>
                                      ))}
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
                                        {savingCriteria ? '⏳ Salvataggio...' : '💾 Salva Modifiche'}
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
                                    <div style={{ fontSize: '24px', marginBottom: '8px' }}>⏳</div>
                                    Nessun criterio di valutazione disponibile. Esegui la preparazione dati per generarli.
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
                            <div style={{ fontSize: '24px', marginBottom: '8px' }}>⏳</div>
                            Caricamento dettagli...
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
                            {isPreparing ? '⏳ Elaborazione...' : '🚀 Esegui Preparazione Dati'}
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
                            🗑️ Elimina
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
    </div>
  )
}