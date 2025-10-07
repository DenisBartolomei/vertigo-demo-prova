import React, { useState } from 'react'

interface InterviewIntroProps {
  positionName: string
  candidateName: string
  onStart: () => void
  onAcceptTerms: () => void
  loading?: boolean
}

export function InterviewIntro({ positionName, candidateName, onStart, onAcceptTerms, loading = false }: InterviewIntroProps) {
  const [acceptedTerms, setAcceptedTerms] = useState(false)
  const [showSecurityDetails, setShowSecurityDetails] = useState(false)

  const handleStart = () => {
    if (acceptedTerms && !loading) {
      onStart()
    }
  }

  return (
    <div className="interview-intro">
      <div className="intro-header">
        <div className="intro-icon">🎯</div>
        <h1 className="intro-title">Welcome to Your Interview</h1>
        <p className="intro-subtitle">
          {candidateName}, you're about to begin your interview for the <strong>{positionName}</strong> position.
        </p>
      </div>

      <div className="intro-content">
        <div className="intro-section">
          <h3>📋 Interview Guidelines</h3>
          <ul>
            <li>This is a written interview that will assess your skills and experience</li>
            <li>Take your time to provide thoughtful, detailed answers</li>
            <li>There's no time limit, but aim to be thorough yet concise</li>
            <li>Answer based on your actual experience and knowledge</li>
            <li>Feel free to ask questions if you need clarification</li>
          </ul>
        </div>

        <div className="intro-section security-section">
          <h3>🔒 Security Measures</h3>
          <p>
            To ensure the integrity of the interview process, we have implemented several security measures:
          </p>
          
          {!showSecurityDetails ? (
            <button 
              className="security-toggle"
              onClick={() => setShowSecurityDetails(true)}
            >
              View Security Details
            </button>
          ) : (
            <div className="security-details">
              <div className="security-warning">
                <strong>⚠️ IMPORTANT:</strong> All activities during this interview are monitored and recorded.
              </div>
              
              <h4>What We Monitor:</h4>
              <ul className="security-list">
                <li><strong>Tab Switching:</strong> Switching to other browser tabs or applications</li>
                <li><strong>Copy/Paste:</strong> Attempts to copy content from or paste content into the interview</li>
                <li><strong>Keyboard Shortcuts:</strong> Use of shortcuts like Ctrl+C, Ctrl+V, F12, etc.</li>
                <li><strong>Right-Click:</strong> Right-clicking on the interview interface</li>
                <li><strong>Developer Tools:</strong> Attempts to open browser developer tools</li>
                <li><strong>Window Focus:</strong> Loss of focus from the interview window</li>
                <li><strong>Screen Activity:</strong> General interaction patterns and timing</li>
              </ul>

              <h4>Consequences:</h4>
              <ul className="consequences-list">
                <li>First violation: Warning notification</li>
                <li>Multiple violations: Temporary interview block</li>
                <li>Severe violations: Interview termination</li>
                <li>All violations are recorded and included in your evaluation report</li>
              </ul>

              <div className="security-note">
                <strong>Note:</strong> These measures are in place to ensure fairness for all candidates and maintain the integrity of our evaluation process.
              </div>
            </div>
          )}
        </div>

        <div className="intro-section">
          <h3>✅ Terms and Conditions</h3>
          <div className="terms-box">
            <p>
              By proceeding with this interview, you acknowledge and agree to:
            </p>
            <ul>
              <li>Answer all questions honestly and based on your own knowledge</li>
              <li>Not use external resources, tools, or assistance during the interview</li>
              <li>Not share interview content with others</li>
              <li>Accept that all activities are monitored and recorded</li>
              <li>Understand that violations may affect your evaluation results</li>
            </ul>
          </div>
          
          <label className="terms-checkbox">
            <input 
              type="checkbox" 
              checked={acceptedTerms}
              onChange={(e) => setAcceptedTerms(e.target.checked)}
            />
            <span>I have read, understood, and agree to the terms and conditions above</span>
          </label>
        </div>
      </div>

      <div className="intro-actions">
      <button 
          className={`start-button ${!acceptedTerms || loading ? 'disabled' : ''}`}
          onClick={handleStart}
          disabled={!acceptedTerms || loading}
        >
          {loading ? '⏳ Avvio in corso...' : acceptedTerms ? '🚀 Inizia Colloquio' : '⚠️ Accetta Termini per Continuare'}
        </button>
      </div>

      <div className="intro-footer">
        <p>
          <strong>Need help?</strong> If you experience any technical issues, please contact our support team.
        </p>
      </div>
    </div>
  )
}
