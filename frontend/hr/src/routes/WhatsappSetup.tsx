import { useState, useEffect } from 'react'
import { Settings, Save, CheckCircle2, AlertCircle, Plus, Trash2, MessageSquare } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'

interface KnockoutRule {
  question: string
  expected_answer: string
  rejection_message: string
}

interface WhatsappConfig {
  tenant_id: string
  bot_name: string
  tone: 'formal' | 'friendly' | 'enthusiastic'
  language: string
  template_name: string | null
  knockout_rules: KnockoutRule[]
  screening_questions: string[]
  knowledge_base: Record<string, any>
}

export function WhatsappSetup() {
  const [config, setConfig] = useState<WhatsappConfig>({
    tenant_id: '',
    bot_name: 'Recruiter AI',
    tone: 'friendly',
    language: 'it',
    template_name: null,
    knockout_rules: [],
    screening_questions: [],
    knowledge_base: {}
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [credentialsValid, setCredentialsValid] = useState<boolean | null>(null)
  const token = localStorage.getItem('hr_jwt')

  useEffect(() => {
    loadConfig()
    validateCredentials()
  }, [])

  const loadConfig = async () => {
    try {
      const response = await fetch(`${API_BASE}/whatsapp/config`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setConfig(data)
      }
    } catch (error) {
      console.error('Error loading config:', error)
    } finally {
      setLoading(false)
    }
  }

  const validateCredentials = async () => {
    try {
      const response = await fetch(`${API_BASE}/whatsapp/config/validate-credentials`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setCredentialsValid(data.valid)
      }
    } catch (error) {
      console.error('Error validating credentials:', error)
      setCredentialsValid(false)
    }
  }

  const saveConfig = async () => {
    setSaving(true)
    setMessage(null)
    
    try {
      const response = await fetch(`${API_BASE}/whatsapp/config`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
      })
      
      if (response.ok) {
        setMessage({ type: 'success', text: 'Configurazione salvata con successo!' })
        await validateCredentials()
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Errore nel salvataggio' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Errore di connessione' })
    } finally {
      setSaving(false)
    }
  }

  const addKnockoutRule = () => {
    setConfig(prev => ({
      ...prev,
      knockout_rules: [...prev.knockout_rules, { question: '', expected_answer: '', rejection_message: '' }]
    }))
  }

  const updateKnockoutRule = (index: number, field: keyof KnockoutRule, value: string) => {
    setConfig(prev => {
      const updated = [...prev.knockout_rules]
      updated[index] = { ...updated[index], [field]: value }
      return { ...prev, knockout_rules: updated }
    })
  }

  const removeKnockoutRule = (index: number) => {
    setConfig(prev => ({
      ...prev,
      knockout_rules: prev.knockout_rules.filter((_, i) => i !== index)
    }))
  }

  const addScreeningQuestion = () => {
    setConfig(prev => ({
      ...prev,
      screening_questions: [...prev.screening_questions, '']
    }))
  }

  const updateScreeningQuestion = (index: number, value: string) => {
    setConfig(prev => {
      const updated = [...prev.screening_questions]
      updated[index] = value
      return { ...prev, screening_questions: updated }
    })
  }

  const removeScreeningQuestion = (index: number) => {
    setConfig(prev => ({
      ...prev,
      screening_questions: prev.screening_questions.filter((_, i) => i !== index)
    }))
  }

  const updateKnowledgeBase = (key: string, value: string) => {
    setConfig(prev => ({
      ...prev,
      knowledge_base: { ...prev.knowledge_base, [key]: value }
    }))
  }

  if (loading) {
    return (
      <div className="container" style={{ display: 'grid', gap: '32px' }}>
        <div className="card fade-in" style={{ textAlign: 'center', padding: '40px' }}>
          <Settings size={24} color="#9CA3AF" style={{ marginBottom: '8px' }} />
          <div style={{ marginTop: '8px' }}>Caricamento configurazione...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="container" style={{ display: 'grid', gap: '32px' }}>
      {/* Header */}
      <div>
        <h1 style={{ 
          fontSize: '28px', 
          fontWeight: '600', 
          margin: '0 0 24px 0',
          color: 'var(--primary-purple)'
        }}>
          Configurazione WhatsApp Screener
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '16px', lineHeight: '1.5', margin: 0 }}>
          Configura il bot AI per il pre-screening automatico dei candidati via WhatsApp
        </p>
      </div>

      {/* Status Credenziali */}
      {credentialsValid !== null && (
        <div className="card fade-in" style={{
          padding: '16px',
          background: credentialsValid 
            ? 'linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%)'
            : 'linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%)',
          border: `1px solid ${credentialsValid ? '#10B981' : '#EF4444'}`
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {credentialsValid ? (
              <>
                <CheckCircle2 size={20} color="#10B981" />
                <span style={{ color: '#065F46', fontWeight: '600' }}>
                  Credenziali WhatsApp valide e connessione attiva
                </span>
              </>
            ) : (
              <>
                <AlertCircle size={20} color="#EF4444" />
                <span style={{ color: '#991B1B', fontWeight: '600' }}>
                  Credenziali WhatsApp non valide o non configurate. Verifica le variabili d'ambiente.
                </span>
              </>
            )}
          </div>
        </div>
      )}

      {/* Configurazione Base */}
      <div className="card fade-in">
        <h2 style={{ margin: '0 0 24px 0', fontSize: '20px', fontWeight: '600', color: 'var(--primary-purple)' }}>
          Identità del Bot
        </h2>

        <div style={{ display: 'grid', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: 'var(--text-primary)', marginBottom: '8px' }}>
              Nome del Bot
            </label>
            <input
              type="text"
              value={config.bot_name}
              onChange={(e) => setConfig(prev => ({ ...prev, bot_name: e.target.value }))}
              placeholder="es. Alessia di Vertigo HR"
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid var(--border-light)',
                fontSize: '14px'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: 'var(--text-primary)', marginBottom: '8px' }}>
              Tono di Voce
            </label>
            <select
              value={config.tone}
              onChange={(e) => setConfig(prev => ({ ...prev, tone: e.target.value as any }))}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid var(--border-light)',
                fontSize: '14px'
              }}
            >
              <option value="formal">Formale</option>
              <option value="friendly">Amichevole</option>
              <option value="enthusiastic">Entusiasta</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: 'var(--text-primary)', marginBottom: '8px' }}>
              Lingua di Default
            </label>
            <select
              value={config.language}
              onChange={(e) => setConfig(prev => ({ ...prev, language: e.target.value }))}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid var(--border-light)',
                fontSize: '14px'
              }}
            >
              <option value="it">Italiano</option>
              <option value="en">Inglese</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: 'var(--text-primary)', marginBottom: '8px' }}>
              Nome Template Message (Meta)
            </label>
            <input
              type="text"
              value={config.template_name || ''}
              onChange={(e) => setConfig(prev => ({ ...prev, template_name: e.target.value || null }))}
              placeholder="es. first_contact_v1"
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid var(--border-light)',
                fontSize: '14px'
              }}
            />
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Il nome del template approvato da Meta per il primo messaggio (a pagamento)
            </p>
          </div>
        </div>
      </div>

      {/* Regole Knock-out */}
      <div className="card fade-in">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: '600', color: 'var(--primary-purple)' }}>
            Criteri Obbligatori (Knock-out)
          </h2>
          <button
            onClick={addKnockoutRule}
            style={{
              padding: '8px 16px',
              background: 'var(--primary-purple)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Plus size={16} />
            Aggiungi Regola
          </button>
        </div>

        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
          Se il candidato non risponde correttamente a queste domande, viene automaticamente squalificato
        </p>

        {config.knockout_rules.length === 0 ? (
          <div style={{ 
            padding: '24px', 
            textAlign: 'center', 
            background: 'var(--bg-secondary)', 
            borderRadius: '8px',
            color: 'var(--text-secondary)'
          }}>
            Nessuna regola knock-out configurata
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '16px' }}>
            {config.knockout_rules.map((rule, index) => (
              <div key={index} style={{
                padding: '16px',
                background: 'var(--bg-secondary)',
                borderRadius: '8px',
                border: '1px solid var(--border-light)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' }}>
                    Regola {index + 1}
                  </span>
                  <button
                    onClick={() => removeKnockoutRule(index)}
                    style={{
                      padding: '4px 8px',
                      background: '#FEE2E2',
                      color: '#991B1B',
                      border: 'none',
                      borderRadius: '4px',
                      fontSize: '12px',
                      cursor: 'pointer'
                    }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                <div style={{ display: 'grid', gap: '12px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', marginBottom: '4px' }}>
                      Domanda
                    </label>
                    <input
                      type="text"
                      value={rule.question}
                      onChange={(e) => updateKnockoutRule(index, 'question', e.target.value)}
                      placeholder="es. Hai la patente B?"
                      style={{
                        width: '100%',
                        padding: '8px',
                        borderRadius: '6px',
                        border: '1px solid var(--border-light)',
                        fontSize: '14px'
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', marginBottom: '4px' }}>
                      Risposta Attesa (parola chiave)
                    </label>
                    <input
                      type="text"
                      value={rule.expected_answer}
                      onChange={(e) => updateKnockoutRule(index, 'expected_answer', e.target.value)}
                      placeholder="es. sì, si, yes"
                      style={{
                        width: '100%',
                        padding: '8px',
                        borderRadius: '6px',
                        border: '1px solid var(--border-light)',
                        fontSize: '14px'
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', marginBottom: '4px' }}>
                      Messaggio di Rifiuto
                    </label>
                    <textarea
                      value={rule.rejection_message}
                      onChange={(e) => updateKnockoutRule(index, 'rejection_message', e.target.value)}
                      placeholder="es. Mi dispiace, per questo ruolo è necessaria la patente B."
                      rows={2}
                      style={{
                        width: '100%',
                        padding: '8px',
                        borderRadius: '6px',
                        border: '1px solid var(--border-light)',
                        fontSize: '14px',
                        resize: 'vertical'
                      }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Domande Screening */}
      <div className="card fade-in">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: '600', color: 'var(--primary-purple)' }}>
            Domande di Screening
          </h2>
          <button
            onClick={addScreeningQuestion}
            style={{
              padding: '8px 16px',
              background: 'var(--primary-purple)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Plus size={16} />
            Aggiungi Domanda
          </button>
        </div>

        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
          Domande aperte che l'AI porrà al candidato durante la conversazione
        </p>

        {config.screening_questions.length === 0 ? (
          <div style={{ 
            padding: '24px', 
            textAlign: 'center', 
            background: 'var(--bg-secondary)', 
            borderRadius: '8px',
            color: 'var(--text-secondary)'
          }}>
            Nessuna domanda di screening configurata
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '12px' }}>
            {config.screening_questions.map((question, index) => (
              <div key={index} style={{
                display: 'flex',
                gap: '8px',
                alignItems: 'flex-start'
              }}>
                <input
                  type="text"
                  value={question}
                  onChange={(e) => updateScreeningQuestion(index, e.target.value)}
                  placeholder="es. Qual è il tuo preavviso attuale?"
                  style={{
                    flex: 1,
                    padding: '10px',
                    borderRadius: '6px',
                    border: '1px solid var(--border-light)',
                    fontSize: '14px'
                  }}
                />
                <button
                  onClick={() => removeScreeningQuestion(index)}
                  style={{
                    padding: '10px',
                    background: '#FEE2E2',
                    color: '#991B1B',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Knowledge Base */}
      <div className="card fade-in">
        <h2 style={{ margin: '0 0 24px 0', fontSize: '20px', fontWeight: '600', color: 'var(--primary-purple)' }}>
          Knowledge Base (Info Utili)
        </h2>

        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
          Informazioni che l'AI può usare per rispondere alle domande del candidato sulla posizione
        </p>

        <div style={{ display: 'grid', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
              RAL / Stipendio
            </label>
            <input
              type="text"
              value={config.knowledge_base.ral || ''}
              onChange={(e) => updateKnowledgeBase('ral', e.target.value)}
              placeholder="es. 30k-40k"
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid var(--border-light)',
                fontSize: '14px'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
              Sede / Location
            </label>
            <input
              type="text"
              value={config.knowledge_base.location || ''}
              onChange={(e) => updateKnowledgeBase('location', e.target.value)}
              placeholder="es. Milano Centro"
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid var(--border-light)',
                fontSize: '14px'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
              Smart Working / Remote Policy
            </label>
            <input
              type="text"
              value={config.knowledge_base.remote_policy || ''}
              onChange={(e) => updateKnowledgeBase('remote_policy', e.target.value)}
              placeholder="es. Ibrido 3+2"
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid var(--border-light)',
                fontSize: '14px'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
              Benefits
            </label>
            <textarea
              value={config.knowledge_base.benefits || ''}
              onChange={(e) => updateKnowledgeBase('benefits', e.target.value)}
              placeholder="es. Buoni pasto, assicurazione sanitaria, palestra"
              rows={3}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid var(--border-light)',
                fontSize: '14px',
                resize: 'vertical'
              }}
            />
          </div>
        </div>
      </div>

      {/* Message e Salva */}
      {message && (
        <div style={{
          padding: '12px',
          borderRadius: '8px',
          backgroundColor: message.type === 'success' ? '#d4edda' : '#f8d7da',
          color: message.type === 'success' ? '#155724' : '#721c24',
          border: `1px solid ${message.type === 'success' ? '#c3e6cb' : '#f5c6cb'}`
        }}>
          {message.text}
        </div>
      )}

      <div className="card fade-in">
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={saveConfig}
            disabled={saving}
            style={{
              background: saving ? '#94a3b8' : 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
              color: 'white',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: '600',
              cursor: saving ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s ease',
              opacity: saving ? 0.7 : 1,
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <Save size={18} />
            {saving ? 'Salvataggio...' : 'Salva Configurazione'}
          </button>
        </div>
      </div>
    </div>
  )
}

