import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ExternalLink, Radar, Sparkles } from 'lucide-react'
import { useId, useState } from 'react'
import { Link } from 'react-router'
import { getCompetitors } from '../../api/competitors'
import { isApiError } from '../../api/client'
import { EvidenceList } from '../../components/intelligence/EvidenceList'
import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import { cn } from '../../lib/cn'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import type { CompetitorItem, CompetitorSignal, CompetitorsResponse } from '../../types/api'
import { formatSignalDate, formatUpdatedAt } from '../intelligence/labels'

const FOCUS =
  'focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:outline-hidden'

function safeHttpsUrl(value: string | null): string | null {
  if (!value) return null
  try {
    const parsed = new URL(value)
    return parsed.protocol === 'https:' ? parsed.toString() : null
  } catch {
    return null
  }
}

function askPersona() {
  window.dispatchEvent(
    new CustomEvent('persona:open', {
      detail: { mode: 'competitor', prompt: 'Give me a competitor update.' },
    }),
  )
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <Card className="p-5">
      <p className="text-label text-secondary uppercase">{label}</p>
      <p className="mt-2 text-h1 text-primary">{value}</p>
    </Card>
  )
}

function CompetitorSignalRow({ signal }: { signal: CompetitorSignal }) {
  const [open, setOpen] = useState(false)
  const panelId = useId()
  return (
    <li className="rounded-lg border border-default bg-surface">
      <div className="flex items-start gap-3 p-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to={`/signals/${signal.signal_id}`}
              className={cn('text-body font-medium text-navy-700 hover:underline', FOCUS)}
            >
              {signal.title}
            </Link>
            {signal.data_origin === 'cached' && <Badge variant="soft-neutral">Cached</Badge>}
          </div>
          <p className="mt-1 text-caption text-secondary">
            {formatSignalDate(signal.date, signal.date_status)}
            {' · '}
            {signal.source_count} source{signal.source_count === 1 ? '' : 's'}
          </p>
          <p className="mt-2 text-body-sm text-secondary">{signal.summary}</p>
        </div>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((v) => !v)}
          className={cn(
            'inline-flex h-8 shrink-0 items-center gap-1 rounded-md px-2 text-caption font-medium text-navy-600 hover:bg-surface-sunken',
            FOCUS,
          )}
        >
          {open ? 'Hide evidence' : 'Show evidence'}
          <ChevronDown
            aria-hidden
            className={cn('size-4 transition-transform duration-120', open && 'rotate-180')}
            strokeWidth={1.75}
          />
        </button>
      </div>
      {open && (
        <div id={panelId} className="border-t border-default bg-surface-sunken p-4">
          <EvidenceList items={signal.evidence} />
        </div>
      )}
    </li>
  )
}

function CompetitorCard({ competitor }: { competitor: CompetitorItem }) {
  const website = safeHttpsUrl(competitor.website_url)
  const active = competitor.tracking_status === 'active'
  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-h3 text-primary">{competitor.name}</h2>
            <Badge variant={active ? 'soft-positive' : 'soft-neutral'}>
              {active ? 'Active' : 'Inactive'}
            </Badge>
          </div>
          <p className="mt-1 text-body-sm text-secondary">
            {website && (
              <>
                <a
                  href={website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={cn('inline-flex items-center gap-1 text-navy-600 hover:underline', FOCUS)}
                >
                  Website
                  <ExternalLink aria-hidden className="size-3.5" strokeWidth={1.75} />
                </a>
                {' · '}
              </>
            )}
            {competitor.last_scanned_at
              ? `Last scanned ${formatUpdatedAt(competitor.last_scanned_at)}`
              : 'Never scanned'}
          </p>
        </div>
        <p className="text-body-sm text-secondary">
          <span className="font-semibold text-primary">{competitor.validated_signal_count}</span>{' '}
          validated signal{competitor.validated_signal_count === 1 ? '' : 's'}
        </p>
      </div>

      {competitor.signals.length === 0 ? (
        <div className="rounded-lg border border-dashed border-default bg-surface-sunken p-4">
          <p className="text-body-sm font-medium text-primary">No competitor evidence collected yet</p>
          <p className="mt-1 text-body-sm text-secondary">
            Nothing has been validated for {competitor.name}.{' '}
            <a href="/#scanning" className={cn('font-medium text-navy-600 hover:underline', FOCUS)}>
              Go to Scanning on the dashboard
            </a>{' '}
            to run a scan.
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          {competitor.signals.map((signal) => (
            <CompetitorSignalRow key={signal.signal_id} signal={signal} />
          ))}
        </ul>
      )}
    </Card>
  )
}

function CompetitorsSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading competitors">
      <div className="grid gap-4 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full rounded-lg" />
        ))}
      </div>
      {Array.from({ length: 3 }).map((_, i) => (
        <Skeleton key={i} className="h-40 w-full rounded-lg" />
      ))}
    </div>
  )
}

function CompetitorsContent({ data }: { data: CompetitorsResponse }) {
  const { totals } = data
  if (totals.competitors === 0 && data.competitors.length === 0) {
    return (
      <Card>
        <EmptyState
          icon={Radar}
          title="No competitors tracked yet"
          description="No competitor organizations are being tracked. Once they are active, run Scan All in the Scanning section of the dashboard to collect public updates."
          action={
            <a
              href="/#scanning"
              className={cn('text-body font-medium text-navy-600 hover:underline', FOCUS)}
            >
              Go to Scanning
            </a>
          }
        />
      </Card>
    )
  }
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <SummaryCard label="Competitors tracked" value={totals.competitors} />
        <SummaryCard label="Validated signals" value={totals.validated_signals} />
        <SummaryCard
          label={`New in the last ${totals.window_days} days`}
          value={totals.new_in_window}
        />
      </div>
      <div className="space-y-4">
        {data.competitors.map((competitor) => (
          <CompetitorCard key={competitor.organization_id} competitor={competitor} />
        ))}
      </div>
    </div>
  )
}

export function CompetitorsPage() {
  useDocumentTitle('Competitors')
  const query = useQuery({
    queryKey: ['competitors'],
    queryFn: getCompetitors,
    refetchOnMount: 'always',
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-h2 font-semibold text-navy-700">Competitor intelligence</h1>
          <p className="mt-1 text-body-sm text-secondary">
            Public updates from assessment and EdTech vendors. Competitor signals are context, never
            customer opportunities.
          </p>
        </div>
        <Button variant="secondary" icon={Sparkles} onClick={askPersona}>
          Ask Sales Persona for a competitor update
        </Button>
      </div>

      {query.data?.data_origin === 'cached' && (
        <Alert variant="cached" title="Showing cached data">
          Some competitor information comes from the cached fallback dataset because a public source
          was temporarily unavailable. Affected items are labelled.
        </Alert>
      )}

      {query.isPending && <CompetitorsSkeleton />}

      {query.isError && (
        <Card>
          <ErrorState
            title="Competitors could not be loaded"
            description={
              isApiError(query.error) ? query.error.message : 'The competitors request failed.'
            }
            reference={isApiError(query.error) ? query.error.requestId : null}
            onRetry={() => void query.refetch()}
            retrying={query.isFetching}
          />
        </Card>
      )}

      {query.data && <CompetitorsContent data={query.data} />}
    </div>
  )
}
