import { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

interface DashboardData {
  overview: {
    totalPositions: number
    totalSessions: number
    activeSessions: number
    completedSessions: number
    totalUsers: number
    avgCompletionTime: number
  }
  positions: Array<{
    _id: string
    position_name: string
    totalSessions: number
    completedSessions: number
    avgScore: number
    lastActivity: string
  }>
  recentActivity: Array<{
    type: 'session_created' | 'session_completed' | 'feedback_generated' | 'token_sent'
    session_id: string
    candidate_name: string
    position_name: string
    timestamp: string
    user_name?: string
  }>
  performanceMetrics: {
    completionRate: number
    avgInterviewDuration: number
    feedbackGenerationTime: number
    tokenUsageRate: number
  }
  skillAnalytics: Array<{
    skill: string
    avgScore: number
    frequency: number
    trend: 'up' | 'down' | 'stable'
  }>
  monthlyTrends: Array<{
    month: string
    sessions: number
    completions: number
    avgScore: number
  }>
}

export function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTimeRange, setSelectedTimeRange] = useState<'7d' | '30d' | '90d' | '1y'>('30d')

  useEffect(() => {
    loadDashboardData()
  }, [selectedTimeRange])

  async function loadDashboardData() {
    try {
      setLoading(true)
      const token = localStorage.getItem('hr_jwt')
      if (!token) {
        setError('Token di autenticazione non trovato')
        return
      }

      const response = await fetch(`${API_BASE}/dashboard/data?timeRange=${selectedTimeRange}`, {
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
      {/* Disclaimer */}
      <div style={{
        background: 'linear-gradient(135deg, #fef3c7, #fde68a)',
        border: '2px solid #f59e0b',
        borderRadius: '12px',
        padding: '16px 20px',
        marginBottom: '24px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        boxShadow: '0 4px 6px rgba(245, 158, 11, 0.1)'
      }}>
        <div style={{ fontSize: '24px' }}>⚠️</div>
        <div>
          <div style={{
            fontSize: '16px',
            fontWeight: '700',
            color: '#92400e',
            marginBottom: '4px'
          }}>
            AVVISO IMPORTANTE
          </div>
          <div style={{
            fontSize: '14px',
            color: '#92400e',
            lineHeight: '1.5'
          }}>
            <strong>I dati mostrati in questa dashboard sono FITTIZI e servono solo a scopo dimostrativo.</strong><br/>
            La dashboard completa sarà implementata in una versione futura del prodotto.
          </div>
        </div>
      </div>
      
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
            Panoramica completa del processo di recruitment
          </p>
        </div>
        
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <label style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
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
              fontSize: '14px'
            }}
          >
            <option value="7d">Ultimi 7 giorni</option>
            <option value="30d">Ultimi 30 giorni</option>
            <option value="90d">Ultimi 90 giorni</option>
            <option value="1y">Ultimo anno</option>
          </select>
        </div>
      </div>

      {/* Overview Cards */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
        gap: '24px',
        marginBottom: '32px'
      }}>
        <MetricCard
          title="Posizioni Attive"
          value={data.overview.totalPositions}
          icon="💼"
          color="var(--primary-purple)"
          trend={data.overview.totalPositions > 0 ? 'up' : 'stable'}
        />
        <MetricCard
          title="Sessioni Totali"
          value={data.overview.totalSessions}
          icon="👥"
          color="var(--accent-purple)"
          trend="up"
        />
        <MetricCard
          title="Sessioni Attive"
          value={data.overview.activeSessions}
          icon="🔄"
          color="#f59e0b"
          trend="stable"
        />
        <MetricCard
          title="Completate"
          value={data.overview.completedSessions}
          icon="✅"
          color="#10b981"
          trend="up"
        />
        <MetricCard
          title="Utenti HR"
          value={data.overview.totalUsers}
          icon="👤"
          color="#8b5cf6"
          trend="stable"
        />
        <MetricCard
          title="Tempo Medio"
          value={`${Math.round(data.overview.avgCompletionTime)}m`}
          icon="⏱️"
          color="#06b6d4"
          trend="down"
        />
      </div>

      {/* Main Content Grid */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: '2fr 1fr', 
        gap: '32px',
        marginBottom: '32px'
      }}>
        {/* Positions Performance */}
        <div style={{
          background: 'white',
          borderRadius: '16px',
          padding: '24px',
          boxShadow: 'var(--shadow-sm)',
          border: '1px solid var(--border-light)'
        }}>
          <h2 style={{ 
            fontSize: '20px', 
            fontWeight: '600', 
            margin: '0 0 20px 0',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            📈 Performance per Posizione
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {data.positions.map((position) => (
              <PositionCard key={position._id} position={position} />
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div style={{
          background: 'white',
          borderRadius: '16px',
          padding: '24px',
          boxShadow: 'var(--shadow-sm)',
          border: '1px solid var(--border-light)'
        }}>
          <h2 style={{ 
            fontSize: '20px', 
            fontWeight: '600', 
            margin: '0 0 20px 0',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            🔔 Attività Recente
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {data.recentActivity.map((activity, index) => (
              <ActivityItem key={index} activity={activity} />
            ))}
          </div>
        </div>
      </div>

      {/* Performance Metrics */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
        gap: '24px',
        marginBottom: '32px'
      }}>
        <PerformanceChart
          title="Tasso di Completamento"
          value={data.performanceMetrics.completionRate}
          unit="%"
          color="#10b981"
          icon="📊"
        />
        <PerformanceChart
          title="Durata Media Intervista"
          value={data.performanceMetrics.avgInterviewDuration}
          unit="min"
          color="#3b82f6"
          icon="⏱️"
        />
        <PerformanceChart
          title="Tempo Generazione Feedback"
          value={data.performanceMetrics.feedbackGenerationTime}
          unit="min"
          color="#f59e0b"
          icon="📝"
        />
        <PerformanceChart
          title="Utilizzo Token"
          value={data.performanceMetrics.tokenUsageRate}
          unit="%"
          color="#8b5cf6"
          icon="🔗"
        />
      </div>

      {/* Skill Analytics */}
      <div style={{
        background: 'white',
        borderRadius: '16px',
        padding: '24px',
        boxShadow: 'var(--shadow-sm)',
        border: '1px solid var(--border-light)',
        marginBottom: '32px'
      }}>
        <h2 style={{ 
          fontSize: '20px', 
          fontWeight: '600', 
          margin: '0 0 20px 0',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          🎯 Analisi Competenze
        </h2>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: '16px' 
        }}>
          {data.skillAnalytics.map((skill, index) => (
            <SkillCard key={index} skill={skill} />
          ))}
        </div>
      </div>

      {/* Monthly Trends */}
      <div style={{
        background: 'white',
        borderRadius: '16px',
        padding: '24px',
        boxShadow: 'var(--shadow-sm)',
        border: '1px solid var(--border-light)'
      }}>
        <h2 style={{ 
          fontSize: '20px', 
          fontWeight: '600', 
          margin: '0 0 20px 0',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          📅 Tendenze Mensili
        </h2>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', 
          gap: '16px' 
        }}>
          {data.monthlyTrends.map((trend, index) => (
            <TrendCard key={index} trend={trend} />
          ))}
        </div>
      </div>
    </div>
  )
}

// Component for metric cards
function MetricCard({ title, value, icon, color, trend }: {
  title: string
  value: number | string
  icon: string
  color: string
  trend: 'up' | 'down' | 'stable'
}) {
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
          <h3 style={{ 
            fontSize: '14px', 
            fontWeight: '500', 
            color: 'var(--text-secondary)',
            margin: '0 0 4px 0'
          }}>
            {title}
          </h3>
          <div style={{ 
            fontSize: '28px', 
            fontWeight: '700', 
            color: 'var(--text-primary)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            {value}
            {trend === 'up' && <span style={{ color: '#10b981', fontSize: '16px' }}>↗️</span>}
            {trend === 'down' && <span style={{ color: '#ef4444', fontSize: '16px' }}>↘️</span>}
            {trend === 'stable' && <span style={{ color: 'var(--text-muted)', fontSize: '16px' }}>→</span>}
          </div>
        </div>
      </div>
    </div>
  )
}

// Component for position cards
function PositionCard({ position }: { position: DashboardData['positions'][0] }) {
  const completionRate = position.totalSessions > 0 
    ? Math.round((position.completedSessions / position.totalSessions) * 100) 
    : 0

  return (
    <div style={{
      padding: '16px',
      border: '1px solid var(--border-light)',
      borderRadius: '12px',
      background: 'var(--bg-secondary)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
        <h4 style={{ 
          fontSize: '16px', 
          fontWeight: '600', 
          margin: '0',
          color: 'var(--text-primary)'
        }}>
          {position.position_name}
        </h4>
        <div style={{
          fontSize: '12px',
          color: 'var(--text-muted)',
          background: 'white',
          padding: '4px 8px',
          borderRadius: '6px',
          border: '1px solid var(--border-light)'
        }}>
          {position.lastActivity}
        </div>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '20px', fontWeight: '600', color: 'var(--primary-purple)' }}>
            {position.totalSessions}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Sessioni
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '20px', fontWeight: '600', color: '#10b981' }}>
            {completionRate}%
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Completate
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '20px', fontWeight: '600', color: '#f59e0b' }}>
            {position.avgScore.toFixed(1)}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Punteggio
          </div>
        </div>
      </div>
    </div>
  )
}

// Component for activity items
function ActivityItem({ activity }: { activity: DashboardData['recentActivity'][0] }) {
  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'session_created': return '🆕'
      case 'session_completed': return '✅'
      case 'feedback_generated': return '📝'
      case 'token_sent': return '📧'
      default: return '📋'
    }
  }

  const getActivityColor = (type: string) => {
    switch (type) {
      case 'session_created': return '#3b82f6'
      case 'session_completed': return '#10b981'
      case 'feedback_generated': return '#f59e0b'
      case 'token_sent': return '#8b5cf6'
      default: return 'var(--text-muted)'
    }
  }

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      padding: '12px',
      background: 'var(--bg-secondary)',
      borderRadius: '8px',
      border: '1px solid var(--border-light)'
    }}>
      <div style={{
        fontSize: '20px',
        width: '32px',
        height: '32px',
        borderRadius: '8px',
        background: `${getActivityColor(activity.type)}20`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        {getActivityIcon(activity.type)}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ 
          fontSize: '14px', 
          fontWeight: '500',
          color: 'var(--text-primary)',
          marginBottom: '2px'
        }}>
          {activity.candidate_name}
        </div>
        <div style={{ 
          fontSize: '12px', 
          color: 'var(--text-secondary)',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis'
        }}>
          {activity.position_name}
        </div>
      </div>
      <div style={{
        fontSize: '11px',
        color: 'var(--text-muted)',
        whiteSpace: 'nowrap'
      }}>
        {new Date(activity.timestamp).toLocaleDateString('it-IT')}
      </div>
    </div>
  )
}

// Component for performance charts
function PerformanceChart({ title, value, unit, color, icon }: {
  title: string
  value: number
  unit: string
  color: string
  icon: string
}) {
  return (
    <div style={{
      background: 'white',
      borderRadius: '16px',
      padding: '24px',
      boxShadow: 'var(--shadow-sm)',
      border: '1px solid var(--border-light)',
      textAlign: 'center'
    }}>
      <div style={{
        fontSize: '32px',
        marginBottom: '12px'
      }}>
        {icon}
      </div>
      <h3 style={{ 
        fontSize: '16px', 
        fontWeight: '600', 
        margin: '0 0 8px 0',
        color: 'var(--text-primary)'
      }}>
        {title}
      </h3>
      <div style={{ 
        fontSize: '32px', 
        fontWeight: '700', 
        color: color,
        marginBottom: '8px'
      }}>
        {value.toFixed(1)}{unit}
      </div>
      <div style={{
        width: '100%',
        height: '8px',
        background: 'var(--bg-secondary)',
        borderRadius: '4px',
        overflow: 'hidden'
      }}>
        <div style={{
          width: `${Math.min(value, 100)}%`,
          height: '100%',
          background: `linear-gradient(90deg, ${color}, ${color}80)`,
          borderRadius: '4px',
          transition: 'width 0.3s ease'
        }} />
      </div>
    </div>
  )
}

// Component for skill cards
function SkillCard({ skill }: { skill: DashboardData['skillAnalytics'][0] }) {
  return (
    <div style={{
      padding: '16px',
      border: '1px solid var(--border-light)',
      borderRadius: '12px',
      background: 'var(--bg-secondary)',
      textAlign: 'center'
    }}>
      <h4 style={{ 
        fontSize: '14px', 
        fontWeight: '600', 
        margin: '0 0 8px 0',
        color: 'var(--text-primary)'
      }}>
        {skill.skill}
      </h4>
      <div style={{ 
        fontSize: '24px', 
        fontWeight: '700', 
        color: 'var(--primary-purple)',
        marginBottom: '4px'
      }}>
        {skill.avgScore.toFixed(1)}
      </div>
      <div style={{ 
        fontSize: '12px', 
        color: 'var(--text-secondary)',
        marginBottom: '8px'
      }}>
        {skill.frequency} valutazioni
      </div>
      <div style={{
        fontSize: '16px',
        color: skill.trend === 'up' ? '#10b981' : skill.trend === 'down' ? '#ef4444' : 'var(--text-muted)'
      }}>
        {skill.trend === 'up' ? '↗️' : skill.trend === 'down' ? '↘️' : '→'}
      </div>
    </div>
  )
}

// Component for trend cards
function TrendCard({ trend }: { trend: DashboardData['monthlyTrends'][0] }) {
  return (
    <div style={{
      padding: '16px',
      border: '1px solid var(--border-light)',
      borderRadius: '12px',
      background: 'var(--bg-secondary)',
      textAlign: 'center'
    }}>
      <h4 style={{ 
        fontSize: '14px', 
        fontWeight: '600', 
        margin: '0 0 12px 0',
        color: 'var(--text-primary)'
      }}>
        {trend.month}
      </h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div>
          <div style={{ fontSize: '18px', fontWeight: '600', color: 'var(--primary-purple)' }}>
            {trend.sessions}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            Sessioni
          </div>
        </div>
        <div>
          <div style={{ fontSize: '18px', fontWeight: '600', color: '#10b981' }}>
            {trend.completions}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            Completate
          </div>
        </div>
        <div>
          <div style={{ fontSize: '18px', fontWeight: '600', color: '#f59e0b' }}>
            {trend.avgScore.toFixed(1)}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            Punteggio
          </div>
        </div>
      </div>
    </div>
  )
}
