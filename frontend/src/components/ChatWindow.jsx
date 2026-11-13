import { useRef, useState } from 'react'
import {
  AlertCircle,
  Bot,
  FileText,
  Info,
  LoaderCircle,
  MessageSquareText,
  UserRound,
} from 'lucide-react'
import ChatInput from './ChatInput'
import { chatWithDocuments, getApiErrorMessage } from '../services/api'

export default function ChatWindow({ documents = [] }) {
  const [selectedDocumentId, setSelectedDocumentId] = useState('')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const sendingRef = useRef(false)
  const messageSequence = useRef(0)

  const activeDocumentId = documents.some(
    (document) => document.document_id === selectedDocumentId,
  )
    ? selectedDocumentId
    : ''

  function nextMessageId() {
    messageSequence.current += 1
    return `chat-message-${messageSequence.current}`
  }

  async function handleSubmit(event) {
    event.preventDefault()
    const question = input.trim()
    if (!question || sendingRef.current || documents.length === 0) return

    sendingRef.current = true
    setIsSending(true)
    setInput('')
    const userMessage = {
      id: nextMessageId(),
      role: 'user',
      content: question,
    }
    setMessages((currentMessages) => [
      ...currentMessages,
      userMessage,
    ])

    try {
      const response = await chatWithDocuments(
        question,
        activeDocumentId ? [activeDocumentId] : null,
      )
      const assistantMessage = {
        id: nextMessageId(),
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        status: response.status,
      }
      setMessages((currentMessages) => [
        ...currentMessages,
        assistantMessage,
      ])
    } catch (error) {
      const errorMessage = {
        id: nextMessageId(),
        role: 'assistant',
        content: getApiErrorMessage(error),
        isError: true,
      }
      setMessages((currentMessages) => [
        ...currentMessages,
        errorMessage,
      ])
    } finally {
      sendingRef.current = false
      setIsSending(false)
    }
  }

  return (
    <section className="panel chat-panel" id="assistant">
      <div className="panel-heading chat-heading">
        <div>
          <span className="eyebrow">WORK WITH YOUR CONTENT</span>
          <h2>AI assistant</h2>
        </div>
        <span className="file-type-badge"><span className="chat-model-dot" /> Local Ollama</span>
      </div>
      <div className="chat-document-scope">
        <label htmlFor="chat-document-select"><FileText size={14} /> Document scope</label>
        <select
          id="chat-document-select"
          value={activeDocumentId}
          onChange={(event) => setSelectedDocumentId(event.target.value)}
          disabled={isSending || documents.length === 0}
        >
          <option value="">All indexed documents</option>
          {documents.map((document) => (
            <option key={document.document_id} value={document.document_id}>
              {document.filename}
            </option>
          ))}
        </select>
      </div>
      <div className="chat-body" aria-live="polite">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-intro-icon"><MessageSquareText size={23} /></div>
            <strong>Ask a question about your documents</strong>
            <p>Answers are grounded in passages retrieved from the selected document scope.</p>
          </div>
        ) : (
          <div className="chat-messages">
            {messages.map((message) => (
              <article
                className={`chat-message ${message.role}${message.isError ? ' error' : ''}`}
                key={message.id}
              >
                <div className="chat-message-author">
                  {message.role === 'user'
                    ? <><UserRound size={14} /> You</>
                    : <><Bot size={14} /> Knowledge Assistant</>}
                </div>
                <p>{message.content}</p>
                {message.status === 'insufficient_context' && (
                  <div className="chat-insufficient-note">
                    <Info size={13} /> No sufficient supporting passage was found.
                  </div>
                )}
                {message.isError && (
                  <div className="chat-insufficient-note">
                    <AlertCircle size={13} /> The request failed. You can try again.
                  </div>
                )}
                {message.sources?.length > 0 && (
                  <div className="chat-sources">
                    <strong>Sources</strong>
                    {message.sources.map((source, index) => (
                      <details key={`${source.document_id}-${source.page_number}-${index}`}>
                        <summary>
                          <FileText size={13} />
                          <span>{source.filename}</span>
                          <span>Page {source.page_number}</span>
                        </summary>
                        <p>{source.excerpt}</p>
                      </details>
                    ))}
                  </div>
                )}
              </article>
            ))}
            {isSending && (
              <div className="chat-loading" role="status">
                <LoaderCircle className="spin" size={15} />
                <span>Retrieving passages and generating an answer...</span>
              </div>
            )}
          </div>
        )}
      </div>
      <ChatInput
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        isSending={isSending}
        disabled={isSending || documents.length === 0}
        hasDocuments={documents.length > 0}
      />
    </section>
  )
}
