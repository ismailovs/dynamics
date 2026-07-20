import { SCREENS } from '../hooks/useAnalysis.js'

export default function TopBar({ screen, onNew, onHistory }) {
  const showBar = screen !== SCREENS.WELCOME

  if (!showBar) return null

  return (
    <header className="top-bar">
      <div className="top-bar-logo">
        5Why<span>AI</span>
      </div>
      <div className="top-bar-actions">
        {screen !== SCREENS.HISTORY && (
          <button className="btn btn-ghost btn-sm" onClick={onHistory} title="History">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </button>
        )}
        <button
          className="btn btn-sm"
          onClick={onNew}
          style={{
            background: 'var(--accent-light)',
            border: '1px solid rgba(37,99,235,0.25)',
            color: 'var(--accent)',
            fontSize: '0.8rem',
            padding: '7px 14px'
          }}
          title="New Analysis"
        >
          + New
        </button>
      </div>
    </header>
  )
}
