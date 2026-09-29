import { Link } from 'react-router'
import type { OpportunitySummary } from '../../types/api'
import {
  FACTOR_LABELS,
  ORG_TYPE_LABELS,
  formatUpdatedAt,
} from '../../features/intelligence/labels'
import { cn } from '../../lib/cn'
import { Badge } from '../ui/Badge'
import { ScoreBandBadge } from './ScoreDisplay'

export function OpportunityCard({ opportunity }: { opportunity: OpportunitySummary }) {
  const high = opportunity.score.band === 'high'
  const topFactors = [...opportunity.score.factors]
    .filter((f) => f.points > 0)
    .sort((a, b) => b.points - a.points)
    .slice(0, 3)

  return (
    <Link
      to={`/opportunities/${opportunity.opportunity_id}`}
      className={cn(
        'block rounded-lg border border-default bg-surface p-5 shadow-xs',
        'transition-shadow duration-120 ease-out hover:shadow-sm',
        'focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:outline-hidden',
        high && 'border-l-4 border-l-status-opportunity',
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-h3 text-primary">{opportunity.organization_name}</h3>
            <Badge variant="soft-opportunity">Potential opportunity</Badge>
            {opportunity.data_origin === 'cached' ? (
              <Badge variant="soft-neutral">Cached</Badge>
            ) : null}
          </div>
          <p className="mt-1 text-caption text-secondary">
            {ORG_TYPE_LABELS[opportunity.organization_type] ?? opportunity.organization_type}
            {opportunity.state_code ? ` · ${opportunity.state_code}` : ''}
            {' · '}
            Updated {formatUpdatedAt(opportunity.updated_at)}
          </p>

          <p className="mt-3 text-body-sm text-secondary">
            {opportunity.signal_count} correlated signal
            {opportunity.signal_count === 1 ? '' : 's'}
            {opportunity.score.explanation_status === 'ready' ? ' · AI explanation ready' : ''}
          </p>

          {topFactors.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {topFactors.map((factor) => (
                <li key={factor.key}>
                  <span className="inline-flex items-center rounded-md bg-surface-sunken px-2 py-0.5 text-caption text-secondary">
                    {FACTOR_LABELS[factor.key] ?? factor.key}
                    <span className="ml-1 tabular-nums text-primary">
                      {factor.points}/{factor.max_points}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="shrink-0 text-right">
          <p className="text-metric tabular-nums text-primary">{opportunity.score.value}</p>
          <p className="text-caption text-muted">/ 100</p>
          <div className="mt-1.5 flex justify-end">
            <ScoreBandBadge band={opportunity.score.band} />
          </div>
        </div>
      </div>
    </Link>
  )
}
