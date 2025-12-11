import { useState, useEffect } from 'react'
import { CheckCircle2, Clock, RefreshCw, Target, FileText, Star, TrendingUp, TrendingDown, Minus, BarChart3, Users, MessageCircle, AlertTriangle, ArrowRight, Briefcase } from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from 'recharts'
import { Skeleton } from '../components/ui/Skeleton'

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
  funnel: {
    cv_analyzed: number
    engaged: number
    interrupted: number
    qualified: number
    interviewed: number
    feedback_ready: number
    feedback_downloaded: number
    total: number
    completed: number
  }
  whatsapp: {
    total_engaged: number
    qualified: number
    interrupted: number
    qualification_rate: number
    interruption_reasons: Array<{ reason: string; count: number }>
    waiting_response?: number
    interrupted_details?: {
      missing_requirements: number
      withdrawal: number
      withdrawal_reasons: Array<{ reason: string; count: number }>
    }
  }
  by_position: Array<{
    position_id: string
    position_name: string
    candidates: number
    qualified: number
    completed: number
    avg_score: number
  }>
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
  const [workflowFilter, setWorkflowFilter] = useState<'full' | 'whatsapp_only'>('full')

  useEffect(() => {
    loadDashboardData()
  }, [selectedTimeRange, selectedPosition, workflowFilter])

  async function loadDashboardData() {
    try {
      setLoading(true)
      const token = localStorage.getItem('hr_jwt')
      if (!token) {
        setError('Token di autenticazione non trovato')
        return
      }

      const response = await fetch(`${API_BASE}/dashboard/data?timeRange=${selectedTimeRange}&positionFilter=${selectedPosition}&workflowFilter=${workflowFilter}`, {
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
          gridTemplateColumns: 'repeat(4, 1fr)', 
          gap: '20px',
          marginBottom: '32px'
        }}>
          {[1, 2, 3, 4].map(i => (
            <div key={i} style={{
              background: 'white',
              borderRadius: '16px',
              border: '1px solid #E5E7EB',
              padding: '20px',
              height: '120px'
            }}>
              <Skeleton width="60%" height="16px" />
              <Skeleton width="40%" height="32px" style={{ marginTop: '12px' }} />
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          <Skeleton height="300px" />
          <Skeleton height="300px" />
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
      
      {/* Header con Filtri */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '20px'
      }}>
        <h2 style={{ margin: 0 }}>Dashboard HR</h2>
        
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <select
            value={selectedTimeRange}
            onChange={(e) => setSelectedTimeRange(e.target.value as any)}
            style={{
              padding: '8px 12px',
              border: '1px solid var(--border-light)',
              borderRadius: '8px',
              background: 'white',
              fontSize: '13px'
            }}
          >
            <option value="7d">Ultimi 7 giorni</option>
            <option value="30d">Ultimi 30 giorni</option>
            <option value="90d">Ultimi 90 giorni</option>
            <option value="1y">Ultimo anno</option>
          </select>
          
          <select
            value={selectedPosition}
            onChange={(e) => setSelectedPosition(e.target.value)}
            style={{
              padding: '8px 12px',
              border: '1px solid var(--border-light)',
              borderRadius: '8px',
              background: 'white',
              fontSize: '13px',
              minWidth: '150px'
            }}
          >
            <option value="all">Tutte le posizioni</option>
            {data.positions.map(position => (
              <option key={position.id} value={position.id}>{position.name}</option>
            ))}
          </select>
        </div>
      </div>
      
      {/* Switch Tipo Workflow */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        marginBottom: '24px'
      }}>
        <div style={{
          display: 'inline-flex',
          background: '#f3f4f6',
          borderRadius: '12px',
          padding: '4px',
          gap: '4px'
        }}>
          <button
            onClick={() => setWorkflowFilter('full')}
            style={{
              padding: '10px 20px',
              border: 'none',
              borderRadius: '10px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '600',
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: workflowFilter === 'full' 
                ? 'linear-gradient(135deg, #6366f1, #8b5cf6)' 
                : 'transparent',
              color: workflowFilter === 'full' ? 'white' : '#6b7280',
              boxShadow: workflowFilter === 'full' ? '0 2px 8px rgba(99, 102, 241, 0.3)' : 'none'
            }}
          >
            <span style={{ fontSize: '16px' }}>🔄</span>
            Iter Completo
            <span style={{ 
              fontSize: '11px', 
              opacity: 0.8,
              fontWeight: '400'
            }}>
              (WhatsApp + Colloquio AI)
            </span>
          </button>
          
          <button
            onClick={() => setWorkflowFilter('whatsapp_only')}
            style={{
              padding: '10px 20px',
              border: 'none',
              borderRadius: '10px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '600',
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: workflowFilter === 'whatsapp_only' 
                ? 'linear-gradient(135deg, #22c55e, #16a34a)' 
                : 'transparent',
              color: workflowFilter === 'whatsapp_only' ? 'white' : '#6b7280',
              boxShadow: workflowFilter === 'whatsapp_only' ? '0 2px 8px rgba(34, 197, 94, 0.3)' : 'none'
            }}
          >
            <span style={{ fontSize: '16px' }}>📱</span>
            Solo WhatsApp
            <span style={{ 
              fontSize: '11px', 
              opacity: 0.8,
              fontWeight: '400'
            }}>
              (Pre-screening)
            </span>
          </button>
        </div>
      </div>

      {/* KPI Principali - Solo 4 card richieste */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(4, 1fr)', 
        gap: '16px',
        marginBottom: '28px'
      }}>
        <KPICard
          title="Candidati Totali"
          value={data.funnel?.total || 0}
          icon={<Users size={22} />}
          color="#6366f1"
          subtitle="Sessioni create"
        />
        <KPICard
          title="Candidature Interrotte"
          value={data.funnel?.interrupted || 0}
          icon={<AlertTriangle size={22} />}
          color="#ef4444"
          subtitle="Candidature non proseguite"
        />
        <KPICard
          title="Recovery Rate"
          value={`${data.metrics.recovery_rate?.toFixed(0) || 0}%`}
          icon={<TrendingUp size={22} />}
          color="#10b981"
          subtitle={`${data.metrics.recovery_count || 0} candidati migliorati`}
        />
        <KPICard
          title="In Attesa di Risposta"
          value={data.whatsapp?.waiting_response || 0}
          icon={<Clock size={22} />}
          color="#8b5cf6"
          subtitle="CV ingaggiati WhatsApp, processo non concluso"
        />
      </div>

      {/* Sezione Grafici - Dettaglio Interrotti */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: '1fr', 
        gap: '24px',
        marginBottom: '28px'
      }}>
        <InterruptedDetailsChart 
          interruptedDetails={data.whatsapp?.interrupted_details}
          totalInterrupted={data.funnel?.interrupted || 0}
        />
      </div>

      {/* Sezione Grafici - Valutazioni */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: '1fr', 
        gap: '24px',
        marginBottom: '28px'
      }}>
        <EvaluationsChart 
          avgCvScore={data.metrics.avg_cv_score}
          avgInterviewScore={data.metrics.avg_interview_score}
          avgOverallScore={data.metrics.avg_overall_score}
        />
      </div>

      {/* Sezione Grafici - 2 colonne */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: '1fr 1fr', 
        gap: '24px',
        marginBottom: '28px'
      }}>
        {/* Funnel di Conversione */}
        <FunnelChart funnel={data.funnel} />
        
        {/* Performance CV vs Colloquio */}
        <PerformancePieChart
          recoveryCount={data.metrics.recovery_count}
          underperformingCount={data.metrics.underperforming_count}
          totalEvaluated={data.metrics.total_evaluated}
        />
      </div>

    </div>
  )
}

// KPI Card compatta
function KPICard({ title, value, icon, color, subtitle }: {
  title: string
  value: number | string
  icon: React.ReactNode
  color: string
  subtitle: string
}) {
  return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '20px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      border: '1px solid var(--border-light)',
      position: 'relative',
      overflow: 'hidden'
    }}>
      <div style={{
        position: 'absolute',
        top: '-15px',
        right: '-15px',
        width: '80px',
        height: '80px',
        background: `radial-gradient(circle, ${color}12, transparent)`,
        borderRadius: '50%'
      }} />
      
      <div style={{ position: 'relative' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            background: `${color}15`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: color
          }}>
            {icon}
          </div>
          <span style={{ 
            fontSize: '12px', 
            fontWeight: '600', 
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.3px'
          }}>
            {title}
          </span>
        </div>
        
        <div style={{ 
          fontSize: '32px', 
          fontWeight: '700', 
          color: 'var(--text-primary)',
          lineHeight: 1,
          marginBottom: '4px'
        }}>
          {value}
        </div>
        
        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          {subtitle}
        </div>
      </div>
    </div>
  )
}

// Funnel di Conversione - Nuova Nomenclatura Stati
function FunnelChart({ funnel }: { funnel: DashboardData['funnel'] }) {
  if (!funnel) return null
  
  // Funnel principale (flusso positivo)
  const mainStages = [
    { name: '📄 CV Analizzati', value: funnel.cv_analyzed, color: '#6366f1', icon: '📄' },
    { name: '📱 Candidati Ingaggiati', value: funnel.engaged, color: '#8b5cf6', icon: '📱' },
    { name: '✓ Pre-screening superato', value: funnel.qualified, color: '#22c55e', icon: '✓' },
    { name: '🎯 Colloquiati', value: funnel.interviewed, color: '#3b82f6', icon: '🎯' },
    { name: '📋 Feedback Pronti', value: funnel.feedback_ready, color: '#f59e0b', icon: '📋' },
    { name: '✅ Feedback Scaricati / inviati', value: funnel.feedback_downloaded, color: '#10b981', icon: '✅' }
  ]
  
  // Totale sessioni per calcolo percentuali
  const totalSessions = funnel.total || Math.max(
    funnel.cv_analyzed + funnel.engaged + funnel.interrupted + funnel.qualified,
    1
  )

  return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '24px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      border: '1px solid var(--border-light)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #6366f120, #22c55e20)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#6366f1'
          }}>
            <TrendingUp size={20} />
          </div>
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>Funnel Candidature</h3>
        </div>
        
        {/* Badge Interrotti */}
        {funnel.interrupted > 0 && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            background: '#fef2f2',
            borderRadius: '8px',
            border: '1px solid #fecaca'
          }}>
            <span style={{ fontSize: '14px' }}>✗</span>
            <span style={{ fontSize: '12px', fontWeight: '600', color: '#dc2626' }}>
              {funnel.interrupted} Interrotti
            </span>
          </div>
        )}
      </div>

      {/* Funnel Visivo */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {mainStages.map((stage, index) => {
          const percentage = totalSessions > 0 ? (stage.value / totalSessions) * 100 : 0
          const prevValue = index > 0 ? mainStages[index - 1].value : totalSessions
          const conversionRate = prevValue > 0 && index > 0
            ? ((stage.value / prevValue) * 100).toFixed(0)
            : null
          
          return (
            <div key={stage.name} style={{ position: 'relative' }}>
              {/* Connettore verticale */}
              {index > 0 && (
                <div style={{
                  position: 'absolute',
                  left: '16px',
                  top: '-8px',
                  width: '2px',
                  height: '8px',
                  background: '#e5e7eb'
                }} />
              )}
              
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '12px',
                padding: '10px 12px',
                background: stage.value > 0 ? `${stage.color}08` : '#f9fafb',
                borderRadius: '10px',
                border: `1px solid ${stage.value > 0 ? `${stage.color}30` : '#e5e7eb'}`,
                transition: 'all 0.2s ease'
              }}>
                {/* Icona circolare */}
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: stage.value > 0 ? stage.color : '#e5e7eb',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontSize: '14px',
                  fontWeight: '600',
                  flexShrink: 0
                }}>
                  {index + 1}
                </div>
                
                {/* Nome e barra */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    marginBottom: '4px'
                  }}>
                    <span style={{ 
                      fontSize: '13px', 
                      fontWeight: '500', 
                      color: stage.value > 0 ? 'var(--text-primary)' : '#9ca3af'
                    }}>
                      {stage.name}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {conversionRate && stage.value > 0 && (
                        <span style={{
                          fontSize: '10px',
                          color: Number(conversionRate) >= 50 ? '#22c55e' : '#f59e0b',
                          background: Number(conversionRate) >= 50 ? '#f0fdf4' : '#fffbeb',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontWeight: '600'
                        }}>
                          {conversionRate}%
                        </span>
                      )}
                      <span style={{ 
                        fontSize: '16px', 
                        fontWeight: '700', 
                        color: stage.value > 0 ? stage.color : '#d1d5db',
                        minWidth: '28px',
                        textAlign: 'right'
                      }}>
                        {stage.value}
                      </span>
                    </div>
                  </div>
                  
                  {/* Progress bar */}
                  <div style={{ 
                    height: '6px', 
                    background: '#e5e7eb', 
                    borderRadius: '3px',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.min(percentage, 100)}%`,
                      background: stage.value > 0 
                        ? `linear-gradient(90deg, ${stage.color}, ${stage.color}aa)` 
                        : 'transparent',
                      borderRadius: '3px',
                      transition: 'width 0.5s ease'
                    }} />
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
      
      {/* Summary footer */}
      <div style={{
        marginTop: '16px',
        paddingTop: '16px',
        borderTop: '1px solid #e5e7eb',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
          Totale candidature: <strong>{totalSessions}</strong>
        </span>
        {funnel.completed > 0 && (
          <span style={{ 
            fontSize: '12px', 
            color: '#22c55e',
            fontWeight: '600'
          }}>
            Conversion rate: {((funnel.feedback_downloaded / totalSessions) * 100).toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  )
}

// Performance per Posizione
function PositionChart({ positions }: { positions: DashboardData['by_position'] }) {
  if (!positions || positions.length === 0) {
    return (
      <div style={{
        background: 'white',
        borderRadius: '16px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        border: '1px solid var(--border-light)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '280px'
      }}>
        <Briefcase size={48} style={{ color: '#d1d5db', marginBottom: '12px' }} />
        <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Nessuna posizione con dati</p>
      </div>
    )
  }

  const chartData = positions.slice(0, 5).map(p => ({
    name: p.position_name.length > 15 ? p.position_name.substring(0, 15) + '...' : p.position_name,
    Candidati: p.candidates,
    Qualificati: p.qualified,
    Completati: p.completed
  }))

  return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '24px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      border: '1px solid var(--border-light)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #3b82f620, #6366f120)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#3b82f6'
        }}>
          <Briefcase size={20} />
        </div>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>Performance per Posizione</h3>
      </div>

      <div style={{ height: '220px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ left: 0, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={100} />
            <Tooltip 
              contentStyle={{ 
                background: 'rgba(0,0,0,0.9)', 
                border: 'none', 
                borderRadius: '8px',
                fontSize: '12px'
              }}
            />
            <Legend wrapperStyle={{ fontSize: '11px' }} />
            <Bar dataKey="Candidati" fill="#6366f1" radius={[0, 4, 4, 0]} />
            <Bar dataKey="Qualificati" fill="#22c55e" radius={[0, 4, 4, 0]} />
            <Bar dataKey="Completati" fill="#10b981" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}


// Performance Pie Chart (compatto)
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
    { name: 'Recupero', value: recoveryCount, color: '#10b981' },
    { name: 'Neutri', value: neutralCount, color: '#94a3b8' },
    { name: 'Underperforming', value: underperformingCount, color: '#ef4444' }
  ].filter(item => item.value > 0)

  const COLORS = data.map(item => item.color)

  return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '24px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      border: '1px solid var(--border-light)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #7C3AED20, #EC489920)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#7C3AED'
        }}>
          <BarChart3 size={20} />
        </div>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>Performance CV vs Colloquio</h3>
      </div>

      {totalEvaluated === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '40px 20px',
          color: 'var(--text-secondary)',
          fontSize: '13px'
        }}>
          <BarChart3 size={40} style={{ color: '#d1d5db', marginBottom: '8px' }} />
          <p style={{ margin: 0 }}>Nessun dato disponibile</p>
        </div>
      ) : (
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          {/* Pie Chart */}
          <div style={{ width: '140px', height: '140px', flexShrink: 0 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  outerRadius={60}
                  innerRadius={40}
                  dataKey="value"
                  animationDuration={600}
                >
                  {data.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{
                    background: 'rgba(0,0,0,0.9)',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '11px'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Legend */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flex: 1 }}>
            {data.map((item, index) => (
              <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{
                  width: '10px',
                  height: '10px',
                  borderRadius: '3px',
                  background: item.color,
                  flexShrink: 0
                }} />
                <span style={{ fontSize: '12px', color: 'var(--text-primary)', flex: 1 }}>
                  {item.name}
                </span>
                <span style={{ 
                  fontSize: '13px', 
                  fontWeight: '700', 
                  color: item.color 
                }}>
                  {item.value}
                </span>
              </div>
            ))}
            
            <div style={{ 
              marginTop: '8px', 
              paddingTop: '8px', 
              borderTop: '1px solid var(--border-light)',
              fontSize: '11px',
              color: 'var(--text-muted)'
            }}>
              <div>Recupero: +0.5 punti dal CV</div>
              <div>Underperf: -0.5 punti dal CV</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Grafico Dettaglio Interrotti
function InterruptedDetailsChart({ 
  interruptedDetails, 
  totalInterrupted 
}: { 
  interruptedDetails?: {
    missing_requirements: number
    withdrawal: number
    withdrawal_reasons: Array<{ reason: string; count: number }>
  }
  totalInterrupted: number
}) {
  if (!interruptedDetails || totalInterrupted === 0) {
    return (
      <div style={{
        background: 'white',
        borderRadius: '16px',
        padding: '24px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        border: '1px solid var(--border-light)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '280px'
      }}>
        <AlertTriangle size={48} style={{ color: '#d1d5db', marginBottom: '12px' }} />
        <p style={{ color: 'var(--text-secondary)', margin: 0 }}>Nessuna candidatura interrotta</p>
      </div>
    )
  }

  const { missing_requirements, withdrawal, withdrawal_reasons } = interruptedDetails

  const chartData = [
    { name: 'Mancanza Requisiti Base', value: missing_requirements, color: '#ef4444' },
    { name: 'Ritiro Candidatura', value: withdrawal, color: '#f59e0b' }
  ].filter(item => item.value > 0)

  const COLORS = chartData.map(item => item.color)

  return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '24px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      border: '1px solid var(--border-light)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #ef444420, #f59e0b20)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#ef4444'
        }}>
          <AlertTriangle size={20} />
        </div>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>Dettaglio Candidature Interrotte</h3>
      </div>

      <div style={{ display: 'flex', gap: '32px', alignItems: 'flex-start' }}>
        {/* Pie Chart */}
        <div style={{ width: '200px', height: '200px', flexShrink: 0 }}>
          <ResponsiveContainer>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                outerRadius={80}
                innerRadius={40}
                dataKey="value"
                animationDuration={600}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index]} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{
                  background: 'rgba(0,0,0,0.9)',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '11px'
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Dettagli */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Statistiche principali */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {chartData.map((item, index) => (
              <div key={index} style={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'space-between',
                padding: '12px',
                background: `${item.color}08`,
                borderRadius: '8px',
                border: `1px solid ${item.color}30`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '3px',
                    background: item.color,
                    flexShrink: 0
                  }} />
                  <span style={{ fontSize: '14px', fontWeight: '500', color: 'var(--text-primary)' }}>
                    {item.name}
                  </span>
                </div>
                <span style={{ 
                  fontSize: '18px', 
                  fontWeight: '700', 
                  color: item.color 
                }}>
                  {item.value}
                </span>
              </div>
            ))}
          </div>

          {/* Motivazioni ritiro (se presenti) */}
          {withdrawal > 0 && withdrawal_reasons && withdrawal_reasons.length > 0 && (
            <div style={{ 
              marginTop: '8px',
              paddingTop: '16px',
              borderTop: '1px solid var(--border-light)'
            }}>
              <div style={{ 
                fontSize: '12px', 
                fontWeight: '600', 
                color: 'var(--text-secondary)',
                marginBottom: '12px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Motivazioni Ritiro Candidatura
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {withdrawal_reasons.slice(0, 5).map((item, index) => (
                  <div key={index} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 12px',
                    background: '#f9fafb',
                    borderRadius: '6px',
                    fontSize: '13px'
                  }}>
                    <span style={{ 
                      color: 'var(--text-primary)',
                      flex: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      marginRight: '12px'
                    }}>
                      {item.reason}
                    </span>
                    <span style={{ 
                      fontSize: '14px', 
                      fontWeight: '600', 
                      color: '#f59e0b',
                      flexShrink: 0
                    }}>
                      {item.count}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Card Valutazioni (solo numeri, senza grafico)
function EvaluationsChart({ 
  avgCvScore, 
  avgInterviewScore, 
  avgOverallScore 
}: { 
  avgCvScore: number
  avgInterviewScore: number
  avgOverallScore: number
}) {
  return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '20px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      border: '1px solid var(--border-light)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #6366f120, #8b5cf620)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#6366f1'
        }}>
          <Star size={20} />
        </div>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>Valutazioni Candidati</h3>
        <span style={{ 
          fontSize: '11px', 
          color: 'var(--text-muted)',
          marginLeft: 'auto',
          padding: '4px 8px',
          background: '#f3f4f6',
          borderRadius: '6px'
        }}>
          Scala: 0-4
        </span>
      </div>

      {/* Valori sintetici */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        gap: '16px',
        marginTop: '8px'
      }}>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '4px',
          flex: 1
        }}>
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: '500' }}>
            Valutazione CV
          </span>
          <span style={{ 
            fontSize: '22px', 
            fontWeight: '700', 
            color: '#6366f1' 
          }}>
            {avgCvScore.toFixed(2)}
          </span>
        </div>

        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '4px',
          flex: 1
        }}>
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: '500' }}>
            Valutazione Colloquio
          </span>
          <span style={{ 
            fontSize: '22px', 
            fontWeight: '700', 
            color: '#3b82f6' 
          }}>
            {avgInterviewScore.toFixed(2)}
          </span>
        </div>

        <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '4px',
            flex: 1
        }}>
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: '500' }}>
            Valutazione Complessiva
          </span>
          <span style={{ 
            fontSize: '22px', 
            fontWeight: '700', 
            color: '#8b5cf6' 
          }}>
            {avgOverallScore.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  )
}
