const STORAGE_KEY = '5whyai_analyses'

export function saveAnalysis(analysis) {
  const all = getAll()
  const idx = all.findIndex(a => a.id === analysis.id)
  if (idx >= 0) {
    all[idx] = analysis
  } else {
    all.unshift(analysis)
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all))
}

export function getAll() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function getById(id) {
  return getAll().find(a => a.id === id) || null
}

export function deleteAnalysis(id) {
  const all = getAll().filter(a => a.id !== id)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all))
}

export function clearAll() {
  localStorage.removeItem(STORAGE_KEY)
}
