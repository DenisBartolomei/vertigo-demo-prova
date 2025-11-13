import { useEffect, useState } from 'react'
import { BarChart3, Search, Mail, Clock, FileText, CheckCircle2, AlertTriangle, AlertCircle, Info, Lock, Download, MessageCircle, Target, TrendingUp, RefreshCw, Rocket } from 'lucide-react'
import { SecurityReport } from '../components/SecurityReport'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'

type Row = { 
  session_id: string; 
  candidate_name: string; 
  candidate_email?: string;
  position_id?: string; 
  position_name?: string; 
  status?: string; 
  interview_token?: string;
  downloaded_at?: string;
  downloaded_by?: string;
  downloaded_by_name?: string;
}

function renderStars(rating: number) {
  const stars = []
  for (let i = 1; i <= 4; i++) {
    stars.push(
      <span
        key={i}
        style={{
          fontSize: '14px',
          color: i <= rating ? '#F59E0B' : '#D1D5DB',
          textShadow: i <= rating ? '0 0 1px rgba(245, 158, 11, 0.3)' : 'none'
        }}
      >
        ★
      </span>
    )
  }
  return stars
}

function formatReport(reportText: string, kind: 'cv' | 'case' | 'conversation') {
  if (!reportText) return null
  
  if (kind === 'cv') {
    return formatCVAnalysisReport(reportText)
  } else if (kind === 'case') {
    return formatCaseEvaluationReport(reportText)
  }
  
  return <pre style={{ margin: 0, fontSize: '12px', whiteSpace: 'pre-wrap' }}>{reportText}</pre>
}

function formatCVAnalysisReport(reportText: string) {
  const lines = reportText.split('\n')
  const sections = []
  let currentSection = { title: '', items: [] as string[], type: 'text' }
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (!line) continue
    
    // Detect main sections (numbered like "1. " or "REPORT")
    if (line.match(/^\d+\.?\s+[A-Z]/) || line.includes('Analisi') || line.includes('REPORT')) {
      if (currentSection.title || currentSection.items.length > 0) {
        sections.push({ ...currentSection, items: [...currentSection.items] })
      }
      currentSection = { title: line.replace(/^[\d\.]+\s*/, ''), items: [], type: 'section' }
    } 
    // Detect subsections (numbered like "2.1 ")
    else if (line.match(/^\d+\.\d+\.?\s+/) || (line.includes('Verifica') && line.includes('/'))) {
      if (currentSection.title || currentSection.items.length > 0) {
        sections.push({ ...currentSection, items: [...currentSection.items] })
      }
      currentSection = { title: line.replace(/^[\d\.]+\s*/, ''), items: [], type: 'subsection' }
    } 
    // Detect bullet points
    else if (line.match(/^[-•o]\s+/)) {
      currentSection.items.push(line.replace(/^[-•o]\s+/, ''))
    }
    // Detect header text (like "Requisiti tecnici richiesti:")
    else if (line.endsWith(':')) {
      if (currentSection.title || currentSection.items.length > 0) {
        sections.push({ ...currentSection, items: [...currentSection.items] })
      }
      currentSection = { title: line, items: [], type: 'header' }
    }
    // Regular text content
    else {
      currentSection.items.push(line)
    }
  }
  
  if (currentSection.title || currentSection.items.length > 0) {
    sections.push(currentSection)
  }
  
  // Helper function to highlight important keywords
  const highlightKeywords = (text: string) => {
    const keywords = [
      'soddisfatto', 'non soddisfatto', 'pienamente', 'requisito', 
      'esperienza', 'competenze', 'certificazioni', 'laurea',
      'ben documentate', 'non menzionata', 'non esplicita', 'assente'
    ]
    
    let highlighted = text
    keywords.forEach(keyword => {
      const regex = new RegExp(`(${keyword})`, 'gi')
      if (keyword.includes('non') || keyword === 'assente') {
        highlighted = highlighted.replace(regex, '<strong style="color: #ef4444">$1</strong>')
      } else if (keyword.includes('soddisfatto') || keyword === 'pienamente' || keyword.includes('ben')) {
        highlighted = highlighted.replace(regex, '<strong style="color: #10b981">$1</strong>')
      } else {
        highlighted = highlighted.replace(regex, '<strong>$1</strong>')
      }
    })
    return highlighted
  }
  
  return (
    <div style={{ lineHeight: '1.8', fontSize: '14px' }}>
      {sections.map((section, index) => (
        <div key={index} style={{ marginBottom: '24px' }}>
          {/* Main Section Header */}
          {section.type === 'section' && (
            <div style={{
              fontSize: '18px',
              fontWeight: '700',
              color: 'var(--primary-purple)',
              marginBottom: '16px',
              paddingBottom: '8px',
              borderBottom: '3px solid var(--primary-purple)',
              background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.05), rgba(167, 139, 250, 0.05))',
              padding: '12px 16px',
              borderRadius: '8px 8px 0 0'
            }}>
              <FileText size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> {section.title}
            </div>
          )}
          
          {/* Subsection Header */}
          {section.type === 'subsection' && (
            <div style={{
              fontSize: '15px',
              fontWeight: '600',
              color: 'var(--text-primary)',
              marginBottom: '12px',
              paddingLeft: '16px',
              paddingTop: '8px',
              paddingBottom: '8px',
              borderLeft: '4px solid var(--accent-purple)',
              background: 'rgba(139, 92, 246, 0.03)',
              borderRadius: '0 6px 6px 0'
            }}>
              📌 {section.title}
            </div>
          )}
          
          {/* Header Text */}
          {section.type === 'header' && (
            <div style={{
              fontSize: '14px',
              fontWeight: '600',
              color: 'var(--text-primary)',
              marginBottom: '10px',
              marginTop: '12px'
            }}>
              {section.title}
            </div>
          )}
          
          {/* Content Items */}
          {section.items.length > 0 && (
            <div style={{
              paddingLeft: section.type === 'section' ? '16px' : section.type === 'subsection' ? '24px' : '0'
            }}>
              {section.items.map((item, itemIndex) => (
                <div 
                  key={itemIndex} 
                  style={{
                    marginBottom: '12px',
                    paddingLeft: '20px',
                    position: 'relative',
                    lineHeight: '1.7',
                    color: 'var(--text-secondary)',
                    wordWrap: 'break-word',
                    overflowWrap: 'break-word'
                  }}
                >
                  <span style={{
                    position: 'absolute',
                    left: '0',
                    top: '2px',
                    color: 'var(--primary-purple)',
                    fontWeight: 'bold',
                    fontSize: '16px'
                  }}>•</span>
                  <span dangerouslySetInnerHTML={{ __html: highlightKeywords(item) }} />
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function formatCaseEvaluationReport(reportText: string) {
  const lines = reportText.split('\n')
  const sections = []
  let currentSection = { title: '', content: '', type: 'text' }
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    
    // Detect main sections
    if (line.includes('Sommario') || line.includes('Summary')) {
      if (currentSection.title) {
        sections.push({ ...currentSection })
      }
      currentSection = { title: line, content: '', type: 'summary' }
    } else if (line.includes('Valutazione') || line.includes('Evaluation') || line.includes('Requisiti') || line.includes('Requirements')) {
      if (currentSection.title) {
        sections.push({ ...currentSection })
      }
      currentSection = { title: line, content: '', type: 'evaluation' }
    } else if (line.match(/^\d+\.?\s+[A-Z]/) || line.includes('Competenza') || line.includes('Skill')) {
      if (currentSection.title) {
        sections.push({ ...currentSection })
      }
      currentSection = { title: line, content: '', type: 'skill' }
    } else if (line.startsWith('•') || line.startsWith('-') || line.startsWith('o')) {
      if (currentSection.title) {
        sections.push({ ...currentSection })
      }
      currentSection = { title: line, content: '', type: 'bullet' }
    } else if (line) {
      currentSection.content += (currentSection.content ? '\n' : '') + line
    }
  }
  
  if (currentSection.title) {
    sections.push(currentSection)
  }
  
  return (
    <div style={{ lineHeight: '1.6' }}>
      {sections.map((section, index) => (
        <div key={index} style={{ marginBottom: '16px' }}>
          {section.type === 'summary' && (
            <div style={{
              background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(167, 139, 250, 0.1))',
              border: '1px solid rgba(139, 92, 246, 0.2)',
              borderRadius: '8px',
              padding: '16px',
              marginBottom: '16px'
            }}>
              <div style={{
                fontSize: '16px',
                fontWeight: '700',
                color: 'var(--primary-purple)',
                marginBottom: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <BarChart3 size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> {section.title}
              </div>
              <div style={{
                fontSize: '13px',
                color: 'var(--text-primary)',
                lineHeight: '1.5'
              }}>
                {section.content.split('\n').map((paragraph, pIndex) => (
                  <div key={pIndex} style={{ marginBottom: '8px' }}>
                    {paragraph}
                  </div>
                ))}
              </div>
            </div>
          )}
          {section.type === 'evaluation' && (
            <div>
              <div style={{
                fontSize: '16px',
                fontWeight: '700',
                color: 'var(--primary-purple)',
                marginBottom: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                🎯 {section.title}
              </div>
              <div style={{
                fontSize: '13px',
                color: 'var(--text-primary)',
                lineHeight: '1.5'
              }}>
                {section.content.split('\n').map((paragraph, pIndex) => (
                  <div key={pIndex} style={{ marginBottom: '8px' }}>
                    {paragraph}
                  </div>
                ))}
              </div>
            </div>
          )}
          {section.type === 'skill' && (
            <div style={{
              background: 'rgba(255, 255, 255, 0.7)',
              border: '1px solid var(--border-light)',
              borderRadius: '6px',
              padding: '12px',
              marginBottom: '8px'
            }}>
              <div style={{
                fontSize: '14px',
                fontWeight: '600',
                color: 'var(--text-primary)',
                marginBottom: '6px'
              }}>
                🎯 {section.title}
              </div>
              <div style={{
                fontSize: '13px',
                color: 'var(--text-secondary)',
                lineHeight: '1.4'
              }}>
                {section.content}
              </div>
            </div>
          )}
          {section.type === 'bullet' && (
            <div style={{
              fontSize: '13px',
              color: 'var(--text-primary)',
              marginBottom: '4px',
              paddingLeft: '16px',
              position: 'relative'
            }}>
              <span style={{
                position: 'absolute',
                left: '0',
                color: 'var(--primary-purple)',
                fontWeight: 'bold'
              }}>•</span>
              {section.title}
            </div>
          )}
          {section.content && section.type === 'text' && (
            <div style={{
              fontSize: '13px',
              color: 'var(--text-secondary)',
              lineHeight: '1.5'
            }}>
              {section.content.split('\n').map((paragraph, pIndex) => (
                <div key={pIndex} style={{ marginBottom: '8px' }}>
                  {paragraph}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export function Candidati() {
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [skills, setSkills] = useState<Record<string, any[]>>({})
  const [reportKind, setReportKind] = useState<Record<string, 'cv' | 'case' | 'conversation'>>({})
  const [reportText, setReportText] = useState<Record<string, string>>({})
  const [conversationData, setConversationData] = useState<Record<string, any[]>>({})
  const [selectedPosition, setSelectedPosition] = useState<string>('')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc' | 'none'>('none')
  const [overallMeans, setOverallMeans] = useState<Record<string, number>>({})
  const [reportExpanded, setReportExpanded] = useState<Record<string, boolean>>({})
  const [securityReports, setSecurityReports] = useState<Record<string, any>>({})
  const [showSecurityReport, setShowSecurityReport] = useState<string | null>(null)
  const [expandedSkills, setExpandedSkills] = useState<Record<string, Set<number>>>({})
  const token = localStorage.getItem('hr_jwt')

  // Toggle skill expansion
  const toggleSkillExpansion = (sessionId: string, skillIndex: number) => {
    setExpandedSkills(prev => {
      const sessionSkills = prev[sessionId] || new Set<number>()
      const newSet = new Set(sessionSkills)
      
      if (newSet.has(skillIndex)) {
        newSet.delete(skillIndex)
      } else {
        newSet.add(skillIndex)
      }
      
      return {
        ...prev,
        [sessionId]: newSet
      }
    })
  }

  // Check if skill is expanded
  const isSkillExpanded = (sessionId: string, skillIndex: number): boolean => {
    return expandedSkills[sessionId]?.has(skillIndex) || false
  }

  async function load() {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/sessions/completed`, { headers: { Authorization: `Bearer ${token}` } })
      if (res.status === 401) {
        // Token expired, redirect to login
        localStorage.removeItem('hr_jwt')
        window.location.href = '/login'
        return
      }
      if (res.ok) {
        const data = await res.json()
        setRows(data.items || [])
        
        // Load security reports and overall means for all sessions
        await loadSecurityReportsAndMeans(data.items || [])
      } else {
        console.error('Failed to load candidates:', res.statusText)
      }
    } catch (error) {
      console.error('Error loading candidates:', error)
    } finally {
      setLoading(false)
    }
  }

  async function loadSecurityReportsAndMeans(sessions: Row[]) {
    const securityReports: Record<string, any> = {}
    const overallMeans: Record<string, number> = {}
    
    // Load data for all sessions in parallel
    const promises = sessions.map(async (session) => {
      const sessionId = session.session_id
      
      // Load security report
      try {
        const securityRes = await fetch(`${API_BASE}/sessions/${sessionId}/security-report`, { 
          headers: { Authorization: `Bearer ${token}` } 
        })
        if (securityRes.ok) {
          const securityData = await securityRes.json()
          securityReports[sessionId] = securityData
        }
      } catch (error) {
        console.error(`Error loading security report for ${sessionId}:`, error)
      }
      
      // Load skills and calculate overall mean
      try {
        const skillsRes = await fetch(`${API_BASE}/sessions/${sessionId}/skills_scaled`, { 
          headers: { Authorization: `Bearer ${token}` } 
        })
        if (skillsRes.ok) {
          const skillsData = await skillsRes.json()
          const skillList = skillsData.items || []
          const mean = calculateOverallMean(skillList)
          if (mean > 0) {
            overallMeans[sessionId] = mean
          }
        }
      } catch (error) {
        console.error(`Error loading skills for ${sessionId}:`, error)
      }
    })
    
    await Promise.all(promises)
    
    // Update state with loaded data
    setSecurityReports(securityReports)
    setOverallMeans(overallMeans)
  }


  useEffect(() => { load() }, [])

  function calculateOverallMean(skillList: any[]): number {
    if (skillList.length === 0) return 0
    const cvMean = skillList.reduce((sum: number, s: any) => sum + (s.cv_0_4 || 0), 0) / skillList.length
    const interviewMean = skillList.reduce((sum: number, s: any) => sum + (s.interview_0_4 || 0), 0) / skillList.length
    return (cvMean + interviewMean) / 2
  }

  async function toggle(id: string) {
    setExpanded(prev => (prev === id ? null : id))
    if (!skills[id]) {
      const r = await fetch(`${API_BASE}/sessions/${id}/skills_scaled`, { headers: { Authorization: `Bearer ${token}` } })
      if (r.ok) {
        const d = await r.json()
        const skillList = d.items || []
        setSkills(prev => ({ ...prev, [id]: skillList }))
        // Calculate and store overall mean for this candidate
        const mean = calculateOverallMean(skillList)
        setOverallMeans(prev => ({ ...prev, [id]: mean }))
      }
    }
  }

  async function fetchReport(id: string, kind: 'cv' | 'case' | 'conversation') {
    setReportKind(prev => ({ ...prev, [id]: kind }))
    
    if (kind === 'conversation') {
      const r = await fetch(`${API_BASE}/sessions/${id}/conversation`, { headers: { Authorization: `Bearer ${token}` } })
      if (r.ok) {
        const d = await r.json()
        setConversationData(prev => ({ ...prev, [id]: d.conversation || [] }))
        setReportText(prev => ({ ...prev, [id]: '' })) // Clear report text for conversation
      } else {
        setConversationData(prev => ({ ...prev, [id]: [] }))
        setReportText(prev => ({ ...prev, [id]: 'Conversation not available' }))
      }
    } else {
      const r = await fetch(`${API_BASE}/sessions/${id}/report/${kind}`, { headers: { Authorization: `Bearer ${token}` } })
      if (r.ok) {
        const d = await r.json()
        const text = typeof d.report === 'string' ? d.report : JSON.stringify(d.report, null, 2)
        setReportText(prev => ({ ...prev, [id]: text }))
        setConversationData(prev => ({ ...prev, [id]: [] })) // Clear conversation data for reports
      } else {
        setReportText(prev => ({ ...prev, [id]: 'Report not available' }))
      }
    }
  }


  async function downloadFeedback(id: string) {
    try {
      const r = await fetch(`${API_BASE}/sessions/${id}/feedback-pdf`, { 
        headers: { Authorization: `Bearer ${token}` } 
      })
      if (r.ok) {
        const blob = await r.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `Report_Feedback_${id}.pdf`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        
        // Refresh the data to show download tracking
        load()
      } else {
        alert('Errore nel download del feedback')
      }
    } catch (error) {
      alert('Errore nel download del feedback')
    }
  }

  async function loadSecurityReport(id: string) {
    try {
      const response = await fetch(`${API_BASE}/sessions/${id}/security-report`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (response.ok) {
        const data = await response.json()
        setSecurityReports(prev => ({ ...prev, [id]: data }))
      } else {
        console.error('Failed to load security report')
      }
    } catch (error) {
      console.error('Error loading security report:', error)
    }
  }

  async function handleGenerateFeedback(id: string) {
      // Salva lo stato precedente in caso di errore
      const originalRows = [...rows];
      const originalStatus = rows.find(row => row.session_id === id)?.status;

      // Aggiornamento ottimistico dell'UI
      setRows(prevRows => prevRows.map(row => 
          row.session_id === id ? { ...row, status: 'Generazione feedback in corso...' } : row
      ));

      try {
          const res = await fetch(`${API_BASE}/sessions/${id}/generate-feedback`, {
              method: 'POST',
              headers: { Authorization: `Bearer ${token}` }
          });

          if (res.ok) {
              const data = await res.json();
              // L'UI è già in "corso...", il backend si occuperà di aggiornare lo stato finale.
              // Possiamo aggiornare l'UI con lo stato restituito per coerenza.
              setRows(prevRows => prevRows.map(row => 
                  row.session_id === id ? { ...row, status: data.status || 'Generazione feedback in corso...' } : row
              ));
              // Potresti voler avviare un polling o attendere un WebSocket per l'aggiornamento finale,
              // ma per ora lasciare che l'utente aggiorni manualmente la pagina è accettabile.
          } else {
              // GESTIONE ERRORE MIGLIORATA
              const errorDetails = await res.text();
              console.error(`ERRORE DAL SERVER (Status: ${res.status}):`, errorDetails);
              alert(`Errore dal server (Status: ${res.status}):\n\n${errorDetails}`);
              
              // Ripristina lo stato solo per la riga fallita, invece di ricaricare tutto
              setRows(prevRows => prevRows.map(row =>
                row.session_id === id ? { ...row, status: originalStatus || 'Errore generazione feedback' } : row
              ));
          }
      } catch (error) {
          console.error('Error generating feedback:', error);
          alert('Errore di rete durante la generazione del feedback.');
          
          // Ripristina lo stato originale in caso di errore di rete
          setRows(originalRows);
      }
  }

  function getSecurityRiskLevel(securityReport: any): { level: string; color: string; IconComponent: React.ComponentType<{ size?: number }> } {
    if (!securityReport) {
      return { level: 'Unknown', color: '#6c757d', IconComponent: Info }
    }
    
    const riskLevel = securityReport.risk_assessment?.level || 'MINIMAL'
    const color = securityReport.risk_assessment?.color || '#6c757d'
    
    let IconComponent = CheckCircle2
    if (riskLevel === 'HIGH') IconComponent = AlertTriangle
    else if (riskLevel === 'MEDIUM') IconComponent = AlertCircle
    else if (riskLevel === 'LOW') IconComponent = Info
    
    return { level: riskLevel, color, IconComponent }
  }


  // Get unique positions for filter dropdown
  const uniquePositions = Array.from(new Set(rows.map(r => r.position_name || r.position_id).filter(Boolean)))
  
  // Filter and sort rows
  const filteredAndSortedRows = rows
    .filter(row => !selectedPosition || row.position_name === selectedPosition || row.position_id === selectedPosition)
    .sort((a, b) => {
      if (sortOrder === 'none') return 0
      const meanA = overallMeans[a.session_id] || 0
      const meanB = overallMeans[b.session_id] || 0
      return sortOrder === 'desc' ? meanB - meanA : meanA - meanB
    })

  return (
    <div className="container" style={{ display: 'grid', gap: 16 }}>
      <div>
        <h2>Reportistica Candidati</h2>
        <p className="muted">Visualizza i report completi dei candidati che hanno terminato l'intero processo di selezione, inclusi colloquio, valutazione delle competenze, analisi finale e report di sicurezza.</p>
      </div>
      
      {/* Filter Section */}
      <div className="card" style={{ 
        background: 'linear-gradient(135deg, var(--light-purple), var(--pastel-pink))',
        border: '1px solid rgba(139, 92, 246, 0.2)',
        padding: '16px'
      }}>
        <h4 style={{ 
          margin: '0 0 12px 0', 
          color: 'var(--text-primary)',
          fontSize: '16px',
          fontWeight: '600'
        }}>
          <Search size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> Filtri e Ordinamento
        </h4>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: '1fr 1fr auto', 
          gap: '12px', 
          alignItems: 'end' 
        }}>
          <div>
            <label style={{ 
              display: 'block', 
              fontSize: '12px', 
              fontWeight: '600', 
              color: 'var(--text-secondary)',
              marginBottom: '4px'
            }}>
              Posizione Lavorativa
            </label>
            <select 
              value={selectedPosition} 
              onChange={e => setSelectedPosition(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-light)',
                background: 'white',
                fontSize: '14px'
              }}
            >
              <option value="">Tutte le posizioni</option>
              {uniquePositions.map(position => (
                <option key={position} value={position}>{position}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label style={{ 
              display: 'block', 
              fontSize: '12px', 
              fontWeight: '600', 
              color: 'var(--text-secondary)',
              marginBottom: '4px'
            }}>
              Ordina per Media Generale
            </label>
            <select 
              value={sortOrder} 
              onChange={e => setSortOrder(e.target.value as 'asc' | 'desc' | 'none')}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-light)',
                background: 'white',
                fontSize: '14px'
              }}
            >
              <option value="none">Nessun ordinamento</option>
              <option value="desc">Media più alta → più bassa</option>
              <option value="asc">Media più bassa → più alta</option>
            </select>
          </div>
          
          <div style={{ 
            display: 'flex', 
            gap: '8px',
            alignItems: 'center'
          }}>
            <button 
              onClick={() => {
                setSelectedPosition('')
                setSortOrder('none')
              }}
              style={{
                padding: '8px 12px',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-light)',
                borderRadius: 'var(--radius-md)',
                fontSize: '12px',
                cursor: 'pointer',
                color: 'var(--text-secondary)'
              }}
            >
              <RefreshCw size={14} style={{ marginRight: '4px', verticalAlign: 'middle' }} /> Reset
            </button>
            <div style={{ 
              fontSize: '11px', 
              color: 'var(--text-secondary)',
              textAlign: 'center'
            }}>
              {filteredAndSortedRows.length} candidati
            </div>
          </div>
        </div>
      </div>
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
          <Clock size={24} color="#9CA3AF" style={{ marginBottom: '8px' }} />
          <div style={{ marginTop: '8px' }}>Caricamento report...</div>
        </div>
      ) : rows.length === 0 ? (
        <div style={{ 
          textAlign: 'center', 
          padding: '40px', 
          color: 'var(--text-muted)',
          background: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-lg)'
        }}>
          <BarChart3 size={48} color="#9CA3AF" style={{ marginBottom: '16px' }} />
          <div style={{ fontSize: '18px', marginBottom: '8px' }}>Nessun report disponibile</div>
          <div>I report appariranno qui quando i candidati completeranno l'intero processo di selezione</div>
        </div>
      ) : filteredAndSortedRows.length === 0 ? (
        <div style={{ 
          textAlign: 'center', 
          padding: '40px', 
          color: 'var(--text-muted)',
          background: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-lg)'
        }}>
          <Search size={48} color="#9CA3AF" style={{ marginBottom: '16px' }} />
          <div style={{ fontSize: '18px', marginBottom: '8px' }}>Nessun candidato trovato</div>
          <div>Prova a modificare i filtri per vedere più risultati</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 12 }}>
          {filteredAndSortedRows.map((r) => {
            const isExpanded = expanded === r.session_id
            console.log(`Candidato: ${r.candidate_name}, Stato ricevuto: '${r.status}'`);
            const currentKind = reportKind[r.session_id] || 'cv'
            return (
              <div key={r.session_id} className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <strong>{r.candidate_name || '—'}</strong>
                      
                      {/* Overall Average Score - Always visible */}
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center',
                        gap: '4px',
                        padding: '2px 6px',
                        borderRadius: '8px',
                        background: overallMeans[r.session_id] !== undefined ? 'rgba(139, 92, 246, 0.1)' : 'rgba(156, 163, 175, 0.1)',
                        border: overallMeans[r.session_id] !== undefined ? '1px solid rgba(139, 92, 246, 0.2)' : '1px solid rgba(156, 163, 175, 0.2)',
                        fontSize: '11px',
                        fontWeight: '600',
                        color: overallMeans[r.session_id] !== undefined ? 'var(--primary-purple)' : '#9CA3AF'
                      }}>
                        <BarChart3 size={14} />
                        <span>
                          {overallMeans[r.session_id] !== undefined 
                            ? `${overallMeans[r.session_id].toFixed(1)}/4` 
                            : 'N/A'
                          }
                        </span>
                      </div>
                      
                      {/* Security Risk Indicator - Always visible */}
                      {(() => {
                        const securityReport = securityReports[r.session_id]
                        const riskInfo = getSecurityRiskLevel(securityReport)
                        return (
                          <div style={{ 
                            display: 'flex', 
                            alignItems: 'center',
                            gap: '4px',
                            padding: '2px 6px',
                            borderRadius: '8px',
                            background: riskInfo.color === '#dc3545' ? 'rgba(220, 53, 69, 0.1)' :
                                       riskInfo.color === '#ffc107' ? 'rgba(255, 193, 7, 0.1)' :
                                       riskInfo.color === '#28a745' ? 'rgba(40, 167, 69, 0.1)' :
                                       'rgba(156, 163, 175, 0.1)',
                            border: `1px solid ${riskInfo.color === '#dc3545' ? 'rgba(220, 53, 69, 0.2)' :
                                           riskInfo.color === '#ffc107' ? 'rgba(255, 193, 7, 0.2)' :
                                           riskInfo.color === '#28a745' ? 'rgba(40, 167, 69, 0.2)' :
                                           'rgba(156, 163, 175, 0.2)'}`,
                            fontSize: '11px',
                            fontWeight: '600',
                            color: riskInfo.color === '#dc3545' ? '#DC3545' :
                                   riskInfo.color === '#ffc107' ? '#FFC107' :
                                   riskInfo.color === '#28a745' ? '#28A745' :
                                   '#9CA3AF'
                          }}>
                            {(() => {
                              const Icon = riskInfo.IconComponent
                              return <Icon size={14} />
                            })()}
                            <span>{riskInfo.level}</span>
                          </div>
                        )
                      })()}
                    </div>
                    <div style={{ color: '#666' }}>{r.position_name || r.position_id || '—'}</div>
                    {r.candidate_email && (
                      <div style={{ 
                        color: '#666', 
                        fontSize: '12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        marginTop: '2px'
                      }}>
                        <Mail size={14} />
                        <span>{r.candidate_email}</span>
                      </div>
                    )}
                    {r.status && (
                      <div style={{ 
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: '500',
                        marginTop: '4px',
                        background: r.status === 'Feedback pronto' ? '#D1FAE5' : 
                                    r.status === 'Pronto per generare feedback' ? '#FEF3C7' :
                                    r.status === 'Colloquio completato' ? '#DBEAFE' :
                                    r.status === 'Errore generazione feedback' ? '#FEE2E2' : '#F3F4F6',
                        color: r.status === 'Feedback pronto' ? '#065F46' :
                               r.status === 'Pronto per generare feedback' ? '#92400E' :
                               r.status === 'Colloquio completato' ? '#1E40AF' :
                               r.status === 'Errore generazione feedback' ? '#991B1B' : '#374151'
                      }}>
                        {r.status}
                      </div>
                    )}
                    {/* Security Report Button */}
                    <div style={{
                      display: 'inline-block',
                      marginLeft: '8px',
                      marginTop: '4px'
                    }}>
                      <button
                        onClick={() => {
                          const securityReport = securityReports[r.session_id]
                          if (!securityReport) {
                            loadSecurityReport(r.session_id)
                          }
                          setShowSecurityReport(r.session_id)
                        }}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          padding: '4px 8px',
                          borderRadius: '12px',
                          fontSize: '12px',
                          fontWeight: '500',
                          border: '1px solid #6c757d',
                          background: '#f8f9fa',
                          color: '#6c757d',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease'
                        }}
                        onMouseOver={(e) => {
                          e.currentTarget.style.transform = 'scale(1.05)'
                        }}
                        onMouseOut={(e) => {
                          e.currentTarget.style.transform = 'scale(1)'
                        }}
                      >
                        <Lock size={14} />
                        <span>Report Sicurezza</span>
                        {securityReports[r.session_id]?.security_summary?.total_events > 0 && (
                          <span style={{
                            backgroundColor: '#6c757d',
                            color: 'white',
                            borderRadius: '50%',
                            width: '16px',
                            height: '16px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '10px',
                            fontWeight: '600'
                          }}>
                            {securityReports[r.session_id].security_summary.total_events}
                          </span>
                        )}
                      </button>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <select 
                      value={currentKind} 
                      onChange={e => fetchReport(r.session_id, e.target.value as 'cv' | 'case' | 'conversation')}
                      style={{
                        width: '240px',
                        padding: '6px 8px',
                        fontSize: '12px',
                        fontWeight: '500',
                        border: '1px solid rgba(139, 92, 246, 0.3)',
                        borderRadius: '6px',
                        background: 'white',
                        color: 'var(--text-primary)',
                        cursor: 'pointer',
                        outline: 'none'
                      }}
                    >
                      <option value="cv">CV ANALYSIS REPORT</option>
                      <option value="case">CASE EVALUATION REPORT</option>
                      <option value="conversation">CONVERSATION</option>
                    </select>
                    <button 
                      onClick={() => toggle(r.session_id)}
                      style={{
                        width: '70px',
                        height: '60px',
                        padding: '8px 6px',
                        fontSize: '11px',
                        fontWeight: '600',
                        border: '1px solid rgba(139, 92, 246, 0.3)',
                        borderRadius: '6px',
                        background: 'var(--primary-purple)',
                        color: 'white',
                        cursor: 'pointer',
                        lineHeight: '1.3',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        textAlign: 'center',
                        whiteSpace: 'normal',
                        wordBreak: 'break-word'
                      }}
                    >
                      {isExpanded ? 'Hide skills' : 'Show skills'}
                    </button>
                    
                                
                    {/* --- BLOCCO DI LOGICA RIPRISTINATO DAL VECCHIO FILE --- */}
                                  
                    {/* Stato: Pronto per generare */}
                    {(r.status === 'Evaluation pending' || r.status === 'Feedback pending' || r.status === 'Pronto per generare feedback' || r.status === 'Evaluation completed') && (
                        <button 
                            onClick={() => handleGenerateFeedback(r.session_id)}
                            style={{ 
                              width: '85px',
                              height: '60px',
                              padding: '8px 6px', 
                              background: '#8B5CF6', 
                              color: 'white', 
                              border: 'none', 
                              borderRadius: 'var(--radius-md)', 
                              fontSize: '11px', 
                              fontWeight: '600',
                              cursor: 'pointer', 
                              display: 'flex', 
                              flexDirection: 'column',
                              alignItems: 'center', 
                              justifyContent: 'center',
                              gap: '3px',
                              lineHeight: '1.3',
                              textAlign: 'center'
                            }}
                        >
                            <Rocket size={14} />
                            <span>Genera Feedback</span>
                        </button>
                    )}
                
                    {/* Stato: In elaborazione */}
                    {r.status === 'Generazione feedback in corso...' && (
                        <button 
                            disabled 
                            style={{ 
                              width: '85px',
                              height: '60px',
                              padding: '8px 6px', 
                              background: '#A5B4FC', 
                              color: 'white', 
                              border: 'none', 
                              borderRadius: 'var(--radius-md)', 
                              fontSize: '11px', 
                              fontWeight: '600',
                              cursor: 'not-allowed', 
                              display: 'flex', 
                              flexDirection: 'column',
                              alignItems: 'center', 
                              justifyContent: 'center',
                              gap: '3px',
                              lineHeight: '1.3',
                              textAlign: 'center'
                            }}
                        >
                            <Clock size={14} />
                            <span>In elaborazione</span>
                        </button>
                    )}
                
                    {/* Stato: Pronto per il download */}
                    {(r.status === 'Feedback pronto' || r.status === 'Feedback ready') && (
                        <button 
                            onClick={() => downloadFeedback(r.session_id)}
                            style={{ 
                              width: '85px',
                              height: '60px',
                              padding: '8px 6px', 
                              background: '#10B981', 
                              color: 'white', 
                              border: 'none', 
                              borderRadius: 'var(--radius-md)', 
                              fontSize: '11px', 
                              fontWeight: '600',
                              cursor: 'pointer', 
                              display: 'flex', 
                              flexDirection: 'column',
                              alignItems: 'center', 
                              justifyContent: 'center',
                              gap: '3px',
                              lineHeight: '1.3',
                              textAlign: 'center'
                            }}
                        >
                            <Download size={14} />
                            <span>Download Feedback</span>
                        </button>
                    )}
                
                    {/* Stato: Errore */}
                    {r.status === 'Errore generazione feedback' && (
                        <div style={{ 
                          width: '85px',
                          height: '60px',
                          display: 'flex', 
                          flexDirection: 'column',
                          alignItems: 'center', 
                          justifyContent: 'center',
                          gap: '4px', 
                          background: '#FEE2E2', 
                          padding: '8px 6px', 
                          borderRadius: 'var(--radius-md)',
                          textAlign: 'center'
                        }}>
                            <span style={{ color: '#991B1B', fontSize: '11px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <AlertCircle size={14} /> Errore
                            </span>
                            <button 
                                onClick={() => handleGenerateFeedback(r.session_id)}
                                style={{ fontSize: '10px', padding: '4px 8px', background: '#DC2626', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: '600' }}
                            >
                                Riprova
                            </button>
                        </div>
                    )}
                
                    {/* Info sul download (se già scaricato) */}
                    {r.downloaded_at && (
                      <div style={{ 
                        width: '95px',
                        minHeight: '60px',
                        fontSize: '9px', 
                        fontWeight: '600',
                        color: 'var(--text-secondary)', 
                        background: 'var(--bg-secondary)', 
                        padding: '8px 6px', 
                        borderRadius: '6px', 
                        border: '1px solid var(--border-light)',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        textAlign: 'center',
                        lineHeight: '1.3',
                        gap: '2px'
                      }}>
                        <Download size={12} />
                        <span>Scaricato da</span>
                        <span style={{ fontWeight: '700' }}>{r.downloaded_by_name || r.downloaded_by}</span>
                        <span style={{ fontSize: '8px' }}>il {new Date(r.downloaded_at).toLocaleDateString('it-IT')}</span>
                      </div>
                    )}
                </div>
                </div>
                {/* Report/Conversation Display */}
                {(reportText[r.session_id] || conversationData[r.session_id]) && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      marginBottom: 8
                    }}>
                      <span style={{ 
                        fontSize: '12px', 
                        fontWeight: '600', 
                        color: 'var(--text-secondary)',
                        textTransform: 'uppercase'
                      }}>
                        {currentKind === 'conversation' ? 'Conversation' : 
                         currentKind === 'cv' ? 'CV Analysis Report' : 
                         'Case Evaluation Report'}
                      </span>
                      <button
                        onClick={() => setReportExpanded(prev => ({ ...prev, [r.session_id]: !prev[r.session_id] }))}
                        style={{
                          fontSize: '10px',
                          padding: '2px 6px',
                          background: 'var(--bg-secondary)',
                          border: '1px solid var(--border-light)',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          color: 'var(--text-secondary)'
                        }}
                      >
                        {reportExpanded[r.session_id] ? 'Hide' : 'Show'}
                      </button>
                    </div>
                    
                    {reportExpanded[r.session_id] && (
                      <div style={{ 
                        background: '#fafafa', 
                        borderRadius: 8, 
                        padding: 12,
                        maxHeight: '400px',
                        overflow: 'auto'
                      }}>
                        {currentKind === 'conversation' ? (
                          <div>
                            {(conversationData[r.session_id] || []).map((msg: any, index: number) => (
                              <div key={index} style={{
                                marginBottom: '12px',
                                padding: '8px 12px',
                                borderRadius: '8px',
                                background: msg.role === 'assistant' ? 'white' : 'var(--light-purple)',
                                border: '1px solid var(--border-light)'
                              }}>
                                <div style={{
                                  fontSize: '11px',
                                  fontWeight: '600',
                                  color: 'var(--text-secondary)',
                                  marginBottom: '4px'
                                }}>
                                  {msg.role === 'assistant' ? '🤖 Interviewer' : '👤 Candidate'}
                                </div>
                                <div style={{ fontSize: '13px', lineHeight: '1.4' }}>
                                  {msg.content}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div style={{ fontSize: '13px', lineHeight: '1.5' }}>
                            {formatReport(reportText[r.session_id], currentKind)}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
                {isExpanded && (
                  <div className="card" style={{ 
                    marginTop: 12, 
                    background: 'linear-gradient(135deg, var(--light-purple), var(--pastel-pink))',
                    border: '1px solid rgba(139, 92, 246, 0.2)'
                  }}>
                    {(skills[r.session_id] || []).length > 0 ? (
                      <div>
                        <h4 style={{ 
                          margin: '0 0 16px 0', 
                          color: 'var(--text-primary)',
                          fontSize: '16px',
                          fontWeight: '600'
                        }}>
                          <BarChart3 size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> Valutazione Competenze
                        </h4>
                        <div style={{
                          background: 'rgba(255, 255, 255, 0.9)',
                          borderRadius: 'var(--radius-lg)',
                          padding: '16px',
                          overflow: 'hidden'
                        }}>
                          <div style={{
                            display: 'grid',
                            gridTemplateColumns: '1fr 120px 120px 40px',
                            gap: '12px',
                            padding: '12px 16px',
                            background: 'var(--primary-purple)',
                            color: 'white',
                            fontWeight: '600',
                            fontSize: '14px',
                            borderRadius: 'var(--radius-md)',
                            marginBottom: '12px'
                          }}>
                            <div>Competenza</div>
                            <div style={{ textAlign: 'center' }}>CV</div>
                            <div style={{ textAlign: 'center' }}>Colloquio</div>
                            <div style={{ textAlign: 'center', fontSize: '11px' }}>Info</div>
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {(skills[r.session_id] || []).map((s: any, i: number) => {
                            const isExpanded = isSkillExpanded(r.session_id, i)
                            const hasNotes = s.notes_cv || s.notes_interview
                            
                            return (
                              <div key={i} style={{
                                background: i % 2 === 0 ? 'rgba(255, 255, 255, 0.8)' : 'rgba(255, 255, 255, 0.6)',
                                borderRadius: 'var(--radius-md)',
                                border: '1px solid rgba(139, 92, 246, 0.1)',
                                transition: 'all 0.2s ease',
                                overflow: 'hidden'
                              }}>
                                {/* Compact Header Row */}
                                <div style={{
                                  display: 'grid',
                                  gridTemplateColumns: '1fr 120px 120px 40px',
                                  gap: '12px',
                                  alignItems: 'center',
                                  padding: '12px 16px'
                                }}>
                                  {/* Skill Name */}
                                  <div style={{ 
                                    fontWeight: '600', 
                                    color: 'var(--text-primary)',
                                    fontSize: '14px',
                                    lineHeight: '1.3'
                                  }}>
                                    {s.skill_name}
                                  </div>
                                  
                                  {/* CV Rating */}
                                  <div style={{ 
                                    display: 'flex', 
                                    justifyContent: 'center',
                                    alignItems: 'center',
                                    gap: '2px'
                                  }}>
                                    {renderStars(s.cv_0_4)}
                                  </div>
                                  
                                  {/* Interview Rating */}
                                  <div style={{ 
                                    display: 'flex', 
                                    justifyContent: 'center',
                                    alignItems: 'center',
                                    gap: '2px'
                                  }}>
                                    {renderStars(s.interview_0_4)}
                                  </div>
                                  
                                  {/* Expand/Collapse Button */}
                                  {hasNotes && (
                                    <button
                                      onClick={() => toggleSkillExpansion(r.session_id, i)}
                                      style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        width: '32px',
                                        height: '32px',
                                        border: 'none',
                                        background: isExpanded ? 'rgba(139, 92, 246, 0.1)' : 'transparent',
                                        borderRadius: '6px',
                                        cursor: 'pointer',
                                        fontSize: '16px',
                                        transition: 'all 0.2s ease',
                                        color: 'var(--primary-purple)'
                                      }}
                                      onMouseOver={(e) => {
                                        e.currentTarget.style.background = 'rgba(139, 92, 246, 0.15)'
                                      }}
                                      onMouseOut={(e) => {
                                        e.currentTarget.style.background = isExpanded ? 'rgba(139, 92, 246, 0.1)' : 'transparent'
                                      }}
                                      title={isExpanded ? "Nascondi dettagli" : "Mostra dettagli"}
                                    >
                                      {isExpanded ? '▼' : '▶'}
                                    </button>
                                  )}
                                </div>
                                
                                {/* Expanded Justifications */}
                                {isExpanded && hasNotes && (
                                  <div style={{
                                    display: 'grid',
                                    gridTemplateColumns: s.notes_cv && s.notes_interview ? '1fr 1fr' : '1fr',
                                    gap: '12px',
                                    padding: '0 16px 12px 16px',
                                    borderTop: '1px solid rgba(139, 92, 246, 0.1)'
                                  }}>
                                    {/* CV Justification */}
                                    {s.notes_cv && (
                                      <div style={{
                                        padding: '12px',
                                        background: 'rgba(139, 92, 246, 0.05)',
                                        borderRadius: 'var(--radius-md)',
                                        border: '1px solid rgba(139, 92, 246, 0.1)'
                                      }}>
                                        <div style={{
                                          fontSize: '11px',
                                          fontWeight: '600',
                                          color: 'var(--primary-purple)',
                                          marginBottom: '6px',
                                          display: 'flex',
                                          alignItems: 'center',
                                          gap: '4px'
                                        }}>
                                          <FileText size={12} style={{ marginRight: '4px', verticalAlign: 'middle' }} /> CV
                                        </div>
                                        <div style={{
                                          fontSize: '12px',
                                          color: 'var(--text-secondary)',
                                          lineHeight: '1.5'
                                        }}>
                                          {s.notes_cv}
                                        </div>
                                      </div>
                                    )}
                                    
                                    {/* Interview Justification */}
                                    {s.notes_interview && (
                                      <div style={{
                                        padding: '12px',
                                        background: 'rgba(34, 197, 94, 0.05)',
                                        borderRadius: 'var(--radius-md)',
                                        border: '1px solid rgba(34, 197, 94, 0.1)'
                                      }}>
                                        <div style={{
                                          fontSize: '11px',
                                          fontWeight: '600',
                                          color: '#22c55e',
                                          marginBottom: '6px',
                                          display: 'flex',
                                          alignItems: 'center',
                                          gap: '4px'
                                        }}>
                                          <MessageCircle size={12} style={{ marginRight: '4px', verticalAlign: 'middle' }} /> Colloquio
                                        </div>
                                        <div style={{
                                          fontSize: '12px',
                                          color: 'var(--text-secondary)',
                                          lineHeight: '1.5'
                                        }}>
                                          {s.notes_interview}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            )
                          })}
                          </div>
                          
                          {/* Overall Means Section */}
                          {(() => {
                            const skillList = skills[r.session_id] || []
                            if (skillList.length === 0) return null
                            
                            const overallMean = calculateOverallMean(skillList)
                            const cvMean = skillList.reduce((sum: number, s: any) => sum + (s.cv_0_4 || 0), 0) / skillList.length
                            const interviewMean = skillList.reduce((sum: number, s: any) => sum + (s.interview_0_4 || 0), 0) / skillList.length
                            
                            return (
                              <div style={{
                                marginTop: '12px',
                                padding: '12px',
                                background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(236, 72, 153, 0.1))',
                                borderRadius: 'var(--radius-md)',
                                border: '1px solid rgba(139, 92, 246, 0.2)'
                              }}>
                                <div style={{
                                  display: 'grid',
                                  gridTemplateColumns: '1fr 80px 80px',
                                  gap: '8px',
                                  padding: '8px 12px',
                                  background: 'rgba(139, 92, 246, 0.15)',
                                  borderRadius: 'var(--radius-md)',
                                  marginBottom: '8px'
                                }}>
                                  <div style={{ 
                                    fontWeight: '600', 
                                    color: 'var(--primary-purple)',
                                    fontSize: '13px'
                                  }}>
                                    <TrendingUp size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Media Generale
                                  </div>
                                  <div style={{ 
                                    display: 'flex', 
                                    justifyContent: 'center',
                                    gap: '1px'
                                  }}>
                                    {renderStars(Math.round(cvMean * 10) / 10)}
                                  </div>
                                  <div style={{ 
                                    display: 'flex', 
                                    justifyContent: 'center',
                                    gap: '1px'
                                  }}>
                                    {renderStars(Math.round(interviewMean * 10) / 10)}
                                  </div>
                                </div>
                                
                                <div style={{
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  fontSize: '11px',
                                  color: 'var(--text-secondary)',
                                  padding: '0 12px'
                                }}>
                                  <div>
                                    <strong style={{ color: 'var(--primary-purple)' }}>
                                      Media CV: {cvMean.toFixed(1)}/4
                                    </strong>
                                  </div>
                                  <div>
                                    <strong style={{ color: 'var(--primary-purple)' }}>
                                      Media Colloquio: {interviewMean.toFixed(1)}/4
                                    </strong>
                                  </div>
                                  <div>
                                    <strong style={{ color: 'var(--primary-purple)' }}>
                                      Media Totale: {overallMean.toFixed(1)}/4
                                    </strong>
                                  </div>
                                </div>
                              </div>
                            )
                          })()}
                        </div>
                      </div>
                    ) : (
                      <div style={{ 
                        textAlign: 'center', 
                        padding: '20px',
                        color: 'var(--text-secondary)',
                        fontSize: '14px'
                      }}>
                        <BarChart3 size={16} style={{ marginRight: '8px', verticalAlign: 'middle' }} /> Nessuna valutazione competenze disponibile
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
      
      {/* Security Report Modal */}
      {showSecurityReport && (
        <SecurityReport
          sessionId={showSecurityReport}
          onClose={() => setShowSecurityReport(null)}
        />
      )}
    </div>
  )
}


