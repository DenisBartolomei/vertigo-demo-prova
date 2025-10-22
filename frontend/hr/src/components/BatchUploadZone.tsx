import React, { useState, useRef } from 'react'

interface BatchUploadZoneProps {
  onFilesSelected: (files: File[]) => void
  selectedFiles: File[]
  onRemoveFile: (index: number) => void
}

export function BatchUploadZone({ onFilesSelected, selectedFiles, onRemoveFile }: BatchUploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    
    const files = Array.from(e.dataTransfer.files).filter(file => 
      file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
    )
    
    // Validazione dimensione file (10MB max)
    const validFiles = files.filter(file => file.size <= 10 * 1024 * 1024)
    
    if (validFiles.length !== files.length) {
      alert(`Alcuni file sono stati esclusi: dimensione massima 10MB`)
    }
    
    if (validFiles.length > 0) {
      onFilesSelected([...selectedFiles, ...validFiles])
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files).filter(file => 
        file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
      )
      
      // Validazione dimensione file (10MB max)
      const validFiles = files.filter(file => file.size <= 10 * 1024 * 1024)
      
      if (validFiles.length !== files.length) {
        alert(`Alcuni file sono stati esclusi: dimensione massima 10MB`)
      }
      
      if (validFiles.length > 0) {
        onFilesSelected([...selectedFiles, ...validFiles])
      }
    }
  }

  const openFileDialog = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="batch-upload-zone">
      <div
        className={`upload-drop-zone ${isDragOver ? 'drag-over' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={openFileDialog}
      >
        <div className="upload-content">
          <div className="upload-icon">
            📤
          </div>
          <h3>Upload Massivo CV</h3>
          <p>
            {isDragOver 
              ? 'Rilascia i file PDF qui' 
              : 'Trascina i file PDF qui o clicca per selezionare'
            }
          </p>
          <div className="upload-hint">
            <small>Supporta file PDF multipli • Max 100 file per batch</small>
          </div>
        </div>
        
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
      </div>

      {selectedFiles.length > 0 && (
        <div className="selected-files">
          <h4>File Selezionati ({selectedFiles.length})</h4>
          <div className="files-list">
            {selectedFiles.map((file, index) => (
              <div key={index} className="file-item">
                <div className="file-info">
                  <span className="file-icon">📄</span>
                  <span className="file-name">{file.name}</span>
                  <span className="file-size">
                    ({(file.size / 1024 / 1024).toFixed(1)} MB)
                  </span>
                </div>
                <button
                  className="remove-file"
                  onClick={() => onRemoveFile(index)}
                  title="Rimuovi file"
                >
                  ❌
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
