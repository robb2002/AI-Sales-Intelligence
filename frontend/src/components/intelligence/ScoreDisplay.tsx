import type { ScoreBand, ScorePayload } from '../../types/api'
import { FACTOR_HINTS, FACTOR_LABELS, SCORE_BAND_LABELS } from '../../features/intelligence/labels'
import { cn } from '../../lib/cn'
import { Badge } from '../ui/Badge'
import { Tooltip } from '../ui/Tooltip'
import { AiPanel } from './AiPanel'

const BAND_BADGE: Record<ScoreBand, string> = {
  high: 'border-transparent bg-amber-50 text-amber-700',
  medium: 'border-navy-200 bg-navy-50 text-navy-500',
  low: 'border-default bg-surface-sunken text-neutral-500',
  monitor: 'border-transparent bg-transparent text-neutral-400',
}

export function ScoreBandBadge({ band }: { band: ScoreBand }) {
  return (
    <span
      className={cn(
        'inline-flex h-6 items-center rounded-full border px-2.5 text-caption font-medium uppercase tracking-wide',
        BAND_BADGE[band],
      )}
    >
      {SCORE_BAND_LABELS[band]}
    </span>
  )
}

export function ScoreDisplay({ score }: { score: ScorePayload }) {
  const delta =
    score.previous_value != null ? score.value - score.previous_value : null

  return (
    <section className="rounded-lg border border-default bg-surface p-6 shadow-xs">
      <p className="text-label text-secondary uppercase">Opportunity score</p>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <p className="text-score text-primary tabular-nums">
          {score.value}
          <span className="ml-2 text-h2 font-semibold text-secondary">/ 100</span>
        </p>
        <ScoreBandBadge band={score.band} />
        {delta != null && delta !== 0 && (
          <span className="text-caption text-status-neutral">
            {delta > 0 ? '+' : ''}
            {delta} since previous score
          </span>
        )}
      </div>
      <p className="mt-1 text-caption text-muted">Weight version {score.weight_version}</p>

      <div className="my-5 border-t border-default" />

      <p className="text-label text-secondary uppercase">Score factors</p>
      <ul className="mt-3 space-y-1">
        {score.factors.map((factor) => {
          const pct = factor.max_points > 0 ? (factor.points / factor.max_points) * 100 : 0
          const name = FACTOR_LABELS[factor.key] ?? factor.key
          return (
            <li key={factor.key} className="flex h-8 items-center gap-3">
              <Tooltip content={FACTOR_HINTS[factor.key] ?? name} side="bottom" className="max-w-64 whitespace-normal">
                <span className="w-44 shrink-0 truncate text-body-sm text-secondary">{name}</span>
              </Tooltip>
              <div className="h-1.5 min-w-0 flex-1 rounded-full bg-surface-sunken">
                <div
                  className="h-1.5 rounded-full bg-amber-500"
                  style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
                />
              </div>
              <span className="w-14 shrink-0 text-right text-body-sm tabular-nums text-secondary">
                {factor.points} / {factor.max_points}
              </span>
            </li>
          )
        })}
      </ul>

      <div className="mt-6">
        {score.explanation_status === 'ready' && score.explanation ? (
          <AiPanel label="explanation">{score.explanation.text}</AiPanel>
        ) : (
          <div className="rounded-xl border border-dashed border-indigo-200 bg-surface-ai-subtle px-5 py-4">
            <p className="text-label text-indigo-600 uppercase">AI explanation unavailable</p>
            <p className="mt-2 text-body-sm text-secondary">
              The rules score and factor breakdown above are still valid. An AI explanation was not
              stored for this score.
            </p>
            <Badge variant="soft-ai" className="mt-3">
              Score unaffected
            </Badge>
          </div>
        )}
      </div>
    </section>
  )
}
