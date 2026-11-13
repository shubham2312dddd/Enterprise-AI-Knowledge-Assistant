import { useState } from 'react'
import { AlertCircle, FileSearch, LoaderCircle, Search, Trash2 } from 'lucide-react'
import { getApiErrorMessage, searchDocuments } from '../services/api'

export default function DocumentSearch({
  documents = [],
  documentsError = '',
  onDeleteDocument,
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [selectedDocumentIds, setSelectedDocumentIds] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [deletingDocumentId, setDeletingDocumentId] = useState('')
  const [error, setError] = useState('')

  function toggleDocument(documentId, checked) {
    setSelectedDocumentIds((currentIds) => {
      if (checked) return [...new Set([...currentIds, documentId])]
      return currentIds.filter((currentId) => currentId !== documentId)
    })
    setResults(null)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const trimmedQuery = query.trim()
    if (!trimmedQuery) {
      setError('Enter a question to search this document.')
      setResults(null)
      return
    }

    setError('')
    setResults(null)
    setIsSearching(true)
    try {
      const response = await searchDocuments(
        trimmedQuery,
        selectedDocumentIds.length > 0 ? selectedDocumentIds : null,
      )
      setResults(response.results)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setIsSearching(false)
    }
  }

  async function handleDelete(document) {
    if (!window.confirm(`Remove "${document.filename}" and its indexed chunks?`)) return

    setError('')
    setDeletingDocumentId(document.document_id)
    try {
      await onDeleteDocument(document.document_id)
      setSelectedDocumentIds((currentIds) => currentIds.filter(
        (currentId) => currentId !== document.document_id,
      ))
      setResults(null)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setDeletingDocumentId('')
    }
  }

  return (
    <section className="panel search-panel" aria-labelledby="document-search-heading">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">RETRIEVAL PREVIEW</span>
          <h2 id="document-search-heading">Search documents</h2>
        </div>
        <span className="file-type-badge"><FileSearch size={14} /> Vector search</span>
      </div>
      <p className="panel-description">
        Search one, several, or all indexed PDFs. Results show the source and original page; no AI answer is generated.
      </p>

      <div className="document-scope" aria-label="Search scope">
        <label className="document-scope-option">
          <input
            type="checkbox"
            checked={selectedDocumentIds.length === 0}
            onChange={() => {
              setSelectedDocumentIds([])
              setResults(null)
            }}
          />
          <span>All indexed documents</span>
        </label>
        {documents.map((document) => (
          <div className="indexed-document-option" key={document.document_id}>
            <label className="document-scope-option">
              <input
                type="checkbox"
                checked={selectedDocumentIds.includes(document.document_id)}
                onChange={(event) => toggleDocument(document.document_id, event.target.checked)}
              />
              <span>
                <strong>{document.filename}</strong>
                <small>{document.pages_with_text.length} text pages · {document.total_chunks} chunks</small>
              </span>
            </label>
            <button
              className="remove-document-button"
              type="button"
              aria-label={`Remove ${document.filename}`}
              disabled={deletingDocumentId === document.document_id}
              onClick={() => handleDelete(document)}
            >
              {deletingDocumentId === document.document_id
                ? <LoaderCircle className="spin" size={14} />
                : <Trash2 size={14} />}
            </button>
          </div>
        ))}
        {documents.length === 0 && (
          <p className="no-indexed-documents">Upload a PDF to start searching.</p>
        )}
      </div>

      <form className="document-search-form" onSubmit={handleSubmit}>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="e.g. What is the main objective of this project?"
          aria-label="Search question"
          disabled={isSearching || documents.length === 0}
        />
        <button
          className="button search-button"
          type="submit"
          disabled={isSearching || documents.length === 0}
        >
          {isSearching ? <LoaderCircle className="spin" size={16} /> : <Search size={16} />}
          <span>{isSearching ? 'Searching' : 'Search'}</span>
        </button>
      </form>

      {documentsError && (
        <div className="inline-alert error-alert" role="alert">
          <AlertCircle size={17} /><span>{documentsError}</span>
        </div>
      )}
      {error && <div className="inline-alert error-alert" role="alert"><AlertCircle size={17} /><span>{error}</span></div>}

      {results !== null && (
        <div className="search-results" aria-live="polite">
          <div className="search-results-heading">
            <strong>{results.length} retrieved {results.length === 1 ? 'passage' : 'passages'}</strong>
            <span>Lower distance indicates a closer match</span>
          </div>
          {results.length === 0 ? (
            <p className="no-search-results">No matching passages were found in this document.</p>
          ) : (
            results.map((result) => (
              <article className="search-result" key={result.chunk_id}>
                <div className="search-result-meta">
                  <span><FileSearch size={14} /> {result.filename}</span>
                  <span>Page {result.page_number}</span>
                  <span>Distance {result.distance.toFixed(3)}</span>
                </div>
                <p>{result.text}</p>
              </article>
            ))
          )}
        </div>
      )}
    </section>
  )
}
