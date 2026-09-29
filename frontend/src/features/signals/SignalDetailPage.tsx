import { useQuery } from '@tanstack/react-query'
import { ExternalLink, Sparkles } from 'lucide-react'
import { Link, useParams } from 'react-router'
import { isApiError } from '../../api/client'
import { getOpportunity } from '../../api/opportunities'
import { getSignal } from '../../api/signals'
import { EvidenceList } from '../../components/intelligence/EvidenceList'
import { OpportunityCard } from '../../components/intelligence/OpportunityCard'
import { ReadableInterpretation } from '../../components/intelligence/ReadableInterpretation'
import {
  SignalStateBadge,
  SignalTypeBadge,
} from '../../components/intelligence/SignalCard'
import { Alert } from '../../components/ui/Alert'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { formatSignalDate } from '../intelligence/labels'

export function SignalDetailPage() {
  const { signalId = '' } = useParams()
  const query = useQuery({
    queryKey: ['signal', signalId],
    queryFn: () => getSignal(signalId),
    enabled: Boolean(signalId),
  })

  const title = query.data?.title ?? 'Signal detail'
  useDocumentTitle(title)

  const oppIds = query.data?.opportunity_ids ?? []
  const oppQuery = useQuery({
    queryKey: ['signal-opportunities', oppIds],
    queryFn: async () => {
      const rows = await Promise.all(oppIds.map((id) => getOpportunity(id)))
      return rows
    },
    enabled: oppIds.length > 0,
  })

  if (query.isLoading) {
    return (
      <div className="mx-auto max-w-240 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full rounded-lg" />
        <Skeleton className="h-56 w-full rounded-lg" />
      </div>
    )
  }

  if (query.isError || !query.data) {
    const err = query.error
    const notFound = isApiError(err) && err.code === 'NOT_FOUND'
    return (
      <ErrorState
        title={notFound ? 'Signal not found' : 'Something went wrong'}
        description={
          isApiError(err)
            ? err.message
            : 'This signal could not be loaded.'
        }
        reference={isApiError(err) ? err.requestId : null}
        onRetry={notFound ? undefined : () => void query.refetch()}
        secondaryAction={
          <Link to="/signals" className="text-body font-medium text-navy-600 hover:underline">
            Back to signals
          </Link>
        }
      />
    )
  }

  const signal = query.data
  const primaryEvidence = signal.evidence[0]

  return (
    <div className="mx-auto max-w-240 space-y-8">
      <header className="space-y-4">
        <p className="text-caption text-secondary">
          <Link to="/signals" className="hover:underline">
            Signals
          </Link>
          {' / '}
          <span className="text-primary">{signal.title}</span>
        </p>

        <div className="flex flex-wrap items-center gap-2">
          <SignalTypeBadge signalType={signal.signal_type} />
          <SignalStateBadge state={signal.state} />
          {signal.data_origin === 'cached' ? (
            <span className="text-caption text-muted">Cached data</span>
          ) : null}
        </div>

        <h1 className="text-h1 text-primary">{signal.title}</h1>

        <p className="text-body-sm text-secondary">
          <Link
            to={`/organizations/${signal.organization_id}`}
            className="font-medium text-navy-600 hover:underline"
          >
            {signal.organization_name}
          </Link>
          {' · '}
          {formatSignalDate(signal.date, signal.date_status)}
        </p>

        <div className="flex flex-wrap gap-2">
          <Link
            to={`/advisor?organization_id=${signal.organization_id}`}
            className="inline-flex h-8 items-center gap-2 rounded-md bg-indigo-600 px-3 text-body-sm font-medium text-inverse hover:bg-indigo-700 focus-visible:ring-2 focus-visible:ring-focus-ring"
          >
            <Sparkles aria-hidden className="size-4" strokeWidth={1.75} />
            Ask Advisor
          </Link>
          <Link
            to={`/signals?organization_id=${signal.organization_id}`}
            className="inline-flex h-8 items-center gap-2 rounded-md border border-default bg-surface px-3 text-body-sm font-medium text-navy-600 hover:bg-surface-sunken focus-visible:ring-2 focus-visible:ring-focus-ring"
          >
            More signals for this org
          </Link>
          {primaryEvidence?.source_url ? (
            <a
              href={primaryEvidence.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-8 items-center gap-1 rounded-md border border-default bg-surface px-3 text-body-sm font-medium text-navy-600 hover:bg-navy-50 focus-visible:ring-2 focus-visible:ring-focus-ring"
            >
              Open primary source
              <ExternalLink aria-hidden className="size-3.5" strokeWidth={1.75} />
            </a>
          ) : null}
        </div>
      </header>

      {signal.state === 'rejected' && signal.rejection_reason && (
        <div className="rounded-lg border border-default bg-surface-sunken px-4 py-3">
          <p className="text-label text-secondary uppercase">Rejection reason</p>
          <p className="mt-1 text-body-sm text-secondary">{signal.rejection_reason}</p>
        </div>
      )}

      <section className="rounded-lg border border-default bg-surface p-6 shadow-xs">
        <p className="text-label text-secondary uppercase">Observed fact</p>
        <p className="mt-1 text-caption text-muted">What the source stated — not an AI prediction</p>
        <p className="mt-3 max-w-[68ch] text-body-lg leading-relaxed text-primary">
          {signal.summary}
        </p>
      </section>

      {signal.ai_summary?.text ? (
        <ReadableInterpretation text={signal.ai_summary.text} />
      ) : null}

      <section>
        {signal.source_count > 1 && (
          <Alert variant="info" className="mb-4" title="Merged cluster">
            These sources describe the same event and were merged into one signal cluster.
          </Alert>
        )}
        <EvidenceList
          items={signal.evidence}
          heading={`Sources (${signal.evidence.length})`}
        />
      </section>

      <section>
        <p className="text-label text-secondary uppercase">Contributing to</p>
        <div className="mt-3 space-y-3">
          {oppIds.length === 0 ? (
            <p className="rounded-lg border border-default bg-surface px-4 py-3 text-body-sm text-secondary">
              This signal does not currently contribute to any potential opportunity. Another
              related validated signal is usually needed before a potential opportunity is formed.
            </p>
          ) : oppQuery.isLoading ? (
            <Skeleton className="h-24 w-full rounded-lg" />
          ) : (
            (oppQuery.data ?? []).map((opp) => (
              <OpportunityCard key={opp.opportunity_id} opportunity={opp} />
            ))
          )}
        </div>
      </section>
    </div>
  )
}
