import { useQuery } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { isApiError } from '../../api/client'
import { getOpportunity } from '../../api/opportunities'
import { AdvisorPanel } from '../../components/intelligence/AdvisorPanel'
import { AiPanel } from '../../components/intelligence/AiPanel'
import { EvidenceList } from '../../components/intelligence/EvidenceList'
import { ReadableAiBody } from '../../components/intelligence/ReadableInterpretation'
import { RecommendedActionBody } from '../../components/intelligence/RecommendedActionBody'
import { ScoreDisplay } from '../../components/intelligence/ScoreDisplay'
import { SignalCard } from '../../components/intelligence/SignalCard'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { ErrorState } from '../../components/ui/ErrorState'
import { Skeleton } from '../../components/ui/Skeleton'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import {
  ORG_TYPE_LABELS,
  SIGNAL_TYPE_DOT,
  SIGNAL_TYPE_LABELS,
  formatSignalDate,
  formatUpdatedAt,
} from '../intelligence/labels'
import { cn } from '../../lib/cn'

export function OpportunityDetailPage() {
  const { opportunityId = '' } = useParams()
  const [advisorOpen, setAdvisorOpen] = useState(false)
  const query = useQuery({
    queryKey: ['opportunity', opportunityId],
    queryFn: () => getOpportunity(opportunityId),
    enabled: Boolean(opportunityId),
    // First open may backfill recommended_action via one LLM call.
    staleTime: 30_000,
  })

  const pageTitle = query.data
    ? `${query.data.organization_name} — Potential Opportunity`
    : 'Potential Opportunity'
  useDocumentTitle(pageTitle)

  if (query.isLoading) {
    return (
      <div className="grid gap-8 xl:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
        <div className="space-y-4">
          <Skeleton className="h-10 w-2/3" />
          <Skeleton className="h-64 w-full rounded-lg" />
          <Skeleton className="h-40 w-full rounded-lg" />
        </div>
        <Skeleton className="h-96 w-full rounded-lg" />
      </div>
    )
  }

  if (query.isError || !query.data) {
    const err = query.error
    const notFound = isApiError(err) && err.code === 'NOT_FOUND'
    return (
      <ErrorState
        title={notFound ? 'Potential opportunity not found' : 'Something went wrong'}
        description={
          isApiError(err)
            ? err.message
            : 'This potential opportunity could not be loaded.'
        }
        reference={isApiError(err) ? err.requestId : null}
        onRetry={notFound ? undefined : () => void query.refetch()}
        secondaryAction={
          <Link
            to="/opportunities"
            className="text-body font-medium text-navy-600 hover:underline"
          >
            Back to potential opportunities
          </Link>
        }
      />
    )
  }

  const opportunity = query.data
  const signalTypes = [...new Set(opportunity.signals.map((s) => s.signal_type))]

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 space-y-3">
          <p className="text-caption text-secondary">
            <Link to="/opportunities" className="hover:underline">
              Potential Opportunities
            </Link>
            {' / '}
            <Link
              to={`/organizations/${opportunity.organization_id}`}
              className="text-primary hover:underline"
            >
              {opportunity.organization_name}
            </Link>
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-h1 text-primary">{opportunity.organization_name}</h1>
            <Badge variant="soft-opportunity">Potential opportunity</Badge>
            {opportunity.data_origin === 'cached' ? (
              <Badge variant="soft-neutral">Cached</Badge>
            ) : null}
          </div>
          <p className="text-body-sm text-secondary">
            {ORG_TYPE_LABELS[opportunity.organization_type] ?? opportunity.organization_type}
            {opportunity.state_code ? ` · ${opportunity.state_code}` : ''}
            {' · '}
            Updated {formatUpdatedAt(opportunity.updated_at)}
            {' · '}
            {opportunity.signal_count} correlated signal
            {opportunity.signal_count === 1 ? '' : 's'}
          </p>
          {signalTypes.length > 0 && (
            <ul className="flex flex-wrap gap-1.5">
              {signalTypes.map((type) => (
                <li key={type}>
                  <span className="inline-flex items-center gap-1.5 rounded-md bg-surface-sunken px-2 py-0.5 text-caption text-secondary">
                    <span
                      className={cn('size-1.5 rounded-full', SIGNAL_TYPE_DOT[type])}
                      aria-hidden
                    />
                    {SIGNAL_TYPE_LABELS[type]}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <div className="flex flex-wrap gap-2">
            <Link
              to={`/organizations/${opportunity.organization_id}`}
              className="inline-flex h-8 items-center rounded-md border border-default bg-surface px-3 text-body-sm font-medium text-navy-600 hover:bg-surface-sunken"
            >
              View organization
            </Link>
            <Link
              to={`/signals?organization_id=${opportunity.organization_id}`}
              className="inline-flex h-8 items-center rounded-md border border-default bg-surface px-3 text-body-sm font-medium text-navy-600 hover:bg-surface-sunken"
            >
              Org signals
            </Link>
          </div>
        </div>
        <Button variant="ai" icon={Sparkles} onClick={() => setAdvisorOpen((v) => !v)}>
          {advisorOpen ? 'Hide Advisor' : 'Ask Advisor'}
        </Button>
      </div>

      {advisorOpen && (
        <AdvisorPanel
          scopeType="opportunity"
          scopeId={opportunity.opportunity_id}
          scopeLabel={opportunity.organization_name}
          compact
        />
      )}

      <div className="grid gap-8 xl:grid-cols-[minmax(0,2fr)_minmax(300px,1fr)]">
        <div className="space-y-8">
          <ScoreDisplay score={opportunity.score} />

          <section>
            <p className="text-label text-secondary uppercase">Observed signals</p>
            <p className="mt-1 text-caption text-muted">
              Validated facts that were correlated into this potential opportunity
            </p>
            <div className="mt-3 space-y-3">
              {opportunity.signals.map((signal) => (
                <SignalCard key={signal.signal_id} signal={signal} />
              ))}
            </div>
          </section>

          <AiPanel label="correlation">
            <ReadableAiBody text={opportunity.correlation.text} tone="dark" />
            <ul className="relative mt-5 space-y-0 border-l border-indigo-400/40 pl-5">
              {opportunity.signals.map((signal) => (
                <li key={signal.signal_id} className="relative py-2.5">
                  <span
                    className={cn(
                      'absolute top-4 -left-[23px] size-2 rounded-full',
                      SIGNAL_TYPE_DOT[signal.signal_type],
                    )}
                  />
                  <Link
                    to={`/signals/${signal.signal_id}`}
                    className="block rounded-md hover:bg-navy-900/40"
                  >
                    <p className="text-caption text-on-ai-muted">
                      {SIGNAL_TYPE_LABELS[signal.signal_type]}
                      {' · '}
                      {formatSignalDate(signal.date, signal.date_status)}
                    </p>
                    <p className="text-body text-on-ai">{signal.title}</p>
                  </Link>
                </li>
              ))}
            </ul>
          </AiPanel>

          {opportunity.recommended_action ? (
            <AiPanel label="recommended" className="border-l-amber-400">
              <RecommendedActionBody text={opportunity.recommended_action.text} />
              {opportunity.recommended_action.evidence_ids.length > 0 ? (
                <p className="mt-4 text-caption text-on-ai-muted">
                  Grounded in {opportunity.recommended_action.evidence_ids.length} stored
                  evidence item
                  {opportunity.recommended_action.evidence_ids.length === 1 ? '' : 's'} on
                  this potential opportunity — not a guaranteed deal.
                </p>
              ) : null}
            </AiPanel>
          ) : (
            <section className="rounded-xl border border-dashed border-indigo-200 bg-surface-ai-subtle px-5 py-4">
              <p className="text-label text-indigo-600 uppercase">
                Recommended next action
              </p>
              <p className="mt-2 text-body-sm text-secondary">
                No evidence-backed next step was produced for this potential opportunity.
                Open this page again after a scan, or ask the Advisor with opportunity scope.
              </p>
            </section>
          )}
        </div>

        <aside className="xl:sticky xl:top-24 xl:self-start">
          <div className="rounded-lg border border-default bg-surface p-5 shadow-xs">
            <EvidenceList
              items={opportunity.evidence}
              heading={`${opportunity.evidence.length} evidence item${
                opportunity.evidence.length === 1 ? '' : 's'
              }`}
            />
          </div>
          <p className="mt-3 hidden text-caption text-muted xl:block">
            Evidence stays visible beside the score and interpretation so every claim can be opened.
          </p>
        </aside>
      </div>
    </div>
  )
}
