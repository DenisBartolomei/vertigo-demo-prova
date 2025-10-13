import React, { useState, useEffect } from 'react'

interface InterviewConfig {
  reasoning_steps: number
  max_attempts: number
  estimated_duration_minutes: number
  max_questions: number
}

interface InterviewConfigProps {
  onConfigUpdate?: (config: InterviewConfig) => void
}

export function InterviewConfig({ onConfigUpdate }: InterviewConfigProps) {
  const [config, setConfig] = useState<InterviewConfig>({
    reasoning_steps: 4,
    max_attempts: 5,
    estimated_duration_minutes: 35,
    max_questions: 11
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const token = localStorage.getItem('authToken')
      const response = await fetch('/api/interview-config', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setConfig(data)
        onConfigUpdate?.(data)
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
      const token = localStorage.getItem('authToken')
      const response = await fetch('/api/interview-config', {
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
        onConfigUpdate?.(data)
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
    return <div className="flex justify-center p-8">Caricamento...</div>
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center gap-2 mb-6">
        <span className="text-2xl">⚙️</span>
        <h2 className="text-xl font-semibold">Configurazione Interviste</h2>
      </div>

      {message && (
        <div className={`mb-4 p-3 rounded-md ${
          message.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {message.text}
        </div>
      )}

      <div className="space-y-6">
        {/* Reasoning Steps */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Numero di Reasoning Steps
          </label>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="2"
              max="10"
              value={config.reasoning_steps}
              onChange={(e) => updateConfig('reasoning_steps', parseInt(e.target.value))}
              className="flex-1"
            />
            <span className="text-lg font-semibold w-12 text-center">{config.reasoning_steps}</span>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            I reasoning steps sono i passaggi logici che l'agente AI segue per guidare il candidato verso la soluzione del case study.
          </p>
        </div>

        {/* Max Attempts */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tentativi Massimi per Step
          </label>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="2"
              max="15"
              value={config.max_attempts}
              onChange={(e) => updateConfig('max_attempts', parseInt(e.target.value))}
              className="flex-1"
            />
            <span className="text-lg font-semibold w-12 text-center">{config.max_attempts}</span>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Numero massimo di tentativi che l'agente intervistatore concede al candidato per completare ogni reasoning step.
          </p>
        </div>

        {/* Stime Calcolate */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="font-medium text-gray-900 mb-3">Stime Calcolate</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-gray-500">Durata Stimata:</span>
              <div className="text-lg font-semibold text-blue-600">{config.estimated_duration_minutes} minuti</div>
            </div>
            <div>
              <span className="text-sm text-gray-500">Domande Massime:</span>
              <div className="text-lg font-semibold text-blue-600">{config.max_questions} domande</div>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            * Stima basata su 1.5 minuti per tentativo + 5 minuti per setup iniziale
          </p>
        </div>

        {/* Guida */}
        <div className="bg-blue-50 rounded-lg p-4">
          <h3 className="font-medium text-blue-900 mb-2">💡 Come Funziona</h3>
          <div className="text-sm text-blue-800 space-y-2">
            <p><strong>Reasoning Steps:</strong> Sono i passaggi logici che l'agente AI intervistatore segue per guidare il candidato attraverso la risoluzione del case study. Ogni step testa competenze specifiche.</p>
            <p><strong>Max Attempts:</strong> Per ogni reasoning step, il candidato ha un numero limitato di tentativi per dimostrare la sua competenza. Se non riesce entro i tentativi massimi, l'agente passa al prossimo step.</p>
            <p><strong>Durata:</strong> La durata totale dipende dal numero di reasoning steps e tentativi massimi. Più parametri alti = intervista più lunga e approfondita.</p>
          </div>
        </div>

        {/* Configurazione Pre-test */}
        <div className="border-t pt-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Configura Pre-test di Selezione</h3>
          
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
            <p className="text-sm text-yellow-800">
              <strong>Nota:</strong> Questa funzione è attualmente in fase di sviluppo. Le opzioni di configurazione per i pre-test di selezione saranno disponibili in una versione futura del sistema.
            </p>
          </div>

          <div className="bg-gray-50 rounded-lg p-4 opacity-50">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-2">
                  Tipo di Pre-test
                </label>
                <select disabled className="w-full p-2 border border-gray-300 rounded-md bg-gray-100 text-gray-500">
                  <option>Selezione non disponibile</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-2">
                  Durata Pre-test (minuti)
                </label>
                <input
                  type="range"
                  min="5"
                  max="60"
                  disabled
                  className="w-full opacity-50"
                />
                <span className="text-sm text-gray-500">Non configurato</span>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-500 mb-2">
                  Numero di Domande
                </label>
                <input
                  type="range"
                  min="5"
                  max="30"
                  disabled
                  className="w-full opacity-50"
                />
                <span className="text-sm text-gray-500">Non configurato</span>
              </div>
            </div>
          </div>
        </div>

        {/* Pulsante Salva */}
        <div className="flex justify-end">
          <button
            onClick={saveConfig}
            disabled={saving}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Salvataggio...' : 'Salva Configurazione'}
          </button>
        </div>
      </div>
    </div>
  )
}
