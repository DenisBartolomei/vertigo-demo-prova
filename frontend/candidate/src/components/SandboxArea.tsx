import React from 'react'

interface SandboxAreaProps {
  input: string
  setInput: (value: string) => void
  onSend: () => void
  loading: boolean
  isListening: boolean
  onVoiceToggle: () => void
  isSpeechSupported: boolean
  speechError: string | null
  isStarted: boolean
  isCompleted: boolean
}

export function SandboxArea({
  input,
  setInput,
  onSend,
  loading,
  isListening,
  onVoiceToggle,
  isSpeechSupported,
  speechError,
  isStarted,
  isCompleted
}: SandboxAreaProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  if (!isStarted || isCompleted) {
    return (
      <div className="sandbox-area">
        <div className="sandbox-header">
          <h2 className="sandbox-title">Answer here</h2>
        </div>
        <div className="sandbox-content">
          <div className="input-sandbox">
            <h3>Ready to start</h3>
            <div style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-muted)',
              fontSize: '16px',
              textAlign: 'center',
              padding: '40px 20px'
            }}>
              {isCompleted 
                ? '🎉 Interview completed successfully!'
                : '👋 Start the interview to use this area'
              }
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="sandbox-area">
      <div className="sandbox-header">
        <h2 className="sandbox-title">Your Answer</h2>
      </div>
      
      <div className="sandbox-content">
        {/* Speech error display */}
        {speechError && (
          <div style={{
            backgroundColor: '#f8d7da',
            border: '1px solid #f5c6cb',
            borderRadius: '8px',
            padding: '8px 12px',
            fontSize: '14px',
            color: '#721c24'
          }}>
            ⚠️ {speechError}
          </div>
        )}
        
        <div className="input-sandbox">
          <h3>Write or speak your answer</h3>
          
          <textarea
            className="sandbox-textarea"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Write or speak your answer here... (Press Enter to send, Shift+Enter for new line, or use 🎤 for voice input)"
            disabled={loading}
          />
          
          <div className="sandbox-controls">
            {/* Voice input button */}
            {isSpeechSupported && (
              <button
                className={`voice-button ${isListening ? 'listening' : ''}`}
                onClick={onVoiceToggle}
                disabled={loading}
                style={{
                  background: isListening 
                    ? 'linear-gradient(135deg, #ff6b6b, #ee5a52)' 
                    : 'linear-gradient(135deg, var(--primary-purple), var(--accent-purple))',
                  border: 'none',
                  borderRadius: '50%',
                  width: '40px',
                  height: '40px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '16px',
                  color: 'white',
                  transition: 'all 0.3s ease',
                  animation: isListening ? 'pulse 1.5s infinite' : 'none',
                  boxShadow: isListening 
                    ? '0 0 20px rgba(255, 107, 107, 0.5)' 
                    : '0 2px 8px rgba(0,0,0,0.1)',
                  flexShrink: 0
                }}
                title={isListening ? 'Stop voice input' : 'Start voice input'}
              >
                {isListening ? '⏹️' : '🎤'}
              </button>
            )}
            
            <button 
              className="sandbox-send-button"
              onClick={onSend} 
              disabled={loading || !input.trim()}
            >
              {loading ? '⏳ Sending...' : '➤ Send Answer'}
            </button>
          </div>
          
          {/* Voice input status */}
          {isListening && (
            <div style={{
              textAlign: 'center',
              padding: '8px 16px',
              fontSize: '14px',
              color: 'var(--primary-purple)',
              fontWeight: '500',
              backgroundColor: 'rgba(139, 69, 255, 0.1)',
              borderRadius: '8px',
              border: '1px solid rgba(139, 69, 255, 0.2)',
              marginTop: '12px'
            }}>
              🎤 Listening... Speak now
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
