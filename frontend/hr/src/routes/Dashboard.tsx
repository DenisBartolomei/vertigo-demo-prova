import { useState, useEffect } from 'react'
import { CheckCircle2, Clock, RefreshCw, Target, FileText, Star, TrendingUp, TrendingDown, Minus, BarChart3 } from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'
import { Skeleton } from '../components/ui/Skeleton'
import { Badge } from '../components/ui/Badge'

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
      <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
        <div style={{ marginBottom: '24px' }}>
          <Skeleton width="200px" height="32px" />
        </div>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(3, 1fr)', 
          gap: '24px',
          marginBottom: '32px'
        }}>
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} style={{
              background: 'white',
              borderRadius: '20px',
              border: '1px solid #E5E7EB',
              padding: '24px'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                marginBottom: '16px'
              }}>
                <Skeleton circle width={48} height={48} />
                <div style={{ flex: 1 }}>
                  <Skeleton width="60%" height="16px" />
                  <Skeleton width="80%" height="24px" style={{ marginTop: '8px' }} />
                </div>
              </div>
            </div>
          ))}
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
          icon={<CheckCircle2 />}
          color="#10b981"
          tooltip="Candidati che hanno terminato l'intervista con successo e ricevuto valutazione completa"
        />
        <MetricCard
          title="Candidati in Attesa di Token"
          value={data.metrics.waiting_token}
          icon={<Clock />}
          color="#f59e0b"
          tooltip="CV analizzati con token generato ma non ancora inviato al candidato"
        />
        <MetricCard
          title="Colloquio in Corso"
          value={data.metrics.in_progress}
          icon={<RefreshCw />}
          color="#3b82f6"
          tooltip="Candidati che hanno ricevuto il token ma non hanno ancora completato l'intervista"
        />
        <MetricCard
          title="Scoring Medio Colloqui"
          value={data.metrics.avg_interview_score.toFixed(2)}
          icon={<Target />}
          color="#3b82f6"
          tooltip="Punteggio medio ottenuto dai candidati durante le interviste, su una scala da 0 a 4"
        />
        <MetricCard
          title="Scoring Medio CV"
          value={data.metrics.avg_cv_score.toFixed(2)}
          icon={<FileText />}
          color="#8b5cf6"
          tooltip="Punteggio medio ottenuto dai candidati nell'analisi dei CV, su una scala da 0 a 4"
        />
        <MetricCard
          title="Scoring Complessivo"
          value={data.metrics.avg_overall_score.toFixed(2)}
          icon={<Star />}
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
  icon: React.ReactNode
  color: string
  tooltip: string
}) {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div className="hover-lift" style={{
      background: 'white',
      borderRadius: '20px',
      padding: '24px',
      boxShadow: 'var(--shadow-md)',
      border: '1px solid var(--border-light)',
      position: 'relative',
      overflow: 'hidden',
      transition: 'all var(--transition-normal)'
    }}>
      {/* Decorative background */}
      <div style={{
        position: 'absolute',
        top: '-20px',
        right: '-20px',
        width: '140px',
        height: '140px',
        background: `radial-gradient(circle, ${color}15, transparent)`,
        borderRadius: '50%',
        pointerEvents: 'none'
      }} />
      
      <div style={{ position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
              <h3 style={{ 
                fontSize: '14px', 
                fontWeight: '600', 
                color: 'var(--text-secondary)',
                margin: 0,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                {title}
              </h3>
              <div 
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
                style={{ position: 'relative', display: 'inline-block', cursor: 'help' }}
              >
                <span style={{ 
                  fontSize: '12px', 
                  color: 'var(--text-muted)',
                  width: '16px',
                  height: '16px',
                  borderRadius: '50%',
                  border: '1.5px solid currentColor',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: '600'
                }}>
                  ?
                </span>
                {showTooltip && (
                  <div className="slide-down" style={{
                    position: 'fixed',
                    background: 'rgba(0,0,0,0.95)',
                    color: 'white',
                    padding: '12px 16px',
                    borderRadius: '10px',
                    fontSize: '13px',
                    lineHeight: '1.5',
                    maxWidth: '300px',
                    zIndex: 10000,
                    boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                    whiteSpace: 'normal',
                    pointerEvents: 'none',
                    marginTop: '4px',
                    marginLeft: '8px'
                  }}>
                    {tooltip}
                  </div>
                )}
              </div>
            </div>
            <div style={{ 
              fontSize: '36px', 
              fontWeight: '700', 
              color: 'var(--text-primary)',
              lineHeight: 1,
              fontFamily: "'Manrope', 'Inter', sans-serif"
            }}>
              {value}
            </div>
          </div>
          <div style={{
            width: '56px',
            height: '56px',
            borderRadius: '16px',
            background: `linear-gradient(135deg, ${color}20, ${color}10)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: color,
            flexShrink: 0
          }}>
            {icon}
          </div>
        </div>
      </div>
    </div>
  )
}

// Performance Pie Chart Component with Recharts
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
  
  const data = [
    { name: 'Recupero', value: recoveryCount, color: '#10b981', icon: <TrendingUp size={16} /> },
    { name: 'Neutri', value: neutralCount, color: '#94a3b8', icon: <Minus size={16} /> },
    { name: 'Underperforming', value: underperformingCount, color: '#ef4444', icon: <TrendingDown size={16} /> }
  ].filter(item => item.value > 0)

  const COLORS = data.map(item => item.color)

  return (
    <div className="hover-lift" style={{
      background: 'white',
      borderRadius: '20px',
      padding: '32px',
      boxShadow: 'var(--shadow-md)',
      border: '1px solid var(--border-light)',
      gridColumn: 'span 2',
      minWidth: '280px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
        <div style={{
          width: '48px',
          height: '48px',
          borderRadius: '14px',
          background: 'linear-gradient(135deg, #7C3AED20, #EC489910)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#7C3AED'
        }}>
          <BarChart3 size={24} />
        </div>
        <h3 style={{ 
          fontSize: '18px', 
          fontWeight: '700', 
          color: 'var(--text-primary)',
          margin: 0
        }}>
          Distribuzione Performance Candidati
        </h3>
      </div>

      {totalEvaluated === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '60px 20px',
          color: 'var(--text-secondary)',
          fontSize: '15px'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.3 }}>📊</div>
          <p style={{ margin: 0 }}>Nessun dato disponibile per visualizzare il grafico</p>
        </div>
      ) : (
        <div>
          <div style={{ 
            display: 'flex', 
            gap: '48px', 
            alignItems: 'center',
            justifyContent: 'center',
            flexWrap: 'wrap',
            marginBottom: '24px'
          }}>
            {/* Recharts Pie Chart */}
            <div style={{ width: '260px', height: '260px' }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={data}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    outerRadius={100}
                    innerRadius={60}
                    fill="#8884d8"
                    dataKey="value"
                    animationBegin={0}
                    animationDuration={800}
                  >
                    {data.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{
                      background: 'rgba(0,0,0,0.9)',
                      border: 'none',
                      borderRadius: '8px',
                      color: 'white',
                      padding: '8px 12px',
                      fontSize: '13px'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Legend */}
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              gap: '16px' 
            }}>
              {data.map((item, index) => (
                <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '10px',
                    background: `${item.color}20`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: item.color,
                    flexShrink: 0
                  }}>
                    {item.icon}
                  </div>
                  <div>
                    <div style={{ 
                      fontSize: '15px', 
                      fontWeight: '600', 
                      color: 'var(--text-primary)',
                      marginBottom: '2px'
                    }}>
                      {item.name}
                    </div>
                    <div style={{ 
                      fontSize: '13px', 
                      color: 'var(--text-secondary)' 
                    }}>
                      {item.value} candidati ({((item.value / totalEvaluated) * 100).toFixed(1)}%)
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Info Box */}
          <div style={{ 
            marginTop: '24px', 
            paddingTop: '24px', 
            borderTop: '1px solid var(--border-light)',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px'
          }}>
            <div style={{
              padding: '12px',
              background: '#10b98110',
              borderRadius: '10px',
              borderLeft: '3px solid #10b981'
            }}>
              <div style={{ fontSize: '12px', fontWeight: '600', color: '#10b981', marginBottom: '4px' }}>
                RECUPERO
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                Miglioramento ≥0.5 punti rispetto al CV
              </div>
            </div>
            <div style={{
              padding: '12px',
              background: '#ef444410',
              borderRadius: '10px',
              borderLeft: '3px solid #ef4444'
            }}>
              <div style={{ fontSize: '12px', fontWeight: '600', color: '#ef4444', marginBottom: '4px' }}>
                UNDERPERFORMING
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                Peggioramento ≥0.5 punti rispetto al CV
              </div>
            </div>
            <div style={{
              padding: '12px',
              background: '#94a3b810',
              borderRadius: '10px',
              borderLeft: '3px solid #94a3b8'
            }}>
              <div style={{ fontSize: '12px', fontWeight: '600', color: '#94a3b8', marginBottom: '4px' }}>
                NEUTRI
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                Performance allineata tra CV e colloquio
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}