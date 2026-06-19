const CATEGORY_COLORS = {
  'Process failure': '#2563eb',
  'Communication failure': '#7c3aed',
  'Training gap': '#0891b2',
  'Tool/resource issue': '#059669',
  'Human error': '#ea580c',
  'Management issue': '#dc2626',
  'Planning issue': '#d97706',
  'Documentation issue': '#6366f1',
  'Quality control issue': '#e11d48',
  'Follow-up failure': '#8b5cf6',
  'System weakness': '#0284c7'
}

export default function ConclusionScreen({ conclusion, problem, issueType, whyPath, onFullConclusion, onNewAnalysis }) {
  const categoryColor = CATEGORY_COLORS[conclusion?.rootCauseCategory] || 'var(--accent)'

  return (
    <div className="screen">
      {/* Header */}
      <div className="mb-28" style={{ textAlign: 'center', paddingTop: 16 }}>
        <div style={{
          width: 56,
          height: 56,
          borderRadius: '50%',
          background: 'rgba(16,185,129,0.1)',
          border: '2px solid rgba(16,185,129,0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 16px'
        }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5">
            <path d="M20 6L9 17l-5-5"/>
          </svg>
        </div>
        <div className="section-label mb-8" style={{ color: 'var(--success)' }}>Analysis Complete</div>
        <h2>Short Conclusion</h2>
      </div>

      {/* Root cause category */}
      {conclusion?.rootCauseCategory && (
        <div className="mb-20" style={{ textAlign: 'center' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 16px',
            borderRadius: 100,
            background: `${categoryColor}18`,
            border: `1px solid ${categoryColor}40`,
            color: categoryColor,
            fontSize: '0.8rem',
            fontWeight: 700,
            letterSpacing: '0.04em'
          }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
            {conclusion.rootCauseCategory}
          </div>
        </div>
      )}

      {/* 5 Why summary trail */}
      <div className="card mb-20" style={{ padding: '16px 20px' }}>
        <div className="section-label mb-12">5 Why Path</div>
        {(whyPath || []).map((item, i) => (
          <div key={i} style={{
            display: 'grid',
            gridTemplateColumns: '52px 1fr',
            gap: 12,
            marginBottom: i < whyPath.length - 1 ? 10 : 0,
            paddingBottom: i < whyPath.length - 1 ? 10 : 0,
            borderBottom: i < whyPath.length - 1 ? '1px solid var(--border)' : 'none'
          }}>
            <div style={{
              fontSize: '0.7rem',
              fontWeight: 800,
              color: ['#2563eb','#7c3aed','#db2777','#ea580c','#dc2626'][i],
              paddingTop: 2,
              letterSpacing: '0.05em',
              textTransform: 'uppercase'
            }}>
              Why {i + 1}
            </div>
            <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
              {item.answer}
            </div>
          </div>
        ))}
      </div>

      {/* Short conclusion text */}
      <div className="card mb-24" style={{ borderLeft: `3px solid var(--accent)` }}>
        <div className="section-label mb-10">Most Likely Root Cause</div>
        <p style={{ fontSize: '0.95rem', lineHeight: 1.7, color: 'var(--text-primary)' }}>
          {conclusion?.short || 'Analysis complete. Click below for the full conclusion.'}
        </p>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <button className="btn btn-primary btn-full btn-lg" onClick={onFullConclusion}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          Show Full Conclusion
        </button>
        <button className="btn btn-secondary btn-full" onClick={onNewAnalysis}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          Start New Analysis
        </button>
      </div>
    </div>
  )
}
