import { useQuery } from '@tanstack/react-query'
import { Radio, Search } from 'lucide-react'
import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router'
import { isApiError } from '../../api/client'
import { listSignals } from '../../api/signals'
import { SignalCard } from '../../components/intelligence/SignalCard'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import type { SignalState, SignalType } from '../../types/api'
import {
  SIGNAL_STATE_LABELS,
  SIGNAL_TYPE_LABELS,
  SIGNAL_TYPES,
} from '../intelligence/labels'
import { useDocumentTitle } from '../../lib/useDocumentTitle'

const STATES: SignalState[] = ['validated', 'rejected', 'merged', 'detected', 'superseded']

export function SignalsPage() {
  useDocumentTitle('Signals')
  const [params, setParams] = useSearchParams()
  const signalType = (params.get('signal_type') as SignalType | null) || ''
  const state = (params.get('state') as SignalState | null) || ''
  const q = params.get('q') ?? ''
  const organizationId = params.get('organization_id') ?? ''

  const query = useQuery({
    queryKey: ['signals', signalType, state, q, organizationId],
    queryFn: () =>
      listSignals({
        organization_id: organizationId || undefined,
        signal_type: signalType ? [signalType] : undefined,
        state: state ? [state] : ['validated', 'rejected', 'merged', 'detected', 'superseded'],
        q: q || undefined,
        limit: 50,
      }),
  })

  const filtersActive = Boolean(signalType || state || q.trim() || organizationId)

  const selectClass =
    'h-10 rounded-md border border-default bg-surface px-3 text-body text-primary focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-hidden'

  const content = useMemo(() => {
    if (query.isLoading) {
      return (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-lg" />
          ))}
        </div>
      )
    }
    if (query.isError) {
      const err = query.error
      return (
        <ErrorState
          description={isApiError(err) ? err.message : 'Signals could not be loaded.'}
          reference={isApiError(err) ? err.requestId : null}
          onRetry={() => void query.refetch()}
          retrying={query.isFetching}
        />
      )
    }
    const rows = query.data?.data ?? []
    if (rows.length === 0) {
      return (
        <EmptyState
          icon={Radio}
          title={filtersActive ? 'No results match these filters' : 'No signals yet'}
          description={
            filtersActive
              ? 'Try clearing a filter or widening the search.'
              : 'Run Scan All from the dashboard to collect public sources and detect signals. An empty list means nothing observable was stored yet — not that the product failed.'
          }
          action={
            filtersActive ? (
              <button
                type="button"
                className="text-body font-medium text-navy-600 hover:underline"
                onClick={() => setParams({})}
              >
                Clear filters
              </button>
            ) : (
              <Link to="/" className="text-body font-medium text-navy-600 hover:underline">
                Go to dashboard
              </Link>
            )
          }
        />
      )
    }
    return (
      <div className="space-y-3">
        {rows.map((signal) => (
          <SignalCard key={signal.signal_id} signal={signal} />
        ))}
      </div>
    )
  }, [filtersActive, query, setParams])

  return (
    <div className="space-y-6">
      <div>
        <p className="text-body-sm text-secondary">
          Observed public signals with evidence. Facts stay separate from AI interpretation.
        </p>
      </div>

      <div className="flex flex-col gap-3 rounded-lg border border-default bg-surface p-4 shadow-xs lg:flex-row lg:items-end">
        <label className="min-w-0 flex-1">
          <span className="mb-1.5 block text-label text-secondary uppercase">Search</span>
          <div className="relative">
            <Search
              aria-hidden
              className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted"
              strokeWidth={1.75}
            />
            <input
              value={q}
              onChange={(e) => {
                const next = new URLSearchParams(params)
                if (e.target.value) next.set('q', e.target.value)
                else next.delete('q')
                setParams(next, { replace: true })
              }}
              placeholder="Search title or summary"
              className={`${selectClass} w-full pl-9`}
            />
          </div>
        </label>
        <label>
          <span className="mb-1.5 block text-label text-secondary uppercase">Signal type</span>
          <select
            className={selectClass}
            value={signalType}
            onChange={(e) => {
              const next = new URLSearchParams(params)
              if (e.target.value) next.set('signal_type', e.target.value)
              else next.delete('signal_type')
              setParams(next, { replace: true })
            }}
          >
            <option value="">All types</option>
            {SIGNAL_TYPES.map((t) => (
              <option key={t} value={t}>
                {SIGNAL_TYPE_LABELS[t]}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="mb-1.5 block text-label text-secondary uppercase">State</span>
          <select
            className={selectClass}
            value={state}
            onChange={(e) => {
              const next = new URLSearchParams(params)
              if (e.target.value) next.set('state', e.target.value)
              else next.delete('state')
              setParams(next, { replace: true })
            }}
          >
            <option value="">All states</option>
            {STATES.map((s) => (
              <option key={s} value={s}>
                {SIGNAL_STATE_LABELS[s]}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex items-center justify-between gap-3">
        <p className="text-caption text-secondary">
          {query.data ? `${query.data.total} signal${query.data.total === 1 ? '' : 's'}` : '—'}
        </p>
      </div>

      {content}
    </div>
  )
}
