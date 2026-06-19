export default function FullConclusionScreen({ conclusion, problem, issueType, whyPath, onBack, onNewAnalysis }) {
  const handleExport = () => {
    const lines = [
      '5WhyAI — Root Cause Analysis Report',
      '=====================================',
      '',
      `Issue Type: ${issueType === 'business' ? 'Business' : 'Personal'}`,
      `Problem: ${problem}`,
      '',
      '5 WHY PATH',
      '----------',
      ...(whyPath || []).map((h, i) => `Why ${i+1}: ${h.answer}`),
      '',
      'ROOT CAUSE CATEGORY',
      '-------------------',
      conclusion?.rootCauseCategory || '',
      '',
      'MOST LIKELY ROOT CAUSE',
      '----------------------',
      conclusion?.mostLikelyRootCause || '',
      '',
      'SHORT CONCLUSION',
      '----------------',
      conclusion?.short || '',
      '',
      'CONTRIBUTING FACTORS',
      '--------------------',
      ...(conclusion?.contributingFactors || []).map((f, i) => `${i+1}. ${f}`),
      '',
      'CORRECTIVE ACTIONS',
      '------------------',
      ...(conclusion?.correctiveActions || []).map((a, i) => `${i+1}. ${a}`),
      '',
      'PREVENTIVE ACTIONS',
      '------------------',
      ...(conclusion?.preventiveActions || []).map((a, i) => `${i+1}. ${a}`),
      '',
      'ACTION PLAN',
      '-----------',
      ...(conclusion?.actionPlan || []).map(a => `Priority ${a.priority}: ${a.action} (${a.timeframe})`),
      '',
      `Generated: ${new Date().toLocaleString()}`,
      'Powered by 5WhyAI — Ask why. Find truth.'
    ]

    const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `5whyai-analysis-${Date.now()}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  const Section = ({ title, children }) => (
    <div className="mb-24">
      <div className="section-label mb-12">{title}</div>
      {children}
    </div>
  )

  const ActionList = ({ items, color = 'var(--accent)' }) => (
    <div>
      {(items || []).map((item, i) => (
        <div key={i} className="action-item">
          <div className="action-item-num" style={{ background: `${color}18`, borderColor: `${color}40`, color }}>
            {i + 1}
          </div>
          <div style={{ fontSize: '0.9rem', paddingTop: 2 }}>{item}</div>
        </div>
      ))}
    </div>
  )

  return (
    <div className="screen">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 }}>
        <button className="btn btn-ghost" onClick={onBack} style={{ paddingLeft: 0 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M19 12H5M12 5l-7 7 7 7"/>
          </svg>
          Back
        </button>
        <div style={{ flex: 1 }}/>
        <button className="btn btn-sm btn-secondary" onClick={handleExport}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
          </svg>
          Export
        </button>
      </div>

      <div className="mb-28">
        <div className="section-label mb-8" style={{ color: 'var(--accent)' }}>Full Conclusion</div>
        <h2 style={{ marginBottom: 4 }}>Complete Analysis Report</h2>
        <p className="text-muted" style={{ fontSize: '0.82rem' }}>
          {issueType === 'business' ? 'Business' : 'Personal'} · {new Date().toLocaleDateString()}
        </p>
      </div>

      {/* Problem Summary */}
      <Section title="1. Problem Summary">
        <div className="card" style={{ borderLeft: '3px solid var(--border)' }}>
          <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)' }}>
            {conclusion?.problemSummary || problem}
          </p>
        </div>
      </Section>

      {/* 5 Why Path */}
      <Section title="2. 5 Why Path">
        <div className="card" style={{ padding: '16px 20px' }}>
          {(whyPath || []).map((item, i) => (
            <div key={i} style={{
              display: 'grid',
              gridTemplateColumns: '1fr',
              marginBottom: i < whyPath.length - 1 ? 16 : 0,
              paddingBottom: i < whyPath.length - 1 ? 16 : 0,
              borderBottom: i < whyPath.length - 1 ? '1px solid var(--border)' : 'none'
            }}>
              <div style={{
                fontSize: '0.7rem',
                fontWeight: 800,
                color: ['#2563eb','#7c3aed','#db2777','#ea580c','#dc2626'][i],
                letterSpacing: '0.07em',
                textTransform: 'uppercase',
                marginBottom: 4
              }}>
                Why {i + 1}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 4, fontStyle: 'italic' }}>
                Q: {item.question}
              </div>
              <div style={{ fontSize: '0.92rem', fontWeight: 600 }}>
                A: {item.answer}
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Root Cause */}
      <Section title="3. Most Likely Root Cause">
        <div className="card" style={{ borderLeft: '3px solid var(--danger)', padding: '16px 20px' }}>
          <p style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>
            {conclusion?.mostLikelyRootCause}
          </p>
          {conclusion?.rootCauseCategory && (
            <span className="badge" style={{
              background: 'rgba(239,68,68,0.08)',
              border: '1px solid rgba(239,68,68,0.25)',
              color: 'var(--danger)',
              fontSize: '0.72rem'
            }}>
              {conclusion.rootCauseCategory}
            </span>
          )}
        </div>
      </Section>

      {/* Contributing Factors */}
      <Section title="4. Contributing Factors">
        <div className="card" style={{ padding: '12px 20px' }}>
          <ActionList items={conclusion?.contributingFactors} color="#f59e0b" />
        </div>
      </Section>

      {/* Corrective Actions */}
      <Section title="5. Recommended Corrective Actions">
        <div className="card" style={{ padding: '12px 20px' }}>
          <ActionList items={conclusion?.correctiveActions} color="#2563eb" />
        </div>
      </Section>

      {/* Preventive Actions */}
      <Section title="6. Preventive Actions">
        <div className="card" style={{ padding: '12px 20px' }}>
          <ActionList items={conclusion?.preventiveActions} color="#10b981" />
        </div>
      </Section>

      {/* Action Plan */}
      {(conclusion?.actionPlan || []).length > 0 && (
        <Section title="7. Simple Action Plan">
          <div className="card" style={{ padding: '12px 20px' }}>
            {(conclusion.actionPlan || []).map((item, i) => (
              <div key={i} style={{
                display: 'grid',
                gridTemplateColumns: '28px 1fr auto',
                gap: 12,
                alignItems: 'center',
                padding: '10px 0',
                borderBottom: i < conclusion.actionPlan.length - 1 ? '1px solid var(--border)' : 'none'
              }}>
                <div style={{
                  width: 28, height: 28, borderRadius: '50%',
                  background: 'var(--accent-light)',
                  border: '1px solid rgba(37,99,235,0.25)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.72rem', fontWeight: 800, color: 'var(--accent)'
                }}>
                  {item.priority}
                </div>
                <div style={{ fontSize: '0.88rem' }}>{item.action}</div>
                <div style={{
                  fontSize: '0.72rem',
                  color: 'var(--text-muted)',
                  background: 'var(--bg-secondary)',
                  padding: '3px 8px',
                  borderRadius: 100,
                  whiteSpace: 'nowrap'
                }}>
                  {item.timeframe}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* CTA */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, paddingTop: 8 }}>
        <button className="btn btn-secondary btn-full" onClick={handleExport}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
          </svg>
          Export as Text File
        </button>
        <button className="btn btn-primary btn-full" onClick={onNewAnalysis}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          Start New Analysis
        </button>
      </div>

      <div className="privacy-notice mt-24">
        Saved analyses are stored locally and can be deleted from your History at any time.
      </div>
    </div>
  )
}
