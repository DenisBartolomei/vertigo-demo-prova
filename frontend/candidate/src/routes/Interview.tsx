import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useAntiCheat } from '../hooks/useAntiCheat'
import { useSpeechRecognition } from '../hooks/useSpeechRecognition'
import { AntiCheatWarning } from '../components/AntiCheatWarning'
import { InterviewIntro } from '../components/InterviewIntro'
import { SandboxArea } from '../components/SandboxArea'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'

// Text formatting component for better message rendering
function FormattedMessage({ content }: { content: string }) {
  const formatInlineText = (text: string) => {
    // Handle inline formatting: **bold**, *italic*, `code`
    let formatted = text
    
    // Handle bold text **text**
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    
    // Handle italic text *text* (but not if it's already bold)
    formatted = formatted.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>')
    
    // Handle inline code `code`
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>')
    
    return formatted
  }
  
  const formatText = (text: string) => {
    // Split by double line breaks to create paragraphs
    const paragraphs = text.split('\n\n').filter(p => p.trim())
    
    return paragraphs.map((paragraph, index) => {
      // Handle single line breaks within paragraphs
      const lines = paragraph.split('\n').filter(line => line.trim())
      
      return (
        <div key={index} style={{ marginBottom: index < paragraphs.length - 1 ? '16px' : '0' }}>
          {lines.map((line, lineIndex) => {
            // Check if line starts with bullet points or numbered lists
            const isBullet = /^[-•*]\s/.test(line)
            const isNumbered = /^\d+\.\s/.test(line)
            const isBold = /^\*\*.*\*\*$/.test(line)
            const isItalic = /^\*.*\*$/.test(line)
            
            if (isBullet) {
              const bulletContent = line.replace(/^[-•*]\s/, '')
              return (
                <div key={lineIndex} style={{ 
                  display: 'flex', 
                  alignItems: 'flex-start', 
                  marginBottom: '8px',
                  paddingLeft: '16px'
                }}>
                  <span style={{ 
                    marginRight: '8px', 
                    color: 'var(--primary-purple)',
                    fontWeight: 'bold'
                  }}>•</span>
                  <span dangerouslySetInnerHTML={{ __html: formatInlineText(bulletContent) }} />
                </div>
              )
            }
            
            if (isNumbered) {
              const match = line.match(/^(\d+)\.\s(.*)/)
              if (match) {
                return (
                  <div key={lineIndex} style={{ 
                    display: 'flex', 
                    alignItems: 'flex-start', 
                    marginBottom: '8px',
                    paddingLeft: '16px'
                  }}>
                    <span style={{ 
                      marginRight: '8px', 
                      color: 'var(--primary-purple)',
                      fontWeight: 'bold',
                      minWidth: '20px'
                    }}>{match[1]}.</span>
                    <span dangerouslySetInnerHTML={{ __html: formatInlineText(match[2]) }} />
                  </div>
                )
              }
            }
            
            if (isBold) {
              const boldContent = line.replace(/^\*\*(.*)\*\*$/, '$1')
              return (
                <div key={lineIndex} style={{ 
                  fontWeight: '600', 
                  marginBottom: '8px',
                  color: 'var(--text-primary)'
                }}>
                  <span dangerouslySetInnerHTML={{ __html: formatInlineText(boldContent) }} />
                </div>
              )
            }
            
            if (isItalic) {
              const italicContent = line.replace(/^\*(.*)\*$/, '$1')
              return (
                <div key={lineIndex} style={{ 
                  fontStyle: 'italic', 
                  marginBottom: '8px',
                  color: 'var(--text-secondary)'
                }}>
                  <span dangerouslySetInnerHTML={{ __html: formatInlineText(italicContent) }} />
                </div>
              )
            }
            
            // Regular line with inline formatting
            return (
              <div key={lineIndex} style={{ 
                marginBottom: lineIndex < lines.length - 1 ? '8px' : '0',
                lineHeight: '1.6'
              }}>
                <span dangerouslySetInnerHTML={{ __html: formatInlineText(line) }} />
              </div>
            )
          })}
        </div>
      )
    })
  }
  
  return <div>{formatText(content)}</div>
}

type Message = { 
  role: 'assistant' | 'user'
  content: string
  timestamp?: string
}

export function Interview() {
  const { token } = useParams()
  const [session, setSession] = useState<any>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [isStarted, setIsStarted] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)
  const [showIntro, setShowIntro] = useState(true)
  const [termsAccepted, setTermsAccepted] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Speech recognition hook
  const {
    isListening,
    transcript,
    isSupported: isSpeechSupported,
    error: speechError,
    startListening,
    stopListening,
    resetTranscript
  } = useSpeechRecognition('it-IT')

  // Anti-cheat system
  const antiCheat = useAntiCheat({
    maxTabSwitches: 3,
    maxCopyPasteAttempts: 2,
    maxRightClicks: 5,
    maxWindowResizes: 10,
    warningThreshold: 3,
    sessionId: token || '',
    onCheatingDetected: async (event) => {
      // Send cheating event to backend
      try {
        await fetch(`${API_BASE}/interviews/${token}/security-event`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(event)
        })
      } catch (err) {
        console.error('Failed to report security event:', err)
      }
    }
  })

  useEffect(() => {
    if (!token) return
    loadSession()
  }, [token])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Sync speech transcript with input
  useEffect(() => {
    if (transcript) {
      setInput(prev => prev + transcript)
      resetTranscript()
    }
  }, [transcript, resetTranscript])

  // Add beforeunload warning when interview is started
  useEffect(() => {
    if (!isStarted) return

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = 'Se chiudi la pagina, il colloquio verrà terminato e inviato per la valutazione. Sei sicuro di voler uscire?'
      return e.returnValue
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [isStarted])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  async function loadSession() {
    try {
      const resp = await fetch(`${API_BASE}/interviews/${token}`)
      if (resp.status === 404) {
        setError('Token non valido o scaduto. Il token può essere utilizzato una sola volta. Se hai già iniziato il colloquio, non puoi più accedere.')
        return
      }
      if (resp.status === 410) {
        setError('Il colloquio è stato completato e la valutazione è terminata. L\'accesso non è più disponibile.')
        return
      }
      if (!resp.ok) throw new Error('Session not found')
      const data = await resp.json()
      setSession(data)
      
      // Check if there's existing conversation state
      const stateResp = await fetch(`${API_BASE}/interviews/${token}/state`)
      if (stateResp.ok) {
        const stateData = await stateResp.json()
        if (stateData.conversation && stateData.conversation.length > 0) {
          setMessages(stateData.conversation)
          setIsStarted(true)
        }
        // Check if interview is already completed
        if (stateData.finished === true) {
          setIsCompleted(true)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load session')
    }
  }

  async function sendMessage() {
    if (!input.trim() || !token) return
    
    const userMessage: Message = { 
      role: 'user', 
      content: input,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)
    
    try {
      const resp = await fetch(`${API_BASE}/interviews/${token}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: input })
      })
      if (resp.status === 410) {
        setError('Il colloquio è stato completato e la valutazione è terminata. L\'accesso non è più disponibile.')
        return
      }
      if (!resp.ok) throw new Error('Failed to send message')
      const data = await resp.json()
      
      // Add the assistant's reply to messages
      if (data.reply) {
        const assistantMessage: Message = {
          role: 'assistant',
          content: data.reply,
          timestamp: new Date().toISOString()
        }
        setMessages(prev => [...prev, assistantMessage])
      }
      
      // Also update from state if available
      if (data.state && data.state.conversation) {
        setMessages(data.state.conversation)
      }
      
      // Check if interview is completed using backend state
      if (data.state && data.state.finished === true) {
        setIsCompleted(true)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message')
      setMessages(prev => prev.slice(0, -1)) // Remove the user message on error
    } finally {
      setLoading(false)
    }
  }

  async function startInterview() {
    if (!token || loading) return // Prevent multiple starts
    setLoading(true)
    try {
      // Start anti-cheat monitoring
      antiCheat.startMonitoring()
      
      const resp = await fetch(`${API_BASE}/interviews/${token}/start`, { method: 'POST' })
      if (resp.status === 410) {
        setError('Il colloquio è stato completato e la valutazione è terminata. L\'accesso non è più disponibile.')
        return
      }
      if (resp.status === 409) {
        setError('Questo colloquio è già stato avviato. Ogni token può essere utilizzato una sola volta.')
        return
      }
      if (resp.status === 404) {
        setError('Token non valido o scaduto. Il token può essere utilizzato una sola volta.')
        return
      }
      if (!resp.ok) throw new Error('Failed to start interview')
      const data = await resp.json()
      
      // Add the initial message from the assistant
      if (data.message) {
        const initialMessage: Message = {
          role: 'assistant',
          content: data.message,
          timestamp: new Date().toISOString()
        }
        setMessages([initialMessage])
      }
      setIsStarted(true)
      setShowIntro(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start interview')
    } finally {
      setLoading(false)
    }
  }

  const handleAcceptTerms = () => {
    setTermsAccepted(true)
  }

  const handleWarningAccept = () => {
    // User acknowledged the warning
  }

  const handleWarningContinue = () => {
    // User wants to continue despite warnings
  }

  const handleVoiceToggle = () => {
    if (isListening) {
      stopListening()
    } else {
      startListening()
    }
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  if (error) {
    return (
      <div className="chat-container">
        <div className="welcome-screen">
          <div className="welcome-icon">⚠️</div>
          <h1 className="welcome-title">Something went wrong</h1>
          <p className="welcome-subtitle">{error}</p>
          <button className="start-button" onClick={() => window.location.reload()}>
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (!session) {
    return (
      <div className="chat-container">
        <div className="welcome-screen">
          <div className="welcome-icon">⏳</div>
          <h1 className="welcome-title">Loading your interview...</h1>
          <p className="welcome-subtitle">Please wait while we prepare everything for you</p>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-container">
      <AntiCheatWarning 
        warningCount={antiCheat.warnings}
        isBlocked={antiCheat.isBlocked}
        onAccept={handleWarningAccept}
        onContinue={handleWarningContinue}
      />
      
      <div className="chat-header">
        <div className="chat-header-icon">🎯</div>
        <div className="chat-header-content">
          <h1>{session.position_name}</h1>
          <p>Interview for {session.candidate_name}</p>
        </div>
      </div>

      {/* Warning message when interview is started */}
      {isStarted && (
        <div style={{
          backgroundColor: '#fff3cd',
          border: '1px solid #ffc107',
          borderRadius: '8px',
          padding: '12px 16px',
          margin: '16px',
          fontSize: '14px',
          color: '#856404',
          textAlign: 'center',
          fontWeight: '500'
        }}>
          ⚠️ <strong>ATTENZIONE:</strong> Se chiudi la pagina o esci dall'intervista, il colloquio verrà terminato e inviato per la valutazione.
        </div>
      )}

      <div className="chat-main-content">
        <div className="chat-messages">
      {showIntro ? (
          <InterviewIntro
            positionName={session.position_name}
            candidateName={session.candidate_name}
            onStart={startInterview}
            onAcceptTerms={handleAcceptTerms}
            loading={loading}
          />
        ) : !isStarted ? (
          <div className="welcome-screen">
            <div className="welcome-icon">🚀</div>
            <h1 className="welcome-title">Ready to start your interview?</h1>
            <p className="welcome-subtitle">
              This interview will help us understand your skills and experience for the {session.position_name} position. 
              Take your time and answer thoughtfully.
            </p>
            <button 
              className="start-button" 
              onClick={startInterview} 
              disabled={loading}
            >
              {loading ? '⏳ Starting...' : '🎯 Start Interview'}
            </button>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'assistant' ? '🤖' : '👤'}
                </div>
                <div className="message-content">
                  <div className="message-bubble">
                    <FormattedMessage content={msg.content} />
                  </div>
                  <div className="message-time">
                    {formatTime(msg.timestamp || new Date().toISOString())}
                  </div>
                </div>
              </div>
            ))}
            
            {loading && (
              <div className="message assistant">
                <div className="message-avatar">🤖</div>
                <div className="message-content">
                  <div className="typing-indicator">
                    <span>Thinking</span>
                    <div className="typing-dots">
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                      <div className="typing-dot"></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
        </div>

        {/* Sandbox Area */}
        <SandboxArea
          input={input}
          setInput={setInput}
          onSend={sendMessage}
          loading={loading}
          isListening={isListening}
          onVoiceToggle={handleVoiceToggle}
          isSpeechSupported={isSpeechSupported}
          speechError={speechError}
          isStarted={isStarted}
          isCompleted={isCompleted}
        />
      </div>
    </div>
  )
}