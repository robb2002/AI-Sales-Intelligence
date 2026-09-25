import { Link } from 'react-router'
import type { OpportunitySummary } from '../../types/api'
import {
  ORG_TYPE_LABELS,
  SIGNAL_TYPE_DOT,
  formatUpdatedAt,
} from '../../features/intelligence/labels'
import { cn } from '../../lib/cn'
import { Badge } from '../ui/Badge'
import { ScoreBandBadge } from './ScoreDisplay'

export function OpportunityCard({ opportunity }: { opportunity: OpportunitySummary }) {
  const high = opportunity.score.band === 'high'
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
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-h3 text-primary">{opportunity.organization_name}</h3>
            <Badge variant="soft-opportunity">Potential opportunity</Badge>
          </div>
          <p className="mt-1 text-caption text-secondary">
            {ORG_TYPE_LABELS[opportunity.organization_type] ?? opportunity.organization_type}
            {opportunity.state_code ? ` · ${opportunity.state_code}` : ''}
            {' · '}
            Updated {formatUpdatedAt(opportunity.updated_at)}
          </p>
          <p className="mt-3 flex flex-wrap items-center gap-2 text-body-sm text-secondary">
            <span>
              {opportunity.signal_count} signal{opportunity.signal_count === 1 ? '' : 's'}
            </span>
            <span className="flex items-center gap-1" aria-hidden>
              {Object.values(SIGNAL_TYPE_DOT)
                .slice(0, Math.min(4, opportunity.signal_count || 1))
                .map((cls, i) => (
                  <span key={i} className={cn('size-1.5 rounded-full', cls)} />
                ))}
            </span>
          </p>
        </div>
        <div className="text-right">
          <p className="text-metric tabular-nums text-primary">{opportunity.score.value}</p>
          <div className="mt-1 flex justify-end">
            <ScoreBandBadge band={opportunity.score.band} />
          </div>
        </div>
      </div>
    </Link>
  )
}
