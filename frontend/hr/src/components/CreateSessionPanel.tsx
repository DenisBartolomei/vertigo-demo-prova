import React, { useState } from 'react'
import { BatchUploadZone } from './BatchUploadZone'

interface CreateSessionPanelProps {
  isOpen: boolean
  onClose: () => void
  positions: any[]
  onBatchUpload: (files: File[], positionId: string) => Promise<void>
  onSingleUpload: (data: {
    positionId: string
    candidateName: string
    candidateEmail: string
    cvFile: File
  }) => Promise<void>
  batchUploading: boolean
}

export function CreateSessionPanel({ 
  isOpen, 
  onClose, 
  positions, 
  onBatchUpload, 
  onSingleUpload,
  batchUploading 
}: CreateSessionPanelProps) {
  const [activeTab, setActiveTab] = useState<'batch' | 'single'>('batch')
  
  // Batch upload state
  const [batchFiles, setBatchFiles] = useState<File[]>([])
  const [batchPositionId, setBatchPositionId] = useState('')
  
  // Single upload state
  const [singlePositionId, setSinglePositionId] = useState('')
  const [candidateName, setCandidateName] = useState('')
  const [candidateEmail, setCandidateEmail] = useState('')
  const [cvFile, setCvFile] = useState<File | null>(null)
  const [singleUploading, setSingleUploading] = useState(false)

  const handleBatchFilesSelected = (files: File[]) => {
    setBatchFiles(files)
  }

  const handleRemoveBatchFile = (index: number) => {
    setBatchFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleBatchSubmit = async () => {
    if (!batchFiles.length || !batchPositionId) return
    await onBatchUpload(batchFiles, batchPositionId)
    setBatchFiles([])
    setBatchPositionId('')
  }

  const handleSingleSubmit = async () => {
    if (!cvFile || !singlePositionId || !candidateName || singleUploading) return
    
    setSingleUploading(true)
    try {
      await onSingleUpload({
        positionId: singlePositionId,
        candidateName,
        candidateEmail,
        cvFile
      })
      setSinglePositionId('')
      setCandidateName('')
      setCandidateEmail('')
      setCvFile(null)
    } finally {
      setSingleUploading(false)
    }
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div className="panel-backdrop" onClick={handleBackdropClick}>
      <div className="create-session-panel">
        <div className="panel-header">
          <h3>Crea Nuove Sessioni</h3>
          <button className="panel-close" onClick={onClose}>
            ✕
          </button>
        </div>
        
        <div className="panel-tabs">
          <button 
            className={`tab-button ${activeTab === 'batch' ? 'active' : ''}`}
            onClick={() => setActiveTab('batch')}
          >
            📤 Upload Massivo
          </button>
          <button 
            className={`tab-button ${activeTab === 'single' ? 'active' : ''}`}
            onClick={() => setActiveTab('single')}
          >
            ⚡ Upload Emergenza
          </button>
        </div>

        <div className="panel-content">
          {activeTab === 'batch' && (
            <div className="upload-section">
              <div className="section-header">
                <h4>Upload Massivo CV</h4>
                <p>Carica centinaia di CV e processali automaticamente alle 19:00</p>
              </div>
              
              <div className="form-group">
                <label>Seleziona Posizione per il Batch</label>
                <select 
                  value={batchPositionId} 
                  onChange={e => setBatchPositionId(e.target.value)}
                >
                  <option value="">Scegli una posizione...</option>
                  {positions.map((p) => (
                    <option key={p._id} value={p._id}>
                      {p.position_name} ({p._id})
                    </option>
                  ))}
                </select>
              </div>
              
              <BatchUploadZone
                onFilesSelected={handleBatchFilesSelected}
                selectedFiles={batchFiles}
                onRemoveFile={handleRemoveBatchFile}
              />
              
              <button 
                onClick={handleBatchSubmit} 
                disabled={!batchFiles.length || !batchPositionId || batchUploading}
                className="submit-button batch-submit"
              >
                {batchUploading ? '⏳' : '🚀'} 
                {batchUploading ? 'Caricamento...' : `Carica ${batchFiles.length} CV per Batch Processing`}
              </button>
              
              <div className="info-box">
                ℹ️ I CV verranno processati automaticamente alle 19:00 di ogni giorno
              </div>
            </div>
          )}

          {activeTab === 'single' && (
            <div className="upload-section">
              <div className="section-header">
                <h4>Upload Singolo (Solo Emergenze)</h4>
                <p>Carica un singolo CV per processamento immediato</p>
              </div>
              
              <div className="form-group">
                <label>Seleziona Posizione</label>
                <select 
                  value={singlePositionId} 
                  onChange={e => setSinglePositionId(e.target.value)}
                >
                  <option value="">Scegli una posizione...</option>
                  {positions.map((p) => (
                    <option key={p._id} value={p._id}>
                      {p.position_name} ({p._id})
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="form-group">
                <label>Nome Candidato</label>
                <input 
                  placeholder="Inserisci il nome completo del candidato" 
                  value={candidateName} 
                  onChange={e => setCandidateName(e.target.value)} 
                />
              </div>
              
              <div className="form-group">
                <label>Indirizzo Email</label>
                <input 
                  placeholder="candidato@esempio.com" 
                  value={candidateEmail} 
                  onChange={e => setCandidateEmail(e.target.value)} 
                />
              </div>
              
              <div className="form-group">
                <label>File CV</label>
                <input 
                  type="file" 
                  accept=".pdf,.txt" 
                  onChange={e => setCvFile(e.target.files?.[0] || null)} 
                />
                {cvFile && (
                  <div className="file-preview">
                    📄 {cvFile.name}
                  </div>
                )}
              </div>
              
              <button 
                onClick={handleSingleSubmit} 
                disabled={!cvFile || !singlePositionId || !candidateName || singleUploading}
                className="submit-button single-submit"
              >
                {singleUploading ? '⏳' : '🚀'} 
                {singleUploading ? 'Creazione in corso...' : 'Crea Sessione & Invia Invito'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
