import React, { useState, useEffect } from 'react'

interface Batch {
  _id: string
  status: string
  created_at: string
  total_requests: number
  request_counts?: {
    total: number
    completed: number
    failed: number
  }
}

interface BatchStatusMonitorProps {
  refreshInterval?: number
}

export function BatchStatusMonitor({ refreshInterval = 30000 }: BatchStatusMonitorProps) {
  const [batches, setBatches] = useState<Batch[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchBatches = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const token = localStorage.getItem('hr_jwt')
      if (!token) {
        throw new Error('No authentication token found')
      }
      
      const API_BASE = import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'
      const response = await fetch(`${API_BASE}/api/batch/list`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication expired')
        }
        throw new Error(`Failed to fetch batches: ${response.statusText}`)
      }
      
      const data = await response.json()
      setBatches(data.batches || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBatches()
    
    const interval = setInterval(fetchBatches, refreshInterval)
    return () => clearInterval(interval)
  }, [refreshInterval])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#10b981'
      case 'in_progress': return '#3b82f6'
      case 'validating': return '#f59e0b'
      case 'failed': return '#ef4444'
      case 'processed': return '#8b5cf6'
      default: return '#6b7280'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✅'
      case 'in_progress': return '⏳'
      case 'validating': return '🔍'
      case 'failed': return '❌'
      case 'processed': return '📥'
      default: return '❓'
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getProgressPercentage = (batch: Batch) => {
    if (!batch.request_counts) return 0
    return Math.round((batch.request_counts.completed / batch.request_counts.total) * 100)
  }

  return (
    <div className="batch-status-monitor">
      <div className="monitor-header">
        <h3>🔄 Stato Batch Jobs</h3>
        <button 
          className="refresh-btn"
          onClick={fetchBatches}
          disabled={loading}
        >
          {loading ? '⏳' : '🔄'} Aggiorna
        </button>
      </div>

      {error && (
        <div className="error-message">
          ❌ Errore: {error}
        </div>
      )}

      {batches.length === 0 && !loading ? (
        <div className="no-batches">
          <div className="no-batches-icon">📋</div>
          <p>Nessun batch job trovato</p>
        </div>
      ) : (
        <div className="batches-list">
          {batches.map((batch) => (
            <div key={batch._id} className="batch-item">
              <div className="batch-header">
                <div className="batch-info">
                  <div className="batch-id">
                    Batch {batch._id.slice(0, 8)}...
                  </div>
                  <div className="batch-date">
                    {formatDate(batch.created_at)}
                  </div>
                </div>
                <div className="batch-status">
                  <span className="status-icon">
                    {getStatusIcon(batch.status)}
                  </span>
                  <span 
                    className="status-text"
                    style={{ color: getStatusColor(batch.status) }}
                  >
                    {batch.status}
                  </span>
                </div>
              </div>

              <div className="batch-details">
                <div className="batch-stats">
                  <span>📊 {batch.total_requests} richieste totali</span>
                  {batch.request_counts && (
                    <>
                      <span>✅ {batch.request_counts.completed} completate</span>
                      {batch.request_counts.failed > 0 && (
                        <span>❌ {batch.request_counts.failed} fallite</span>
                      )}
                    </>
                  )}
                </div>

                {batch.request_counts && batch.status === 'in_progress' && (
                  <div className="progress-bar">
                    <div 
                      className="progress-fill"
                      style={{ 
                        width: `${getProgressPercentage(batch)}%`,
                        backgroundColor: getStatusColor('in_progress')
                      }}
                    />
                    <span className="progress-text">
                      {getProgressPercentage(batch)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
