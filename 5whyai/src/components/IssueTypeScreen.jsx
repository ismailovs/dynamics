export default function IssueTypeScreen({ onSelect, onBack }) {
  const types = [
    {
      id: 'business',
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <rect x="2" y="7" width="20" height="14" rx="2"/>
          <path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/>
          <line x1="12" y1="12" x2="12" y2="16"/>
          <line x1="10" y1="14" x2="14" y2="14"/>
        </svg>
      ),
      label: 'Business Issue',
      desc: 'Operations, processes, teams, quality, delivery, compliance'
    },
    {
      id: 'personal',
      icon: (
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
          <circle cx="12" cy="7" r="4"/>
        </svg>
      ),
      label: 'Personal Issue',
      desc: 'Habits, decisions, goals, relationships, performance'
    }
  ]

  return (
    <div className="screen">
      <button className="btn btn-ghost mb-24" onClick={onBack} style={{ alignSelf: 'flex-start', paddingLeft: 0 }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M19 12H5M12 5l-7 7 7 7"/>
        </svg>
        Back
      </button>

      <div className="mb-32">
        <div className="section-label mb-8">Step 1 of 3</div>
        <h2 style={{ marginBottom: 8 }}>What type of issue is this?</h2>
        <p className="text-secondary" style={{ fontSize: '0.9rem' }}>
          This helps the AI generate more relevant root cause options.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {types.map(({ id, icon, label, desc }) => (
          <button
            key={id}
            className="answer-btn"
            style={{ padding: '20px 22px', gap: 18, alignItems: 'flex-start' }}
            onClick={() => onSelect(id)}
          >
            <div style={{
              width: 52,
              height: 52,
              borderRadius: 14,
              background: 'var(--accent-light)',
              border: '1px solid rgba(37,99,235,0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent)',
              flexShrink: 0
            }}>
              {icon}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: '1rem', marginBottom: 4 }}>{label}</div>
              <div style={{ fontSize: '0.83rem', color: 'var(--text-muted)', fontWeight: 400 }}>{desc}</div>
            </div>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ flexShrink: 0, color: 'var(--text-muted)', marginTop: 4 }}>
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </button>
        ))}
      </div>
    </div>
  )
}
