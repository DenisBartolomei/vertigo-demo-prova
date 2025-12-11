import { useEffect, useState, useMemo } from 'react'
import { BarChart3, TrendingUp, Info, AlertCircle, Loader2 } from 'lucide-react'
import { Card, CardHeader, CardBody } from '../components/ui/Card'
import { Skeleton } from '../components/ui/Skeleton'
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from 'recharts'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'

interface Position {
  _id: string
  position_name: string
}

interface BenchmarkData {
  position_id: string
  position_name: string
  market_json: Record<string, number>
  market_skills_list: string[]
  chart_cat_base64?: string  // Grafico Sunburst in base64
  created_at?: string
  updated_at?: string
}

// Colori per il grafico (gradiente viola/rosa)
const CHART_COLORS = [
  '#7C3AED', '#8B5CF6', '#A78BFA', '#C4B5FD', '#DDD6FE',
  '#EDE9FE', '#F3E8FF', '#FAE8FF', '#FCE7F3', '#FDF2F8'
]

// Componente semplificato per visualizzare le categorie
function SimpleCategoryList({ data }: { data: Record<string, number> }) {
  const organizedData = useMemo(() => {
    const entries = Object.entries(data)
      .filter(([_, value]) => value > 0)
      .sort(([_, a], [__, b]) => b - a)
      .slice(0, 10)
    
    const top3 = entries.slice(0, 3)
    const middle4 = entries.slice(3, 7)
    const bottom3 = entries.slice(7, 10)
    
    return { top3, middle4, bottom3 }
  }, [data])

  const { top3, middle4, bottom3 } = organizedData

  const CategorySection = ({ 
    title, 
    items, 
    color 
  }: { 
    title: string
    items: [string, number][]
    color: string
  }) => {
    if (items.length === 0) return null
    
    return (
      <div style={{ marginBottom: '32px' }}>
        <h3 style={{
          fontSize: '14px',
          fontWeight: '600',
          color: color,
          marginBottom: '12px',
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          {title}
        </h3>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}>
          {items.map(([name, value], idx) => (
            <div
              key={`${title}-${idx}`}
              style={{
                padding: '12px 16px',
                background: '#F9FAFB',
                border: `1px solid ${color}20`,
                borderRadius: '6px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#F3F4F6'
                e.currentTarget.style.borderColor = `${color}40`
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#F9FAFB'
                e.currentTarget.style.borderColor = `${color}20`
              }}
            >
              <span style={{
                fontSize: '14px',
                color: 'var(--text-primary)',
                fontWeight: '500'
              }}>
                {name}
              </span>
              <span style={{
                fontSize: '13px',
                color: 'var(--text-secondary)',
                fontWeight: '400'
              }}>
                {value.toLocaleString('it-IT')}
              </span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: '24px', background: 'white', borderRadius: '8px' }}>
      <CategorySection 
        title="Ruoli Rilevanti" 
        items={top3} 
        color="#7C3AED" 
      />
      <CategorySection 
        title="Ruoli Comuni" 
        items={middle4} 
        color="#A78BFA" 
      />
      <CategorySection 
        title="Ruoli a Basso Impatto" 
        items={bottom3} 
        color="#C4B5FD" 
      />
    </div>
  )
}

export function Benchmark() {
  const [positions, setPositions] = useState<Position[]>([])
  const [selectedPositionId, setSelectedPositionId] = useState<string>('')
  const [benchmarkData, setBenchmarkData] = useState<BenchmarkData | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingPositions, setLoadingPositions] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const token = localStorage.getItem('hr_jwt')

  useEffect(() => {
    loadPositions()
  }, [])

  useEffect(() => {
    if (selectedPositionId) {
      loadBenchmarkData(selectedPositionId)
    } else {
      setBenchmarkData(null)
    }
  }, [selectedPositionId])

  async function loadPositions() {
    setLoadingPositions(true)
    try {
      const resp = await fetch(`${API_BASE}/positions`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (resp.ok) {
        const data = await resp.json()
        setPositions(data.positions || [])
      }
    } catch (err) {
      console.error('Error loading positions:', err)
    } finally {
      setLoadingPositions(false)
    }
  }

  async function loadBenchmarkData(positionId: string) {
    setLoading(true)
    setError(null)
    try {
      const resp = await fetch(`${API_BASE}/positions/${positionId}/benchmark`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (resp.status === 404) {
        setError('Benchmark non disponibile per questa posizione. Esegui prima la data preparation.')
        setBenchmarkData(null)
        return
      }
      
      if (!resp.ok) {
        throw new Error('Errore nel caricamento dei dati di benchmark')
      }
      
      const data = await resp.json()
      console.log('Benchmark data received:', {
        hasChart: !!data.chart_cat_base64,
        chartLength: data.chart_cat_base64?.length || 0,
        marketJsonKeys: Object.keys(data.market_json || {}).length
      })
      setBenchmarkData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore sconosciuto')
      setBenchmarkData(null)
    } finally {
      setLoading(false)
    }
  }

  // Converti market_json in array per il grafico a barre
  const marketJsonArray = benchmarkData?.market_json
    ? Object.entries(benchmarkData.market_json)
        .map(([category, value]) => ({
          name: category,
          value: typeof value === 'number' ? value : parseFloat(String(value)) || 0
        }))
        .filter(item => item.value > 0) // Filtra valori zero
        .sort((a, b) => b.value - a.value)
        .slice(0, 15)
    : []

  return (
    <div className="container" style={{ display: 'grid', gap: '32px', position: 'relative' }}>
      <div>
        <h2>Benchmark di Mercato</h2>
        <p className="muted">Analizza le categorie professionali e le competenze più richieste nel mercato</p>
      </div>

      {/* Selettore Posizione */}
      <Card>
        <CardBody>
          <label style={{
            display: 'block',
            fontSize: '14px',
            fontWeight: '600',
            color: 'var(--text-primary)',
            marginBottom: '8px'
          }}>
            Seleziona Posizione
          </label>
          {loadingPositions ? (
            <Skeleton width="100%" height="40px" />
          ) : (
            <select
              value={selectedPositionId}
              onChange={(e) => setSelectedPositionId(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 16px',
                fontSize: '16px',
                border: '1px solid var(--border-light)',
                borderRadius: '8px',
                background: 'white',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = '#7C3AED'
                e.currentTarget.style.boxShadow = '0 0 0 3px rgba(124, 58, 237, 0.1)'
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-light)'
                e.currentTarget.style.boxShadow = 'none'
              }}
            >
              <option value="">-- Seleziona una posizione --</option>
              {positions.map(pos => (
                <option key={pos._id} value={pos._id}>
                  {pos.position_name}
                </option>
              ))}
            </select>
          )}
        </CardBody>
      </Card>

      {/* Loading State */}
      {loading && (
        <Card>
          <CardBody>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '48px',
              gap: '12px',
              color: 'var(--text-secondary)'
            }}>
              <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
              <span>Caricamento dati di benchmark...</span>
              <style>{`
                @keyframes spin {
                  to { transform: rotate(360deg); }
                }
              `}</style>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Error State */}
      {error && !loading && (
        <Card>
          <CardBody>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '24px',
              background: '#FEF2F2',
              borderRadius: '8px',
              border: '1px solid #FEE2E2',
              color: '#991B1B'
            }}>
              <AlertCircle size={24} />
              <div>
                <div style={{ fontWeight: '600', marginBottom: '4px' }}>Errore</div>
                <div style={{ fontSize: '14px' }}>{error}</div>
              </div>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Benchmark Data */}
      {benchmarkData && !loading && !error && (
        <>
          {/* Info Card */}
          <Card style={{ marginBottom: '24px', background: 'linear-gradient(135deg, #F5F3FF 0%, #FCE7F3 100%)' }}>
            <CardBody>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <Info size={20} color="#7C3AED" />
                <div style={{ fontSize: '14px', color: 'var(--text-primary)' }}>
                  <strong>Posizione:</strong> {benchmarkData.position_name}
                  {benchmarkData.updated_at && (
                    <span style={{ marginLeft: '16px', color: 'var(--text-secondary)' }}>
                      Aggiornato: {new Date(benchmarkData.updated_at).toLocaleDateString('it-IT')}
                    </span>
                  )}
                </div>
              </div>
            </CardBody>
          </Card>

          {/* Market JSON - Categorie Professionali */}
          <Card style={{ marginBottom: '24px' }}>
            <CardHeader>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <TrendingUp size={20} color="#7C3AED" />
                <h2 style={{
                  fontSize: '20px',
                  fontWeight: '600',
                  color: 'var(--text-primary)',
                  margin: 0
                }}>
                  Categorie Professionali nel Mercato secondo notazione ESCO
                </h2>
              </div>
            </CardHeader>
            <CardBody>
              <p style={{
                fontSize: '14px',
                color: 'var(--text-secondary)',
                marginBottom: '24px',
                lineHeight: '1.6'
              }}>
                Rappresenta la distribuzione delle categorie professionali nel mercato del lavoro per questa posizione, basata su un'analisi di candidati benchmark.
              </p>
              
              {benchmarkData.market_json && Object.keys(benchmarkData.market_json).length > 0 ? (
                <SimpleCategoryList data={benchmarkData.market_json} />
              ) : marketJsonArray.length > 0 ? (
                // Fallback al grafico a barre se il Sunburst non è disponibile (cache vecchia)
                <div>
                  <div style={{
                    padding: '12px 16px',
                    marginBottom: '16px',
                    background: '#FEF3C7',
                    border: '1px solid #FCD34D',
                    borderRadius: '8px',
                    color: '#92400E',
                    fontSize: '14px'
                  }}>
                    ⚠️ Grafico Sunburst non disponibile. Esegui di nuovo la data preparation per vedere il nuovo grafico.
                  </div>
                  <div style={{ height: `${Math.max(marketJsonArray.length * 50, 400)}px`, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={marketJsonArray}
                        layout="vertical"
                        margin={{ top: 20, right: 30, left: 300, bottom: 20 }}
                      >
                        <XAxis type="number" hide />
                        <YAxis 
                          type="category" 
                          dataKey="name" 
                          width={280}
                          tick={{ 
                            fontSize: 14, 
                            fill: 'var(--text-primary)',
                            fontWeight: '500',
                            textAnchor: 'end'
                          }}
                          tickLine={false}
                          axisLine={false}
                          interval={0}
                        />
                        <Tooltip 
                          formatter={(value: number) => value.toLocaleString('it-IT')}
                          contentStyle={{
                            background: 'white',
                            border: '1px solid #E5E7EB',
                            borderRadius: '8px',
                            padding: '8px',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                          }}
                        />
                        <Bar 
                          dataKey="value" 
                          radius={[0, 8, 8, 0]}
                          label={false}
                        >
                          {marketJsonArray.map((entry, index) => (
                            <Cell 
                              key={`cell-${index}`} 
                              fill={CHART_COLORS[index % CHART_COLORS.length]} 
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ) : (
                <div style={{
                  padding: '48px',
                  textAlign: 'center',
                  color: 'var(--text-secondary)'
                }}>
                  Nessun dato disponibile per le categorie professionali
                </div>
              )}
            </CardBody>
          </Card>

          {/* Market Skills List */}
          <Card>
            <CardHeader>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <BarChart3 size={20} color="#7C3AED" />
                <h2 style={{
                  fontSize: '20px',
                  fontWeight: '600',
                  color: 'var(--text-primary)',
                  margin: 0
                }}>
                  Competenze più Richieste secondo notazione ESCO
                </h2>
              </div>
            </CardHeader>
            <CardBody>
              <p style={{
                fontSize: '14px',
                color: 'var(--text-secondary)',
                marginBottom: '24px',
                lineHeight: '1.6'
              }}>
                Le 15 competenze più comuni tra i candidati benchmark per questa posizione. 
                Queste skill rappresentano le capacità tecniche e professionali più frequenti 
                nel pool di candidati analizzati per questo ruolo.
              </p>
              
              {benchmarkData.market_skills_list && benchmarkData.market_skills_list.length > 0 ? (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                  gap: '12px'
                }}>
                  {benchmarkData.market_skills_list.map((skill, index) => (
                    <div
                      key={index}
                      style={{
                        padding: '12px 16px',
                        background: 'linear-gradient(135deg, #F5F3FF 0%, #FCE7F3 100%)',
                        borderRadius: '8px',
                        border: '1px solid rgba(124, 58, 237, 0.2)',
                        fontSize: '14px',
                        fontWeight: '500',
                        color: 'var(--text-primary)',
                        textAlign: 'center',
                        transition: 'all 0.2s ease',
                        cursor: 'default'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translateY(-2px)'
                        e.currentTarget.style.boxShadow = '0 4px 12px rgba(124, 58, 237, 0.15)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)'
                        e.currentTarget.style.boxShadow = 'none'
                      }}
                    >
                      {skill}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{
                  padding: '48px',
                  textAlign: 'center',
                  color: 'var(--text-secondary)'
                }}>
                  Nessuna competenza disponibile
                </div>
              )}
            </CardBody>
          </Card>
        </>
      )}

      {/* Empty State */}
      {!selectedPositionId && !loading && !error && (
        <Card>
          <CardBody>
            <div style={{
              padding: '48px',
              textAlign: 'center',
              color: 'var(--text-secondary)'
            }}>
              <BarChart3 size={48} style={{ marginBottom: '16px', opacity: 0.5 }} />
              <div style={{ fontSize: '16px', fontWeight: '500', marginBottom: '8px' }}>
                Seleziona una posizione per visualizzare i dati di benchmark
              </div>
              <div style={{ fontSize: '14px' }}>
                I dati di benchmark vengono generati durante la fase di data preparation della posizione
              </div>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  )
}

