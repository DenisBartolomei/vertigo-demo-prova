import { useState, useEffect, useRef } from 'react'
import type { SandboxAreaRef } from '../components/SandboxArea'
import { useParams } from 'react-router-dom'
import { AlertTriangle, Clock, Monitor, AlertCircle, Pin, Lock, Target, Rocket, Bot, User, Send, CheckCircle2 } from 'lucide-react'
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
  const [showFullscreenWarning, setShowFullscreenWarning] = useState(false)
  const [fullscreenWarningStep, setFullscreenWarningStep] = useState(1) // 1 = fullscreen, 2 = pointer lock
  const [showFullscreenReturnPrompt, setShowFullscreenReturnPrompt] = useState(false)
  const [showMultipleDisplayBlock, setShowMultipleDisplayBlock] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const sandboxAreaRef = useRef<SandboxAreaRef>(null)
  const earlyFullscreenHandlerRef = useRef<(() => void) | null>(null)

  // Speech recognition hook
  const {
    isListening,
    transcript,
    isSupported: isSpeechSupported,
    error: speechError,
    startListening,
    stopListening,
    resetTranscript,
  } = useSpeechRecognition('it-IT')

  // Anti-cheat system con protezione fullscreen e screenshot (MODALITÀ MODERATA)
  const antiCheat = useAntiCheat({
    maxTabSwitches: 3,
    maxCopyPasteAttempts: 2,
    maxRightClicks: 5,
    maxWindowResizes: 10,
    warningThreshold: 3,
    sessionId: token || '',
    enforceFullscreen: true,              // ✅ Fullscreen obbligatorio
    terminateOnFullscreenExit: false,     // ✅ Modalità moderata: warning invece di terminare
    maxFullscreenExits: 2,                // ✅ Massimo 2 uscite prima di terminare
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
    },
    onInterviewTerminated: () => {
      // Chiamato quando il colloquio viene terminato per violazioni di sicurezza
      setError('COLLOQUIO TERMINATO: Hai superato il numero massimo di violazioni delle regole di sicurezza.')
      setIsCompleted(true)
      setIsStarted(false)
      // Notifica il backend della terminazione
      fetch(`${API_BASE}/interviews/${token}/terminated`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'security_violations' })
      }).catch(err => console.error('Failed to report termination:', err))
    },
    onFullscreenExit: () => {
      // Mostra il prompt per rientrare in fullscreen
      console.log('[Interview] onFullscreenExit chiamato, mostro prompt rosso')
      setShowFullscreenReturnPrompt(true)
    },
    onMultipleDisplayDetected: () => {
      // Blocca l'interfaccia quando viene rilevato un doppio schermo durante il colloquio
      setShowMultipleDisplayBlock(true)
    }
  })

  useEffect(() => {
    if (!token) return
    loadSession()
  }, [token])

  useEffect(() => {
    scrollToBottom()
    
    // Auto-focus sul textarea quando arriva un messaggio dall'assistente
    const lastMessage = messages[messages.length - 1]
    if (lastMessage && lastMessage.role === 'assistant' && !loading) {
      // Delay per assicurarsi che il componente sia renderizzato
      setTimeout(() => {
        sandboxAreaRef.current?.focus()
      }, 100)
    }
  }, [messages, loading])

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
      e.returnValue = 'If you close the page, the interview will be terminated and sent for evaluation. Are you sure you want to exit?'
      return e.returnValue
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [isStarted])

  // NOTA: scorciatoia Ctrl/Cmd+M rimossa.
  // Ora il microfono si controlla solo tramite Tab + Invio nella UI (gestito in SandboxArea).

  // Stop security monitoring when interview is completed
  useEffect(() => {
    if (isCompleted) {
      // Ferma il monitoraggio di sicurezza quando il colloquio è finito
      antiCheat.stopMonitoring()
      console.log('Monitoraggio sicurezza fermato: colloquio completato')
    }
  }, [isCompleted, antiCheat])


  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  async function loadSession() {
    try {
      const resp = await fetch(`${API_BASE}/interviews/${token}`)
      if (resp.status === 404) {
        setError('Token not valid or expired. The token can be used only once. If you have already started the interview, you cannot access it anymore.')
        return
      }
      if (resp.status === 410) {
        setError('The interview has been completed and the evaluation has been finished. The access is no longer available.')
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
        setError('The interview has been completed and the evaluation has been finished. The access is no longer available.')
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
    
    // Controlla prima se c'è un doppio schermo attivo
    if (antiCheat.checkMultipleDisplays()) {
      setShowMultipleDisplayBlock(true)
      return
    }
    
    // Mostra prima il popup di avviso fullscreen (sempre dallo step 1)
    setFullscreenWarningStep(1)
    setShowFullscreenWarning(true)
  }

  function handleCheckMultipleDisplaysAgain() {
    // Controlla di nuovo se il doppio schermo è ancora presente
    if (!antiCheat.checkMultipleDisplays()) {
      // Se non è più presente, resetta il flag e chiudi il popup
      antiCheat.resetMultipleDisplayBlock()
      setShowMultipleDisplayBlock(false)
      
      // Se il colloquio non è ancora iniziato, mostra il warning fullscreen
      // Se il colloquio è già iniziato, continua normalmente
      if (!isStarted) {
      setShowFullscreenWarning(true)
      }
      // Se il colloquio è già iniziato, il popup si chiude e l'utente può continuare
    }
    // Se è ancora presente, il popup rimane aperto
  }

  async function handleFullscreenWarningAccept() {
    if (fullscreenWarningStep === 1) {
      // CRITICO: Registra l'event listener per fullscreenchange PRIMA di richiedere fullscreen
      // Questo assicura che l'uscita dal fullscreen venga rilevata anche se startMonitoring() non è ancora stato chiamato
      const handleFullscreenChangeEarly = () => {
        const isNowFullscreen = !!document.fullscreenElement
        console.log('[Fullscreen] Early handler chiamato. isNowFullscreen:', isNowFullscreen)
        
        if (!isNowFullscreen) {
          // L'utente è uscito dal fullscreen PRIMA che startMonitoring() venga chiamato
          console.log('[Fullscreen] ⚠️ UTENTE USCITO DAL FULLSCREEN PRIMA DELL\'AVVIO!')
          console.log('[Fullscreen] Early handler: imposto showFullscreenReturnPrompt a true')
          setShowFullscreenReturnPrompt(true)
          console.log('[Fullscreen] Early handler: showFullscreenReturnPrompt impostato')
          // Rimuovi questo listener temporaneo
          if (earlyFullscreenHandlerRef.current) {
            document.removeEventListener('fullscreenchange', earlyFullscreenHandlerRef.current)
            earlyFullscreenHandlerRef.current = null
          }
        }
      }
      
      earlyFullscreenHandlerRef.current = handleFullscreenChangeEarly
      document.addEventListener('fullscreenchange', handleFullscreenChangeEarly)
      
      // Step 1: Richiedi fullscreen
      try {
        await document.documentElement.requestFullscreen()
        console.log('[Fullscreen] ✅ Fullscreen attivato con successo')
        console.log('[Fullscreen] document.fullscreenElement:', document.fullscreenElement)
        
        // CRITICO: Verifica che il fullscreen sia effettivamente attivo
        // A volte il browser può richiedere un momento per attivarlo
        await new Promise(resolve => setTimeout(resolve, 100))
        const isActuallyFullscreen = !!document.fullscreenElement
        console.log('[Fullscreen] Verifica fullscreen dopo delay:', isActuallyFullscreen)
        
        if (!isActuallyFullscreen) {
          throw new Error('Fullscreen non attivato correttamente')
        }
        
        // Passa allo step 2 (pointer lock)
        setFullscreenWarningStep(2)
      } catch (fsErr) {
        console.error('[Fullscreen] ❌ Errore attivazione fullscreen:', fsErr)
        setError('Failed to enter fullscreen. Please allow fullscreen mode to start the interview.')
        setShowFullscreenWarning(false)
        setFullscreenWarningStep(1) // Reset step
        if (earlyFullscreenHandlerRef.current) {
          document.removeEventListener('fullscreenchange', earlyFullscreenHandlerRef.current)
          earlyFullscreenHandlerRef.current = null
        }
        return
      }
    } else if (fullscreenWarningStep === 2) {
      // Step 2: Richiedi pointer lock e avvia colloquio
      setShowFullscreenWarning(false)
      setLoading(true)
      
      try {
        // CRITICO: Rimuovi il listener temporaneo early (ora startMonitoring() gestirà fullscreenchange)
        if (earlyFullscreenHandlerRef.current) {
          document.removeEventListener('fullscreenchange', earlyFullscreenHandlerRef.current)
          earlyFullscreenHandlerRef.current = null
        }
        
        // CRITICO: Rimuovi il listener temporaneo early (ora startMonitoring() gestirà fullscreenchange)
        if (earlyFullscreenHandlerRef.current) {
          document.removeEventListener('fullscreenchange', earlyFullscreenHandlerRef.current)
          earlyFullscreenHandlerRef.current = null
        }
        
        // CRITICO: Start anti-cheat monitoring PRIMA di richiedere pointer lock
        antiCheat.startMonitoring()
        
        // CRITICO: Richiedi pointer lock IMMEDIATAMENTE (mentre siamo ancora nel contesto del gesto utente)
        console.log('[Pointer Lock] 🔒 Richiesta pointer lock immediata...')
        antiCheat.requestPointerLock()
        
        // Verifica dopo un breve delay se si è attivato
        setTimeout(() => {
          const isLocked = !!(
            document.pointerLockElement ||
            (document as any).webkitPointerLockElement ||
            (document as any).mozPointerLockElement
          )
          if (!isLocked) {
            console.warn('[Pointer Lock] ⚠️ Non attivato immediatamente, retry...')
            antiCheat.requestPointerLock()
          } else {
            console.log('[Pointer Lock] ✅ Attivato con successo!')
          }
        }, 200)
        
        // Avvia il colloquio
        const resp = await fetch(`${API_BASE}/interviews/${token}/start`, { method: 'POST' })
        if (resp.status === 400) {
          setError('Please complete your profile information first by entering your name and surname.')
          setLoading(false)
          return
        }
        if (resp.status === 410) {
          setError('The interview has been completed and the evaluation has been finished. The access is no longer available.')
          setLoading(false)
          return
        }
        if (resp.status === 409) {
          setError('This interview has already been started. Each token can be used only once.')
          setLoading(false)
          return
        }
        if (resp.status === 404) {
          setError('Token not valid or expired. The token can be used only once.')
          setLoading(false)
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
        setLoading(false) // IMPORTANTE: Reset loading dopo aver avviato il colloquio
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to start interview')
        setLoading(false)
      }
    }
  }

  function handleReenterFullscreen() {
    setShowFullscreenReturnPrompt(false)
    antiCheat.reenterFullscreen()
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
          <AlertTriangle size={36} color="white" style={{ marginBottom: '24px' }} />
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
          <Clock size={36} color="white" style={{ marginBottom: '24px' }} />
          <h1 className="welcome-title">Loading your interview...</h1>
          <p className="welcome-subtitle">Please wait while we prepare everything for you</p>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-container">
      {/* Popup di blocco doppio schermo */}
      {showMultipleDisplayBlock && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(220, 38, 38, 0.95)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10001
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '16px',
            padding: '32px',
            maxWidth: '600px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
          }}>
            <div style={{ textAlign: 'center', marginBottom: '24px' }}>
              <Monitor size={64} color="#dc2626" style={{ marginBottom: '16px' }} />
              <h2 style={{ fontSize: '24px', fontWeight: '600', color: '#dc2626', marginBottom: '12px' }}>
                Doppio Schermo Rilevato
              </h2>
            </div>
            <div style={{ fontSize: '16px', lineHeight: '1.6', color: '#4a4a4a', marginBottom: '24px' }}>
              <p style={{ marginBottom: '16px' }}>
                <strong style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertCircle size={18} /> ATTENZIONE:
                </strong> Il sistema ha rilevato la presenza di più schermi collegati al tuo computer.
              </p>
              <div style={{ backgroundColor: '#fee2e2', border: '1px solid #dc2626', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
                <p style={{ margin: 0, color: '#991b1b' }}>
                  <strong style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertTriangle size={16} /> Regola di sicurezza:
                  </strong>
                </p>
                <ul style={{ marginTop: '12px', paddingLeft: '20px', color: '#991b1b' }}>
                  <li>Per garantire l'integrità del colloquio, è necessario utilizzare <strong>un solo schermo</strong></li>
                  <li>Disconnetti tutti i monitor aggiuntivi prima di procedere</li>
                  <li>Una volta disconnesso lo schermo aggiuntivo, clicca su "Verifica di nuovo"</li>
                </ul>
              </div>
              <p style={{ fontSize: '14px', color: '#666', margin: 0 }}>
                <Pin size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Questo controllo viene eseguito anche durante il colloquio per garantire la sicurezza del processo.
              </p>
            </div>
            <button
              onClick={handleCheckMultipleDisplaysAgain}
              style={{
                width: '100%',
                padding: '16px',
                fontSize: '18px',
                fontWeight: '600',
                color: 'white',
                backgroundColor: '#16a34a',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                transition: 'all 0.2s',
                marginBottom: '12px'
              }}
              onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#15803d'}
              onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#16a34a'}
            >
              <CheckCircle2 size={18} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Verifica di nuovo
            </button>
          </div>
        </div>
      )}

      {/* Guida navigazione tastiera (in alto a destra) */}
      {isStarted && !isCompleted && (
        <div
          style={{
            position: 'fixed',
            top: '20px',
            right: '20px',
            zIndex: 9000,
            backgroundColor: 'rgba(17, 24, 39, 0.9)',
            color: 'white',
            padding: '12px 16px',
            borderRadius: '12px',
            fontSize: '12px',
            maxWidth: '260px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: '4px' }}>⌨️ Keyboard Navigation</div>
          <div style={{ lineHeight: 1.5 }}>
            <div>• <span style={{ 
              display: 'inline-block',
              padding: '2px 6px',
              backgroundColor: '#f3f4f6',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '11px',
              fontWeight: '600',
              color: '#374151'
            }}>⇥ Tab</span>: Switch between text area and microphone</div>
            <div>• <span style={{ 
              display: 'inline-block',
              padding: '2px 6px',
              backgroundColor: '#f3f4f6',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '11px',
              fontWeight: '600',
              color: '#374151'
            }}>↵ Enter</span> (on microphone): Toggle voice input</div>
            <div>• <span style={{ 
              display: 'inline-block',
              padding: '2px 6px',
              backgroundColor: '#f3f4f6',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '11px',
              fontWeight: '600',
              color: '#374151'
            }}>↵ Enter</span> (on text area): Send answer</div>
          </div>
        </div>
      )}

      {/* Popup di avviso fullscreen prima dell'inizio */}
      {showFullscreenWarning && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.85)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '16px',
            padding: '32px',
            maxWidth: '600px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
          }}>
            {/* Step 1: Fullscreen Warning */}
            {fullscreenWarningStep === 1 && (
              <>
                <div style={{ textAlign: 'center', marginBottom: '24px' }}>
                  <Lock size={64} color="#7c3aed" style={{ marginBottom: '16px' }} />
                  <h2 style={{ fontSize: '24px', fontWeight: '600', color: '#1a1a1a', marginBottom: '12px' }}>
                    Modalità Schermo Intero Obbligatoria
                  </h2>
                  <div style={{ fontSize: '14px', color: '#666', marginTop: '8px' }}>
                    Passo 1/2
                  </div>
                </div>
                <div style={{ fontSize: '16px', lineHeight: '1.6', color: '#4a4a4a', marginBottom: '24px' }}>
                  <p style={{ marginBottom: '16px' }}>
                    <strong style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <AlertCircle size={18} /> IMPORTANTE:
                    </strong> Quando cliccherai "Ho capito", il colloquio inizierà in modalità schermo intero.
                  </p>
                  <div style={{ backgroundColor: '#fff3cd', border: '1px solid #ffc107', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
                    <p style={{ margin: 0, color: '#856404' }}>
                      <strong style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <AlertTriangle size={16} /> Regole di sicurezza:
                      </strong>
                    </p>
                    <ul style={{ marginTop: '12px', paddingLeft: '20px', color: '#856404' }}>
                      <li>Devi rimanere in modalità schermo intero per tutta la durata del colloquio</li>
                      <li>Uscire dallo schermo intero verrà registrato come tentativo di violazione</li>
                      <li>Sono consentite <strong>massimo 2 uscite</strong> accidentali</li>
                      <li>Oltre il limite, il colloquio verrà <strong>automaticamente terminato</strong></li>
                    </ul>
                  </div>
                  <p style={{ fontSize: '14px', color: '#666', margin: 0 }}>
                    <Pin size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Per uscire dallo schermo intero temporaneamente, ti verrà mostrato un pulsante per rientrare.
                  </p>
                </div>
                <button
                  onClick={handleFullscreenWarningAccept}
                  style={{
                    width: '100%',
                    padding: '16px',
                    fontSize: '18px',
                    fontWeight: '600',
                    color: 'white',
                    backgroundColor: '#7c3aed',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#6d28d9'}
                  onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#7c3aed'}
                >
                  <CheckCircle2 size={18} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Ho capito, continua
                </button>
              </>
            )}

            {/* Step 2: Pointer Lock Warning */}
            {fullscreenWarningStep === 2 && (
              <>
                <div style={{ textAlign: 'center', marginBottom: '24px' }}>
                  <Lock size={64} color="#7c3aed" style={{ marginBottom: '16px' }} />
                  <h2 style={{ fontSize: '24px', fontWeight: '600', color: '#1a1a1a', marginBottom: '12px' }}>
                    Blocco Cursore Richiesto
                  </h2>
                  <div style={{ fontSize: '14px', color: '#666', marginTop: '8px' }}>
                    Passo 2/2
                  </div>
                </div>
                <div style={{ fontSize: '16px', lineHeight: '1.6', color: '#4a4a4a', marginBottom: '24px' }}>
                  <p style={{ marginBottom: '16px' }}>
                    <strong style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <AlertCircle size={18} /> IMPORTANTE:
                    </strong> Per garantire l'integrità del colloquio, è necessario bloccare temporaneamente il cursore del mouse all'interno della finestra.
                  </p>
                  <div style={{ backgroundColor: '#e0e7ff', border: '1px solid #7c3aed', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
                    <p style={{ margin: 0, color: '#4338ca' }}>
                      <strong style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Lock size={16} /> Informazioni sul blocco cursore:
                      </strong>
                    </p>
                    <ul style={{ marginTop: '12px', paddingLeft: '20px', color: '#4338ca' }}>
                      <li>Il blocco del cursore è <strong>temporaneo</strong> e attivo solo durante il colloquio</li>
                      <li>Il sistema <strong>monitora</strong> continuamente lo stato del blocco</li>
                      <li>Se il blocco viene perso, verrà riattivato automaticamente</li>
                      <li>Puoi uscire dal blocco premendo ESC, ma questa azione verrà registrata</li>
                    </ul>
                  </div>
                  <p style={{ fontSize: '14px', color: '#666', margin: 0 }}>
                    <Pin size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Clicca "Avvia colloquio" per attivare il blocco cursore e iniziare.
                  </p>
                </div>
                <button
                  onClick={handleFullscreenWarningAccept}
                  style={{
                    width: '100%',
                    padding: '16px',
                    fontSize: '18px',
                    fontWeight: '600',
                    color: 'white',
                    backgroundColor: '#7c3aed',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#6d28d9'}
                  onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#7c3aed'}
                >
                  <CheckCircle2 size={18} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Ho capito, avvia il colloquio
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Prompt per rientrare in fullscreen */}
      {showFullscreenReturnPrompt && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(220, 38, 38, 0.95)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '16px',
            padding: '32px',
            maxWidth: '500px',
            textAlign: 'center',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
          }}>
            <AlertTriangle size={64} color="#dc2626" style={{ marginBottom: '16px' }} />
            <h2 style={{ fontSize: '28px', fontWeight: '700', color: '#dc2626', marginBottom: '16px' }}>
              ATTENZIONE!
            </h2>
            <p style={{ fontSize: '18px', lineHeight: '1.6', color: '#4a4a4a', marginBottom: '24px' }}>
              Sei uscito dalla modalità schermo intero. Questa azione è stata <strong>registrata</strong> nel tuo report di valutazione.
            </p>
            <p style={{ fontSize: '16px', color: '#666', marginBottom: '8px' }}>
              Uscite rimanenti: <strong style={{ color: '#dc2626', fontSize: '20px' }}>
                {2 - (antiCheat.getCheatingSummary().highSeverityEvents || 0)}
              </strong>
            </p>
            <p style={{ fontSize: '14px', color: '#666', marginBottom: '32px' }}>
              Clicca il pulsante per tornare alla sessione
            </p>
            <button
              onClick={handleReenterFullscreen}
              style={{
                width: '100%',
                padding: '20px',
                fontSize: '20px',
                fontWeight: '700',
                color: 'white',
                backgroundColor: '#16a34a',
                border: 'none',
                borderRadius: '12px',
                cursor: 'pointer',
                boxShadow: '0 4px 16px rgba(22, 163, 74, 0.4)',
                transition: 'all 0.2s'
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.backgroundColor = '#15803d'
                e.currentTarget.style.transform = 'scale(1.02)'
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.backgroundColor = '#16a34a'
                e.currentTarget.style.transform = 'scale(1)'
              }}
            >
              <Lock size={18} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Ritorna alla Sessione a Tutto Schermo
            </button>
          </div>
        </div>
      )}
      
      <AntiCheatWarning 
        warningCount={antiCheat.warnings}
        isBlocked={antiCheat.isBlocked}
        onAccept={handleWarningAccept}
        onContinue={handleWarningContinue}
      />
      
      <div className="chat-header">
        <div className="chat-header-icon" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Target size={20} color="white" />
        </div>
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
          <AlertCircle size={16} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> <strong>ATTENTION:</strong> If you close the page or exit the interview, the interview will be terminated and sent for evaluation.
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
            <div className="welcome-icon" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Rocket size={36} color="white" />
            </div>
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
              {loading ? (
                <>
                  <Clock size={18} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Starting...
                </>
              ) : (
                <>
                  <Target size={18} style={{ marginRight: '6px', verticalAlign: 'middle' }} /> Start Interview
                </>
              )}
            </button>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className="message-avatar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {msg.role === 'assistant' ? <Bot size={14} color="white" /> : <User size={14} />}
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
                <div className="message-avatar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Bot size={14} color="white" />
                </div>
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
          ref={sandboxAreaRef}
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