import { useEffect, useState } from 'react'
import { FileText, User, Mail, Upload, Play, Copy, CheckCircle2 } from 'lucide-react'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Card, CardHeader, CardBody } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://vertigo-ai-backend-tbia7kjh7a-oc.a.run.app'
const CANDIDATE_BASE = import.meta.env.VITE_CANDIDATE_BASE || 'http://localhost:3001'

export function Sessions() {
  const [positionId, setPositionId] = useState('')
  const [candidateName, setCandidateName] = useState('')
  const [candidateEmail, setCandidateEmail] = useState('')
  const [cvFile, setCvFile] = useState<File | null>(null)
  const [result, setResult] = useState<any | null>(null)
  const [copied, setCopied] = useState(false)
  const token = localStorage.getItem('hr_jwt')

  async function createSession() {
    if (!cvFile) {
      alert('Seleziona un file CV')
      return
    }
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
    alert('Preparazione avviata')
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="container" style={{ display: 'grid', gap: '32px', maxWidth: '800px' }}>
      <div>
        <h2>Nuove Sessioni</h2>
        <p className="muted">Crea una nuova sessione di colloquio per un candidato caricando il suo CV.</p>
      </div>

      <Card>
        <CardHeader>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #7C3AED 0%, #EC4899 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white'
            }}>
              <FileText size={20} />
            </div>
            <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '600' }}>Crea Nuova Sessione</h3>
          </div>
        </CardHeader>
        <CardBody>
          <div style={{ display: 'grid', gap: '20px' }}>
            <Input
              label="ID Posizione"
              placeholder="es. senior-dev-2024"
              value={positionId}
              onChange={e => setPositionId(e.target.value)}
              leftIcon={<FileText size={18} />}
              fullWidth
            />
            
            <Input
              label="Nome Candidato"
              placeholder="Mario Rossi"
              value={candidateName}
              onChange={e => setCandidateName(e.target.value)}
              leftIcon={<User size={18} />}
              fullWidth
            />
            
            <Input
              type="email"
              label="Email Candidato"
              placeholder="mario.rossi@email.com"
              value={candidateEmail}
              onChange={e => setCandidateEmail(e.target.value)}
              leftIcon={<Mail size={18} />}
              fullWidth
            />
            
            <div>
              <label style={{
                display: 'block',
                fontSize: '14px',
                fontWeight: '500',
                color: '#1F2937',
                marginBottom: '8px'
              }}>
                File CV (PDF o TXT)
              </label>
              <div style={{
                border: '2px dashed #E5E7EB',
                borderRadius: '8px',
                padding: '24px',
                textAlign: 'center',
                background: cvFile ? '#F5F3FF' : '#FAFAFA',
                transition: 'all 0.2s ease',
                cursor: 'pointer'
              }}
              onDragOver={(e) => {
                e.preventDefault()
                e.currentTarget.style.borderColor = '#7C3AED'
                e.currentTarget.style.background = '#F5F3FF'
              }}
              onDragLeave={(e) => {
                e.currentTarget.style.borderColor = '#E5E7EB'
                e.currentTarget.style.background = cvFile ? '#F5F3FF' : '#FAFAFA'
              }}
              onDrop={(e) => {
                e.preventDefault()
                const file = e.dataTransfer.files[0]
                if (file && (file.type === 'application/pdf' || file.type === 'text/plain')) {
                  setCvFile(file)
                }
                e.currentTarget.style.borderColor = '#E5E7EB'
                e.currentTarget.style.background = '#F5F3FF'
              }}
              onClick={() => {
                const input = document.createElement('input')
                input.type = 'file'
                input.accept = '.pdf,.txt'
                input.onchange = (e: any) => {
                  const file = e.target.files?.[0]
                  if (file) setCvFile(file)
                }
                input.click()
              }}
              >
                {cvFile ? (
                  <div>
                    <Upload size={32} color="#7C3AED" style={{ marginBottom: '8px' }} />
                    <div style={{ fontWeight: '600', color: '#7C3AED', marginBottom: '4px' }}>
                      {cvFile.name}
                    </div>
                    <div style={{ fontSize: '12px', color: '#6B7280' }}>
                      Clicca per selezionare un altro file
                    </div>
                  </div>
                ) : (
                  <div>
                    <Upload size={32} color="#9CA3AF" style={{ marginBottom: '8px' }} />
                    <div style={{ fontWeight: '500', color: '#6B7280', marginBottom: '4px' }}>
                      Trascina il file qui o clicca per selezionare
                    </div>
                    <div style={{ fontSize: '12px', color: '#9CA3AF' }}>
                      PDF o TXT fino a 10MB
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <div style={{ display: 'flex', gap: '12px' }}>
              <Button
                onClick={createSession}
                variant="primary"
                size="lg"
                leftIcon={<Upload size={18} />}
                style={{ flex: 1 }}
                disabled={!positionId || !candidateName || !candidateEmail || !cvFile}
              >
                Crea Sessione & Invita
              </Button>
              {result?.session_id && (
                <Button
                  onClick={prepareSession}
                  variant="secondary"
                  size="lg"
                  leftIcon={<Play size={18} />}
                >
                  Prepara Sessione
                </Button>
              )}
            </div>
          </div>
        </CardBody>
      </Card>

      {result && (
        <Card style={{
          border: '2px solid #7C3AED',
          background: 'linear-gradient(135deg, rgba(124, 58, 237, 0.05), rgba(236, 72, 153, 0.05))'
        }}>
          <CardHeader>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <CheckCircle2 size={24} color="#10B981" />
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '600' }}>Sessione Creata</h3>
            </div>
          </CardHeader>
          <CardBody>
            <div style={{ display: 'grid', gap: '16px' }}>
              <div>
                <div style={{
                  fontSize: '12px',
                  fontWeight: '600',
                  color: '#6B7280',
                  textTransform: 'uppercase',
                  marginBottom: '4px'
                }}>
                  Session ID
                </div>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '12px',
                  background: 'white',
                  borderRadius: '8px',
                  border: '1px solid #E5E7EB'
                }}>
                  <code style={{ flex: 1, fontSize: '14px', color: '#1F2937' }}>
                    {result.session_id}
                  </code>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(result.session_id)}
                    leftIcon={copied ? <CheckCircle2 size={16} /> : <Copy size={16} />}
                  >
                    {copied ? 'Copiato!' : 'Copia'}
                  </Button>
                </div>
              </div>

              <div>
                <div style={{
                  fontSize: '12px',
                  fontWeight: '600',
                  color: '#6B7280',
                  textTransform: 'uppercase',
                  marginBottom: '4px'
                }}>
                  Interview Token
                </div>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '12px',
                  background: 'white',
                  borderRadius: '8px',
                  border: '1px solid #E5E7EB'
                }}>
                  <code style={{ flex: 1, fontSize: '14px', color: '#1F2937' }}>
                    {result.interview_token}
                  </code>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(result.interview_token)}
                    leftIcon={copied ? <CheckCircle2 size={16} /> : <Copy size={16} />}
                  >
                    {copied ? 'Copiato!' : 'Copia'}
                  </Button>
                </div>
              </div>

              <div>
                <div style={{
                  fontSize: '12px',
                  fontWeight: '600',
                  color: '#6B7280',
                  textTransform: 'uppercase',
                  marginBottom: '4px'
                }}>
                  Link Candidato
                </div>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '12px',
                  background: 'white',
                  borderRadius: '8px',
                  border: '1px solid #E5E7EB'
                }}>
                  <code style={{ flex: 1, fontSize: '14px', color: '#7C3AED', wordBreak: 'break-all' }}>
                    {CANDIDATE_BASE}/interview/{result.interview_token}
                  </code>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(`${CANDIDATE_BASE}/interview/${result.interview_token}`)}
                    leftIcon={copied ? <CheckCircle2 size={16} /> : <Copy size={16} />}
                  >
                    {copied ? 'Copiato!' : 'Copia'}
                  </Button>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  )
}
