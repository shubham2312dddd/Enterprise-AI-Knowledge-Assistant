import { useEffect, useState } from 'react'
import { ArrowDownToLine, FileText, ShieldCheck } from 'lucide-react'
import './App.css'
import ChatWindow from './components/ChatWindow'
import DocumentSearch from './components/DocumentSearch'
import FileUpload from './components/FileUpload'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import {
  checkBackendHealth,
  deleteDocument,
  getApiErrorMessage,
  listDocuments,
  uploadPdf,
} from './services/api'

function App() {
  const [connectionStatus, setConnectionStatus] = useState('checking')
  const [file, setFile] = useState(null)
  const [documentInfo, setDocumentInfo] = useState(null)
  const [documents, setDocuments] = useState([])
  const [documentsError, setDocumentsError] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploadError, setUploadError] = useState('')

  async function checkConnection() {
    setConnectionStatus('checking')
    try {
      await checkBackendHealth()
      setConnectionStatus('online')
    } catch {
      setConnectionStatus('offline')
    }
  }

  useEffect(() => {
    let isActive = true
    checkBackendHealth()
      .then(() => {
        if (isActive) setConnectionStatus('online')
      })
      .catch(() => {
        if (isActive) setConnectionStatus('offline')
      })

    return () => {
      isActive = false
    }
  }, [])

  useEffect(() => {
    let isActive = true
    listDocuments()
      .then((indexedDocuments) => {
        if (isActive) {
          setDocuments(indexedDocuments)
          setDocumentsError('')
        }
      })
      .catch((error) => {
        if (isActive) setDocumentsError(getApiErrorMessage(error))
      })

    return () => {
      isActive = false
    }
  }, [])

  async function refreshDocuments() {
    try {
      setDocuments(await listDocuments())
      setDocumentsError('')
    } catch (error) {
      setDocumentsError(getApiErrorMessage(error))
    }
  }

  async function handleFileSelected(selectedFile, validationError = '') {
    setUploadError(validationError)
    if (!selectedFile) return

    setFile(selectedFile)
    setDocumentInfo(null)
    setProgress(0)
    setIsUploading(true)
    try {
      const result = await uploadPdf(selectedFile, setProgress)
      setDocumentInfo(result)
      await refreshDocuments()
    } catch (error) {
      setUploadError(getApiErrorMessage(error))
    } finally {
      setIsUploading(false)
    }
  }

  async function handleDeleteDocument(documentId) {
    await deleteDocument(documentId)
    setDocuments((currentDocuments) => currentDocuments.filter(
      (document) => document.document_id !== documentId,
    ))
    if (documentInfo?.document_id === documentId) {
      setDocumentInfo(null)
      setFile(null)
    }
  }

  return (
    <div className="app-shell" id="overview">
      <Sidebar />
      <main className="main-content">
        <Header connectionStatus={connectionStatus} onRetry={checkConnection} />
        <div className="page-content">
          <section className="welcome-section">
            <div>
              <span className="eyebrow">ENTERPRISE KNOWLEDGE WORKSPACE</span>
              <h1>Your knowledge, <span>in one place.</span></h1>
              <p>Upload a document to extract and review its contents in your workspace.</p>
            </div>
            <div className="welcome-mark"><FileText size={27} /><ArrowDownToLine size={17} /></div>
          </section>

          <div className="workspace-grid">
            <FileUpload
              file={file}
              documentInfo={documentInfo}
              isUploading={isUploading}
              progress={progress}
              error={uploadError}
              onFileSelected={handleFileSelected}
            />
            <ChatWindow documents={documents} />
          </div>

          <DocumentSearch
            documents={documents}
            documentsError={documentsError}
            onDeleteDocument={handleDeleteDocument}
          />

          <footer className="page-footer">
            <span><ShieldCheck size={15} /> Documents are processed locally by your configured backend.</span>
            <span>Enterprise AI Knowledge Assistant <span className="footer-dot">·</span> Development preview</span>
          </footer>
        </div>
      </main>
    </div>
  )
}

export default App
