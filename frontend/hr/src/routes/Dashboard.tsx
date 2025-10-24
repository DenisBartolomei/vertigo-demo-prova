import { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

interface DashboardData {
  metrics: {
    completed_interviews: number
    waiting_token: number
    in_progress: number
    avg_interview_duration: number
    avg_takeover_time: number
    recovery_count: number
    recovery_rate: number
    underperforming_count: number
    underperforming_rate: number
    avg_interview_score: number
    avg_cv_score: number
    avg_overall_score: number
    total_evaluated: number
  }
  positions: Array<{
    id: string
    name: string
  }>
}

export function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTimeRange, setSelectedTimeRange] = useState<'7d' | '30d' | '90d' | '1y'>('30d')
  const [selectedPosition, setSelectedPosition] = useState<string>("all")

  useEffect(() => {
    loadDashboardData()
  }, [selectedTimeRange, selectedPosition])

  async function loadDashboardData() {
    try {
      setLoading(true)
      const token = localStorage.getItem('hr_jwt')
      if (!token) {
        setError('Token di autenticazione non trovato')
        return
      }

      const response = await fetch(`${API_BASE}/dashboard/data?timeRange=${selectedTimeRange}&positionFilter=${selectedPosition}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error('Errore nel caricamento dei dati del dashboard')
      }

      const dashboardData = await response.json()
      setData(dashboardData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore sconosciuto')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '400px',
        fontSize: '18px',
        color: 'var(--text-secondary)'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📊</div>
          <div>Caricamento dashboard...</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '400px',
        fontSize: '18px',
        color: 'var(--error-color, #ef4444)'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>⚠️</div>
          <div>{error}</div>
          <button 
            onClick={loadDashboardData}
            style={{
              marginTop: '16px',
              padding: '8px 16px',
              background: 'var(--primary-purple)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer'
            }}
          >
            Riprova
          </button>
        </div>
      </div>
    )
  }

  if (!data) return null

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '32px'
      }}>
        <div>
          <h1 style={{ 
            fontSize: '32px', 
            fontWeight: '700', 
            margin: '0 0 8px 0',
            background: 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}>
            📊 Dashboard HR
          </h1>
          <p style={{ 
            fontSize: '16px', 
            color: 'var(--text-secondary)', 
            margin: '0' 
          }}>
            Indicatori di performance per il processo di recruitment
          </p>
        </div>
        
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <label style={{ fontSize: '14px', color: 'var(--text-secondary)', fontWeight: '500' }}>
              Periodo:
            </label>
            <select
              value={selectedTimeRange}
              onChange={(e) => setSelectedTimeRange(e.target.value as any)}
              style={{
                padding: '8px 12px',
                border: '2px solid var(--border-light)',
                borderRadius: '8px',
                background: 'white',
                fontSize: '14px',
                minWidth: '140px'
              }}
            >
              <option value="7d">Ultimi 7 giorni</option>
              <option value="30d">Ultimi 30 giorni</option>
              <option value="90d">Ultimi 90 giorni</option>
              <option value="1y">Ultimo anno</option>
            </select>
          </div>
          
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <label style={{ fontSize: '14px', color: 'var(--text-secondary)', fontWeight: '500' }}>
              Posizione:
            </label>
            <select
              value={selectedPosition}
              onChange={(e) => setSelectedPosition(e.target.value)}
              style={{
                padding: '8px 12px',
                border: '2px solid var(--border-light)',
                borderRadius: '8px',
                background: 'white',
                fontSize: '14px',
                minWidth: '160px'
              }}
            >
              <option value="all">Tutte le posizioni</option>
              {data.positions.map(position => (
                <option key={position.id} value={position.id}>{position.name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Indicatori Principali */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
        gap: '24px',
        marginBottom: '32px'
      }}>
        <MetricCard
          title="Colloqui Completati"
          value={data.metrics.completed_interviews}
          icon="✅"
          color="#10b981"
          tooltip="Candidati che hanno terminato l'intervista con successo e ricevuto valutazione completa"
        />
        <MetricCard
          title="Candidati in Attesa di Token"
          value={data.metrics.waiting_token}
          icon="⏳"
          color="#f59e0b"
          tooltip="CV analizzati con token generato ma non ancora inviato al candidato"
        />
        <MetricCard
          title="Colloquio in Corso"
          value={data.metrics.in_progress}
          icon="🔄"
          color="#3b82f6"
          tooltip="Candidati che hanno ricevuto il token ma non hanno ancora completato l'intervista"
        />
        <MetricCard
          title="Durata Media Colloquio"
          value={`${data.metrics.avg_interview_duration.toFixed(1)}m`}
          icon="⏱️"
          color="#06b6d4"
          tooltip="Tempo medio impiegato dai candidati per completare l'intervista, dall'inizio alla fine"
        />
        <MetricCard
          title="Tempo di Presa in Carico"
          value={`${data.metrics.avg_takeover_time.toFixed(1)}h`}
          icon="📋"
          color="#8b5cf6"
          tooltip="Tempo medio che intercorre tra il completamento dell'intervista e l'invio del link al candidato"
        />
        <MetricCard
          title="Tasso di Recupero"
          value={`${data.metrics.recovery_count} (${data.metrics.recovery_rate.toFixed(1)}%)`}
          icon="📈"
          color="#10b981"
          tooltip="Candidati che hanno dimostrato competenze superiori durante il colloquio rispetto a quanto emerge dal CV (miglioramento di almeno mezzo punto)"
        />
        <MetricCard
          title="Underperforming"
          value={`${data.metrics.underperforming_count} (${data.metrics.underperforming_rate.toFixed(1)}%)`}
          icon="📉"
          color="#ef4444"
          tooltip="Candidati che hanno dimostrato competenze inferiori durante il colloquio rispetto a quanto emerge dal CV (peggioramento di almeno mezzo punto)"
        />
        <MetricCard
          title="Scoring Medio Colloqui"
          value={data.metrics.avg_interview_score.toFixed(2)}
          icon="🎯"
          color="#3b82f6"
          tooltip="Punteggio medio ottenuto dai candidati durante le interviste, su una scala da 0 a 4"
        />
        <MetricCard
          title="Scoring Medio CV"
          value={data.metrics.avg_cv_score.toFixed(2)}
          icon="📄"
          color="#8b5cf6"
          tooltip="Punteggio medio ottenuto dai candidati nell'analisi dei CV, su una scala da 0 a 4"
        />
        <MetricCard
          title="Scoring Complessivo"
          value={data.metrics.avg_overall_score.toFixed(2)}
          icon="⭐"
          color="#6366f1"
          tooltip="Punteggio medio complessivo che combina la valutazione del CV e della performance in intervista"
        />
      </div>

    </div>
  )
}

// Component for metric cards with tooltip
function MetricCard({ title, value, icon, color, tooltip }: {
  title: string
  value: number | string
  icon: string
  color: string
  tooltip: string
}) {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '24px',
      boxShadow: 'var(--shadow-sm)',
      border: '1px solid var(--border-light)',
      position: 'relative',
      overflow: 'hidden'
    }}>
      <div style={{
        position: 'absolute',
        top: '0',
        right: '0',
        width: '100px',
        height: '100px',
        background: `linear-gradient(135deg, ${color}20, ${color}10)`,
        borderRadius: '50%',
        transform: 'translate(30px, -30px)'
      }} />
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
        <div style={{
          fontSize: '24px',
          width: '40px',
          height: '40px',
          borderRadius: '10px',
          background: `${color}20`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          {icon}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <h3 style={{ 
              fontSize: '14px', 
              fontWeight: '500', 
              color: 'var(--text-secondary)',
              margin: '0 0 4px 0'
            }}>
              {title}
            </h3>
            <div 
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
              style={{ position: 'relative', display: 'inline-block' }}
            >
              <span style={{ 
                fontSize: '14px', 
                color: 'var(--text-muted)', 
                cursor: 'help',
                marginLeft: '4px'
              }}>
                ❓
              </span>
              {showTooltip && (
                <div style={{
                  position: 'absolute',
                  top: '-10px',
                  left: '25px',
                  transform: 'translateY(-100%)',
                  background: 'rgba(0,0,0,0.95)',
                  color: 'white',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  fontSize: '13px',
                  lineHeight: '1.4',
                  width: '280px',
                  zIndex: 1000,
                  boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                  whiteSpace: 'normal'
                }}>
                  {tooltip}
                </div>
              )}
            </div>
          </div>
          <div style={{ 
            fontSize: '28px', 
            fontWeight: '700', 
            color: 'var(--text-primary)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            {value}
          </div>
        </div>
      </div>
    </div>
  )
}
