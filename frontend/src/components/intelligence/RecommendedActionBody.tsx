import { ArrowRight, Sparkles } from 'lucide-react'
import { RichText } from './RichText'

/** Renders stored recommended-action prose: lead + bullets with **bold** and emoji. */
export function RecommendedActionBody({ text }: { text: string }) {
  const { lead, bullets } = splitRecommendedProse(text)
  if (!lead && bullets.length === 0) return null

  return (
    <div className="space-y-4">
      {lead ? (
        <div className="flex gap-3">
          <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-amber-400/15 text-amber-300">
            <Sparkles aria-hidden className="size-4" strokeWidth={1.75} />
          </span>
          <p className="text-body-lg font-medium leading-relaxed text-on-ai">
            <RichText text={lead} strongClassName="font-semibold text-amber-200" />
          </p>
        </div>
      ) : null}

      {bullets.length > 0 ? (
        <ul className="space-y-2.5 border-l border-amber-400/35 pl-4">
          {bullets.map((bullet, index) => (
            <li key={index} className="flex gap-2.5">
              <ArrowRight
                aria-hidden
                className="mt-1 size-3.5 shrink-0 text-amber-300"
                strokeWidth={2}
              />
              <p className="min-w-0 text-body leading-relaxed text-on-ai-muted">
                <RichText text={bullet} strongClassName="font-semibold text-on-ai" />
              </p>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

function splitRecommendedProse(text: string): { lead: string; bullets: string[] } {
  const raw = text.trim()
  if (!raw) return { lead: '', bullets: [] }

  const lines = raw
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)

  const isBullet = (line: string) => /^[-*•]\s+|^\d+[.)]\s+/.test(line)
  const stripBullet = (line: string) =>
    line.replace(/^[-*•]\s+/, '').replace(/^\d+[.)]\s+/, '').trim()

  if (lines.some(isBullet)) {
    const leadLines: string[] = []
    const bullets: string[] = []
    for (const line of lines) {
      if (isBullet(line)) bullets.push(stripBullet(line))
      else if (bullets.length === 0) leadLines.push(line)
      else bullets.push(line)
    }
    return {
      lead: leadLines.join(' ').trim(),
      bullets: bullets.slice(0, 6),
    }
  }

  // Single paragraph: first sentence as lead, remaining as soft bullets.
  const cleaned = raw.replace(/\s+/g, ' ').trim()
  const sentences = cleaned
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean)
  if (sentences.length <= 1) return { lead: cleaned, bullets: [] }
  return {
    lead: sentences[0],
    bullets: sentences.slice(1, 6).map((s) => s.replace(/[.]+$/, '')),
  }
}
