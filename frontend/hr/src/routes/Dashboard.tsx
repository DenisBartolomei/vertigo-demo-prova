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
  const [isDownloading, setIsDownloading] = useState(false) // NUOVO STATO

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

  // --- NUOVA FUNZIONE PER SCARICARE IL REPORT ---
  async function downloadDashboardReport() {
    setIsDownloading(true);
    const token = localStorage.getItem('hr_jwt');
    if (!token) {
      alert('Errore: Token di autenticazione non trovato.');
      setIsDownloading(false);
      return;
    }

    try {
      // Costruisce l'URL con i filtri correnti. L'endpoint /dashboard/report/pdf è ipotetico
      // e dovrà essere implementato nel backend.
      const reportUrl = `${API_BASE}/dashboard/report/pdf?timeRange=${selectedTimeRange}&positionFilter=${selectedPosition}`;
      
      const response = await fetch(reportUrl, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Errore dal server (${response.status}): ${errorText || 'Impossibile generare il report.'}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Report_Dashboard_${selectedPosition}_${new Date().toLocaleDateString('it-IT')}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

    } catch (error) {
      console.error('Errore nel download del report:', error);
      alert(error instanceof Error ? error.message : 'Si è verificato un errore imprevisto durante il download.');
    } finally {
      setIsDownloading(false);
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

          {/* --- NUOVO PULSANTE DI DOWNLOAD --- */}
          <button
            onClick={downloadDashboardReport}
            disabled={isDownloading}
            style={{
              padding: '8px 16px',
              background: 'var(--primary-purple)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: isDownloading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              opacity: isDownloading ? 0.7 : 1,
              fontSize: '14px',
              fontWeight: '500',
              marginLeft: '8px'
            }}
          >
            {isDownloading ? '📥 In download...' : '📥 Scarica Report'}
          </button>
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

  const recoveryPercent = (recoveryCount / total) * 100
  const underperformingPercent = (underperformingCount / total) * 100
  const neutralPercent = (neutralCount / total) * 100

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

      <div style={{ 
        display: 'flex', 
        gap: '32px', 
        alignItems: 'center',
        justifyContent: 'center',
        flexWrap: 'wrap'
      }}>
        {/* Grafico a torta SVG */}
        <svg width="200" height="200" viewBox="0 0 200 200">
          {slices.map((slice, index) => (
            <path
              key={index}
              d={slice.path}
              fill={slice.color}
              stroke="white"
              strokeWidth="2"
            />
          ))}
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