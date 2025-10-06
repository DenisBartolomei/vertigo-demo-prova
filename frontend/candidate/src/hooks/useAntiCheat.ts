import { useState, useEffect, useCallback, useRef } from 'react'

interface CheatingEvent {
  type: 'tab_switch' | 'copy_paste' | 'right_click' | 'devtools' | 'keyboard_shortcut' | 'focus_loss' | 'window_resize'
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
  onCheatingDetected: (event: CheatingEvent) => void
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

  const addEvent = useCallback((event: CheatingEvent) => {
    setEvents(prev => [...prev, event])
    config.onCheatingDetected(event)
    
    // Check if we should show warning or block
    if (event.severity === 'high') {
      setWarnings(prev => {
        const newWarnings = prev + 1
        if (newWarnings >= config.warningThreshold) {
          setIsBlocked(true)
        }
        return newWarnings
      })
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

  const startMonitoring = useCallback(() => {
    setIsMonitoring(true)
    
    // Document events
    document.addEventListener('visibilitychange', handleVisibilityChange)
    document.addEventListener('contextmenu', handleContextMenu)
    document.addEventListener('copy', handleCopyPaste)
    document.addEventListener('paste', handleCopyPaste)
    document.addEventListener('cut', handleCopyPaste)
    document.addEventListener('keydown', handleKeyboardShortcuts)
    
    // Window events
    window.addEventListener('blur', handleWindowBlur)
    window.addEventListener('focus', handleWindowFocus)
    window.addEventListener('resize', handleResize)
    
    // Dev tools detection interval
    const devToolsInterval = setInterval(detectDevTools, 1000)
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      document.removeEventListener('contextmenu', handleContextMenu)
      document.removeEventListener('copy', handleCopyPaste)
      document.removeEventListener('paste', handleCopyPaste)
      document.removeEventListener('cut', handleCopyPaste)
      document.removeEventListener('keydown', handleKeyboardShortcuts)
      
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
    detectDevTools
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
    getCheatingSummary
  }
}
