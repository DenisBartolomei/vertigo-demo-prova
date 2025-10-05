import { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'
const CANDIDATE_BASE = import.meta.env.VITE_CANDIDATE_BASE || 'http://localhost:3001'

export function Sessions() {
  const [positionId, setPositionId] = useState('')
  const [candidateName, setCandidateName] = useState('')
  const [candidateEmail, setCandidateEmail] = useState('')
  const [cvFile, setCvFile] = useState<File | null>(null)
  const [result, setResult] = useState<any | null>(null)
  const token = localStorage.getItem('hr_jwt')

  async function createSession() {
    if (!cvFile) return
    const formData = new FormData()
    formData.append('position_id', positionId)
    formData.append('candidate_name', candidateName)
    formData.append('candidate_email', candidateEmail)
    formData.append('frontend_base_url', CANDIDATE_BASE)
    formData.append('cv_file', cvFile)
    const resp = await fetch(`${API_BASE}/sessions`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: formData })
    const data = await resp.json()
    setResult(data)
  }

  async function prepareSession() {
    if (!result?.session_id) return
    await fetch(`${API_BASE}/sessions/${result.session_id}/prepare`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } })
    alert('Preparation started')
  }

  return (
    <div style={{ display: 'grid', gap: 16, maxWidth: 640 }}>
      <h2>Sessions</h2>
      <input placeholder="Position ID" value={positionId} onChange={e => setPositionId(e.target.value)} />
      <input placeholder="Candidate name" value={candidateName} onChange={e => setCandidateName(e.target.value)} />
      <input placeholder="Candidate email" value={candidateEmail} onChange={e => setCandidateEmail(e.target.value)} />
      <input type="file" accept=".pdf,.txt" onChange={e => setCvFile(e.target.files?.[0] || null)} />
      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={createSession}>Create session & invite</button>
        <button onClick={prepareSession} disabled={!result?.session_id}>Prepare session</button>
      </div>
      {result && (
        <div style={{ border: '1px solid #eee', padding: 12, borderRadius: 8 }}>
          <div>session_id: {result.session_id}</div>
          <div>interview_token: {result.interview_token}</div>
          <div>candidate link: {CANDIDATE_BASE}/interview/{result.interview_token}</div>
        </div>
      )}
    </div>
  )
}


