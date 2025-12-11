import { useState, useEffect } from 'react'
import { Settings, Save, CheckCircle2, AlertCircle } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'

interface WhatsappConfig {
  tenant_id: string
  bot_name: string
  tone: 'formal' | 'friendly' | 'enthusiastic'
  language: string
  template_name: string | null
  knowledge_base: Record<string, any>
}

export function WhatsappSetup() {
  const [config, setConfig] = useState<WhatsappConfig>({
    tenant_id: '',
    bot_name: 'Recruiter AI',
    tone: 'friendly',
    language: 'it',
    template_name: null,
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
        
        // Normalizza il codice lingua: "en" -> "en_US" per retrocompatibilità
        let normalizedLanguage = data.language || 'it'
        if (normalizedLanguage === 'en') {
          normalizedLanguage = 'en_US'
        }
        
        // Merge con valori di default per gestire campi mancanti
        setConfig(prev => ({
          ...prev,
          ...data,
          language: normalizedLanguage,
          knowledge_base: data.knowledge_base || {}
        }))
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
              Nome dell'Agente AI
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
              Lingua Template WhatsApp Business
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
              <option value="it">Italiano (it)</option>
              <option value="en_US">Inglese (en_US)</option>
            </select>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Codice lingua per i template WhatsApp Business. Italiano usa "it", Inglese usa "en_US"
            </p>
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

      {/* Knowledge Base */}
      <div className="card fade-in">
        <h2 style={{ margin: '0 0 24px 0', fontSize: '20px', fontWeight: '600', color: 'var(--primary-purple)' }}>
          Knowledge Base Aziendale
        </h2>

        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
          Informazioni <strong>generiche dell'azienda</strong> che l'AI può usare per rispondere alle domande dei candidati. 
          Le informazioni specifiche della posizione (RAL, sede, requisiti knockout, smart working) vengono prese automaticamente 
          dalla <strong>sezione Annunci → Dettagli Posizione</strong>.
        </p>

        <div style={{ display: 'grid', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
              Benefits Aziendali
            </label>
            <textarea
              value={config.knowledge_base.benefits || ''}
              onChange={(e) => updateKnowledgeBase('benefits', e.target.value)}
              placeholder="es. Buoni pasto 8€, assicurazione sanitaria, abbonamento palestra, contributo spese bambini"
              rows={4}
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

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
              Info Azienda / Cultura
            </label>
            <textarea
              value={config.knowledge_base.company_info || ''}
              onChange={(e) => updateKnowledgeBase('company_info', e.target.value)}
              placeholder="es. Azienda leader nel settore tech, ambiente giovane e dinamico, progetti internazionali"
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

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
              Processo di Selezione
            </label>
            <textarea
              value={config.knowledge_base.hiring_process || ''}
              onChange={(e) => updateKnowledgeBase('hiring_process', e.target.value)}
              placeholder="es. 1) Pre-screening WhatsApp 2) Colloquio scritto 3) Colloquio tecnico 4) Offerta"
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

          <div>
            <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', marginBottom: '8px' }}>
              Altre Info Utili
            </label>
            <textarea
              value={config.knowledge_base.other || ''}
              onChange={(e) => updateKnowledgeBase('other', e.target.value)}
              placeholder="es. Parcheggio gratuito, mensa aziendale, orari flessibili"
              rows={2}
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

        <div style={{ 
          marginTop: '20px', 
          padding: '12px', 
          background: 'linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%)', 
          borderRadius: '8px',
          border: '1px solid #C7D2FE'
        }}>
          <p style={{ fontSize: '13px', color: '#4338CA', margin: 0 }}>
            💡 <strong>Nota:</strong> RAL, sede, smart working e requisiti knockout sono configurati per ogni singola posizione 
            nella sezione <strong>Annunci → Dettagli Posizione</strong>. L'agente WhatsApp li recupera automaticamente 
            in base alla posizione per cui il candidato si è candidato.
          </p>
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

