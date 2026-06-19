import { useState } from 'react'

const PLACEHOLDERS = {
  business: 'Example: Customers are complaining about late delivery',
  personal: 'Example: I keep missing my daily exercise goals'
}

const EXAMPLES = {
  business: [
    'Customer complaints are increasing each month',
    'Production line is missing quality targets',
    'Project deadlines are not being met',
    'Team communication is breaking down'
  ],
  personal: [
    'I cannot stick to a consistent sleep schedule',
    'I keep procrastinating on important tasks',
    'I am not making progress on my goals',
    'I keep making the same mistake repeatedly'
  ]
}

export default function ProblemInputScreen({ issueType, onSubmit, onBack, loading }) {
  const [problem, setProblem] = useState('')

  const handleSubmit = () => {
    const trimmed = problem.trim()
    if (trimmed.length < 10) return
    onSubmit(trimmed)
  }

  const handleExample = (ex) => setProblem(ex)

  return (
    <div className="screen">
      <button className="btn btn-ghost mb-24" onClick={onBack} style={{ alignSelf: 'flex-start', paddingLeft: 0 }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M19 12H5M12 5l-7 7 7 7"/>
        </svg>
        Back
      </button>

      <div className="mb-24">
        <div className="section-label mb-8">Step 2 of 3</div>
        <h2 style={{ marginBottom: 8 }}>What problem do you want to solve?</h2>
        <p className="text-secondary" style={{ fontSize: '0.9rem' }}>
          Describe it clearly and specifically. The AI will guide the analysis.
        </p>
      </div>

      <div className="mb-20">
        <textarea
          className="input-field"
          placeholder={PLACEHOLDERS[issueType] || PLACEHOLDERS.business}
          value={problem}
          onChange={e => setProblem(e.target.value)}
          rows={3}
          autoFocus
          onKeyDown={e => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit()
          }}
        />
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 6, textAlign: 'right' }}>
          {problem.length} chars &nbsp;·&nbsp; Ctrl+Enter to start
        </div>
      </div>

      {/* Quick examples */}
      <div className="mb-24">
        <div className="section-label mb-10">Quick examples</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {(EXAMPLES[issueType] || EXAMPLES.business).map((ex) => (
            <button
              key={ex}
              onClick={() => handleExample(ex)}
              style={{
                background: 'transparent',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                padding: '10px 14px',
                textAlign: 'left',
                color: 'var(--text-secondary)',
                fontSize: '0.85rem',
                cursor: 'pointer',
                transition: 'all var(--transition)',
                fontFamily: 'var(--font)'
              }}
              onMouseOver={e => {
                e.currentTarget.style.borderColor = 'var(--accent)'
                e.currentTarget.style.color = 'var(--text-primary)'
              }}
              onMouseOut={e => {
                e.currentTarget.style.borderColor = 'var(--border)'
                e.currentTarget.style.color = 'var(--text-secondary)'
              }}
            >
              "{ex}"
            </button>
          ))}
        </div>
      </div>

      <button
        className="btn btn-primary btn-full btn-lg"
        onClick={handleSubmit}
        disabled={problem.trim().length < 10 || loading}
      >
        {loading ? (
          <>
            <div className="loading-dots"><span/><span/><span/></div>
            Analyzing…
          </>
        ) : (
          <>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
            Start 5 Why Analysis
          </>
        )}
      </button>

      <div className="privacy-notice mt-20">
        <strong>Confidential.</strong> Your input is processed securely and not shown to other users.
      </div>
    </div>
  )
}
