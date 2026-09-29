import { useQuery } from '@tanstack/react-query'
import { Target } from 'lucide-react'
import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router'
import { isApiError } from '../../api/client'
import { listOpportunities } from '../../api/opportunities'
import { OpportunityCard } from '../../components/intelligence/OpportunityCard'
import { Card } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import type { ScoreBand } from '../../types/api'
import { SCORE_BAND_LABELS } from '../intelligence/labels'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { ScoreBandChart } from '../dashboard/ScoreBandChart'

const BANDS: ScoreBand[] = ['high', 'medium', 'low', 'monitor']

export function OpportunitiesPage() {
  useDocumentTitle('Potential Opportunities')
  const [params, setParams] = useSearchParams()
  const band = (params.get('band') as ScoreBand | null) || ''
  const sort = (params.get('sort') as 'score' | 'updated_at' | null) || 'score'
  const organizationId = params.get('organization_id') ?? ''

  const query = useQuery({
    queryKey: ['opportunities', band, sort, organizationId],
    queryFn: () =>
      listOpportunities({
        organization_id: organizationId || undefined,
        band: band ? [band] : undefined,
        sort,
        direction: 'desc',
        limit: 50,
      }),
  })

  const selectClass =
    'h-10 rounded-md border border-default bg-surface px-3 text-body text-primary focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-hidden'

  const rows = query.data?.data ?? []
  const byBand = useMemo(() => {
    const counts: Record<ScoreBand, number> = {
      high: 0,
      medium: 0,
      low: 0,
      monitor: 0,
    }
    for (const row of rows) {
      counts[row.score.band] += 1
    }
    return counts
  }, [rows])

  const content = useMemo(() => {
    if (query.isLoading) {
      return (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-lg" />
          ))}
        </div>
      )
    }
    if (query.isError) {
      const err = query.error
      return (
        <ErrorState
          description={isApiError(err) ? err.message : 'Potential opportunities could not be loaded.'}
          reference={isApiError(err) ? err.requestId : null}
          onRetry={() => void query.refetch()}
          retrying={query.isFetching}
        />
      )
    }
    if (rows.length === 0) {
      return (
        <EmptyState
          icon={Target}
          title={band ? 'No potential opportunities in this band' : 'No potential opportunities yet'}
          description={
            band
              ? 'Try another score band or clear the filter.'
              : 'A potential opportunity appears only when at least two validated signal types correlate, pass the recency rule, and score 50 or higher. Signals can still be useful without one.'
          }
          action={
            band ? (
              <button
                type="button"
                className="text-body font-medium text-navy-600 hover:underline"
                onClick={() => {
                  const next = new URLSearchParams(params)
                  next.delete('band')
                  setParams(next)
                }}
              >
                Clear band filter
              </button>
            ) : (
              <Link to="/signals" className="text-body font-medium text-navy-600 hover:underline">
                Browse signals
              </Link>
            )
          }
        />
      )
    }
    return (
      <div className="space-y-3">
        {rows.map((row) => (
          <OpportunityCard key={row.opportunity_id} opportunity={row} />
        ))}
      </div>
    )
  }, [band, params, query, rows, setParams])

  const total = query.data?.total ?? 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-primary">Potential opportunities</h1>
        <p className="mt-1 text-body-sm text-secondary">
          Prioritized by rules score. Factors and AI explanation stay attached — never a bare number.
          Nothing here is guaranteed; each item is a potential opportunity backed by evidence.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Card className="p-4">
          <p className="text-label text-secondary uppercase">Total</p>
          <p className="mt-1 text-metric tabular-nums text-primary">
            {query.isLoading ? '—' : total}
          </p>
        </Card>
        {BANDS.map((b) => (
          <Card key={b} className="p-4">
            <p className="text-label text-secondary uppercase">{SCORE_BAND_LABELS[b]}</p>
            <p className="mt-1 text-metric tabular-nums text-primary">
              {query.isLoading ? '—' : byBand[b]}
            </p>
            <p className="mt-0.5 text-caption text-muted">In loaded list</p>
          </Card>
        ))}
      </div>

      {!query.isLoading && rows.length > 0 && (
        <ScoreBandChart byBand={byBand} />
      )}

      <div className="flex flex-col gap-3 rounded-lg border border-default bg-surface p-4 shadow-xs sm:flex-row sm:items-end">
        <label>
          <span className="mb-1.5 block text-label text-secondary uppercase">Score band</span>
          <select
            className={selectClass}
            value={band}
            onChange={(e) => {
              const next = new URLSearchParams(params)
              if (e.target.value) next.set('band', e.target.value)
              else next.delete('band')
              setParams(next, { replace: true })
            }}
          >
            <option value="">All bands</option>
            {BANDS.map((b) => (
              <option key={b} value={b}>
                {SCORE_BAND_LABELS[b]}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="mb-1.5 block text-label text-secondary uppercase">Sort</span>
          <select
            className={selectClass}
            value={sort}
            onChange={(e) => {
              const next = new URLSearchParams(params)
              next.set('sort', e.target.value)
              setParams(next, { replace: true })
            }}
          >
            <option value="score">Score, high to low</option>
            <option value="updated_at">Most recently updated</option>
          </select>
        </label>
      </div>

      {content}
    </div>
  )
}
