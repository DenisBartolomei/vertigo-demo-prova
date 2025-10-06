import React, { useState, useEffect } from 'react'

interface AntiCheatWarningProps {
  warningCount: number
  isBlocked: boolean
  onAccept: () => void
  onContinue: () => void
}

export function AntiCheatWarning({ warningCount, isBlocked, onAccept, onContinue }: AntiCheatWarningProps) {
  const [showWarning, setShowWarning] = useState(false)
  const [countdown, setCountdown] = useState(5)

  useEffect(() => {
    if (warningCount > 0) {
      setShowWarning(true)
      setCountdown(5)
      
      const timer = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            clearInterval(timer)
            return 0
          }
          return prev - 1
        })
      }, 1000)

      return () => clearInterval(timer)
    }
  }, [warningCount])

  const handleAccept = () => {
    setShowWarning(false)
    onAccept()
  }

  const handleContinue = () => {
    setShowWarning(false)
    onContinue()
  }

  if (!showWarning && !isBlocked) return null

  if (isBlocked) {
    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.9)',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        <div style={{
          backgroundColor: '#1a1a1a',
          padding: '40px',
          borderRadius: '12px',
          textAlign: 'center',
          maxWidth: '500px',
          border: '2px solid #ff4444'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '20px' }}>🚫</div>
          <h2 style={{ color: '#ff4444', marginBottom: '16px' }}>
            Interview Blocked
          </h2>
          <p style={{ marginBottom: '20px', lineHeight: '1.5' }}>
            Multiple suspicious activities have been detected. The interview has been temporarily blocked for security reasons.
          </p>
          <p style={{ fontSize: '14px', color: '#888', marginBottom: '24px' }}>
            All activities have been recorded and will be included in your evaluation report.
          </p>
          <button
            onClick={handleAccept}
            style={{
              backgroundColor: '#ff4444',
              color: 'white',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '6px',
              fontSize: '16px',
              cursor: 'pointer',
              fontWeight: '500'
            }}
          >
            I Understand
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      zIndex: 10000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: 'white',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      <div style={{
        backgroundColor: '#1a1a1a',
        padding: '40px',
        borderRadius: '12px',
        textAlign: 'center',
        maxWidth: '500px',
        border: '2px solid #ffa500'
      }}>
        <div style={{ fontSize: '48px', marginBottom: '20px' }}>⚠️</div>
        <h2 style={{ color: '#ffa500', marginBottom: '16px' }}>
          Security Warning
        </h2>
        <p style={{ marginBottom: '20px', lineHeight: '1.5' }}>
          Suspicious activity detected. Please focus on the interview and avoid:
        </p>
        <ul style={{ 
          textAlign: 'left', 
          marginBottom: '20px',
          paddingLeft: '20px',
          lineHeight: '1.6'
        }}>
          <li>Switching tabs or windows</li>
          <li>Copying and pasting content</li>
          <li>Using keyboard shortcuts</li>
          <li>Right-clicking on the page</li>
          <li>Opening developer tools</li>
        </ul>
        <p style={{ fontSize: '14px', color: '#888', marginBottom: '24px' }}>
          All activities are being monitored and recorded. Continued violations may result in interview termination.
        </p>
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
          <button
            onClick={handleAccept}
            style={{
              backgroundColor: '#ffa500',
              color: 'white',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '6px',
              fontSize: '16px',
              cursor: 'pointer',
              fontWeight: '500'
            }}
          >
            I Understand
          </button>
          <button
            onClick={handleContinue}
            style={{
              backgroundColor: '#333',
              color: 'white',
              border: '1px solid #666',
              padding: '12px 24px',
              borderRadius: '6px',
              fontSize: '16px',
              cursor: 'pointer',
              fontWeight: '500'
            }}
          >
            Continue Interview
          </button>
        </div>
        {countdown > 0 && (
          <p style={{ 
            marginTop: '16px', 
            fontSize: '14px', 
            color: '#888' 
          }}>
            Auto-continue in {countdown} seconds
          </p>
        )}
      </div>
    </div>
  )
}
