import { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8001'

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
      
      if (!dashboardData || !dashboardData.metrics) {
        throw new Error('Formato dati dashboard non valido - è necessario un redeploy del backend')
      }
      
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
      <div style={{ marginBottom: '24px' }}>
        <h2>Dashboard HR</h2>
      </div>
      
      <div style={{ 
        display: 'flex', 
        justifyContent: 'flex-end', 
        alignItems: 'center',
        marginBottom: '32px',
        gap: '16px'
      }}>
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
        gridTemplateColumns: 'repeat(3, 1fr)', 
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

      {/* Grafico a Torta Performance */}
      <div style={{ marginTop: '32px' }}>
        <PerformancePieChart
          recoveryCount={data.metrics.recovery_count}
          underperformingCount={data.metrics.underperforming_count}
          totalEvaluated={data.metrics.total_evaluated}
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
      position: 'relative'
    }}>
      <div style={{
        position: 'absolute',
        top: '0',
        right: '0',
        width: '100px',
        height: '100px',
        background: `linear-gradient(135deg, ${color}20, ${color}10)`,
        borderRadius: '50%',
        transform: 'translate(30px, -30px)',
        pointerEvents: 'none',
        overflow: 'hidden'
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
                  position: 'fixed',
                  background: 'rgba(0,0,0,0.95)',
                  color: 'white',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  fontSize: '13px',
                  lineHeight: '1.4',
                  maxWidth: '280px',
                  zIndex: 10000,
                  boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                  whiteSpace: 'normal',
                  pointerEvents: 'none',
                  marginTop: '-8px',
                  marginLeft: '8px'
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

// Performance Pie Chart Component
function PerformancePieChart({ 
  recoveryCount, 
  underperformingCount, 
  totalEvaluated 
}: {
  recoveryCount: number
  underperformingCount: number
  totalEvaluated: number
}) {
  const neutralCount = totalEvaluated - recoveryCount - underperformingCount
  const total = totalEvaluated || 1 // Evita divisione per zero

  const recoveryPercent = total > 0 ? (recoveryCount / total) * 100 : 0
  const underperformingPercent = total > 0 ? (underperformingCount / total) * 100 : 0
  const neutralPercent = total > 0 ? (neutralCount / total) * 100 : 0

  // Calcola gli angoli per il grafico a torta
  const recoveryAngle = (recoveryPercent / 100) * 360
  const underperformingAngle = (underperformingPercent / 100) * 360
  const neutralAngle = (neutralPercent / 100) * 360

  // Funzione per creare il path SVG di uno spicchio
  const createSlice = (startAngle: number, endAngle: number, color: string) => {
    const radius = 80
    const centerX = 100
    const centerY = 100

    const startRad = (startAngle - 90) * (Math.PI / 180)
    const endRad = (endAngle - 90) * (Math.PI / 180)

    const x1 = centerX + radius * Math.cos(startRad)
    const y1 = centerY + radius * Math.sin(startRad)
    const x2 = centerX + radius * Math.cos(endRad)
    const y2 = centerY + radius * Math.sin(endRad)

    const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0

    return {
      path: `M ${centerX} ${centerY} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`,
      color
    }
  }

  const slices = []
  let currentAngle = 0

  // Se una categoria ha il 100%, mostra solo quella
  if (recoveryPercent === 100) {
    slices.push({
      path: 'M 100 20 A 80 80 0 1 1 100 20 Z', // Cerchio completo
      color: '#10b981',
      label: 'Recupero',
      count: recoveryCount,
      percent: recoveryPercent
    })
  } else if (underperformingPercent === 100) {
    slices.push({
      path: 'M 100 20 A 80 80 0 1 1 100 20 Z', // Cerchio completo
      color: '#ef4444',
      label: 'Underperforming',
      count: underperformingCount,
      percent: underperformingPercent
    })
  } else if (neutralPercent === 100) {
    slices.push({
      path: 'M 100 20 A 80 80 0 1 1 100 20 Z', // Cerchio completo
      color: '#94a3b8',
      label: 'Neutri',
      count: neutralCount,
      percent: neutralPercent
    })
  } else {
    // Caso normale: più categorie
    if (recoveryPercent > 0) {
      slices.push({
        ...createSlice(currentAngle, currentAngle + recoveryAngle, '#10b981'),
        label: 'Recupero',
        count: recoveryCount,
        percent: recoveryPercent
      })
      currentAngle += recoveryAngle
    }

    if (neutralPercent > 0) {
      slices.push({
        ...createSlice(currentAngle, currentAngle + neutralAngle, '#94a3b8'),
        label: 'Neutri',
        count: neutralCount,
        percent: neutralPercent
      })
      currentAngle += neutralAngle
    }

    if (underperformingPercent > 0) {
      slices.push({
        ...createSlice(currentAngle, currentAngle + underperformingAngle, '#ef4444'),
        label: 'Underperforming',
        count: underperformingCount,
        percent: underperformingPercent
      })
    }
  }

  return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '24px',
      boxShadow: 'var(--shadow-sm)',
      border: '1px solid var(--border-light)',
      gridColumn: 'span 2',
      minWidth: '280px'
    }}>
      <h3 style={{ 
        fontSize: '16px', 
        fontWeight: '600', 
        color: 'var(--text-primary)',
        marginBottom: '20px',
        textAlign: 'center'
      }}>
        📊 Distribuzione Performance Candidati
      </h3>

      {totalEvaluated === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '40px',
          color: 'var(--text-secondary)',
          fontSize: '14px'
        }}>
          Nessun dato disponibile per visualizzare il grafico
        </div>
      ) : (
        <div style={{ 
          display: 'flex', 
          gap: '32px', 
          alignItems: 'center',
          justifyContent: 'center',
          flexWrap: 'wrap'
        }}>
          {/* Grafico a torta SVG */}
          <svg width="200" height="200" viewBox="0 0 200 200" style={{ display: 'block' }}>
            {slices.length === 0 ? (
              <circle cx="100" cy="100" r="80" fill="#e5e7eb" />
            ) : slices.length === 1 && (slices[0].percent === 100) ? (
              // Cerchio completo per una categoria al 100%
              <circle cx="100" cy="100" r="80" fill={slices[0].color} />
            ) : (
              slices.map((slice, index) => (
                <path
                  key={index}
                  d={slice.path}
                  fill={slice.color}
                  stroke="white"
                  strokeWidth="2"
                />
              ))
            )}
          </svg>

        {/* Leggenda */}
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          gap: '12px' 
        }}>
          {slices.map((slice, index) => (
            <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                width: '16px',
                height: '16px',
                borderRadius: '4px',
                background: slice.color,
                flexShrink: 0
              }} />
              <div>
                <div style={{ 
                  fontSize: '14px', 
                  fontWeight: '600', 
                  color: 'var(--text-primary)' 
                }}>
                  {slice.label}
                </div>
                <div style={{ 
                  fontSize: '12px', 
                  color: 'var(--text-secondary)' 
                }}>
                  {slice.count} candidati ({slice.percent.toFixed(1)}%)
                </div>
              </div>
            </div>
          ))}
        </div>
        </div>
      )}

      <div style={{ 
        marginTop: '16px', 
        paddingTop: '16px', 
        borderTop: '1px solid var(--border-light)',
        fontSize: '13px',
        color: 'var(--text-secondary)',
        textAlign: 'center'
      }}>
        <strong>Recupero:</strong> Candidati che hanno performato meglio in colloquio rispetto al CV (miglioramento ≥0.5 punti)<br/>
        <strong>Underperforming:</strong> Candidati che hanno performato peggio in colloquio rispetto al CV (peggioramento ≥0.5 punti)<br/>
        <strong>Neutri:</strong> Candidati con performance allineata tra CV e colloquio
      </div>
    </div>
  )
}