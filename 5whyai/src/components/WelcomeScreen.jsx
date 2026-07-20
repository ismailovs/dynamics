export default function WelcomeScreen({ onStart, onHistory }) {
  return (
    <div className="screen" style={{ justifyContent: 'center', minHeight: '100dvh', paddingTop: 60 }}>
      {/* Logo mark */}
      <div className="mb-32" style={{ textAlign: 'center' }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 72,
          height: 72,
          borderRadius: 20,
          background: 'linear-gradient(135deg, #1e3a8a, #2563eb)',
          boxShadow: '0 0 40px rgba(37,99,235,0.35)',
          marginBottom: 24
        }}>
          <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
            <path d="M18 4L32 12V24L18 32L4 24V12L18 4Z" stroke="white" strokeWidth="2" fill="none" />
            <text x="18" y="22" textAnchor="middle" fill="white" fontSize="12" fontWeight="900" fontFamily="Inter,sans-serif">5W</text>
          </svg>
        </div>

        <h1 style={{ marginBottom: 8 }}>
          5Why<span style={{ color: 'var(--accent)' }}>AI</span>
        </h1>

        <p className="hero-tagline mb-24">Fast Root Cause Analysis</p>

        <div style={{
          display: 'inline-flex',
          gap: 8,
          flexWrap: 'wrap',
          justifyContent: 'center',
          marginBottom: 40
        }}>
          {['5 Whys Method', 'AI-Powered', 'Instant Analysis'].map(tag => (
            <span key={tag} className="badge badge-accent">{tag}</span>
          ))}
        </div>

        <div className="privacy-notice mb-32" style={{ maxWidth: 400, margin: '0 auto 32px' }}>
          <strong>Your analysis is private.</strong> Do not enter passwords, financial account numbers, medical records, or highly sensitive personal information. 5WhyAI does not share your answers with other users.
        </div>
      </div>

      {/* CTA */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 380, margin: '0 auto', width: '100%' }}>
        <button className="btn btn-primary btn-full btn-lg" onClick={onStart}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
          Start New Analysis
        </button>
        <button className="btn btn-secondary btn-full" onClick={onHistory}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          View History
        </button>
      </div>

      {/* Footer */}
      <div style={{ textAlign: 'center', marginTop: 48, color: 'var(--text-muted)', fontSize: '0.78rem' }}>
        Ask why. Find truth.
      </div>
    </div>
  )
}
