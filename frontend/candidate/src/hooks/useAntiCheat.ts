import { useState, useEffect, useCallback, useRef } from 'react'

interface CheatingEvent {
  type: 'tab_switch' | 'copy_paste' | 'right_click' | 'devtools' | 'keyboard_shortcut' | 'focus_loss' | 'window_resize' | 'screenshot_attempt' | 'fullscreen_exit' | 'print_attempt'
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
}

export function useAntiCheat(config: AntiCheatConfig) {
  const [events, setEvents] = useState<CheatingEvent[]>([])
  const [isMonitoring, setIsMonitoring] = useState(false)
  const [warnings, setWarnings] = useState(0)
  const [isBlocked, setIsBlocked] = useState(false)
  
  const tabSwitchCount = useRef(0)
  const copyPasteCount = useRef(0)
  const rightClickCount = useRef(0)
  const windowResizeCount = useRef(0)
  const lastFocusTime = useRef(Date.now())
  const isVisible = useRef(true)
  const fullscreenExitCount = useRef(0)
  const isFullscreen = useRef(false)
  const screenshotAttemptCount = useRef(0)

  const addEvent = useCallback((event: CheatingEvent) => {
    setEvents(prev => [...prev, event])
    config.onCheatingDetected(event)
    
    // Just track warnings, don't block interview
    if (event.severity === 'high') {
      setWarnings(prev => prev + 1)
    }
  }, [config])

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
        alert('⚠️ ATTENZIONE: Il tentativo di screenshot è stato rilevato e registrato nel report di valutazione.')
        return true
      }
    }
    return false
  }, [addEvent])

  // NUOVO: Fullscreen enforcement
  const requestFullscreen = useCallback(() => {
    const elem = document.documentElement
    if (elem.requestFullscreen) {
      elem.requestFullscreen().catch(err => {
        console.error('Fullscreen request failed:', err)
      })
    }
  }, [])

  const handleFullscreenChange = useCallback(() => {
    const isNowFullscreen = !!document.fullscreenElement
    
    if (isFullscreen.current && !isNowFullscreen) {
      // L'utente è uscito dal fullscreen
      fullscreenExitCount.current++
      
      const event: CheatingEvent = {
        type: 'fullscreen_exit',
        timestamp: new Date().toISOString(),
        details: `Fullscreen exit #${fullscreenExitCount.current}`,
        severity: 'high'
      }
      addEvent(event)
      
      // Opzione 1: TERMINA IL COLLOQUIO
      if (config.terminateOnFullscreenExit) {
        if (config.onInterviewTerminated) {
          config.onInterviewTerminated()
        }
        return
      }
      
      // Opzione 2: Modalità moderata - mostra UI per rientrare
      if (config.enforceFullscreen) {
        const maxExits = config.maxFullscreenExits || 2
        if (fullscreenExitCount.current > maxExits) {
          if (config.onInterviewTerminated) {
            config.onInterviewTerminated()
          }
          return
        }
        
        // Notifica l'UI che l'utente è uscito dal fullscreen
        if (config.onFullscreenExit) {
          config.onFullscreenExit()
        }
      }
    }
    
    isFullscreen.current = isNowFullscreen
  }, [addEvent, config])

  // NUOVO: Blocco tasto ESC in fullscreen
  const handleEscapeKey = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && isFullscreen.current && config.enforceFullscreen) {
      e.preventDefault()
      e.stopPropagation()
      
      const event: CheatingEvent = {
        type: 'keyboard_shortcut',
        timestamp: new Date().toISOString(),
        details: 'Blocked ESC key in fullscreen mode',
        severity: 'medium'
      }
      addEvent(event)
      
      return false
    }
  }, [addEvent, config.enforceFullscreen])

  const startMonitoring = useCallback(() => {
    setIsMonitoring(true)
    
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
    
    // Window events
    window.addEventListener('blur', handleWindowBlur)
    window.addEventListener('focus', handleWindowFocus)
    window.addEventListener('resize', handleResize)
    
    // Dev tools detection interval
    const devToolsInterval = setInterval(detectDevTools, 1000)
    
    // NUOVO: Se enforceFullscreen è attivo, richiedi fullscreen all'inizio
    if (config.enforceFullscreen) {
      setTimeout(() => {
        requestFullscreen()
      }, 500)
    }
    
    return () => {
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
      
      window.removeEventListener('blur', handleWindowBlur)
      window.removeEventListener('focus', handleWindowFocus)
      window.removeEventListener('resize', handleResize)
      
      clearInterval(devToolsInterval)
    }
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
    requestFullscreen,
    config.enforceFullscreen
  ])

  const stopMonitoring = useCallback(() => {
    setIsMonitoring(false)
  }, [])

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

  return {
    events,
    isMonitoring,
    warnings,
    isBlocked,
    startMonitoring,
    stopMonitoring,
    resetCounters,
    getCheatingScore,
    getCheatingSummary,
    reenterFullscreen: requestFullscreen
  }
}
