import { useState } from 'react'

const WHY_COLORS = ['#2563eb', '#7c3aed', '#db2777', '#ea580c', '#dc2626']
const WHY_LABELS = ['Why 1', 'Why 2', 'Why 3', 'Why 4', 'Why 5']

export default function WhyQuestionScreen({
  whyLevel,
  question,
  answers,
  problem,
  whyPath,
  onAnswer,
  loading,
  error
}) {
  const [showOther, setShowOther] = useState(false)
  const [customAnswer, setCustomAnswer] = useState('')

  const color = WHY_COLORS[Math.min(whyLevel - 1, 4)]
  const label = WHY_LABELS[Math.min(whyLevel - 1, 4)]
  const progress = (whyLevel / 5) * 100

  const handleSelect = (answer) => {
    setShowOther(false)
    setCustomAnswer('')
    onAnswer(answer)
  }

  const handleCustomSubmit = () => {
    const trimmed = customAnswer.trim()
    if (trimmed.length < 3) return
    onAnswer(trimmed)
  }

  if (loading) {
    return (
      <div className="screen" style={{ alignItems: 'center', justifyContent: 'center', minHeight: '70vh' }}>
        <div style={{ textAlign: 'center' }}>
          <div className="loading-dots" style={{ justifyContent: 'center', marginBottom: 16 }}>
            <span/><span/><span/>
          </div>
          <p className="text-secondary" style={{ fontSize: '0.9rem' }}>
            {whyLevel > 5 ? 'Generating conclusion…' : `Generating Why ${whyLevel}…`}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="screen">
      {/* Progress */}
      <div className="mb-20">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{
            fontSize: '0.78rem',
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color
          }}>
            {label} of 5
          </span>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            {whyLevel}/5
          </span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{
              width: `${progress}%`,
              background: `linear-gradient(90deg, #2563eb, ${color})`
            }}
          />
        </div>
      </div>

      {/* Problem context (collapsed) */}
      <div className="mb-20" style={{
        padding: '10px 14px',
        background: 'var(--bg-card)',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border)',
        fontSize: '0.82rem'
      }}>
        <span className="text-muted">Problem: </span>
        <span className="text-secondary">{problem}</span>
      </div>

      {/* Why path trail */}
      {whyPath.length > 0 && (
        <div className="mb-20">
          {whyPath.map((item, i) => (
            <div key={i} style={{
              display: 'flex',
              gap: 10,
              marginBottom: 8,
              alignItems: 'flex-start'
            }}>
              <span style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                color: WHY_COLORS[i],
                paddingTop: 2,
                minWidth: 36,
                letterSpacing: '0.05em'
              }}>
                WHY {i + 1}
              </span>
              <span style={{ fontSize: '0.83rem', color: 'var(--text-secondary)' }}>
                {item.answer}
              </span>
            </div>
          ))}
          <div style={{ height: 1, background: 'var(--border)', marginTop: 12 }} />
        </div>
      )}

      {/* Question */}
      <div className="mb-24">
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 12px',
          borderRadius: 100,
          background: `rgba(${color === '#2563eb' ? '37,99,235' : color === '#7c3aed' ? '124,58,237' : color === '#db2777' ? '219,39,119' : color === '#ea580c' ? '234,88,12' : '220,38,38'},0.12)`,
          border: `1px solid ${color}33`,
          color,
          fontSize: '0.75rem',
          fontWeight: 700,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          marginBottom: 14
        }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
          </svg>
          {label}
        </div>

        <h2 style={{ color: 'var(--text-primary)', lineHeight: 1.25 }}>{question}</h2>
      </div>

      {error && (
        <div style={{
          padding: '12px 16px',
          background: 'rgba(239,68,68,0.08)',
          border: '1px solid rgba(239,68,68,0.25)',
          borderRadius: 'var(--radius-sm)',
          color: 'var(--danger)',
          fontSize: '0.85rem',
          marginBottom: 16
        }}>
          {error}
        </div>
      )}

      {/* Answer buttons */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 12 }}>
        {(answers || []).map((answer, i) => (
          <button
            key={i}
            className="answer-btn"
            onClick={() => handleSelect(answer)}
            disabled={loading}
          >
            <span className="answer-btn-index">{i + 1}</span>
            <span style={{ flex: 1 }}>{answer}</span>
          </button>
        ))}
      </div>

      {/* Other answer */}
      {!showOther ? (
        <button
          className="answer-btn"
          onClick={() => setShowOther(true)}
          style={{
            borderStyle: 'dashed',
            color: 'var(--text-muted)'
          }}
        >
          <span style={{
            width: 28, height: 28, borderRadius: '50%', background: 'var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
          }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 5v14M5 12h14"/>
            </svg>
          </span>
          <span>Other Answer</span>
        </button>
      ) : (
        <div style={{ marginTop: 4 }}>
          <textarea
            className="input-field"
            placeholder="Describe the reason in your own words…"
            value={customAnswer}
            onChange={e => setCustomAnswer(e.target.value)}
            rows={2}
            autoFocus
            onKeyDown={e => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleCustomSubmit()
            }}
          />
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button
              className="btn btn-primary"
              style={{ flex: 1 }}
              onClick={handleCustomSubmit}
              disabled={customAnswer.trim().length < 3}
            >
              Submit Answer
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => { setShowOther(false); setCustomAnswer('') }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
