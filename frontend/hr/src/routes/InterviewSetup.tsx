import React, { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'

interface InterviewConfig {
  reasoning_steps: number
  max_attempts: number
  estimated_duration_minutes: number
  max_questions: number
}

export function InterviewSetup() {
  const [config, setConfig] = useState<InterviewConfig>({
    reasoning_steps: 4,
    max_attempts: 5,
    estimated_duration_minutes: 35,
    max_questions: 11
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const token = localStorage.getItem('hr_jwt')

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const response = await fetch(`${API_BASE}/interview-config`, {
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

  const saveConfig = async () => {
    setSaving(true)
    setMessage(null)
    
    try {
      const response = await fetch(`${API_BASE}/interview-config`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          reasoning_steps: config.reasoning_steps,
          max_attempts: config.max_attempts
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setConfig(data)
        setMessage({ type: 'success', text: 'Configurazione salvata con successo!' })
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

  const updateConfig = (field: keyof InterviewConfig, value: number) => {
    setConfig(prev => {
      const updated = { ...prev, [field]: value }
      
      // Ricalcola automaticamente i valori derivati
      if (field === 'reasoning_steps' || field === 'max_attempts') {
        updated.estimated_duration_minutes = Math.round((updated.reasoning_steps * updated.max_attempts * 1.5) + 5)
        updated.max_questions = (updated.reasoning_steps * 2) + 3
      }
      
      return updated
    })
  }

  if (loading) {
    return (
      <div className="container" style={{ display: 'grid', gap: '32px' }}>
        <div className="card fade-in" style={{ textAlign: 'center', padding: '40px' }}>
          <div style={{ fontSize: '24px', marginBottom: '8px' }}>⏳</div>
          Caricamento configurazione...
        </div>
      </div>
    )
  }

  return (
    <div className="container" style={{ display: 'grid', gap: '32px' }}>
      {/* Header */}
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
            ⚙️
          </div>
          <h1 style={{ 
            fontSize: '28px', 
            fontWeight: '600', 
            margin: 0,
            background: 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}>
            Setup Colloqui
          </h1>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '16px', lineHeight: '1.5' }}>
          Configura i parametri per personalizzare la durata e la complessità delle interviste per la tua azienda.
        </p>
      </div>

      {/* Box 1: Configurazione Interviste */}
      <div className="card fade-in">
        <div style={{ 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          padding: '20px',
          borderRadius: '12px',
          marginBottom: '24px'
        }}>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: '600' }}>
            🎯 Configurazione Interviste
          </h2>
          <p style={{ margin: '8px 0 0 0', opacity: 0.9, fontSize: '14px' }}>
            Personalizza la durata e la complessità dei colloqui
          </p>
        </div>

        {message && (
          <div style={{
            marginBottom: '20px',
            padding: '12px',
            borderRadius: '8px',
            backgroundColor: message.type === 'success' ? '#d4edda' : '#f8d7da',
            color: message.type === 'success' ? '#155724' : '#721c24',
            border: `1px solid ${message.type === 'success' ? '#c3e6cb' : '#f5c6cb'}`
          }}>
            {message.text}
          </div>
        )}

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
                max="6"
                value={config.reasoning_steps}
                onChange={(e) => updateConfig('reasoning_steps', parseInt(e.target.value))}
                style={{ flex: 1, height: '8px', borderRadius: '4px', background: '#e2e8f0' }}
              />
              <div style={{ 
                fontSize: '24px', 
                fontWeight: '700', 
                color: 'var(--primary-purple)',
                minWidth: '40px',
                textAlign: 'center'
              }}>
                {config.reasoning_steps}
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
                max="5"
                value={config.max_attempts}
                onChange={(e) => updateConfig('max_attempts', parseInt(e.target.value))}
                style={{ flex: 1, height: '8px', borderRadius: '4px', background: '#e2e8f0' }}
              />
              <div style={{ 
                fontSize: '24px', 
                fontWeight: '700', 
                color: 'var(--primary-purple)',
                minWidth: '40px',
                textAlign: 'center'
              }}>
                {config.max_attempts}
              </div>
            </div>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: '1.4' }}>
              Numero massimo di tentativi che l'agente intervistatore concede al candidato per completare ogni reasoning step.
            </p>
          </div>

          {/* Stime Calcolate */}
          <div style={{ 
            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            color: 'white',
            padding: '20px',
            borderRadius: '12px'
          }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '18px', fontWeight: '600' }}>
              📊 Stime Calcolate
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '12px', opacity: 0.8, marginBottom: '4px' }}>Durata Stimata</div>
                <div style={{ fontSize: '24px', fontWeight: '700' }}>{config.estimated_duration_minutes} min</div>
              </div>
              <div>
                <div style={{ fontSize: '12px', opacity: 0.8, marginBottom: '4px' }}>Domande Massime</div>
                <div style={{ fontSize: '24px', fontWeight: '700' }}>{config.max_questions}</div>
              </div>
            </div>
            <p style={{ fontSize: '12px', opacity: 0.8, marginTop: '12px', margin: '12px 0 0 0' }}>
              * Stima basata su 1.5 minuti per tentativo + 5 minuti per setup iniziale
            </p>
          </div>

          {/* Pulsante Salva */}
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
                opacity: saving ? 0.7 : 1
              }}
            >
              {saving ? 'Salvataggio...' : 'Salva Configurazione'}
            </button>
          </div>
        </div>
      </div>

      {/* Box 2: Pre-screening */}
      <div className="card fade-in">
        <div style={{ 
          background: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
          color: '#8b4513',
          padding: '20px',
          borderRadius: '12px',
          marginBottom: '24px'
        }}>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: '600' }}>
            🔍 Pre-screening Candidati
          </h2>
          <p style={{ margin: '8px 0 0 0', opacity: 0.8, fontSize: '14px' }}>
            Configurazione test preliminari per filtrare i candidati
          </p>
        </div>

        <div style={{ 
          background: '#fef3c7',
          border: '1px solid #f59e0b',
          borderRadius: '12px',
          padding: '20px',
          marginBottom: '20px'
        }}>
          <p style={{ 
            margin: 0, 
            fontSize: '14px', 
            color: '#92400e',
            lineHeight: '1.5'
          }}>
            <strong>Nota:</strong> Questa funzione è attualmente in fase di sviluppo. Le opzioni di configurazione per i pre-test di selezione saranno disponibili in una versione futura del sistema.
          </p>
        </div>

        <div style={{ 
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: '12px',
          padding: '20px',
          opacity: 0.6
        }}>
          <div style={{ display: 'grid', gap: '20px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#64748b', marginBottom: '8px' }}>
                Tipo di Pre-test
              </label>
              <select disabled style={{ 
                width: '100%', 
                padding: '12px', 
                border: '1px solid #cbd5e1', 
                borderRadius: '8px', 
                backgroundColor: '#f1f5f9',
                color: '#64748b',
                fontSize: '14px'
              }}>
                <option>Selezione non disponibile</option>
              </select>
            </div>
            
            <div>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#64748b', marginBottom: '8px' }}>
                Durata Pre-test (minuti)
              </label>
              <input
                type="range"
                min="5"
                max="60"
                disabled
                style={{ 
                  width: '100%', 
                  height: '8px', 
                  borderRadius: '4px', 
                  background: '#e2e8f0',
                  opacity: 0.5
                }}
              />
              <span style={{ fontSize: '12px', color: '#64748b', marginTop: '4px', display: 'block' }}>Non configurato</span>
            </div>
            
            <div>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: '500', color: '#64748b', marginBottom: '8px' }}>
                Numero di Domande
              </label>
              <input
                type="range"
                min="5"
                max="30"
                disabled
                style={{ 
                  width: '100%', 
                  height: '8px', 
                  borderRadius: '4px', 
                  background: '#e2e8f0',
                  opacity: 0.5
                }}
              />
              <span style={{ fontSize: '12px', color: '#64748b', marginTop: '4px', display: 'block' }}>Non configurato</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
