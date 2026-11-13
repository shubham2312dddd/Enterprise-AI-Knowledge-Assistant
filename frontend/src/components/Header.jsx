import { RefreshCw, Sparkles } from 'lucide-react'

export default function Header({ connectionStatus, onRetry }) {
  const labels = {
    checking: 'Connecting',
    online: 'Backend connected',
    offline: 'Backend unavailable',
  }

  return (
    <header className="topbar">
      <div className="breadcrumb"><span>Workspace</span><span className="breadcrumb-separator">/</span><strong>Overview</strong></div>
      <div className="topbar-actions">
        <div className={`connection-status ${connectionStatus}`} role="status">
          <span className="status-dot" />
          <span>{labels[connectionStatus]}</span>
        </div>
        {connectionStatus !== 'online' && (
          <button className="icon-button" type="button" onClick={onRetry} aria-label="Retry backend connection">
            <RefreshCw size={16} />
          </button>
        )}
        <div className="topbar-divider" />
        <span className="topbar-product"><Sparkles size={16} /> AI workspace</span>
        <span className="topbar-avatar" aria-label="Enterprise workspace">EA</span>
      </div>
    </header>
  )
}
