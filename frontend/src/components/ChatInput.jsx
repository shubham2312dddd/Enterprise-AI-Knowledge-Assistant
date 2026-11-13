import { LoaderCircle, LockKeyhole, Send } from 'lucide-react'

export default function ChatInput({
  value,
  onChange,
  onSubmit,
  isSending,
  disabled,
  hasDocuments,
}) {
  return (
    <form className="chat-input-area" onSubmit={onSubmit}>
      <div className="chat-input">
        <input
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Ask a question about your documents..."
          disabled={disabled}
          aria-label="Chat input"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          aria-label="Send message"
        >
          {isSending
            ? <LoaderCircle className="spin" size={16} />
            : <Send size={17} />}
        </button>
      </div>
      <div className="chat-input-note">
        <LockKeyhole size={13} />
        {!hasDocuments
          ? 'Upload and index a PDF to start asking questions.'
          : 'Answers use retrieved passages from your selected documents.'}
      </div>
    </form>
  )
}
