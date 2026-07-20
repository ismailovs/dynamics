import { useState, useEffect } from 'react'
import { getAll, deleteAnalysis } from '../utils/storage.js'

const CATEGORY_COLORS = {
  'Process failure': '#2563eb',
  'Communication failure': '#7c3aed',
  'Training gap': '#0891b2',
  'Follow-up failure': '#8b5cf6',
  'System weakness': '#0284c7',
  'Human error': '#ea580c',
  'Management issue': '#dc2626'
}

export default function HistoryScreen({ onBack, onLoad, onNewAnalysis }) {
  const [analyses, setAnalyses] = useState([])
  const [toDelete, setToDelete] = useState(null)

  useEffect(() => {
    setAnalyses(getAll())
  }, [])

  const handleDelete = (id) => {
    deleteAnalysis(id)
    setAnalyses(getAll())
    setToDelete(null)
  }

  return (
    <div className="screen">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 }}>
        <button className="btn btn-ghost" onClick={onBack} style={{ paddingLeft: 0 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M19 12H5M12 5l-7 7 7 7"/>
          </svg>
          Back
        </button>
        <div style={{ flex: 1 }}>
          <h2 style={{ fontSize: '1.3rem' }}>Analysis History</h2>
        </div>
      </div>

      {analyses.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
              <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <p style={{ marginBottom: 24 }}>No saved analyses yet.</p>
          <button className="btn btn-primary" onClick={onNewAnalysis}>
            Start Your First Analysis
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {analyses.map(a => {
            const catColor = CATEGORY_COLORS[a.conclusion?.rootCauseCategory] || 'var(--accent)'
            return (
              <div key={a.id}>
                <div
                  className="history-item"
                  onClick={() => onLoad(a)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                    <span style={{
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: 100,
                      background: a.issueType === 'business' ? 'rgba(37,99,235,0.12)' : 'rgba(16,185,129,0.1)',
                      color: a.issueType === 'business' ? 'var(--accent)' : 'var(--success)',
                      letterSpacing: '0.05em',
                      textTransform: 'uppercase'
                    }}>
                      {a.issueType}
                    </span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>
                      {new Date(a.createdAt).toLocaleDateString()}
                    </span>
                  </div>

                  <div style={{ fontWeight: 600, fontSize: '0.92rem', marginBottom: 4 }}>
                    {a.problem}
                  </div>

                  {a.conclusion?.rootCauseCategory && (
                    <div style={{
                      fontSize: '0.75rem',
                      color: catColor,
                      fontWeight: 500
                    }}>
                      {a.conclusion.rootCauseCategory}
                    </div>
                  )}

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {(a.whyPath || []).length} whys completed
                    </span>
                    <button
                      className="btn btn-sm"
                      style={{
                        background: 'transparent',
                        border: '1px solid rgba(239,68,68,0.25)',
                        color: 'var(--danger)',
                        padding: '4px 10px',
                        fontSize: '0.75rem'
                      }}
                      onClick={e => { e.stopPropagation(); setToDelete(a.id) }}
                    >
                      Delete
                    </button>
                  </div>
                </div>

                {toDelete === a.id && (
                  <div style={{
                    marginTop: 4,
                    padding: '12px 14px',
                    background: 'rgba(239,68,68,0.06)',
                    border: '1px solid rgba(239,68,68,0.25)',
                    borderRadius: 'var(--radius-sm)',
                    display: 'flex',
                    gap: 10,
                    alignItems: 'center'
                  }}>
                    <span style={{ flex: 1, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      Delete this analysis?
                    </span>
                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(a.id)}>
                      Delete
                    </button>
                    <button className="btn btn-sm btn-ghost" onClick={() => setToDelete(null)}>
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
