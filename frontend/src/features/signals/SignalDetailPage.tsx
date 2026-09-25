import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { isApiError } from '../../api/client'
import { getOpportunity } from '../../api/opportunities'
import { getSignal } from '../../api/signals'
import { AiInlineNote } from '../../components/intelligence/AiPanel'
import { EvidenceList } from '../../components/intelligence/EvidenceList'
import { OpportunityCard } from '../../components/intelligence/OpportunityCard'
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

  return (
    <div className="mx-auto max-w-240 space-y-8">
      <div>
        <p className="text-caption text-secondary">
          <Link to="/signals" className="hover:underline">
            Signals
          </Link>
          {' / '}
          <span className="text-primary">{signal.title}</span>
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <SignalTypeBadge signalType={signal.signal_type} />
          <SignalStateBadge state={signal.state} />
        </div>
        <h2 className="mt-3 text-h1 text-primary">{signal.title}</h2>
        <p className="mt-2 text-body-sm text-secondary">
          <span className="font-medium text-navy-600">{signal.organization_name}</span>
          {' · '}
          {formatSignalDate(signal.date, signal.date_status)}
          {signal.data_origin === 'cached' ? ' · Cached data' : ''}
        </p>
      </div>

      {signal.state === 'rejected' && signal.rejection_reason && (
        <div className="rounded-lg border border-default bg-surface-sunken px-4 py-3">
          <p className="text-label text-secondary uppercase">Rejection reason</p>
          <p className="mt-1 text-body-sm text-secondary">{signal.rejection_reason}</p>
        </div>
      )}

      <section className="rounded-lg border border-default bg-surface p-6 shadow-xs">
        <p className="text-label text-secondary uppercase">What the source stated</p>
        <p className="mt-3 max-w-[68ch] text-body-lg text-primary">{signal.summary}</p>
      </section>

      {signal.ai_summary?.text ? (
        <AiInlineNote>{signal.ai_summary.text}</AiInlineNote>
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
              This signal does not currently contribute to any potential opportunity.
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
