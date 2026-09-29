/** Split stored AI/insight prose into a lead + short bullets for scannable UI.
 * Does not invent content — only reshapes existing text. */

const MAX_BULLETS = 5

export function splitInsightProse(text: string): { lead: string; bullets: string[] } {
  const raw = text.trim()
  if (!raw) return { lead: '', bullets: [] }

  // Prefer existing list markers if the model already wrote them.
  const lines = raw
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
  const marked = lines
    .map((line) => line.replace(/^[-*•]\s+/, '').replace(/^\d+[.)]\s+/, '').trim())
    .filter(Boolean)

  if (lines.length > 1 && lines.some((line) => /^[-*•]|\d+[.)]\s+/.test(line))) {
    const lead = marked[0]
    const bullets = marked.slice(1, 1 + MAX_BULLETS)
    return { lead, bullets }
  }

  const cleaned = raw.replace(/\s+/g, ' ').trim()
  const sentences = cleaned
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean)

  if (sentences.length <= 1) {
    return { lead: cleaned, bullets: [] }
  }

  const lead = sentences[0]
  const bullets = sentences.slice(1, 1 + MAX_BULLETS).map((s) => s.replace(/[.]+$/, ''))
  return { lead, bullets }
}
