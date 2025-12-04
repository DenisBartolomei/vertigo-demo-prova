import { useState, useEffect, useCallback, useRef } from 'react'

interface CheatingEvent {
  type: 'tab_switch' | 'copy_paste' | 'right_click' | 'devtools' | 'keyboard_shortcut' | 'focus_loss' | 'window_resize' | 'screenshot_attempt' | 'fullscreen_exit' | 'print_attempt' | 'multiple_display' | 'pointer_lock_exit' | 'pointer_lock_failed' | 'pointer_lock_lost'
  timestamp: string
  details?: string
  severity: 'low' | 'medium' | 'high'
}

interface AntiCheatConfig {
  maxTabSwitches: number
  maxCopyPasteAttempts: number
  maxRightClicks: number
  maxWindowResizes: number
  warningThreshold: number
  sessionId: string
  enforceFullscreen?: boolean
  terminateOnFullscreenExit?: boolean
  maxFullscreenExits?: number
  onCheatingDetected: (event: CheatingEvent) => void
  onInterviewTerminated?: () => void
  onFullscreenExit?: () => void
  onMultipleDisplayDetected?: () => void
}

export function useAntiCheat(config: AntiCheatConfig) {
  const [events, setEvents] = useState<CheatingEvent[]>([])
  const [isMonitoring, setIsMonitoring] = useState(false)
  const isMonitoringRef = useRef(false) // Ref per accesso sincrono allo stato
  const [warnings, setWarnings] = useState(0)
  const [isBlocked, setIsBlocked] = useState(false)
  const [cursorPosition, setCursorPosition] = useState({ 
    x: typeof window !== 'undefined' ? window.innerWidth / 2 : 0, 
    y: typeof window !== 'undefined' ? window.innerHeight / 2 : 0 
  })
  const [isPointerLocked, setIsPointerLocked] = useState(false)
  
  const tabSwitchCount = useRef(0)
  const copyPasteCount = useRef(0)
  const rightClickCount = useRef(0)
  const windowResizeCount = useRef(0)
  const lastFocusTime = useRef(Date.now())
  const isVisible = useRef(true)
  const fullscreenExitCount = useRef(0)
  const isFullscreen = useRef(false)
  const screenshotAttemptCount = useRef(0)
  const multipleDisplayCount = useRef(0)
  const multipleDisplayBlocked = useRef(false)
  const lastScreenCheck = useRef<{ width: number; height: number; availWidth: number; availHeight: number } | null>(null)
  const cleanupRef = useRef<(() => void) | null>(null)
  
  // Pointer Lock refs
  const pointerLockExitCount = useRef(0)
  const cursorPositionRef = useRef({ x: window.innerWidth / 2, y: window.innerHeight / 2 })
  const isPointerLockActive = useRef(false)
  
  // Batching per security events
  const eventBuffer = useRef<CheatingEvent[]>([])
  const batchTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const isSendingBatch = useRef(false)

  // Funzione per inviare batch di eventi
  const sendEventBatch = useCallback(async (events: CheatingEvent[]) => {
    if (events.length === 0 || isSendingBatch.current) return
    
    isSendingBatch.current = true
    try {
      // Invia tutti gli eventi in un'unica chiamata (il backend li gestirà)
      for (const event of events) {
        await config.onCheatingDetected(event)
      }
      eventBuffer.current = []
    } catch (error) {
      console.error('Error sending event batch:', error)
    } finally {
      isSendingBatch.current = false
    }
  }, [config])

  // Schedula invio batch dopo 5 secondi
  const scheduleBatchSend = useCallback(() => {
    if (batchTimeoutRef.current) {
      clearTimeout(batchTimeoutRef.current)
    }
    
    batchTimeoutRef.current = setTimeout(() => {
      if (eventBuffer.current.length > 0) {
        const eventsToSend = [...eventBuffer.current]
        eventBuffer.current = []
        sendEventBatch(eventsToSend)
      }
      batchTimeoutRef.current = null
    }, 5000) // 5 secondi
  }, [sendEventBatch])

  const addEvent = useCallback((event: CheatingEvent) => {
    // NON registrare eventi se il monitoraggio è fermo
    // Usa il ref sincrono per evitare problemi di timing con setState
    if (!isMonitoringRef.current) {
      return
    }
    
    setEvents(prev => [...prev, event])
    
    // Just track warnings, don't block interview
    if (event.severity === 'high') {
      setWarnings(prev => prev + 1)
    }
    
    // Batching: accumula eventi invece di inviarli immediatamente
    // Eccezione: eventi high severity critici vengono inviati immediatamente
    const isCriticalHighSeverity = event.severity === 'high' && 
      (event.type === 'fullscreen_exit' || event.type === 'multiple_display')
    
    if (isCriticalHighSeverity) {
      // Invia immediatamente eventi critici
      config.onCheatingDetected(event)
    } else {
      // Accumula eventi normali nel buffer
      eventBuffer.current.push(event)
      
      // Se il buffer raggiunge 10 eventi, invia immediatamente
      if (eventBuffer.current.length >= 10) {
        const eventsToSend = [...eventBuffer.current]
        eventBuffer.current = []
        sendEventBatch(eventsToSend)
        if (batchTimeoutRef.current) {
          clearTimeout(batchTimeoutRef.current)
          batchTimeoutRef.current = null
        }
      } else {
        // Altrimenti schedula invio dopo 5 secondi
        scheduleBatchSend()
      }
    }
  }, [config, sendEventBatch, scheduleBatchSend])

  const handleVisibilityChange = useCallback(() => {
    if (document.hidden) {
      isVisible.current = false
      tabSwitchCount.current++
      
      const event: CheatingEvent = {
        type: 'tab_switch',
        timestamp: new Date().toISOString(),
        details: `Tab switch #${tabSwitchCount.current}`,
        severity: tabSwitchCount.current > config.maxTabSwitches ? 'high' : 'medium'
      }
      addEvent(event)
    } else {
      isVisible.current = true
      lastFocusTime.current = Date.now()
    }
  }, [addEvent, config.maxTabSwitches])

  const handleWindowBlur = useCallback(() => {
    const event: CheatingEvent = {
      type: 'focus_loss',
      timestamp: new Date().toISOString(),
      details: 'Window lost focus',
      severity: 'medium'
    }
    addEvent(event)
  }, [addEvent])

  const handleWindowFocus = useCallback(() => {
    lastFocusTime.current = Date.now()
  }, [])

  const handleContextMenu = useCallback((e: MouseEvent) => {
    e.preventDefault()
    rightClickCount.current++
    
    const event: CheatingEvent = {
      type: 'right_click',
      timestamp: new Date().toISOString(),
      details: `Right click attempt #${rightClickCount.current}`,
      severity: rightClickCount.current > config.maxRightClicks ? 'high' : 'low'
    }
    addEvent(event)
  }, [addEvent, config.maxRightClicks])

  const handleCopyPaste = useCallback((e: ClipboardEvent) => {
    e.preventDefault()
    copyPasteCount.current++
    
    const event: CheatingEvent = {
      type: 'copy_paste',
      timestamp: new Date().toISOString(),
      details: `Copy/paste attempt #${copyPasteCount.current}`,
      severity: copyPasteCount.current > config.maxCopyPasteAttempts ? 'high' : 'medium'
    }
    addEvent(event)
  }, [addEvent, config.maxCopyPasteAttempts])

  const handleKeyboardShortcuts = useCallback((e: KeyboardEvent) => {
    const isCtrlOrCmd = e.ctrlKey || e.metaKey
    const isAlt = e.altKey
    const isShift = e.shiftKey
    
    // Block common cheating shortcuts
    const blockedShortcuts = [
      { key: 'c', ctrl: true, name: 'Copy' },
      { key: 'v', ctrl: true, name: 'Paste' },
      { key: 'x', ctrl: true, name: 'Cut' },
      { key: 'a', ctrl: true, name: 'Select All' },
      { key: 's', ctrl: true, name: 'Save' },
      { key: 'p', ctrl: true, name: 'Print' },
      { key: 'F12', name: 'Developer Tools' },
      { key: 'F5', name: 'Refresh' },
      { key: 'F11', name: 'Fullscreen' },
      { key: 'Tab', alt: true, name: 'Alt+Tab' },
      { key: 'Tab', shift: true, name: 'Shift+Tab' }
    ]

    for (const shortcut of blockedShortcuts) {
      if (
        e.key === shortcut.key &&
        (!shortcut.ctrl || isCtrlOrCmd) &&
        (!shortcut.alt || isAlt) &&
        (!shortcut.shift || isShift)
      ) {
        e.preventDefault()
        
        const event: CheatingEvent = {
          type: 'keyboard_shortcut',
          timestamp: new Date().toISOString(),
          details: `Blocked shortcut: ${shortcut.name}`,
          severity: 'high'
        }
        addEvent(event)
        break
      }
    }
  }, [addEvent])

  const handleResize = useCallback(() => {
    windowResizeCount.current++
    
    const event: CheatingEvent = {
      type: 'window_resize',
      timestamp: new Date().toISOString(),
      details: `Window resize #${windowResizeCount.current}`,
      severity: windowResizeCount.current > config.maxWindowResizes ? 'medium' : 'low'
    }
    addEvent(event)
  }, [addEvent, config.maxWindowResizes])

  const detectDevTools = useCallback(() => {
    // Simple dev tools detection
    const threshold = 160
    const widthThreshold = window.outerWidth - window.innerWidth > threshold
    const heightThreshold = window.outerHeight - window.innerHeight > threshold
    
    if (widthThreshold || heightThreshold) {
      const event: CheatingEvent = {
        type: 'devtools',
        timestamp: new Date().toISOString(),
        details: 'Developer tools detected',
        severity: 'high'
      }
      addEvent(event)
    }
  }, [addEvent])

  // Pointer Lock API functions - definiti PRIMA di handleScreenshotAttempt per evitare errori di inizializzazione
  const isPointerLockSupported = useCallback((): boolean => {
    return typeof document.body.requestPointerLock === 'function' ||
           typeof (document.body as any).webkitRequestPointerLock === 'function' ||
           typeof (document.body as any).mozRequestPointerLock === 'function'
  }, [])
  
  const requestPointerLock = useCallback(() => {
    if (!isPointerLockSupported()) {
      console.warn('[Pointer Lock] API non supportata dal browser')
      // Browser non supporta pointer lock - fallback graceful
      const event: CheatingEvent = {
        type: 'pointer_lock_failed',
        timestamp: new Date().toISOString(),
        details: 'Pointer Lock API not supported by browser',
        severity: 'medium'
      }
      addEvent(event)
      return
    }
    
    // Verifica se il pointer lock è già attivo
    const isAlreadyLocked = !!(
      document.pointerLockElement ||
      (document as any).webkitPointerLockElement ||
      (document as any).mozPointerLockElement
    )
    
    if (isAlreadyLocked) {
      console.log('[Pointer Lock] Già attivo, skip')
      return
    }
    
    const elem = document.body
    console.log('[Pointer Lock] Tentativo di attivare pointer lock...')
    
    // Prova con metodo standard
    if (elem.requestPointerLock) {
      const promise = elem.requestPointerLock()
      if (promise) {
        promise
          .then(() => {
            console.log('[Pointer Lock] ✅ Richiesta accettata dal browser')
          })
          .catch((err: Error) => {
            console.error('[Pointer Lock] ❌ Errore nella richiesta:', err)
            const event: CheatingEvent = {
              type: 'pointer_lock_failed',
              timestamp: new Date().toISOString(),
              details: `Pointer lock request failed: ${err.message}`,
              severity: 'high'
            }
            addEvent(event)
          })
      } else {
        // Alcuni browser non restituiscono una promise
        console.log('[Pointer Lock] Richiesta inviata (browser senza promise)')
      }
    } else if ((elem as any).webkitRequestPointerLock) {
      // Fallback per Safari/WebKit
      console.log('[Pointer Lock] Usando webkitRequestPointerLock')
      ;(elem as any).webkitRequestPointerLock()
    } else if ((elem as any).mozRequestPointerLock) {
      // Fallback per Firefox
      console.log('[Pointer Lock] Usando mozRequestPointerLock')
      ;(elem as any).mozRequestPointerLock()
    } else {
      console.error('[Pointer Lock] Nessun metodo disponibile per questo browser')
      const event: CheatingEvent = {
        type: 'pointer_lock_failed',
        timestamp: new Date().toISOString(),
        details: 'No pointer lock method available',
        severity: 'high'
      }
      addEvent(event)
    }
  }, [addEvent, isPointerLockSupported])

  // NUOVO: Blocco screenshot
  const handleScreenshotAttempt = useCallback((e: KeyboardEvent) => {
    const isCtrlOrCmd = e.ctrlKey || e.metaKey
    const isShift = e.shiftKey
    
    // Blocca tutte le scorciatoie screenshot comuni
    const screenshotShortcuts = [
      // Windows
      { key: 'PrintScreen', name: 'PrtScn' },
      { key: 'Print', name: 'Print' },
      // Mac
      { key: '3', shift: true, cmd: true, name: 'Cmd+Shift+3' },
      { key: '4', shift: true, cmd: true, name: 'Cmd+Shift+4' },
      { key: '5', shift: true, cmd: true, name: 'Cmd+Shift+5' },
      // Print
      { key: 'p', ctrl: true, name: 'Ctrl+P' }
    ]

    for (const shortcut of screenshotShortcuts) {
      const keyMatch = e.key === shortcut.key
      const shiftMatch = !shortcut.shift || isShift
      const cmdMatch = !shortcut.cmd || isCtrlOrCmd
      const ctrlMatch = !shortcut.ctrl || isCtrlOrCmd
      
      if (keyMatch && shiftMatch && cmdMatch && ctrlMatch) {
        e.preventDefault()
        e.stopPropagation()
        screenshotAttemptCount.current++
        
        const event: CheatingEvent = {
          type: 'screenshot_attempt',
          timestamp: new Date().toISOString(),
          details: `Screenshot attempt blocked: ${shortcut.name} (attempt #${screenshotAttemptCount.current})`,
          severity: 'high'
        }
        addEvent(event)
        
        // Mostra alert visibile
        alert('ATTENZIONE: Il tentativo di screenshot è stato rilevato e registrato nel report di valutazione.')
        
        // CRITICO: Se il pointer lock si disattiva dopo screenshot, riattivalo
        setTimeout(() => {
          if (isFullscreen.current && isMonitoringRef.current && config.enforceFullscreen) {
            const isLocked = !!(
              document.pointerLockElement ||
              (document as any).webkitPointerLockElement ||
              (document as any).mozPointerLockElement
            )
            if (!isLocked && document.fullscreenElement) {
              console.log('[Pointer Lock] Screenshot rilevato, riattivo pointer lock...')
              requestPointerLock()
            }
          }
        }, 300)
        
        return true
      }
    }
    return false
  }, [addEvent, isFullscreen, config, requestPointerLock])

  // NUOVO: Fullscreen enforcement
  const requestFullscreen = useCallback(() => {
    const elem = document.documentElement
    if (elem.requestFullscreen) {
      elem.requestFullscreen().catch(err => {
        console.error('Fullscreen request failed:', err)
      })
      // Pointer lock verrà richiesto automaticamente da handleFullscreenChange quando fullscreen si attiva
    }
  }, [])

  const handleFullscreenChange = useCallback(() => {
    console.log('[Fullscreen] handleFullscreenChange chiamato. isMonitoring:', isMonitoringRef.current)
    
    // NON registrare eventi se il monitoraggio è fermo
    // Ma se il fullscreen esce, DOBBIAMO sempre mostrare il prompt (anche se monitoring non è ancora attivo)
    // Il check isMonitoring serve solo per evitare eventi duplicati, non per bloccare il prompt
    if (!isMonitoringRef.current) {
      console.log('[Fullscreen] Monitoraggio non ancora attivo, ma controllo comunque l\'uscita fullscreen')
      // Non ritornare early - controlla comunque se il fullscreen è uscito
    }
    
    const isNowFullscreen = !!document.fullscreenElement
    const wasFullscreenBefore = isFullscreen.current
    console.log(`[Fullscreen] Stato fullscreen: was=${wasFullscreenBefore}, now=${isNowFullscreen}, isMonitoring=${isMonitoringRef.current}`)
    
    // CRITICO: Se il fullscreen è uscito, mostra SEMPRE il prompt
    // Controlla sia isFullscreen.current che document.fullscreenElement per essere sicuri
    const fullscreenJustExited = (wasFullscreenBefore || isFullscreen.current) && !isNowFullscreen
    console.log(`[Fullscreen] fullscreenJustExited=${fullscreenJustExited}`)
    
    if (fullscreenJustExited) {
      // L'utente è uscito dal fullscreen - SEMPRE mostrare il prompt, anche se monitoring non è ancora attivo
      console.log('[Fullscreen] ⚠️ UTENTE USCITO DAL FULLSCREEN!')
      fullscreenExitCount.current++
      
      // Registra evento solo se monitoring è attivo
      if (isMonitoringRef.current) {
        const event: CheatingEvent = {
          type: 'fullscreen_exit',
          timestamp: new Date().toISOString(),
          details: `Fullscreen exit #${fullscreenExitCount.current}`,
          severity: 'high'
        }
        addEvent(event)
      }
      
      // Opzione 1: TERMINA IL COLLOQUIO
      if (config.terminateOnFullscreenExit) {
        console.log('[Fullscreen] Terminando colloquio per uscita fullscreen')
        if (config.onInterviewTerminated) {
          config.onInterviewTerminated()
        }
        return
      }
      
      // Opzione 2: Modalità moderata - mostra UI per rientrare
      // IMPORTANTE: Mostra sempre il prompt, anche se monitoring non è ancora attivo
      if (config.enforceFullscreen) {
        const maxExits = config.maxFullscreenExits || 2
        console.log(`[Fullscreen] Uscite: ${fullscreenExitCount.current}/${maxExits}`)
        if (fullscreenExitCount.current > maxExits) {
          console.log('[Fullscreen] Superato limite uscite, terminando colloquio')
          if (config.onInterviewTerminated) {
            config.onInterviewTerminated()
          }
          return
        }
        
        // Notifica l'UI che l'utente è uscito dal fullscreen - SEMPRE, anche se monitoring non è attivo
        if (config.onFullscreenExit) {
          console.log('[Fullscreen] ✅ Chiamando onFullscreenExit per mostrare prompt rosso...')
          config.onFullscreenExit()
        } else {
          console.error('[Fullscreen] ❌ onFullscreenExit non definito!')
        }
      } else {
        console.log('[Fullscreen] enforceFullscreen non attivo, skip onFullscreenExit')
      }
    }
    
    const wasFullscreen = isFullscreen.current
    
    // CRITICO: Aggiorna isFullscreen.current PRIMA di controllare l'uscita
    // Questo assicura che la condizione di uscita funzioni correttamente
    isFullscreen.current = isNowFullscreen
    console.log(`[Fullscreen] Aggiornato isFullscreen.current: ${wasFullscreen} -> ${isNowFullscreen}`)
    
    // Quando fullscreen si attiva, richiedi anche pointer lock
    if (isNowFullscreen && !wasFullscreen) {
      // Fullscreen appena attivato - richiedi pointer lock con retry automatico
      console.log('[Pointer Lock] Fullscreen attivato, richiedo pointer lock...')
      
      // Retry automatico se il pointer lock non si attiva
      let retryCount = 0
      const maxRetries = 5
      const retryInterval = 500
      
      const tryPointerLock = () => {
        if (!document.fullscreenElement || !isMonitoringRef.current) {
          console.warn('[Pointer Lock] Fullscreen non più attivo o monitoring fermato, skip pointer lock')
          return
        }
        
        // Verifica se il pointer lock è già attivo
        const isLocked = !!(
          document.pointerLockElement ||
          (document as any).webkitPointerLockElement ||
          (document as any).mozPointerLockElement
        )
        
        if (isLocked) {
          console.log('[Pointer Lock] Pointer lock già attivo, skip')
          return
        }
        
        console.log(`[Pointer Lock] Tentativo ${retryCount + 1}/${maxRetries}...`)
        requestPointerLock()
        
        // Verifica dopo un breve delay se si è attivato
        setTimeout(() => {
          const stillLocked = !!(
            document.pointerLockElement ||
            (document as any).webkitPointerLockElement ||
            (document as any).mozPointerLockElement
          )
          
          if (!stillLocked && retryCount < maxRetries - 1) {
            retryCount++
            setTimeout(tryPointerLock, retryInterval)
          } else if (!stillLocked) {
            console.error('[Pointer Lock] Impossibile attivare pointer lock dopo tutti i tentativi')
            const event: CheatingEvent = {
              type: 'pointer_lock_failed',
              timestamp: new Date().toISOString(),
              details: 'Pointer lock failed after multiple retry attempts',
              severity: 'high'
            }
            addEvent(event)
          }
        }, 200)
      }
      
      // Primo tentativo dopo un breve delay
      setTimeout(tryPointerLock, 200)
    } else if (!isNowFullscreen && wasFullscreen) {
      // Fullscreen appena disattivato - esci anche da pointer lock se attivo
      console.log('[Pointer Lock] Fullscreen disattivato, esco da pointer lock...')
      if (isPointerLockActive.current && document.exitPointerLock) {
        document.exitPointerLock()
      }
    }
  }, [addEvent, config, requestPointerLock])
  
  const handlePointerLockChange = useCallback(() => {
    // Usa il ref per avere lo stato di monitoraggio aggiornato
    if (!isMonitoringRef.current) {
      return
    }
    
    const isLocked = !!(
      document.pointerLockElement ||
      (document as any).webkitPointerLockElement ||
      (document as any).mozPointerLockElement
    )
    
    // Gestisci classe CSS per nascondere cursore sistema
    if (isLocked) {
      document.body.classList.add('pointer-locked')
      document.documentElement.classList.add('pointer-locked')
    } else {
      document.body.classList.remove('pointer-locked')
      document.documentElement.classList.remove('pointer-locked')
    }
    
    if (isPointerLockActive.current && !isLocked) {
      // Pointer lock perso
      pointerLockExitCount.current++
      
      // Assumiamo che sia sempre un'azione utente (ESC) a meno che non sia un errore browser
      // Per semplicità, trattiamo tutti gli exit come high severity (utente ha premuto ESC)
      const event: CheatingEvent = {
        type: 'pointer_lock_exit',
        timestamp: new Date().toISOString(),
        details: `Pointer lock exit #${pointerLockExitCount.current} (user pressed ESC or lock lost)`,
        severity: 'high'
      }
      addEvent(event)
      
      // Stesso comportamento di fullscreen exits
      if (config.enforceFullscreen) {
        const maxExits = config.maxFullscreenExits || 2
        if (pointerLockExitCount.current > maxExits) {
          if (config.onInterviewTerminated) {
            config.onInterviewTerminated()
          }
          return
        }
        
        // Notifica come fullscreen exit
        if (config.onFullscreenExit) {
          console.log('[Pointer Lock] Chiamando onFullscreenExit per mostrare prompt...')
          config.onFullscreenExit()
        }
      }
      
      // Se fullscreen è ancora attivo, prova a riattivare pointer lock
      if (isFullscreen.current && config.enforceFullscreen) {
        setTimeout(() => {
          if (document.fullscreenElement && !isPointerLockActive.current) {
            requestPointerLock()
          }
        }, 500)
      }
    } else if (!isPointerLockActive.current && isLocked) {
      // Pointer lock appena attivato - inizializza posizione cursore al centro
      console.log('[Pointer Lock] ✅ Pointer lock ATTIVATO con successo!')
      const centerX = window.innerWidth / 2
      const centerY = window.innerHeight / 2
      cursorPositionRef.current = { x: centerX, y: centerY }
      setCursorPosition(cursorPositionRef.current)
      console.log(`[Pointer Lock] Cursore finto inizializzato a (${centerX}, ${centerY})`)
    } else if (isPointerLockActive.current && !isLocked) {
      console.log('[Pointer Lock] ❌ Pointer lock DISATTIVATO')
      // Quando si disattiva, mantieni la posizione corrente ma nascondi il cursore finto
    }
    
    isPointerLockActive.current = isLocked
    setIsPointerLocked(isLocked) // Aggiorna lo stato per il componente FakeCursor
    console.log(`[Pointer Lock] Stato aggiornato: isPointerLocked=${isLocked}, isPointerLockActive=${isPointerLockActive.current}`)
  }, [addEvent, config, requestPointerLock])
  
  const handleMouseMove = useCallback((e: MouseEvent) => {
    // Se il pointer lock non è attivo ma dovrebbe esserlo (fullscreen attivo), riattivalo
    if (!isPointerLockActive.current && isFullscreen.current && isMonitoringRef.current) {
      const isLocked = !!(
        document.pointerLockElement ||
        (document as any).webkitPointerLockElement ||
        (document as any).mozPointerLockElement
      )
      
      if (!isLocked) {
        console.log('[Pointer Lock] Rilevato movimento mouse senza pointer lock, riattivazione...')
        requestPointerLock()
      }
      return
    }
    
    if (!isPointerLockActive.current) {
      return
    }
    
    // Usa movementX e movementY per aggiornare posizione relativa
    const newX = Math.max(0, Math.min(window.innerWidth, cursorPositionRef.current.x + e.movementX))
    const newY = Math.max(0, Math.min(window.innerHeight, cursorPositionRef.current.y + e.movementY))
    
    cursorPositionRef.current = { x: newX, y: newY }
    setCursorPosition(cursorPositionRef.current)
  }, [requestPointerLock])

  // NUOVO: Blocco tasto ESC in fullscreen
  const handleEscapeKey = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && isFullscreen.current && config.enforceFullscreen) {
      // Se il pointer lock è attivo, NON bloccare ESC (permettere uscita dal pointer lock)
      const isLocked = !!(
        document.pointerLockElement ||
        (document as any).webkitPointerLockElement ||
        (document as any).mozPointerLockElement
      )
      
      if (isLocked) {
        // Pointer lock attivo: permettere ESC per uscire dal pointer lock
        // L'uscita verrà rilevata da handlePointerLockChange che chiamerà onFullscreenExit
        return
      }
      
      // Pointer lock NON attivo: permettere ESC per uscire dal fullscreen
      // L'uscita verrà rilevata da handleFullscreenChange che chiamerà onFullscreenExit
      // NON bloccare ESC - permettere l'uscita ma registrare l'evento
      const event: CheatingEvent = {
        type: 'keyboard_shortcut',
        timestamp: new Date().toISOString(),
        details: 'ESC key pressed to exit fullscreen',
        severity: 'high'
      }
      addEvent(event)
      
      // NON chiamare preventDefault() - permettere ESC per uscire dal fullscreen
      // handleFullscreenChange rileverà l'uscita e chiamerà onFullscreenExit
    }
  }, [addEvent, config.enforceFullscreen])

  // NUOVO: Rilevamento schermi multipli (migliorato)
  const detectMultipleDisplays = useCallback((): boolean => {
    try {
      const currentScreen = {
        width: window.screen.width,
        height: window.screen.height,
        availWidth: window.screen.availWidth,
        availHeight: window.screen.availHeight
      }

      // Controllo 1: Risoluzione totale schermo molto grande (> 3000px larghezza) = probabile multi-monitor
      const isVeryWideScreen = currentScreen.width > 3000

      // Controllo 2: Differenza significativa tra screen.width e availWidth (spazio taskbar/barre)
      // Se la differenza è molto grande, potrebbe indicare multi-monitor
      const widthDiff = currentScreen.width - currentScreen.availWidth
      const heightDiff = currentScreen.height - currentScreen.availHeight
      const hasLargeDiff = widthDiff > 200 || heightDiff > 200

      // Controllo 3: Se la finestra è posizionata fuori dallo schermo disponibile, potrebbe essere su un altro monitor
      const windowLeft = window.screenX || window.screenLeft || 0
      const windowTop = window.screenY || window.screenTop || 0
      const isOutOfBounds = 
        windowLeft < -50 || 
        windowLeft > currentScreen.availWidth + 50 ||
        windowTop < -50 ||
        windowTop > currentScreen.availHeight + 50

      // Controllo 4: Rapporto screen.width / window.innerWidth > 1.5 (finestra piccola su schermo grande)
      const screenVsWindowRatio = currentScreen.width / (window.innerWidth || 1)
      const isSuspiciousRatio = screenVsWindowRatio > 1.5 && window.innerWidth > 0 && window.innerWidth < 2000

      // Controllo 5: Cambiamento improvviso di risoluzione (indicatore di connessione/disconnessione monitor)
      let hasResolutionChange = false
      if (lastScreenCheck.current) {
        const widthChanged = Math.abs(currentScreen.width - lastScreenCheck.current.width) > 100
        const heightChanged = Math.abs(currentScreen.height - lastScreenCheck.current.height) > 100
        
        if (widthChanged || heightChanged) {
          hasResolutionChange = true
        }
      }

      // Se almeno due controlli sono positivi, c'è un doppio schermo (per ridurre falsi positivi)
      const checks = [isVeryWideScreen, hasLargeDiff, isOutOfBounds, isSuspiciousRatio, hasResolutionChange]
      const positiveChecks = checks.filter(Boolean).length
      const hasMultipleDisplays = positiveChecks >= 2

      lastScreenCheck.current = currentScreen

      return hasMultipleDisplays
    } catch (error) {
      console.error('Error detecting multiple displays:', error)
      return false
    }
  }, [])

  // Funzione per il controllo periodico durante il colloquio
  const checkMultipleDisplaysPeriodic = useCallback(() => {
    const hasMultipleDisplays = detectMultipleDisplays()
    
    if (hasMultipleDisplays) {
      multipleDisplayCount.current++
      
      const event: CheatingEvent = {
        type: 'multiple_display',
        timestamp: new Date().toISOString(),
        details: `Multiple display detected (check #${multipleDisplayCount.current})`,
        severity: 'high'
      }
      addEvent(event)
      
      // Chiama la callback per bloccare l'interfaccia se non è già bloccata
      if (!multipleDisplayBlocked.current && config.onMultipleDisplayDetected) {
        multipleDisplayBlocked.current = true
        config.onMultipleDisplayDetected()
      }
    } else {
      // Se non è più rilevato, resetta il flag per permettere nuove chiamate
      multipleDisplayBlocked.current = false
    }
  }, [detectMultipleDisplays, addEvent, config])

  // Funzione esportata per controllo esterno (prima dell'avvio)
  const checkMultipleDisplays = useCallback((): boolean => {
    return detectMultipleDisplays()
  }, [detectMultipleDisplays])

  const startMonitoring = useCallback(() => {
    // Rimuovi eventuali listener precedenti prima di aggiungerne di nuovi
    if (cleanupRef.current) {
      cleanupRef.current()
      cleanupRef.current = null
    }
    
    setIsMonitoring(true)
    isMonitoringRef.current = true
    
    // Document events
    document.addEventListener('visibilitychange', handleVisibilityChange)
    document.addEventListener('contextmenu', handleContextMenu)
    document.addEventListener('copy', handleCopyPaste)
    document.addEventListener('paste', handleCopyPaste)
    document.addEventListener('cut', handleCopyPaste)
    document.addEventListener('keydown', handleKeyboardShortcuts)
    
    // NUOVO: Screenshot e fullscreen protection
    document.addEventListener('keydown', handleScreenshotAttempt, true) // capture phase
    document.addEventListener('keydown', handleEscapeKey, true)
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    
    // Pointer Lock API events
    document.addEventListener('pointerlockchange', handlePointerLockChange)
    document.addEventListener('webkitpointerlockchange', handlePointerLockChange)
    document.addEventListener('mozpointerlockchange', handlePointerLockChange)
    document.addEventListener('mousemove', handleMouseMove)
    
    // Window events
    window.addEventListener('blur', handleWindowBlur)
    window.addEventListener('focus', handleWindowFocus)
    window.addEventListener('resize', handleResize)
    
    // Dev tools detection interval
    const devToolsInterval = setInterval(detectDevTools, 1000)
    
    // NUOVO: Monitoraggio schermi multipli ogni 90 secondi
    const multipleDisplayInterval = setInterval(checkMultipleDisplaysPeriodic, 90000)
    
    // NUOVO: Monitoraggio continuo del pointer lock - verifica ogni 2 secondi se è ancora attivo
    const pointerLockMonitor = setInterval(() => {
      if (isFullscreen.current && isMonitoringRef.current && config.enforceFullscreen) {
        const isLocked = !!(
          document.pointerLockElement ||
          (document as any).webkitPointerLockElement ||
          (document as any).mozPointerLockElement
        )
        
        if (!isLocked && !isPointerLockActive.current) {
          // Pointer lock non attivo ma dovrebbe esserlo - riattivalo
          console.log('[Pointer Lock] Monitor: pointer lock perso, riattivazione...')
          requestPointerLock()
        }
      }
    }, 2000) // Controlla ogni 2 secondi
    
    // NUOVO: Se enforceFullscreen è attivo, richiedi fullscreen all'inizio
    if (config.enforceFullscreen) {
      setTimeout(() => {
        requestFullscreen()
      }, 500)
    }
    
    // Salva la funzione di cleanup
    const cleanup = () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      document.removeEventListener('contextmenu', handleContextMenu)
      document.removeEventListener('copy', handleCopyPaste)
      document.removeEventListener('paste', handleCopyPaste)
      document.removeEventListener('cut', handleCopyPaste)
      document.removeEventListener('keydown', handleKeyboardShortcuts)
      
      // NUOVO: Cleanup screenshot e fullscreen
      document.removeEventListener('keydown', handleScreenshotAttempt, true)
      document.removeEventListener('keydown', handleEscapeKey, true)
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      
      // Cleanup Pointer Lock events
      document.removeEventListener('pointerlockchange', handlePointerLockChange)
      document.removeEventListener('webkitpointerlockchange', handlePointerLockChange)
      document.removeEventListener('mozpointerlockchange', handlePointerLockChange)
      document.removeEventListener('mousemove', handleMouseMove)
      
      // Exit pointer lock if active
      if (isPointerLockActive.current && document.exitPointerLock) {
        document.exitPointerLock()
      }
      
      window.removeEventListener('blur', handleWindowBlur)
      window.removeEventListener('focus', handleWindowFocus)
      window.removeEventListener('resize', handleResize)
      
      clearInterval(devToolsInterval)
      clearInterval(multipleDisplayInterval)
      clearInterval(pointerLockMonitor)
    }
    
    cleanupRef.current = cleanup
    return cleanup
  }, [
    handleVisibilityChange,
    handleContextMenu,
    handleCopyPaste,
    handleKeyboardShortcuts,
    handleWindowBlur,
    handleWindowFocus,
    handleResize,
    detectDevTools,
    handleScreenshotAttempt,
    handleEscapeKey,
    handleFullscreenChange,
    handlePointerLockChange,
    handleMouseMove,
    requestFullscreen,
    config.enforceFullscreen,
    checkMultipleDisplaysPeriodic
  ])

  const stopMonitoring = useCallback(() => {
    console.log('[Pointer Lock] stopMonitoring chiamato - disattivo pointer lock')
    setIsMonitoring(false)
    isMonitoringRef.current = false
    
    // Rimuovi classe CSS pointer-locked
    document.body.classList.remove('pointer-locked')
    document.documentElement.classList.remove('pointer-locked')
    
    // Exit pointer lock se attivo (importante quando il colloquio è completato)
    if (isPointerLockActive.current) {
      console.log('[Pointer Lock] Disattivo pointer lock perché monitoring fermato')
      if (document.exitPointerLock) {
        try {
          const result = document.exitPointerLock() as any
          // Alcuni browser restituiscono una Promise, altri void
          if (result && typeof result.then === 'function') {
            result.then(() => {
              console.log('[Pointer Lock] Pointer lock disattivato con successo')
            }).catch(() => {
              // Ignora errori se pointer lock non è attivo
            })
          } else {
            console.log('[Pointer Lock] Pointer lock disattivato (sincrono)')
          }
        } catch (err) {
          // Ignora errori se pointer lock non è attivo
          console.log('[Pointer Lock] Errore disattivazione pointer lock (ignorato):', err)
        }
      } else if ((document as any).webkitExitPointerLock) {
        (document as any).webkitExitPointerLock()
      } else if ((document as any).mozExitPointerLock) {
        (document as any).mozExitPointerLock()
      }
      isPointerLockActive.current = false
      setIsPointerLocked(false)
    }
    
    // Invia eventuali eventi rimasti nel buffer
    if (eventBuffer.current.length > 0) {
      const eventsToSend = [...eventBuffer.current]
      eventBuffer.current = []
      sendEventBatch(eventsToSend)
    }
    
    // Pulisci timeout batch
    if (batchTimeoutRef.current) {
      clearTimeout(batchTimeoutRef.current)
      batchTimeoutRef.current = null
    }
    
    // Rimuovi tutti gli event listener
    if (cleanupRef.current) {
      cleanupRef.current()
      cleanupRef.current = null
    }
  }, [sendEventBatch])

  const resetCounters = useCallback(() => {
    tabSwitchCount.current = 0
    copyPasteCount.current = 0
    rightClickCount.current = 0
    windowResizeCount.current = 0
    setEvents([])
    setWarnings(0)
    setIsBlocked(false)
  }, [])

  const getCheatingScore = useCallback(() => {
    let score = 0
    events.forEach(event => {
      switch (event.severity) {
        case 'high': score += 10; break
        case 'medium': score += 5; break
        case 'low': score += 1; break
      }
    })
    return score
  }, [events])

  const getCheatingSummary = useCallback(() => {
    const summary = {
      totalEvents: events.length,
      tabSwitches: tabSwitchCount.current,
      copyPasteAttempts: copyPasteCount.current,
      rightClicks: rightClickCount.current,
      windowResizes: windowResizeCount.current,
      warnings: warnings,
      isBlocked: isBlocked,
      cheatingScore: getCheatingScore(),
      highSeverityEvents: events.filter(e => e.severity === 'high').length,
      mediumSeverityEvents: events.filter(e => e.severity === 'medium').length,
      lowSeverityEvents: events.filter(e => e.severity === 'low').length
    }
    return summary
  }, [events, warnings, isBlocked, getCheatingScore])

  const resetMultipleDisplayBlock = useCallback(() => {
    multipleDisplayBlocked.current = false
  }, [])

  return {
    events,
    isMonitoring,
    warnings,
    isBlocked,
    cursorPosition,
    isPointerLocked,
    startMonitoring,
    stopMonitoring,
    resetCounters,
    getCheatingScore,
    getCheatingSummary,
    reenterFullscreen: requestFullscreen,
    requestPointerLock,
    checkMultipleDisplays,
    resetMultipleDisplayBlock
  }
}
