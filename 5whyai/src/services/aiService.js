const BASE = '/api'

export async function fetchNextWhy({ problem, issueType, whyLevel, previousAnswer, whyHistory }) {
  const res = await fetch(`${BASE}/next-why`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ problem, issueType, whyLevel, previousAnswer, whyHistory })
  })
  if (!res.ok) throw new Error(`Server error: ${res.status}`)
  return res.json()
}

export async function fetchConclusion({ problem, issueType, whyPath }) {
  const res = await fetch(`${BASE}/conclusion`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ problem, issueType, whyPath })
  })
  if (!res.ok) throw new Error(`Server error: ${res.status}`)
  return res.json()
}
