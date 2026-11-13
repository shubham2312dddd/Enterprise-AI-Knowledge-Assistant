import { useRef, useState } from 'react'
import { AlertCircle, CheckCircle2, FileText, LoaderCircle, UploadCloud } from 'lucide-react'

const MAX_FILE_SIZE = 20 * 1024 * 1024

function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export default function FileUpload({ file, documentInfo, isUploading, progress, error, onFileSelected }) {
  const inputRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)

  function acceptFile(candidate) {
    if (!candidate) return
    if (!candidate.name.toLowerCase().endsWith('.pdf')) {
      onFileSelected(null, 'Select a PDF file to continue.')
      return
    }
    if (candidate.size > MAX_FILE_SIZE) {
      onFileSelected(null, 'The PDF exceeds the 20 MB upload limit.')
      return
    }
    if (candidate.size === 0) {
      onFileSelected(null, 'The selected PDF is empty.')
      return
    }
    onFileSelected(candidate)
  }

  function handleDrop(event) {
    event.preventDefault()
    setIsDragging(false)
    acceptFile(event.dataTransfer.files[0])
  }

  return (
    <section className="panel document-panel" id="documents">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">YOUR KNOWLEDGE BASE</span>
          <h2>Upload a document</h2>
        </div>
        <span className="file-type-badge">PDF only</span>
      </div>
      <p className="panel-description">Add a PDF to extract its text and prepare it for your workspace.</p>

      <input
        ref={inputRef}
        className="visually-hidden"
        type="file"
        accept=".pdf,application/pdf"
        onChange={(event) => {
          acceptFile(event.target.files[0])
          event.target.value = ''
        }}
        aria-label="Choose a PDF file"
      />
      <div
        className={`dropzone${isDragging ? ' dragging' : ''}${isUploading ? ' uploading' : ''}`}
        onDragOver={(event) => { event.preventDefault(); setIsDragging(true) }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <div className="upload-icon"><UploadCloud size={23} /></div>
        <strong>Drag and drop your PDF here</strong>
        <span>or</span>
        <button
          className="button button-secondary browse-button"
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={isUploading}
        >
          Browse files
        </button>
        <small>Maximum file size: 20 MB</small>
      </div>

      {error && <div className="inline-alert error-alert" role="alert"><AlertCircle size={17} /><span>{error}</span></div>}

      {file && (
        <div className="selected-file">
          <div className="file-icon"><FileText size={19} /></div>
          <div className="selected-file-details">
            <strong title={file.name}>{file.name}</strong>
            <span>{formatFileSize(file.size)}</span>
          </div>
          {isUploading && <span className="upload-state"><LoaderCircle className="spin" size={16} /> Processing</span>}
          {!isUploading && documentInfo && <span className="upload-state success"><CheckCircle2 size={16} /> Indexed</span>}
        </div>
      )}

      {isUploading && (
        <div className="progress-wrap" aria-label={`Upload progress ${progress}%`}>
          <div className="progress-track"><div className="progress-bar" style={{ width: `${progress}%` }} /></div>
          <span>{progress}%</span>
        </div>
      )}

      {documentInfo && (
        <div className="document-result" aria-live="polite">
          <div className="result-heading"><CheckCircle2 size={18} /><strong>Indexing successful</strong></div>
          <div className="result-stats">
            <div><strong>{documentInfo.total_pages ?? documentInfo.page_count}</strong><span>pages processed</span></div>
            <div><strong>{(documentInfo.extracted_characters ?? documentInfo.character_count).toLocaleString()}</strong><span>characters extracted</span></div>
            <div><strong>{documentInfo.total_chunks}</strong><span>chunks indexed</span></div>
          </div>
          {documentInfo.empty_pages?.length > 0 && (
            <p className="empty-pages-note">
              No selectable text on page{documentInfo.empty_pages.length === 1 ? '' : 's'} {documentInfo.empty_pages.join(', ')}.
            </p>
          )}
          <div className="text-preview">
            <span className="preview-label">EXTRACTED TEXT PREVIEW</span>
            <p>{documentInfo.text_preview || 'No selectable text was found in this PDF.'}</p>
          </div>
        </div>
      )}
    </section>
  )
}
